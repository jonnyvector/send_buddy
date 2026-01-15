# Phase 1: Data Models & Grade System

## Overview
Implement the complete database schema and climbing grade conversion system. This is the foundation for all other features.

## Priority: CRITICAL
Everything else depends on these models being correct.

---

## 1. Database Models

### 1.1 User (extends Django's AbstractUser)
```python
# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
import uuid

class UserQuerySet(models.QuerySet):
    """Custom queryset with block enforcement"""

    def visible_to(self, viewer):
        """
        Filter users visible to viewer (enforces blocks + privacy).

        Excludes:
        - Users blocked by viewer
        - Users who blocked viewer
        - Users with profile_visible=False
        """
        if not viewer or not viewer.is_authenticated:
            return self.filter(profile_visible=True)

        return self.exclude(
            Q(blocks_received__blocker=viewer) |  # Users blocked by viewer
            Q(blocks_given__blocked=viewer)        # Users who blocked viewer
        ).filter(profile_visible=True)


class UserManager(models.Manager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def visible_to(self, viewer):
        return self.get_queryset().visible_to(viewer)


class RiskTolerance(models.TextChoices):
    CONSERVATIVE = 'conservative', 'Conservative'
    BALANCED = 'balanced', 'Balanced'
    AGGRESSIVE = 'aggressive', 'Aggressive'


class GradeSystem(models.TextChoices):
    YDS = 'yds', 'YDS'
    FRENCH = 'french', 'French'
    V_SCALE = 'v_scale', 'V-Scale'


class User(AbstractUser):
    """Extended user model with climbing-specific fields"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Profile basics
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    # Location
    home_location = models.CharField(max_length=200, help_text="City, Country")
    home_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    home_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Preferences
    risk_tolerance = models.CharField(
        max_length=20,
        choices=RiskTolerance.choices,
        default=RiskTolerance.BALANCED
    )

    preferred_grade_system = models.CharField(
        max_length=10,
        choices=GradeSystem.choices,
        default=GradeSystem.YDS
    )

    # Profile visibility
    profile_visible = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Email verification
    email_verified = models.BooleanField(default=False)

    # Use email for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']  # Required for createsuperuser (email is already required)

    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.display_name} ({self.email})"
```

**Required fields for registration:**
- email (unique, used for login)
- password
- display_name
- home_location

**Settings to configure:**
```python
# config/settings.py
AUTH_USER_MODEL = 'users.User'
```

**Key Features:**
- ✅ **Email authentication** - Uses email instead of username for login
- ✅ **Block enforcement** - `User.objects.visible_to(viewer)` automatically excludes blocked users
- ✅ **TextChoices** - Type-safe enums for choices
- ✅ **Custom queryset** - Centralized privacy logic

---

### 1.2 DisciplineProfile

```python
# users/models.py

from django.core.exceptions import ValidationError

class Discipline(models.TextChoices):
    SPORT = 'sport', 'Sport Climbing'
    TRAD = 'trad', 'Trad Climbing'
    BOULDERING = 'bouldering', 'Bouldering'
    MULTIPITCH = 'multipitch', 'Multipitch'
    GYM = 'gym', 'Gym Climbing'


class DisciplineProfile(models.Model):
    """Climbing discipline-specific profile for a user"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disciplines')
    discipline = models.CharField(max_length=20, choices=Discipline.choices)

    # Grading
    grade_system = models.CharField(max_length=10, choices=GradeSystem.choices)
    comfortable_grade_min_display = models.CharField(max_length=10, help_text="User-entered grade (e.g., '5.10a')")
    comfortable_grade_max_display = models.CharField(max_length=10, help_text="User-entered grade (e.g., '5.11c')")
    projecting_grade_display = models.CharField(max_length=10, blank=True, help_text="Optional projecting grade")

    # Internal normalized scores (0-100 scale for matching)
    comfortable_grade_min_score = models.IntegerField()
    comfortable_grade_max_score = models.IntegerField()
    projecting_grade_score = models.IntegerField(null=True, blank=True)

    # Experience
    years_experience = models.IntegerField(null=True, blank=True)
    can_lead = models.BooleanField(default=False)
    can_belay = models.BooleanField(default=True)
    can_build_anchors = models.BooleanField(default=False, help_text="For trad/multipitch")

    notes = models.TextField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discipline_profiles'
        unique_together = ['user', 'discipline']

    def __str__(self):
        return f"{self.user.display_name} - {self.get_discipline_display()}"

    def clean(self):
        """Validate grade system matches discipline"""
        super().clean()

        # Bouldering must use V-Scale
        if self.discipline == Discipline.BOULDERING and self.grade_system != GradeSystem.V_SCALE:
            raise ValidationError({
                'grade_system': f'Bouldering must use V-Scale, not {self.get_grade_system_display()}'
            })

        # Sport/trad/multipitch/gym should use YDS or French
        if self.discipline in [Discipline.SPORT, Discipline.TRAD, Discipline.MULTIPITCH, Discipline.GYM]:
            if self.grade_system == GradeSystem.V_SCALE:
                raise ValidationError({
                    'grade_system': f'{self.get_discipline_display()} cannot use V-Scale'
                })

        # Ensure min <= max
        if self.comfortable_grade_min_score > self.comfortable_grade_max_score:
            raise ValidationError({
                'comfortable_grade_max_display': 'Maximum grade must be >= minimum grade'
            })
```

