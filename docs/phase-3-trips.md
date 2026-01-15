# Phase 3: Trip & Availability Management

## Overview
Implement trip creation, editing, and availability block management. This is critical for the matchmaking system.

**Recent Updates:**
- Added comprehensive serializers with proper read/write separation
- Fixed model field inconsistencies (Trip uses ForeignKey to Destination, not separate name/lat/lng)
- Added rate limiting and security best practices from Phase 2
- Created ViewSets with proper queryset optimization
- Marked map endpoints as Phase 3.5 (requires complex aggregation, optional for MVP)

## Dependencies
- Phase 1 (Trip/AvailabilityBlock models) ✓
- Phase 2 (Authentication) ✓

---

## 1. Backend API Endpoints

### 1.1 List Destinations (for autocomplete)

**GET `/api/destinations/`**

Query params:
- `search` (optional) - filter by name
- `limit` (default 20)

Response (200):
```json
{
  "count": 9,
  "results": [
    {
      "slug": "railay",
      "name": "Railay, Krabi",
      "country": "Thailand",
      "lat": "8.009700",
      "lng": "98.839500",
      "primary_disciplines": ["sport"],
      "season": "Nov-Apr (dry season)",
      "image_url": ""
    }
  ]
}
```

**Use case:** Destination autocomplete in trip creation form

---

### 1.2 Get Crags for Destination

**GET `/api/destinations/:slug/crags/`**

Response (200):
```json
{
  "destination": {
    "slug": "railay",
    "name": "Railay, Krabi"
  },
  "crags": [
    {
      "id": "uuid",
      "name": "Thaiwand Wall",
      "disciplines": ["sport"],
      "route_count": 200,
      "approach_time": 15
    },
    {
      "id": "uuid",
      "name": "Fire Wall",
      "disciplines": ["sport"],
      "route_count": 100,
      "approach_time": 20
    }
  ]
}
```

**Use case:** Show crag options after user selects destination

---

### 1.3 Map Data (Destinations with Active Trips)

**GET `/api/map/destinations/`**

Query params:
- `start_date` (optional) - filter trips starting after this date
- `end_date` (optional) - filter trips ending before this date
- `disciplines` (optional, comma-separated) - e.g., "sport,trad"

Response (200):
```json
{
  "destinations": [
    {
      "slug": "red-river-gorge",
      "name": "Red River Gorge, KY",
      "lat": 37.7781,
      "lng": -83.6816,
      "active_trip_count": 12,
      "active_user_count": 15,
      "disciplines": ["sport", "trad"],
      "date_range": {
        "earliest_arrival": "2026-03-10",
        "latest_departure": "2026-04-15"
      }
    }
  ]
}
```

**Use case:** Interactive map view showing climbing destinations with active trips

---

### 1.4 Map - Destination Detail

**GET `/api/map/destinations/:slug/`**

Response (200):
```json
{
  "destination": {
    "slug": "railay",
    "name": "Railay, Krabi",
    "country": "Thailand",
    "lat": 8.0097,
    "lng": 98.8395,
    "description": "Limestone sport climbing paradise",
    "season": "Nov-Apr (dry season)"
  },
  "active_trips": 8,
  "users": [
    {
      "id": "uuid",
      "display_name": "Alex Climber",
      "avatar": "https://...",
      "trip": {
        "start_date": "2026-03-15",
        "end_date": "2026-03-28",
        "preferred_crags": ["Thaiwand Wall"]
      }
    }
  ]
}
```

**Use case:** Popup details when clicking a destination on the map

---

### 1.5 Create Trip

**POST `/api/trips/`**

Request:
```json
{
  "destination": "railay",
  "preferred_crags": ["uuid-thaiwand", "uuid-fire-wall"],
  "custom_crag_notes": "",
  "start_date": "2026-03-15",
  "end_date": "2026-03-28",
  "preferred_disciplines": ["sport"],
  "notes": "Looking for partners to project routes in the 5.11-5.12 range"
}
```

Response (201):
```json
{
  "id": "uuid",
  "user": "uuid",
  "destination": {
    "slug": "railay",
    "name": "Railay, Krabi",
    "country": "Thailand",
    "lat": "8.009700",
    "lng": "98.839500",
    "season": "Nov-Apr (dry season)",
    "primary_disciplines": ["sport"]
  },
  "preferred_crags": [
    {
      "id": "uuid-thaiwand",
      "name": "Thaiwand Wall",
      "disciplines": ["sport"],
      "route_count": 200,
      "approach_time": 15
    },
    {
      "id": "uuid-fire-wall",
      "name": "Fire Wall",
      "disciplines": ["sport"],
      "route_count": 100,
      "approach_time": 20
    }
  ],
  "custom_crag_notes": "",
  "start_date": "2026-03-15",
  "end_date": "2026-03-28",
  "preferred_disciplines": ["sport"],
  "notes": "Looking for partners to project routes in the 5.11-5.12 range",
  "is_active": true,
  "created_at": "2026-01-13T10:30:00Z",
  "availability": []
}
```

