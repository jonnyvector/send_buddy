# Mountain Project API Integration - Specification

## Overview
Integrate Mountain Project's API to provide users with a comprehensive, searchable database of climbing destinations and crags when creating trips. This replaces the current hardcoded seed data with real, up-to-date climbing area information.

## Goals
1. **Rich destination data**: Access 10,000+ climbing areas worldwide from Mountain Project
2. **Smart autocomplete**: Users can search and select destinations as they type
3. **Accurate metadata**: Get real route counts, coordinates, disciplines, and descriptions
4. **Offline-ready**: Cache data locally to avoid API rate limits and improve performance
5. **Future-proof**: Regular sync to keep data fresh

## Mountain Project API

### API Details
- **Base URL**: `https://www.mountainproject.com/data`
- **Authentication**: Requires API key (free, sign up at mountainproject.com/data)
- **Rate Limits**: 200 requests per hour (per IP)
- **Documentation**: https://www.mountainproject.com/data

### Key Endpoints

#### 1. Get Routes and Areas
```
GET /get-routes-for-lat-lon
Parameters:
  - lat: latitude
  - lon: longitude
  - maxDistance: radius in miles (default 30)
  - maxResults: max number of results (default 10)
  - key: API key

Response:
{
  "routes": [{
    "id": "105924807",
    "name": "Churning in the Butter",
    "type": "Trad, Alpine",
    "rating": "5.10a",
    "stars": 4.5,
    "starVotes": 234,
    "pitches": "3",
    "location": ["California", "High Sierra", "Mt. Whitney"],
    "url": "https://www.mountainproject.com/route/...",
    "imgSqSmall": "...",
    "imgSmall": "...",
    "imgSmallMed": "...",
    "imgMedium": "...",
    "longitude": -118.2923,
    "latitude": 36.5785
  }],
  "success": 1
}
```

#### 2. Search for Areas
```
GET /search
Parameters:
  - query: search term (e.g., "Red River Gorge")
  - type: "area" | "route" (we'll use "area")
  - key: API key

Response: Similar structure to above
```

## Data Model Updates

### Destination Model (existing)
```python
class Destination(models.Model):
    slug = models.SlugField(unique=True, primary_key=True)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    primary_disciplines = models.JSONField(default=list)
    season = models.CharField(max_length=100, blank=True)

    # NEW FIELDS TO ADD:
    mp_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    mp_url = models.URLField(blank=True)
    mp_star_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    mp_star_votes = models.IntegerField(null=True, blank=True)
    location_hierarchy = models.JSONField(default=list)  # e.g., ["USA", "Kentucky", "Red River Gorge"]
    last_synced = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Crag Model (existing)
```python
class Crag(models.Model):
    # ... existing fields ...

    # NEW FIELDS TO ADD:
    mp_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    mp_url = models.URLField(blank=True)
    mp_star_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    parent_area_mp_id = models.CharField(max_length=50, blank=True, null=True)
    last_synced = models.DateTimeField(null=True, blank=True)
```

## Backend Implementation

### Phase 1: Mountain Project Service

**File**: `trips/services/mountain_project.py`

```python
import requests
from django.conf import settings
from django.core.cache import cache

class MountainProjectAPI:
    BASE_URL = "https://www.mountainproject.com/data"

    def __init__(self):
        self.api_key = settings.MOUNTAIN_PROJECT_API_KEY

    def search_areas(self, query: str, max_results: int = 20):
        """Search for climbing areas by name"""
        # Implementation with caching

    def get_area_details(self, area_id: str):
        """Get detailed info for a specific area"""
        # Implementation

    def get_nearby_areas(self, lat: float, lng: float, radius_miles: int = 50):
        """Find areas near coordinates"""
        # Implementation
```

### Phase 2: Management Command for Initial Sync

**File**: `trips/management/commands/sync_mountain_project.py`

```python
from django.core.management.base import BaseCommand
from trips.services.mountain_project import MountainProjectAPI
from trips.models import Destination, Crag

