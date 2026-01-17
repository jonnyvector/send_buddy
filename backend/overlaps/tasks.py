from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging

from .models import TripOverlap
from .services import OverlapEngine
from trips.models import Trip

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def detect_all_overlaps():
    """
    Daily task to detect new trip overlaps.
    Runs at 6 AM daily via Celery Beat.

    Returns:
        str: Summary of detection results
    """
    try:
        # Get active users with upcoming trips
        active_users = User.objects.filter(
            is_active=True,
            trips__end_date__gte=timezone.now().date(),
            trips__is_active=True
        ).distinct()

        logger.info(f"Starting overlap detection for {active_users.count()} users")

        new_overlaps = []
        errors = []

        for user in active_users:
            try:
                overlaps = OverlapEngine.detect_overlaps_for_user(user)
                new_overlaps.extend(overlaps)

                if overlaps:
                    logger.info(f"Detected {len(overlaps)} overlaps for user {user.id}")
            except Exception as e:
                error_msg = f"Error detecting overlaps for user {user.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Clean up expired overlaps
        expired_count = OverlapEngine.cleanup_expired_overlaps()

        result = f"Detected {len(new_overlaps)} new overlaps for {active_users.count()} users"
        if expired_count > 0:
            result += f", cleaned up {expired_count} expired overlaps"
        if errors:
            result += f", {len(errors)} errors occurred"

        logger.info(result)
        return result

    except Exception as e:
        error_msg = f"Critical error in detect_all_overlaps: {e}"
        logger.error(error_msg)
        return error_msg


@shared_task
def send_overlap_notifications():
    """
    Send notifications for unsent overlaps.
    Runs every 2 hours via Celery Beat.

    Returns:
        str: Summary of notifications sent
    """
    try:
        from notifications.services import NotificationService

        # Get overlaps that haven't been notified and are still upcoming
        unsent_overlaps = TripOverlap.objects.filter(
            notification_sent=False,
            overlap_start_date__gte=timezone.now().date()
        ).select_related('user1', 'user2', 'trip1', 'trip2', 'overlap_destination')

        logger.info(f"Found {unsent_overlaps.count()} overlaps needing notifications")

        sent_count = 0
        errors = []

        for overlap in unsent_overlaps:
            try:
                # Send notification to user1
                NotificationService.create_notification(
                    recipient=overlap.user1,
                    notification_type='trip_overlap',
                    title=f'Trip Overlap Detected!',
                    message=(
                        f'Your trip to {overlap.overlap_destination.name} overlaps with '
                        f'{overlap.user2.get_display_name()}\'s trip! '
                        f'Overlap: {overlap.overlap_start_date} to {overlap.overlap_end_date} '
                        f'(Score: {overlap.overlap_score}%)'
                    ),
                    metadata={
                        'overlap_id': str(overlap.id),
                        'trip_id': str(overlap.trip1.id),
                        'other_user_id': str(overlap.user2.id),
                        'overlap_score': overlap.overlap_score,
                        'destination': overlap.overlap_destination.name
                    }
                )

                # Send notification to user2
                NotificationService.create_notification(
                    recipient=overlap.user2,
                    notification_type='trip_overlap',
                    title=f'Trip Overlap Detected!',
                    message=(
                        f'Your trip to {overlap.overlap_destination.name} overlaps with '
                        f'{overlap.user1.get_display_name()}\'s trip! '
                        f'Overlap: {overlap.overlap_start_date} to {overlap.overlap_end_date} '
                        f'(Score: {overlap.overlap_score}%)'
                    ),
                    metadata={
                        'overlap_id': str(overlap.id),
                        'trip_id': str(overlap.trip2.id),
                        'other_user_id': str(overlap.user1.id),
                        'overlap_score': overlap.overlap_score,
                        'destination': overlap.overlap_destination.name
                    }
                )

                # Mark as sent
                overlap.notification_sent = True
                overlap.notification_sent_at = timezone.now()
                overlap.save()

                sent_count += 1
                logger.info(f"Sent notifications for overlap {overlap.id}")

            except Exception as e:
                error_msg = f"Error sending notification for overlap {overlap.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        result = f"Sent notifications for {sent_count} overlaps"
        if errors:
            result += f", {len(errors)} errors occurred"

        logger.info(result)
        return result

    except Exception as e:
        error_msg = f"Critical error in send_overlap_notifications: {e}"
        logger.error(error_msg)
        return error_msg


@shared_task
def update_trip_statuses():
    """
    Daily task to update trip statuses based on dates.
    Marks trips as in_progress or completed based on current date.

    Returns:
        str: Summary of status updates
    """
    try:
        today = timezone.now().date()

        # Mark trips as in_progress
        in_progress_count = Trip.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            trip_status='planned'
        ).update(trip_status='in_progress')

        # Mark trips as completed
        completed_count = Trip.objects.filter(
            end_date__lt=today,
            trip_status__in=['planned', 'in_progress']
        ).update(trip_status='completed')

        result = f"Updated {in_progress_count} trips to in_progress, {completed_count} trips to completed"
        logger.info(result)
        return result

    except Exception as e:
        error_msg = f"Error in update_trip_statuses: {e}"
        logger.error(error_msg)
        return error_msg


