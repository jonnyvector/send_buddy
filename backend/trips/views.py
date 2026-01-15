from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.db.models import Count, Min, Max
from datetime import date, datetime
from django.db.models import Q
from .models import Destination, Crag, Trip, AvailabilityBlock
from .serializers import (
    DestinationSerializer, DestinationListSerializer,
    DestinationAutocompleteSerializer,
    CragSerializer, TripSerializer, TripListSerializer,
    TripUpdateSerializer, AvailabilityBlockSerializer
)


# ==============================================================================
# DESTINATION & CRAG VIEWSETS
# ==============================================================================

class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for destinations (for autocomplete/browsing)"""
    queryset = Destination.objects.all()
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return DestinationListSerializer
        return DestinationSerializer

    def get_queryset(self):
        queryset = Destination.objects.all()

        # Search filter for autocomplete
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Limit for autocomplete (only on list action)
        if self.action == 'list':
            limit = self.request.query_params.get('limit', 20)
            return queryset[:int(limit)]

        return queryset

    @action(detail=True, methods=['get'], url_path='crags')
    def crags(self, request, slug=None):
        """Get all crags for a destination"""
        destination = self.get_object()
        crags = destination.crags.all()
        serializer = CragSerializer(crags, many=True)
        return Response({
            'destination': {
                'slug': destination.slug,
                'name': destination.name
            },
            'crags': serializer.data
        })


# ==============================================================================
# TRIP VIEWSET
# ==============================================================================

@method_decorator(ratelimit(key='user', rate='20/h', method='POST'), name='create')
class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TripListSerializer
        elif self.action in ['update', 'partial_update']:
            return TripUpdateSerializer
        return TripSerializer

    def get_queryset(self):
        queryset = Trip.objects.filter(user=self.request.user).select_related('destination').prefetch_related('preferred_crags', 'availability')

        # Filters
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            queryset = queryset.filter(start_date__gte=date.today())

        return queryset.order_by('start_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def next(self, request):
        """Get next upcoming trip"""
        trip = Trip.objects.filter(
            user=request.user,
            start_date__gte=date.today(),
            is_active=True
        ).select_related('destination').prefetch_related('preferred_crags').order_by('start_date').first()

        if trip:
            serializer = TripSerializer(trip)
            return Response(serializer.data)
        else:
            return Response({'detail': 'No upcoming trips'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='availability')
    def add_availability(self, request, pk=None):
        """Add a single availability block"""
        trip = self.get_object()
        serializer = AvailabilityBlockSerializer(data=request.data, context={'trip': trip})
        serializer.is_valid(raise_exception=True)
        serializer.save(trip=trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='availability/bulk')
    @method_decorator(ratelimit(key='user', rate='10/h', method='POST'))
    def bulk_add_availability(self, request, pk=None):
        """Bulk add availability blocks"""
        trip = self.get_object()
        blocks_data = request.data.get('blocks', [])

        created_blocks = []
        errors = []

        for block_data in blocks_data:
            serializer = AvailabilityBlockSerializer(data=block_data, context={'trip': trip})
            if serializer.is_valid():
                block = serializer.save(trip=trip)
                created_blocks.append(block)
            else:
                errors.append({
                    'block': block_data,
                    'errors': serializer.errors
                })

        return Response({
            'created': len(created_blocks),
            'failed': len(errors),
            'availability': AvailabilityBlockSerializer(created_blocks, many=True).data,
            'errors': errors if errors else None
        }, status=status.HTTP_201_CREATED if created_blocks else status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# AVAILABILITY BLOCK VIEWSET
# ==============================================================================

class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(trip__user=self.request.user).select_related('trip')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self, 'trip'):
            context['trip'] = self.trip
        return context


# ==============================================================================
# MAP DESTINATIONS ENDPOINT
# ==============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def map_destinations(request):
    """
    Get all destinations with active trips for the map view.

    Query Parameters:
    - start_date (optional): Filter trips starting after this date (YYYY-MM-DD)
    - end_date (optional): Filter trips ending before this date (YYYY-MM-DD)
    - disciplines (optional): Comma-separated list (e.g., "sport,trad,bouldering")

    Returns:
    {
        "destinations": [
            {
                "slug": "red-river-gorge",
                "name": "Red River Gorge",
                "location": "Kentucky, USA",
                "lat": 37.7833,
                "lng": -83.6833,
                "active_trip_count": 12,
                "active_user_count": 15,
                "disciplines": ["sport", "trad"],
                "date_range": {
                    "earliest_arrival": "2026-03-15",
                    "latest_departure": "2026-04-10"
                }
            }
        ]
    }
    """
    # Parse query parameters
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    disciplines_str = request.query_params.get('disciplines')

    # Build queryset - start with active trips only
    trips_queryset = Trip.objects.filter(is_active=True).select_related('destination', 'user')

    # Filter by date range if provided
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            trips_queryset = trips_queryset.filter(start_date__gte=start_date)
        except ValueError:
            return Response(
                {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            trips_queryset = trips_queryset.filter(end_date__lte=end_date)
        except ValueError:
            return Response(
                {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Filter by disciplines if provided
    if disciplines_str:
        disciplines = [d.strip() for d in disciplines_str.split(',')]
        # Filter trips that have at least one matching discipline
        from django.contrib.postgres.fields import ArrayField
        from django.db.models import Q

        discipline_query = Q()
        for discipline in disciplines:
            discipline_query |= Q(preferred_disciplines__contains=[discipline])

        trips_queryset = trips_queryset.filter(discipline_query)

    # Aggregate trips by destination
    destination_aggregates = trips_queryset.values('destination').annotate(
        trip_count=Count('id', distinct=True),
        user_count=Count('user', distinct=True),
        earliest_arrival=Min('start_date'),
        latest_departure=Max('end_date')
    )

    # Build destination data
    destinations_data = []

    for agg in destination_aggregates:
        destination_slug = agg['destination']

        try:
            destination = Destination.objects.get(slug=destination_slug)
        except Destination.DoesNotExist:
            continue

        # Collect unique disciplines across all trips for this destination
        destination_trips = trips_queryset.filter(destination=destination)
        all_disciplines = set()

        for trip in destination_trips:
            if trip.preferred_disciplines:
                all_disciplines.update(trip.preferred_disciplines)

        destinations_data.append({
            'slug': destination.slug,
            'name': destination.name,
            'location': f"{destination.name}, {destination.country}",
            'lat': str(destination.lat),
            'lng': str(destination.lng),
            'active_trip_count': agg['trip_count'],
            'active_user_count': agg['user_count'],
            'disciplines': sorted(list(all_disciplines)),
            'date_range': {
                'earliest_arrival': agg['earliest_arrival'].isoformat() if agg['earliest_arrival'] else None,
                'latest_departure': agg['latest_departure'].isoformat() if agg['latest_departure'] else None
            }
        })

    return Response({
        'destinations': destinations_data
    })


# ==============================================================================
# DESTINATION AUTOCOMPLETE ENDPOINT
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def autocomplete_destinations(request):
    """
    Search destinations for autocomplete.

    Searches by name, country, or location hierarchy and returns a limited set
    of results ordered by popularity (using OpenBeta data when available) and name.

    Query Parameters:
    - q (required): Search query (minimum 2 characters)
    - limit (optional): Maximum number of results (default: 10, max: 50)

    Returns:
    [
        {
            "slug": "red-river-gorge",
            "name": "Red River Gorge, KY",
            "country": "USA",
            "lat": "37.783300",
            "lng": "-83.683300",
            "primary_disciplines": ["sport", "trad"],
            "mp_star_rating": "4.20",  # May be null for areas without OpenBeta star rating data
            "location_hierarchy": ["USA", "Kentucky", "Red River Gorge"]
        },
        ...
    ]
    """
    query = request.GET.get('q', '').strip()
    limit = request.GET.get('limit', '10')

    # Validate query length
    if len(query) < 2:
        return Response(
            {'error': 'Query must be at least 2 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse and validate limit
    try:
        limit = int(limit)
        if limit < 1 or limit > 50:
            limit = 10
    except ValueError:
        limit = 10

    # Build search query
    # Search by name, country, or any item in location_hierarchy
    # Order by star rating (nulls last) then by name
    from django.db.models import F
    from django.db.models.functions import Coalesce

    destinations = Destination.objects.filter(
        Q(name__icontains=query) |
        Q(country__icontains=query) |
        Q(location_hierarchy__icontains=query)
    ).order_by(
        # Order by star rating descending (nulls last), then by name
        F('mp_star_rating').desc(nulls_last=True),
        'name'
    )[:limit]

    serializer = DestinationAutocompleteSerializer(destinations, many=True)
    return Response(serializer.data)
