from rest_framework import serializers
from users.serializers import DisciplineProfileSerializer
from trips.serializers import DestinationListSerializer


class MatchTripSerializer(serializers.Serializer):
    """Lightweight trip serializer for match responses"""
    id = serializers.UUIDField(read_only=True)
    destination = DestinationListSerializer(read_only=True)
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)
    preferred_disciplines = serializers.ListField(read_only=True)


class MatchUserSerializer(serializers.Serializer):
    """User serializer for match responses"""
    id = serializers.UUIDField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    bio = serializers.CharField(read_only=True)
    home_location = serializers.CharField(read_only=True)
    risk_tolerance = serializers.CharField(read_only=True)
    disciplines = DisciplineProfileSerializer(many=True, read_only=True)
    experience_tags = serializers.SerializerMethodField()

    def get_experience_tags(self, obj):
        return [tag.tag.slug for tag in obj.experience_tags.all()]


class OverlapDatesSerializer(serializers.Serializer):
    """Date overlap information"""
    start = serializers.DateField()
    end = serializers.DateField()
    days = serializers.IntegerField()


class MatchSerializer(serializers.Serializer):
    """Single match result"""
    matched_user = MatchUserSerializer(read_only=True, source='user')
    trip = MatchTripSerializer(read_only=True)
    score = serializers.IntegerField(read_only=True, source='match_score')
    common_disciplines = serializers.SerializerMethodField()
    skill_match = serializers.SerializerMethodField()
    availability_overlap = serializers.SerializerMethodField()
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    overlap_dates = OverlapDatesSerializer(read_only=True)

    def get_common_disciplines(self, obj):
        """Extract common disciplines from reasons or trip data"""
        # Get from trip's preferred_disciplines if available
        if obj.get('trip'):
            return obj['trip'].preferred_disciplines or []
        return []

    def get_skill_match(self, obj):
        """Extract skill match description from reasons"""
        for reason in obj.get('reasons', []):
            if 'grade' in reason.lower() or 'skill' in reason.lower():
                return reason
        return ''

    def get_availability_overlap(self, obj):
        """Get number of overlapping days"""
        overlap_dates = obj.get('overlap_dates', {})
        return overlap_dates.get('days', 0)


class MatchListSerializer(serializers.Serializer):
    """Match list response"""
    trip = MatchTripSerializer(read_only=True)
    matches = MatchSerializer(many=True, read_only=True)


class AvailabilityOverlapSerializer(serializers.Serializer):
    """Availability overlap for match detail"""
    date = serializers.DateField()
    time_blocks = serializers.ListField(child=serializers.CharField())


class GradeCompatibilitySerializer(serializers.Serializer):
    """Grade compatibility info for a discipline"""
    overlap_range = serializers.CharField()
    compatibility = serializers.CharField()  # "high", "medium", "low"


class MatchDetailSerializer(serializers.Serializer):
    """Detailed match response"""
    matched_user = MatchUserSerializer(read_only=True, source='user')
    trip = MatchTripSerializer(read_only=True)
    score = serializers.IntegerField(read_only=True, source='match_score')
    common_disciplines = serializers.SerializerMethodField()
    skill_match = serializers.SerializerMethodField()
    availability_overlap = serializers.SerializerMethodField()
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    overlap_dates = OverlapDatesSerializer(read_only=True)
    availability_blocks = AvailabilityOverlapSerializer(many=True, read_only=True, source='availability_overlap')
    shared_disciplines = serializers.ListField(child=serializers.CharField(), read_only=True)
    grade_compatibility = serializers.DictField(child=GradeCompatibilitySerializer(), read_only=True)

    def get_common_disciplines(self, obj):
        """Extract common disciplines from reasons or trip data"""
        if obj.get('trip'):
            return obj['trip'].preferred_disciplines or []
        return []

    def get_skill_match(self, obj):
        """Extract skill match description from reasons"""
        for reason in obj.get('reasons', []):
            if 'grade' in reason.lower() or 'skill' in reason.lower():
                return reason
        return ''

    def get_availability_overlap(self, obj):
        """Get number of overlapping days"""
        overlap_dates = obj.get('overlap_dates', {})
        return overlap_dates.get('days', 0)
