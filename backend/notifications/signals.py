from django.db.models.signals import post_save
from django.dispatch import receiver
from trips.models import Trip
from climbing_sessions.models import Session
from matching.services import MatchingService
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Trip)
def notify_matching_users(sender, instance, created, **kwargs):
    """
    Signal handler that creates notifications when a new trip is created.
    Finds top matches and notifies them about the new match.

    Args:
        sender: The model class (Trip)
        instance: The actual trip instance that was saved
        created: Boolean indicating if this is a new trip
        **kwargs: Additional signal arguments
    """
    # Only process new trips that are active
    if not created or not instance.is_active:
        return

    try:
        trip = instance
        trip_owner = trip.user

        logger.info(f"Processing new trip {trip.id} for notifications")

        # Find potential matches for this trip
        # We'll notify users who have matching trips to the same destination
        matching_service = MatchingService(trip_owner, trip, limit=3)
        matches = matching_service.get_matches()

        if not matches:
            logger.info(f"No matches found for trip {trip.id}")
            return

        # Create notifications for top matches
        notification_count = 0
        for match in matches[:3]:  # Top 3 matches only
            matched_user = match['user']
            match_score = match['score']

            # Create notification for the matched user
            notification = NotificationService.create_new_match_notification(
                recipient=matched_user,
                matched_user=trip_owner,
                trip=trip,
                match_score=match_score
            )

            if notification:
                notification_count += 1

        logger.info(
            f"Created {notification_count} new_match notifications for trip {trip.id}"
        )

    except Exception as e:
        logger.error(
            f"Error creating notifications for trip {instance.id}: {str(e)}",
            exc_info=True
        )


@receiver(post_save, sender=Session)
def notify_session_updates(sender, instance, created, **kwargs):
    """
    Signal handler for session/connection requests and status changes.
    Creates notifications when:
    - A new session request is created (pending status)
    - A session is accepted
    - A session is declined
    """
    try:
        session = instance

        # New session request - notify the invitee
        if created and session.status == 'pending':
            from notifications.models import Notification
            from django.contrib.contenttypes.models import ContentType

            logger.info(f"Creating notification for new session request {session.id}")

            # Create notification for the invitee (person receiving the request)
            notification = Notification.objects.create(
                recipient=session.invitee,
                notification_type='connection_request',
                priority='critical',  # Show popup for connection requests
                content_type=ContentType.objects.get_for_model(Session),
                object_id=session.id,
                title=f"New Connection Request from {session.inviter.display_name}",
                message=(
                    f"{session.inviter.display_name} wants to climb with you "
                    f"at {session.trip.destination.name}!"
                ),
                action_url=f"/sessions"
            )

            logger.info(f"Created connection_request notification {notification.id} for session {session.id}")

        # Session accepted - notify the inviter
        elif not created and session.status == 'accepted':
            from notifications.models import Notification
            from django.contrib.contenttypes.models import ContentType

            # Check if we already created a notification for this acceptance
            existing = Notification.objects.filter(
                notification_type='connection_accepted',
                object_id=session.id
            ).exists()

            if not existing:
                logger.info(f"Creating notification for accepted session {session.id}")

                notification = Notification.objects.create(
                    recipient=session.inviter,
                    notification_type='connection_accepted',
                    priority='critical',  # Show popup for accepted connections
                    content_type=ContentType.objects.get_for_model(Session),
                    object_id=session.id,
                    title=f"{session.invitee.display_name} accepted your request!",
                    message=(
                        f"{session.invitee.display_name} accepted your connection request. "
                        f"You can now chat and plan your climbing session!"
                    ),
                    action_url=f"/sessions/{session.id}"
                )

                logger.info(f"Created connection_accepted notification {notification.id}")

    except Exception as e:
        logger.error(
            f"Error creating notification for session {instance.id}: {str(e)}",
            exc_info=True
        )
