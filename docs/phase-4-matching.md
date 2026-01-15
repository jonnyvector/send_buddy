# Phase 4: Matching Algorithm & Feed

## Overview
Implement the core matchmaking algorithm and match feed UI. This is the **most critical** feature of Send Buddy.

**Recent Updates:**
- Fixed model field references (destination_name → destination.name)
- Added comprehensive serializers section with read/write separation
- Changed to ViewSets for consistency with Phase 2 & 3
- Added rate limiting and security best practices
- Added URL configuration section
- Added queryset optimization guidance
- Moved Redis caching to future enhancements (not MVP)
- Note: User blocking (Phase 6) excluded from MVP - can be added later

## Dependencies
- Phase 1 (All models + Grade system) ✓
- Phase 2 (Authentication) ✓
- Phase 3 (Trips) ✓
- Phase 6 (Blocking - optional, recommended for production)

---

## 1. Matching Algorithm Specification

### 1.1 Core Matching Logic

**Goal:** Given a user's trip, return the top N most compatible users with overlapping trips.

**Input:**
- User ID
- Trip ID (optional - defaults to next upcoming trip)
- Limit (default 10)

**Output:**
- List of match objects with:
  - Matched user profile
  - Match score (0-100)
  - Reasons for match
  - Overlapping details

---

### 1.2 Scoring Weights (Phase 1 MVP)

| Factor | Weight | Notes |
|--------|--------|-------|
| **Location overlap** | 30 | Same destination (exact match) |
| **Date overlap** | 20 | Number of overlapping days (max 20 points for 5+ days) |
| **Discipline overlap** | 20 | Shared disciplines |
| **Grade compatibility** | 15 | Overlapping comfortable grade ranges |
| **Risk tolerance match** | 10 | 0=perfect match, -10=opposite |
| **Availability overlap** | 5 | Shared available time blocks |

**Maximum score:** 100

---

### 1.3 Scoring Formula Details

#### Location Match (0-30 points)
```python
def score_location(trip1, trip2):
    # Exact destination match (using ForeignKey relationship)
    if trip1.destination == trip2.destination:
        return 30

    # Future: Use lat/lng proximity for nearby destinations
    # if haversine_distance(trip1.destination, trip2.destination) < 50km:
    #     return 20

    return 0
```

#### Date Overlap (0-20 points)
```python
def score_date_overlap(trip1, trip2):
    overlap_start = max(trip1.start_date, trip2.start_date)
    overlap_end = min(trip1.end_date, trip2.end_date)

    if overlap_start > overlap_end:
        return 0  # No overlap

    overlap_days = (overlap_end - overlap_start).days + 1
    return min(20, overlap_days * 4)  # 4 points per overlapping day, max 20
```

#### Discipline Overlap (0-20 points)
```python
def score_discipline(trip1, trip2, user1_disciplines, user2_disciplines):
    trip_disciplines = set(trip1.preferred_disciplines) & set(trip2.preferred_disciplines)

    if not trip_disciplines:
        return 0

    # Check if both users have profiles for shared disciplines
    user1_has = {d.discipline for d in user1_disciplines}
    user2_has = {d.discipline for d in user2_disciplines}

    common = trip_disciplines & user1_has & user2_has

    if not common:
        return 5  # Partial: trip overlap but no user profiles

    return 20  # Full match
```

#### Grade Compatibility (0-15 points)
```python
def score_grade_compatibility(user1_disciplines, user2_disciplines, shared_discipline):
    # Get discipline profiles
    user1_profile = user1_disciplines.get(discipline=shared_discipline)
    user2_profile = user2_disciplines.get(discipline=shared_discipline)

    # Check if comfortable ranges overlap
    u1_min = user1_profile.comfortable_grade_min_score
    u1_max = user1_profile.comfortable_grade_max_score
    u2_min = user2_profile.comfortable_grade_min_score
    u2_max = user2_profile.comfortable_grade_max_score

    # Calculate overlap
    overlap_start = max(u1_min, u2_min)
    overlap_end = min(u1_max, u2_max)

    if overlap_start > overlap_end:
        return 0  # No grade overlap

    overlap_range = overlap_end - overlap_start
    avg_range = ((u1_max - u1_min) + (u2_max - u2_min)) / 2

    overlap_ratio = overlap_range / avg_range if avg_range > 0 else 0

    return int(15 * overlap_ratio)  # 0-15 points
```