**Business Logic:**
- User can have 1 profile per discipline
- Grade scores are computed on save using conversion table
- Display grades are stored as-entered for UX
- ✅ **Grade system validation** - Bouldering must use V-Scale; sport/trad cannot use V-Scale
- ✅ **Min/Max validation** - Ensures grade ranges are logical

---

### 1.3 ExperienceTag

```python
# users/models.py

class ExperienceTag(models.Model):
    """Predefined experience/equipment tags"""

    CATEGORY_CHOICES = [
        ('skill', 'Skill'),
        ('equipment', 'Equipment'),
        ('logistics', 'Logistics'),
        ('preference', 'Preference'),
    ]

    slug = models.SlugField(unique=True, primary_key=True)
    display_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'experience_tags'

class UserExperienceTag(models.Model):
    """Many-to-many through table for user tags"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experience_tags')
    tag = models.ForeignKey(ExperienceTag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_experience_tags'
        unique_together = ['user', 'tag']
```

**Seed tags (examples):**
```python
SEED_TAGS = [
    # Skills
    ('lead_belay_certified', 'Lead Belay Certified', 'skill'),
    ('multipitch_experience', 'Multipitch Experience', 'skill'),
    ('trad_anchor_building', 'Can Build Trad Anchors', 'skill'),
    ('outdoor_beginner_friendly', 'Beginner Friendly', 'skill'),

    # Equipment
    ('has_rope', 'Has Rope', 'equipment'),
    ('has_quickdraws', 'Has Quickdraws', 'equipment'),
    ('has_trad_rack', 'Has Trad Rack', 'equipment'),
    ('has_crash_pad', 'Has Crash Pad', 'equipment'),

    # Logistics
    ('has_car', 'Has Car', 'logistics'),
    ('has_scooter', 'Has Scooter/Bike', 'logistics'),

    # Preferences
    ('early_morning', 'Early Morning Person', 'preference'),
    ('social_climber', 'Social Climber', 'preference'),
    ('project_focused', 'Project Focused', 'preference'),
]
```

---

### 1.4 Destination (Climbing Location)

```python
# trips/models.py

class Destination(models.Model):
    """Top-level climbing destination/region"""

    slug = models.SlugField(unique=True, primary_key=True, max_length=100)
    name = models.CharField(max_length=200)  # "Red River Gorge, KY"
    country = models.CharField(max_length=100)

    # Coordinates
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)

    # Metadata
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)

    # Climbing info
    primary_disciplines = models.JSONField(default=list, help_text="['sport', 'trad']")
    season = models.CharField(max_length=100, blank=True, help_text="Best season (e.g., 'Oct-May')")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'destinations'
        ordering = ['name']

    def __str__(self):
        return self.name
```

**Examples:**
- `red-river-gorge` → "Red River Gorge, KY"
- `railay` → "Railay, Krabi"
- `kalymnos` → "Kalymnos, Greece"

---

### 1.5 Crag (Specific Climbing Area)