class Command(BaseCommand):
    help = 'Sync climbing areas from Mountain Project API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--popular-only',
            action='store_true',
            help='Only sync popular destinations (4+ stars)'
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Sync specific region (e.g., "USA", "Thailand")'
        )

    def handle(self, *args, **options):
        # 1. Fetch popular areas from MP
        # 2. Create/update Destination records
        # 3. Fetch crags for each destination
        # 4. Create/update Crag records
        # 5. Log sync stats
```

### Phase 3: Autocomplete API Endpoint

**File**: `trips/views.py`

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Destination
from .serializers import DestinationAutocompleteSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def autocomplete_destinations(request):
    """
    Search destinations for autocomplete

    Query params:
    - q: search query
    - limit: max results (default 10)
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))

    if len(query) < 2:
        return Response([])

    # Search by name, country, or location hierarchy
    destinations = Destination.objects.filter(
        Q(name__icontains=query) |
        Q(country__icontains=query) |
        Q(location_hierarchy__contains=[query])
    ).order_by('-mp_star_rating', 'name')[:limit]

    serializer = DestinationAutocompleteSerializer(destinations, many=True)
    return Response(serializer.data)
```

**File**: `trips/serializers.py`

```python
class DestinationAutocompleteSerializer(serializers.ModelSerializer):
    """Lightweight serializer for autocomplete"""
    class Meta:
        model = Destination
        fields = [
            'slug', 'name', 'country',
            'lat', 'lng', 'primary_disciplines',
            'mp_star_rating', 'location_hierarchy'
        ]
```

**URL**: `trips/urls.py`
```python
urlpatterns = [
    # ... existing patterns ...
    path('destinations/autocomplete/', views.autocomplete_destinations, name='destinations-autocomplete'),
]
```

## Frontend Implementation

### Phase 4: Destination Autocomplete Component

**File**: `frontend/components/DestinationAutocomplete.tsx`

```tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash';
import { api } from '@/lib/api';

interface Destination {
  slug: string;
  name: string;
  country: string;
  lat: number;
  lng: number;
  primary_disciplines: string[];
  mp_star_rating?: number;
  location_hierarchy: string[];
}

interface DestinationAutocompleteProps {
  value: Destination | null;
  onChange: (destination: Destination | null) => void;
  placeholder?: string;
  error?: string;
}

export function DestinationAutocomplete({
  value,
  onChange,
  placeholder = 'Search climbing areas...',
  error,
}: DestinationAutocompleteProps) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Destination[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  // Debounced search
  const searchDestinations = useCallback(
    debounce(async (searchQuery: string) => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        return;
      }

      setIsLoading(true);
      try {
        const results = await api.autocompleteDestinations(searchQuery);
        setSuggestions(results);
        setShowDropdown(true);
      } catch (err) {
        console.error('Failed to search destinations:', err);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    []
  );

  useEffect(() => {
    searchDestinations(query);
  }, [query, searchDestinations]);

  const handleSelect = (destination: Destination) => {
    onChange(destination);
    setQuery(destination.name);
    setShowDropdown(false);
  };

  return (
    <div className="relative">
      <input
        type="text"
        value={value ? value.name : query}
        onChange={(e) => {
          setQuery(e.target.value);
          if (value) onChange(null); // Clear selection when typing
        }}
        onFocus={() => query.length >= 2 && setShowDropdown(true)}
        placeholder={placeholder}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D97757]"
      />

      {isLoading && (
        <div className="absolute right-3 top-3">
          <LoadingSpinner size="sm" />
        </div>
      )}

      {showDropdown && suggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
          {suggestions.map((dest) => (
            <button
              key={dest.slug}
              type="button"
              onClick={() => handleSelect(dest)}
              className="w-full px-4 py-3 text-left hover:bg-gray-100 transition-colors"
            >
              <div className="font-medium text-gray-900">{dest.name}</div>
              <div className="text-sm text-gray-600">
                {dest.location_hierarchy.join(' > ')}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {dest.mp_star_rating && (
                  <span className="text-xs text-yellow-600">
                    ★ {dest.mp_star_rating.toFixed(1)}
                  </span>
                )}
                <span className="text-xs text-gray-500">
                  {dest.primary_disciplines.join(', ')}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      )}
    </div>
  );
}
```

