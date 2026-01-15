from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Avg
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from .models import Session, Message, Feedback
from .serializers import (
    SessionSerializer, SessionListSerializer, CreateSessionSerializer,
    MessageSerializer, FeedbackSerializer, FeedbackStatsSerializer
)


@method_decorator(ratelimit(key='user', rate='10/h', method='POST'), name='create')
class SessionViewSet(viewsets.ModelViewSet):
    """ViewSet for session operations"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Session.objects.filter(
            Q(inviter=self.request.user) | Q(invitee=self.request.user)
        ).select_related('inviter', 'invitee', 'trip__destination').prefetch_related('messages')

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by role
        role_filter = self.request.query_params.get('role')
        if role_filter == 'inviter':
            queryset = queryset.filter(inviter=self.request.user)
        elif role_filter == 'invitee':
            queryset = queryset.filter(invitee=self.request.user)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return SessionListSerializer
        return SessionSerializer

    def create(self, request):
        """Send invitation"""
        serializer = CreateSessionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        session = Session.objects.create(
            inviter=request.user,
            invitee=serializer.validated_data['invitee'],
            trip=serializer.validated_data['trip'],
            proposed_date=serializer.validated_data['proposed_date'],
            time_block=serializer.validated_data['time_block'],
            crag=serializer.validated_data.get('crag', ''),
            goal=serializer.validated_data.get('goal', ''),
            status='pending'
        )

        # Send invitation email to invitee
        from users.email import send_session_invitation
        try:
            send_session_invitation(session)
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send session invitation email: {e}")

        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept invitation"""
        session = self.get_object()

        if session.invitee != request.user:
            return Response(
                {'detail': 'Only invitee can accept'},
                status=status.HTTP_403_FORBIDDEN
            )

        if session.status != 'pending':
            return Response(
                {'detail': 'Can only accept pending invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.status = 'accepted'
        session.save()

        # Send notification to inviter
        from users.email import send_session_accepted
        try:
            send_session_accepted(session)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send session accepted email: {e}")

        return Response({
            'id': session.id,
            'status': 'accepted',
            'message': 'Invitation accepted'
        })

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline invitation"""
        session = self.get_object()

        if session.invitee != request.user:
            return Response(
                {'detail': 'Only invitee can decline'},
                status=status.HTTP_403_FORBIDDEN
            )

        session.status = 'declined'
        session.save()

        # Add optional message
        message_body = request.data.get('message')
        if message_body:
            Message.objects.create(
                session=session,
                sender=request.user,
                body=message_body
            )
            session.last_message_at = now()
            session.save()

        # TODO: Send notification to inviter (Phase 6+)

        return Response({
            'id': session.id,
            'status': 'declined',
            'message': 'Invitation declined'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel session"""
        session = self.get_object()

        if request.user not in [session.inviter, session.invitee]:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        session.status = 'cancelled'
        session.save()

        # Add optional reason as message
        reason = request.data.get('reason')
        if reason:
            Message.objects.create(
                session=session,
                sender=request.user,
                body=f"Cancelled: {reason}"
            )
            session.last_message_at = now()
            session.save()

        # Send notification to other party
        from users.email import send_session_cancelled
        recipient = session.invitee if request.user == session.inviter else session.inviter
        try:
            send_session_cancelled(session, request.user, recipient, reason)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send session cancelled email: {e}")

        return Response({
            'id': session.id,
            'status': 'cancelled',
            'message': 'Session cancelled'
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark session as completed"""
        session = self.get_object()

        if request.user not in [session.inviter, session.invitee]:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        session.status = 'completed'
        session.save()

        # Send feedback reminders to both participants
        from users.email import send_session_completed_reminder
        try:
            # Send to inviter
            send_session_completed_reminder(session, session.inviter, session.invitee)
            # Send to invitee
            send_session_completed_reminder(session, session.invitee, session.inviter)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send session completed reminder emails: {e}")

        return Response({
            'id': session.id,
            'status': 'completed',
            'message': 'Session marked as completed. Please provide feedback.'
        })

    @action(detail=True, methods=['get', 'post'])
    @method_decorator(ratelimit(key='user', rate='100/h', method='POST'))
    def messages(self, request, pk=None):
        """Get or send messages"""
        session = self.get_object()

        if request.method == 'GET':
            messages = session.messages.all().order_by('created_at')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            body = request.data.get('body')
            if not body:
                return Response(
                    {'detail': 'Message body required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if session status allows messaging
            if session.status not in ['pending', 'accepted']:
                return Response(
                    {'detail': 'Can only send messages to pending or accepted sessions'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            message = Message.objects.create(
                session=session,
                sender=request.user,
                body=body
            )

            session.last_message_at = now()
            session.save()

            # TODO: Send notification to other party (Phase 6+)

            return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark messages as read"""
        # TODO: Implement unread tracking (future phase)
        return Response({'message': 'Messages marked as read'})


# ============================================================================
# PHASE 6: FEEDBACK VIEWS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
@never_cache
def submit_feedback(request, session_id):
    """Submit post-session feedback"""
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        session = Session.objects.select_related(
            'inviter', 'invitee'
        ).get(id=session_id)
    except Session.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    if request.user not in [session.inviter, session.invitee]:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Use serializer for validation and creation
    serializer = FeedbackSerializer(
        data=request.data,
        context={'session': session, 'user': request.user}
    )

    try:
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()

        return Response({
            'message': 'Feedback submitted successfully',
            'feedback_id': str(feedback.id)
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Handle duplicate feedback
        if 'already submitted' in str(e):
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT
            )
        raise


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def feedback_stats(request):
    """Get aggregate feedback stats for current user"""
    feedbacks = Feedback.objects.filter(ratee=request.user)

    if not feedbacks.exists():
        stats_data = {
            'total_ratings': 0,
            'average_safety': 0.0,
            'average_communication': 0.0,
            'average_overall': 0.0,
            'distribution': {
                '1_stars': 0,
                '2_stars': 0,
                '3_stars': 0,
                '4_stars': 0,
                '5_stars': 0
            }
        }
        serializer = FeedbackStatsSerializer(stats_data)
        return Response(serializer.data)

    # Calculate aggregates
    total = feedbacks.count()
    aggregates = feedbacks.aggregate(
        avg_safety=Avg('safety_rating'),
        avg_comm=Avg('communication_rating'),
        avg_overall=Avg('overall_rating')
    )

    # Calculate distribution (consistent naming: all plural)
    distribution = {}
    for i in range(1, 6):
        count = feedbacks.filter(overall_rating=i).count()
        distribution[f'{i}_stars'] = count

    stats_data = {
        'total_ratings': total,
        'average_safety': round(aggregates['avg_safety'], 2),
        'average_communication': round(aggregates['avg_comm'], 2),
        'average_overall': round(aggregates['avg_overall'], 2),
        'distribution': distribution
    }

    serializer = FeedbackStatsSerializer(stats_data)
    return Response(serializer.data)