```python
# trips/models.py

class Crag(models.Model):
    """Specific climbing area within a destination"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='crags')

    name = models.CharField(max_length=200)  # "Muir Valley"
    slug = models.SlugField(max_length=100)

    # Coordinates (optional - not all crags have precise coords)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    description = models.TextField(blank=True)
    disciplines = models.JSONField(default=list, help_text="['sport']")

    # Useful metadata
    approach_time = models.IntegerField(null=True, blank=True, help_text="Minutes from parking")
    route_count = models.IntegerField(null=True, blank=True, help_text="Approximate route count")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crags'
        unique_together = ['destination', 'slug']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.destination.name})"
```

**Examples (Red River Gorge):**
- Muir Valley
- Miguel's Pizza
- PMRP (Pendergrass-Murray Recreational Preserve)
- The Motherlode
- Left Flank

**Examples (Railay):**
- Thaiwand Wall
- Fire Wall
- Diamond Cave
- Ao Nang Tower

---

### 1.6 Trip

```python
# trips/models.py

from django.utils import timezone
from django.core.exceptions import ValidationError

class Trip(models.Model):
    """A climbing trip (date range + location)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')

    # Location (structured)
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, related_name='trips')
    preferred_crags = models.ManyToManyField(Crag, blank=True, related_name='trips')

    # Fallback for unlisted crags
    custom_crag_notes = models.CharField(max_length=300, blank=True, help_text="If specific crag not in database")

    # Dates
    start_date = models.DateField()
    end_date = models.DateField()

    # Preferences for this trip
    preferred_disciplines = models.JSONField(default=list, help_text="['sport', 'bouldering']")
    notes = models.TextField(max_length=500, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trips'
        ordering = ['start_date']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')),
                name='trip_end_after_start'
            ),
        ]

    def __str__(self):
        return f"{self.user.display_name} - {self.destination.name} ({self.start_date})"

    def clean(self):
        """Validate trip dates and crags"""
        super().clean()

        # Ensure end_date >= start_date
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date must be on or after start date'
            })

        # For new trips, ensure start_date >= today
        if not self.pk and self.start_date:
            today = timezone.now().date()
            if self.start_date < today:
                raise ValidationError({
                    'start_date': 'Cannot create trips in the past'
                })

    def validate_crags_belong_to_destination(self):
        """
        Call this after save (when M2M is available).
        Ensures all preferred_crags belong to the trip's destination.
        """
        invalid_crags = self.preferred_crags.exclude(destination=self.destination)
        if invalid_crags.exists():
            crag_names = ', '.join(invalid_crags.values_list('name', flat=True))
            raise ValidationError(
                f'The following crags do not belong to {self.destination.name}: {crag_names}'
            )
```

**Changes from original:**
- ✅ `destination` is now a ForeignKey to Destination (not free text)
- ✅ `preferred_crags` is a many-to-many to Crag
- ✅ `custom_crag_notes` for unlisted crags (fallback)

**Validation:**
- ✅ **DB constraint** - `end_date >= start_date` enforced at database level
- ✅ **clean() method** - Validates dates and prevents past trips
- ✅ **Crag validation** - `validate_crags_belong_to_destination()` ensures crag/destination consistency

---

### 1.7 AvailabilityBlock

```python
# trips/models.py

class TimeBlock(models.TextChoices):
    MORNING = 'morning', 'Morning'
    AFTERNOON = 'afternoon', 'Afternoon'
    FULL_DAY = 'full_day', 'Full Day'
    REST = 'rest', 'Rest Day'


class AvailabilityBlock(models.Model):
    """Specific availability within a trip"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='availability')

    date = models.DateField()
    time_block = models.CharField(max_length=20, choices=TimeBlock.choices)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'availability_blocks'
        unique_together = ['trip', 'date', 'time_block']
        ordering = ['date', 'time_block']

    def __str__(self):
        return f"{self.trip.user.display_name} - {self.date} ({self.get_time_block_display()})"

    def clean(self):
        """Validate date is within trip's date range"""
        super().clean()

        if self.trip and self.date:
            if self.date < self.trip.start_date:
                raise ValidationError({
                    'date': f'Date must be on or after trip start date ({self.trip.start_date})'
                })

            if self.date > self.trip.end_date:
                raise ValidationError({
                    'date': f'Date must be on or before trip end date ({self.trip.end_date})'
                })
```

