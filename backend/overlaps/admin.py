from django.contrib import admin
from .models import TripOverlap


@admin.register(TripOverlap)
class TripOverlapAdmin(admin.ModelAdmin):
    list_display = (
        'user1', 'user2', 'overlap_destination',
        'overlap_start_date', 'overlap_end_date', 'overlap_days',
        'overlap_score', 'notification_sent', 'connection_created'
    )
    list_filter = (
        'notification_sent', 'connection_created',
        'user1_dismissed', 'user2_dismissed', 'detected_at'
    )
    search_fields = (
        'user1__email', 'user1__display_name',
        'user2__email', 'user2__display_name',
        'overlap_destination__name'
    )
    readonly_fields = ('id', 'detected_at')
    date_hierarchy = 'overlap_start_date'

    fieldsets = (
        ('Users & Trips', {
            'fields': ('id', 'user1', 'user2', 'trip1', 'trip2')
        }),
        ('Overlap Details', {
            'fields': (
                'overlap_destination', 'overlap_start_date',
                'overlap_end_date', 'overlap_days', 'overlap_score'
            )
        }),
        ('Notification & Status', {
            'fields': (
                'notification_sent', 'notification_sent_at',
                'user1_dismissed', 'user2_dismissed',
                'connection_created', 'detected_at'
            )
        }),
    )