from django.contrib import admin
from .models import Session, Message, Feedback


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitee', 'proposed_date', 'time_block', 'status', 'created_at')
    list_filter = ('status', 'time_block', 'proposed_date')
    search_fields = ('inviter__email', 'inviter__display_name', 'invitee__email', 'invitee__display_name')
    readonly_fields = ('created_at', 'updated_at', 'last_message_at')
    inlines = [MessageInline]

    fieldsets = (
        ('Participants', {'fields': ('inviter', 'invitee', 'trip')}),
        ('Details', {'fields': ('proposed_date', 'time_block', 'crag', 'goal')}),
        ('Status', {'fields': ('status',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'last_message_at')}),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'body_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('sender__email', 'sender__display_name', 'body')
    readonly_fields = ('created_at',)

    def body_preview(self, obj):
        return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
    body_preview.short_description = 'Body'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('rater', 'ratee', 'session', 'overall_rating', 'safety_rating', 'communication_rating', 'created_at')
    list_filter = ('overall_rating', 'safety_rating', 'communication_rating')
    search_fields = ('rater__email', 'rater__display_name', 'ratee__email', 'ratee__display_name')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Session', {'fields': ('session',)}),
        ('Participants', {'fields': ('rater', 'ratee')}),
        ('Ratings', {'fields': ('safety_rating', 'communication_rating', 'overall_rating')}),
        ('Notes', {'fields': ('notes',)}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