**Business Logic:**
- ✅ **Date validation** - Date must be within trip's date range (enforced in `clean()`)
- ✅ **Unique constraint** - Cannot have duplicate time blocks for same trip/date
- Users can mark entire days as "rest"

---

### 1.8 Session (Climbing Session / Invitation)

```python
# climbing_sessions/models.py

class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class Session(models.Model):
    """An invitation to climb together"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Participants
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_sent')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_received')

    # Trip context (IMPORTANT: This is the inviter's trip)
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='sessions',
                             help_text="The inviter's trip that this session is part of")

    # Proposed details
    proposed_date = models.DateField()
    time_block = models.CharField(max_length=20, choices=TimeBlock.choices)
    crag = models.CharField(max_length=200, blank=True)
    goal = models.TextField(max_length=300, blank=True, help_text="What to climb/work on")

    # Status
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sessions'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=~models.Q(inviter=models.F('invitee')),
                name='session_no_self_invite'
            ),
        ]

    def __str__(self):
        return f"{self.inviter.display_name} → {self.invitee.display_name} ({self.proposed_date})"

    def clean(self):
        """Validate session details"""
        super().clean()

        # Prevent self-invites
        if self.inviter_id and self.invitee_id and self.inviter_id == self.invitee_id:
            raise ValidationError('Cannot invite yourself')

        # Ensure trip belongs to inviter
        if self.trip and self.inviter and self.trip.user_id != self.inviter_id:
            raise ValidationError({
                'trip': 'Session trip must belong to the inviter'
            })

        # Ensure proposed_date is within trip dates
        if self.trip and self.proposed_date:
            if self.proposed_date < self.trip.start_date or self.proposed_date > self.trip.end_date:
                raise ValidationError({
                    'proposed_date': f'Date must be within trip dates ({self.trip.start_date} - {self.trip.end_date})'
                })
```

**Key Clarifications:**
- ✅ **Trip ownership** - `trip` field ALWAYS refers to the **inviter's trip**
- ✅ **Self-invite prevention** - DB constraint + clean() validation
- ✅ **Date validation** - Proposed date must be within inviter's trip dates
- ✅ **Trip ownership validation** - Trip must belong to inviter

---

### 1.9 Message

```python
# climbing_sessions/models.py

class Message(models.Model):
    """Chat message within a session"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)

    body = models.TextField(max_length=2000)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
```

**Business Logic:**
- Update `session.last_message_at` on create
- Only inviter/invitee can send messages

---

### 1.10 Feedback

```python
# climbing_sessions/models.py

class Feedback(models.Model):
    """Post-session feedback (private)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='feedback')

    # Who rated whom
    rater = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_given')
    ratee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_received')

    # Ratings (1-5 scale)
    safety_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    overall_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Private notes (not shown to ratee in MVP)
    notes = models.TextField(max_length=1000, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback'
        unique_together = ['session', 'rater', 'ratee']
```

**Business Logic:**
- Only created after session status = 'completed'
- Both participants should rate each other (2 feedback per session)
- In Phase 2: compute aggregate reputation score

---

### 1.11 Block

```python
# users/models.py

class Block(models.Model):
    """User blocking another user"""

    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_given')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_received')

    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blocks'
        unique_together = ['blocker', 'blocked']
        constraints = [
            models.CheckConstraint(
                check=~models.Q(blocker=models.F('blocked')),
                name='block_no_self_block'
            ),
        ]

    def __str__(self):
        return f"{self.blocker.display_name} blocked {self.blocked.display_name}"
```

**Critical:** Block relationships must be enforced in **all queries**:
- ✅ **Centralized enforcement** - Use `User.objects.visible_to(viewer)` everywhere
- ✅ **Self-block prevention** - DB constraint prevents blocker == blocked
- Blocked users never appear in matches
- Cannot send session invites
- Cannot see each other's profiles

---

### 1.12 Report

```python
# users/models.py

class Report(models.Model):
    """User reporting another user"""

    REASON_CHOICES = [
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Behavior'),
        ('spam', 'Spam'),
        ('safety', 'Safety Concern'),
        ('fake', 'Fake Profile'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')

    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(max_length=2000)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_notes = models.TextField(max_length=2000, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
```

