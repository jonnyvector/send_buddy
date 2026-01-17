from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import TripOverlap
from trips.serializers import TripMinimalSerializer, DestinationSerializer
from users.serializers import UserMinimalSerializer

User = get_user_model()


class TripOverlapSerializer(serializers.ModelSerializer):
    """
    Basic serializer for trip overlaps.
    Shows the other user and trip from the perspective of the request user.
    """
    friend = serializers.SerializerMethodField()
    friend_trip = serializers.SerializerMethodField()
    my_trip = serializers.SerializerMethodField()
    destination_name = serializers.CharField(source='overlap_destination.name', read_only=True)
    is_dismissed = serializers.SerializerMethodField()

    class Meta:
        model = TripOverlap
        fields = [
            'id',
            'friend',
            'friend_trip',
            'my_trip',
            'destination_name',
            'overlap_start_date',
            'overlap_end_date',
            'overlap_days',
            'overlap_score',
            'is_dismissed',
            'detected_at'
        ]
        read_only_fields = fields

    def get_friend(self, obj):
        """Return the other user (not the request user)."""
        request = self.context.get('request')
        if not request or not request.user:
            return None

        if obj.user1 == request.user:
            return UserMinimalSerializer(obj.user2).data
        return UserMinimalSerializer(obj.user1).data

    def get_friend_trip(self, obj):
        """Return the other user's trip."""
        request = self.context.get('request')
        if not request or not request.user:
            return None

        if obj.user1 == request.user:
            return TripMinimalSerializer(obj.trip2, context=self.context).data
        return TripMinimalSerializer(obj.trip1, context=self.context).data

    def get_my_trip(self, obj):
        """Return the current user's trip."""
        request = self.context.get('request')
        if not request or not request.user:
            return None

        if obj.user1 == request.user:
            return TripMinimalSerializer(obj.trip1, context=self.context).data
        return TripMinimalSerializer(obj.trip2, context=self.context).data

    def get_is_dismissed(self, obj):
        """Check if the current user has dismissed this overlap."""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        if obj.user1 == request.user:
            return obj.user1_dismissed
        elif obj.user2 == request.user:
            return obj.user2_dismissed
        return False


class TripOverlapDetailSerializer(TripOverlapSerializer):
    """
    Detailed serializer for trip overlaps with full trip information.
    """
    overlap_destination = DestinationSerializer(read_only=True)
    connection_created = serializers.BooleanField(read_only=True)
    notification_sent = serializers.BooleanField(read_only=True)

    class Meta(TripOverlapSerializer.Meta):
        fields = TripOverlapSerializer.Meta.fields + [
            'overlap_destination',
            'connection_created',
            'notification_sent',
            'notification_sent_at'
        ]


class TripOverlapCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating trip overlaps (typically used by admin/system).
    """

    class Meta:
        model = TripOverlap
        fields = [
            'user1',
            'user2',
            'trip1',
            'trip2',
            'overlap_destination',
            'overlap_start_date',
            'overlap_end_date',
            'overlap_days',
            'overlap_score'
        ]

    def validate(self, attrs):
        """Validate the overlap creation."""
        user1 = attrs.get('user1')
        user2 = attrs.get('user2')
        trip1 = attrs.get('trip1')
        trip2 = attrs.get('trip2')

        # Ensure users are different
        if user1 == user2:
            raise serializers.ValidationError("Cannot create overlap between same user")

        # Ensure trips belong to the correct users
        if trip1.user != user1:
            raise serializers.ValidationError("Trip1 must belong to user1")
        if trip2.user != user2:
            raise serializers.ValidationError("Trip2 must belong to user2")

        # Ensure trips are at the same destination
        if trip1.destination != trip2.destination:
            raise serializers.ValidationError("Trips must be at the same destination")

        # Check for existing overlap
        existing = TripOverlap.objects.filter(
            Q(trip1=trip1, trip2=trip2) |
            Q(trip1=trip2, trip2=trip1)
        ).exists()

        if existing:
            raise serializers.ValidationError("Overlap already exists for these trips")

        # Ensure dates actually overlap
        overlap_start = max(trip1.start_date, trip2.start_date)
        overlap_end = min(trip1.end_date, trip2.end_date)

        if overlap_start > overlap_end:
            raise serializers.ValidationError("Trips do not have overlapping dates")

        return attrs


class DismissOverlapSerializer(serializers.Serializer):
    """
    Serializer for dismissing an overlap.
    """
    overlap_id = serializers.UUIDField(required=True)

    def validate_overlap_id(self, value):
        """Ensure the overlap exists and user is part of it."""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")

        try:
            overlap = TripOverlap.objects.get(id=value)
        except TripOverlap.DoesNotExist:
            raise serializers.ValidationError("Overlap not found")

        # Check if user is part of this overlap
        if overlap.user1 != request.user and overlap.user2 != request.user:
            raise serializers.ValidationError("You are not part of this overlap")

        return value
