from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, DisciplineProfile, ExperienceTag, UserExperienceTag,
    Block, Report, GradeConversion
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'gender', 'weight_kg', 'home_location', 'is_staff', 'email_verified', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'email_verified', 'profile_visible', 'risk_tolerance', 'gender', 'preferred_partner_gender', 'preferred_weight_difference')
    search_fields = ('email', 'display_name', 'home_location')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('display_name', 'avatar', 'bio')}),
        ('Location', {'fields': ('home_location', 'home_lat', 'home_lng')}),
        ('Preferences', {'fields': ('risk_tolerance', 'preferred_grade_system', 'profile_visible')}),
        ('Gender & Partner Preferences', {'fields': ('gender', 'preferred_partner_gender')}),
        ('Weight & Belay Safety', {'fields': ('weight_kg', 'preferred_weight_difference')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'email_verified')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'password1', 'password2'),
        }),
    )


@admin.register(DisciplineProfile)
class DisciplineProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'discipline', 'grade_system', 'comfortable_grade_min_display',
                    'comfortable_grade_max_display', 'can_lead', 'can_belay', 'created_at')
    list_filter = ('discipline', 'grade_system', 'can_lead', 'can_belay', 'can_build_anchors')
    search_fields = ('user__email', 'user__display_name')
    readonly_fields = ('comfortable_grade_min_score', 'comfortable_grade_max_score', 'projecting_grade_score')

    fieldsets = (
        ('User & Discipline', {'fields': ('user', 'discipline')}),
        ('Grades', {'fields': (
            'grade_system',
            'comfortable_grade_min_display', 'comfortable_grade_min_score',
            'comfortable_grade_max_display', 'comfortable_grade_max_score',
            'projecting_grade_display', 'projecting_grade_score'
        )}),
        ('Experience', {'fields': ('years_experience', 'can_lead', 'can_belay', 'can_build_anchors')}),
        ('Notes', {'fields': ('notes',)}),
    )


@admin.register(ExperienceTag)
class ExperienceTagAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'category', 'slug')
    list_filter = ('category',)
    search_fields = ('display_name', 'slug')


@admin.register(UserExperienceTag)
class UserExperienceTagAdmin(admin.ModelAdmin):
    list_display = ('user', 'tag')
    list_filter = ('tag__category',)
    search_fields = ('user__email', 'user__display_name', 'tag__display_name')


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__email', 'blocker__display_name', 'blocked__email', 'blocked__display_name')
    readonly_fields = ('created_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status')
    search_fields = ('reporter__email', 'reporter__display_name', 'reported__email', 'reported__display_name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Report Details', {'fields': ('reporter', 'reported', 'reason', 'details')}),
        ('Status', {'fields': ('status', 'admin_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GradeConversion)
class GradeConversionAdmin(admin.ModelAdmin):
    list_display = ('discipline', 'score', 'yds_grade', 'french_grade', 'v_scale_grade')
    list_filter = ('discipline',)
    search_fields = ('yds_grade', 'french_grade', 'v_scale_grade')
    ordering = ('discipline', 'score')
