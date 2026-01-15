from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from users.models import User, DisciplineProfile, Block, GradeConversion, Discipline, GradeSystem, RiskTolerance
from trips.models import Destination, Crag, Trip, AvailabilityBlock, TimeBlock


class MatchViewSetTest(TestCase):
    """Test Match API endpoints"""

    def setUp(self):
        """Create test data"""
        self.client = APIClient()

        # Create destination
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        # Create crags
        self.muir_valley = Crag.objects.create(
            destination=self.destination,
            name='Muir Valley',
            slug='muir-valley',
            disciplines=['sport']
        )

        # Create grade conversions
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=60,
            yds_grade='5.10d',
            french_grade='6b'
        )
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=70,
            yds_grade='5.11c',
            french_grade='6c'
        )

        # Create users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        # Create discipline profiles
        DisciplineProfile.objects.create(
            user=self.user1,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        DisciplineProfile.objects.create(
            user=self.user2,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.11c',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=70
        )

        # Create trips
        self.trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        self.trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

    def test_list_matches_unauthenticated(self):
        """Test GET /api/matches/ requires authentication"""
        response = self.client.get('/api/matches/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_matches_no_trips(self):
        """Test GET /api/matches/ returns 404 when user has no upcoming trips"""
        # Create user with no trips
        user_no_trips = User.objects.create_user(
            email='notrips@example.com',
            password='password123',
            display_name='No Trips',
            home_location='Boulder, CO',
            email_verified=True
        )

        self.client.force_authenticate(user=user_no_trips)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('No upcoming trips', response.data['detail'])

    def test_list_matches_success(self):
        """Test GET /api/matches/ returns matches for authenticated user"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trip', response.data)
        self.assertIn('matches', response.data)

        # Should have user2 as a match
        self.assertEqual(len(response.data['matches']), 1)
        self.assertEqual(response.data['matches'][0]['user']['id'], str(self.user2.id))
        self.assertGreater(response.data['matches'][0]['match_score'], 20)

    def test_list_matches_with_trip_param(self):
        """Test GET /api/matches/?trip=<uuid> returns matches for specific trip"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/matches/?trip={self.trip1.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trip']['id'], str(self.trip1.id))
        self.assertEqual(len(response.data['matches']), 1)

    def test_list_matches_with_invalid_trip(self):
        """Test GET /api/matches/?trip=<invalid> returns 404"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/?trip=00000000-0000-0000-0000-000000000000')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_matches_with_limit(self):
        """Test GET /api/matches/?limit=2 respects limit parameter"""
        # Create additional users
        for i in range(3):
            user = User.objects.create_user(
                email=f'limituser{i}@example.com',
                password='password123',
                display_name=f'Limit User {i}',
                home_location='Boulder, CO',
                email_verified=True,
                risk_tolerance=RiskTolerance.BALANCED
            )

            DisciplineProfile.objects.create(
                user=user,
                discipline=Discipline.SPORT,
                grade_system=GradeSystem.YDS,
                comfortable_grade_min_display='5.10a',
                comfortable_grade_max_display='5.10d',
                comfortable_grade_min_score=50,
                comfortable_grade_max_score=60
            )

            Trip.objects.create(
                user=user,
                destination=self.destination,
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=5),
                preferred_disciplines=['sport']
            )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/?limit=2')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['matches']), 2)

    def test_list_matches_excludes_blocked_users(self):
        """Test matches exclude users blocked by current user"""
        # user1 blocks user2
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['matches']), 0)

    def test_list_matches_excludes_users_who_blocked_me(self):
        """Test matches exclude users who blocked current user"""
        # user2 blocks user1
        Block.objects.create(blocker=self.user2, blocked=self.user1)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['matches']), 0)

    def test_match_detail_success(self):
        """Test GET /api/matches/<user_id>/detail/ returns detailed match info"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/matches/{self.user2.id}/detail/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], str(self.user2.id))
        self.assertIn('match_score', response.data)
        self.assertIn('reasons', response.data)
        self.assertIn('overlap_dates', response.data)

    def test_match_detail_not_found(self):
        """Test GET /api/matches/<invalid_user_id>/detail/ returns 404"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/00000000-0000-0000-0000-000000000000/detail/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_match_detail_unauthenticated(self):
        """Test GET /api/matches/<user_id>/detail/ requires authentication"""
        response = self.client.get(f'/api/matches/{self.user2.id}/detail/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_match_response_structure(self):
        """Test match response contains all required fields"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check trip structure
        trip = response.data['trip']
        self.assertIn('id', trip)
        self.assertIn('destination', trip)
        self.assertIn('start_date', trip)
        self.assertIn('end_date', trip)

        # Check match structure
        match = response.data['matches'][0]
        self.assertIn('user', match)
        self.assertIn('trip', match)
        self.assertIn('match_score', match)
        self.assertIn('reasons', match)
        self.assertIn('overlap_dates', match)

        # Check user structure
        user = match['user']
        self.assertIn('id', user)
        self.assertIn('display_name', user)
        self.assertIn('bio', user)
        self.assertIn('home_location', user)
        self.assertIn('risk_tolerance', user)
        self.assertIn('disciplines', user)

        # Check overlap_dates structure
        overlap = match['overlap_dates']
        self.assertIn('start', overlap)
        self.assertIn('end', overlap)
        self.assertIn('days', overlap)

    def test_match_score_calculation(self):
        """Test match score is calculated correctly"""
        # Add availability for higher score
        AvailabilityBlock.objects.create(
            trip=self.trip1,
            date=date.today() + timedelta(days=1),
            time_block=TimeBlock.MORNING
        )
        AvailabilityBlock.objects.create(
            trip=self.trip2,
            date=date.today() + timedelta(days=1),
            time_block=TimeBlock.MORNING
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        match = response.data['matches'][0]
        # Score should be:
        # - Location: 25 (same destination, no crags)
        # - Date: 20 (5 days overlap)
        # - Discipline: 20 (shared sport)
        # - Grade: ~13 (partial overlap)
        # - Risk: 10 (same)
        # - Availability: 1 (1 overlap)
        # Total: ~89
        self.assertGreater(match['match_score'], 70)
        self.assertIn('Both in Red River Gorge, KY', match['reasons'])

    def test_matches_sorted_by_score(self):
        """Test matches are returned sorted by score descending"""
        # Create user with higher compatibility
        user_high = User.objects.create_user(
            email='high@example.com',
            password='password123',
            display_name='High Match',
            home_location='Boulder, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        # Create user with lower compatibility (different risk tolerance)
        user_low = User.objects.create_user(
            email='low@example.com',
            password='password123',
            display_name='Low Match',
            home_location='Denver, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.AGGRESSIVE
        )

        # Create profiles for both
        for user in [user_high, user_low]:
            DisciplineProfile.objects.create(
                user=user,
                discipline=Discipline.SPORT,
                grade_system=GradeSystem.YDS,
                comfortable_grade_min_display='5.10a',
                comfortable_grade_max_display='5.10d',
                comfortable_grade_min_score=50,
                comfortable_grade_max_score=60
            )

            Trip.objects.create(
                user=user,
                destination=self.destination,
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=5),
                preferred_disciplines=['sport']
            )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify sorted by score
        matches = response.data['matches']
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(
                matches[i]['match_score'],
                matches[i + 1]['match_score']
            )
