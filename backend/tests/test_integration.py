"""
Integration tests for complete user flows in Send Buddy.

These tests verify end-to-end functionality across multiple apps:
- User registration → verification → login → profile setup
- Trip creation → matching → session invitation → messaging → completion → feedback
- Block flow → verify exclusion from matches and sessions
- Report flow
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch
from users.models import User, DisciplineProfile, Block, Report, GradeConversion, Discipline, GradeSystem, RiskTolerance
from trips.models import Destination, Trip, AvailabilityBlock, TimeBlock
from climbing_sessions.models import Session, Message, Feedback, SessionStatus
from matching.services import MatchingService


class UserRegistrationAndLoginFlowTest(TestCase):
    """Test complete user registration and login flow"""

    @patch('users.serializers.send_verification_email')
    def test_complete_registration_login_flow(self, mock_send_email):
        """Test: Register → Verify Email → Login → Update Profile"""
        client = APIClient()

        # 1. Register
        register_url = reverse('register')
        register_data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'New User',
            'home_location': 'Boulder, CO'
        }
        response = client.post(register_url, register_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email='newuser@example.com')
        self.assertFalse(user.email_verified)

        # 2. Verify email (simulate)
        user.email_verified = True
        user.save()

        # 3. Login
        login_url = reverse('login')
        login_data = {
            'email': 'newuser@example.com',
            'password': 'password123'
        }
        response = client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        access_token = response.data['access']

        # 4. Update profile
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_url = reverse('current-user')
        profile_data = {
            'bio': 'I love climbing!',
            'risk_tolerance': RiskTolerance.BALANCED
        }
        response = client.patch(profile_url, profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertEqual(user.bio, 'I love climbing!')


class CompleteTripMatchingSessionFlowTest(TestCase):
    """Test complete flow from trip creation to session completion"""

    def setUp(self):
        """Set up test data"""
        # Create destination
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
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

    @patch('climbing_sessions.views.send_session_invitation')
    @patch('climbing_sessions.views.send_session_accepted')
    @patch('climbing_sessions.views.send_session_completed_reminder')
    def test_complete_trip_to_session_flow(self, mock_completed, mock_accepted, mock_invitation):
        """
        Test complete flow:
        1. Create two users with profiles
        2. Both create trips to same destination
        3. User1 gets matches
        4. User1 invites User2 to session
        5. User2 accepts
        6. They exchange messages
        7. Session completed
        8. Both submit feedback
        """
        client = APIClient()

        # 1. Create User 1
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        DisciplineProfile.objects.create(
            user=user1,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        # 2. Create User 2
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO',
            email_verified=True,
            risk_tolerance=RiskTolerance.BALANCED
        )

        DisciplineProfile.objects.create(
            user=user2,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        # 3. User1 creates trip
        client.force_authenticate(user=user1)
        trip_url = reverse('trip-list')
        trip_data = {
            'destination': 'red-river-gorge',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=5)),
            'preferred_disciplines': ['sport']
        }
        response = client.post(trip_url, trip_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        trip1 = Trip.objects.get(user=user1)

        # 4. User2 creates trip
        client.force_authenticate(user=user2)
        response = client.post(trip_url, trip_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        trip2 = Trip.objects.get(user=user2)

        # 5. User1 gets matches
        service = MatchingService(user1, trip1, limit=10)
        matches = service.get_matches()

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['user'], user2)
        self.assertGreater(matches[0]['match_score'], 20)

        # 6. User1 sends session invitation
        client.force_authenticate(user=user1)
        session_url = reverse('session-list')
        session_data = {
            'invitee': str(user2.id),
            'trip': str(trip1.id),
            'proposed_date': str(date.today()),
            'time_block': TimeBlock.MORNING,
            'crag': 'Muir Valley',
            'goal': 'Sport climbing'
        }
        response = client.post(session_url, session_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session = Session.objects.get(inviter=user1, invitee=user2)
        self.assertEqual(session.status, SessionStatus.PENDING)

        # 7. User2 accepts invitation
        client.force_authenticate(user=user2)
        accept_url = reverse('session-accept', kwargs={'pk': str(session.id)})
        response = client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.ACCEPTED)

        # 8. They exchange messages
        messages_url = reverse('session-messages', kwargs={'pk': str(session.id)})

        # User2 sends message
        response = client.post(messages_url, {'body': 'Looking forward to it!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User1 responds
        client.force_authenticate(user=user1)
        response = client.post(messages_url, {'body': 'Me too! See you there.'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(session.messages.count(), 2)

        # 9. Session completed
        complete_url = reverse('session-complete', kwargs={'pk': str(session.id)})
        response = client.post(complete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)

        # 10. Both submit feedback
        feedback_url = reverse('submit-feedback', kwargs={'session_id': str(session.id)})

        # User1 rates User2
        feedback_data = {
            'safety_rating': 5,
            'communication_rating': 5,
            'overall_rating': 5,
            'notes': 'Excellent partner!'
        }
        response = client.post(feedback_url, feedback_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User2 rates User1
        client.force_authenticate(user=user2)
        feedback_data = {
            'safety_rating': 5,
            'communication_rating': 4,
            'overall_rating': 5,
            'notes': 'Great climber!'
        }
        response = client.post(feedback_url, feedback_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Feedback.objects.filter(session=session).count(), 2)

        # 11. Verify feedback stats
        stats_url = reverse('feedback-stats')
        response = client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_ratings'], 1)


class BlockUserFlowTest(TestCase):
    """Test block flow and its effects"""

    def setUp(self):
        """Set up test data"""
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )

        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO',
            email_verified=True
        )

        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO',
            email_verified=True
        )

        DisciplineProfile.objects.create(
            user=self.user1,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10a',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=50
        )

        DisciplineProfile.objects.create(
            user=self.user2,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10a',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=50
        )

    def test_block_excludes_from_matches(self):
        """Test blocking excludes user from matches"""
        # Create trips for both users
        trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        # Before blocking - should get match
        service = MatchingService(self.user1, trip1)
        matches_before = service.get_matches()
        self.assertEqual(len(matches_before), 1)

        # Block user2
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        # After blocking - should not get match
        service = MatchingService(self.user1, trip1)
        matches_after = service.get_matches()
        self.assertEqual(len(matches_after), 0)

    @patch('climbing_sessions.views.send_session_cancelled')
    def test_block_cancels_pending_sessions(self, mock_send_email):
        """Test blocking cancels pending/accepted sessions"""
        client = APIClient()

        trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # Create pending session
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=trip1,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.PENDING
        )

        # Block user
        client.force_authenticate(user=self.user1)
        block_url = reverse('block-user', kwargs={'user_id': str(self.user2.id)})
        response = client.post(block_url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify session cancelled
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.CANCELLED)

    def test_cannot_create_session_with_blocked_user(self):
        """Test cannot create session with blocked user"""
        client = APIClient()

        trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # Block user2
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        # Try to create session
        client.force_authenticate(user=self.user1)
        session_url = reverse('session-list')
        session_data = {
            'invitee': str(self.user2.id),
            'trip': str(trip1.id),
            'proposed_date': str(date.today()),
            'time_block': TimeBlock.MORNING
        }
        response = client.post(session_url, session_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReportUserFlowTest(TestCase):
    """Test report flow"""

    @patch('users.views.mail_admins')
    def test_complete_report_flow(self, mock_mail_admins):
        """Test: Create session → Report user → Admin review"""
        client = APIClient()

        # Create users
        reporter = User.objects.create_user(
            email='reporter@example.com',
            password='password123',
            display_name='Reporter',
            home_location='Boulder, CO',
            email_verified=True
        )

        reported = User.objects.create_user(
            email='reported@example.com',
            password='password123',
            display_name='Reported',
            home_location='Denver, CO',
            email_verified=True
        )

        # Report user
        client.force_authenticate(user=reporter)
        report_url = reverse('report-user', kwargs={'user_id': str(reported.id)})
        report_data = {
            'reason': 'harassment',
            'details': 'User was harassing me during our climb session'
        }
        response = client.post(report_url, report_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify report created
        report = Report.objects.get(reporter=reporter, reported=reported)
        self.assertEqual(report.reason, 'harassment')
        self.assertEqual(report.status, 'open')

        # Verify admin notification sent
        mock_mail_admins.assert_called_once()

        # Admin updates status (simulated)
        report.status = 'investigating'
        report.admin_notes = 'Looking into this case'
        report.save()

        self.assertEqual(report.status, 'investigating')


class BilateralBlockingTest(TestCase):
    """Test bilateral blocking scenarios"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO',
            email_verified=True
        )

        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO',
            email_verified=True
        )

        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )

        DisciplineProfile.objects.create(
            user=self.user1,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10a',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=50
        )

        DisciplineProfile.objects.create(
            user=self.user2,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10a',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=50
        )

    def test_bilateral_blocking_excludes_both_ways(self):
        """Test if user2 blocks user1, user1 also cannot see user2"""
        trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport']
        )

        # user2 blocks user1
        Block.objects.create(blocker=self.user2, blocked=self.user1)

        # user1 should not see user2 in matches
        service = MatchingService(self.user1, trip1)
        matches = service.get_matches()
        self.assertEqual(len(matches), 0)

        # user2 should not see user1 in matches
        service = MatchingService(self.user2, trip2)
        matches = service.get_matches()
        self.assertEqual(len(matches), 0)
