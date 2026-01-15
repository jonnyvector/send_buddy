"""
WebSocket consumers for real-time messaging in climbing sessions.

Handles WebSocket connections for session chat, including:
- JWT authentication
- Room group management
- Message broadcasting
- Database persistence
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from asgiref.sync import sync_to_async
from .models import Session, Message
from users.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for session chat.

    Authentication:
        Expects JWT access token in query string: ?token=<access_token>

    Message format (client -> server):
        {
            "type": "message",
            "content": "Hello world"
        }

    Message format (server -> client):
        {
            "type": "message",
            "message_id": "uuid",
            "content": "Hello world",
            "sender_id": "user_uuid",
            "sender_name": "John Doe",
            "created_at": "2026-01-13T12:00:00Z"
        }

    Typing indicator (client -> server):
        {
            "type": "typing",
            "is_typing": true
        }

    Typing indicator (server -> client):
        {
            "type": "typing",
            "sender_id": "user_uuid",
            "sender_name": "John Doe",
            "is_typing": true
        }
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        - Authenticate user via JWT token
        - Verify user is participant in session
        - Join room group for session
        """
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'
        self.user = None

        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=', 1)[1]
                break

        if not token:
            await self.close(code=4001)  # No token provided
            return

        # Authenticate user
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            self.user = await self.get_user(user_id)

            if not self.user:
                await self.close(code=4002)  # User not found
                return

        except (TokenError, InvalidToken, KeyError):
            await self.close(code=4003)  # Invalid token
            return

        # Verify user is participant in session
        is_participant = await self.check_session_participant(self.session_id, self.user.id)
        if not is_participant:
            await self.close(code=4004)  # Not a participant
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnect.

        - Leave room group
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket.

        - Parse message data
        - Handle different message types (message, typing)
        - Save to database (for messages)
        - Broadcast to room group
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            else:
                # Unknown message type, ignore
                pass

        except json.JSONDecodeError:
            # Invalid JSON, ignore
            pass

    async def handle_message(self, data):
        """
        Handle chat message.

        - Validate content
        - Save to database
        - Update session's last_message_at
        - Broadcast to room group
        """
        content = data.get('content', '').strip()

        if not content or len(content) > 2000:
            return  # Invalid content

        # Save message to database
        message = await self.save_message(self.session_id, self.user.id, content)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'content': message.body,
                'sender_id': str(self.user.id),
                'sender_name': self.user.display_name,
                'created_at': message.created_at.isoformat(),
            }
        )

    async def handle_typing(self, data):
        """
        Handle typing indicator.

        - Broadcast typing status to room group
        """
        is_typing = data.get('is_typing', False)

        # Broadcast typing indicator to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'sender_id': str(self.user.id),
                'sender_name': self.user.display_name,
                'is_typing': is_typing,
            }
        )

    async def chat_message(self, event):
        """
        Receive chat message from room group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'created_at': event['created_at'],
        }))

    async def typing_indicator(self, event):
        """
        Receive typing indicator from room group and send to WebSocket.

        Note: Don't send typing indicator back to sender
        """
        if event['sender_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender_id': event['sender_id'],
                'sender_name': event['sender_name'],
                'is_typing': event['is_typing'],
            }))

    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def check_session_participant(self, session_id, user_id):
        """Check if user is a participant in the session."""
        try:
            session = Session.objects.get(id=session_id)
            return session.inviter_id == user_id or session.invitee_id == user_id
        except Session.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, session_id, sender_id, content):
        """
        Save message to database and update session's last_message_at.

        Returns the created Message instance.
        """
        session = Session.objects.get(id=session_id)
        message = Message.objects.create(
            session=session,
            sender_id=sender_id,
            body=content
        )

        # Update session's last_message_at
        session.last_message_at = timezone.now()
        session.save(update_fields=['last_message_at'])

        return message
