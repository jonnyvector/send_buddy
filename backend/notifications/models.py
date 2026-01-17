from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import uuid


class Notification(models.Model):
    """
    Notification model for Send Buddy application.
    Supports various notification types with priority levels.
    """

    NOTIFICATION_TYPES = [
        # Legacy matching notifications
        ('new_match', 'New Match'),
        ('connection_request', 'Connection Request'),
        ('connection_accepted', 'Connection Accepted'),
        ('connection_declined', 'Connection Declined'),
        ('session_invite', 'Session Invite'),
        ('session_update', 'Session Update'),

        # Social Network notifications
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Request Accepted'),
        ('friend_trip_posted', 'Friend Posted a Trip'),

        # Overlap Engine notifications
        ('trip_overlap_detected', 'Trip Overlap Detected'),
        ('friend_in_home_crag', 'Friend Coming to Your Home Crag'),

        # Group Features notifications
        ('group_invite', 'Group Invitation'),
        ('group_trip_posted', 'Group Trip Posted'),
        ('group_trip_updated', 'Group Trip Updated'),
    ]

    PRIORITY_LEVELS = [
        ('critical', 'Critical'),  # Show popup
        ('high', 'High'),          # Badge + notification
        ('medium', 'Medium'),      # Badge only
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='medium'
    )

    # Generic relation to any model (Trip, Connection, Session, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(
        max_length=255,
        blank=True,
        help_text='Frontend URL to navigate to on click'
    )

    # Metadata
    is_read = models.BooleanField(default=False)
    popup_shown = models.BooleanField(
        default=False,
        help_text='Track if popup was displayed to user'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['recipient', 'popup_shown']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.display_name}"

    def mark_as_read(self):
        """Mark notification as read and set read_at timestamp"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_popup_shown(self):
        """Mark that popup was shown to user"""
        if not self.popup_shown:
            self.popup_shown = True
            self.save(update_fields=['popup_shown'])
