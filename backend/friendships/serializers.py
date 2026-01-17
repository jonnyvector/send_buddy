from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Friendship
from users.models import User
from users.serializers import PublicUserSerializer


class FriendshipSerializer(serializers.ModelSerializer):
    """For listing friendships with full details"""
    requester = PublicUserSerializer(read_only=True)
    addressee = PublicUserSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = [
            'id', 'requester', 'addressee', 'status',
            'created_at', 'accepted_at', 'connection_source',
            'is_expired', 'days_until_expiry'
        ]
        read_only_fields = ['id', 'created_at', 'accepted_at']

    def get_is_expired(self, obj):
        """Check if pending request has expired"""
        if obj.status != 'pending':
            return False

        from .services import FriendshipService
        expiry_date = obj.created_at + timedelta(days=FriendshipService.REQUEST_EXPIRY_DAYS)
        return timezone.now() > expiry_date

    def get_days_until_expiry(self, obj):
        """Calculate days until request expires (for pending requests)"""
        if obj.status != 'pending':
            return None

        from .services import FriendshipService
        expiry_date = obj.created_at + timedelta(days=FriendshipService.REQUEST_EXPIRY_DAYS)
        remaining = (expiry_date - timezone.now()).days
        return max(0, remaining)


class FriendshipCreateSerializer(serializers.Serializer):
    """For creating friend requests"""
    addressee_id = serializers.UUIDField()

    def validate_addressee_id(self, value):
        """Validate addressee exists and is visible to requester"""
        requester = self.context['request'].user

        try:
            addressee = User.objects.visible_to(requester).get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found or not available")

        # Additional validation will be done in the service
        return value

    def create(self, validated_data):
        """Create friendship through service"""
        from .services import FriendshipService

        requester = self.context['request'].user
        addressee = User.objects.get(id=validated_data['addressee_id'])

        try:
            friendship = FriendshipService.send_friend_request(requester, addressee)
            return friendship
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class FriendSerializer(serializers.ModelSerializer):
    """For listing friends (just the user info)"""
    # Custom fields to include additional friend information
    friendship_id = serializers.SerializerMethodField()
    friendship_since = serializers.SerializerMethodField()
    mutual_friends_count = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name', 'avatar_url',
            'home_location', 'bio',
            'friendship_id', 'friendship_since', 'mutual_friends_count'
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        """Get the avatar URL if available"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_friendship_id(self, obj):
        """Get the friendship ID for this friend"""
        current_user = self.context.get('request').user

        friendship = Friendship.objects.filter(
            models.Q(requester=current_user, addressee=obj, status='accepted') |
            models.Q(requester=obj, addressee=current_user, status='accepted')
        ).first()

        return str(friendship.id) if friendship else None

    def get_friendship_since(self, obj):
        """Get when the friendship was accepted"""
        current_user = self.context.get('request').user

        friendship = Friendship.objects.filter(
            models.Q(requester=current_user, addressee=obj, status='accepted') |
            models.Q(requester=obj, addressee=current_user, status='accepted')
        ).first()

        return friendship.accepted_at if friendship else None

    def get_mutual_friends_count(self, obj):
        """Count mutual friends between current user and this friend"""
        current_user = self.context.get('request').user

        # Get current user's friends
        current_user_friends = set(Friendship.get_friends(current_user).values_list('id', flat=True))

        # Get this friend's friends
        friend_friends = set(Friendship.get_friends(obj).values_list('id', flat=True))

        # Calculate intersection, excluding both users
        mutual = current_user_friends & friend_friends
        mutual.discard(current_user.id)
        mutual.discard(obj.id)

        return len(mutual)


class FriendSuggestionSerializer(serializers.Serializer):
    """For friend suggestions with reason"""
    user = PublicUserSerializer()
    reason = serializers.CharField()
    mutual_friends_count = serializers.IntegerField()

    class Meta:
        fields = ['user', 'reason', 'mutual_friends_count']


class FriendshipStatusSerializer(serializers.Serializer):
    """For checking friendship status between users"""
    user_id = serializers.UUIDField()
    is_friend = serializers.BooleanField()
    is_pending_sent = serializers.BooleanField()
    is_pending_received = serializers.BooleanField()
    is_blocked = serializers.BooleanField()
    friendship_id = serializers.UUIDField(allow_null=True)


# Import models.Q for the FriendSerializer
from django.db import models