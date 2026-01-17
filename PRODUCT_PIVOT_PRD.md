# Send Buddy: Social Utility Pivot - Product Requirements Document

**Document Version:** 1.0
**Date:** January 16, 2026
**Status:** Draft - Pending Approval

---

## Executive Summary

### Strategic Pivot
Send Buddy is evolving from a transactional matchmaking app (Tinder for climbers) to a **social utility and network** (Strava meets shared calendar). The goal is to shift from low-frequency, desperate-need usage to daily/weekly retention by enabling users to stay connected with their climbing network, plan trips, and discover where friends are climbing.

### Core Shift
- **Old Model:** User searches filters → finds stranger → one-time connection
- **New Model:** User posts climbing schedule → stays connected with network → discovers organic overlap opportunities

### Success Metrics
- **Retention:** Increase DAU/MAU ratio from ~10% to 40%+
- **Engagement:** Users check app 3-5x/week (vs. current 1x/month)
- **Network Effect:** Average user has 8+ connections within 3 months
- **Conversion:** 60% of trips result in either friend overlap or successful partner match

---

## 1. New Data Entities

### 1.1 Trip Entity (Enhanced)

**Current State:**
- Trip already exists with: destination, dates, disciplines, grade preferences
- Linked to User (owner)
- Used for matching algorithm

**New Fields Required:**

```python
class Trip(models.Model):
    # Existing fields...
    user = models.ForeignKey(User)
    destination = models.ForeignKey(Destination)
    start_date = models.DateField()
    end_date = models.DateField()
    preferred_disciplines = ArrayField()

    # NEW FIELDS
    visibility_status = models.CharField(
        max_length=20,
        choices=[
            ('looking_for_partners', 'Looking for Partners'),  # Public matchmaking
            ('open_to_friends', 'Open to Friends'),           # Network-only visibility
            ('full_private', 'Full/Private')                   # Hidden from everyone
        ],
        default='open_to_friends'
    )

    is_group_trip = models.BooleanField(default=False)
    organizer = models.ForeignKey(User, null=True, blank=True, related_name='organized_trips')
    invited_users = models.ManyToManyField(User, blank=True, related_name='invited_trips')

    # Trip completion tracking
    trip_status = models.CharField(
        max_length=20,
        choices=[
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='planned'
    )

    # Social features
    notes_public = models.TextField(blank=True)  # Visible to network
    notes_private = models.TextField(blank=True)  # Personal only

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Business Rules:**
- `visibility_status = 'looking_for_partners'` → Trip appears in public Partner Finder
- `visibility_status = 'open_to_friends'` → Trip visible only to user's network
- `visibility_status = 'full_private'` → Trip visible only to trip creator and invited users
- Group trips (`is_group_trip=True`) require an organizer
- Invited users see trip regardless of visibility status
- Past trips (`end_date < today`) automatically marked as historical but remain visible on profile

---

### 1.2 Friendship/Network Entity (NEW)

**Purpose:** Enable social graph for "friend/follow" functionality

```python
class Friendship(models.Model):
    """
    Represents a connection between two users.
    Can be one-directional (Follow) or bi-directional (Friends).
    """

    requester = models.ForeignKey(User, related_name='friendship_requests_sent')
    addressee = models.ForeignKey(User, related_name='friendship_requests_received')

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),      # Request sent, not accepted
            ('accepted', 'Accepted'),    # Mutual friends
            ('following', 'Following')   # One-way follow (if we allow this)
        ],
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    connection_source = models.CharField(
        max_length=50,
        choices=[
            ('matched_trip', 'Met via Trip Match'),
            ('completed_session', 'Climbed Together'),
            ('manual_add', 'Manual Add'),
            ('imported', 'Imported from Contact')
        ],
        null=True, blank=True
    )

    class Meta:
        unique_together = ('requester', 'addressee')
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['addressee', 'status']),
        ]

    def __str__(self):
        return f"{self.requester} → {self.addressee} ({self.status})"
```

**Helper Methods:**
```python
# Get all accepted friends for a user
def get_friends(user):
    return User.objects.filter(
        Q(friendship_requests_received__requester=user, friendship_requests_received__status='accepted') |
        Q(friendship_requests_sent__addressee=user, friendship_requests_sent__status='accepted')
    ).distinct()

# Check if two users are friends
def are_friends(user1, user2):
    return Friendship.objects.filter(
        Q(requester=user1, addressee=user2, status='accepted') |
        Q(requester=user2, addressee=user1, status='accepted')
    ).exists()
```

---

### 1.3 TripOverlap Entity (NEW)

**Purpose:** Cache and track detected overlaps between users' trips for the "Overlap Engine"

```python
class TripOverlap(models.Model):
    """
    Represents a detected overlap between two users' trips.
    Auto-generated by the Overlap Engine.
    """

    user1 = models.ForeignKey(User, related_name='overlaps_as_user1')
    user2 = models.ForeignKey(User, related_name='overlaps_as_user2')

    trip1 = models.ForeignKey(Trip, related_name='overlaps_as_trip1')
    trip2 = models.ForeignKey(Trip, related_name='overlaps_as_trip2')

    # Overlap details
    overlap_destination = models.ForeignKey(Destination)
    overlap_start_date = models.DateField()
    overlap_end_date = models.DateField()
    overlap_days = models.IntegerField()  # Number of overlapping days

    # Overlap score (0-100) based on:
    # - Number of overlapping days
    # - Discipline compatibility
    # - Friendship status
    # - Distance from user's home crag
    overlap_score = models.IntegerField()

    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    # User actions
    user1_dismissed = models.BooleanField(default=False)
    user2_dismissed = models.BooleanField(default=False)
    connection_created = models.BooleanField(default=False)  # Did they connect?

    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip1', 'trip2')
        indexes = [
            models.Index(fields=['overlap_start_date', 'notification_sent']),
            models.Index(fields=['user1', 'notification_sent']),
            models.Index(fields=['user2', 'notification_sent']),
        ]
