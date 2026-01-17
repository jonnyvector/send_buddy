from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import Notification
from users.models import User
from trips.models import Trip
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class for creating and managing notifications.
    Centralizes notification creation logic for consistency.
    """

    @staticmethod
    def create_new_match_notification(recipient, matched_user, trip, match_score):
        """
        Create a notification when a new match is found.

        Args:
            recipient (User): User who will receive the notification
            matched_user (User): The user who was matched
            trip (Trip): The trip that created the match
            match_score (int): Match score (0-100)

        Returns:
            Notification: The created notification object
        """
        try:
            # Create notification linked to the trip
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type='new_match',
                priority='critical',  # Show popup for matches
                content_type=ContentType.objects.get_for_model(Trip),
                object_id=trip.id,
                title=f"New Match: {matched_user.display_name}",
                message=(
                    f"You've been matched with {matched_user.display_name} "
                    f"for your trip to {trip.destination.name}! "
                    f"Match score: {match_score}%"
                ),
                action_url=f"/users/{matched_user.id}"
            )

            logger.info(
                f"Created new_match notification for user {recipient.id} "
                f"matching {matched_user.id} on trip {trip.id}"
            )

            return notification

        except Exception as e:
            logger.error(
                f"Failed to create new_match notification: {str(e)}",
                exc_info=True
            )
            return None

    @staticmethod
    def create_connection_request_notification(recipient, connection):
        """
        Create a notification when someone sends a connection request.
        (For Phase 2 - when Connection model is implemented)

        Args:
            recipient (User): User who will receive the notification
            connection (Connection): The connection request object

        Returns:
            Notification: The created notification object
        """
        # Placeholder for Phase 2
        # Will be implemented when Connection model is added
        logger.warning("Connection notifications not yet implemented (Phase 2)")
        return None

    @staticmethod
    def create_connection_status_notification(recipient, connection, status):
        """
        Create a notification when a connection request is accepted/declined.
        (For Phase 2 - when Connection model is implemented)

        Args:
            recipient (User): User who will receive the notification
            connection (Connection): The connection object
            status (str): 'accepted' or 'declined'

        Returns:
            Notification: The created notification object
        """
        # Placeholder for Phase 2
        logger.warning("Connection status notifications not yet implemented (Phase 2)")
        return None

    @staticmethod
    def create_friend_request_notification(requester, addressee):
        """
        Create a notification when someone sends a friend request.

        Args:
            requester (User): User who sent the friend request
            addressee (User): User who will receive the notification

        Returns:
            Notification: The created notification object or None if blocked
        """
        try:
            # Check for bilateral blocking - never send notifications to blocked users
            from users.models import Block
            from django.db.models import Q

            if Block.objects.filter(
                Q(blocker=requester, blocked=addressee) |
                Q(blocker=addressee, blocked=requester)
            ).exists():
                logger.info(
                    f"Skipping friend_request notification - blocking exists between "
                    f"user {requester.id} and {addressee.id}"
                )
                return None

            # Get the friendship object to link to notification
            from friendships.models import Friendship
            friendship = Friendship.objects.filter(
                requester=requester,
                addressee=addressee,
                status='pending'
            ).first()

            if not friendship:
                logger.warning(
                    f"No pending friendship found from {requester.id} to {addressee.id}"
                )
                return None

            notification = Notification.objects.create(
                recipient=addressee,
                notification_type='friend_request',
                priority='high',
                content_type=ContentType.objects.get_for_model(Friendship),
                object_id=friendship.id,
                title=f"{requester.display_name} sent you a friend request",
                message=(
                    f"{requester.display_name} wants to connect with you on Send Buddy!"
                ),
                action_url=f"/friends/requests"
            )

            logger.info(
                f"Created friend_request notification for user {addressee.id} "
                f"from {requester.id}"
            )

            return notification

        except Exception as e:
            logger.error(
                f"Failed to create friend_request notification: {str(e)}",
                exc_info=True
            )
            return None

    @staticmethod
    def create_friend_accepted_notification(friendship):
        """
        Create a notification when a friend request is accepted.

        Args:
            friendship (Friendship): The accepted friendship object

        Returns:
            Notification: The created notification object or None if blocked
        """
        try:
            # Check for bilateral blocking
            from users.models import Block
            from django.db.models import Q

            if Block.objects.filter(
                Q(blocker=friendship.requester, blocked=friendship.addressee) |
                Q(blocker=friendship.addressee, blocked=friendship.requester)
            ).exists():
                logger.info(
                    f"Skipping friend_accepted notification - blocking exists between "
                    f"user {friendship.requester.id} and {friendship.addressee.id}"
                )
                return None

            # Notify the original requester that their request was accepted
            notification = Notification.objects.create(
                recipient=friendship.requester,
                notification_type='friend_accepted',
                priority='high',
                content_type=ContentType.objects.get_for_model(friendship),
                object_id=friendship.id,
                title=f"{friendship.addressee.display_name} accepted your friend request",
                message=(
                    f"You and {friendship.addressee.display_name} are now friends! "
                    f"Start planning your next climbing adventure together."
                ),
                action_url=f"/users/{friendship.addressee.id}"
            )

            logger.info(
                f"Created friend_accepted notification for user {friendship.requester.id} "
                f"about {friendship.addressee.id}"
            )

            return notification

        except Exception as e:
            logger.error(
                f"Failed to create friend_accepted notification: {str(e)}",
                exc_info=True
            )
            return None

    @staticmethod
    def create_friend_trip_notification(recipient, trip):
        """
        Create a notification when a friend posts a new trip.

        Args:
            recipient (User): Friend who will receive the notification
            trip (Trip): The trip that was posted

        Returns:
            Notification: The created notification object or None if blocked
        """
        try:
            # Check for bilateral blocking
            from users.models import Block
            from django.db.models import Q

            if Block.objects.filter(
                Q(blocker=trip.user, blocked=recipient) |
                Q(blocker=recipient, blocked=trip.user)
            ).exists():
                logger.info(
                    f"Skipping friend_trip_posted notification - blocking exists between "
                    f"user {trip.user.id} and {recipient.id}"
                )
                return None

            notification = Notification.objects.create(
                recipient=recipient,
                notification_type='friend_trip_posted',
                priority='medium',
                content_type=ContentType.objects.get_for_model(Trip),
                object_id=trip.id,
                title=f"{trip.user.display_name} posted a new trip",
                message=(
                    f"{trip.user.display_name} is planning a trip to {trip.destination.name} "
                    f"from {trip.start_date.strftime('%b %d')} to {trip.end_date.strftime('%b %d')}"
                ),
                action_url=f"/trips/{trip.id}"
            )

            logger.info(
                f"Created friend_trip_posted notification for user {recipient.id} "
                f"about trip {trip.id}"
            )

            return notification

        except Exception as e:
            logger.error(
                f"Failed to create friend_trip_posted notification: {str(e)}",
                exc_info=True
            )
            return None

    @staticmethod
    def create_overlap_notification(overlap):
        """
        Create notifications for both users when a trip overlap is detected.

        Args:
            overlap (TripOverlap): The detected overlap

        Returns:
            list: Created notification objects
        """
        try:
            # Check for bilateral blocking
            from users.models import Block
            from django.db.models import Q

            if Block.objects.filter(
                Q(blocker=overlap.user1, blocked=overlap.user2) |
                Q(blocker=overlap.user2, blocked=overlap.user1)
            ).exists():
                logger.info(
                    f"Skipping overlap notification - blocking exists between "
                    f"user {overlap.user1.id} and {overlap.user2.id}"
                )
                return []

            from overlaps.models import TripOverlap
            notifications = []

            # Determine priority based on overlap score and friendship
            from friendships.models import Friendship
            are_friends = Friendship.are_friends(overlap.user1, overlap.user2)

            priority = 'critical' if are_friends or overlap.overlap_score >= 80 else 'high'

            # Notification for user1
            notif1 = Notification.objects.create(
                recipient=overlap.user1,
                notification_type='trip_overlap_detected',
                priority=priority,
                content_type=ContentType.objects.get_for_model(TripOverlap),
                object_id=overlap.id,
                title=f"Trip overlap with {overlap.user2.display_name}!",
                message=(
                    f"You and {overlap.user2.display_name} will both be at "
                    f"{overlap.overlap_destination.name} for {overlap.overlap_days} days "
                    f"({overlap.overlap_start_date.strftime('%b %d')} - "
                    f"{overlap.overlap_end_date.strftime('%b %d')})"
                ),
                action_url=f"/overlaps/{overlap.id}"
            )
            notifications.append(notif1)

            # Notification for user2
            notif2 = Notification.objects.create(
                recipient=overlap.user2,
                notification_type='trip_overlap_detected',
                priority=priority,
                content_type=ContentType.objects.get_for_model(TripOverlap),
                object_id=overlap.id,
                title=f"Trip overlap with {overlap.user1.display_name}!",
                message=(
                    f"You and {overlap.user1.display_name} will both be at "
                    f"{overlap.overlap_destination.name} for {overlap.overlap_days} days "
                    f"({overlap.overlap_start_date.strftime('%b %d')} - "
                    f"{overlap.overlap_end_date.strftime('%b %d')})"
                ),
                action_url=f"/overlaps/{overlap.id}"
            )
            notifications.append(notif2)

            logger.info(
                f"Created overlap notifications for users {overlap.user1.id} and {overlap.user2.id}"
            )

            return notifications

        except Exception as e:
            logger.error(
                f"Failed to create overlap notifications: {str(e)}",
                exc_info=True
            )
            return []

    @staticmethod
    def create_group_invite_notification(membership):
        """
        Create a notification when someone is invited to a group.

        Args:
            membership (GroupMembership): The group membership object (role='pending')

        Returns:
            Notification: The created notification object or None if blocked
        """
        try:
            # Check for blocking between invitee and group creator
            from users.models import Block
            from django.db.models import Q

            if Block.objects.filter(
                Q(blocker=membership.group.creator, blocked=membership.user) |
                Q(blocker=membership.user, blocked=membership.group.creator)
            ).exists():
                logger.info(
                    f"Skipping group_invite notification - blocking exists between "
                    f"creator {membership.group.creator.id} and {membership.user.id}"
                )
                return None

            from groups.models import GroupMembership
            notification = Notification.objects.create(
                recipient=membership.user,
                notification_type='group_invite',
                priority='high',
                content_type=ContentType.objects.get_for_model(GroupMembership),
                object_id=membership.id,
                title=f"Invitation to join {membership.group.name}",
                message=(
                    f"You've been invited to join the climbing group '{membership.group.name}'"
                ),
                action_url=f"/groups/{membership.group.id}/invites"
            )

            logger.info(
                f"Created group_invite notification for user {membership.user.id} "
                f"to group {membership.group.id}"
            )

            return notification

        except Exception as e:
            logger.error(
                f"Failed to create group_invite notification: {str(e)}",
                exc_info=True
            )
            return None

    @staticmethod
    def create_group_trip_notification(group, trip, notification_type='group_trip_posted'):
        """
        Create notifications for all group members when a trip is posted or updated.

        Args:
            group (ClimbingGroup): The group the trip belongs to
            trip (Trip): The trip that was posted/updated
            notification_type (str): Either 'group_trip_posted' or 'group_trip_updated'

        Returns:
            list: Created notification objects
        """
        try:
            from users.models import Block
            from django.db.models import Q

            notifications = []

            # Get all active group members (excluding pending invites and the trip creator)
            active_members = group.members.exclude(
                id=trip.user.id
            ).filter(
                climbing_groups__id=group.id,
                climbing_groups__groupmembership__role__in=['admin', 'member']
            ).distinct()

            for member in active_members:
                # Check for blocking between trip creator and member
                if Block.objects.filter(
                    Q(blocker=trip.user, blocked=member) |
                    Q(blocker=member, blocked=trip.user)
                ).exists():
                    logger.info(
                        f"Skipping {notification_type} notification - blocking exists between "
                        f"trip creator {trip.user.id} and member {member.id}"
                    )
                    continue

                # Determine title and message based on notification type
                if notification_type == 'group_trip_posted':
                    title = f"New trip in {group.name}"
                    message = (
                        f"{trip.user.display_name} posted a trip to {trip.destination.name} "
                        f"in your group '{group.name}' "
                        f"({trip.start_date.strftime('%b %d')} - {trip.end_date.strftime('%b %d')})"
                    )
                    priority = 'medium'
                else:  # group_trip_updated
                    title = f"Trip updated in {group.name}"
                    message = (
                        f"{trip.user.display_name} updated their trip to {trip.destination.name} "
                        f"in '{group.name}'"
                    )
                    priority = 'medium'

                notification = Notification.objects.create(
                    recipient=member,
                    notification_type=notification_type,
                    priority=priority,
                    content_type=ContentType.objects.get_for_model(Trip),
                    object_id=trip.id,
                    title=title,
                    message=message,
                    action_url=f"/trips/{trip.id}"
                )
                notifications.append(notification)

            logger.info(
                f"Created {len(notifications)} {notification_type} notifications for group {group.id}"
            )

            return notifications

        except Exception as e:
            logger.error(
                f"Failed to create {notification_type} notifications: {str(e)}",
                exc_info=True
            )
            return []

    @staticmethod
    def get_unread_notifications(user, limit=None):
        """
        Get unread notifications for a user.

        Args:
            user (User): The user to get notifications for
            limit (int, optional): Maximum number of notifications to return

        Returns:
            QuerySet: Unread notifications
        """
        queryset = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).select_related(
            'recipient',
            'content_type'
        ).order_by('-created_at')

        if limit:
            queryset = queryset[:limit]

        return queryset

    @staticmethod
    def get_unshown_popup_notifications(user, limit=None):
        """
        Get critical notifications that haven't been shown as popups yet.

        Args:
            user (User): The user to get notifications for
            limit (int, optional): Maximum number of notifications to return

        Returns:
            QuerySet: Critical unshown notifications
        """
        queryset = Notification.objects.filter(
            recipient=user,
            priority='critical',
            popup_shown=False
        ).select_related(
            'recipient',
            'content_type'
        ).order_by('-created_at')

        if limit:
            queryset = queryset[:limit]

        return queryset

    @staticmethod
    def mark_popup_shown(notification_id):
        """
        Mark that a notification popup was shown to the user.

        Args:
            notification_id (str/UUID): The notification ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.mark_popup_shown()
            return True
        except Notification.DoesNotExist:
            logger.error(f"Notification {notification_id} not found")
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark popup shown for notification {notification_id}: {str(e)}",
                exc_info=True
            )
            return False

    @staticmethod
    @transaction.atomic
    def bulk_create_notifications(notifications_data):
        """
        Bulk create multiple notifications efficiently.

        Args:
            notifications_data (list): List of dicts with notification data

        Returns:
            list: Created notification objects
        """
        try:
            notifications = []
            for data in notifications_data:
                notification = Notification(
                    recipient=data['recipient'],
                    notification_type=data['notification_type'],
                    priority=data['priority'],
                    content_type=data['content_type'],
                    object_id=data['object_id'],
                    title=data['title'],
                    message=data['message'],
                    action_url=data.get('action_url', ''),
                )
                notifications.append(notification)

            created = Notification.objects.bulk_create(notifications)
            logger.info(f"Bulk created {len(created)} notifications")
            return created

        except Exception as e:
            logger.error(
                f"Failed to bulk create notifications: {str(e)}",
                exc_info=True
            )
            return []
