from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import FeedService
from .serializers import FeedSerializer


class FeedViewSet(viewsets.ViewSet):
    """
    ViewSet for social feed functionality.

    Provides:
    - Main feed (GET /api/feed/)
    - Network trips only (GET /api/feed/network-trips/)
    - Overlaps only (GET /api/feed/overlaps/)
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/feed/ - Main social feed

        Returns combined feed of friends' trips, overlaps, and group activities.

        Query Parameters:
        - limit: Number of items to return (default: 50)
        - offset: Number of items to skip (default: 0)

        Response:
        {
            "items": [
                {
                    "type": "friend_trip",
                    "timestamp": "2026-01-15T10:30:00Z",
                    "action_text": "John posted a trip to Red River Gorge",
                    "trip": {...},
                    "user": {...}
                },
                {
                    "type": "overlap",
                    "timestamp": "2026-01-14T08:00:00Z",
                    "action_text": "You and Sarah will both be in Yosemite (5 days overlap)",
                    "overlap": {...},
                    "friend": {...}
                }
            ],
            "has_more": true,
            "total_count": 127
        }
        """
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        # Validate pagination parameters
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if offset < 0:
            return Response(
                {'error': 'Offset must be non-negative'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            feed_data = FeedService.get_feed(request.user, limit=limit, offset=offset)
            serializer = FeedSerializer(feed_data)
            return Response(serializer.data)
        except Exception as e:
            # Log the error in production
            return Response(
                {'error': 'Failed to generate feed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def network_trips(self, request):
        """
        GET /api/feed/network-trips/ - Just friends' trips

        Returns only trip activities from friends (no overlaps or groups).

        Query Parameters:
        - limit: Number of items to return (default: 50)
        - offset: Number of items to skip (default: 0)

        Response: Same format as main feed
        """
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        # Validate pagination parameters
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if offset < 0:
            return Response(
                {'error': 'Offset must be non-negative'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            feed_data = FeedService.get_network_trips(
                request.user, limit=limit, offset=offset
            )
            serializer = FeedSerializer(feed_data)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': 'Failed to generate network trips feed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def overlaps(self, request):
        """
        GET /api/feed/overlaps/ - Just trip overlaps

        Returns only overlap activities (no friend trips or groups).

        Query Parameters:
        - limit: Number of items to return (default: 50)
        - offset: Number of items to skip (default: 0)

        Response: Same format as main feed
        """
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        # Validate pagination parameters
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if offset < 0:
            return Response(
                {'error': 'Offset must be non-negative'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            feed_data = FeedService.get_overlaps_feed(
                request.user, limit=limit, offset=offset
            )
            serializer = FeedSerializer(feed_data)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': 'Failed to generate overlaps feed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
