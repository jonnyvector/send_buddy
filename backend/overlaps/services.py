from django.db.models import Q, F, Exists, OuterRef
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from typing import List, Optional
import logging
from math import radians, sin, cos, sqrt, atan2

from .models import TripOverlap
from trips.models import Trip, Destination
from friendships.models import Friendship
from friendships.services import FriendshipService
from users.models import Block, User

logger = logging.getLogger(__name__)


class OverlapEngine:
    """
    Service for detecting and managing trip overlaps between users.
    Enforces bilateral blocking and visibility rules.
    """

    # Constants for scoring
    MAX_DAYS_SCORE = 30
    POINTS_PER_DAY = 6
    MAX_SCORED_DAYS = 5
    DISCIPLINE_SCORE = 25
    GRADE_SCORE = 20
    FRIENDSHIP_SCORE = 15
    CRAG_BONUS = 10

    # Distance threshold for cross-path detection (km)
    CROSS_PATH_DISTANCE_KM = 100

    @staticmethod
    def detect_overlaps_for_user(user: User) -> List[TripOverlap]:
        """
        Detect all trip overlaps for a specific user's trips.

        Args:
            user: User to detect overlaps for

        Returns:
            List of newly created TripOverlap objects
        """
        if not user or not user.is_authenticated:
            return []

        new_overlaps = []
        today = timezone.now().date()

        # Get user's upcoming trips with visible status (not full/private)
        user_trips = Trip.objects.filter(
            user=user,
            end_date__gte=today,
            is_active=True,
            visibility_status__in=['looking_for_partners', 'open_to_friends']
        ).select_related('destination').prefetch_related('preferred_crags')

        if not user_trips.exists():
            logger.debug(f"No eligible trips found for user {user.id}")
            return []

        # Get friends and their IDs
        friends = Friendship.get_friends(user)
        friend_ids = set(friends.values_list('id', flat=True))

        # Get visible users (applies blocking logic)
        visible_users = User.objects.visible_to(user).exclude(id=user.id)

        # Build query for other users' trips
        if friend_ids:
            # Friends' trips that are open_to_friends or looking_for_partners
            other_trips_query = Trip.objects.filter(
                Q(user__in=friend_ids, visibility_status__in=['open_to_friends', 'looking_for_partners']) |
                Q(visibility_status='looking_for_partners'),
                user__in=visible_users,
                end_date__gte=today,
                is_active=True
            ).exclude(user=user)
        else:
            # No friends, only see trips that are looking_for_partners
            other_trips_query = Trip.objects.filter(
                user__in=visible_users,
                visibility_status='looking_for_partners',
                end_date__gte=today,
                is_active=True
            ).exclude(user=user)

        other_trips = other_trips_query.select_related(
            'user', 'destination'
        ).prefetch_related('preferred_crags')

        # Process each user trip against other trips
        for user_trip in user_trips:
            # Find trips at the same destination with overlapping dates
            matching_trips = other_trips.filter(
                destination=user_trip.destination,
                start_date__lte=user_trip.end_date,
                end_date__gte=user_trip.start_date
            )

            for other_trip in matching_trips:
                # Check if overlap already exists (in either direction)
                existing = TripOverlap.objects.filter(
                    Q(trip1=user_trip, trip2=other_trip) |
                    Q(trip1=other_trip, trip2=user_trip)
                ).exists()

                if existing:
                    continue

                # Calculate overlap dates
                overlap_start = max(user_trip.start_date, other_trip.start_date)
                overlap_end = min(user_trip.end_date, other_trip.end_date)
                overlap_days = (overlap_end - overlap_start).days + 1

                # Check if users are friends
                are_friends = other_trip.user_id in friend_ids

                # Calculate overlap score
                score = OverlapEngine.calculate_overlap_score(
                    user_trip, other_trip, are_friends
                )

                # Create the overlap record
                try:
                    with transaction.atomic():
                        overlap = TripOverlap.objects.create(
                            user1=user,
                            user2=other_trip.user,
                            trip1=user_trip,
                            trip2=other_trip,
                            overlap_destination=user_trip.destination,
                            overlap_start_date=overlap_start,
                            overlap_end_date=overlap_end,
                            overlap_days=overlap_days,
                            overlap_score=score
                        )
                        new_overlaps.append(overlap)

                        logger.info(
                            f"Created overlap between trips {user_trip.id} and {other_trip.id} "
                            f"with score {score}"
                        )
                except Exception as e:
                    logger.error(f"Error creating overlap: {e}")
                    continue

        return new_overlaps

    @staticmethod
    def detect_overlaps_for_trip(trip: Trip) -> List[TripOverlap]:
        """
        Detect overlaps for a newly created/updated trip.
        Called when a trip is created or dates/destination changed.

        Args:
            trip: The trip to detect overlaps for

        Returns:
            List of newly created TripOverlap objects
        """
        if not trip or not trip.is_active:
            return []

        # Skip if trip is private
        if trip.visibility_status == 'full_private':
            return []

        new_overlaps = []
        today = timezone.now().date()

        # Skip past trips
        if trip.end_date < today:
            return []

        user = trip.user

        # Get friends
        friends = Friendship.get_friends(user)
        friend_ids = set(friends.values_list('id', flat=True))

        # Get visible users
        visible_users = User.objects.visible_to(user).exclude(id=user.id)

        # Build query for other trips
        # Get visible friend IDs (intersection of friends and visible users)
        visible_friend_ids = friend_ids & set(visible_users.values_list('id', flat=True))

        # Calculate minimum end date (must overlap with our trip AND not be in the past)
        min_end_date = max(trip.start_date, today)

        if visible_friend_ids and trip.visibility_status == 'open_to_friends':
            # If trip is open to friends, match with friends' trips
            other_trips_query = Trip.objects.filter(
                user_id__in=visible_friend_ids,
                visibility_status__in=['open_to_friends', 'looking_for_partners'],
                destination=trip.destination,
                start_date__lte=trip.end_date,
                end_date__gte=min_end_date,
                is_active=True
            )
        elif trip.visibility_status == 'looking_for_partners':
            # If looking for partners, match with anyone visible
            visible_user_ids = set(visible_users.values_list('id', flat=True))
            other_trips_query = Trip.objects.filter(
                Q(user_id__in=visible_friend_ids, visibility_status__in=['open_to_friends', 'looking_for_partners']) |
                Q(user_id__in=visible_user_ids, visibility_status='looking_for_partners'),
                destination=trip.destination,
                start_date__lte=trip.end_date,
                end_date__gte=min_end_date,
                is_active=True
            )
        else:
            # No matches for full/private trips
            return []

        other_trips = other_trips_query.select_related(
            'user', 'destination'
        ).prefetch_related('preferred_crags')

        for other_trip in other_trips:
            # Check if overlap already exists
            existing = TripOverlap.objects.filter(
                Q(trip1=trip, trip2=other_trip) |
                Q(trip1=other_trip, trip2=trip)
            ).exists()

            if existing:
                continue

            # Calculate overlap
            overlap_start = max(trip.start_date, other_trip.start_date)
            overlap_end = min(trip.end_date, other_trip.end_date)
            overlap_days = (overlap_end - overlap_start).days + 1

            # Check friendship
            are_friends = other_trip.user_id in friend_ids

            # Calculate score
            score = OverlapEngine.calculate_overlap_score(
                trip, other_trip, are_friends
            )

            # Create overlap record
            try:
                with transaction.atomic():
                    overlap = TripOverlap.objects.create(
                        user1=user,
                        user2=other_trip.user,
                        trip1=trip,
                        trip2=other_trip,
                        overlap_destination=trip.destination,
                        overlap_start_date=overlap_start,
                        overlap_end_date=overlap_end,
                        overlap_days=overlap_days,
                        overlap_score=score
                    )
                    new_overlaps.append(overlap)

                    logger.info(
                        f"Created overlap for new trip {trip.id} with trip {other_trip.id}"
                    )

                    # Note: Notifications will be sent by the background task

            except Exception as e:
                logger.error(f"Error creating overlap for trip {trip.id}: {e}")
                continue

        return new_overlaps

    @staticmethod
    def calculate_overlap_score(trip1: Trip, trip2: Trip, are_friends: bool = False) -> int:
        """
        Calculate overlap score (0-100) based on multiple factors.

        Args:
            trip1: First trip
            trip2: Second trip
            are_friends: Whether the users are friends

        Returns:
            Score between 0 and 100
        """
        score = 0

        # 1. Days score (max 30 points)
        overlap_start = max(trip1.start_date, trip2.start_date)
        overlap_end = min(trip1.end_date, trip2.end_date)
        overlap_days = (overlap_end - overlap_start).days + 1

        days_score = min(overlap_days * OverlapEngine.POINTS_PER_DAY, OverlapEngine.MAX_DAYS_SCORE)
        score += days_score

        # 2. Discipline compatibility (max 25 points)
        if trip1.preferred_disciplines and trip2.preferred_disciplines:
            disciplines1 = set(trip1.preferred_disciplines)
            disciplines2 = set(trip2.preferred_disciplines)

            if disciplines1 and disciplines2:
                # Calculate overlap ratio
                intersection = disciplines1 & disciplines2
                union = disciplines1 | disciplines2

                if union:
                    overlap_ratio = len(intersection) / len(union)
                    discipline_score = int(overlap_ratio * OverlapEngine.DISCIPLINE_SCORE)
                    score += discipline_score

        # 3. Grade compatibility (max 20 points)
        if (trip1.min_grade and trip1.max_grade and
            trip2.min_grade and trip2.max_grade and
            trip1.grade_system == trip2.grade_system):

            # Check if grade ranges overlap
            # Simple string comparison - in production would need grade conversion
            grades_overlap = not (trip1.max_grade < trip2.min_grade or
                                trip2.max_grade < trip1.min_grade)

            if grades_overlap:
                # Give full points for overlap, could be more sophisticated
                score += OverlapEngine.GRADE_SCORE

        # 4. Friendship bonus (15 points)
        if are_friends:
            score += OverlapEngine.FRIENDSHIP_SCORE

        # 5. Crag bonus (max 10 points)
        if trip1.preferred_crags.exists() and trip2.preferred_crags.exists():
            crags1 = set(trip1.preferred_crags.values_list('id', flat=True))
            crags2 = set(trip2.preferred_crags.values_list('id', flat=True))

            if crags1 & crags2:  # If there's any overlap
                score += OverlapEngine.CRAG_BONUS

        # Ensure score is within bounds
        return min(score, 100)

    @staticmethod
    def detect_cross_path(user: User, trip: Trip) -> Optional[bool]:
        """
        Detect if a friend's trip overlaps with user's home location.
        Used to notify: "Your friend is coming to your area!"

        Args:
            user: The user whose home location to check
            trip: The trip to check against

        Returns:
            True if cross-path detected, False otherwise
        """
        if not user.home_latitude or not user.home_longitude:
            return False

        if not trip.destination:
            return False

        # Calculate distance between user's home and trip destination
        distance = OverlapEngine._calculate_distance(
            user.home_latitude,
            user.home_longitude,
            trip.destination.lat,
            trip.destination.lng
        )

        # Check if within threshold
        if distance <= OverlapEngine.CROSS_PATH_DISTANCE_KM:
            logger.info(
                f"Cross-path detected: Trip {trip.id} to {trip.destination.name} "
                f"is within {distance:.1f}km of user {user.id}'s home location"
            )
            return True

        return False

    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = radians(float(lat1))
        lat2_rad = radians(float(lat2))
        delta_lat = radians(float(lat2) - float(lat1))
        delta_lon = radians(float(lon2) - float(lon1))

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @staticmethod
    def get_overlaps_for_user(user: User, include_dismissed: bool = False) -> List[TripOverlap]:
        """
        Get all active (non-dismissed) overlaps for a user.

        Args:
            user: The user to get overlaps for
            include_dismissed: Whether to include dismissed overlaps

        Returns:
            QuerySet of TripOverlap objects
        """
        today = timezone.now().date()

        query = TripOverlap.objects.filter(
            Q(user1=user) | Q(user2=user),
            overlap_end_date__gte=today
        )

        if not include_dismissed:
            # Exclude dismissed overlaps
            query = query.exclude(
                Q(user1=user, user1_dismissed=True) |
                Q(user2=user, user2_dismissed=True)
            )

        return query.select_related(
            'user1', 'user2', 'trip1', 'trip2', 'overlap_destination'
        ).order_by('-overlap_score', 'overlap_start_date')

    @staticmethod
    def dismiss_overlap(overlap_id: str, user: User) -> bool:
        """
        Mark an overlap as dismissed by user.

        Args:
            overlap_id: ID of the overlap to dismiss
            user: User dismissing the overlap

        Returns:
            True if successfully dismissed, False otherwise
        """
        try:
            overlap = TripOverlap.objects.get(id=overlap_id)

            if overlap.user1 == user:
                overlap.user1_dismissed = True
            elif overlap.user2 == user:
                overlap.user2_dismissed = True
            else:
                logger.warning(f"User {user.id} attempted to dismiss overlap {overlap_id} they're not part of")
                return False

            overlap.save()
            logger.info(f"User {user.id} dismissed overlap {overlap_id}")
            return True

        except TripOverlap.DoesNotExist:
            logger.error(f"Overlap {overlap_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error dismissing overlap {overlap_id}: {e}")
            return False

    @staticmethod
    def cleanup_expired_overlaps() -> int:
        """
        Remove overlaps where both trips have ended more than 30 days ago.

        Returns:
            Number of overlaps deleted
        """
        cutoff_date = timezone.now().date() - timedelta(days=30)

        expired_overlaps = TripOverlap.objects.filter(
            overlap_end_date__lt=cutoff_date
        )

        count = expired_overlaps.count()
        expired_overlaps.delete()

        if count > 0:
            logger.info(f"Cleaned up {count} expired overlaps")

        return count