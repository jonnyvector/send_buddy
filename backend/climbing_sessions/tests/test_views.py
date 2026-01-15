from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch
from users.models import User, Block
from trips.models import Destination, Trip, TimeBlock
from climbing_sessions.models import Session, Message, Feedback, SessionStatus


class SessionViewSetTest(TestCase):
    """Test session endpoints"""

    def setUp(self):
        self.client = APIClient()
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

        self.trip = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

    @patch('climbing_sessions.views.send_session_invitation')
    def test_create_session(self, mock_send_email):
        """Test creating a session (sending invitation)"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('session-list')
        data = {
            'invitee': str(self.user2.id),
            'trip': str(self.trip.id),
            'proposed_date': str(date.today()),
            'time_block': TimeBlock.MORNING,
            'crag': 'Muir Valley',
            'goal': 'Sport climbing 5.10s'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Session.objects.filter(inviter=self.user1).count(), 1)

        session = Session.objects.get(inviter=self.user1)
        self.assertEqual(session.invitee, self.user2)
        self.assertEqual(session.status, SessionStatus.PENDING)

    def test_create_session_blocked_user_rejected(self):
        """Test cannot create session with blocked user"""
        self.client.force_authenticate(user=self.user1)

        # user1 blocks user2
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        url = reverse('session-list')
        data = {
            'invitee': str(self.user2.id),
            'trip': str(self.trip.id),
            'proposed_date': str(date.today()),
            'time_block': TimeBlock.MORNING
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('climbing_sessions.views.send_session_accepted')
    def test_accept_session(self, mock_send_email):
        """Test accepting a session invitation"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.PENDING
        )

        self.client.force_authenticate(user=self.user2)
        url = reverse('session-accept', kwargs={'pk': str(session.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.ACCEPTED)

    def test_only_invitee_can_accept(self):
        """Test only invitee can accept session"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.PENDING
        )

        # Try to accept as inviter
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-accept', kwargs={'pk': str(session.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_only_accept_pending_sessions(self):
        """Test can only accept pending sessions"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.DECLINED
        )

        self.client.force_authenticate(user=self.user2)
        url = reverse('session-accept', kwargs={'pk': str(session.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decline_session(self):
        """Test declining a session invitation"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.PENDING
        )

        self.client.force_authenticate(user=self.user2)
        url = reverse('session-decline', kwargs={'pk': str(session.id)})
        data = {'message': 'Sorry, not available that day'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.DECLINED)

        # Verify message was created
        self.assertTrue(session.messages.filter(sender=self.user2).exists())

    @patch('climbing_sessions.views.send_session_cancelled')
    def test_cancel_session(self, mock_send_email):
        """Test cancelling a session"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-cancel', kwargs={'pk': str(session.id)})
        data = {'reason': 'Weather looks bad'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.CANCELLED)

    def test_either_party_can_cancel(self):
        """Test either inviter or invitee can cancel session"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        # Invitee cancels
        self.client.force_authenticate(user=self.user2)
        url = reverse('session-cancel', kwargs={'pk': str(session.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('climbing_sessions.views.send_session_completed_reminder')
    def test_complete_session(self, mock_send_email):
        """Test marking session as completed"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-complete', kwargs={'pk': str(session.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)

    def test_list_sessions(self):
        """Test listing user's sessions"""
        Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )

        trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        Session.objects.create(
            inviter=self.user2,
            invitee=self.user1,
            trip=trip2,
            proposed_date=date.today(),
            time_block=TimeBlock.AFTERNOON
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_sessions_by_status(self):
        """Test filtering sessions by status"""
        Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.PENDING
        )

        Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today() + timedelta(days=1),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url, {'status': 'pending'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_send_message(self):
        """Test sending a message in a session"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-messages', kwargs={'pk': str(session.id)})
        data = {'body': 'Hey, what time should we meet?'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(session.messages.count(), 1)

        message = session.messages.first()
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.body, 'Hey, what time should we meet?')

    def test_get_messages(self):
        """Test getting messages from a session"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

        Message.objects.create(
            session=session,
            sender=self.user1,
            body='First message'
        )
        Message.objects.create(
            session=session,
            sender=self.user2,
            body='Second message'
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-messages', kwargs={'pk': str(session.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_cannot_message_completed_session(self):
        """Test cannot send messages to completed sessions"""
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.COMPLETED
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('session-messages', kwargs={'pk': str(session.id)})
        data = {'body': 'Test message'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FeedbackViewTest(TestCase):
    """Test feedback endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO'
        )

        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        self.session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.COMPLETED
        )

    def test_submit_feedback(self):
        """Test submitting feedback"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('submit-feedback', kwargs={'session_id': str(self.session.id)})
        data = {
            'safety_rating': 5,
            'communication_rating': 4,
            'overall_rating': 5,
            'notes': 'Great climbing partner!'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Feedback.objects.filter(
                session=self.session,
                rater=self.user1,
                ratee=self.user2
            ).exists()
        )

    def test_cannot_submit_duplicate_feedback(self):
        """Test cannot submit feedback twice"""
        Feedback.objects.create(
            session=self.session,
            rater=self.user1,
            ratee=self.user2,
            safety_rating=5,
            communication_rating=4,
            overall_rating=5
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('submit-feedback', kwargs={'session_id': str(self.session.id)})
        data = {
            'safety_rating': 4,
            'communication_rating': 3,
            'overall_rating': 4
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_both_users_can_submit_feedback(self):
        """Test both participants can submit feedback"""
        # user1 submits
        self.client.force_authenticate(user=self.user1)
        url = reverse('submit-feedback', kwargs={'session_id': str(self.session.id)})
        data = {
            'safety_rating': 5,
            'communication_rating': 4,
            'overall_rating': 5
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # user2 submits
        self.client.force_authenticate(user=self.user2)
        data = {
            'safety_rating': 4,
            'communication_rating': 5,
            'overall_rating': 4
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Feedback.objects.filter(session=self.session).count(), 2)

    def test_non_participant_cannot_submit_feedback(self):
        """Test non-participants cannot submit feedback"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='password123',
            display_name='Other',
            home_location='Austin, TX'
        )

        self.client.force_authenticate(user=other_user)
        url = reverse('submit-feedback', kwargs={'session_id': str(self.session.id)})
        data = {
            'safety_rating': 5,
            'communication_rating': 4,
            'overall_rating': 5
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_feedback_stats(self):
        """Test getting aggregated feedback stats"""
        # Create multiple feedbacks for user2
        for i in range(3):
            other_user = User.objects.create_user(
                email=f'other{i}@example.com',
                password='password123',
                display_name=f'Other {i}',
                home_location='Boulder, CO'
            )

            other_trip = Trip.objects.create(
                user=other_user,
                destination=self.destination,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=3)
            )

            other_session = Session.objects.create(
                inviter=other_user,
                invitee=self.user2,
                trip=other_trip,
                proposed_date=date.today(),
                time_block=TimeBlock.MORNING,
                status=SessionStatus.COMPLETED
            )

            Feedback.objects.create(
                session=other_session,
                rater=other_user,
                ratee=self.user2,
                safety_rating=5,
                communication_rating=4,
                overall_rating=5
            )

        self.client.force_authenticate(user=self.user2)
        url = reverse('feedback-stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_ratings'], 3)
        self.assertGreater(response.data['average_overall'], 0)

    def test_feedback_stats_empty(self):
        """Test feedback stats with no feedback"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('feedback-stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_ratings'], 0)
        self.assertEqual(response.data['average_overall'], 0.0)


class SessionUnreadCountTestCase(TestCase):
    """Test session unread_count field in SessionListSerializer"""

    def setUp(self):
        self.client = APIClient()

        # Create users
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

        # Create destination and trip
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # Create session
        self.session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.ACCEPTED
        )

    def test_unread_count_zero_when_no_messages(self):
        """Test unread_count is 0 when no messages exist"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 0)

    def test_unread_count_zero_when_all_from_current_user(self):
        """Test unread_count is 0 when all messages are from current user"""
        # user1 sends 3 messages
        Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Message 1 from user1'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Message 2 from user1'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Message 3 from user1'
        )

        # When user1 views sessions, unread_count should be 0 (all are their own)
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 0)

    def test_unread_count_accurate_from_other_party(self):
        """Test unread_count is accurate when messages are from other party"""
        # user2 sends 2 messages
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Message 1 from user2'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Message 2 from user2'
        )

        # When user1 views sessions, unread_count should be 2
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 2)

    def test_unread_count_mixed_messages(self):
        """Test unread_count with messages from both parties"""
        # user1 sends 1 message
        Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Message from user1'
        )

        # user2 sends 3 messages
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Message 1 from user2'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Message 2 from user2'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Message 3 from user2'
        )

        # When user1 views, should see 3 unread (from user2)
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 3)

        # When user2 views, should see 1 unread (from user1)
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 1)

    def test_unread_count_updates_when_new_message_added(self):
        """Test unread_count updates when new message is added"""
        self.client.force_authenticate(user=self.user1)

        # Initially no messages
        url = reverse('session-list')
        response = self.client.get(url)
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 0)

        # user2 sends a message
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='New message from user2'
        )

        # Now unread_count should be 1
        response = self.client.get(url)
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 1)

        # user2 sends another message
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Another message from user2'
        )

        # Now unread_count should be 2
        response = self.client.get(url)
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 2)

    def test_unread_count_correct_for_both_perspectives(self):
        """Test unread_count is correct for both inviter and invitee perspectives"""
        # Create a conversation
        Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Hello from user1'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Hi from user2'
        )
        Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Another from user2'
        )

        # user1 perspective (inviter): should see 2 unread from user2
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 2)

        # user2 perspective (invitee): should see 1 unread from user1
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]
        self.assertEqual(session_data['unread_count'], 1)

    def test_unread_count_field_included_in_list_response(self):
        """Test unread_count field is included in GET /api/sessions/ response"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Find the specific session we created in setUp
        session_data = [s for s in response.data if s['id'] == str(self.session.id)][0]

        # Verify unread_count field exists
        self.assertIn('unread_count', session_data)
        self.assertIsInstance(session_data['unread_count'], int)