---

## 2. Grade Conversion System

### 2.1 GradeConversion Model

```python
# users/models.py

class GradeConversion(models.Model):
    """Master grade conversion table"""

    # Discipline
    discipline = models.CharField(max_length=20, choices=Discipline.choices)

    # Normalized score (0-100)
    score = models.IntegerField()

    # Display grades
    yds_grade = models.CharField(max_length=10, blank=True, help_text="e.g., '5.10a'")
    french_grade = models.CharField(max_length=10, blank=True, help_text="e.g., '6a'")
    v_scale_grade = models.CharField(max_length=10, blank=True, help_text="e.g., 'V3'")

    class Meta:
        db_table = 'grade_conversions'
        ordering = ['discipline', 'score']
        constraints = [
            models.UniqueConstraint(
                fields=['discipline', 'score'],
                name='unique_grade_per_discipline'
            ),
        ]
        indexes = [
            models.Index(fields=['discipline', 'yds_grade']),
            models.Index(fields=['discipline', 'french_grade']),
            models.Index(fields=['discipline', 'v_scale_grade']),
        ]

    def __str__(self):
        if self.discipline == Discipline.BOULDERING:
            return f"{self.v_scale_grade} (score: {self.score})"
        else:
            return f"{self.yds_grade} / {self.french_grade} (score: {self.score})"
```

**Key Changes:**
- ✅ **Per-discipline uniqueness** - `(discipline, score)` unique constraint (fixes overlapping scores)
- ✅ **Indexes for lookups** - Fast grade→score queries
- ✅ **Removed global unique** - Allows sport V40=40 and boulder V3=40 to coexist

### 2.2 Seed Data (Sport/Trad)

```python
# users/management/commands/seed_grades.py

SPORT_TRAD_GRADES = [
    # score, yds, french
    (0, '5.5', '4a'),
    (5, '5.6', '4b'),
    (10, '5.7', '4c'),
    (15, '5.8', '5a'),
    (20, '5.9', '5b'),
    (25, '5.10a', '5c'),
    (27, '5.10b', '6a'),
    (30, '5.10c', '6a+'),
    (32, '5.10d', '6b'),
    (35, '5.11a', '6b+'),
    (37, '5.11b', '6c'),
    (40, '5.11c', '6c+'),
    (42, '5.11d', '7a'),
    (45, '5.12a', '7a+'),
    (47, '5.12b', '7b'),
    (50, '5.12c', '7b+'),
    (52, '5.12d', '7c'),
    (55, '5.13a', '7c+'),
    (57, '5.13b', '8a'),
    (60, '5.13c', '8a+'),
    (62, '5.13d', '8b'),
    (65, '5.14a', '8b+'),
    (67, '5.14b', '8c'),
    (70, '5.14c', '8c+'),
    (72, '5.14d', '9a'),
    (75, '5.15a', '9a+'),
    (77, '5.15b', '9b'),
    (80, '5.15c', '9b+'),
]

BOULDERING_GRADES = [
    # score, v_scale, french
    (0, 'V0', '4'),
    (5, 'V1', '5'),
    (10, 'V2', '5+'),
    (15, 'V3', '6A'),
    (20, 'V4', '6B'),
    (25, 'V5', '6C'),
    (30, 'V6', '7A'),
    (35, 'V7', '7A+'),
    (40, 'V8', '7B'),
    (45, 'V9', '7B+'),
    (50, 'V10', '7C'),
    (55, 'V11', '7C+'),
    (60, 'V12', '8A'),
    (65, 'V13', '8A+'),
    (70, 'V14', '8B'),
    (75, 'V15', '8B+'),
    (80, 'V16', '8C'),
]
```

### 2.3 Conversion Logic

