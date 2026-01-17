# Climber Profile Page Upgrade Specification

## Overview

Transform the user profile page from a simple form-based display into an immersive "Magazine Cover" experience that showcases a climber's identity, skills, network, and climbing history.

**Design Tone:** Young, Fun, & Safe - matching Send Buddy's "Immersive Electric Nature" design system.

---

## Current State Analysis

### Existing Pages
- `/app/profile/page.tsx` - Edit profile (own profile, form-based)
- `/app/users/[id]/page.tsx` - Public profile view (viewing others)

### Current User Model Fields (backend/users/models.py)
| Field | Type | Purpose |
|-------|------|---------|
| display_name | CharField | User's name |
| avatar | ImageField | Profile photo |
| bio | TextField | Short bio (500 chars) |
| home_location | CharField | "City, Country" |
| home_lat/lng | DecimalField | Coordinates |
| risk_tolerance | Choice | conservative/balanced/aggressive |
| preferred_grade_system | Choice | yds/french/v_scale |
| gender | Choice | For partner matching |
| weight_kg | Integer | For belay safety |
| profile_visible | Boolean | Privacy toggle |
| created_at | DateTime | Account creation |

### Related Models
- **DisciplineProfile** - Grade ranges, skills (can_lead, can_belay, can_build_anchors)
- **ExperienceTag** - Skills, equipment, logistics, preferences
- **Friendship** - Connections with status (pending/accepted/following)
- **Session** - Climbing invites with status
- **Feedback** - Post-session ratings (safety, communication, overall)

### Current Public Profile UI (`/app/users/[id]/page.tsx`)
- Basic avatar with initial fallback
- Name + location
- Bio
- Climbing preferences (risk tolerance, grade system)
- Experience tags by category
- Discipline profiles with grade ranges
- Connect button

---

## Target Design: Magazine Cover Profile

### Section 1: Hero Section
**Magazine-cover style full-width header**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Full-width background: climbing action photo or gradient]          │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Semi-transparent scrim (hero-scrim gradient)                    │ │
│ │                                                                 │ │
│ │   ┌──────┐                                                     │ │
│ │   │Avatar│  BOULDER BOY                      [Edit Profile]    │ │
│ │   │ 🟢   │  📍 Denver, Colorado                                │ │
│ │   └──────┘                                                     │ │
│ │   Badge: "Experienced Trad Leader"                             │ │
│ │                                                                 │ │
│ │   ┌──────────┐ ┌──────────┐ ┌──────────┐                      │ │
│ │   │ 23       │ │ 2021     │ │ "The     │                      │ │
│ │   │ Sessions │ │ Since    │ │ Diamond" │                      │ │
│ │   └──────────┘ └──────────┘ └──────────┘                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- `avatar` - Existing (with new background photo field)
- `display_name` - Existing
- `home_location` - Existing
- `skill_badge` - NEW: Computed from disciplines/experience
- `sessions_count` - Query: completed sessions
- `member_since` - Existing: created_at.year
- `first_send` - NEW: Optional notable climb field

**New Backend Fields:**
```python
# User model additions
profile_background = models.ImageField(upload_to='profile_backgrounds/', null=True, blank=True)
first_notable_send = models.CharField(max_length=200, blank=True, help_text="Notable first send")
first_send_year = models.IntegerField(null=True, blank=True)
```

---

### Section 2: Climber Attributes
**Two-column card with radar chart and grade stats**

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLIMBER ATTRIBUTES                                                  │
├─────────────────────────────────┬───────────────────────────────────┤
│                                 │                                   │
│      [Radar Chart]              │   SPORT      5.11c - 5.12b       │
│                                 │   TRAD       5.10a - 5.11a       │
│     Endurance ─●                │   BOULDER    V5 - V7             │
│              /   \              │   MULTIPITCH 5.10d max           │
│    Power ───●     ●─── Tech    │                                   │
│              \   /              │   Risk: Balanced                 │
│     Mental ───●                 │   System: YDS                    │
│                                 │                                   │
└─────────────────────────────────┴───────────────────────────────────┘
```

**Data Requirements:**
- Radar chart dimensions - NEW: User self-assessment
- Grade stats - Existing: DisciplineProfile
- Risk tolerance - Existing
- Grade system - Existing

**New Backend Fields:**
```python
# User model additions for radar chart (1-10 scale)
attr_endurance = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
attr_power = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
attr_technique = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
attr_mental = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
attr_flexibility = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
```

**Frontend Component:**
- Use `recharts` or `chart.js` for radar chart
- Component: `<ClimberRadarChart attributes={user.attributes} />`

---

### Section 3: Upcoming Trips
**Horizontal scrollable trip cards**

```
┌─────────────────────────────────────────────────────────────────────┐
│ UPCOMING TRIPS                                        [View All →]  │
├─────────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │
│ │ Tonsai Beach  │ │ Red River    │ │ Rifle        │              │
│ │ Thailand      │ │ Gorge, KY    │ │ Colorado     │              │
│ │               │ │              │ │              │              │
│ │ Mar 15-25     │ │ Apr 5-12     │ │ May 1-7      │              │
│ │ 🟢 Looking    │ │ 🔵 Open to   │ │ 🟡 Private   │              │
│ │    for        │ │    Friends   │ │              │              │
│ │    Partners   │ │              │ │              │              │
│ └───────────────┘ └───────────────┘ └───────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- User's active/upcoming trips - Existing: Trip model
- Visibility status - Existing: `visibility_status` field

