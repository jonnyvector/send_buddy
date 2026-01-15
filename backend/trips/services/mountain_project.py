"""
Mountain Project API Integration Service

This module provides a Python interface to the Mountain Project API for fetching
climbing area data, including destinations, crags, and route information.

API Documentation: https://www.mountainproject.com/data
Rate Limits: 200 requests per hour per IP
"""

import requests
from django.conf import settings
from django.core.cache import cache
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MountainProjectAPIError(Exception):
    """Exception raised for Mountain Project API errors"""
    pass


class MountainProjectAPI:
    """
    Service class for interacting with the Mountain Project API.

    Features:
    - Search for climbing areas by name
    - Get detailed information for specific areas
    - Automatic caching to respect rate limits (200 req/hour)
    - Graceful error handling
    """

    BASE_URL = "https://www.mountainproject.com/data"

    # Cache TTL settings
    CACHE_TTL_SEARCH = 86400  # 24 hours for search results
    CACHE_TTL_AREA_DETAILS = 604800  # 7 days for area details

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Mountain Project API client.

        Args:
            api_key: Optional API key. If not provided, uses settings.MOUNTAIN_PROJECT_API_KEY
        """
        self.api_key = api_key or getattr(settings, 'MOUNTAIN_PROJECT_API_KEY', '')
        if not self.api_key:
            logger.warning("Mountain Project API key not configured. Set MOUNTAIN_PROJECT_API_KEY in settings.")

    def _make_request(self, endpoint: str, params: Dict[str, Any], cache_key: Optional[str] = None, cache_ttl: int = 3600) -> Dict[str, Any]:
        """
        Make a request to the Mountain Project API with caching.

        Args:
            endpoint: API endpoint (e.g., 'get-routes', 'search')
            params: Query parameters
            cache_key: Optional cache key. If provided, response will be cached.
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)

        Returns:
            JSON response as dictionary

        Raises:
            MountainProjectAPIError: If API request fails
        """
        # Check cache first
        if cache_key:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_response

        # Add API key to params
        params['key'] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            logger.info(f"Making request to Mountain Project API: {endpoint}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for API-level errors
            if not data.get('success', False):
                error_msg = data.get('error', 'Unknown API error')
                raise MountainProjectAPIError(f"Mountain Project API error: {error_msg}")

            # Cache successful response
            if cache_key:
                cache.set(cache_key, data, cache_ttl)
                logger.debug(f"Cached response for key: {cache_key} (TTL: {cache_ttl}s)")

            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Mountain Project API rate limit exceeded (200 req/hour)")
                raise MountainProjectAPIError("Rate limit exceeded. Please try again later.")
            else:
                logger.error(f"HTTP error calling Mountain Project API: {e}")
                raise MountainProjectAPIError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error calling Mountain Project API: {e}")
            raise MountainProjectAPIError(f"Request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response from Mountain Project API: {e}")
            raise MountainProjectAPIError(f"Invalid response format: {e}")

    def search_areas(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for climbing areas by name.

        Args:
            query: Search term (e.g., "Red River Gorge")
            max_results: Maximum number of results to return (default: 20)

        Returns:
            List of area dictionaries with fields:
            - id: Mountain Project area ID
            - name: Area name
            - type: Type of climbing (e.g., "Trad, Sport")
            - url: Mountain Project URL
            - location: List of location hierarchy (e.g., ["USA", "Kentucky", "Red River Gorge"])
            - latitude, longitude: Coordinates
            - stars: Average star rating (0-4)
            - starVotes: Number of votes

        Example:
            >>> api = MountainProjectAPI()
            >>> results = api.search_areas("red river")
            >>> print(results[0]['name'])
            'Red River Gorge'
        """
        if not query or len(query.strip()) < 2:
            return []

        cache_key = f"mp_search_areas:{query.lower()}:{max_results}"

        try:
            response = self._make_request(
                endpoint='search',
                params={
                    'q': query,
                    'type': 'area',
                    'maxResults': max_results
                },
                cache_key=cache_key,
                cache_ttl=self.CACHE_TTL_SEARCH
            )

            # Return routes (despite the name, these are areas when type='area')
            routes = response.get('routes', [])
            logger.info(f"Found {len(routes)} areas for query: '{query}'")
            return routes

        except MountainProjectAPIError as e:
            logger.error(f"Failed to search areas: {e}")
            # Return empty list on error (graceful degradation)
            return []

    def get_area_details(self, area_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific climbing area.

        Args:
            area_id: Mountain Project area ID (e.g., "105924807")

        Returns:
            Dictionary with area details or None if not found:
            - id: Mountain Project area ID
            - name: Area name
            - type: Climbing types
            - url: Mountain Project URL
            - location: Location hierarchy list
            - latitude, longitude: Coordinates
            - stars: Average rating
            - starVotes: Number of votes
            - imgSqSmall, imgSmall, imgSmallMed, imgMedium: Image URLs

        Example:
            >>> api = MountainProjectAPI()
            >>> area = api.get_area_details("105924807")
            >>> print(area['name'])
        """
        if not area_id:
            return None

        cache_key = f"mp_area_details:{area_id}"

        try:
            response = self._make_request(
                endpoint='get-routes',
                params={
                    'routeIds': area_id
                },
                cache_key=cache_key,
                cache_ttl=self.CACHE_TTL_AREA_DETAILS
            )

            routes = response.get('routes', [])
            if routes:
                area = routes[0]
                logger.info(f"Retrieved details for area: {area.get('name')} (ID: {area_id})")
                return area
            else:
                logger.warning(f"No area found with ID: {area_id}")
                return None

        except MountainProjectAPIError as e:
            logger.error(f"Failed to get area details for ID {area_id}: {e}")
            return None

    def get_nearby_areas(self, lat: float, lng: float, radius_miles: int = 50, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Find climbing areas near a set of coordinates.

        Args:
            lat: Latitude
            lng: Longitude
            radius_miles: Search radius in miles (default: 50)
            max_results: Maximum number of results (default: 20)

        Returns:
            List of area dictionaries (same format as search_areas)

        Example:
            >>> api = MountainProjectAPI()
            >>> areas = api.get_nearby_areas(37.7833, -83.6833, radius_miles=30)
            >>> for area in areas:
            ...     print(f"{area['name']} - {area['stars']} stars")
        """
        cache_key = f"mp_nearby:{lat},{lng}:{radius_miles}:{max_results}"

        try:
            response = self._make_request(
                endpoint='get-routes-for-lat-lon',
                params={
                    'lat': lat,
                    'lon': lng,
                    'maxDistance': radius_miles,
                    'maxResults': max_results
                },
                cache_key=cache_key,
                cache_ttl=self.CACHE_TTL_SEARCH
            )

            routes = response.get('routes', [])
            logger.info(f"Found {len(routes)} areas within {radius_miles} miles of ({lat}, {lng})")
            return routes

        except MountainProjectAPIError as e:
            logger.error(f"Failed to get nearby areas: {e}")
            return []
