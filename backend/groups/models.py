from django.db import models
from django.conf import settings
import uuid


class ClimbingGroup(models.Model):
    """
    Represents a climbing crew/group.
    Groups can plan trips together.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='GroupMembership',
        related_name='climbing_groups'
    )

    # Settings
    is_private = models.BooleanField(default=False)  # Invite-only vs. discoverable
    auto_accept_members = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'climbing_groups'
        ordering = ['name']

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    """
    Through model for Group membership with roles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ClimbingGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Admin'),
            ('member', 'Member'),
            ('pending', 'Pending Invitation')
        ],
        default='member'
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'group_memberships'
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user} - {self.group} ({self.role})"