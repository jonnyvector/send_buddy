from rest_framework import serializers
from .models import Destination, Crag, Trip, AvailabilityBlock
from users.serializers import UserMinimalSerializer
from datetime import date


# ==============================================================================
# DESTINATION & CRAG SERIALIZERS
# ==============================================================================

class DestinationSerializer(serializers.ModelSerializer):
    """Read-only serializer for destinations"""

    class Meta:
        model = Destination
        fields = [
            'slug', 'name', 'country', 'lat', 'lng',
            'description', 'image_url', 'primary_disciplines', 'season'
        ]
        read_only_fields = fields


class DestinationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for destination lists/autocomplete"""

    class Meta:
        model = Destination
        fields = ['slug', 'name', 'country', 'lat', 'lng', 'primary_disciplines', 'season']
        read_only_fields = fields


class DestinationAutocompleteSerializer(serializers.ModelSerializer):
    """Lightweight serializer for autocomplete with Mountain Project data"""

    class Meta:
        model = Destination
        fields = [
            'slug', 'name', 'country',
            'lat', 'lng', 'primary_disciplines',
            'mp_star_rating', 'location_hierarchy'
        ]
        read_only_fields = fields


class CragSerializer(serializers.ModelSerializer):
    """Read-only serializer for crags"""

    class Meta:
        model = Crag
        fields = ['id', 'name', 'disciplines', 'route_count', 'approach_time', 'description']
        read_only_fields = fields


# ==============================================================================
# TRIP & AVAILABILITY SERIALIZERS
# ==============================================================================

class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'trip', 'date', 'time_block', 'notes']
        read_only_fields = ['id', 'trip']

    def validate_date(self, value):
        # Validate date is within trip date range
        trip = self.context.get('trip')
        if trip and not (trip.start_date <= value <= trip.end_date):
            raise serializers.ValidationError(
                f"Date must be between {trip.start_date} and {trip.end_date}"
            )
        return value

    def validate(self, data):
        # Check for unique constraint (trip, date, time_block) with better error message
        trip = self.context.get('trip')
        if trip:
            existing = AvailabilityBlock.objects.filter(
                trip=trip,
                date=data['date'],
                time_block=data['time_block']
            ).exists()

            if existing:
                raise serializers.ValidationError({
                    'time_block': f"You already have a {data['time_block']} block for {data['date']}"
                })

        return data


class TripMinimalSerializer(serializers.ModelSerializer):
    """Minimal trip serializer for nested representations"""

    destination_name = serializers.CharField(source='destination.name', read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'destination_name',
            'start_date',
            'end_date',
            'visibility_status',
        ]
        read_only_fields = fields


class TripSerializer(serializers.ModelSerializer):
    """Full trip serializer with nested destination and crags"""

    # Nested read-only fields
    destination = DestinationSerializer(read_only=True)
    preferred_crags = CragSerializer(many=True, read_only=True)
    availability = AvailabilityBlockSerializer(many=True, read_only=True)
    user = UserMinimalSerializer(read_only=True)
    organizer = UserMinimalSerializer(read_only=True)
    invited_users = UserMinimalSerializer(many=True, read_only=True)

    # Write-only fields for creation/update
    destination_slug = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Destination.objects.all(),
        source='destination',
        write_only=True
    )
    preferred_crag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Crag.objects.all(),
        source='preferred_crags',
        write_only=True,
        required=False
    )
    invited_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Trip
        fields = [
            'id', 'user',
            # Read fields
            'destination', 'preferred_crags', 'availability',
            'organizer', 'invited_users',
            # Write fields
            'destination_slug', 'preferred_crag_ids', 'invited_user_ids',
            # Common fields
            'custom_crag_notes', 'start_date', 'end_date',
            'preferred_disciplines', 'grade_system', 'min_grade', 'max_grade',
            'notes', 'is_active',
            # New social utility fields
            'visibility_status', 'trip_status', 'is_group_trip',
            'notes_public', 'notes_private',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'trip_status',
            'destination', 'preferred_crags', 'availability',
            'organizer', 'invited_users'
        ]

    def validate(self, data):
        # Validate date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    'end_date': "End date must be on or after start date"
                })

            if start_date < date.today():
                raise serializers.ValidationError({
                    'start_date': "Start date cannot be in the past"
                })

        # Check for overlapping trips at the same destination
        destination = data.get('destination')
        user = self.context['request'].user

        if destination and start_date and end_date:
            overlapping = Trip.objects.filter(
                user=user,
                destination=destination,
                is_active=True,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if overlapping.exists():
                raise serializers.ValidationError({
                    'start_date': f"You already have an overlapping trip to {destination.name} during these dates"
                })

        # Validate preferred_crags belong to destination
        preferred_crags = data.get('preferred_crags', [])

        if destination and preferred_crags:
            for crag in preferred_crags:
                if crag.destination != destination:
                    raise serializers.ValidationError({
                        'preferred_crag_ids': f"Crag '{crag.name}' does not belong to {destination.name}"
                    })

        # Validate invited_user_ids exist
        invited_user_ids = data.get('invited_user_ids', [])
        if invited_user_ids:
            from users.models import User
            valid_users = User.objects.filter(id__in=invited_user_ids)
            if valid_users.count() != len(invited_user_ids):
                raise serializers.ValidationError({
                    'invited_user_ids': "One or more user IDs are invalid"
                })

        return data

    def create(self, validated_data):
        # Extract invited_user_ids before creating the trip
        invited_user_ids = validated_data.pop('invited_user_ids', [])

        # Create the trip
        trip = super().create(validated_data)

        # Set organizer to the trip owner if it's a group trip
        if trip.is_group_trip and not trip.organizer:
            trip.organizer = trip.user
            trip.save(update_fields=['organizer'])

        # Add invited users
        if invited_user_ids:
            from users.models import User
            invited_users = User.objects.filter(id__in=invited_user_ids)
            trip.invited_users.set(invited_users)

        return trip


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for trip lists"""

    destination = DestinationListSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    organizer = UserMinimalSerializer(read_only=True)
    availability_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'user', 'organizer', 'destination', 'start_date', 'end_date',
            'preferred_disciplines', 'grade_system', 'min_grade', 'max_grade',
            'is_active', 'notes', 'availability_count',
            'visibility_status', 'trip_status', 'is_group_trip', 'notes_public'
        ]
        read_only_fields = fields

    def get_availability_count(self, obj):
        return obj.availability.count()


