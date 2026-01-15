from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import never_cache
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from .models import User, Report
from .serializers import AdminReportSerializer, UpdateReportSerializer
from climbing_sessions.models import Session


@api_view(['GET'])
@permission_classes([IsAdminUser])
@never_cache
def list_reports(request):
    """List all reports (admin only)"""
    status_filter = request.query_params.get('status')
    ordering = request.query_params.get('ordering', '-created_at')

    queryset = Report.objects.select_related(
        'reporter', 'reported'
    ).all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Validate and apply ordering
    allowed_ordering = ['created_at', '-created_at', 'updated_at', '-updated_at']
    if ordering in allowed_ordering:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-created_at')

    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.max_page_size = 100
    page = paginator.paginate_queryset(queryset, request)

    serializer = AdminReportSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@never_cache
def update_report(request, report_id):
    """Update report status (admin only)"""
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Track if status changed
    old_status = report.status

    serializer = UpdateReportSerializer(
        report,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # Send email notification if status changed to investigating, resolved, or dismissed
    if old_status != report.status and report.status in ['investigating', 'resolved', 'dismissed']:
        from .email import send_report_status_update
        try:
            send_report_status_update(report)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send report status update email: {e}")

    # Return full report data
    response_serializer = AdminReportSerializer(report)
    return Response(response_serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
@never_cache
def disable_user(request, user_id):
    """Disable user account (admin only)"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get duration from request
    duration_days = request.data.get('duration_days')
    reason = request.data.get('reason', 'Admin action')

    # Validate duration
    disabled_until = None
    if duration_days:
        try:
            days = int(duration_days)
            if days > 0:
                disabled_until = timezone.now() + timedelta(days=days)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid duration_days. Must be a positive integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Disable user
    user.is_active = False
    user.save()

    # Future: Store disable info in user model or separate DisableLog table
    # For now, we could add fields to User model:
    # user.disabled_until = disabled_until
    # user.disable_reason = reason
    # user.save()

    # Cancel all pending/accepted sessions
    Session.objects.filter(
        Q(inviter=user) | Q(invitee=user),
        status__in=['pending', 'accepted']
    ).update(status='cancelled')

    return Response({
        'message': 'User account disabled',
        'user_id': str(user.id),
        'disabled_until': disabled_until.isoformat() if disabled_until else None
    }, status=status.HTTP_200_OK)
