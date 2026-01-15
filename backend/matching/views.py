from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from datetime import date
from trips.models import Trip
from .services import MatchingService
from .serializers import MatchListSerializer, MatchDetailSerializer


@method_decorator(ratelimit(key='user', rate='30/m', method='GET'), name='list')
class MatchViewSet(viewsets.ViewSet):
    """ViewSet for match operations"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get matches for a trip"""

        trip_id = request.query_params.get('trip')
        limit = int(request.query_params.get('limit', 10))

        # Get trip
        if trip_id:
            try:
                trip = Trip.objects.select_related('destination').prefetch_related(
                    'preferred_crags', 'availability'
                ).get(id=trip_id, user=request.user)
            except Trip.DoesNotExist:
                return Response(
                    {'detail': 'Trip not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get next upcoming trip
            trip = Trip.objects.filter(
                user=request.user,
                start_date__gte=date.today(),
                is_active=True
            ).select_related('destination').prefetch_related(
                'preferred_crags', 'availability'
            ).order_by('start_date').first()

            if not trip:
                return Response(
                    {'detail': 'No upcoming trips'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Run matching algorithm
        service = MatchingService(request.user, trip, limit=min(limit, 50))
        matches = service.get_matches()

        # Serialize response
        data = {
            'trip': trip,
            'matches': matches
        }
        serializer = MatchListSerializer(data)

        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='detail')
    def match_detail(self, request, pk=None):
        """Get detailed match info for a specific user"""

        trip_id = request.query_params.get('trip')
        matched_user_id = pk

        # Get trip (same logic as list)
        if trip_id:
            try:
                trip = Trip.objects.select_related('destination').prefetch_related(
                    'preferred_crags', 'availability'
                ).get(id=trip_id, user=request.user)
            except Trip.DoesNotExist:
                return Response(
                    {'detail': 'Trip not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            trip = Trip.objects.filter(
                user=request.user,
                start_date__gte=date.today(),
                is_active=True
            ).select_related('destination').prefetch_related(
                'preferred_crags', 'availability'
            ).order_by('start_date').first()

            if not trip:
                return Response(
                    {'detail': 'No upcoming trips'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Run matching for this specific user
        service = MatchingService(request.user, trip, limit=50)
        all_matches = service.get_matches()

        # Find the specific match
        matched_user = next(
            (m for m in all_matches if str(m['user'].id) == matched_user_id),
            None
        )

        if not matched_user:
            return Response(
                {'detail': 'Match not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Add detailed availability overlap and grade compatibility
        serializer = MatchDetailSerializer(matched_user)

        return Response(serializer.data)
