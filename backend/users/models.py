from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
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


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def visible_to(self, viewer):
        return self.get_queryset().visible_to(viewer)

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class RiskTolerance(models.TextChoices):
    CONSERVATIVE = 'conservative', 'Conservative'
    BALANCED = 'balanced', 'Balanced'
    AGGRESSIVE = 'aggressive', 'Aggressive'


class GradeSystem(models.TextChoices):
    YDS = 'yds', 'YDS'
    FRENCH = 'french', 'French'
    V_SCALE = 'v_scale', 'V-Scale'


class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    NON_BINARY = 'non_binary', 'Non-binary'
    PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'


class PartnerGenderPreference(models.TextChoices):
    NO_PREFERENCE = 'no_preference', 'No preference'
    PREFER_MALE = 'prefer_male', 'Prefer male'
    PREFER_FEMALE = 'prefer_female', 'Prefer female'
    PREFER_NON_BINARY = 'prefer_non_binary', 'Prefer non-binary'
    SAME_GENDER = 'same_gender', 'Same gender as me'


class WeightDifferencePreference(models.TextChoices):
    NO_PREFERENCE = 'no_preference', 'No preference'
    SIMILAR = 'similar', 'Similar weight (± 15kg / 33lbs)'
    MODERATE = 'moderate', 'Moderate difference (± 30kg / 66lbs)'
    CLOSE = 'close', 'Close weight (± 10kg / 22lbs)'


class User(AbstractUser):
    """Extended user model with climbing-specific fields"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Override email to make it unique and required
    email = models.EmailField(unique=True)

    # Override username to make it optional (using email for auth instead)
    username = models.CharField(max_length=150, blank=True, null=True)

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

    # Gender & Partner Preferences
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
        help_text="Your gender identity (optional)"
    )

    preferred_partner_gender = models.CharField(
        max_length=20,
        choices=PartnerGenderPreference.choices,
        default=PartnerGenderPreference.NO_PREFERENCE,
        help_text="Gender preference for climbing partners"
    )

    # Weight & Belay Safety
    weight_kg = models.IntegerField(
        null=True,
        blank=True,
        help_text="Your weight in kilograms (for belay safety matching)"
    )

    preferred_weight_difference = models.CharField(
        max_length=20,
        choices=WeightDifferencePreference.choices,
        default=WeightDifferencePreference.NO_PREFERENCE,
        help_text="Acceptable weight difference for safe belaying"
    )

    # Profile visibility
    profile_visible = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Email verification (disabled for dev - normally False)
    email_verified = models.BooleanField(default=True)

    # Use email for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']  # Required for createsuperuser (email is already required)

    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.display_name} ({self.email})"


class Discipline(models.TextChoices):
    SPORT = 'sport', 'Sport Climbing'
    TRAD = 'trad', 'Trad Climbing'
    BOULDERING = 'bouldering', 'Bouldering'
    MULTIPITCH = 'multipitch', 'Multipitch'
    GYM = 'gym', 'Gym Climbing'


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

    def save(self, *args, **kwargs):
        """Auto-compute grade scores before saving"""
        from .utils import grade_to_score

        # Compute comfortable grade scores
        self.comfortable_grade_min_score = grade_to_score(
            self.comfortable_grade_min_display,
            self.grade_system,
            self.discipline
        )
        self.comfortable_grade_max_score = grade_to_score(
            self.comfortable_grade_max_display,
            self.grade_system,
            self.discipline
        )

        # Compute projecting grade score if provided
        if self.projecting_grade_display:
            self.projecting_grade_score = grade_to_score(
                self.projecting_grade_display,
                self.grade_system,
                self.discipline
            )
        else:
            self.projecting_grade_score = None

        # Run validation
        self.full_clean()

        super().save(*args, **kwargs)


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

    def __str__(self):
        return self.display_name


class UserExperienceTag(models.Model):
    """Many-to-many through table for user tags"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experience_tags')
    tag = models.ForeignKey(ExperienceTag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_experience_tags'
        unique_together = ['user', 'tag']

    def __str__(self):
        return f"{self.user.display_name} - {self.tag.display_name}"


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

    def __str__(self):
        return f"Report by {self.reporter.display_name} about {self.reported.display_name}"
