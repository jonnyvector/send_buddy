from django.test import TestCase
from datetime import date, timedelta
from users.models import User, DisciplineProfile, Block, GradeConversion, Discipline, GradeSystem, RiskTolerance
from trips.models import Destination, Crag, Trip, AvailabilityBlock, TimeBlock
from matching.services import MatchingService


class MatchingServiceTest(TestCase):
    """Test MatchingService - CRITICAL for matching algorithm"""

    def setUp(self):
        """Create test data"""
        # Create destination
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        self.other_destination = Destination.objects.create(
            slug='yosemite',
            name='Yosemite, CA',
            country='USA',
            lat=37.8,
            lng=-119.5
        )

        # Create crags for Red River Gorge
        self.muir_valley = Crag.objects.create(
            destination=self.destination,
            name='Muir Valley',
            slug='muir-valley',
            disciplines=['sport']
        )

        self.pmrp = Crag.objects.create(
            destination=self.destination,
            name='Pendergrass-Murray Recreational Preserve',
            slug='pmrp',
            disciplines=['sport', 'trad']
        )

        self.motherlode = Crag.objects.create(
            destination=self.destination,
            name='The Motherlode',
            slug='motherlode',
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

        self.user3 = User.objects.create_user(
            email='user3@example.com',
            password='password123',
            display_name='User 3',
            home_location='Austin, TX',
            email_verified=True,
            risk_tolerance=RiskTolerance.AGGRESSIVE
        )

        # Create discipline profiles for user1 and user2
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
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

    def test_get_candidates_excludes_blocked_users(self):
        """Test _get_candidates excludes users blocked by me"""
        # user2 creates trip
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # user1 blocks user2
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        # Get matches for user1
        service = MatchingService(self.user1, self.trip1)
        candidates = service._get_candidates()

        # user2 should be excluded
        self.assertNotIn(self.user2, candidates)

    def test_get_candidates_excludes_users_who_blocked_me(self):
        """Test _get_candidates excludes users who blocked me"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # user2 blocks user1
        Block.objects.create(blocker=self.user2, blocked=self.user1)

        service = MatchingService(self.user1, self.trip1)
        candidates = service._get_candidates()

        # user2 should be excluded
        self.assertNotIn(self.user2, candidates)

    def test_get_candidates_requires_same_destination(self):
        """Test candidates must have trip to same destination"""
        # user2 trip to different destination
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.other_destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        candidate_trip = service._get_candidate_trip(self.user2)

        # Should return None (no matching trip)
        self.assertIsNone(candidate_trip)

    def test_score_location_same_destination(self):
        """Test _score_location awards 25 points for same destination (no crags specified)"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        # Changed from 30 to 25 because no crags are specified
        self.assertEqual(score, 25)

    def test_score_location_different_destination(self):
        """Test _score_location awards 0 points for different destination"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.other_destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        self.assertEqual(score, 0)

    def test_score_location_same_destination_same_crags(self):
        """Test _score_location awards 30 points for same destination + overlapping crags"""
        # Add Muir Valley to user1's trip
        self.trip1.preferred_crags.add(self.muir_valley)

        # Create trip2 with same crag
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )
        trip2.preferred_crags.add(self.muir_valley)

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        self.assertEqual(score, 30)

    def test_score_location_same_destination_different_crags(self):
        """Test _score_location awards 20 points for same destination + different crags"""
        # Add Muir Valley to user1's trip
        self.trip1.preferred_crags.add(self.muir_valley)

        # Create trip2 with different crag (PMRP)
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )
        trip2.preferred_crags.add(self.pmrp)

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        self.assertEqual(score, 20)

    def test_score_location_same_destination_no_crag_preference(self):
        """Test _score_location awards 25 points when both have no crag preference"""
        # Neither trip has crags specified
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        self.assertEqual(score, 25)

    def test_score_location_same_destination_one_has_crags(self):
        """Test _score_location awards 25 points when only one trip has crag preference"""
        # Add Muir Valley to user1's trip only
        self.trip1.preferred_crags.add(self.muir_valley)

        # trip2 has no crag preference
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        self.assertEqual(score, 25)

    def test_score_location_same_destination_partial_crag_overlap(self):
        """Test _score_location awards 30 points for partial crag overlap"""
        # user1 wants Muir Valley and PMRP
        self.trip1.preferred_crags.add(self.muir_valley, self.pmrp)

        # user2 wants Muir Valley and Motherlode (overlap on Muir Valley)
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )
        trip2.preferred_crags.add(self.muir_valley, self.motherlode)

        service = MatchingService(self.user1, self.trip1)
        score = service._score_location(trip2)

        # Should be 30 because there is overlap (Muir Valley)
        self.assertEqual(score, 30)

    def test_score_date_overlap_full_overlap(self):
        """Test _score_date_overlap with full date overlap"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        score, details = service._score_date_overlap(trip2)

        # 6 days overlap * 4 = 24, max 20
        self.assertEqual(score, 20)
        self.assertEqual(details['days'], 6)

    def test_score_date_overlap_partial_overlap(self):
        """Test _score_date_overlap with partial overlap"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=8)
        )

        service = MatchingService(self.user1, self.trip1)
        score, details = service._score_date_overlap(trip2)

        # 3 days overlap (days 3, 4, 5) * 4 = 12
        self.assertEqual(score, 12)
        self.assertEqual(details['days'], 3)

    def test_score_date_overlap_no_overlap(self):
        """Test _score_date_overlap with no overlap"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15)
        )

        service = MatchingService(self.user1, self.trip1)
        score, details = service._score_date_overlap(trip2)

        self.assertEqual(score, 0)
        self.assertEqual(details, {})

    def test_score_discipline_shared_discipline(self):
        """Test _score_discipline awards 20 points for shared discipline"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        service = MatchingService(self.user1, self.trip1)
        score, shared = service._score_discipline(self.user2, trip2)

        self.assertEqual(score, 20)
        self.assertIn('sport', shared)

    def test_score_discipline_no_shared_discipline(self):
        """Test _score_discipline with no shared discipline"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['bouldering']
        )

        service = MatchingService(self.user1, self.trip1)
        score, shared = service._score_discipline(self.user2, trip2)

        self.assertEqual(score, 0)
        self.assertEqual(shared, [])

    def test_score_grade_compatibility_full_overlap(self):
        """Test _score_grade_compatibility with full overlap"""
        # user1: 5.10a-5.10d (50-60)
        # user2: 5.10a-5.11c (50-70)
        # Overlap: 50-60 (10 points range)

        service = MatchingService(self.user1, self.trip1)
        score = service._score_grade_compatibility(self.user2, ['sport'])

        # Full overlap should give score of at least 10
        self.assertGreaterEqual(score, 10)

    def test_score_grade_compatibility_no_overlap(self):
        """Test _score_grade_compatibility with no overlap"""
        # Create user with non-overlapping grades
        user_advanced = User.objects.create_user(
            email='advanced@example.com',
            password='password123',
            display_name='Advanced',
            home_location='Boulder, CO',
            email_verified=True
        )

        # Create advanced grade
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=90,
            yds_grade='5.13a',
            french_grade='7c+'
        )

        DisciplineProfile.objects.create(
            user=user_advanced,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.13a',
            comfortable_grade_max_display='5.13a',
            comfortable_grade_min_score=90,
            comfortable_grade_max_score=90
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_grade_compatibility(user_advanced, ['sport'])

        self.assertEqual(score, 0)

    def test_score_risk_tolerance_same(self):
        """Test _score_risk_tolerance awards 10 points for same tolerance"""
        service = MatchingService(self.user1, self.trip1)
        score = service._score_risk_tolerance(self.user2)

        self.assertEqual(score, 10)

    def test_score_risk_tolerance_different_by_one(self):
        """Test _score_risk_tolerance awards 3 points for 1 step difference"""
        # user1: balanced, user3: aggressive (diff = 1)
        service = MatchingService(self.user1, self.trip1)
        score = service._score_risk_tolerance(self.user3)

        self.assertEqual(score, 3)

    def test_score_risk_tolerance_different_by_two(self):
        """Test _score_risk_tolerance awards -10 points for 2 step difference"""
        user_conservative = User.objects.create_user(
            email='conservative@example.com',
            password='password123',
            display_name='Conservative',
            home_location='Boulder, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.CONSERVATIVE
        )

        # user3: aggressive, user_conservative: conservative (diff = 2)
        service = MatchingService(self.user3, self.trip1)
        score = service._score_risk_tolerance(user_conservative)

        self.assertEqual(score, -10)

    def test_score_availability_with_overlap(self):
        """Test _score_availability with overlapping availability"""
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # Add matching availability
        AvailabilityBlock.objects.create(
            trip=self.trip1,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )
        AvailabilityBlock.objects.create(
            trip=self.trip1,
            date=date.today() + timedelta(days=1),
            time_block=TimeBlock.AFTERNOON
        )

        AvailabilityBlock.objects.create(
            trip=trip2,
            date=date.today(),
            time_block=TimeBlock.MORNING  # Matches
        )
        AvailabilityBlock.objects.create(
            trip=trip2,
            date=date.today() + timedelta(days=2),
            time_block=TimeBlock.MORNING  # No match
        )

        service = MatchingService(self.user1, self.trip1)
        score = service._score_availability(trip2)

        # 1 overlapping availability
        self.assertEqual(score, 1)

    def test_full_matching_algorithm(self):
        """Test complete matching algorithm with mock data"""
        # Create complete profile for user2
        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        # Add availability
        AvailabilityBlock.objects.create(
            trip=self.trip1,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )
        AvailabilityBlock.objects.create(
            trip=trip2,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )

        # Get matches
        service = MatchingService(self.user1, self.trip1, limit=10)
        matches = service.get_matches()

        # Should have user2 as a match
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['user'], self.user2)
        self.assertGreater(matches[0]['match_score'], 20)  # Above minimum threshold

        # Verify scoring components
        self.assertIn('reasons', matches[0])
        self.assertIn('overlap_dates', matches[0])

    def test_matching_excludes_low_scores(self):
        """Test matching excludes candidates below minimum threshold"""
        # Create user3 with different destination (0 location score)
        trip3 = Trip.objects.create(
            user=self.user3,
            destination=self.other_destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        service = MatchingService(self.user1, self.trip1)
        matches = service.get_matches()

        # user3 should not be in matches (low score)
        user_ids = [match['user'].id for match in matches]
        self.assertNotIn(self.user3.id, user_ids)

    def test_matching_sorts_by_score(self):
        """Test matches are sorted by score descending"""
        # Create multiple users with different scores
        user_perfect = User.objects.create_user(
            email='perfect@example.com',
            password='password123',
            display_name='Perfect Match',
            home_location='Boulder, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        user_good = User.objects.create_user(
            email='good@example.com',
            password='password123',
            display_name='Good Match',
            home_location='Denver, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.AGGRESSIVE
        )

        # Create profiles
        DisciplineProfile.objects.create(
            user=user_perfect,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        DisciplineProfile.objects.create(
            user=user_good,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.11c',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=70
        )

        # Create trips
        trip_perfect = Trip.objects.create(
            user=user_perfect,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        trip_good = Trip.objects.create(
            user=user_good,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        # Get matches
        service = MatchingService(self.user1, self.trip1)
        matches = service.get_matches()

        # Verify sorted by score
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(
                matches[i]['match_score'],
                matches[i + 1]['match_score']
            )

    def test_matching_respects_limit(self):
        """Test matching respects the limit parameter"""
        # Create 5 potential matches
        for i in range(5):
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
                start_date=date.today(),
                end_date=date.today() + timedelta(days=5),
                preferred_disciplines=['sport']
            )

        # Request only 3 matches
        service = MatchingService(self.user1, self.trip1, limit=3)
        matches = service.get_matches()

        self.assertLessEqual(len(matches), 3)