```

---

### 1.4 Group (Climbing Crew) Entity (NEW)

**Purpose:** Allow experienced climbers to create recurring crews

```python
class ClimbingGroup(models.Model):
    """
    Represents a climbing crew/group.
    Groups can plan trips together.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    creator = models.ForeignKey(User, related_name='created_groups')
    members = models.ManyToManyField(User, through='GroupMembership', related_name='climbing_groups')

    # Settings
    is_private = models.BooleanField(default=False)  # Invite-only vs. discoverable
    auto_accept_members = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

class GroupMembership(models.Model):
    """
    Through model for Group membership with roles.
    """

    group = models.ForeignKey(ClimbingGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Admin'),
            ('member', 'Member'),
            ('pending', 'Pending Invitation')
        ],
        default='member'
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
```

---

### 1.5 Notification Entity (Updated)

**Current State:** Notifications already exist for matches and session requests

**New Notification Types:**

```python
# Add to existing NotificationType choices:
NOTIFICATION_TYPES = [
    # Existing
    ('new_match', 'New Match'),
    ('connection_request', 'Connection Request'),
    ('connection_accepted', 'Connection Accepted'),

    # NEW - Social Network
    ('friend_request', 'Friend Request'),
    ('friend_accepted', 'Friend Request Accepted'),
    ('friend_trip_posted', 'Friend Posted a Trip'),

    # NEW - Overlap Engine
    ('trip_overlap_detected', 'Trip Overlap Detected'),
    ('friend_in_home_crag', 'Friend Coming to Your Home Crag'),

    # NEW - Group Features
    ('group_invite', 'Group Invitation'),
    ('group_trip_posted', 'Group Trip Posted'),
    ('group_trip_updated', 'Group Trip Updated'),
]
```

---

## 2. Key User Flows

### 2.1 Flow: Posting a Trip

**Actors:** User (any climber planning a trip)

**Preconditions:** User is logged in

**Steps:**

1. User navigates to "Plan a Trip" (primary CTA on dashboard)
2. User enters trip details:
   - Destination (autocomplete search)
   - Dates (start/end with date picker)
   - Disciplines (multi-select: sport, trad, bouldering, etc.)
   - Optional: Specific crags, grade preferences, notes
3. User selects **Visibility Status**:
   - 🔍 "Looking for Partners" → Public matchmaking enabled
   - 👥 "Open to Friends" → Visible to network only (default)
   - 🔒 "Full/Private" → Hidden from everyone
4. Optional: User marks as "Group Trip" and invites friends/group members
5. User clicks "Post Trip"

**Outcomes:**
- Trip saved to database with selected visibility
- Trip appears on user's profile (upcoming trips section)
- If visibility = "open_to_friends" → Friends see in their feed: "Sarah just planned a trip to Red River Gorge (Oct 12-14)"
- If visibility = "looking_for_partners" → Trip enters public Partner Finder pool
- **Overlap Engine triggered** → System checks for date/location overlaps with friends' trips

**UI Requirements:**
- Trip creation form (modal or full page)
- Visual calendar picker with range selection
- Destination autocomplete with location preview
- Clear visibility status selector with icons and descriptions
- "Invite Friends" flow for group trips

---

### 2.2 Flow: Adding a Friend

**Actors:** User A (requester), User B (addressee)

**Trigger:** User A wants to connect with User B

**Steps:**

**Path 1: Manual Friend Request**
1. User A discovers User B via:
   - Profile view (from match, session, or search)
   - "People You May Know" recommendations
2. User A clicks "Add Friend" button on User B's profile
3. Friend request created with `status='pending'`
4. User B receives notification: "User A sent you a friend request"
5. User B views request and clicks "Accept" or "Decline"
6. If accepted:
   - Friendship status → 'accepted'
   - Both users notified: "You are now friends with [Name]"
   - Both users can now see each other's "Open to Friends" trips

**Path 2: Auto-Friend After Session**
1. User A and User B complete a climbing session together
2. System prompts: "Want to add [User B] to your climbing network?"
3. If both users accept → Auto-friend (skip pending state)

**Business Rules:**
- Users cannot send duplicate friend requests
- Blocked users cannot send friend requests
- Friend requests expire after 90 days if not accepted
- Users can have max 500 friends (prevent spam/abuse)

**UI Requirements:**
- "Add Friend" button on profiles (state: Not Friends / Request Sent / Friends)
- Friend request notification popup
- "People You May Know" section on dashboard
- Post-session friend suggestion prompt

---

### 2.3 Flow: Discovering a Trip Overlap

**Actors:** User A, User B (friends)

**Trigger:** Overlap Engine detects overlap (runs as background job)

**Background Process:**

```python
# Pseudo-code for Overlap Engine
def detect_overlaps():
    """
    Runs daily to detect new trip overlaps.
    """
    for user in active_users:
        friends = get_friends(user)
        user_trips = user.trips.filter(end_date__gte=today(), visibility_status__in=['looking_for_partners', 'open_to_friends'])

        for trip in user_trips:
            for friend in friends:
                friend_trips = friend.trips.filter(
                    destination=trip.destination,
                    start_date__lte=trip.end_date,
                    end_date__gte=trip.start_date,
                    visibility_status__in=['looking_for_partners', 'open_to_friends']
                )

                for friend_trip in friend_trips:
                    # Calculate overlap
                    overlap_start = max(trip.start_date, friend_trip.start_date)
                    overlap_end = min(trip.end_date, friend_trip.end_date)
                    overlap_days = (overlap_end - overlap_start).days + 1

                    # Create or update TripOverlap
                    TripOverlap.objects.get_or_create(
                        trip1=trip,
                        trip2=friend_trip,
                        defaults={
                            'user1': user,
                            'user2': friend,
                            'overlap_destination': trip.destination,
                            'overlap_start_date': overlap_start,
                            'overlap_end_date': overlap_end,
                            'overlap_days': overlap_days,
                            'overlap_score': calculate_overlap_score(trip, friend_trip)
                        }
                    )
```

**User Flow:**

1. **Overlap Detected:**
   - System creates TripOverlap record
   - Overlap score calculated (based on days, disciplines, proximity)

2. **Notification Sent:**
   - Both User A and User B receive notification:
     - **Critical priority** (shows popup)
     - Title: "Trip Overlap with [Friend Name]"
     - Message: "You and Sarah will both be in Red River Gorge from Oct 12-14 (3 days overlap)"
     - Action: "View Details" → Opens overlap detail view

3. **User Views Overlap:**
   - Detail card shows:
     - Friend's name and avatar
     - Shared destination
     - Overlap dates highlighted on mini calendar
     - Common disciplines
     - CTA: "Send Connection Request" or "Start Planning"

4. **User Takes Action:**
   - Send session/connection request
   - Dismiss overlap (marks `user1_dismissed=True`)
   - Message friend directly (future: in-app messaging)

**Special Case: Cross-Path Detection**
- If User A hasn't planned a trip but Friend B is coming to User A's home crag:
  - Notification: "Sarah is coming to [Your Home Crag] Oct 12-14. Want to meet up?"
  - This uses `user.home_location` to detect proximity

**UI Requirements:**
- Overlap notification popup (critical priority)
- Overlap detail card/modal
- "Overlaps" tab on dashboard showing all upcoming overlaps
- Visual calendar view with overlap highlighting

---

### 2.4 Flow: Viewing the Social Feed

**Actor:** User

**Preconditions:** User has friends/network

**Steps:**

1. User opens Send Buddy app
2. Dashboard shows **"Your Network"** feed (primary view)
3. Feed displays recent activities from friends:
   - "Sarah posted a trip to Red River Gorge (Oct 12-14)"
   - "Mike just got back from Joshua Tree" (trip completed)
   - "Alex is looking for a belay partner in Thailand next month"
   - "3 of your friends are going to Las Vegas this spring"

4. Feed items are clickable:
   - Click on friend's trip → View trip details
   - Click on friend's name → View friend's profile
   - Click "React" → Send encouragement (future: likes/comments)

5. User can filter feed:
   - "Looking for Partners" (only public trips)
   - "All Friends" (all network activity)
   - "This Month" / "Next 3 Months" (time filter)

**Feed Algorithm:**
- Prioritize trips with overlaps
- Show trips to destinations user has been to
- Show trips with compatible disciplines
- Decay older posts (trips >6 months in past get lower priority)

**UI Requirements:**
- Card-based feed with infinite scroll
- Activity cards showing:
  - Friend avatar + name
  - Trip destination, dates, disciplines
  - Visibility status indicator
  - Quick actions: "View Trip", "Send Request", "Dismiss"
- Time-based grouping: "This Week", "Next Month", "Upcoming", "Past Trips"

---

### 2.5 Flow: Viewing the Crag Calendar

**Actor:** User

**Preconditions:** User has trips and/or friends with trips

**Steps:**

1. User clicks "Calendar" tab on dashboard
2. Calendar view loads showing:
   - **My Trips** (color-coded by visibility: green = open to friends, blue = looking for partners, gray = private)
   - **Friends' Trips** (overlaid in different color, e.g., orange)
   - **Overlaps** (highlighted with special indicator)

3. Calendar interactions:
   - Click on trip → View trip details popup
   - Click on overlap → View overlap detail
   - Hover on trip → Quick preview tooltip
   - Switch view: Month / 3-Month / 6-Month

4. Optional filters:
   - Toggle "My Trips" on/off
   - Toggle "Friends' Trips" on/off
   - Filter by destination
   - Filter by friend

**Visual Design:**
- Multi-trip days show stacked bars or count indicator
- Overlaps have distinct visual treatment (e.g., diagonal stripes)
- Today indicator clearly marked
- Legend explaining color codes

**UI Requirements:**
- Interactive calendar component (use library: react-big-calendar or similar)
- Trip detail popover on click
- Color-coded legend
- Mobile-responsive (month view for mobile, 3-month for desktop)

---

### 2.6 Flow: Solo Traveler Posts Public Trip

**Actor:** Solo Traveler (planning trip without existing network)

**Trigger:** User is traveling alone to Thailand and needs a belay partner

**Steps:**

1. User creates trip (as in Flow 2.1)
2. User selects visibility: **"Looking for Partners"**
3. Trip posted with `visibility_status='looking_for_partners'`

4. **Dual Visibility:**
   - Trip appears in user's profile (visible to friends if they have any)
   - **Trip enters Public Partner Finder** (matchmaking pool)

5. **Matchmaking Activated:**
   - System runs matching algorithm (existing functionality)
   - Potential matches discovered based on:
     - Same destination + overlapping dates
     - Compatible disciplines
     - Skill level compatibility
     - No blocking relationship

6. **Matched Users Notified:**
   - Other solo travelers going to Thailand get match notifications
   - "New Match: [User Name] is also going to Thailand (Oct 12-14)"

7. **User Can Switch Visibility:**
   - If user finds a partner → Change visibility to "Full/Private" or "Open to Friends"
   - Trip no longer appears in public Partner Finder

**Business Rules:**
- Only trips with `visibility_status='looking_for_partners'` enter matchmaking
- Matchmaking runs on trip creation and daily for active trips
- Users matched to max 10 people per trip (prevent spam)
- If trip is in past → Automatically hidden from Partner Finder

**UI Requirements:**
- Clear explanation of "Looking for Partners" visibility
- Toggle to switch visibility after posting
- "Partner Finder" tab showing public trips (searchable/filterable)
- Match notification popup (same as existing)

---

## 3. Updated UI Requirements

### 3.1 Dashboard / Home Screen (Complete Redesign)

**Current State:** Dashboard likely shows matches or generic content

**New Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  SEND BUDDY                     🔔 Notifications  👤 Profile │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [+] Plan a Trip     [📅] Calendar     [🔍] Find Partners   │
│                                                               │
├───────────────────────┬─────────────────────────────────────┤
│                       │                                       │
│   YOUR NETWORK FEED   │   UPCOMING TRIPS & OVERLAPS          │
│                       │                                       │
│ 📍 Sarah posted a     │   ┌─────────────────────────────┐   │
│    trip to Red River  │   │ Your Next Trip              │   │
│    Gorge (Oct 12-14)  │   │ Joshua Tree                 │   │
│    [View Trip]        │   │ Mar 15-20, 2026             │   │
│                       │   │ Looking for Partners 🔍     │   │
│ 🎯 OVERLAP!           │   │ [View Details]              │   │
│    You and Mike will  │   └─────────────────────────────┘   │
│    both be in Vegas   │                                       │
│    (Feb 10-12)        │   ┌─────────────────────────────┐   │
│    [Connect]          │   │ Detected Overlaps (2)       │   │
│                       │   │                               │   │
│ 👥 3 friends are      │   │ • Mike - Las Vegas          │   │
│    going to Joshua    │   │   Feb 10-12 (3 days)        │   │
│    Tree this spring   │   │   [View]                    │   │
│    [See Who]          │   │                               │   │
│                       │   │ • Alex - Red River Gorge    │   │
│ 📅 Alex completed     │   │   Oct 13-14 (2 days)        │   │
│    trip to Thailand   │   │   [View]                    │   │
│    [See Photos]       │   └─────────────────────────────┘   │
│                       │                                       │
│ [Load More...]        │   [View All Trips]                   │
│                       │                                       │
└───────────────────────┴─────────────────────────────────────┘
```

**Components:**
- **Top Navigation:** Primary actions (Plan Trip, Calendar, Find Partners)
- **Left Column (60%):** Social feed with friend activities
- **Right Column (40%):** User's upcoming trips + overlaps sidebar
- **Mobile:** Stack vertically, feed first

---

### 3.2 Profile Page Updates

**New Sections to Add:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Avatar]  Sarah Johnson                                     │
│            📍 Boulder, CO                                    │
│            👥 142 Friends  |  🧗 23 Trips Completed          │
│                                                               │
│  [Add Friend] [Message] [...]                                │
├─────────────────────────────────────────────────────────────┤
│  About  |  UPCOMING TRIPS  |  Past Trips  |  Disciplines    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📍 UPCOMING TRIPS (3)                                        │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Red River Gorge                                     │     │
│  │ Oct 12-14, 2026  •  Sport, Trad                    │     │
│  │ 👥 Open to Friends                                  │     │
│  │ [View Details]                                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Joshua Tree                                         │     │
│  │ Mar 15-20, 2026  •  Bouldering                     │     │
│  │ 🔍 Looking for Partners                             │     │
│  │ [Send Request]                                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Thailand (Group Trip)                               │     │
│  │ Dec 1-15, 2026  •  Sport, Multi-pitch              │     │
│  │ 🔒 Private (Invite Only)                            │     │
│  │ 6 climbers going                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  [Show All Trips]                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Visibility Rules:**
- Public trips: Visible to everyone
- "Open to Friends" trips: Visible to friends only
- "Full/Private" trips: Visible to trip creator and invited users only
- Past trips: Always visible (privacy toggle in settings)

---

### 3.3 Trip Detail Page (New)

**Purpose:** Full detail view for a single trip

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Profile                                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📍 RED RIVER GORGE                                          │
│  October 12-14, 2026  (3 days)                               │
│                                                               │
│  Organized by: Sarah Johnson  [View Profile]                 │
│  Visibility: 👥 Open to Friends                              │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  TRIP DETAILS                                                │
│                                                               │
│  Disciplines: Sport, Trad                                    │
│  Grade Range: 5.10a - 5.12b                                  │
│  Crags: Muir Valley, PMRP                                    │
│                                                               │
│  Notes:                                                       │
│  "Looking to climb multi-pitch routes and work on           │
│   projecting some harder sport climbs. Open to meeting      │
│   up with friends for a day or grabbing dinner!"            │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  CLIMBERS GOING (4)                                          │
│                                                               │
│  [Avatar] Sarah Johnson (Organizer)                          │
│  [Avatar] Mike Chen                                          │
│  [Avatar] Alex Rivera                                        │
│  [Avatar] + You! [Join Trip]                                 │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  OVERLAPPING FRIENDS (2)                                     │
│                                                               │
│  [Avatar] Emma Wu - Oct 13-15 (2 days overlap)              │
│           [Send Request]                                     │
│                                                               │
│  [Avatar] James Park - Oct 10-14 (3 days overlap)           │
│           [Send Request]                                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.4 Calendar View

**Component:** Full-page calendar showing user's trips + friends' trips

**Features:**
- Month view with color-coded trip bars
- Overlap highlighting
- Click to view trip details
- Filter by destination, friend, visibility
- Export to Google Calendar (future)

**Visual Treatment:**
```
       MARCH 2026                                [Filter ▾]
┌───┬───┬───┬───┬───┬───┬───┐
│ S │ M │ T │ W │ T │ F │ S │
├───┼───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │ 1 │
├───┼───┼───┼───┼───┼───┼───┤
│ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │
├───┼───┼───┼───┼───┼───┼───┤
│ 9 │10 │11 │12 │13 │14 │15 │
│   │   │   │ ▇▇▇▇▇▇▇▇▇▇▇▇▇ │  ← Joshua Tree (You)
│   │   │   │ ▓▓▓▓▓▓▓       │  ← Vegas (Mike) *OVERLAP*
├───┼───┼───┼───┼───┼───┼───┤
│16 │17 │18 │19 │20 │21 │22 │
│▇▇▇│   │   │   │   │   │   │
├───┼───┼───┼───┼───┼───┼───┤
│23 │24 │25 │26 │27 │28 │29 │
├───┼───┼───┼───┼───┼───┼───┤
│30 │31 │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┴───┘

Legend:
▇▇▇ Your Trips (Green)
▓▓▓ Friends' Trips (Orange)
▒▒▒ Overlaps (Highlighted)
```

---

### 3.5 Partner Finder (Public Matchmaking)

**Purpose:** Searchable directory of trips marked "Looking for Partners"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  FIND CLIMBING PARTNERS                                      │
│                                                               │
│  [Search destination...] [Date Range] [Disciplines ▾]        │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  TRIPS LOOKING FOR PARTNERS (24)                             │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ [Avatar] Mike Chen                                  │     │
│  │ 📍 Joshua Tree  •  Mar 10-15  •  Bouldering        │     │
│  │ 85% Match  •  V4-V7  •  "Looking for pad share"   │     │
│  │ [View Profile] [Send Request]                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ [Avatar] Emma Wu                                    │     │
│  │ 📍 Red River Gorge  •  Oct 12-14  •  Sport, Trad  │     │
│  │ 72% Match  •  5.10a-5.11c  •  "Can lead & belay"  │     │
│  │ [View Profile] [Send Request]                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  [Load More...]                                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Matching Algorithm (Existing + Enhanced):**
- Same destination + overlapping dates (required)
- Discipline compatibility (weight: 30%)
- Skill level match (weight: 25%)
- Friend-of-friend bonus (weight: 15%)
- Profile completeness (weight: 10%)
- Safety score (weight: 20%)

---

### 3.6 Notifications Center Updates

**New Notification Types UI:**

```
┌─────────────────────────────────────────────────────────────┐
│  NOTIFICATIONS                               [Mark All Read] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🎯 TRIP OVERLAP DETECTED                             2h ago │
│     You and Mike Chen will both be in Las Vegas              │
│     Feb 10-12 (3 days overlap)                               │
│     [View Details] [Dismiss]                                 │
│                                                               │
│  👥 FRIEND REQUEST                                    1d ago │
│     Sarah Johnson sent you a friend request                  │
│     [Accept] [Decline]                                       │
│                                                               │
│  📍 FRIEND POSTED TRIP                                3d ago │
│     Alex Rivera is going to Red River Gorge (Oct 12-14)      │
│     [View Trip]                                              │
│                                                               │
│  🏠 FRIEND COMING TO YOUR CRAG                        5d ago │
│     Emma Wu is coming to Boulder (your home crag)            │
│     Mar 5-8, 2026                                            │
│     [Send Message] [Dismiss]                                 │
│                                                               │
│  🔍 NEW MATCH                                        1w ago  │
│     You've been matched with James Park (85% match)          │
│     Both going to Thailand in December                       │
│     [View Match]                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Technical Implementation Plan

### 4.1 Database Migrations

**Migration Strategy:**

1. **Phase 1: Add New Models (Non-Breaking)**
   - Add `Friendship` model
   - Add `TripOverlap` model
   - Add `ClimbingGroup` and `GroupMembership` models
   - Add new notification types

2. **Phase 2: Extend Trip Model**
   - Add new fields to Trip: `visibility_status`, `is_group_trip`, `organizer`, `trip_status`, `notes_public`, `notes_private`
   - Set default `visibility_status='open_to_friends'` for existing trips
   - Backfill `trip_status` based on dates (past trips → 'completed')

3. **Phase 3: Data Cleanup**
   - Existing sessions can optionally create friendships
   - Run script: "Convert completed sessions to friendships"

**Migration Checklist:**
```bash
# Create new models
python manage.py makemigrations friendships
python manage.py makemigrations overlaps
python manage.py makemigrations groups

# Extend existing models
python manage.py makemigrations trips
python manage.py makemigrations notifications

# Run migrations
python manage.py migrate

# Backfill data
python manage.py backfill_trip_visibility
python manage.py convert_sessions_to_friendships --dry-run
python manage.py convert_sessions_to_friendships  # After review
```

---

### 4.2 New API Endpoints

**Friendships:**
```
POST   /api/friendships/                    # Send friend request
GET    /api/friendships/                    # List user's friends
GET    /api/friendships/pending/            # List pending requests
PATCH  /api/friendships/{id}/accept/        # Accept request
PATCH  /api/friendships/{id}/decline/       # Decline request
DELETE /api/friendships/{id}/               # Remove friend
GET    /api/friendships/suggestions/        # Friend suggestions
```

**Trips (Enhanced):**
```
POST   /api/trips/                          # Create trip (with new fields)
GET    /api/trips/                          # List trips (filtered by visibility)
GET    /api/trips/{id}/                     # Trip detail
PATCH  /api/trips/{id}/                     # Update trip
DELETE /api/trips/{id}/                     # Delete trip
GET    /api/trips/upcoming/                 # User's upcoming trips
GET    /api/trips/past/                     # User's past trips
GET    /api/trips/public/                   # Public trips (looking for partners)
POST   /api/trips/{id}/invite-users/        # Invite users to group trip
```

**Overlaps:**
```
GET    /api/overlaps/                       # List user's overlaps
GET    /api/overlaps/{id}/                  # Overlap detail
PATCH  /api/overlaps/{id}/dismiss/          # Dismiss overlap
POST   /api/overlaps/detect/                # Manually trigger overlap detection (admin)
```

**Groups:**
```
POST   /api/groups/                         # Create group
GET    /api/groups/                         # List user's groups
GET    /api/groups/{id}/                    # Group detail
PATCH  /api/groups/{id}/                    # Update group
DELETE /api/groups/{id}/                    # Delete group
POST   /api/groups/{id}/invite/             # Invite user to group
POST   /api/groups/{id}/join/               # Join group (if public)
DELETE /api/groups/{id}/members/{user_id}/  # Remove member
```

**Social Feed:**
```
GET    /api/feed/                           # Social feed (friend activities)
GET    /api/feed/network-trips/             # Friends' trips only
GET    /api/feed/overlaps/                  # Overlaps only
```

---

### 4.3 Background Jobs (Celery Tasks)

**New Scheduled Tasks:**

```python
# tasks.py

@shared_task
def detect_trip_overlaps():
    """
    Runs daily at 6:00 AM to detect new trip overlaps.
    Creates TripOverlap records and sends notifications.
    """
    # See pseudo-code in Section 2.3
    pass

@shared_task
def send_overlap_notifications():
    """
    Sends notifications for newly detected overlaps that haven't been notified.
    """
    overlaps = TripOverlap.objects.filter(
        notification_sent=False,
        overlap_start_date__gte=timezone.now().date()
    )

    for overlap in overlaps:
        # Send notification to both users
        NotificationService.create_overlap_notification(overlap)
        overlap.notification_sent = True
        overlap.notification_sent_at = timezone.now()
        overlap.save()

@shared_task
def update_trip_statuses():
    """
    Runs daily to mark trips as 'in_progress' or 'completed' based on dates.
    """
    today = timezone.now().date()

    # Mark trips as in_progress
    Trip.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        trip_status='planned'
    ).update(trip_status='in_progress')

    # Mark trips as completed
    Trip.objects.filter(
        end_date__lt=today,
        trip_status__in=['planned', 'in_progress']
    ).update(trip_status='completed')

@shared_task
def send_friend_trip_notifications():
    """
    Sends notifications when friends post new trips.
    Runs every 6 hours.
    """
    # Get trips created in last 6 hours with visibility='open_to_friends' or 'looking_for_partners'
    recent_trips = Trip.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=6),
        visibility_status__in=['open_to_friends', 'looking_for_partners']
    )

    for trip in recent_trips:
        friends = get_friends(trip.user)

        for friend in friends:
            NotificationService.create_friend_trip_notification(
                recipient=friend,
                trip=trip
            )
```

**Celery Beat Schedule:**
```python
# settings.py

CELERY_BEAT_SCHEDULE = {
    'detect-overlaps-daily': {
        'task': 'trips.tasks.detect_trip_overlaps',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    'send-overlap-notifications': {
        'task': 'trips.tasks.send_overlap_notifications',
        'schedule': crontab(hour='*/2'),  # Every 2 hours
    },
    'update-trip-statuses': {
        'task': 'trips.tasks.update_trip_statuses',
        'schedule': crontab(hour=0, minute=30),  # Daily at 12:30 AM
    },
    'send-friend-trip-notifications': {
        'task': 'trips.tasks.send_friend_trip_notifications',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}
```

---

### 4.4 Frontend Components (React/Next.js)

**New Pages:**
```
/dashboard              # Social feed + upcoming trips (default home)
/calendar               # Calendar view
/trips/new              # Create trip form
/trips/{id}             # Trip detail
/partners               # Public partner finder
/friends                # Friends list + requests
/groups                 # Groups list
/groups/{id}            # Group detail
/overlaps               # All overlaps list
```

**New Components:**
```typescript
// components/feed/FeedCard.tsx
// Displays a single feed item (friend's trip)

// components/trips/TripCard.tsx
// Compact trip display for lists

// components/trips/TripDetailCard.tsx
// Full trip detail view

// components/calendar/CalendarView.tsx
// Interactive calendar with trips

// components/overlaps/OverlapCard.tsx
// Overlap notification/detail

// components/friends/FriendCard.tsx
// Friend list item

// components/friends/FriendRequestCard.tsx
// Pending friend request

// components/groups/GroupCard.tsx
// Group list item

// components/trips/TripVisibilitySelector.tsx
// Radio group for selecting visibility status
```

---

### 4.5 Services & Business Logic

**New Service Classes:**

```python
# friendships/services.py

class FriendshipService:
    @staticmethod
    def send_friend_request(requester, addressee):
        """Create friend request and send notification."""
        pass

    @staticmethod
    def accept_friend_request(friendship_id):
        """Accept request and notify both users."""
        pass

    @staticmethod
    def get_friends(user):
        """Get all accepted friends for user."""
        pass

    @staticmethod
    def get_mutual_friends(user1, user2):
        """Get mutual friends between two users."""
        pass

    @staticmethod
    def suggest_friends(user, limit=10):
        """Suggest friends based on completed sessions, mutual friends."""
        pass
```

```python
# trips/services/overlap_engine.py

class OverlapEngine:
    @staticmethod
    def detect_overlaps_for_user(user):
        """Detect all overlaps for a specific user's trips."""
        pass

    @staticmethod
    def detect_overlaps_for_trip(trip):
        """Detect overlaps for a specific trip."""
        pass

    @staticmethod
    def calculate_overlap_score(trip1, trip2):
        """
        Calculate overlap score (0-100) based on:
        - Number of overlapping days (0-30 points)
        - Discipline compatibility (0-25 points)
        - Skill level match (0-20 points)
        - Friendship status (0-15 points)
        - Proximity to home crag (0-10 points)
        """
        pass

    @staticmethod
    def detect_cross_path(user, trip):
        """
        Detect if a friend's trip overlaps with user's home crag.
        """
        pass
