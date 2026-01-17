from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import timedelta
from trips.models import Trip
from overlaps.models import TripOverlap
from friendships.models import Friendship
from users.models import User


class FeedService:
    """Service for generating user social feeds"""

    # Priority constants for feed item ordering
    PRIORITY_HIGH_OVERLAP = 100
    PRIORITY_SAME_DESTINATION = 80
    PRIORITY_LOOKING_FOR_PARTNERS = 70
    PRIORITY_FRIEND_NEW_TRIP = 60
    PRIORITY_GROUP_ACTIVITY = 50
    PRIORITY_COMPLETED_TRIP = 40

    @staticmethod
    def get_feed(user, limit=50, offset=0):
        """
        Generate social feed for user showing:
        - Friends' new trips (visibility = open_to_friends or looking_for_partners)
        - Friends' completed trips
        - Trip overlaps
        - Group activities (if in groups)

        Returns dict with:
        - items: list of feed items sorted by relevance/recency
        - has_more: boolean indicating if more items exist
        - total_count: total number of items available
        """
        feed_items = []

        # Get friends
        friends = Friendship.get_friends(user)

        # Get user's visited/planned destinations for relevance scoring
        user_destinations = set(
            Trip.objects.filter(user=user, is_active=True)
            .values_list('destination_id', flat=True)
        )

        # 1. Get friends' trips
        feed_items.extend(
            FeedService._get_friend_trips(user, friends, user_destinations)
        )

        # 2. Get overlaps
        feed_items.extend(FeedService._get_overlaps(user))

        # 3. Get group activities
        feed_items.extend(FeedService._get_group_activities(user, friends))

        # Sort by priority (descending) and timestamp (descending)
        feed_items.sort(
            key=lambda x: (x['priority'], x['timestamp']),
            reverse=True
        )

        # Apply pagination
        total_count = len(feed_items)
        paginated_items = feed_items[offset:offset + limit]
        has_more = offset + limit < total_count

        return {
            'items': paginated_items,
            'has_more': has_more,
            'total_count': total_count,
        }

    @staticmethod
    def _get_friend_trips(user, friends, user_destinations):
        """Get feed items for friends' trips"""
        feed_items = []

        # Get visible trips from friends (created in last 30 days or upcoming)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        today = timezone.now().date()

        friend_trips = (
            Trip.objects.filter(
                Q(user__in=friends) &
                Q(is_active=True) &
                (
                    Q(visibility_status='looking_for_partners') |
                    Q(visibility_status='open_to_friends')
                ) &
                (
                    Q(created_at__gte=thirty_days_ago) |
                    Q(start_date__gte=today)
                )
            )
            .select_related('user', 'destination')
            .order_by('-created_at')
        )

        for trip in friend_trips:
            feed_items.append(
                FeedService.get_feed_item_for_trip(trip, user, user_destinations)
            )

        return feed_items

    @staticmethod
    def _get_overlaps(user):
        """Get feed items for trip overlaps"""
        feed_items = []

        # Get non-dismissed overlaps
        overlaps = (
            TripOverlap.objects.filter(
                Q(user1=user, user1_dismissed=False) |
                Q(user2=user, user2_dismissed=False)
            )
            .select_related(
                'user1', 'user2', 'overlap_destination', 'trip1', 'trip2'
            )
            .order_by('-overlap_score', '-detected_at')
        )

        for overlap in overlaps:
            feed_items.append(FeedService.get_feed_item_for_overlap(overlap, user))

        return feed_items

    @staticmethod
    def _get_group_activities(user, friends):
        """Get feed items for group trip activities"""
        feed_items = []

        # Get group trips that user is invited to or friends are organizing
        thirty_days_ago = timezone.now() - timedelta(days=30)

        group_trips = (
            Trip.objects.filter(
                Q(is_group_trip=True) &
                Q(is_active=True) &
                (
                    Q(invited_users=user) |
                    Q(organizer__in=friends)
                ) &
                Q(created_at__gte=thirty_days_ago)
            )
            .select_related('user', 'destination', 'organizer')
            .prefetch_related('invited_users')
            .distinct()
            .order_by('-created_at')
        )

        for trip in group_trips:
            # Skip if user is the organizer
            if trip.organizer == user:
                continue

            feed_items.append({
                'type': 'group_trip',
                'trip': trip,
                'user': trip.organizer or trip.user,
                'timestamp': trip.created_at,
                'priority': FeedService.PRIORITY_GROUP_ACTIVITY,
                'action_text': f"{(trip.organizer or trip.user).display_name} organized a group trip to {trip.destination.name}",
            })

        return feed_items

    @staticmethod
    def get_feed_item_for_trip(trip, viewer, user_destinations=None):
        """
        Generate feed item data for a trip.

        Returns dict with:
        - type: 'friend_trip' | 'friend_trip_completed' | 'looking_for_partners'
        - trip: trip object
        - user: trip owner
        - timestamp: trip created_at
        - priority: int (for sorting)
        - action_text: descriptive text
        """
        if user_destinations is None:
            user_destinations = set()

        # Determine type and priority
        if trip.trip_status == 'completed':
            item_type = 'friend_trip_completed'
            priority = FeedService.PRIORITY_COMPLETED_TRIP
            action_text = f"{trip.user.display_name} completed trip to {trip.destination.name}"
        elif trip.visibility_status == 'looking_for_partners':
            item_type = 'looking_for_partners'
            # Boost priority if it's a destination the viewer has visited/planned
            if trip.destination_id in user_destinations:
                priority = FeedService.PRIORITY_SAME_DESTINATION
            else:
                priority = FeedService.PRIORITY_LOOKING_FOR_PARTNERS
            action_text = f"{trip.user.display_name} is looking for partners in {trip.destination.name}"
        else:
            item_type = 'friend_trip'
            # Boost priority if it's a destination the viewer has visited/planned
            if trip.destination_id in user_destinations:
                priority = FeedService.PRIORITY_SAME_DESTINATION
            else:
                priority = FeedService.PRIORITY_FRIEND_NEW_TRIP
            action_text = f"{trip.user.display_name} posted a trip to {trip.destination.name}"

        # Apply time decay for items older than 7 days
        days_old = (timezone.now() - trip.created_at).days
        if days_old > 7:
            priority = max(priority - (days_old - 7) * 5, 10)

        return {
            'type': item_type,
            'trip': trip,
            'user': trip.user,
            'timestamp': trip.created_at,
            'priority': priority,
            'action_text': action_text,
        }

    @staticmethod
    def get_feed_item_for_overlap(overlap, viewer):
        """
        Generate feed item data for an overlap.

        Returns dict with:
        - type: 'overlap'
        - overlap: overlap object
        - friend: the other user in the overlap
        - timestamp: overlap detected_at
        - priority: int (for sorting)
        - action_text: descriptive text
        """
        # Determine the other user (friend)
        friend = overlap.user2 if overlap.user1 == viewer else overlap.user1

        # Calculate priority based on overlap score
        priority = FeedService.PRIORITY_HIGH_OVERLAP

        # Boost for high-quality overlaps
        if overlap.overlap_score >= 80:
            priority += 10
        elif overlap.overlap_score >= 60:
            priority += 5

        # Apply time decay for items older than 7 days
        days_old = (timezone.now() - overlap.detected_at).days
        if days_old > 7:
            priority = max(priority - (days_old - 7) * 5, 10)

        action_text = (
            f"You and {friend.display_name} will both be in "
            f"{overlap.overlap_destination.name} ({overlap.overlap_days} days overlap)"
        )

        return {
            'type': 'overlap',
            'overlap': overlap,
            'friend': friend,
            'timestamp': overlap.detected_at,
            'priority': priority,
            'action_text': action_text,
        }

    @staticmethod
    def get_network_trips(user, limit=50, offset=0):
        """
        Get just friends' trips (no overlaps or groups).
        Useful for a filtered feed view.
        """
        friends = Friendship.get_friends(user)
        user_destinations = set(
            Trip.objects.filter(user=user, is_active=True)
            .values_list('destination_id', flat=True)
        )

        feed_items = FeedService._get_friend_trips(user, friends, user_destinations)

        # Sort by priority and timestamp
        feed_items.sort(
            key=lambda x: (x['priority'], x['timestamp']),
            reverse=True
        )

        total_count = len(feed_items)
        paginated_items = feed_items[offset:offset + limit]
        has_more = offset + limit < total_count

        return {
            'items': paginated_items,
            'has_more': has_more,
            'total_count': total_count,
        }

    @staticmethod
    def get_overlaps_feed(user, limit=50, offset=0):
        """
        Get just trip overlaps.
        Useful for a filtered feed view.
        """
        feed_items = FeedService._get_overlaps(user)

        # Sort by priority and timestamp
        feed_items.sort(
            key=lambda x: (x['priority'], x['timestamp']),
            reverse=True
        )

        total_count = len(feed_items)
        paginated_items = feed_items[offset:offset + limit]
        has_more = offset + limit < total_count

        return {
            'items': paginated_items,
            'has_more': has_more,
            'total_count': total_count,
        }
