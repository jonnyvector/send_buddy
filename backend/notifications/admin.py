from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model"""

    list_display = [
        'id',
        'recipient',
        'notification_type',
        'priority',
        'title',
        'is_read',
        'popup_shown',
        'created_at',
    ]

    list_filter = [
        'notification_type',
        'priority',
        'is_read',
        'popup_shown',
        'created_at',
    ]

    search_fields = [
        'recipient__email',
        'recipient__display_name',
        'title',
        'message',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'read_at',
    ]

    fieldsets = (
        ('Recipient', {
            'fields': ('recipient',)
        }),
        ('Notification Details', {
            'fields': (
                'notification_type',
                'priority',
                'title',
                'message',
                'action_url',
            )
        }),
        ('Related Object', {
            'fields': (
                'content_type',
                'object_id',
            )
        }),
        ('Status', {
            'fields': (
                'is_read',
                'popup_shown',
                'read_at',
            )
        }),
        ('Metadata', {
            'fields': (
                'id',
                'created_at',
            )
        }),
    )

    ordering = ['-created_at']

    def has_add_permission(self, request):
        """Disable manual creation through admin - should be created via signals/service"""
        return False
