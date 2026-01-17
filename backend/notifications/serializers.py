from rest_framework import serializers
from .models import Notification
from users.models import User


class NotificationRecipientSerializer(serializers.ModelSerializer):
    """Minimal user serializer for notification recipient"""

    class Meta:
        model = User
        fields = ['id', 'display_name', 'avatar']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Complete notification serializer with nested user information.
    Includes related object details based on notification type.
    """

    recipient = NotificationRecipientSerializer(read_only=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    # Related object data (will be populated dynamically)
    related_user = serializers.SerializerMethodField()
    related_trip = serializers.SerializerMethodField()
    related_friendship = serializers.SerializerMethodField()
    related_overlap = serializers.SerializerMethodField()
    related_group = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'notification_type',
            'notification_type_display',
            'priority',
            'priority_display',
            'title',
            'message',
            'action_url',
            'is_read',
            'popup_shown',
            'created_at',
            'read_at',
            'related_user',
            'related_trip',
            'related_friendship',
            'related_overlap',
            'related_group',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'read_at',
        ]

    def get_related_user(self, obj):
        """
        Get user information from the related object.
        For new_match notifications, this is the matched user.
        For connection notifications, this is the other user in the connection.
        """
        try:
            content_obj = obj.content_object
            if not content_obj:
                return None

            # For Trip objects (new_match), we need to get the trip owner
            if hasattr(content_obj, 'user'):
                user = content_obj.user
                return {
                    'id': str(user.id),
                    'display_name': user.display_name,
                    'avatar': user.avatar.url if user.avatar else None,
                }

            # For Connection objects (future implementation)
            # Will need to determine which user to show based on requester/recipient

            return None
        except Exception:
            return None

    def get_related_trip(self, obj):
        """
        Get trip information from the related object.
        For new_match notifications, this includes trip details.
        """
        try:
            content_obj = obj.content_object
            if not content_obj:
                return None

            # For Trip objects
            from trips.models import Trip
            if isinstance(content_obj, Trip):
                return {
                    'id': str(content_obj.id),
                    'destination': content_obj.destination.name,
                    'start_date': content_obj.start_date.isoformat(),
                    'end_date': content_obj.end_date.isoformat(),
                }

            return None
        except Exception:
            return None

    def get_related_friendship(self, obj):
        """
        Get friendship information from the related object.
        For friend_request and friend_accepted notifications.
        """
        try:
            content_obj = obj.content_object
            if not content_obj:
                return None

            # For Friendship objects
            from friendships.models import Friendship
            if isinstance(content_obj, Friendship):
                # Determine which user to show (not the recipient)
                other_user = (
                    content_obj.requester
                    if content_obj.addressee.id == obj.recipient.id
                    else content_obj.addressee
                )
                return {
                    'id': str(content_obj.id),
                    'requester_id': str(content_obj.requester.id),
                    'addressee_id': str(content_obj.addressee.id),
                    'status': content_obj.status,
                    'other_user': {
                        'id': str(other_user.id),
                        'display_name': other_user.display_name,
                        'avatar': other_user.avatar.url if other_user.avatar else None,
                    }
                }

            return None
        except Exception:
            return None

    def get_related_overlap(self, obj):
        """
        Get overlap information from the related object.
        For trip_overlap_detected and friend_in_home_crag notifications.
        """
        try:
            content_obj = obj.content_object
            if not content_obj:
                return None

            # For TripOverlap objects
            from overlaps.models import TripOverlap
            if isinstance(content_obj, TripOverlap):
                # Determine which user to show (not the recipient)
                other_user = (
                    content_obj.user1
                    if content_obj.user2.id == obj.recipient.id
                    else content_obj.user2
                )
                return {
                    'id': str(content_obj.id),
                    'destination': content_obj.overlap_destination.name,
                    'start_date': content_obj.overlap_start_date.isoformat(),
                    'end_date': content_obj.overlap_end_date.isoformat(),
                    'overlap_days': content_obj.overlap_days,
                    'overlap_score': content_obj.overlap_score,
                    'other_user': {
                        'id': str(other_user.id),
                        'display_name': other_user.display_name,
                        'avatar': other_user.avatar.url if other_user.avatar else None,
                    }
                }

            return None
        except Exception:
            return None

    def get_related_group(self, obj):
        """
        Get group information from the related object.
        For group_invite, group_trip_posted, and group_trip_updated notifications.
        """
        try:
            content_obj = obj.content_object
            if not content_obj:
                return None

            # For ClimbingGroup objects
            from groups.models import ClimbingGroup
            if isinstance(content_obj, ClimbingGroup):
                return {
                    'id': str(content_obj.id),
                    'name': content_obj.name,
                    'description': content_obj.description,
                    'member_count': content_obj.members.count(),
                }

            # For GroupMembership objects (invitations)
            from groups.models import GroupMembership
            if isinstance(content_obj, GroupMembership):
                return {
                    'id': str(content_obj.id),
                    'group': {
                        'id': str(content_obj.group.id),
                        'name': content_obj.group.name,
                        'description': content_obj.group.description,
                    },
                    'role': content_obj.role,
                }

            return None
        except Exception:
            return None


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text='List of notification IDs to mark as read. If empty, marks all as read.'
    )
