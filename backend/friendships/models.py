from django.db import models
from django.db.models import Q
from django.conf import settings
import uuid


class Friendship(models.Model):
    """
    Represents a connection between two users.
    Can be one-directional (Follow) or bi-directional (Friends).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendship_requests_sent'
    )
    addressee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendship_requests_received'
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('following', 'Following')
        ],
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    connection_source = models.CharField(
        max_length=50,
        choices=[
            ('matched_trip', 'Met via Trip Match'),
            ('completed_session', 'Climbed Together'),
            ('manual_add', 'Manual Add'),
            ('imported', 'Imported from Contact')
        ],
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'friendships'
        unique_together = ('requester', 'addressee')
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['addressee', 'status']),
        ]

    def __str__(self):
        return f"{self.requester} → {self.addressee} ({self.status})"

    @classmethod
    def get_friends(cls, user):
        """Get all accepted friends for a user"""
        from users.models import User

        # Get User objects visible to the requesting user
        friends = User.objects.visible_to(user).filter(
            Q(friendship_requests_received__requester=user,
              friendship_requests_received__status='accepted') |
            Q(friendship_requests_sent__addressee=user,
              friendship_requests_sent__status='accepted')
        ).distinct()

        return friends

    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends"""
        # First check if they've blocked each other
        from users.models import Block
        if Block.objects.filter(
            Q(blocker=user1, blocked=user2) |
            Q(blocker=user2, blocked=user1)
        ).exists():
            return False

        # Check if they have an accepted friendship
        return cls.objects.filter(
            Q(requester=user1, addressee=user2, status='accepted') |
            Q(requester=user2, addressee=user1, status='accepted')
        ).exists()