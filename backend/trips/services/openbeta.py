"""
OpenBeta API Integration Service

This module provides a Python interface to the OpenBeta API for fetching
climbing area data, including destinations, crags, and route information.

OpenBeta is a free, open-source climbing resource built by climbers, for climbers.

API Documentation: https://docs.openbeta.io/
GraphQL Endpoint: https://api.openbeta.io/graphql
Rate Limits: Reasonable usage expected (be respectful)
"""

import requests
from django.conf import settings
from django.core.cache import cache
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class OpenBetaAPIError(Exception):
    """Exception raised for OpenBeta API errors"""
    pass


class OpenBetaAPI:
    """
    Service class for interacting with the OpenBeta GraphQL API.

    Features:
    - Search for climbing areas by name
    - Get detailed information for specific areas
    - Automatic caching to be respectful of the free API
    - Graceful error handling

    Note: OpenBeta replaced Mountain Project API which closed in 2025.
    """

    # Cache TTL settings
    CACHE_TTL_SEARCH = 86400  # 24 hours for search results
    CACHE_TTL_AREA_DETAILS = 604800  # 7 days for area details (604800 = 7 days in seconds)

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the OpenBeta API client.

        Args:
            api_url: Optional API URL. If not provided, uses settings.OPENBETA_API_URL
        """
        self.api_url = api_url or getattr(
            settings,
            'OPENBETA_API_URL',
            'https://api.openbeta.io/graphql'
        )

    def _make_graphql_request(
        self,
        query: str,
        variables: Dict[str, Any],
        cache_key: Optional[str] = None,
        cache_ttl: int = 3600
    ) -> Dict[str, Any]:
        """
        Make a GraphQL request to the OpenBeta API with caching.

        Args:
            query: GraphQL query string
            variables: GraphQL query variables
            cache_key: Optional cache key. If provided, response will be cached.
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)

        Returns:
            GraphQL response data

        Raises:
            OpenBetaAPIError: If API request fails
        """
        # Check cache first
        if cache_key:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_response

        # Prepare GraphQL request
        payload = {
            'query': query,
            'variables': variables
        }

        try:
            logger.info(f"Making request to OpenBeta API")
            response = requests.post(
                self.api_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Check for GraphQL errors
            if 'errors' in data:
                error_messages = [err.get('message', 'Unknown error') for err in data['errors']]
                error_msg = '; '.join(error_messages)
                raise OpenBetaAPIError(f"GraphQL errors: {error_msg}")

            # Extract data from response
            result = data.get('data', {})

            # Cache successful response
            if cache_key:
                cache.set(cache_key, result, cache_ttl)
                logger.debug(f"Cached response for key: {cache_key} (TTL: {cache_ttl}s)")

            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("OpenBeta API rate limit exceeded")
                raise OpenBetaAPIError("Rate limit exceeded. Please try again later.")
            else:
                logger.error(f"HTTP error calling OpenBeta API: {e}")
                raise OpenBetaAPIError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error calling OpenBeta API: {e}")
            raise OpenBetaAPIError(f"Request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response from OpenBeta API: {e}")
            raise OpenBetaAPIError(f"Invalid response format: {e}")

    def search_areas(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for climbing areas by name.

        Args:
            query: Search term (e.g., "Red River Gorge")
            limit: Maximum number of results to return (default: 20)

        Returns:
            List of area dictionaries with fields:
            - uuid: OpenBeta area UUID
            - area_name: Area name
            - pathTokens: Location hierarchy (e.g., ["USA", "Kentucky", "Red River Gorge"])
            - metadata: {lat: float, lng: float}
            - totalClimbs: Total number of climbs/routes
            - density: Climb density metric

        Example:
            >>> api = OpenBetaAPI()
            >>> results = api.search_areas("red river")
            >>> print(results[0]['area_name'])
            'Red River Gorge'
        """
        if not query or len(query.strip()) < 2:
            return []

        # Sanitize cache key (replace spaces and special chars)
        cache_safe_query = query.lower().replace(' ', '_').replace(':', '_')
        cache_key = f"openbeta_search_areas_{cache_safe_query}_{limit}"

        # GraphQL query for area search
        graphql_query = """
        query SearchAreas($name: String!, $limit: Int!) {
          areas(filter: {area_name: {match: $name}}, limit: $limit) {
            area_name
            uuid
            metadata {
              lat
              lng
            }
            pathTokens
            totalClimbs
            density
          }
        }
        """

        try:
            response = self._make_graphql_request(
                query=graphql_query,
                variables={'name': query, 'limit': limit},
                cache_key=cache_key,
                cache_ttl=self.CACHE_TTL_SEARCH
            )

            areas = response.get('areas', [])
            logger.info(f"Found {len(areas)} areas for query: '{query}'")
            return areas

        except OpenBetaAPIError as e:
            logger.error(f"Failed to search areas: {e}")
            # Return empty list on error (graceful degradation)
            return []

    def get_area_details(self, area_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific climbing area.

        Args:
            area_uuid: OpenBeta area UUID (e.g., "c7a1c7e0-9b9a-5f3a-8e1a-1b2c3d4e5f6a")

        Returns:
            Dictionary with area details or None if not found:
            - uuid: OpenBeta area UUID
            - area_name: Area name
            - pathTokens: Location hierarchy
            - metadata: {lat: float, lng: float}
            - totalClimbs: Number of climbs
            - density: Climb density
            - content: {description: string}

        Example:
            >>> api = OpenBetaAPI()
            >>> area = api.get_area_details("c7a1c7e0-9b9a-5f3a-8e1a-1b2c3d4e5f6a")
            >>> print(area['area_name'])
        """
        if not area_uuid:
            return None

        cache_key = f"openbeta_area_details_{area_uuid}"

        # GraphQL query for area details
        graphql_query = """
        query GetArea($uuid: ID!) {
          area(uuid: $uuid) {
            area_name
            uuid
            metadata {
              lat
              lng
            }
            pathTokens
            totalClimbs
            density
            content {
              description
            }
          }
        }
        """

        try:
            response = self._make_graphql_request(
                query=graphql_query,
                variables={'uuid': area_uuid},
                cache_key=cache_key,
                cache_ttl=self.CACHE_TTL_AREA_DETAILS
            )

            area = response.get('area')
            if area:
                logger.info(f"Retrieved details for area: {area.get('area_name')} (UUID: {area_uuid})")
                return area
            else:
                logger.warning(f"No area found with UUID: {area_uuid}")
                return None

        except OpenBetaAPIError as e:
            logger.error(f"Failed to get area details for UUID {area_uuid}: {e}")
            return None

    def normalize_area_data(self, area_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OpenBeta area data to match our expected format.

        This helper method transforms OpenBeta's data structure to be compatible
        with our Destination model fields and serializers.

        Args:
            area_data: Raw area data from OpenBeta API

        Returns:
            Normalized dictionary with fields:
            - id: area UUID (maps to mp_id in our model)
            - name: area name
            - location: location hierarchy
            - latitude, longitude: coordinates
            - totalClimbs: route count
            - description: area description (if available)
            - url: OpenBeta URL for the area
        """
        metadata = area_data.get('metadata') or {}
        content = area_data.get('content') or {}

        normalized = {
            'id': area_data.get('uuid'),
            'name': area_data.get('area_name', ''),
            'location': area_data.get('pathTokens', []),
            'latitude': metadata.get('lat'),
            'longitude': metadata.get('lng'),
            'totalClimbs': area_data.get('totalClimbs', 0),
            'density': area_data.get('density', 0),
            'description': content.get('description', ''),
            # Construct OpenBeta URL
            'url': f"https://openbeta.io/crag/{area_data.get('uuid')}" if area_data.get('uuid') else ''
        }

        return normalized