```python
# users/utils.py

import re

def normalize_grade(grade: str, grade_system: str) -> str:
    """
    Normalize user-entered grade to match database format.

    Handles common variations:
    - Case: "5.10a" vs "5.10A", "6a+" vs "6A+", "V3" vs "v3"
    - Spaces: "V 3" → "V3", "5. 10a" → "5.10a"
    - French formatting: "6A+" → "6a+"

    Args:
        grade: Raw user input
        grade_system: 'yds', 'french', or 'v_scale'

    Returns:
        Normalized grade string
    """
    # Strip whitespace
    grade = grade.strip()

    # Remove internal spaces
    grade = re.sub(r'\s+', '', grade)

    if grade_system == 'yds':
        # YDS: lowercase letter suffix (5.10a, not 5.10A)
        # Pattern: 5.XX[a-d]
        grade = re.sub(r'([0-9]+)\.([0-9]+)([a-dA-D]?)', lambda m: f"{m.group(1)}.{m.group(2)}{m.group(3).lower()}", grade)

    elif grade_system == 'french':
        # French: lowercase letter, preserve + (6a+, not 6A+)
        # Pattern: [4-9][a-c][+]?
        grade = re.sub(r'([4-9])([a-cA-C])(\+?)', lambda m: f"{m.group(1)}{m.group(2).lower()}{m.group(3)}", grade)

    elif grade_system == 'v_scale':
        # V-Scale: uppercase V, rest is number (V3, not v3 or V 3)
        grade = re.sub(r'^v', 'V', grade, flags=re.IGNORECASE)

    return grade


def grade_to_score(grade_display: str, grade_system: str, discipline: str) -> int:
    """
    Convert user-entered grade to internal score.

    Args:
        grade_display: e.g., "5.10a", "6b", "V3"
        grade_system: "yds", "french", "v_scale"
        discipline: "sport", "bouldering", etc.

    Returns:
        int: Normalized score 0-100

    Raises:
        ValueError: If grade not found
    """
    # Normalize input before lookup
    normalized_grade = normalize_grade(grade_display, grade_system)

    field_map = {
        'yds': 'yds_grade',
        'french': 'french_grade',
        'v_scale': 'v_scale_grade',
    }

    field = field_map[grade_system]

    try:
        conversion = GradeConversion.objects.get(
            discipline=discipline,
            **{field: normalized_grade}
        )
        return conversion.score
    except GradeConversion.DoesNotExist:
        raise ValueError(f"Grade '{normalized_grade}' not found in {grade_system} for {discipline}")


def score_to_grade(score: int, grade_system: str, discipline: str) -> str:
    """Convert score back to display grade (finds closest grade <= score)"""
    field_map = {
        'yds': 'yds_grade',
        'french': 'french_grade',
        'v_scale': 'v_scale_grade',
    }

    field = field_map[grade_system]

    conversion = GradeConversion.objects.filter(
        discipline=discipline,
        score__lte=score
    ).order_by('-score').first()

    if conversion:
        return getattr(conversion, field)
    return None
```

**Key Features:**
- ✅ **Grade normalization** - Handles case, spacing, and formatting variations
- ✅ **Safe lookups** - Normalizes before querying to prevent mismatches
- ✅ **System-specific rules** - YDS lowercase letters, French lowercase with +, V-Scale uppercase V

---

### 2.4 Location Seed Data

Create management command to seed ~30-50 top climbing destinations with major crags.

