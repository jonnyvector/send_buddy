from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    DestinationViewSet, TripViewSet, AvailabilityBlockViewSet,
    map_destinations, autocomplete_destinations
)

router = DefaultRouter()
router.register(r'destinations', DestinationViewSet, basename='destination')
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'availability', AvailabilityBlockViewSet, basename='availability')

urlpatterns = [
    # Map destinations endpoint
    path('map/destinations/', map_destinations, name='map_destinations'),

    # Destination autocomplete endpoint
    path('destinations/autocomplete/', autocomplete_destinations, name='destinations_autocomplete'),
] + router.urls