**API Endpoint:**
- Existing: `GET /api/trips/?is_active=true`
- May need: `GET /api/users/{id}/trips/` for public profile

---

### Section 4: Belay Network
**Friends/connections display with face pile**

```
┌─────────────────────────────────────────────────────────────────────┐
│ BELAY NETWORK                                         [View All →]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   [😀][😎][🧗][🏔️][⛰️][+12 more]     47 Connections              │
│                                                                     │
│   12 Mutual Friends with you                                       │
│                                                                     │
│   Recent: Sarah M., Alex T., Chris K.                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- Friends list - Existing: Friendship model
- Mutual friends count - Existing: Can be computed
- Connection count - Existing: Query count

**API Endpoint:**
- `GET /api/friendships/` - Existing
- May need: `GET /api/users/{id}/connections/` (public subset)

**Frontend Component:**
- `<FacePile users={friends} maxVisible={6} />`

---

### Section 5: Recent Beta (Media Gallery)
**Photo/video uploads - NEW FEATURE**

```
┌─────────────────────────────────────────────────────────────────────┐
│ RECENT BETA                                           [Add Media]   │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│ │             │ │             │ │             │ │             │   │
│ │  [Photo 1]  │ │  [Photo 2]  │ │  [Video 1]  │ │  [Photo 3]  │   │
│ │             │ │             │ │   ▶️         │ │             │   │
│ │             │ │             │ │             │ │             │   │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
│   "Sending      "Approach to     "Beta spray     "Summit selfie"  │
│    the crux"     Indian Creek"    on project"                     │
└─────────────────────────────────────────────────────────────────────┘
```

**New Backend Model:**
```python
# New: users/models.py or media/models.py

class UserMedia(models.Model):
    """User-uploaded climbing photos/videos"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media')

    MEDIA_TYPES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
    ]
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)

    # Storage
    file = models.FileField(upload_to='user_media/%Y/%m/')
    thumbnail = models.ImageField(upload_to='user_media/thumbs/', null=True, blank=True)

    # Metadata
    caption = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    climb_name = models.CharField(max_length=200, blank=True)

    # Privacy
    is_public = models.BooleanField(default=True)

    # Ordering
    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_media'
        ordering = ['-created_at']
```

**New API Endpoints:**
```
GET    /api/users/{id}/media/     - List user's public media
POST   /api/users/me/media/       - Upload new media
DELETE /api/users/me/media/{id}/  - Delete own media
PATCH  /api/users/me/media/{id}/  - Update caption/order
```

**Frontend Components:**
- `<MediaGallery userId={user.id} editable={isOwnProfile} />`
- `<MediaUploader onUpload={handleUpload} />`
- `<MediaLightbox media={selectedMedia} />`

---

### Section 6: Recommendations (Testimonials)
**Partner testimonials - NEW FEATURE**

```
┌─────────────────────────────────────────────────────────────────────┐
│ PARTNER RECOMMENDATIONS                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   "Alex is the most reliable belay partner I've ever had.          │
│    Always attentive and great at reading the route."               │
│                                                     — Sarah M.      │
│                                                       Climbed 5x    │
│                                                                     │
│   "Super patient teacher, helped me finally send my project!"      │
│                                                     — Chris K.      │
│                                                       Climbed 3x    │
│                                                                     │
│                                              [Request Recommendation]│
└─────────────────────────────────────────────────────────────────────┘
```

**New Backend Model:**
```python
# New: users/models.py

class Recommendation(models.Model):
    """Public testimonial from climbing partner"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who wrote it for whom
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations_given')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations_received')

    # Content
    body = models.TextField(max_length=500)

    # Verification
    sessions_together = models.IntegerField(default=0)  # Auto-computed
    is_verified = models.BooleanField(default=False)    # Confirmed climbed together

    # Approval workflow
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Display
    is_featured = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'recommendations'
        unique_together = ['author', 'recipient']  # One rec per pair
        ordering = ['-is_featured', '-created_at']
