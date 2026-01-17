from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TripOverlapViewSet

app_name = 'overlaps'

router = DefaultRouter()
router.register('overlaps', TripOverlapViewSet, basename='tripoverlap')

urlpatterns = [
    path('', include(router.urls)),
]