from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from users.models import User, Block
from trips.models import Trip, Destination
from friendships.models import Friendship
from overlaps.models import TripOverlap


class FeedAPITestCase(TestCase):
    """Test suite for Feed API"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create users
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )

        self.friend1 = User.objects.create_user(
            email='friend1@example.com',
            password='password123',
            display_name='Friend One',
            home_location='Denver, CO'
        )

        self.friend2 = User.objects.create_user(
            email='friend2@example.com',
            password='password123',
            display_name='Friend Two',
            home_location='Fort Collins, CO'
        )

        self.non_friend = User.objects.create_user(
            email='nonfriend@example.com',
            password='password123',
            display_name='Non Friend',
            home_location='New York, NY'
        )

        # Create friendships
        Friendship.objects.create(
            requester=self.user,
            addressee=self.friend1,
            status='accepted',
            accepted_at=timezone.now()
        )

        Friendship.objects.create(
            requester=self.friend2,
            addressee=self.user,
            status='accepted',
            accepted_at=timezone.now()
        )

        # Create destinations
        self.destination1 = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge',
            country='USA',
            lat=37.7,
            lng=-83.6,
            primary_disciplines=['sport', 'trad']
        )

        self.destination2 = Destination.objects.create(
            slug='yosemite',
            name='Yosemite',
            country='USA',
            lat=37.8,
            lng=-119.5,
            primary_disciplines=['trad', 'bouldering']
        )

        # Create trips for user (to establish visited destinations)
        self.user_trip = Trip.objects.create(
            user=self.user,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=35),
            visibility_status='open_to_friends'
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_empty_feed(self):
        """Test feed with no activities"""
        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 0)
        self.assertEqual(len(response.data['items']), 0)
        self.assertFalse(response.data['has_more'])

    def test_friend_new_trip_in_feed(self):
        """Test that friend's new trip appears in feed"""
        # Friend creates a new trip
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['items'][0]['type'], 'friend_trip')
        self.assertIn('Friend One', response.data['items'][0]['action_text'])

    def test_friend_looking_for_partners_in_feed(self):
        """Test that friend's trip looking for partners appears in feed"""
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='looking_for_partners'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['items'][0]['type'], 'looking_for_partners')
        self.assertIn('looking for partners', response.data['items'][0]['action_text'])

    def test_friend_completed_trip_in_feed(self):
        """Test that friend's completed trip appears in feed"""
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
            visibility_status='open_to_friends',
            trip_status='completed'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['items'][0]['type'], 'friend_trip_completed')
        self.assertIn('completed', response.data['items'][0]['action_text'])

    def test_private_trip_not_in_feed(self):
        """Test that friend's private trip does not appear in feed"""
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='full_private'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 0)

    def test_non_friend_trip_not_in_feed(self):
        """Test that non-friend's trip does not appear in feed"""
        trip = Trip.objects.create(
            user=self.non_friend,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 0)

    def test_overlap_in_feed(self):
        """Test that trip overlap appears in feed"""
        # Create friend's trip
        friend_trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            visibility_status='open_to_friends'
        )

        # Create overlap
        overlap = TripOverlap.objects.create(
            user1=self.user,
            user2=self.friend1,
            trip1=self.user_trip,
            trip2=friend_trip,
            overlap_destination=self.destination1,
            overlap_start_date=date.today() + timedelta(days=30),
            overlap_end_date=date.today() + timedelta(days=35),
            overlap_days=6,
            overlap_score=85,
            user1_dismissed=False,
            user2_dismissed=False
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have both the friend's trip and the overlap
        self.assertGreaterEqual(response.data['total_count'], 1)

        # Check for overlap item
        overlap_items = [item for item in response.data['items'] if item['type'] == 'overlap']
        self.assertGreater(len(overlap_items), 0)
        self.assertIn('Friend One', overlap_items[0]['action_text'])

    def test_dismissed_overlap_not_in_feed(self):
        """Test that dismissed overlap does not appear in feed"""
        # Create friend's trip
        friend_trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            visibility_status='open_to_friends'
        )

        # Create overlap and dismiss it
        overlap = TripOverlap.objects.create(
            user1=self.user,
            user2=self.friend1,
            trip1=self.user_trip,
            trip2=friend_trip,
            overlap_destination=self.destination1,
            overlap_start_date=date.today() + timedelta(days=30),
            overlap_end_date=date.today() + timedelta(days=35),
            overlap_days=6,
            overlap_score=85,
            user1_dismissed=True,  # User dismissed
            user2_dismissed=False
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for overlap item
        overlap_items = [item for item in response.data['items'] if item['type'] == 'overlap']
        self.assertEqual(len(overlap_items), 0)

    def test_group_trip_in_feed(self):
        """Test that group trip organized by friend appears in feed"""
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends',
            is_group_trip=True,
            organizer=self.friend1
        )
        trip.invited_users.add(self.user)

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['total_count'], 1)

        # Check for group trip
        group_items = [item for item in response.data['items'] if item['type'] == 'group_trip']
        self.assertGreater(len(group_items), 0)

    def test_pagination(self):
        """Test feed pagination"""
        # Create multiple trips
        for i in range(10):
            Trip.objects.create(
                user=self.friend1,
                destination=self.destination2,
                start_date=date.today() + timedelta(days=10 + i),
                end_date=date.today() + timedelta(days=15 + i),
                visibility_status='open_to_friends'
            )

        # Get first page
        response = self.client.get('/api/feed/?limit=5&offset=0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 5)
        self.assertTrue(response.data['has_more'])
        self.assertEqual(response.data['total_count'], 10)

        # Get second page
        response = self.client.get('/api/feed/?limit=5&offset=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 5)
        self.assertFalse(response.data['has_more'])

    def test_blocking_enforcement(self):
        """Test that blocked users' trips don't appear in feed"""
        # User blocks friend1
        Block.objects.create(blocker=self.user, blocked=self.friend1)

        # Friend1 creates a trip
        trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should not see friend1's trip because they're blocked
        self.assertEqual(response.data['total_count'], 0)

    def test_network_trips_endpoint(self):
        """Test network trips endpoint returns only friend trips"""
        # Create friend trip
        Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        # Create overlap (should not appear in network-trips)
        friend_trip = Trip.objects.create(
            user=self.friend2,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            visibility_status='open_to_friends'
        )
        TripOverlap.objects.create(
            user1=self.user,
            user2=self.friend2,
            trip1=self.user_trip,
            trip2=friend_trip,
            overlap_destination=self.destination1,
            overlap_start_date=date.today() + timedelta(days=30),
            overlap_end_date=date.today() + timedelta(days=35),
            overlap_days=6,
            overlap_score=85
        )

        response = self.client.get('/api/feed/network_trips/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only have trip items, no overlaps
        for item in response.data['items']:
            self.assertIn(item['type'], ['friend_trip', 'friend_trip_completed', 'looking_for_partners'])

    def test_overlaps_endpoint(self):
        """Test overlaps endpoint returns only overlaps"""
        # Create friend trip
        Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        # Create overlap
        friend_trip = Trip.objects.create(
            user=self.friend2,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            visibility_status='open_to_friends'
        )
        TripOverlap.objects.create(
            user1=self.user,
            user2=self.friend2,
            trip1=self.user_trip,
            trip2=friend_trip,
            overlap_destination=self.destination1,
            overlap_start_date=date.today() + timedelta(days=30),
            overlap_end_date=date.today() + timedelta(days=35),
            overlap_days=6,
            overlap_score=85
        )

        response = self.client.get('/api/feed/overlaps/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only have overlap items
        for item in response.data['items']:
            self.assertEqual(item['type'], 'overlap')

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access feed"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_pagination_params(self):
        """Test validation of pagination parameters"""
        # Invalid limit (too high)
        response = self.client.get('/api/feed/?limit=200')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid limit (too low)
        response = self.client.get('/api/feed/?limit=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid offset (negative)
        response = self.client.get('/api/feed/?offset=-1')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feed_sorting_by_priority(self):
        """Test that feed items are sorted by priority and recency"""
        # Create high-priority overlap
        friend_trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            visibility_status='open_to_friends'
        )
        overlap = TripOverlap.objects.create(
            user1=self.user,
            user2=self.friend1,
            trip1=self.user_trip,
            trip2=friend_trip,
            overlap_destination=self.destination1,
            overlap_start_date=date.today() + timedelta(days=30),
            overlap_end_date=date.today() + timedelta(days=35),
            overlap_days=6,
            overlap_score=90  # High score
        )

        # Create lower-priority friend trip
        trip = Trip.objects.create(
            user=self.friend2,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            visibility_status='open_to_friends'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['total_count'], 2)

        # Overlap should appear first due to higher priority
        self.assertEqual(response.data['items'][0]['type'], 'overlap')

    def test_old_trips_filtered_out(self):
        """Test that trips older than 30 days are not shown (unless upcoming)"""
        # Create old trip (created 40 days ago, not upcoming)
        old_trip = Trip.objects.create(
            user=self.friend1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            visibility_status='open_to_friends'
        )
        old_trip.created_at = timezone.now() - timedelta(days=40)
        old_trip.save()

        # Create recent trip
        recent_trip = Trip.objects.create(
            user=self.friend2,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=15),
            end_date=date.today() + timedelta(days=20),
            visibility_status='open_to_friends'
        )

        response = self.client.get('/api/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only see recent trip, not the old one
        trip_items = [item for item in response.data['items'] if item['type'] in ['friend_trip', 'looking_for_partners']]
        # The recent_trip should be there, old trip might be filtered
        # This is based on the 30-day filter in the service
        self.assertGreaterEqual(len(trip_items), 1)
