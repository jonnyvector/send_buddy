from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check endpoint"""
    return Response({'status': 'ok', 'message': 'Send Buddy API is running'})


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint with available routes"""
    return Response({
        'message': 'Welcome to Send Buddy API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health/',
            'admin': '/admin/',
            'authentication': {
                'register': 'POST /api/auth/register/',
                'verify_email': 'POST /api/auth/verify-email/',
                'resend_verification': 'POST /api/auth/resend-verification/',
                'login': 'POST /api/auth/login/',
                'logout': 'POST /api/auth/logout/',
                'token_refresh': 'POST /api/auth/token/refresh/',
                'password_reset_request': 'POST /api/auth/password-reset/request/',
                'password_reset_confirm': 'POST /api/auth/password-reset/confirm/',
            },
            'user_profile': {
                'current_user': 'GET/PATCH /api/users/me/',
                'upload_avatar': 'POST /api/users/me/avatar/',
                'change_password': 'POST /api/users/me/change-password/',
            },
            'destinations': {
                'list': 'GET /api/destinations/ (search, limit params)',
                'detail': 'GET /api/destinations/:slug/',
                'crags': 'GET /api/destinations/:slug/crags/',
            },
            'trips': {
                'list': 'GET /api/trips/ (is_active, upcoming params)',
                'create': 'POST /api/trips/',
                'detail': 'GET /api/trips/:id/',
                'update': 'PATCH /api/trips/:id/',
                'delete': 'DELETE /api/trips/:id/',
                'next_upcoming': 'GET /api/trips/next/',
                'add_availability': 'POST /api/trips/:id/availability/',
                'bulk_add_availability': 'POST /api/trips/:id/availability/bulk/',
            },
            'availability': {
                'list': 'GET /api/availability/',
                'detail': 'GET /api/availability/:id/',
                'update': 'PATCH /api/availability/:id/',
                'delete': 'DELETE /api/availability/:id/',
            },
            'matching': {
                'list_matches': 'GET /api/matches/ (trip, limit params)',
                'match_detail': 'GET /api/matches/:user_id/detail/ (trip param)',
            },
            'sessions': {
                'list': 'GET /api/sessions/ (status, role params)',
                'create': 'POST /api/sessions/',
                'detail': 'GET /api/sessions/:id/',
                'accept': 'POST /api/sessions/:id/accept/',
                'decline': 'POST /api/sessions/:id/decline/',
                'cancel': 'POST /api/sessions/:id/cancel/',
                'complete': 'POST /api/sessions/:id/complete/',
                'messages': 'GET/POST /api/sessions/:id/messages/',
                'mark_read': 'POST /api/sessions/:id/mark-read/',
            },
            'blocking': {
                'block_user': 'POST /api/users/:user_id/block/',
                'unblock_user': 'DELETE /api/users/:user_id/block/',
                'list_blocked': 'GET /api/blocks/',
            },
            'reporting': {
                'report_user': 'POST /api/users/:user_id/report/',
                'my_reports': 'GET /api/reports/my/ (status param)',
            },
            'feedback': {
                'submit_feedback': 'POST /api/sessions/:session_id/feedback/',
                'my_stats': 'GET /api/feedback/stats/',
            },
            'admin': {
                'list_reports': 'GET /api/admin/reports/ (status, ordering params)',
                'update_report': 'PATCH /api/admin/reports/:id/',
                'disable_user': 'POST /api/admin/users/:user_id/disable/',
            },
        },
        'documentation': 'See /docs/ for full API documentation (coming soon)'
    })