#### Risk Tolerance (0 to -10 points)
```python
RISK_SCORES = {'conservative': 0, 'balanced': 1, 'aggressive': 2}

def score_risk_tolerance(user1, user2):
    diff = abs(RISK_SCORES[user1.risk_tolerance] - RISK_SCORES[user2.risk_tolerance])

    if diff == 0:
        return 10  # Perfect match
    elif diff == 1:
        return 3   # Acceptable
    else:
        return -10  # Mismatch (conservative + aggressive = bad)
```

#### Availability Overlap (0-5 points)
```python
def score_availability(trip1_avail, trip2_avail):
    # Find matching date + time_block combinations
    trip1_slots = {(a.date, a.time_block) for a in trip1_avail if a.time_block != 'rest'}
    trip2_slots = {(a.date, a.time_block) for a in trip2_avail if a.time_block != 'rest'}

    overlap_count = len(trip1_slots & trip2_slots)

    return min(5, overlap_count)  # 1 point per overlapping slot, max 5
```

---

### 1.4 Match Reasons

Generate human-readable reasons for the match:

```python
reasons = []

if location_score > 0:
    reasons.append(f"Both in {trip.destination.name}")

if date_score > 0:
    reasons.append(f"{overlap_days} day overlap")

if discipline_score > 0:
    common_disciplines = ', '.join(shared_disciplines)
    reasons.append(f"Both climb {common_disciplines}")

if grade_score > 10:
    reasons.append(f"Similar {discipline} grades")

if risk_score == 10:
    reasons.append("Same risk tolerance")

if availability_score > 0:
    reasons.append(f"{overlap_count} matching time slots")
```

---

### 1.5 Filtering & Exclusions