```python
# trips/management/commands/seed_locations.py

from decimal import Decimal
from django.core.management.base import BaseCommand
from trips.models import Destination, Crag

DESTINATIONS = {
    'red-river-gorge': {
        'name': 'Red River Gorge, KY',
        'country': 'USA',
        'lat': Decimal('37.7781'),
        'lng': Decimal('-83.6816'),
        'disciplines': ['sport', 'trad'],
        'season': 'Oct-May (best)',
        'description': 'World-class sport climbing in sandstone',
        'crags': [
            {'name': 'Muir Valley', 'slug': 'muir-valley', 'disciplines': ['sport'], 'routes': 400},
            {'name': "Miguel's Pizza", 'slug': 'miguels', 'disciplines': ['sport'], 'routes': 300},
            {'name': 'PMRP', 'slug': 'pmrp', 'disciplines': ['sport', 'trad'], 'routes': 500},
            {'name': 'The Motherlode', 'slug': 'motherlode', 'disciplines': ['sport'], 'routes': 200},
            {'name': 'Left Flank', 'slug': 'left-flank', 'disciplines': ['sport'], 'routes': 150},
        ]
    },
    'railay': {
        'name': 'Railay, Krabi',
        'country': 'Thailand',
        'lat': Decimal('8.0097'),
        'lng': Decimal('98.8395'),
        'disciplines': ['sport'],
        'season': 'Nov-Apr (dry season)',
        'description': 'Limestone sport climbing paradise',
        'crags': [
            {'name': 'Thaiwand Wall', 'slug': 'thaiwand', 'disciplines': ['sport'], 'routes': 200},
            {'name': 'Fire Wall', 'slug': 'fire-wall', 'disciplines': ['sport'], 'routes': 100},
            {'name': 'Diamond Cave', 'slug': 'diamond-cave', 'disciplines': ['sport'], 'routes': 50},
            {'name': 'Ao Nang Tower', 'slug': 'ao-nang', 'disciplines': ['sport'], 'routes': 80},
        ]
    },
    'kalymnos': {
        'name': 'Kalymnos',
        'country': 'Greece',
        'lat': Decimal('36.9500'),
        'lng': Decimal('26.9833'),
        'disciplines': ['sport'],
        'season': 'Oct-May',
        'description': 'Greek island with endless limestone routes',
        'crags': [
            {'name': 'Grande Grotta', 'slug': 'grande-grotta', 'disciplines': ['sport'], 'routes': 300},
            {'name': 'Odyssey', 'slug': 'odyssey', 'disciplines': ['sport'], 'routes': 150},
            {'name': 'Arginonta Valley', 'slug': 'arginonta', 'disciplines': ['sport'], 'routes': 200},
        ]
    },
    'yosemite': {
        'name': 'Yosemite, CA',
        'country': 'USA',
        'lat': Decimal('37.7459'),
        'lng': Decimal('-119.5937'),
        'disciplines': ['trad', 'multipitch', 'bouldering'],
        'season': 'Apr-Oct',
        'description': 'Iconic granite big walls',
        'crags': [
            {'name': 'El Capitan', 'slug': 'el-cap', 'disciplines': ['trad', 'multipitch'], 'routes': 100},
            {'name': 'Camp 4 Boulders', 'slug': 'camp4', 'disciplines': ['bouldering'], 'routes': 300},
        ]
    },
    'red-rocks': {
        'name': 'Red Rocks, NV',
        'country': 'USA',
        'lat': Decimal('36.1347'),
        'lng': Decimal('-115.4268'),
        'disciplines': ['sport', 'trad', 'multipitch'],
        'season': 'Oct-May',
        'description': 'Red sandstone near Las Vegas',
        'crags': [
            {'name': 'Black Velvet Canyon', 'slug': 'black-velvet', 'disciplines': ['trad', 'multipitch'], 'routes': 50},
            {'name': 'Calico Basin', 'slug': 'calico', 'disciplines': ['sport'], 'routes': 200},
        ]
    },
    'smith-rock': {
        'name': 'Smith Rock, OR',
        'country': 'USA',
        'lat': Decimal('44.3672'),
        'lng': Decimal('-121.1407'),
        'disciplines': ['sport', 'trad'],
        'season': 'Mar-Nov',
        'description': 'Birthplace of American sport climbing',
        'crags': []  # Can add later
    },
    'el-chorro': {
        'name': 'El Chorro',
        'country': 'Spain',
        'lat': Decimal('36.9186'),
        'lng': Decimal('-4.7686'),
        'disciplines': ['sport', 'multipitch'],
        'season': 'Oct-May',
        'description': 'Spanish limestone with long routes',
        'crags': []
    },
    'fontainebleau': {
        'name': 'Fontainebleau',
        'country': 'France',
        'lat': Decimal('48.4084'),
        'lng': Decimal('2.7002'),
        'disciplines': ['bouldering'],
        'season': 'Apr-May, Sep-Oct',
        'description': 'World-famous bouldering forest',
        'crags': []
    },
    'tonsai': {
        'name': 'Tonsai, Krabi',
        'country': 'Thailand',
        'lat': Decimal('8.0155'),
        'lng': Decimal('98.8347'),
        'disciplines': ['sport'],
        'season': 'Nov-Apr',
        'description': 'Beach-side limestone climbing',
        'crags': []
    },
}

class Command(BaseCommand):
    help = 'Seed climbing destinations and crags'

    def handle(self, *args, **options):
        self.stdout.write('Seeding destinations...')

        for slug, data in DESTINATIONS.items():
            destination, created = Destination.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': data['name'],
                    'country': data['country'],
                    'lat': data['lat'],
                    'lng': data['lng'],
                    'primary_disciplines': data['disciplines'],
                    'season': data.get('season', ''),
                    'description': data.get('description', ''),
                }
            )

            status = 'Created' if created else 'Updated'
            self.stdout.write(f"  {status}: {destination.name}")

            # Create crags
            for crag_data in data.get('crags', []):
                crag, created = Crag.objects.update_or_create(
                    destination=destination,
                    slug=crag_data['slug'],
                    defaults={
                        'name': crag_data['name'],
                        'disciplines': crag_data['disciplines'],
                        'route_count': crag_data.get('routes'),
                    }
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f"    {status} crag: {crag.name}")

        self.stdout.write(self.style.SUCCESS('✓ Destinations seeded successfully'))
```