```

**New API Endpoints:**
```
GET    /api/users/{id}/recommendations/          - List approved recommendations
POST   /api/users/{id}/recommendations/          - Write recommendation for user
POST   /api/recommendations/{id}/approve/        - Approve (recipient only)
POST   /api/recommendations/{id}/reject/         - Reject (recipient only)
DELETE /api/recommendations/{id}/                - Delete (author only)
```

**Frontend Components:**
- `<RecommendationCard recommendation={rec} />`
- `<WriteRecommendationModal recipientId={userId} />`
- `<RecommendationApprovalList />` (in settings/notifications)

---

## Component Hierarchy

```
ProfilePage (or UserProfilePage for /users/[id])
├── ProfileHero
│   ├── ProfileBackground
│   ├── Avatar (with skill badge)
│   ├── ProfileInfo (name, location, bio)
│   ├── QuickStats (sessions, since, first send)
│   └── ProfileActions (Edit/Connect button)
│
├── ClimberAttributesCard
│   ├── ClimberRadarChart
│   └── GradeStatsPanel
│       └── DisciplineGradeRow (per discipline)
│
├── UpcomingTripsCard
│   └── TripCard (horizontal scroll)
│
├── BelayNetworkCard
│   ├── FacePile
│   ├── ConnectionStats
│   └── MutualFriendsInfo
│
├── RecentBetaCard
│   ├── MediaGrid
│   │   └── MediaThumbnail
│   ├── MediaUploader (if own profile)
│   └── MediaLightbox
│
└── RecommendationsCard
    ├── RecommendationQuote
    └── WriteRecommendationButton
```

---

## Implementation Phases

### Phase 1: Backend Models & Migrations
1. Add new User fields (profile_background, first_send, attributes)
2. Create UserMedia model
3. Create Recommendation model
4. Write migrations
5. Create serializers
6. Create ViewSets with proper permissions

### Phase 2: API Endpoints
1. `GET /api/users/{id}/profile-stats/` - Aggregated stats
2. Media CRUD endpoints
3. Recommendation CRUD endpoints
4. Update UserSerializer with new fields

### Phase 3: Hero Section Component
1. ProfileHero component with background
2. Avatar with skill badge logic
3. QuickStats component
4. Responsive layout (mobile: stacked, desktop: side-by-side)

### Phase 4: Attributes & Trips
1. Radar chart component (install recharts)
2. Grade stats panel
3. Trip cards with visibility badges
4. Horizontal scroll container

### Phase 5: Network & Media
1. FacePile component
2. MediaGallery with upload
3. Lightbox viewer
4. File upload handling (consider S3/Cloudinary)

### Phase 6: Recommendations
1. Recommendation display components
2. Write recommendation modal
3. Approval workflow in notifications
4. "Climbed X times" verification

---

## Technical Considerations

### File Storage
- Current: Local Django media storage
- Recommended: AWS S3 or Cloudinary for production
- Thumbnail generation for videos

### Performance
- Lazy load media gallery
- Paginate recommendations
- Cache friend counts
- Use `select_related`/`prefetch_related` in queries

### Privacy
- Respect `profile_visible` flag
- Media `is_public` per-item control
- Recommendations require recipient approval
- Block enforcement on all queries

### Accessibility
- Alt text for all images
- Keyboard navigation in gallery
- Screen reader support for radar chart
- Color contrast compliance

---

## API Response Shape

### Profile Stats Endpoint
```json
GET /api/users/{id}/profile-stats/

{
  "completed_sessions_count": 23,
  "member_since_year": 2021,
  "connections_count": 47,
  "mutual_friends_count": 12,
  "recommendations_count": 5,
  "media_count": 8
}
```

### Extended User Serializer
```json
{
  "id": "uuid",
  "display_name": "Boulder Boy",
  "avatar": "/media/avatars/...",
  "profile_background": "/media/backgrounds/...",
  "home_location": "Denver, Colorado",
  "bio": "...",

  // New fields
  "first_notable_send": "The Diamond",
  "first_send_year": 2019,
  "attributes": {
    "endurance": 7,
    "power": 6,
    "technique": 8,
    "mental": 7,
    "flexibility": 5
  },

  // Existing
  "risk_tolerance": "balanced",
  "preferred_grade_system": "yds",
  "disciplines": [...],
  "experience_tags": [...]
}
```

---

## Files to Create/Modify

### Backend
| File | Action | Purpose |
|------|--------|---------|
| `users/models.py` | Modify | Add new User fields, UserMedia, Recommendation |
| `users/serializers.py` | Modify | Add new serializers |
| `users/views.py` | Modify | Add new endpoints |
| `users/urls.py` | Modify | Register new routes |
| `config/settings.py` | Modify | File upload settings |

### Frontend
| File | Action | Purpose |
|------|--------|---------|
| `components/profile/ProfileHero.tsx` | Create | Hero section |
| `components/profile/ClimberRadarChart.tsx` | Create | Radar visualization |
| `components/profile/GradeStatsPanel.tsx` | Create | Grade display |
| `components/profile/FacePile.tsx` | Create | Friend avatars |
| `components/profile/MediaGallery.tsx` | Create | Photo grid |
| `components/profile/RecommendationCard.tsx` | Create | Testimonial |
| `app/users/[id]/page.tsx` | Modify | Assemble new layout |
| `lib/types.ts` | Modify | Add new types |
| `lib/api.ts` | Modify | Add new API methods |

---

## Success Criteria

1. **Visual Impact**: Profile immediately conveys climber identity
2. **Social Proof**: Recommendations and network visible
3. **Discoverability**: Upcoming trips attract potential partners
4. **Media Rich**: Photos make profile engaging
5. **Mobile First**: Works beautifully on phone
6. **Performance**: Page loads under 2 seconds
7. **Accessibility**: WCAG 2.1 AA compliant