**CRITICAL:** Exclude users who:
- Have `profile_visible = False`
- Have no active trips
- Have `email_verified = False`
- Are the current user (don't match with yourself)

**Phase 6 (Blocking):** When implemented, also exclude:
- Users blocked by the current user
- Users who have blocked the current user

---

## 2. Backend API Endpoints

### 2.1 Get Matches for Trip

**GET `/api/matches/?trip=<trip_id>`**

Query params:
- `trip` (UUID, optional - defaults to next upcoming trip)
- `limit` (int, default 10, max 50)
- `discipline` (optional filter, e.g., "sport")

**Rate Limiting:**
- 30 requests per user per minute

**Permissions:**
- User must be authenticated

Response (200):
```json
{
  "trip": {
    "id": "uuid",
    "destination": {
      "slug": "railay",
      "name": "Railay, Krabi",
      "country": "Thailand"
    },
    "start_date": "2026-03-15",
    "end_date": "2026-03-28"
  },
  "matches": [
    {
      "user": {
        "id": "uuid",
        "display_name": "Sarah Climbs",
        "avatar": "https://...",
        "bio": "Sport climbing enthusiast...",
        "home_location": "Bangkok, Thailand",
        "risk_tolerance": "balanced",
        "disciplines": [
          {
            "discipline": "sport",
            "comfortable_grade_min_display": "5.10a",
            "comfortable_grade_max_display": "5.11c"
          }
        ],
        "experience_tags": ["lead_belay_certified", "has_rope"]
      },
      "trip": {
        "id": "uuid",
        "destination": {
          "slug": "railay",
          "name": "Railay, Krabi",
          "country": "Thailand"
        },
        "start_date": "2026-03-10",
        "end_date": "2026-03-25",
        "preferred_disciplines": ["sport"]
      },
      "match_score": 85,
      "reasons": [
        "Both in Railay, Krabi",
        "13 day overlap",
        "Both climb sport",
        "Similar sport grades",
        "Same risk tolerance"
      ],
      "overlap_dates": {
        "start": "2026-03-15",
        "end": "2026-03-25",
        "days": 10
      }
    }
  ]
}
```

Response (404) - No upcoming trips:
```json
{
  "detail": "No upcoming trips"
}
```

Response (400) - Invalid trip ID:
```json
{
  "detail": "Invalid trip ID"
}
```

---

### 2.2 Get Match Detail

**GET `/api/matches/:user_id/?trip=<trip_id>`**

Shows detailed match info for a specific user.

Response (200):
```json
{
  "user": { ... full profile ... },
  "trip": { ... their trip ... },
  "match_score": 85,
  "reasons": [...],
  "overlap_dates": { ... },
  "availability_overlap": [
    {
      "date": "2026-03-16",
      "time_blocks": ["morning", "afternoon"]
    }
  ],
  "shared_disciplines": ["sport"],
  "grade_compatibility": {
    "sport": {
      "overlap_range": "5.10a - 5.11c",
      "compatibility": "high"
    }
  }
}
```

---

## 3. Backend Serializers

### 3.1 Serializers

```python
# matching/serializers.py

from rest_framework import serializers
from users.models import User
from users.serializers import UserSerializer, DisciplineProfileSerializer
from trips.serializers import TripListSerializer, DestinationListSerializer


class MatchTripSerializer(serializers.Serializer):
    """Lightweight trip serializer for match responses"""
    id = serializers.UUIDField(read_only=True)
    destination = DestinationListSerializer(read_only=True)
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)
    preferred_disciplines = serializers.ListField(read_only=True)


class MatchUserSerializer(serializers.Serializer):
    """User serializer for match responses"""
    id = serializers.UUIDField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    bio = serializers.CharField(read_only=True)
    home_location = serializers.CharField(read_only=True)
    risk_tolerance = serializers.CharField(read_only=True)
    disciplines = DisciplineProfileSerializer(many=True, read_only=True)
    experience_tags = serializers.SerializerMethodField()

    def get_experience_tags(self, obj):
        return [tag.tag.slug for tag in obj.experience_tags.all()]


class OverlapDatesSerializer(serializers.Serializer):
    """Date overlap information"""
    start = serializers.DateField()
    end = serializers.DateField()
    days = serializers.IntegerField()


class MatchSerializer(serializers.Serializer):
    """Single match result"""
    user = MatchUserSerializer(read_only=True)
    trip = MatchTripSerializer(read_only=True)
    match_score = serializers.IntegerField(read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    overlap_dates = OverlapDatesSerializer(read_only=True)


class MatchListSerializer(serializers.Serializer):
    """Match list response"""
    trip = MatchTripSerializer(read_only=True)
    matches = MatchSerializer(many=True, read_only=True)


class AvailabilityOverlapSerializer(serializers.Serializer):
    """Availability overlap for match detail"""
    date = serializers.DateField()
    time_blocks = serializers.ListField(child=serializers.CharField())


class GradeCompatibilitySerializer(serializers.Serializer):
    """Grade compatibility info for a discipline"""
    overlap_range = serializers.CharField()
    compatibility = serializers.CharField()  # "high", "medium", "low"


class MatchDetailSerializer(serializers.Serializer):
    """Detailed match response"""
    user = MatchUserSerializer(read_only=True)
    trip = MatchTripSerializer(read_only=True)
    match_score = serializers.IntegerField(read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    overlap_dates = OverlapDatesSerializer(read_only=True)
    availability_overlap = AvailabilityOverlapSerializer(many=True, read_only=True)
    shared_disciplines = serializers.ListField(child=serializers.CharField(), read_only=True)
    grade_compatibility = serializers.DictField(child=GradeCompatibilitySerializer(), read_only=True)
```

---

## 4. Backend Implementation

### 4.1 Matching Service

```python
# matching/services.py

from typing import List, Dict
from django.db.models import Q
from users.models import User
from trips.models import Trip

class MatchingService:
    def __init__(self, user: User, trip: Trip, limit: int = 10):
        self.user = user
        self.trip = trip
        self.limit = limit

    def get_matches(self) -> List[Dict]:
        """Main matching function"""

        # Get candidate users
        candidates = self._get_candidates()

        # Score each candidate
        scored_matches = []
        for candidate in candidates:
            candidate_trip = self._get_candidate_trip(candidate)
            if not candidate_trip:
                continue

            score, reasons, details = self._calculate_match_score(candidate, candidate_trip)

            if score > 20:  # Minimum threshold
                scored_matches.append({
                    'user': candidate,
                    'trip': candidate_trip,
                    'match_score': score,
                    'reasons': reasons,
                    'overlap_dates': details['overlap_dates'],
                })

        # Sort by score descending
        scored_matches.sort(key=lambda x: x['match_score'], reverse=True)

        return scored_matches[:self.limit]

    def _get_candidates(self):
        """Get all eligible candidate users"""

        # TODO Phase 6: Add blocking filter
        # blocked_ids = self.user.blocking.values_list('blocked_id', flat=True)
        # blocked_by_ids = self.user.blocked_by.values_list('blocker_id', flat=True)
        # excluded_ids = set(blocked_ids) | set(blocked_by_ids)

        # Get all users with active trips overlapping my trip's dates
        candidates = User.objects.filter(
            trips__is_active=True,
            trips__start_date__lte=self.trip.end_date,
            trips__end_date__gte=self.trip.start_date,
            email_verified=True,
            profile_visible=True
        ).exclude(
            id=self.user.id  # Don't match with yourself
        ).select_related(
            # Optimize queries
        ).prefetch_related(
            'disciplines', 'experience_tags'
        ).distinct()

        return candidates

    def _get_candidate_trip(self, candidate: User):
        """Get the candidate's trip that overlaps with my trip"""
        return candidate.trips.filter(
            is_active=True,
            start_date__lte=self.trip.end_date,
            end_date__gte=self.trip.start_date,
            destination=self.trip.destination  # Same destination (ForeignKey)
        ).select_related('destination').prefetch_related('preferred_crags', 'availability').first()

    def _calculate_match_score(self, candidate: User, candidate_trip: Trip):
        """Calculate total match score"""

        score = 0
        reasons = []
        details = {}

        # 1. Location (30 points)
        location_score = self._score_location(candidate_trip)
        score += location_score
        if location_score > 0:
            reasons.append(f"Both in {self.trip.destination.name}")

        # 2. Date overlap (20 points)
        date_score, overlap_dates = self._score_date_overlap(candidate_trip)
        score += date_score
        details['overlap_dates'] = overlap_dates
        if date_score > 0:
            reasons.append(f"{overlap_dates['days']} day overlap")

        # 3. Discipline (20 points)
        discipline_score, shared = self._score_discipline(candidate, candidate_trip)
        score += discipline_score
        if shared:
            reasons.append(f"Both climb {', '.join(shared)}")

        # 4. Grade compatibility (15 points)
        grade_score = self._score_grade_compatibility(candidate, shared)
        score += grade_score
        if grade_score > 10:
            reasons.append(f"Similar grades")

        # 5. Risk tolerance (0 to -10)
        risk_score = self._score_risk_tolerance(candidate)
        score += risk_score
        if risk_score == 10:
            reasons.append("Same risk tolerance")

        # 6. Availability (5 points)
        avail_score = self._score_availability(candidate_trip)
        score += avail_score

        return score, reasons, details

    def _score_location(self, candidate_trip):
        # Compare ForeignKey IDs (more efficient than string comparison)
        if self.trip.destination_id == candidate_trip.destination_id:
            return 30
        return 0

    def _score_date_overlap(self, candidate_trip):
        overlap_start = max(self.trip.start_date, candidate_trip.start_date)
        overlap_end = min(self.trip.end_date, candidate_trip.end_date)

        if overlap_start > overlap_end:
            return 0, {}

        overlap_days = (overlap_end - overlap_start).days + 1
        score = min(20, overlap_days * 4)

        details = {
            'start': overlap_start,
            'end': overlap_end,
            'days': overlap_days
        }

        return score, details

    def _score_discipline(self, candidate, candidate_trip):
        trip_disciplines = set(self.trip.preferred_disciplines) & set(candidate_trip.preferred_disciplines)

        if not trip_disciplines:
            return 0, []

        # Check user profiles
        my_disciplines = {d.discipline for d in self.user.disciplines.all()}
        their_disciplines = {d.discipline for d in candidate.disciplines.all()}

        shared = list(trip_disciplines & my_disciplines & their_disciplines)

        if shared:
            return 20, shared
        else:
            return 5, list(trip_disciplines)

    def _score_grade_compatibility(self, candidate, shared_disciplines):
        if not shared_disciplines:
            return 0

        # For MVP, check first shared discipline
        discipline = shared_disciplines[0]

        try:
            my_profile = self.user.disciplines.get(discipline=discipline)
            their_profile = candidate.disciplines.get(discipline=discipline)
        except:
            return 0

        # Calculate grade overlap
        overlap_start = max(my_profile.comfortable_grade_min_score, their_profile.comfortable_grade_min_score)
        overlap_end = min(my_profile.comfortable_grade_max_score, their_profile.comfortable_grade_max_score)

        if overlap_start > overlap_end:
            return 0

        overlap_range = overlap_end - overlap_start
        avg_range = ((my_profile.comfortable_grade_max_score - my_profile.comfortable_grade_min_score) +
                     (their_profile.comfortable_grade_max_score - their_profile.comfortable_grade_min_score)) / 2

        overlap_ratio = overlap_range / avg_range if avg_range > 0 else 0

        return int(15 * overlap_ratio)

    def _score_risk_tolerance(self, candidate):
        RISK_SCORES = {'conservative': 0, 'balanced': 1, 'aggressive': 2}

        diff = abs(RISK_SCORES[self.user.risk_tolerance] - RISK_SCORES[candidate.risk_tolerance])

        if diff == 0:
            return 10
        elif diff == 1:
            return 3
        else:
            return -10

    def _score_availability(self, candidate_trip):
        my_avail = set(
            (a.date, a.time_block)
            for a in self.trip.availability.exclude(time_block='rest')
        )
        their_avail = set(
            (a.date, a.time_block)
            for a in candidate_trip.availability.exclude(time_block='rest')
        )

        overlap_count = len(my_avail & their_avail)
        return min(5, overlap_count)
```

---

### 4.2 Views (ViewSet)

```python
# matching/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from datetime import date
from trips.models import Trip
from .services import MatchingService
from .serializers import MatchListSerializer, MatchDetailSerializer


@method_decorator(ratelimit(key='user', rate='30/m', method='GET'), name='list')
class MatchViewSet(viewsets.ViewSet):
    """ViewSet for match operations"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get matches for a trip"""

        trip_id = request.query_params.get('trip')
        limit = int(request.query_params.get('limit', 10))

        # Get trip
        if trip_id:
            try:
                trip = Trip.objects.select_related('destination').prefetch_related(
                    'preferred_crags', 'availability'
                ).get(id=trip_id, user=request.user)
            except Trip.DoesNotExist:
                return Response(
                    {'detail': 'Trip not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get next upcoming trip
            trip = Trip.objects.filter(
                user=request.user,
                start_date__gte=date.today(),
                is_active=True
            ).select_related('destination').prefetch_related(
                'preferred_crags', 'availability'
            ).order_by('start_date').first()

            if not trip:
                return Response(
                    {'detail': 'No upcoming trips'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Run matching algorithm
        service = MatchingService(request.user, trip, limit=min(limit, 50))
        matches = service.get_matches()

        # Serialize response
        data = {
            'trip': trip,
            'matches': matches
        }
        serializer = MatchListSerializer(data)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        """Get detailed match info for a specific user"""

        trip_id = request.query_params.get('trip')
        matched_user_id = pk

        # Get trip (same logic as list)
        if trip_id:
            try:
                trip = Trip.objects.select_related('destination').prefetch_related(
                    'preferred_crags', 'availability'
                ).get(id=trip_id, user=request.user)
            except Trip.DoesNotExist:
                return Response(
                    {'detail': 'Trip not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            trip = Trip.objects.filter(
                user=request.user,
                start_date__gte=date.today(),
                is_active=True
            ).select_related('destination').prefetch_related(
                'preferred_crags', 'availability'
            ).order_by('start_date').first()

            if not trip:
                return Response(
                    {'detail': 'No upcoming trips'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Run matching for this specific user
        service = MatchingService(request.user, trip, limit=50)
        all_matches = service.get_matches()

        # Find the specific match
        matched_user = next(
            (m for m in all_matches if str(m['user'].id) == matched_user_id),
            None
        )

        if not matched_user:
            return Response(
                {'detail': 'Match not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Add detailed availability overlap and grade compatibility
        serializer = MatchDetailSerializer(matched_user)

        return Response(serializer.data)
```

---

### 4.3 URLs

```python
# matching/urls.py

from rest_framework.routers import DefaultRouter
from .views import MatchViewSet

router = DefaultRouter()
router.register(r'matches', MatchViewSet, basename='match')

urlpatterns = router.urls
```

```python
# config/urls.py

urlpatterns = [
    ...
    path('api/', include('matching.urls')),
]
```

**Generated Routes:**
- `GET /api/matches/` - List matches for a trip
- `GET /api/matches/:user_id/detail/` - Get match detail for specific user

---

## 5. Frontend Implementation

### 5.1 Pages & Routes

#### `/matches` - Match Feed
- Query param: `?trip=<trip_id>` (optional)
- Shows ranked list of matches
- Filter chips: Discipline, Grade range, Risk tolerance
- Each match card:
  - User avatar + name
  - Match score (visual indicator, e.g., stars or %)
  - Reasons (bullet list)
  - Overlap summary
  - "Send Invite" button

#### `/matches/:user_id` - Match Detail
- Full user profile
- Detailed compatibility breakdown
- Trip overlap visualization (calendar)
- Grade comparison chart
- "Send Invite" button

---

### 5.2 Components

#### `MatchCard`
```typescript
interface MatchCardProps {
  match: Match;
  onInvite: (userId: string) => void;
}

// Displays:
// - User avatar + name
// - Match score (e.g., 85% with color coding)
// - Top 3 reasons
// - Overlap dates
// - CTA button
```

#### `MatchScoreIndicator`
```typescript
interface MatchScoreIndicatorProps {
  score: number; // 0-100
}

// Visual:
// - 80-100: Green, 5 stars, "Excellent Match"
// - 60-79: Blue, 4 stars, "Great Match"
// - 40-59: Yellow, 3 stars, "Good Match"
// - 20-39: Orange, 2 stars, "Fair Match"
```

#### `MatchDetailView`
```typescript
interface MatchDetailViewProps {
  match: MatchDetail;
  onInvite: () => void;
}

// Sections:
// - User profile card
// - Compatibility score breakdown (pie chart or bars)
// - Trip overlap calendar
// - Grade range comparison
// - Shared experience tags
```

---

### 5.3 State Management

```typescript
// lib/matching.ts

interface Match {
  user: User;
  trip: Trip;
  match_score: number;
  reasons: string[];
  overlap_dates: {
    start: string;
    end: string;
    days: number;
  };
}

export const useMatchStore = create<MatchState>((set) => ({
  matches: [],
  currentMatch: null,
  isLoading: false,
  currentTrip: null,

  fetchMatches: async (tripId?: string) => { ... },
  fetchMatchDetail: async (userId: string, tripId: string) => { ... },
}));
```

---

## 6. Implementation Checklist

### Backend
- [ ] **Serializers** (matching/serializers.py)
  - [ ] MatchTripSerializer
  - [ ] MatchUserSerializer
  - [ ] OverlapDatesSerializer
  - [ ] MatchSerializer
  - [ ] MatchListSerializer
  - [ ] AvailabilityOverlapSerializer
  - [ ] GradeCompatibilitySerializer
  - [ ] MatchDetailSerializer

- [ ] **Matching Service** (matching/services.py)
  - [ ] MatchingService class
  - [ ] _get_candidates (with queryset optimization)
  - [ ] _get_candidate_trip (with select_related/prefetch_related)
  - [ ] _calculate_match_score
  - [ ] _score_location (30 points)
  - [ ] _score_date_overlap (20 points)
  - [ ] _score_discipline (20 points)
  - [ ] _score_grade_compatibility (15 points)
  - [ ] _score_risk_tolerance (-10 to 10 points)
  - [ ] _score_availability (5 points)

- [ ] **ViewSet** (matching/views.py)
  - [ ] MatchViewSet with rate limiting (30/min)
  - [ ] list action (GET /api/matches/)
  - [ ] detail action (GET /api/matches/:user_id/detail/)

- [ ] **URL Configuration** (matching/urls.py)
  - [ ] Register MatchViewSet with router
  - [ ] Include in config/urls.py

- [ ] **Validation & Security**
  - [ ] Rate limiting (30 requests per minute)
  - [ ] User ownership validation (only match own trips)
  - [ ] Email verification check
  - [ ] Profile visibility check
  - [ ] Queryset optimization (select_related, prefetch_related)

- [ ] **Tests** (matching/tests.py)
  - [ ] Test scoring functions individually
  - [ ] Test matching algorithm with various user/trip combinations
  - [ ] Test edge cases (no overlap, perfect match, no trips)
  - [ ] Test filtering (profile_visible, email_verified)
  - [ ] Test rate limiting
  - [ ] Test match detail endpoint

### Frontend
- [ ] **State Management** (lib/matching.ts)
  - [ ] Create match store with Zustand
  - [ ] Implement fetchMatches
  - [ ] Implement fetchMatchDetail

- [ ] **Pages**
  - [ ] Build match feed page (`/matches`)
  - [ ] Build match detail page (`/matches/:user_id`)

- [ ] **Components**
  - [ ] MatchCard component
  - [ ] MatchScoreIndicator component
  - [ ] MatchDetailView component
  - [ ] Add filter UI (discipline, grade, risk - optional for MVP)

- [ ] **Integration**
  - [ ] Add "Send Invite" action (links to Phase 5)
  - [ ] Add loading states
  - [ ] Add error handling
  - [ ] Test on mobile

### Testing
- [ ] **Backend Tests**
  - [ ] Test all scoring functions return correct values
  - [ ] Test matching with 2 overlapping users (should match)
  - [ ] Test matching with no overlapping users (empty results)
  - [ ] Test filtering excludes invisible profiles
  - [ ] Test filtering excludes unverified emails
  - [ ] Test rate limiting triggers correctly

- [ ] **Frontend E2E Tests**
  - [ ] Test match feed loads correctly
  - [ ] Test match detail view shows full info
  - [ ] Test empty state (no matches)

---

## 7. Performance Optimization (Phase 2)

- Cache match results for 15 minutes (Redis)
- Precompute matches for all active trips (background job)
- Add database indexes on trip dates, destination
- Pagination for large result sets

---

## 8. Estimated Timeline

### Backend (10-12 hours)
- Serializers (8 serializers with validation): 2 hours
- MatchingService class (all scoring functions): 4 hours
- ViewSet with rate limiting: 1.5 hours
- URL configuration and integration: 0.5 hours
- Tests (comprehensive backend tests): 3 hours

### Frontend (8-10 hours)
- Match state management (Zustand store): 1.5 hours
- Match feed page and components: 4 hours
- Match detail view: 2 hours
- UI polish and error handling: 1.5 hours
- Frontend tests: 1 hour

**Total (MVP): ~18-22 hours**

**Note:** Caching and performance optimization (Redis, precomputation) deferred to future enhancement.

---

## Next Phase
**Phase 5: Sessions & Messaging**
