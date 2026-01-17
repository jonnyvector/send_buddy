from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
import logging

from .models import TripOverlap
from .serializers import (
    TripOverlapSerializer,
    TripOverlapDetailSerializer,
    DismissOverlapSerializer
)
from .services import OverlapEngine

logger = logging.getLogger(__name__)


class TripOverlapViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing trip overlaps.
    Users can only see overlaps they are part of.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TripOverlapSerializer

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return TripOverlapDetailSerializer
        return TripOverlapSerializer

    def get_queryset(self):
        """
        Get overlaps for the current user.
        - Filter overlaps where user is either user1 or user2
        - Exclude dismissed overlaps
        - Only show future/current overlaps
        """
        user = self.request.user
        today = timezone.now().date()

        queryset = TripOverlap.objects.filter(
            Q(user1=user) | Q(user2=user),
            overlap_end_date__gte=today
        )

        # Exclude dismissed overlaps
        queryset = queryset.exclude(
            Q(user1=user, user1_dismissed=True) |
            Q(user2=user, user2_dismissed=True)
        )

        # Apply filters from query params
        destination_slug = self.request.query_params.get('destination')
        if destination_slug:
            queryset = queryset.filter(overlap_destination__slug=destination_slug)

        min_score = self.request.query_params.get('min_score')
        if min_score:
            try:
                queryset = queryset.filter(overlap_score__gte=int(min_score))
            except ValueError:
                pass  # Ignore invalid score values

        # Optimize query with select_related
        queryset = queryset.select_related(
            'user1', 'user2', 'trip1', 'trip2', 'overlap_destination'
        ).prefetch_related(
            'trip1__preferred_crags', 'trip2__preferred_crags'
        )

        # Order by score (highest first) and then by start date
        return queryset.order_by('-overlap_score', 'overlap_start_date')

    def list(self, request, *args, **kwargs):
        """
        List all overlaps for the current user.
        Supports filtering by destination and minimum score.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Add pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        # Add summary statistics
        total_overlaps = queryset.count()
        high_score_overlaps = queryset.filter(overlap_score__gte=70).count()

        return Response({
            'count': total_overlaps,
            'high_score_count': high_score_overlaps,
            'results': serializer.data
        })

    @action(detail=True, methods=['patch'])
    def dismiss(self, request, pk=None):
        """
        Dismiss an overlap so it won't appear in the user's list.
        """
        overlap = self.get_object()

        # Use the service to handle dismissal
        success = OverlapEngine.dismiss_overlap(overlap.id, request.user)

        if success:
            return Response(
                {'status': 'dismissed', 'message': 'Overlap has been dismissed'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Could not dismiss overlap'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def detect_for_user(self, request):
        """
        Manually trigger overlap detection for the current user.
        This is useful after creating/updating trips.
        """
        try:
            new_overlaps = OverlapEngine.detect_overlaps_for_user(request.user)

            # Serialize the new overlaps
            serializer = TripOverlapSerializer(
                new_overlaps,
                many=True,
                context={'request': request}
            )

            return Response({
                'status': 'success',
                'message': f'Detected {len(new_overlaps)} new overlaps',
                'overlaps': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error detecting overlaps for user {request.user.id}: {e}")
            return Response(
                {'error': 'Failed to detect overlaps'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def dismissed(self, request):
        """
        Get list of dismissed overlaps for the current user.
        Useful for potentially un-dismissing overlaps.
        """
        user = request.user
        today = timezone.now().date()

        queryset = TripOverlap.objects.filter(
            Q(user1=user, user1_dismissed=True) |
            Q(user2=user, user2_dismissed=True),
            overlap_end_date__gte=today
        ).select_related(
            'user1', 'user2', 'trip1', 'trip2', 'overlap_destination'
        ).order_by('-overlap_score', 'overlap_start_date')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def undismiss(self, request, pk=None):
        """
        Un-dismiss a previously dismissed overlap.
        """
        try:
            overlap = TripOverlap.objects.get(id=pk)
        except TripOverlap.DoesNotExist:
            return Response(
                {'error': 'Overlap not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is part of this overlap
        if overlap.user1 == request.user:
            overlap.user1_dismissed = False
            overlap.save()
        elif overlap.user2 == request.user:
            overlap.user2_dismissed = False
            overlap.save()
        else:
            return Response(
                {'error': 'You are not part of this overlap'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(overlap)
        return Response({
            'status': 'undismissed',
            'overlap': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get statistics about the user's overlaps.
        """
        user = request.user
        today = timezone.now().date()

        # All overlaps (including dismissed)
        all_overlaps = TripOverlap.objects.filter(
            Q(user1=user) | Q(user2=user),
            overlap_end_date__gte=today
        )

        # Active overlaps
        active_overlaps = all_overlaps.exclude(
            Q(user1=user, user1_dismissed=True) |
            Q(user2=user, user2_dismissed=True)
        )

        # Calculate statistics
        stats = {
            'total_overlaps': all_overlaps.count(),
            'active_overlaps': active_overlaps.count(),
            'dismissed_overlaps': all_overlaps.count() - active_overlaps.count(),
            'high_score_overlaps': active_overlaps.filter(overlap_score__gte=70).count(),
            'connections_made': all_overlaps.filter(connection_created=True).count(),
            'average_score': active_overlaps.aggregate(
                avg_score=models.Avg('overlap_score')
            )['avg_score'] or 0,
            'destinations': list(
                active_overlaps.values('overlap_destination__name', 'overlap_destination__slug')
                .annotate(count=models.Count('id'))
                .order_by('-count')[:5]
            )
        }

        return Response(stats)
