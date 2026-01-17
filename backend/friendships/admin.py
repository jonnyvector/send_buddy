from django.contrib import admin
from .models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('requester', 'addressee', 'status', 'connection_source', 'created_at', 'accepted_at')
    list_filter = ('status', 'connection_source', 'created_at')
    search_fields = ('requester__email', 'requester__display_name', 'addressee__email', 'addressee__display_name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('id', 'requester', 'addressee', 'status')
        }),
        ('Metadata', {
            'fields': ('connection_source', 'created_at', 'accepted_at')
        }),
    )