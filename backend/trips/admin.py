from django.contrib import admin
from .models import Destination, Crag, Trip, AvailabilityBlock


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'lat', 'lng', 'season')
    list_filter = ('country',)
    search_fields = ('name', 'country', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Crag)
class CragAdmin(admin.ModelAdmin):
    list_display = ('name', 'destination', 'route_count', 'approach_time')
    list_filter = ('destination',)
    search_fields = ('name', 'destination__name', 'description')
    readonly_fields = ('created_at', 'updated_at')


class AvailabilityBlockInline(admin.TabularInline):
    model = AvailabilityBlock
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('user', 'destination', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'destination', 'start_date')
    search_fields = ('user__email', 'user__display_name', 'destination__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('preferred_crags',)
    inlines = [AvailabilityBlockInline]

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Location', {'fields': ('destination', 'preferred_crags', 'custom_crag_notes')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Preferences', {'fields': ('preferred_disciplines', 'notes')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ('trip', 'date', 'time_block', 'notes')
    list_filter = ('time_block', 'date')
    search_fields = ('trip__user__email', 'trip__user__display_name', 'trip__destination__name')