### API Client Update

**File**: `frontend/lib/api.ts`

```typescript
// Add to APIClient class
async autocompleteDestinations(query: string, limit: number = 10): Promise<Destination[]> {
  return this.request<Destination[]>(
    `/api/destinations/autocomplete/?q=${encodeURIComponent(query)}&limit=${limit}`,
    { auth: true }
  );
}
```

## User Experience Flow

### Creating a Trip
1. User clicks "Create Trip"
2. Form shows "Destination" field with autocomplete
3. User types "red r" → sees:
   - Red River Gorge, KY (USA > Kentucky > Red River Gorge) ★ 4.2
   - Red Rocks, NV (USA > Nevada > Red Rocks) ★ 4.5
4. User selects "Red River Gorge, KY"
5. Form auto-fills coordinates, shows climbing disciplines
6. Optional: Show crag selector for that destination
7. User fills dates and other trip details
8. Submit creates trip with structured destination data

## Technical Considerations

### Rate Limiting
- **API Limits**: Mountain Project allows 200 req/hour
- **Solution**:
  - Cache autocomplete results for 24 hours
  - Sync popular areas weekly via cron job
  - Use Django cache framework for API responses

### Data Freshness
- **Weekly sync** of top 500 most popular areas (4+ stars)
- **On-demand fetch** for less popular areas when searched
- **Cache TTL**: 7 days for area details, 1 day for search results

### Performance
- **Database indexing** on `name`, `country`, `mp_star_rating`
- **PostgreSQL full-text search** for fast autocomplete
- **Limit results** to 20 per autocomplete query

### Error Handling
- **API down**: Fall back to cached data, show warning
- **Rate limit hit**: Use cached results, schedule retry
- **Invalid data**: Log errors, skip malformed records

## Implementation Phases

### Phase 1: Backend Setup (Day 1)
- [ ] Add Mountain Project API key to settings
- [ ] Create `MountainProjectAPI` service class
- [ ] Add new fields to Destination and Crag models
- [ ] Create and run migrations

### Phase 2: Data Sync (Day 1-2)
- [ ] Create `sync_mountain_project` management command
- [ ] Sync top 100 popular US destinations
- [ ] Sync international destinations (Thailand, Greece, Spain, etc.)
- [ ] Test data quality and completeness

### Phase 3: API Endpoint (Day 2)
- [ ] Create autocomplete serializer
- [ ] Create autocomplete view with search logic
- [ ] Add URL pattern
- [ ] Test endpoint with Postman/curl

### Phase 4: Frontend Component (Day 3)
- [ ] Create DestinationAutocomplete component
- [ ] Add debounced search
- [ ] Style dropdown with Tailwind
- [ ] Add to trip creation form
- [ ] Test user experience

### Phase 5: Polish & Deploy (Day 4)
- [ ] Add loading states
- [ ] Error handling and fallbacks
- [ ] Cache optimization
- [ ] Documentation
- [ ] Deploy to production

## Success Metrics
- **Coverage**: 500+ destinations in database
- **Search speed**: < 200ms for autocomplete queries
- **User adoption**: 80%+ of trips use destination autocomplete
- **Data accuracy**: Manual verification of top 50 areas

## Future Enhancements
- **Crag-level autocomplete**: Search specific crags within destinations
- **Route filtering**: "Show me 5.10 sport climbs in RRG"
- **Weather integration**: Show current conditions for destinations
- **Photo integration**: Use Mountain Project images for destinations
- **Community updates**: Allow users to suggest missing areas
