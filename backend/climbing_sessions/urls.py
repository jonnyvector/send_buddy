from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet, submit_feedback, feedback_stats

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = router.urls + [
    # Phase 6: Feedback endpoints
    path('sessions/<uuid:session_id>/feedback/', submit_feedback, name='submit_feedback'),
    path('feedback/stats/', feedback_stats, name='feedback_stats'),
]