**Validation:**
- end_date >= start_date
- start_date >= today
- preferred_disciplines must be valid choices (sport, trad, bouldering, multipitch, gym)
- destination (slug) must exist in database
- preferred_crags (if provided) must belong to the selected destination

**Rate Limiting:**
- 20 trip creation attempts per user per hour

**Permissions:**
- User must be authenticated

---

### 1.6 List My Trips

**GET `/api/trips/`**

Query params:
- `is_active=true` (default: show all active trips)
- `upcoming=true` (filter start_date >= today)

Response (200):
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "destination": {
        "slug": "railay",
        "name": "Railay, Krabi",
        "country": "Thailand"
      },
      "start_date": "2026-03-15",
      "end_date": "2026-03-28",
      "preferred_disciplines": ["sport", "bouldering"],
      "is_active": true,
      "notes": "Looking for sport climbing partners",
      "availability_count": 5
    }
  ]
}
```

**Permissions:**
- User must be authenticated
- Can only view own trips

---

### 1.7 Get Trip Detail

**GET `/api/trips/:id/`**

Response (200):
```json
{
  "id": "uuid",
  "user": "uuid",
  "destination": {
    "slug": "railay",
    "name": "Railay, Krabi",
    "country": "Thailand",
    "lat": "8.009700",
    "lng": "98.839500",
    "season": "Nov-Apr (dry season)",
    "primary_disciplines": ["sport"]
  },
  "preferred_crags": [
    {
      "id": "uuid",
      "name": "Thaiwand Wall",
      "disciplines": ["sport"],
      "route_count": 200,
      "approach_time": 15
    }
  ],
  "custom_crag_notes": "",
  "start_date": "2026-03-15",
  "end_date": "2026-03-28",
  "preferred_disciplines": ["sport", "bouldering"],
  "notes": "Interested in projecting 5.11+ routes",
  "is_active": true,
  "created_at": "2026-01-13T10:30:00Z",
  "availability": [
    {
      "id": "uuid",
      "date": "2026-03-16",
      "time_block": "morning",
      "notes": "Prefer easy warmup routes"
    }
  ]
}
```

**Permissions:**
- User must own the trip (for MVP)
- Future: visible to potential matches based on matching algorithm

---

### 1.8 Update Trip

**PATCH `/api/trips/:id/`**

Request:
```json
{
  "notes": "Updated trip notes",
  "custom_crag_notes": "Focus on Thaiwand Wall and Fire Wall",
  "preferred_disciplines": ["sport"],
  "is_active": true
}
```

Response (200):
```json
{
  "id": "uuid",
  "destination": {...},
  "notes": "Updated trip notes",
  "custom_crag_notes": "Focus on Thaiwand Wall and Fire Wall",
  "preferred_disciplines": ["sport"],
  "is_active": true,
  ...other fields...
}
```

**Allowed updates:**
- `notes` (general trip notes)
- `custom_crag_notes` (specific crag preferences)
- `preferred_disciplines` (update discipline preferences)
- `preferred_crags` (update ManyToMany relationship)
- `is_active` (deactivate trip)

**Not allowed:**
- `start_date`, `end_date` (changing dates - delete + recreate instead to avoid availability conflicts)
- `destination` (changing destination - delete + recreate instead)

**Permissions:**
- User must own the trip

---

### 1.9 Delete Trip

**DELETE `/api/trips/:id/`**

Response (204): No content

**Business Logic:**
- Soft delete by setting `is_active=False` (MVP)
- OR hard delete (be careful of foreign key constraints)

---

### 1.10 Add Availability Block

**POST `/api/trips/:trip_id/availability/`**

Request:
```json
{
  "date": "2026-03-16",
  "time_block": "morning",
  "notes": "Prefer easy warmup routes"
}
```

Response (201):
```json
{
  "id": "uuid",
  "trip": "trip-uuid",
  "date": "2026-03-16",
  "time_block": "morning",
  "notes": "Prefer easy warmup routes"
}
```

**Validation:**
- date must be within trip's start_date and end_date
- Unique constraint: (trip, date, time_block)

---

### 1.11 Bulk Add Availability

**POST `/api/trips/:trip_id/availability/bulk/`**

Request:
```json
{
  "blocks": [
    { "date": "2026-03-16", "time_block": "morning" },
    { "date": "2026-03-16", "time_block": "afternoon" },
    { "date": "2026-03-17", "time_block": "full_day" },
    { "date": "2026-03-18", "time_block": "rest" }
  ]
}
```

Response (201):
```json
{
  "created": 4,
  "availability": [...]
}
```

**Use case:**
- User selects multiple days in calendar UI
- Faster than individual requests

---

### 1.12 Update Availability Block

**PATCH `/api/availability/:id/`**

Request:
```json
{
  "time_block": "full_day",
  "notes": "Updated notes"
}
```

Response (200):
```json
{
  "id": "uuid",
  "trip": "trip-uuid",
  "date": "2026-03-16",
  "time_block": "full_day",
  "notes": "Updated notes"
}
```

---

### 1.13 Delete Availability Block

**DELETE `/api/availability/:id/`**

Response (204): No content

---

### 1.14 Get Next Upcoming Trip

**GET `/api/trips/next/`**

Returns the user's next upcoming trip (start_date >= today, earliest first).

Response (200):
```json
{
  "id": "uuid",
  "destination_name": "Railay, Thailand",
  "start_date": "2026-03-15",
  ...
}
```

Response (404) if no upcoming trips:
```json
{
  "detail": "No upcoming trips"
}
```

---

## 2. Frontend Implementation

### 2.1 Map View - Interactive Destination Explorer

**New Page:** `/explore`

**Purpose:**
- Discover climbing destinations with active trips
- Plan trips based on where other climbers are going
- Visualize seasonal climbing trends

---

#### MapView Component

```typescript
// app/explore/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { useRouter } from 'next/navigation';
import 'leaflet/dist/leaflet.css';

