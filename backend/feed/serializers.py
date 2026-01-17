from rest_framework import serializers
from trips.serializers import TripListSerializer
from overlaps.serializers import TripOverlapSerializer
from users.serializers import UserMinimalSerializer


class FeedItemSerializer(serializers.Serializer):
    """
    Polymorphic feed item serializer.
    Handles different types of feed items (trips, overlaps, group activities).
    """

    type = serializers.CharField(
        help_text="Type of feed item: 'friend_trip', 'friend_trip_completed', 'looking_for_partners', 'overlap', 'group_trip'"
    )
    timestamp = serializers.DateTimeField(
        help_text="When this activity occurred"
    )
    action_text = serializers.CharField(
        help_text="Human-readable description of the activity"
    )

    # Nested data - one or more of these will be populated depending on type
    trip = TripListSerializer(required=False, allow_null=True)
    overlap = TripOverlapSerializer(required=False, allow_null=True)
    user = UserMinimalSerializer(
        required=False,
        allow_null=True,
        help_text="The user who performed this action (trip owner, friend, etc.)"
    )
    friend = UserMinimalSerializer(
        required=False,
        allow_null=True,
        help_text="For overlaps: the other user in the overlap"
    )

    # Internal field used for sorting (not exposed to client)
    priority = serializers.IntegerField(read_only=True)


class FeedSerializer(serializers.Serializer):
    """Full feed response with pagination metadata"""

    items = FeedItemSerializer(many=True)
    has_more = serializers.BooleanField(
        help_text="Whether there are more items available"
    )
    total_count = serializers.IntegerField(
        help_text="Total number of feed items available"
    )