**Usage:**
```bash
python manage.py seed_locations
```

**MVP Destinations (Priority 1):**
- Red River Gorge, KY (USA) - sport/trad
- Railay, Krabi (Thailand) - sport
- Kalymnos (Greece) - sport
- Yosemite, CA (USA) - trad/multipitch/bouldering
- Red Rocks, NV (USA) - sport/trad/multipitch
- Smith Rock, OR (USA) - sport/trad
- El Chorro (Spain) - sport/multipitch
- Fontainebleau (France) - bouldering
- Tonsai, Krabi (Thailand) - sport

**Expand later with:**
- El Potrero Chico (Mexico)
- Squamish (Canada)
- Index, WA (USA)
- Joshua Tree, CA (USA)
- Margalef (Spain)
- Ceuse (France)
- Arco (Italy)
- Leonidio (Greece)
- And more...

---

## 3. Implementation Checklist

### Django Models
- [ ] Extend User model in `users/models.py`
- [ ] Create DisciplineProfile model
- [ ] Create ExperienceTag + UserExperienceTag models
- [ ] Create Block + Report models
- [ ] Create GradeConversion model
- [ ] **Create Destination model in `trips/`**
- [ ] **Create Crag model in `trips/`**
- [ ] Create Trip + AvailabilityBlock models in `trips/`
- [ ] Create Session + Message + Feedback models in `climbing_sessions/`

### Migrations
- [ ] Configure `AUTH_USER_MODEL` in settings
- [ ] Run `makemigrations`
- [ ] Run `migrate`

### Seed Data
- [ ] Create management command `seed_grades`
- [ ] Create management command `seed_experience_tags`
- [ ] **Create management command `seed_locations`**
- [ ] Run all seed commands

### Utilities
- [ ] Implement `grade_to_score()` function
- [ ] Implement `score_to_grade()` function
- [ ] Write unit tests for grade conversion

### Admin Interface
- [ ] Register all models in admin.py
- [ ] Add list filters and search
- [ ] Test CRUD operations

---

## 4. Testing Requirements

### Unit Tests
```python
# tests/test_models.py
def test_user_creation()
def test_discipline_profile_unique_constraint()
def test_trip_date_validation()
def test_block_prevents_duplicate()

# tests/test_grade_conversion.py
def test_yds_to_score()
def test_french_to_score()
def test_v_scale_to_score()
def test_score_to_yds()
def test_invalid_grade_raises_error()
```

### Integration Tests
- Test creating a full user profile with multiple disciplines
- Test grade conversions across all systems
- Test block enforcement in queries

---

## 5. Dependencies

**Required before:**
- Django project setup ✓
- PostgreSQL connection ✓

**Blocks:**
- Authentication (needs User model)
- Trip management (needs Trip model)
- Matching (needs all models + grade system)

---

## 6. Estimated Timeline

- Models implementation: 3-4 hours
- **Location models (Destination + Crag): 1 hour**
- Grade conversion system: 2 hours
- Seed data (grades + experience tags): 1 hour
- **Location seed data: 2 hours**
- Testing: 2 hours
- **Total: ~11 hours** (was 8 hours)

---

## Next Phase
Once Phase 1 is complete, move to **Phase 2: Authentication & User Management**.