```

```python
# feed/services.py

class FeedService:
    @staticmethod
    def get_feed(user, limit=50):
        """
        Generate social feed for user showing:
        - Friends' new trips
        - Friends' completed trips
        - Overlaps
        - Group activities
        """
        pass

    @staticmethod
    def get_feed_item_for_trip(trip):
        """Generate feed item data for a trip."""
        pass
```

---

## 5. Migration & Rollout Strategy

### 5.1 Phased Rollout

**Phase 1: Foundation (Week 1-2)**
- Backend: Add new models (Friendship, TripOverlap, Group)
- Backend: Add new fields to Trip model
- Backend: Create API endpoints for friendships
- Database: Run migrations on staging
- Testing: Unit tests for new models and services

**Phase 2: Friend System (Week 3-4)**
- Frontend: Add "Add Friend" button to profiles
- Frontend: Friend requests notification flow
- Frontend: Friends list page
- Backend: Friend suggestion algorithm
- Testing: Integration tests for friendship workflows

**Phase 3: Enhanced Trips (Week 5-6)**
- Frontend: Update trip creation form with visibility selector
- Frontend: Trip detail page
- Backend: Update trip serializers with new fields
- Backend: Implement visibility filtering in trip API
- Testing: Test all visibility states

**Phase 4: Social Feed (Week 7-8)**
- Frontend: Build feed component
- Backend: Implement FeedService
- Backend: Friend trip notifications
- Frontend: Dashboard redesign with feed
- Testing: Feed algorithm accuracy

**Phase 5: Overlap Engine (Week 9-10)**
- Backend: Implement OverlapEngine service
- Backend: Create Celery tasks for overlap detection
- Backend: Overlap notifications
- Frontend: Overlap cards and detail views
- Frontend: Overlaps tab on dashboard
- Testing: Overlap detection accuracy

**Phase 6: Calendar View (Week 11-12)**
- Frontend: Build calendar component
- Frontend: Integrate trips and overlaps
- Frontend: Calendar filtering
- Testing: Calendar performance with many trips

**Phase 7: Groups & Polish (Week 13-14)**
- Backend: Groups API
- Frontend: Groups pages
- Frontend: Group trip creation
- Polish: UI refinements, bug fixes
- Testing: End-to-end testing

**Phase 8: Soft Launch (Week 15)**
- Deploy to production with feature flag
- Enable for 10% of users (beta testers)
- Monitor metrics: DAU, retention, friend connections
- Gather feedback

**Phase 9: Full Launch (Week 16+)**
- Enable for all users
- Marketing push: "New Send Buddy - Stay Connected with Your Crew"
- Monitor and iterate

---

### 5.2 Success Metrics

**North Star Metric:** Weekly Active Users (WAU)

**Key Metrics:**

| Metric | Current Baseline | 3-Month Target | 6-Month Target |
|--------|------------------|----------------|----------------|
| DAU/MAU Ratio | ~10% | 25% | 40% |
| Avg. Friends per User | 0 | 5 | 12 |
| Avg. Trips Posted per User | 0.5 | 2 | 4 |
| Overlap Detection Rate | N/A | 30% of trips have overlap | 50% |
| Friend-to-Friend Connections | 0% | 40% | 60% |
| Session Frequency | 1x/month | 1x/week | 3x/week |

**Engagement Metrics:**
- Feed views per session
- Calendar views per week
- Friend requests sent per user
- Overlap notifications clicked (CTR)

**Conversion Metrics:**
- % of trips with visibility = "looking_for_partners"
- % of overlaps that result in connection request
- % of friend requests that result in accepted friendship

---

### 5.3 Risk Mitigation

**Risk 1: Low Friend Adoption**
- Mitigation: Auto-suggest friends from completed sessions
- Mitigation: Incentivize friending (unlock features)
- Mitigation: Import contacts (email, phone)

**Risk 2: Overlap Engine Accuracy**
- Mitigation: Allow users to manually dismiss bad overlaps
- Mitigation: Improve scoring algorithm based on user feedback
- Mitigation: Test with synthetic data before launch

**Risk 3: Feed Spam (Too Many Notifications)**
- Mitigation: Implement notification frequency limits
- Mitigation: Allow users to mute specific friends or groups
- Mitigation: Smart batching (daily digest option)

**Risk 4: Privacy Concerns**
- Mitigation: Clear visibility controls and explanations
- Mitigation: Opt-out of all social features (settings)
- Mitigation: Private mode for sensitive trips

**Risk 5: Performance (Calendar & Feed)**
- Mitigation: Pagination and lazy loading
- Mitigation: Cache feed and calendar data
- Mitigation: Database indexing on date range queries

---

## 6. Open Questions & Future Considerations

### 6.1 Open Questions for Product Team

1. **Friendship Model:**
   - Should friendships be bi-directional (mutual) or allow one-way follows?
   - Current assumption: Bi-directional (like Facebook, not Twitter)

2. **Overlap Notifications:**
   - How many overlap notifications per week is too many?
   - Should we batch overlaps into a daily digest?

3. **Trip Visibility:**
   - Can users change visibility after posting? (Current assumption: Yes)
   - Should completed trips always be public or have privacy settings?

4. **Groups:**
   - Max group size? (Current assumption: 50 members)
   - Can groups have private trip pools?

5. **Feed Algorithm:**
   - Should we use ML to personalize feed ranking?
   - How far back should we show trips? (Current assumption: 6 months)

### 6.2 Future Features (Post-MVP)

**Phase 10+:**
- **In-App Messaging:** Real-time chat beyond session messages
- **Trip Photos & Logs:** Users can upload trip reports and photos
- **Social Reactions:** Like, comment on friends' trips
- **Trip Recommendations:** "Based on your trips, try Red Rocks"
- **Climb Logging:** Log individual routes climbed during trips
- **Leaderboards:** Most trips, most friends, most crags visited
- **Trip Sharing:** Share trip links to non-users (growth)
- **Calendar Export:** Sync with Google Calendar, Apple Calendar
- **Weather Integration:** Show weather for upcoming trips
- **Gear Sharing:** Coordinate gear needs for group trips
- **Transportation Coordination:** Carpool matching for trips

---

## 7. Conclusion

This pivot transforms Send Buddy from a low-frequency matchmaking tool into a daily-use social utility. By making trips the central object and layering social connections + overlap detection on top, we create a sticky, network-effect-driven product.

**Key Success Factors:**
1. **Seamless Trip Posting:** Must be dead simple (< 30 seconds)
2. **Accurate Overlaps:** Overlap engine must surface real, valuable opportunities
3. **Friend Growth:** Need viral loops to grow friend networks quickly
4. **FOMO Feed:** Feed must drive engagement through social proof

**Next Steps:**
1. Review and approve this PRD
2. Create detailed technical specifications for each phase
3. Design high-fidelity mockups for new UI components
4. Begin Phase 1 implementation (Foundation)
5. Set up analytics tracking for new metrics

---

**Document Status:** Ready for Review
**Prepared By:** Claude (AI Product Assistant)
**Review Requested From:** Product Team, Engineering Lead, Design Lead