@shared_task
def detect_overlaps_for_new_trip(trip_id):
    """
    Task triggered when a new trip is created or updated.
    Detects overlaps immediately for better UX.

    Args:
        trip_id: UUID of the trip to detect overlaps for

    Returns:
        str: Summary of detection results
    """
    try:
        trip = Trip.objects.select_related('user', 'destination').get(id=trip_id)

        # Skip if trip is not active or is private
        if not trip.is_active or trip.visibility_status == 'full_private':
            return f"Trip {trip_id} is not eligible for overlap detection"

        overlaps = OverlapEngine.detect_overlaps_for_trip(trip)

        result = f"Detected {len(overlaps)} overlaps for trip {trip_id}"
        logger.info(result)

        # Send notifications immediately for high-score overlaps
        high_score_overlaps = [o for o in overlaps if o.overlap_score >= 70]
        if high_score_overlaps:
            # Trigger notification task
            send_high_score_overlap_notifications.delay([o.id for o in high_score_overlaps])
            result += f", {len(high_score_overlaps)} are high-score matches"

        return result

    except Trip.DoesNotExist:
        error_msg = f"Trip {trip_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error detecting overlaps for trip {trip_id}: {e}"
        logger.error(error_msg)
        return error_msg


@shared_task
def send_high_score_overlap_notifications(overlap_ids):
    """
    Send immediate notifications for high-score overlaps.
    Used when new high-score overlaps are detected.

    Args:
        overlap_ids: List of overlap IDs to notify about

    Returns:
        str: Summary of notifications sent
    """
    try:
        from notifications.services import NotificationService

        overlaps = TripOverlap.objects.filter(
            id__in=overlap_ids,
            notification_sent=False
        ).select_related('user1', 'user2', 'trip1', 'trip2', 'overlap_destination')

        sent_count = 0

        for overlap in overlaps:
            try:
                # Priority notification for high scores
                priority = 'critical' if overlap.overlap_score >= 85 else 'high'

                # Notify user1
                NotificationService.create_notification(
                    recipient=overlap.user1,
                    notification_type='trip_overlap',
                    priority=priority,
                    title=f'High Match Score: {overlap.overlap_score}%!',
                    message=(
                        f'Great match with {overlap.user2.get_display_name()} '
                        f'for {overlap.overlap_destination.name}! '
                        f'{overlap.overlap_days} overlapping days.'
                    ),
                    metadata={
                        'overlap_id': str(overlap.id),
                        'trip_id': str(overlap.trip1.id),
                        'other_user_id': str(overlap.user2.id),
                        'overlap_score': overlap.overlap_score,
                        'is_high_score': True
                    }
                )

                # Notify user2
                NotificationService.create_notification(
                    recipient=overlap.user2,
                    notification_type='trip_overlap',
                    priority=priority,
                    title=f'High Match Score: {overlap.overlap_score}%!',
                    message=(
                        f'Great match with {overlap.user1.get_display_name()} '
                        f'for {overlap.overlap_destination.name}! '
                        f'{overlap.overlap_days} overlapping days.'
                    ),
                    metadata={
                        'overlap_id': str(overlap.id),
                        'trip_id': str(overlap.trip2.id),
                        'other_user_id': str(overlap.user1.id),
                        'overlap_score': overlap.overlap_score,
                        'is_high_score': True
                    }
                )

                overlap.notification_sent = True
                overlap.notification_sent_at = timezone.now()
                overlap.save()

                sent_count += 1

            except Exception as e:
                logger.error(f"Error sending high-score notification for overlap {overlap.id}: {e}")

        result = f"Sent high-score notifications for {sent_count} overlaps"
        logger.info(result)
        return result

    except Exception as e:
        error_msg = f"Error in send_high_score_overlap_notifications: {e}"
        logger.error(error_msg)
        return error_msg


@shared_task
def detect_cross_path_overlaps():
    """
    Weekly task to detect when friends are visiting user's home area.
    Runs once a week to find trips near users' home locations.

    Returns:
        str: Summary of cross-path detections
    """
    try:
        from notifications.services import NotificationService

        # Get users with home locations set
        users_with_homes = User.objects.filter(
            home_latitude__isnull=False,
            home_longitude__isnull=False,
            is_active=True
        )

        cross_paths_found = 0

        for user in users_with_homes:
            # Get user's friends
            from friendships.models import Friendship
            friends = Friendship.get_friends(user)

            if not friends.exists():
                continue

            # Get friends' upcoming trips
            friend_trips = Trip.objects.filter(
                user__in=friends,
                end_date__gte=timezone.now().date(),
                is_active=True,
                visibility_status__in=['looking_for_partners', 'open_to_friends']
            ).select_related('user', 'destination')

            for trip in friend_trips:
                # Check if trip is near user's home
                if OverlapEngine.detect_cross_path(user, trip):
                    # Send notification
                    NotificationService.create_notification(
                        recipient=user,
                        notification_type='cross_path',
                        title=f'{trip.user.get_display_name()} is coming to your area!',
                        message=(
                            f'Your friend is planning a trip to {trip.destination.name} '
                            f'from {trip.start_date} to {trip.end_date}.'
                        ),
                        metadata={
                            'trip_id': str(trip.id),
                            'friend_id': str(trip.user.id),
                            'destination': trip.destination.name
                        }
                    )

                    cross_paths_found += 1

        result = f"Detected {cross_paths_found} cross-path overlaps"
        logger.info(result)
        return result

    except Exception as e:
        error_msg = f"Error in detect_cross_path_overlaps: {e}"
        logger.error(error_msg)
        return error_msg