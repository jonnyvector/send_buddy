from django.contrib import admin
from .models import ClimbingGroup, GroupMembership


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1
    readonly_fields = ('joined_at',)


@admin.register(ClimbingGroup)
class ClimbingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'is_private', 'auto_accept_members', 'created_at', 'member_count')
    list_filter = ('is_private', 'auto_accept_members', 'created_at')
    search_fields = ('name', 'description', 'creator__email', 'creator__display_name')
    readonly_fields = ('id', 'created_at')
    inlines = [GroupMembershipInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'creator')
        }),
        ('Settings', {
            'fields': ('is_private', 'auto_accept_members')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__email', 'user__display_name', 'group__name')
    readonly_fields = ('id', 'joined_at')

    fieldsets = (
        (None, {
            'fields': ('id', 'group', 'user', 'role')
        }),
        ('Metadata', {
            'fields': ('joined_at',)
        }),
    )