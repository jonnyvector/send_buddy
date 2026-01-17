from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .models import Friendship
from .serializers import (
    FriendshipSerializer,
    FriendshipCreateSerializer,
    FriendSerializer,
    FriendSuggestionSerializer,
    FriendshipStatusSerializer
)
from .services import FriendshipService
from users.models import User, Block


class FriendshipPagination(PageNumberPagination):
    """Custom pagination for friendships"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class FriendshipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing friendships.

    Endpoints:
    - GET /api/friendships/ - List user's accepted friendships
    - POST /api/friendships/ - Send friend request
    - GET /api/friendships/pending/ - List pending requests received
    - GET /api/friendships/sent/ - List pending requests sent
    - GET /api/friendships/friends/ - List just the friend users (not friendships)
    - PATCH /api/friendships/{id}/accept/ - Accept friend request
    - PATCH /api/friendships/{id}/decline/ - Decline friend request
    - DELETE /api/friendships/{id}/ - Remove friend
    - GET /api/friendships/suggestions/ - Get friend suggestions
    - POST /api/friendships/check_status/ - Check friendship status with a user
    """
    permission_classes = [IsAuthenticated]
    pagination_class = FriendshipPagination
    serializer_class = FriendshipSerializer

    def get_queryset(self):
        """
        Return friendships where user is requester or addressee.
        By default shows only accepted friendships.
        Enforces bilateral blocking.
        """
        user = self.request.user

        # Get blocked user IDs (bilateral)
        blocked_users = Block.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker', 'blocked')

        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user.id:
                blocked_ids.add(blocked_id)
            else:
                blocked_ids.add(blocker_id)

        # Return accepted friendships by default, excluding blocked users
        queryset = Friendship.objects.filter(
            Q(requester=user, status='accepted') |
            Q(addressee=user, status='accepted')
        ).exclude(
            Q(requester_id__in=blocked_ids) |
            Q(addressee_id__in=blocked_ids)
        ).select_related('requester', 'addressee').order_by('-accepted_at')

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return FriendshipCreateSerializer
        elif self.action == 'friends':
            return FriendSerializer
        elif self.action == 'suggestions':
            return FriendSuggestionSerializer
        elif self.action == 'check_status':
            return FriendshipStatusSerializer
        return FriendshipSerializer

    @method_decorator(ratelimit(key='user', rate='20/h', method='POST'))
    def create(self, request):
        """Send friend request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            friendship = serializer.save()
            response_serializer = FriendshipSerializer(friendship, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """List pending friend requests received by the user"""
        pending_requests = FriendshipService.get_pending_requests(request.user)
        page = self.paginate_queryset(pending_requests)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sent(self, request):
        """List pending friend requests sent by the user"""
        sent_requests = FriendshipService.get_sent_requests(request.user)
        page = self.paginate_queryset(sent_requests)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(sent_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def friends(self, request):
        """List user's friends (returns User objects, not Friendship objects)"""
        friends = FriendshipService.get_friends(request.user)
        page = self.paginate_queryset(friends)

        if page is not None:
            serializer = FriendSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FriendSerializer(friends, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def accept(self, request, pk=None):
        """Accept friend request"""
        try:
            friendship = FriendshipService.accept_friend_request(pk, request.user)
            serializer = self.get_serializer(friendship)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['patch'])
    def decline(self, request, pk=None):
        """Decline friend request"""
        try:
            FriendshipService.decline_friend_request(pk, request.user)
            return Response(
                {'message': 'Friend request declined'},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, pk=None):
        """Remove friend (unfriend)"""
        try:
            FriendshipService.remove_friend(pk, request.user)
            return Response(
                {'message': 'Friend removed successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get friend suggestions"""
        limit = int(request.query_params.get('limit', 10))
        suggestions = FriendshipService.suggest_friends(request.user, limit=limit)

        # Transform the suggestions into serializer format
        serialized_suggestions = []
        for suggestion in suggestions:
            serialized_suggestions.append({
                'user': suggestion['user'],
                'reason': suggestion['reason'],
                'mutual_friends_count': suggestion['mutual_friends_count']
            })

        serializer = FriendSuggestionSerializer(serialized_suggestions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """Check friendship status with another user"""
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        current_user = request.user

        # Check blocking status
        is_blocked = Block.objects.filter(
            Q(blocker=current_user, blocked=target_user) |
            Q(blocker=target_user, blocked=current_user)
        ).exists()

        # Check friendship status
        friendship = Friendship.objects.filter(
            Q(requester=current_user, addressee=target_user) |
            Q(requester=target_user, addressee=current_user)
        ).first()

        status_data = {
            'user_id': user_id,
            'is_friend': False,
            'is_pending_sent': False,
            'is_pending_received': False,
            'is_blocked': is_blocked,
            'friendship_id': None
        }

        if friendship:
            status_data['friendship_id'] = friendship.id

            if friendship.status == 'accepted':
                status_data['is_friend'] = True
            elif friendship.status == 'pending':
                if friendship.requester == current_user:
                    status_data['is_pending_sent'] = True
                else:
                    status_data['is_pending_received'] = True

        serializer = FriendshipStatusSerializer(status_data)
        return Response(serializer.data)