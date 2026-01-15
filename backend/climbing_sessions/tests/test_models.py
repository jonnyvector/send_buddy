from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, timedelta
from users.models import User
from trips.models import Destination, Trip, TimeBlock
from climbing_sessions.models import Session, Message, Feedback, SessionStatus


class SessionModelTest(TestCase):
    """Test Session model"""

    def setUp(self):
        self.inviter = User.objects.create_user(
            email='inviter@example.com',
            password='password123',
            display_name='Inviter',
            home_location='Boulder, CO'
        )
        self.invitee = User.objects.create_user(
            email='invitee@example.com',
            password='password123',
            display_name='Invitee',
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
            user=self.inviter,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

    def test_create_session(self):
        """Test creating a session"""
        session = Session.objects.create(
            inviter=self.inviter,
            invitee=self.invitee,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )
        self.assertEqual(session.inviter, self.inviter)
        self.assertEqual(session.invitee, self.invitee)
        self.assertEqual(session.status, SessionStatus.PENDING)

    def test_session_default_status_pending(self):
        """Test session defaults to pending status"""
        session = Session.objects.create(
            inviter=self.inviter,
            invitee=self.invitee,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )
        self.assertEqual(session.status, SessionStatus.PENDING)

    def test_session_status_transitions(self):
        """Test session status can transition"""
        session = Session.objects.create(
            inviter=self.inviter,
            invitee=self.invitee,
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )

        # Accept
        session.status = SessionStatus.ACCEPTED
        session.save()
        self.assertEqual(session.status, SessionStatus.ACCEPTED)

        # Complete
        session.status = SessionStatus.COMPLETED
        session.save()
        self.assertEqual(session.status, SessionStatus.COMPLETED)

    def test_cannot_invite_self(self):
        """Test user cannot invite themselves"""
        session = Session(
            inviter=self.inviter,
            invitee=self.inviter,  # Same user
            trip=self.trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )
        with self.assertRaises(ValidationError):
            session.clean()

    def test_trip_must_belong_to_inviter(self):
        """Test trip must belong to inviter"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='password123',
            display_name='Other',
            home_location='Austin, TX'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        session = Session(
            inviter=self.inviter,
            invitee=self.invitee,
            trip=other_trip,  # Doesn't belong to inviter
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING
        )
        with self.assertRaises(ValidationError):
            session.clean()

    def test_proposed_date_within_trip_dates(self):
        """Test proposed_date must be within trip dates"""
        session = Session(
            inviter=self.inviter,
            invitee=self.invitee,
            trip=self.trip,
            proposed_date=date.today() + timedelta(days=10),  # After trip end
            time_block=TimeBlock.MORNING
        )
        with self.assertRaises(ValidationError):
            session.clean()


class MessageModelTest(TestCase):
    """Test Message model"""

    def setUp(self):
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
            time_block=TimeBlock.MORNING
        )

    def test_create_message(self):
        """Test creating a message"""
        message = Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='Hey, looking forward to climbing!'
        )
        self.assertEqual(message.session, self.session)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.body, 'Hey, looking forward to climbing!')

    def test_message_ordering(self):
        """Test messages are ordered by created_at"""
        msg1 = Message.objects.create(
            session=self.session,
            sender=self.user1,
            body='First message'
        )
        msg2 = Message.objects.create(
            session=self.session,
            sender=self.user2,
            body='Second message'
        )

        messages = list(self.session.messages.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)


class FeedbackModelTest(TestCase):
    """Test Feedback model"""

    def setUp(self):
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

    def test_create_feedback(self):
        """Test creating feedback"""
        feedback = Feedback.objects.create(
            session=self.session,
            rater=self.user1,
            ratee=self.user2,
            safety_rating=5,
            communication_rating=4,
            overall_rating=5,
            notes='Great climbing partner!'
        )
        self.assertEqual(feedback.rater, self.user1)
        self.assertEqual(feedback.ratee, self.user2)
        self.assertEqual(feedback.safety_rating, 5)

    def test_feedback_unique_per_session_rater_ratee(self):
        """Test cannot submit duplicate feedback"""
        Feedback.objects.create(
            session=self.session,
            rater=self.user1,
            ratee=self.user2,
            safety_rating=5,
            communication_rating=4,
            overall_rating=5
        )

        with self.assertRaises(IntegrityError):
            Feedback.objects.create(
                session=self.session,
                rater=self.user1,
                ratee=self.user2,  # Duplicate
                safety_rating=4,
                communication_rating=3,
                overall_rating=4
            )

    def test_both_users_can_leave_feedback(self):
        """Test both users can leave feedback for the same session"""
        Feedback.objects.create(
            session=self.session,
            rater=self.user1,
            ratee=self.user2,
            safety_rating=5,
            communication_rating=4,
            overall_rating=5
        )

        Feedback.objects.create(
            session=self.session,
            rater=self.user2,
            ratee=self.user1,
            safety_rating=4,
            communication_rating=5,
            overall_rating=4
        )

        self.assertEqual(Feedback.objects.filter(session=self.session).count(), 2)

    def test_rating_validation(self):
        """Test ratings must be 1-5"""
        # This is enforced by validators on the model
        feedback = Feedback(
            session=self.session,
            rater=self.user1,
            ratee=self.user2,
            safety_rating=6,  # Invalid
            communication_rating=4,
            overall_rating=5
        )

        with self.assertRaises(ValidationError):
            feedback.full_clean()
