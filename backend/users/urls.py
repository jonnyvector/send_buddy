from django.urls import path
from . import views, admin_views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/register/', views.register, name='register'),
    path('auth/verify-email/', views.verify_email, name='verify_email'),
    path('auth/resend-verification/', views.resend_verification, name='resend_verification'),
    path('auth/login/', views.login, name='login'),
    path('auth/token/refresh/', views.token_refresh, name='token_refresh'),
    path('auth/logout/', views.logout, name='logout'),

    # Password Reset
    path('auth/password-reset/', views.password_reset_request, name='password_reset_request'),
    path('auth/password-reset/validate/', views.password_reset_validate, name='password_reset_validate'),
    path('auth/password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),

    # User Profile
    path('users/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/me/avatar/', views.upload_avatar, name='upload_avatar'),
    path('users/me/change-password/', views.change_password, name='change_password'),
    path('users/<uuid:user_id>/', views.get_public_profile, name='public_profile'),

    # Discipline Profiles
    path('users/me/disciplines/', views.manage_disciplines, name='manage_disciplines'),
    path('users/me/disciplines/<uuid:pk>/', views.manage_discipline_detail, name='manage_discipline_detail'),

    # Experience Tags
    path('experience-tags/', views.list_all_experience_tags, name='list_all_experience_tags'),
    path('users/me/experience-tags/', views.manage_experience_tags, name='manage_experience_tags'),
    path('users/me/experience-tags/<slug:tag_slug>/', views.remove_experience_tag, name='remove_experience_tag'),

    # Phase 6: Blocking
    path('users/<uuid:user_id>/block/', views.block_user, name='block_user'),
    path('blocks/', views.list_blocked_users, name='list_blocked_users'),

    # Phase 6: Reporting
    path('users/<uuid:user_id>/report/', views.report_user, name='report_user'),
    path('reports/my/', views.list_my_reports, name='list_my_reports'),

    # Phase 6: Admin Moderation
    path('admin/reports/', admin_views.list_reports, name='admin_list_reports'),
    path('admin/reports/<uuid:report_id>/', admin_views.update_report, name='admin_update_report'),
    path('admin/users/<uuid:user_id>/disable/', admin_views.disable_user, name='admin_disable_user'),
]
