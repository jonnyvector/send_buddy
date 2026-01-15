from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import uuid


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

    # Mountain Project integration
    mp_id = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text='Mountain Project area ID')
    mp_url = models.URLField(blank=True, help_text='Mountain Project area URL')
    mp_star_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, help_text='Mountain Project star rating (0-4)')
    mp_star_votes = models.IntegerField(null=True, blank=True, help_text='Number of star rating votes')
    location_hierarchy = models.JSONField(default=list, help_text='Location hierarchy from MP (e.g., ["USA", "Kentucky", "Red River Gorge"])')
    last_synced = models.DateTimeField(null=True, blank=True, help_text='Last time data was synced from Mountain Project')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'destinations'
        ordering = ['name']

    def __str__(self):
        return self.name


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

    # Mountain Project integration
    mp_id = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text='Mountain Project area/crag ID')
    mp_url = models.URLField(blank=True, help_text='Mountain Project URL')
    mp_star_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, help_text='Mountain Project star rating (0-4)')
    parent_area_mp_id = models.CharField(max_length=50, blank=True, null=True, help_text='Mountain Project ID of parent area')
    last_synced = models.DateTimeField(null=True, blank=True, help_text='Last time data was synced from Mountain Project')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crags'
        unique_together = ['destination', 'slug']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.destination.name})"


class Trip(models.Model):
    """A climbing trip (date range + location)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')

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

    # Grade preferences
    grade_system = models.CharField(
        max_length=20,
        blank=True,
        help_text="Grade system used (yds, french, v_scale)"
    )
    min_grade = models.CharField(
        max_length=10,
        blank=True,
        help_text="Minimum grade for this trip (e.g., '5.10a', 'V4', '6b')"
    )
    max_grade = models.CharField(
        max_length=10,
        blank=True,
        help_text="Maximum grade for this trip (e.g., '5.12c', 'V8', '7b')"
    )

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
