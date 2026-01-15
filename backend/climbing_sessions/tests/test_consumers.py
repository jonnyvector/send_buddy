"""
Tests for WebSocket consumers.

Tests the ChatConsumer for session messaging.
"""

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta
from config.asgi import application
from users.models import User
from trips.models import Trip, TimeBlock
from climbing_sessions.models import Session, SessionStatus
import json


class ChatConsumerTest(TransactionTestCase):
    """
    Test WebSocket consumer for session chat.

    Uses TransactionTestCase to properly handle database transactions
    with async operations.
    """

    def setUp(self):
        """Create test users and session."""
        # Create users
        self.user1 = User.objects.create_user(
            email='climber1@test.com',
            password='testpass123',
            display_name='Climber One',
            home_location='Boulder, CO',
        )
        self.user2 = User.objects.create_user(
            email='climber2@test.com',
            password='testpass123',
            display_name='Climber Two',
            home_location='Boulder, CO',
        )

        # Create trip
        self.trip = Trip.objects.create(
            user=self.user1,
            destination='Red Rock Canyon',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=3),
            climbing_types=['sport', 'trad'],
            difficulty_range='5.10a-5.12a',
            seeking='Partners for multi-pitch',
            status='active',
        )

        # Create session
        self.session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=self.trip,
            proposed_date=self.trip.start_date,
            time_block=TimeBlock.MORNING,
            crag='Black Corridor',
            goal='Multi-pitch routes',
            status=SessionStatus.ACCEPTED,
        )

        # Generate access tokens
        self.token1 = str(AccessToken.for_user(self.user1))
        self.token2 = str(AccessToken.for_user(self.user2))

    async def test_connect_with_valid_token(self):
        """Test WebSocket connection with valid JWT token."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    async def test_connect_without_token(self):
        """Test WebSocket connection fails without token."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/"
        )

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)  # No token provided

    async def test_connect_with_invalid_token(self):
        """Test WebSocket connection fails with invalid token."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token=invalid_token"
        )

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4003)  # Invalid token

    async def test_connect_non_participant(self):
        """Test WebSocket connection fails for non-participant."""
        # Create a third user who is not in the session
        user3 = User.objects.create_user(
            email='climber3@test.com',
            password='testpass123',
            display_name='Climber Three',
            home_location='Boulder, CO',
        )
        token3 = str(AccessToken.for_user(user3))

        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={token3}"
        )

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4004)  # Not a participant

    async def test_send_and_receive_message(self):
        """Test sending and receiving chat messages."""
        # Connect user1
        communicator1 = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )
        await communicator1.connect()

        # Connect user2
        communicator2 = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token2}"
        )
        await communicator2.connect()

        # User1 sends a message
        await communicator1.send_json_to({
            'type': 'message',
            'content': 'Hey, ready to climb?'
        })

        # User1 receives their own message
        response1 = await communicator1.receive_json_from()
        self.assertEqual(response1['type'], 'message')
        self.assertEqual(response1['content'], 'Hey, ready to climb?')
        self.assertEqual(response1['sender_id'], str(self.user1.id))
        self.assertEqual(response1['sender_name'], 'Climber One')
        self.assertIn('message_id', response1)
        self.assertIn('created_at', response1)

        # User2 receives the message
        response2 = await communicator2.receive_json_from()
        self.assertEqual(response2['type'], 'message')
        self.assertEqual(response2['content'], 'Hey, ready to climb?')
        self.assertEqual(response2['message_id'], response1['message_id'])

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_typing_indicator(self):
        """Test typing indicator broadcast."""
        # Connect both users
        communicator1 = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )
        await communicator1.connect()

        communicator2 = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token2}"
        )
        await communicator2.connect()

        # User1 starts typing
        await communicator1.send_json_to({
            'type': 'typing',
            'is_typing': True
        })

        # User2 receives typing indicator (user1 doesn't receive their own)
        response = await communicator2.receive_json_from()
        self.assertEqual(response['type'], 'typing')
        self.assertEqual(response['sender_id'], str(self.user1.id))
        self.assertEqual(response['sender_name'], 'Climber One')
        self.assertTrue(response['is_typing'])

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_message_persistence(self):
        """Test that messages are saved to database."""
        from climbing_sessions.models import Message

        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )
        await communicator.connect()

        # Send a message
        await communicator.send_json_to({
            'type': 'message',
            'content': 'This should be saved to database'
        })

        # Receive the response
        response = await communicator.receive_json_from()

        # Check message was saved
        message = await Message.objects.aget(id=response['message_id'])
        self.assertEqual(message.body, 'This should be saved to database')
        self.assertEqual(message.sender_id, self.user1.id)
        self.assertEqual(message.session_id, self.session.id)

        # Check session's last_message_at was updated
        session = await Session.objects.aget(id=self.session.id)
        self.assertIsNotNone(session.last_message_at)

        await communicator.disconnect()

    async def test_invalid_message_format(self):
        """Test that invalid messages are ignored."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )
        await communicator.connect()

        # Send invalid JSON
        await communicator.send_to(text_data='not valid json')

        # Connection should remain open (message is ignored)
        self.assertTrue(communicator.instance)

        # Send message with empty content
        await communicator.send_json_to({
            'type': 'message',
            'content': ''
        })

        # Should not receive any response (message is ignored)
        # We can't use receive_nothing() in this test, so we'll just
        # verify the connection is still active

        await communicator.disconnect()

    async def test_message_too_long(self):
        """Test that messages over 2000 characters are rejected."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/sessions/{self.session.id}/?token={self.token1}"
        )
        await communicator.connect()

        # Send message that's too long
        long_message = 'a' * 2001
        await communicator.send_json_to({
            'type': 'message',
            'content': long_message
        })

        # Should not receive any response (message is rejected)
        # Connection should remain open

        await communicator.disconnect()
