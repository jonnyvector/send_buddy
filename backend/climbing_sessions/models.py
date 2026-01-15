from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from trips.models import TimeBlock
import uuid


class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class Session(models.Model):
    """An invitation to climb together"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Participants
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions_sent')
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions_received')

    # Trip context (IMPORTANT: This is the inviter's trip)
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='sessions',
                             help_text="The inviter's trip that this session is part of")

    # Proposed details
    proposed_date = models.DateField()
    time_block = models.CharField(max_length=20, choices=TimeBlock.choices)
    crag = models.CharField(max_length=200, blank=True)
    goal = models.TextField(max_length=300, blank=True, help_text="What to climb/work on")

    # Status
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sessions'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=~models.Q(inviter=models.F('invitee')),
                name='session_no_self_invite'
            ),
        ]

    def __str__(self):
        return f"{self.inviter.display_name} → {self.invitee.display_name} ({self.proposed_date})"

    def clean(self):
        """Validate session details"""
        super().clean()

        # Prevent self-invites
        if self.inviter_id and self.invitee_id and self.inviter_id == self.invitee_id:
            raise ValidationError('Cannot invite yourself')

        # Ensure trip belongs to inviter
        if self.trip and self.inviter and self.trip.user_id != self.inviter_id:
            raise ValidationError({
                'trip': 'Session trip must belong to the inviter'
            })

        # Ensure proposed_date is within trip dates
        if self.trip and self.proposed_date:
            if self.proposed_date < self.trip.start_date or self.proposed_date > self.trip.end_date:
                raise ValidationError({
                    'proposed_date': f'Date must be within trip dates ({self.trip.start_date} - {self.trip.end_date})'
                })


class Message(models.Model):
    """Chat message within a session"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    body = models.TextField(max_length=2000)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.display_name} at {self.created_at}"


class Feedback(models.Model):
    """Post-session feedback (private)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='feedback')

    # Who rated whom
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_given')
    ratee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_received')

    # Ratings (1-5 scale)
    safety_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    overall_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Private notes (not shown to ratee in MVP)
    notes = models.TextField(max_length=1000, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback'
        unique_together = ['session', 'rater', 'ratee']

    def __str__(self):
        return f"Feedback from {self.rater.display_name} about {self.ratee.display_name}"
