# Spec Updates Summary

## Changes Made

### Phase 1: Data Models & Grade System
**Updated:** Added hierarchical location database

**New Models:**
- `Destination` - Top-level climbing regions (e.g., "Red River Gorge, KY")
- `Crag` - Specific climbing areas within destinations (e.g., "Muir Valley")

**Updated Models:**
- `Trip` - Now uses ForeignKey to Destination + ManyToMany to Crag (instead of free text)

**New Seed Data:**
- Added `seed_locations` management command
- Includes ~9 top destinations with major crags:
  - Red River Gorge, KY (USA)
  - Railay, Krabi (Thailand)
  - Kalymnos (Greece)
  - Yosemite, CA (USA)
  - Red Rocks, NV (USA)
  - Smith Rock, OR (USA)
  - El Chorro (Spain)
  - Fontainebleau (France)
  - Tonsai, Krabi (Thailand)

**Time Estimate:** 8 hours → **11 hours** (+3 hours)

---

### Phase 3: Trip & Availability Management
**Updated:** Added map view and location features

**New API Endpoints:**
- `GET /api/destinations/` - List destinations (autocomplete)
- `GET /api/destinations/:slug/crags/` - Get crags for a destination
- `GET /api/map/destinations/` - Map data (destinations with active trips)
- `GET /api/map/destinations/:slug/` - Map destination detail

**Updated API Endpoints:**
- `POST /api/trips/` - Now uses `destination` (slug) + `preferred_crags` (UUIDs)

**New Frontend Pages:**
- `/explore` - Interactive map view with Leaflet/OSM
  - Shows destinations with active trips
  - Color-coded by activity level
  - Click markers for details
  - Filters: date range, disciplines

**New Frontend Components:**
- `MapView` - Main map component
- `MapFilters` - Sidebar filters for map
- `DestinationAutocomplete` - Destination search/select
- `CragSelector` - Multi-select crags for trip

**Updated Frontend Components:**
- `TripForm` - Now uses destination autocomplete + crag selector

**Time Estimate:** 13 hours → **19 hours** (+6 hours)

---

### Phase 4: Matching Algorithm & Feed
**Updated:** Crag-aware matching

**Updated Matching Logic:**
```python
# Location scoring (0-30 points)
- Same destination + same crags: 30 points
- Same destination, different crags: 20 points
- Same destination, no crags specified: 25 points
- Different destinations: 0 points
```

**Benefits:**
- Better precision (Muir Valley climbers match with Muir Valley climbers)
- Still flexible (someone with no crag preference sees everyone)
- Granular recommendations

**Time Estimate:** No change (17 hours) - logic update only

---

### Phase 5: Sessions & Messaging
**Updated:** Crag selection in invitations

**Updated Invitation Flow:**
- Destination pre-filled from trip
- Crag dropdown (select one crag for this session)
- Optional text input for wall/sector

**Example:**
```json
{
  "trip_id": "uuid",
  "invitee_id": "uuid",
  "proposed_date": "2026-03-16",
  "time_block": "morning",
  "crag_id": "uuid-thaiwand",  // NEW
  "wall_sector": "Humanality Wall",  // NEW (optional)
  "goal": "Project 5.11s"
}
```

**Time Estimate:** No change (17 hours) - minor UI update

---

## New Total Time Estimate

| Phase | Original | Updated | Change |
|-------|----------|---------|--------|
| Phase 1 | 8 hrs | **11 hrs** | +3 hrs |
| Phase 2 | 14 hrs | 14 hrs | - |
| Phase 3 | 13 hrs | **19 hrs** | +6 hrs |
| Phase 4 | 17 hrs | 17 hrs | - |
| Phase 5 | 17 hrs | 17 hrs | - |
| Phase 6 | 15 hrs | 15 hrs | - |
| **Total** | **84 hrs** | **93 hrs** | **+9 hrs** |

---

## Key Benefits

### 1. Better Matching Precision
- "I'm going to Muir Valley" matches with other Muir Valley climbers
- Not just "I'm going to Red River Gorge" (too broad)

### 2. Trip Planning
- Interactive map shows where climbers are going
- Discover popular destinations
- See trends (e.g., "Railay is busy in March")

### 3. Data Quality
- Standardized destination names (no typos)
- Consistent coordinates for mapping
- Crag metadata (approach time, route count, etc.)

### 4. Future Expansion
- User-submitted crags (moderated)
- Route database integration
- Seasonal recommendations
- "Near me" feature

---

## Implementation Priority

**Phase 1 (CRITICAL):**
- ✅ Must implement Destination + Crag models from the start
- ✅ Seed data needed before any trips can be created

**Phase 3 (HIGH):**
- ✅ Destination autocomplete (required for trip creation)
- ✅ Crag selector (optional in MVP, can default to "any crag")
- 🔵 Map view (nice-to-have, can be Phase 1.5)

**Recommendation:**
- Build Destination/Crag models in Phase 1 ✅
- Add autocomplete in Phase 3 ✅
- Map view can be added after core matching works (or include in Phase 3 for wow factor)

---

## Files Updated

- ✅ `docs/phase-1-data-models.md` - Added Destination, Crag models + seed data
- ✅ `docs/phase-3-trips.md` - Added API endpoints + Map View (partial)
- ⏳ `docs/phase-4-matching.md` - Need to update matching logic
- ⏳ `docs/phase-5-sessions.md` - Need to update invitation with crag
- ⏳ `docs/README.md` - Need to update time estimates

---

## Next Steps

1. ✅ Phase 1 updated
2. 🔄 Phase 3 partially updated (need to finish Map View component spec)
3. ⏳ Update Phase 4 matching logic
4. ⏳ Update Phase 5 invitation
5. ⏳ Update main README with new estimates