interface DestinationMarker {
  slug: string;
  name: string;
  lat: number;
  lng: number;
  active_trip_count: number;
  active_user_count: number;
  disciplines: string[];
  date_range: {
    earliest_arrival: string;
    latest_departure: string;
  };
}

export default function ExplorePage() {
  const router = useRouter();
  const [destinations, setDestinations] = useState<DestinationMarker[]>([]);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    disciplines: [] as string[],
  });
  const [selectedDest, setSelectedDest] = useState<DestinationMarker | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchMapData();
  }, [filters]);

  const fetchMapData = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.disciplines.length > 0) {
        params.append('disciplines', filters.disciplines.join(','));
      }

      const response = await api.get(`/api/map/destinations/?${params}`);
      setDestinations(response.destinations);
    } catch (error) {
      console.error('Failed to fetch map data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getMarkerColor = (count: number) => {
    if (count >= 10) return 'red';
    if (count >= 3) return 'orange';
    if (count >= 1) return 'green';
    return 'gray';
  };

  return (
    <div className="h-screen w-full flex">
      {/* Sidebar Filters */}
      <MapFilters
        filters={filters}
        onFilterChange={setFilters}
      />

      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer
          center={[20, 0]}
          zoom={2}
          className="h-full w-full"
          scrollWheelZoom={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />

          {destinations.map((dest) => (
            <Marker
              key={dest.slug}
              position={[dest.lat, dest.lng]}
              eventHandlers={{
                click: () => setSelectedDest(dest),
              }}
            >
              <Popup>
                <DestinationPopup
                  destination={dest}
                  onViewMatches={() => {
                    router.push(`/matches?destination=${dest.slug}`);
                  }}
                />
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
            <div className="spinner">Loading...</div>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

#### MapFilters Component

```typescript
// components/MapFilters.tsx

interface MapFiltersProps {
  filters: {
    start_date: string;
    end_date: string;
    disciplines: string[];
  };
  onFilterChange: (filters: any) => void;
}

export default function MapFilters({ filters, onFilterChange }: MapFiltersProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const disciplines = [
    { value: 'sport', label: 'Sport', icon: '🧗' },
    { value: 'trad', label: 'Trad', icon: '🪢' },
    { value: 'bouldering', label: 'Boulder', icon: '🪨' },
    { value: 'multipitch', label: 'Multipitch', icon: '⛰️' },
  ];

  const toggleDiscipline = (disc: string) => {
    const newDisciplines = filters.disciplines.includes(disc)
      ? filters.disciplines.filter(d => d !== disc)
      : [...filters.disciplines, disc];

    onFilterChange({ ...filters, disciplines: newDisciplines });
  };

  return (
    <div className={`
      bg-white border-r shadow-lg
      transition-all duration-300
      ${isCollapsed ? 'w-12' : 'w-80'}
    `}>
      {/* Collapse button */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute top-4 -right-3 bg-white rounded-full p-2 shadow-md"
      >
        {isCollapsed ? '→' : '←'}
      </button>

      {!isCollapsed && (
        <div className="p-6 space-y-6">
          <h2 className="text-xl font-bold">Filters</h2>

          {/* Date Range */}
          <div className="space-y-3">
            <label className="block text-sm font-medium">Date Range</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => onFilterChange({ ...filters, start_date: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
            <span className="text-sm text-gray-500">to</span>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => onFilterChange({ ...filters, end_date: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>

          {/* Disciplines */}
          <div className="space-y-3">
            <label className="block text-sm font-medium">Disciplines</label>
            <div className="space-y-2">
              {disciplines.map(disc => (
                <label key={disc.value} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.disciplines.includes(disc.value)}
                    onChange={() => toggleDiscipline(disc.value)}
                    className="rounded"
                  />
                  <span>{disc.icon} {disc.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Clear filters */}
          <button
            onClick={() => onFilterChange({ start_date: '', end_date: '', disciplines: [] })}
            className="w-full px-4 py-2 text-sm text-gray-600 border rounded hover:bg-gray-50"
          >
            Clear Filters
          </button>
        </div>
      )}
    </div>
  );
}
```

---

#### DestinationPopup Component

```typescript
// components/DestinationPopup.tsx

interface DestinationPopupProps {
  destination: DestinationMarker;
  onViewMatches: () => void;
}

export default function DestinationPopup({ destination, onViewMatches }: DestinationPopupProps) {
  return (
    <div className="min-w-[250px] p-2">
      <h3 className="font-bold text-lg mb-2">{destination.name}</h3>

      <div className="space-y-2 mb-3">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium">👥 {destination.active_user_count}</span>
          <span className="text-gray-600">climbers</span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium">🗓️ {destination.active_trip_count}</span>
          <span className="text-gray-600">active trips</span>
        </div>

        {destination.date_range && (
          <div className="text-xs text-gray-500">
            {new Date(destination.date_range.earliest_arrival).toLocaleDateString()} -
            {new Date(destination.date_range.latest_departure).toLocaleDateString()}
          </div>
        )}

        <div className="flex gap-1">
          {destination.disciplines.map(d => (
            <span key={d} className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
              {d}
            </span>
          ))}
        </div>
      </div>

      <button
        onClick={onViewMatches}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        View Matches
      </button>
    </div>
  );
}
```

---

#### Custom Map Markers

```typescript
// components/CustomMarker.tsx

import L from 'leaflet';

export const createCustomMarker = (count: number, color: string) => {
  const htmlContent = `
    <div style="
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background-color: ${color};
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      border: 2px solid white;
    ">
      ${count}
    </div>
  `;

  return L.divIcon({
    html: htmlContent,
    className: 'custom-marker',
    iconSize: [40, 40],
    iconAnchor: [20, 40],
  });
};

// Color mapping
export const getMarkerColor = (count: number): string => {
  if (count >= 10) return '#ef4444'; // red-500
  if (count >= 3) return '#f59e0b';  // amber-500
  if (count >= 1) return '#10b981';  // green-500
  return '#9ca3af';  // gray-400
};
```

---

#### Map State Management

```typescript
// lib/map.ts

import { create } from 'zustand';

interface MapState {
  destinations: DestinationMarker[];
  selectedDestination: DestinationMarker | null;
  filters: {
    start_date: string;
    end_date: string;
    disciplines: string[];
  };
  isLoading: boolean;

  setDestinations: (destinations: DestinationMarker[]) => void;
  setSelectedDestination: (dest: DestinationMarker | null) => void;
  setFilters: (filters: Partial<MapState['filters']>) => void;
  fetchMapData: () => Promise<void>;
}

export const useMapStore = create<MapState>((set, get) => ({
  destinations: [],
  selectedDestination: null,
  filters: {
    start_date: '',
    end_date: '',
    disciplines: [],
  },
  isLoading: false,

  setDestinations: (destinations) => set({ destinations }),

  setSelectedDestination: (dest) => set({ selectedDestination: dest }),

  setFilters: (newFilters) => set((state) => ({
    filters: { ...state.filters, ...newFilters }
  })),

  fetchMapData: async () => {
    set({ isLoading: true });
    try {
      const { filters } = get();
      const params = new URLSearchParams();

      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.disciplines.length > 0) {
        params.append('disciplines', filters.disciplines.join(','));
      }

      const response = await api.get(`/api/map/destinations/?${params}`);
      set({ destinations: response.destinations });
    } catch (error) {
      console.error('Failed to fetch map data:', error);
    } finally {
      set({ isLoading: false });
    }
  },
}));
```

---

#### Install Dependencies

```bash
# Leaflet for maps (free, open-source)
npm install leaflet react-leaflet
npm install -D @types/leaflet

# Alternative: Mapbox GL (better visuals, paid tier)
# npm install mapbox-gl react-map-gl
```

---

#### CSS Fixes for Leaflet

```css
/* app/explore/page.module.css */

/* Fix Leaflet default marker icons */
.leaflet-container {
  width: 100%;
  height: 100%;
}

/* Custom marker styles */
.custom-marker {
  background: transparent;
  border: none;
}

/* Popup styles */
.leaflet-popup-content-wrapper {
  border-radius: 8px;
  padding: 0;
}

.leaflet-popup-content {
  margin: 0;
}
```

---

### 2.2 Pages & Routes

#### `/trips` - Trip List
- Show all user's trips
- Filter: Upcoming / Past / All
- "Create New Trip" button → `/trips/new`
- Each trip card:
  - Destination name + dates
  - Discipline icons
  - Availability summary (e.g., "5 days available")
  - "View Details" → `/trips/:id`

#### `/trips/new` - Create Trip
- Form fields:
  - Destination name (text input with autocomplete - Phase 2 enhancement)
  - Start date & End date (date pickers)
  - Preferred disciplines (multi-select checkboxes)
  - Crag notes (textarea)
- "Create Trip" button
- On success → redirect to `/trips/:id` (new trip detail page)

#### `/trips/:id` - Trip Detail
- Trip info header (destination, dates, disciplines)
- **Availability Calendar:**
  - Month view showing trip date range
  - Each day shows availability blocks (morning/afternoon/full_day/rest)
  - Click day to add/edit availability
- "Edit Trip" button → modal or inline edit
- "Find Matches" button → `/matches?trip=:id`

#### `/trips/:id/edit` - Edit Trip (Modal or Page)
- Form to update crag_notes, disciplines, is_active
- Cannot change dates/destination (must create new trip)

---

### 2.2 Components

#### `TripCard`
```typescript
interface TripCardProps {
  trip: Trip;
  onClick: () => void;
}

// Displays:
// - Destination name
// - Date range
// - Discipline icons
// - Availability count
```

#### `TripForm`
```typescript
interface TripFormProps {
  initialData?: Partial<Trip>;
  onSubmit: (data: TripFormData) => Promise<void>;
  onCancel: () => void;
}

// Form fields:
// - destination_name (required)
// - start_date, end_date (date pickers)
// - preferred_disciplines (checkboxes)
// - crag_notes (textarea)
```

#### `AvailabilityCalendar`
```typescript
interface AvailabilityCalendarProps {
  trip: Trip;
  availability: AvailabilityBlock[];
  onAddBlock: (date: string, timeBlock: string) => Promise<void>;
  onUpdateBlock: (id: string, data: Partial<AvailabilityBlock>) => Promise<void>;
  onDeleteBlock: (id: string) => Promise<void>;
}

// Calendar view:
// - Show only trip date range
// - Color-code time blocks (morning=blue, afternoon=orange, full_day=green, rest=gray)
// - Click day to open time block selector
```

#### `AvailabilityBlockSelector`
```typescript
interface AvailabilityBlockSelectorProps {
  date: string;
  existingBlocks: AvailabilityBlock[];
  onSave: (timeBlock: string, notes: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

// Modal or popover:
// - Radio buttons: Morning / Afternoon / Full Day / Rest Day
// - Notes input
// - Save/Delete buttons
```

---

### 2.3 State Management

```typescript
// lib/trips.ts

interface Trip {
  id: string;
  destination_name: string;
  destination_lat: number | null;
  destination_lng: number | null;
  start_date: string; // ISO date
  end_date: string;
  preferred_disciplines: string[];
  crag_notes: string;
  is_active: boolean;
  availability: AvailabilityBlock[];
}

interface AvailabilityBlock {
  id: string;
  trip: string;
  date: string;
  time_block: 'morning' | 'afternoon' | 'full_day' | 'rest';
  notes: string;
}

// Zustand store
export const useTripStore = create<TripState>((set) => ({
  trips: [],
  currentTrip: null,
  isLoading: false,

  fetchTrips: async () => { ... },
  createTrip: async (data: TripFormData) => { ... },
  updateTrip: async (id: string, data: Partial<Trip>) => { ... },
  deleteTrip: async (id: string) => { ... },
  fetchTripDetail: async (id: string) => { ... },

  addAvailability: async (tripId: string, block: AvailabilityBlockInput) => { ... },
  updateAvailability: async (id: string, data: Partial<AvailabilityBlock>) => { ... },
  deleteAvailability: async (id: string) => { ... },
}));
```

---

## 3. Backend Implementation Details

### 3.1 Serializers

```python
# trips/serializers.py

from rest_framework import serializers
from .models import Destination, Crag, Trip, AvailabilityBlock
from datetime import date


# ==============================================================================
# DESTINATION & CRAG SERIALIZERS
# ==============================================================================

class DestinationSerializer(serializers.ModelSerializer):
    """Read-only serializer for destinations"""

    class Meta:
        model = Destination
        fields = [
            'slug', 'name', 'country', 'lat', 'lng',
            'description', 'image_url', 'primary_disciplines', 'season'
        ]
        read_only_fields = fields


class DestinationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for destination lists/autocomplete"""

    class Meta:
        model = Destination
        fields = ['slug', 'name', 'country', 'lat', 'lng', 'primary_disciplines', 'season']
        read_only_fields = fields


class CragSerializer(serializers.ModelSerializer):
    """Read-only serializer for crags"""

    class Meta:
        model = Crag
        fields = ['id', 'name', 'disciplines', 'route_count', 'approach_time', 'description']
        read_only_fields = fields


# ==============================================================================
# TRIP & AVAILABILITY SERIALIZERS
# ==============================================================================

class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'trip', 'date', 'time_block', 'notes']
        read_only_fields = ['id', 'trip']

    def validate_date(self, value):
        # Validate date is within trip date range
        trip = self.context.get('trip')
        if trip and not (trip.start_date <= value <= trip.end_date):
            raise serializers.ValidationError(
                f"Date must be between {trip.start_date} and {trip.end_date}"
            )
        return value

    def validate(self, data):
        # Check for unique constraint (trip, date, time_block) with better error message
        trip = self.context.get('trip')
        if trip:
            existing = AvailabilityBlock.objects.filter(
                trip=trip,
                date=data['date'],
                time_block=data['time_block']
            ).exists()

            if existing:
                raise serializers.ValidationError({
                    'time_block': f"You already have a {data['time_block']} block for {data['date']}"
                })

        return data


class TripSerializer(serializers.ModelSerializer):
    """Full trip serializer with nested destination and crags"""

    # Nested read-only fields
    destination = DestinationSerializer(read_only=True)
    preferred_crags = CragSerializer(many=True, read_only=True)
    availability = AvailabilityBlockSerializer(many=True, read_only=True)

    # Write-only fields for creation/update
    destination_slug = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Destination.objects.all(),
        source='destination',
        write_only=True
    )
    preferred_crag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Crag.objects.all(),
        source='preferred_crags',
        write_only=True,
        required=False
    )

    class Meta:
        model = Trip
        fields = [
            'id', 'user',
            # Read fields
            'destination', 'preferred_crags', 'availability',
            # Write fields
            'destination_slug', 'preferred_crag_ids',
            # Common fields
            'custom_crag_notes', 'start_date', 'end_date',
            'preferred_disciplines', 'notes', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'destination', 'preferred_crags', 'availability']

    def validate(self, data):
        # Validate date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    'end_date': "End date must be on or after start date"
                })

            if start_date < date.today():
                raise serializers.ValidationError({
                    'start_date': "Start date cannot be in the past"
                })

        # Validate preferred_crags belong to destination
        destination = data.get('destination')
        preferred_crags = data.get('preferred_crags', [])

        if destination and preferred_crags:
            for crag in preferred_crags:
                if crag.destination != destination:
                    raise serializers.ValidationError({
                        'preferred_crag_ids': f"Crag '{crag.name}' does not belong to {destination.name}"
                    })

        return data


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for trip lists"""

    destination = DestinationListSerializer(read_only=True)
    availability_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'destination', 'start_date', 'end_date',
            'preferred_disciplines', 'is_active', 'notes',
            'availability_count'
        ]
        read_only_fields = fields

    def get_availability_count(self, obj):
        return obj.availability.count()


class TripUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating trips (excludes dates and destination)"""

    preferred_crag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Crag.objects.all(),
        source='preferred_crags',
        required=False
    )

    class Meta:
        model = Trip
        fields = [
            'custom_crag_notes', 'preferred_disciplines', 'notes',
            'is_active', 'preferred_crag_ids'
        ]

    def validate_preferred_crag_ids(self, value):
        # Ensure crags belong to the trip's destination
        trip = self.instance
        if trip:
            for crag in value:
                if crag.destination != trip.destination:
                    raise serializers.ValidationError(
                        f"Crag '{crag.name}' does not belong to {trip.destination.name}"
                    )
        return value
```

---

### 3.2 Views

```python
# trips/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from datetime import date
from .models import Destination, Crag, Trip, AvailabilityBlock
from .serializers import (
    DestinationSerializer, DestinationListSerializer,
    CragSerializer, TripSerializer, TripListSerializer,
    TripUpdateSerializer, AvailabilityBlockSerializer
)


# ==============================================================================
# DESTINATION & CRAG VIEWSETS
# ==============================================================================

class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for destinations (for autocomplete/browsing)"""
    queryset = Destination.objects.all()
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return DestinationListSerializer
        return DestinationSerializer

    def get_queryset(self):
        queryset = Destination.objects.all()

        # Search filter for autocomplete
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Limit for autocomplete
        limit = self.request.query_params.get('limit', 20)
        return queryset[:int(limit)]

    @action(detail=True, methods=['get'], url_path='crags')
    def crags(self, request, slug=None):
        """Get all crags for a destination"""
        destination = self.get_object()
        crags = destination.crags.all()
        serializer = CragSerializer(crags, many=True)
        return Response({
            'destination': {
                'slug': destination.slug,
                'name': destination.name
            },
            'crags': serializer.data
        })


# ==============================================================================
# TRIP VIEWSET
# ==============================================================================

@method_decorator(ratelimit(key='user', rate='20/h', method='POST'), name='create')
class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TripListSerializer
        elif self.action in ['update', 'partial_update']:
            return TripUpdateSerializer
        return TripSerializer

    def get_queryset(self):
        queryset = Trip.objects.filter(user=self.request.user).select_related('destination').prefetch_related('preferred_crags', 'availability')

        # Filters
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            queryset = queryset.filter(start_date__gte=date.today())

        return queryset.order_by('start_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def next(self, request):
        """Get next upcoming trip"""
        trip = Trip.objects.filter(
            user=request.user,
            start_date__gte=date.today(),
            is_active=True
        ).select_related('destination').prefetch_related('preferred_crags').order_by('start_date').first()

        if trip:
            serializer = TripSerializer(trip)
            return Response(serializer.data)
        else:
            return Response({'detail': 'No upcoming trips'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='availability')
    def add_availability(self, request, pk=None):
        """Add a single availability block"""
        trip = self.get_object()
        serializer = AvailabilityBlockSerializer(data=request.data, context={'trip': trip})
        serializer.is_valid(raise_exception=True)
        serializer.save(trip=trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='availability/bulk')
    @method_decorator(ratelimit(key='user', rate='10/h', method='POST'))
    def bulk_add_availability(self, request, pk=None):
        """Bulk add availability blocks"""
        trip = self.get_object()
        blocks_data = request.data.get('blocks', [])

        created_blocks = []
        errors = []

        for block_data in blocks_data:
            serializer = AvailabilityBlockSerializer(data=block_data, context={'trip': trip})
            if serializer.is_valid():
                block = serializer.save(trip=trip)
                created_blocks.append(block)
            else:
                errors.append({
                    'block': block_data,
                    'errors': serializer.errors
                })

        return Response({
            'created': len(created_blocks),
            'failed': len(errors),
            'availability': AvailabilityBlockSerializer(created_blocks, many=True).data,
            'errors': errors if errors else None
        }, status=status.HTTP_201_CREATED if created_blocks else status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# AVAILABILITY BLOCK VIEWSET
# ==============================================================================

class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(trip__user=self.request.user).select_related('trip')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self, 'trip'):
            context['trip'] = self.trip
        return context


# ==============================================================================
# MAP VIEWSETS (Phase 3.5 - Advanced)
# ==============================================================================

# NOTE: Map endpoints require complex aggregation queries
# These will be added in Phase 3.5 or can be skipped for MVP
# Example endpoint: GET /api/map/destinations/
# - Count trips per destination
# - Count unique users per destination
# - Filter by date range and disciplines
# - Return aggregated data for map markers
```

---

### 3.3 URLs

```python
# trips/urls.py

from rest_framework.routers import DefaultRouter
from .views import DestinationViewSet, TripViewSet, AvailabilityBlockViewSet

router = DefaultRouter()
router.register(r'destinations', DestinationViewSet, basename='destination')
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'availability', AvailabilityBlockViewSet, basename='availability')

urlpatterns = router.urls
```

```python
# config/urls.py

urlpatterns = [
    ...
    path('api/', include('trips.urls')),
]
```

**Generated Routes:**
- `GET /api/destinations/` - List destinations (with search filter)
- `GET /api/destinations/:slug/` - Destination detail
- `GET /api/destinations/:slug/crags/` - Get crags for destination
- `GET /api/trips/` - List user's trips
- `POST /api/trips/` - Create trip
- `GET /api/trips/:id/` - Trip detail
- `PATCH /api/trips/:id/` - Update trip
- `DELETE /api/trips/:id/` - Delete trip
- `GET /api/trips/next/` - Get next upcoming trip
- `POST /api/trips/:id/availability/` - Add availability block
- `POST /api/trips/:id/availability/bulk/` - Bulk add availability
- `GET /api/availability/` - List availability blocks
- `GET /api/availability/:id/` - Availability detail
- `PATCH /api/availability/:id/` - Update availability
- `DELETE /api/availability/:id/` - Delete availability

---

## 4. UI/UX Considerations

### 4.1 Trip Creation Flow
1. User clicks "Create Trip"
2. Form opens with:
   - Destination autocomplete (Phase 2: use Google Places API or seed data)
   - Date range picker (highlight conflicts if overlaps existing trip)
   - Discipline checkboxes with icons
   - Crag notes textarea
3. On submit → create trip → redirect to trip detail page
4. Prompt user to add availability

### 4.2 Availability Calendar UX
- Show month view with only trip date range highlighted
- Each day cell shows:
  - Morning block (top half)
  - Afternoon block (bottom half)
  - Full day (whole cell)
  - Rest day (strikethrough or gray)
- Click day → modal with time block options
- Quick add: Click + drag to select multiple days → bulk add modal

### 4.3 Mobile Considerations
- Use date picker native to mobile (not custom)
- Availability calendar: vertical list view on mobile (not calendar grid)
- Swipe gestures for navigating trip list

---

## 5. Implementation Checklist

### Backend
- [ ] **Serializers** (trips/serializers.py)
  - [ ] DestinationSerializer (read-only)
  - [ ] DestinationListSerializer (lightweight for autocomplete)
  - [ ] CragSerializer (read-only)
  - [ ] TripSerializer (with nested destination/crags, write-only slug/ids)
  - [ ] TripListSerializer (lightweight for lists)
  - [ ] TripUpdateSerializer (excludes dates/destination)
  - [ ] AvailabilityBlockSerializer (with date range validation)

- [ ] **ViewSets** (trips/views.py)
  - [ ] DestinationViewSet (read-only, search filter, crags action)
  - [ ] TripViewSet (CRUD + next endpoint + availability actions)
  - [ ] AvailabilityBlockViewSet (CRUD for individual blocks)

- [ ] **URL Configuration** (trips/urls.py)
  - [ ] Register DestinationViewSet
  - [ ] Register TripViewSet
  - [ ] Register AvailabilityBlockViewSet
  - [ ] Include in main config/urls.py

- [ ] **Validation & Security**
  - [ ] Date validation (start_date >= today, end_date >= start_date)
  - [ ] Crag-destination relationship validation
  - [ ] Availability block date range validation
  - [ ] Unique constraint validation (trip, date, time_block)
  - [ ] Rate limiting (20/hour for trip creation, 10/hour for bulk availability)
  - [ ] User ownership validation (can only view/edit own trips)

- [ ] **Tests** (trips/tests.py)
  - [ ] Test destination list and detail
  - [ ] Test destination crags endpoint
  - [ ] Test trip creation with validation
  - [ ] Test trip listing with filters (is_active, upcoming)
  - [ ] Test trip detail retrieval
  - [ ] Test trip update (allowed and disallowed fields)
  - [ ] Test trip deletion
  - [ ] Test next upcoming trip endpoint
  - [ ] Test add availability block
  - [ ] Test bulk add availability
  - [ ] Test availability validation errors
  - [ ] Test rate limiting

### Frontend
- [ ] **State Management** (lib/trips.ts)
  - [ ] Create trip store with Zustand
  - [ ] Implement fetchTrips
  - [ ] Implement createTrip
  - [ ] Implement updateTrip
  - [ ] Implement deleteTrip
  - [ ] Implement availability CRUD methods

- [ ] **Pages**
  - [ ] Build trip list page (`/trips`)
  - [ ] Build trip creation form (`/trips/new`)
  - [ ] Build trip detail page (`/trips/:id`)
  - [ ] Build trip edit modal/page

- [ ] **Components**
  - [ ] TripCard component
  - [ ] TripForm component
  - [ ] AvailabilityCalendar component
  - [ ] AvailabilityBlockSelector modal
  - [ ] DestinationAutocomplete component (Phase 3.5)

- [ ] **Map View (Phase 3.5 - Optional for MVP)**
  - [ ] Map page (`/explore`)
  - [ ] MapFilters component
  - [ ] DestinationPopup component
  - [ ] Install Leaflet dependencies
  - [ ] Create map state management
  - [ ] Implement map endpoints on backend

- [ ] **UI Polish**
  - [ ] Add date pickers (react-datepicker or similar)
  - [ ] Add discipline icons
  - [ ] Add loading states
  - [ ] Add error handling
  - [ ] Test on mobile

### Testing
- [ ] **Backend API Tests**
  - [ ] Test create trip flow
  - [ ] Test add availability blocks
  - [ ] Test bulk add availability
  - [ ] Test edit/delete trip
  - [ ] Test date validation errors
  - [ ] Test crag validation errors
  - [ ] Test rate limiting triggers

- [ ] **Frontend E2E Tests**
  - [ ] Test trip creation flow
  - [ ] Test trip editing
  - [ ] Test availability calendar interaction
  - [ ] Test mobile responsiveness

---

## 6. Future Enhancements (Phase 2+)

- Destination autocomplete with seed data (popular crags)
- Location search with geocoding
- Calendar sync (Google Calendar, iCal export)
- Recurring trips (e.g., "Every weekend at local gym")
- Trip templates

---

## 7. Estimated Timeline

### Backend (8-10 hours)
- Serializers (all 7 serializers with validation): 2 hours
- ViewSets (3 ViewSets with rate limiting): 2 hours
- URL configuration and integration: 0.5 hours
- Tests (comprehensive backend tests): 3 hours
- Documentation and manual testing: 1.5 hours

### Frontend (12-14 hours)
- Trip state management (Zustand store): 2 hours
- Trip CRUD pages and forms: 4 hours
- Availability calendar component: 4 hours
- UI polish and error handling: 2 hours
- Frontend tests: 2 hours

### Map View (Phase 3.5 - Optional) (6-8 hours)
- Backend map aggregation endpoints: 2 hours
- Map implementation (Leaflet setup): 2 hours
- Map filters and state management: 2 hours
- Testing and polish: 2 hours

**Total (MVP - without map): ~20-24 hours**
**Total (with map): ~26-32 hours**

---

## Next Phase
**Phase 4: Matching Algorithm & Feed**
