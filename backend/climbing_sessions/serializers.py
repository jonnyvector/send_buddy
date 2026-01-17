from rest_framework import serializers
from .models import Session, Message, SessionStatus, Feedback
from trips.models import Trip, TimeBlock
from users.models import User, Block
from users.serializers import UserSerializer
from trips.serializers import TripSerializer
from django.db import IntegrityError
from django.db.models import Q


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'session', 'sender', 'body', 'created_at']
        read_only_fields = ['id', 'session', 'sender', 'created_at']


class SessionSerializer(serializers.ModelSerializer):
    inviter = UserSerializer(read_only=True)
    invitee = UserSerializer(read_only=True)
    trip = TripSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'inviter', 'invitee', 'trip', 'proposed_date',
            'time_block', 'crag', 'goal', 'status', 'created_at',
            'updated_at', 'last_message_at', 'messages'
        ]
        read_only_fields = ['id', 'inviter', 'status', 'created_at', 'updated_at', 'last_message_at']


class SessionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view (no messages)"""
    inviter = UserSerializer(read_only=True)
    invitee = UserSerializer(read_only=True)
    trip = TripSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'inviter', 'invitee', 'trip', 'proposed_date',
            'time_block', 'crag', 'goal', 'status', 'created_at',
            'updated_at', 'last_message_at', 'unread_count'
        ]
        read_only_fields = ['id', 'inviter', 'status', 'created_at', 'updated_at', 'last_message_at']

    def get_unread_count(self, obj):
        """
        Count messages in this session that were NOT sent by the current user.
        This is a simplified approach - assumes all messages from other party are unread.
        """
        request = self.context.get('request')
        if not request or not request.user:
            return 0

        # Count messages sent by the other party (not by current user)
        return obj.messages.exclude(sender=request.user).count()


class CreateSessionSerializer(serializers.Serializer):
    invitee_id = serializers.UUIDField()
    trip_id = serializers.UUIDField()
    proposed_date = serializers.DateField()
    time_block = serializers.ChoiceField(choices=TimeBlock.choices)
    crag = serializers.CharField(max_length=200, required=False, allow_blank=True)
    goal = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, data):
        user = self.context['request'].user

        # Check if invitee exists and is visible to current user (enforces bilateral blocking)
        try:
            invitee = User.objects.visible_to(user).get(id=data['invitee_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"invitee_id": "Cannot send invitation to this user"})

        # Prevent self-invites
        if invitee == user:
            raise serializers.ValidationError("Cannot invite yourself")

        # Check trip ownership and date range
        try:
            trip = Trip.objects.get(id=data['trip_id'], user=user)
        except Trip.DoesNotExist:
            raise serializers.ValidationError({"trip_id": "Trip not found"})

        if not (trip.start_date <= data['proposed_date'] <= trip.end_date):
            raise serializers.ValidationError({
                "proposed_date": f"Date must be within trip dates ({trip.start_date} to {trip.end_date})"
            })

        # Check for duplicate invitation
        duplicate = Session.objects.filter(
            inviter=user,
            invitee=invitee,
            proposed_date=data['proposed_date'],
            status__in=[SessionStatus.PENDING, SessionStatus.ACCEPTED]
        ).exists()

        if duplicate:
            raise serializers.ValidationError(
                "You already have a pending or accepted invitation with this user for this date"
            )

        data['invitee'] = invitee
        data['trip'] = trip

        return data


# Phase 6: Feedback Serializers

class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for creating feedback"""

    class Meta:
        model = Feedback
        fields = [
            'safety_rating', 'communication_rating',
            'overall_rating', 'notes'
        ]

    def validate(self, data):
        """Validate feedback data"""
        session = self.context.get('session')
        user = self.context.get('user')

        if not session:
            raise serializers.ValidationError("Session required")

        # Check session status
        if session.status != 'completed':
            raise serializers.ValidationError(
                "Can only provide feedback for completed sessions"
            )

        # Check for duplicate
        if Feedback.objects.filter(session=session, rater=user).exists():
            raise serializers.ValidationError(
                "Feedback already submitted for this session"
            )

        return data

    def create(self, validated_data):
        """Create feedback with atomic duplicate check"""
        session = self.context['session']
        user = self.context['user']

        # Determine who is being rated
        ratee = session.invitee if user == session.inviter else session.inviter

        try:
            feedback = Feedback.objects.create(
                session=session,
                rater=user,
                ratee=ratee,
                **validated_data
            )
            return feedback
        except IntegrityError:
            raise serializers.ValidationError(
                "Feedback already submitted for this session"
            )


class FeedbackStatsSerializer(serializers.Serializer):
    """Serializer for feedback statistics"""
    total_ratings = serializers.IntegerField()
    average_safety = serializers.FloatField()
    average_communication = serializers.FloatField()
    average_overall = serializers.FloatField()
    distribution = serializers.DictField()
