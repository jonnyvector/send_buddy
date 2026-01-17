from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer, MarkReadSerializer
import logging

logger = logging.getLogger(__name__)


class NotificationPagination(PageNumberPagination):
    """Custom pagination for notifications"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@method_decorator(ratelimit(key='user', rate='60/m', method='GET'), name='list')
@method_decorator(ratelimit(key='user', rate='60/m', method='GET'), name='unread')
@method_decorator(ratelimit(key='user', rate='60/m', method='GET'), name='unread_count')
class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications.

    Provides endpoints for:
    - Listing all notifications (paginated)
    - Getting unread notifications
    - Getting unread count
    - Marking notifications as read
    - Deleting notifications
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        """
        Get notifications for the authenticated user.
        Uses select_related for optimal query performance.
        """
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related(
            'recipient',
            'content_type'
        ).prefetch_related(
            'content_object'
        )

    def list(self, request, *args, **kwargs):
        """
        GET /api/notifications/
        List all notifications for the authenticated user (paginated)
        """
        queryset = self.get_queryset()

        # Optional filter by read/unread status
        read_status = request.query_params.get('read')
        if read_status is not None:
            is_read = read_status.lower() == 'true'
            queryset = queryset.filter(is_read=is_read)

        # Optional filter by notification type
        notification_type = request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='unread')
    def unread(self, request):
        """
        GET /api/notifications/unread/
        Get all unread notifications for the authenticated user.
        Returns full notification objects with optional limit.
        """
        limit = request.query_params.get('limit')
        queryset = self.get_queryset().filter(is_read=False)

        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        GET /api/notifications/unread-count/
        Get count of unread notifications only (lightweight endpoint).
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """
        POST /api/notifications/{id}/mark-read/
        Mark a single notification as read.
        """
        notification = self.get_object()

        # Ensure user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'Not authorized to modify this notification'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_read()
        serializer = self.get_serializer(notification)

        logger.info(
            f"Notification {notification.id} marked as read by user {request.user.id}"
        )

        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        POST /api/notifications/mark-all-read/
        Mark all unread notifications as read for the authenticated user.
        """
        updated_count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )

        logger.info(
            f"User {request.user.id} marked {updated_count} notifications as read"
        )

        return Response({
            'detail': f'Marked {updated_count} notifications as read',
            'count': updated_count
        })

    @action(detail=True, methods=['post'], url_path='mark-popup-shown')
    def mark_popup_shown(self, request, pk=None):
        """
        POST /api/notifications/{id}/mark-popup-shown/
        Mark that the popup was shown to the user for this notification.
        Used by frontend to track which popups have been displayed.
        """
        notification = self.get_object()

        # Ensure user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'Not authorized to modify this notification'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_popup_shown()
        serializer = self.get_serializer(notification)

        logger.info(
            f"Notification {notification.id} popup shown to user {request.user.id}"
        )

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/notifications/{id}/
        Delete a single notification.
        """
        notification = self.get_object()

        # Ensure user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'Not authorized to delete this notification'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification_id = notification.id
        notification.delete()

        logger.info(
            f"Notification {notification_id} deleted by user {request.user.id}"
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
