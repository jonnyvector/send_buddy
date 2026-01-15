from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Message


@receiver(post_save, sender=Message)
def update_session_last_message_at(sender, instance, created, **kwargs):
    """Update session.last_message_at when a new message is created"""
    if created:
        instance.session.last_message_at = instance.created_at
        instance.session.save(update_fields=['last_message_at'])