class TripPublicSerializer(serializers.ModelSerializer):
    """Public serializer for 'Looking for Partners' listings - excludes private notes"""

    destination = DestinationListSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    organizer = UserMinimalSerializer(read_only=True)
    preferred_crags = CragSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id', 'user', 'organizer', 'destination', 'preferred_crags',
            'start_date', 'end_date',
            'preferred_disciplines', 'grade_system', 'min_grade', 'max_grade',
            'notes_public', 'is_group_trip', 'trip_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class TripUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating trips (allows editing dates, disciplines, grades, etc.)"""

    preferred_crag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Crag.objects.all(),
        source='preferred_crags',
        required=False
    )
    invited_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Trip
        fields = [
            'start_date', 'end_date',
            'custom_crag_notes', 'preferred_disciplines',
            'grade_system', 'min_grade', 'max_grade',
            'notes', 'is_active', 'preferred_crag_ids',
            'visibility_status', 'is_group_trip', 'notes_public', 'notes_private',
            'invited_user_ids'
        ]

    def validate(self, data):
        """Validate that end_date is after start_date and no overlapping trips"""
        start_date = data.get('start_date', self.instance.start_date if self.instance else None)
        end_date = data.get('end_date', self.instance.end_date if self.instance else None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': "End date must be on or after start date"
            })

        # Check for overlapping trips when dates are being changed
        if self.instance and (data.get('start_date') or data.get('end_date')):
            overlapping = Trip.objects.filter(
                user=self.instance.user,
                destination=self.instance.destination,
                is_active=True,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError({
                    'start_date': f"You already have an overlapping trip to {self.instance.destination.name} during these dates"
                })

        # Validate invited_user_ids exist
        invited_user_ids = data.get('invited_user_ids', [])
        if invited_user_ids:
            from users.models import User
            valid_users = User.objects.filter(id__in=invited_user_ids)
            if valid_users.count() != len(invited_user_ids):
                raise serializers.ValidationError({
                    'invited_user_ids': "One or more user IDs are invalid"
                })

        return data

    def validate_preferred_crag_ids(self, value):
        # Ensure crags belong to the trip's destination
        trip = self.instance
        if trip:
            for crag in value:
                if crag.destination != trip.destination:
                    raise serializers.ValidationError(
                        f"Crag '{crag.name}' does not belong to {trip.destination.name}"
                    )
        return value

    def update(self, instance, validated_data):
        # Extract invited_user_ids before updating
        invited_user_ids = validated_data.pop('invited_user_ids', None)

        # Update the trip
        trip = super().update(instance, validated_data)

        # Update invited users if provided
        if invited_user_ids is not None:
            from users.models import User
            invited_users = User.objects.filter(id__in=invited_user_ids)
            trip.invited_users.set(invited_users)

        return trip
