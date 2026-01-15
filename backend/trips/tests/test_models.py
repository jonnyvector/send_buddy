from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from users.models import User
from trips.models import Destination, Crag, Trip, AvailabilityBlock, TimeBlock


class DestinationModelTest(TestCase):
    """Test Destination model"""

    def test_create_destination(self):
        """Test creating a destination"""
        destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6,
            primary_disciplines=['sport', 'trad']
        )
        self.assertEqual(destination.name, 'Red River Gorge, KY')
        self.assertEqual(destination.country, 'USA')
        self.assertIn('sport', destination.primary_disciplines)

    def test_destination_slug_unique(self):
        """Test destination slug must be unique"""
        Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        with self.assertRaises(Exception):  # IntegrityError
            Destination.objects.create(
                slug='red-river-gorge',  # Duplicate
                name='Different Name',
                country='USA',
                lat=37.7,
                lng=-83.6
            )


class CragModelTest(TestCase):
    """Test Crag model"""

    def setUp(self):
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

    def test_create_crag(self):
        """Test creating a crag"""
        crag = Crag.objects.create(
            destination=self.destination,
            name='Muir Valley',
            slug='muir-valley',
            disciplines=['sport'],
            approach_time=10,
            route_count=200
        )
        self.assertEqual(crag.name, 'Muir Valley')
        self.assertEqual(crag.destination, self.destination)
        self.assertIn('sport', crag.disciplines)

    def test_crag_unique_per_destination(self):
        """Test crag slug must be unique per destination"""
        Crag.objects.create(
            destination=self.destination,
            name='Muir Valley',
            slug='muir-valley'
        )

        with self.assertRaises(Exception):  # IntegrityError
            Crag.objects.create(
                destination=self.destination,
                name='Different Name',
                slug='muir-valley'  # Duplicate for same destination
            )


class TripModelTest(TestCase):
    """Test Trip model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

    def test_create_trip(self):
        """Test creating a trip"""
        trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            preferred_disciplines=['sport', 'trad']
        )
        self.assertEqual(trip.user, self.user)
        self.assertEqual(trip.destination, self.destination)
        self.assertTrue(trip.is_active)

    def test_trip_date_validation(self):
        """Test end_date must be >= start_date"""
        trip = Trip(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=1)  # Before start
        )
        with self.assertRaises(ValidationError):
            trip.clean()

    def test_trip_cannot_be_in_past(self):
        """Test new trip cannot start in the past"""
        trip = Trip(
            user=self.user,
            destination=self.destination,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            trip.clean()

    def test_trip_is_active_default(self):
        """Test is_active defaults to True"""
        trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )
        self.assertTrue(trip.is_active)

    def test_validate_crags_belong_to_destination(self):
        """Test crags must belong to trip's destination"""
        other_destination = Destination.objects.create(
            slug='yosemite',
            name='Yosemite, CA',
            country='USA',
            lat=37.8,
            lng=-119.5
        )

        crag1 = Crag.objects.create(
            destination=self.destination,
            name='Muir Valley',
            slug='muir-valley'
        )

        crag2 = Crag.objects.create(
            destination=other_destination,
            name='El Capitan',
            slug='el-capitan'
        )

        trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        # Add valid crag
        trip.preferred_crags.add(crag1)

        # Add invalid crag (different destination)
        trip.preferred_crags.add(crag2)

        with self.assertRaises(ValidationError):
            trip.validate_crags_belong_to_destination()


class AvailabilityBlockModelTest(TestCase):
    """Test AvailabilityBlock model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )
        self.trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

    def test_create_availability_block(self):
        """Test creating an availability block"""
        block = AvailabilityBlock.objects.create(
            trip=self.trip,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )
        self.assertEqual(block.trip, self.trip)
        self.assertEqual(block.time_block, TimeBlock.MORNING)

    def test_availability_date_within_trip_dates(self):
        """Test availability date must be within trip dates"""
        block = AvailabilityBlock(
            trip=self.trip,
            date=date.today() + timedelta(days=10),  # After trip end
            time_block=TimeBlock.MORNING
        )
        with self.assertRaises(ValidationError):
            block.clean()

    def test_availability_date_before_trip_start(self):
        """Test availability date must be after trip start"""
        block = AvailabilityBlock(
            trip=self.trip,
            date=date.today() - timedelta(days=1),  # Before trip start
            time_block=TimeBlock.AFTERNOON
        )
        with self.assertRaises(ValidationError):
            block.clean()

    def test_unique_trip_date_time_block(self):
        """Test trip+date+time_block must be unique"""
        AvailabilityBlock.objects.create(
            trip=self.trip,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )

        with self.assertRaises(Exception):  # IntegrityError
            AvailabilityBlock.objects.create(
                trip=self.trip,
                date=date.today(),
                time_block=TimeBlock.MORNING  # Duplicate
            )

    def test_multiple_time_blocks_same_date(self):
        """Test can have multiple time blocks on same date"""
        AvailabilityBlock.objects.create(
            trip=self.trip,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )
        AvailabilityBlock.objects.create(
            trip=self.trip,
            date=date.today(),
            time_block=TimeBlock.AFTERNOON
        )

        self.assertEqual(
            AvailabilityBlock.objects.filter(trip=self.trip, date=date.today()).count(),
            2
        )
