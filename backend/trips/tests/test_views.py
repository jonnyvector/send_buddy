from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from users.models import User
from trips.models import Destination, Crag, Trip, AvailabilityBlock, TimeBlock


class DestinationViewSetTest(TestCase):
    """Test destination endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.destination1 = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6,
            primary_disciplines=['sport', 'trad']
        )
        self.destination2 = Destination.objects.create(
            slug='yosemite',
            name='Yosemite, CA',
            country='USA',
            lat=37.8,
            lng=-119.5,
            primary_disciplines=['trad', 'bouldering']
        )

    def test_list_destinations(self):
        """Test listing destinations"""
        url = reverse('destination-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_search_destinations(self):
        """Test searching destinations"""
        url = reverse('destination-list')
        response = self.client.get(url, {'search': 'River'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['slug'], 'red-river-gorge')

    def test_get_destination_detail(self):
        """Test getting destination detail"""
        url = reverse('destination-detail', kwargs={'slug': 'red-river-gorge'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Red River Gorge, KY')
        self.assertIn('sport', response.data['primary_disciplines'])

    def test_list_destination_crags(self):
        """Test listing crags for a destination"""
        crag = Crag.objects.create(
            destination=self.destination1,
            name='Muir Valley',
            slug='muir-valley',
            disciplines=['sport']
        )

        url = reverse('destination-crags', kwargs={'slug': 'red-river-gorge'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['crags']), 1)
        self.assertEqual(response.data['crags'][0]['name'], 'Muir Valley')


class TripViewSetTest(TestCase):
    """Test trip CRUD endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.client.force_authenticate(user=self.user)

        self.destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

    def test_create_trip(self):
        """Test creating a trip"""
        url = reverse('trip-list')
        data = {
            'destination': 'red-river-gorge',
            'start_date': str(date.today() + timedelta(days=1)),
            'end_date': str(date.today() + timedelta(days=5)),
            'preferred_disciplines': ['sport', 'trad'],
            'notes': 'Looking forward to this trip!'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trip.objects.filter(user=self.user).count(), 1)

        trip = Trip.objects.get(user=self.user)
        self.assertEqual(trip.destination, self.destination)
        self.assertIn('sport', trip.preferred_disciplines)

    def test_list_user_trips(self):
        """Test listing user's trips"""
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15)
        )

        url = reverse('trip-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_active_trips(self):
        """Test filtering by is_active"""
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            is_active=True
        )
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            is_active=False
        )

        url = reverse('trip-list')
        response = self.client.get(url, {'is_active': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_trip(self):
        """Test updating a trip"""
        trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        url = reverse('trip-detail', kwargs={'pk': str(trip.id)})
        data = {
            'notes': 'Updated notes',
            'is_active': False
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.notes, 'Updated notes')
        self.assertFalse(trip.is_active)

    def test_delete_trip(self):
        """Test deleting a trip"""
        trip = Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        url = reverse('trip-detail', kwargs={'pk': str(trip.id)})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Trip.objects.filter(id=trip.id).exists())

    def test_cannot_access_other_users_trip(self):
        """Test cannot access another user's trip"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='password123',
            display_name='Other User',
            home_location='Denver, CO'
        )
        other_trip = Trip.objects.create(
            user=other_user,
            destination=self.destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )

        url = reverse('trip-detail', kwargs={'pk': str(other_trip.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_next_upcoming_trip(self):
        """Test getting next upcoming trip"""
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            is_active=True
        )
        Trip.objects.create(
            user=self.user,
            destination=self.destination,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            is_active=True
        )

        url = reverse('trip-next')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return earliest upcoming trip
        self.assertEqual(
            response.data['start_date'],
            str(date.today() + timedelta(days=1))
        )


class AvailabilityBlockViewSetTest(TestCase):
    """Test availability block endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.client.force_authenticate(user=self.user)

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

    def test_add_availability_block(self):
        """Test adding an availability block"""
        url = reverse('trip-add-availability', kwargs={'pk': str(self.trip.id)})
        data = {
            'date': str(date.today()),
            'time_block': TimeBlock.MORNING
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            AvailabilityBlock.objects.filter(trip=self.trip).count(),
            1
        )

    def test_bulk_add_availability(self):
        """Test bulk adding availability blocks"""
        url = reverse('trip-bulk-add-availability', kwargs={'pk': str(self.trip.id)})
        data = {
            'blocks': [
                {
                    'date': str(date.today()),
                    'time_block': TimeBlock.MORNING
                },
                {
                    'date': str(date.today() + timedelta(days=1)),
                    'time_block': TimeBlock.AFTERNOON
                }
            ]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created'], 2)
        self.assertEqual(response.data['failed'], 0)

    def test_availability_date_validation(self):
        """Test availability date must be within trip dates"""
        url = reverse('trip-add-availability', kwargs={'pk': str(self.trip.id)})
        data = {
            'date': str(date.today() + timedelta(days=10)),  # Outside trip
            'time_block': TimeBlock.MORNING
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_availability_block(self):
        """Test deleting an availability block"""
        block = AvailabilityBlock.objects.create(
            trip=self.trip,
            date=date.today(),
            time_block=TimeBlock.MORNING
        )

        url = reverse('availabilityblock-detail', kwargs={'pk': str(block.id)})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AvailabilityBlock.objects.filter(id=block.id).exists())


class MapDestinationsAPITestCase(TestCase):
    """Test map destinations API endpoint"""

    def setUp(self):
        self.client = APIClient()

        # Create destinations
        self.destination1 = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge',
            country='Kentucky, USA',
            lat=37.7833,
            lng=-83.6833,
            primary_disciplines=['sport', 'trad']
        )
        self.destination2 = Destination.objects.create(
            slug='yosemite',
            name='Yosemite',
            country='California, USA',
            lat=37.8651,
            lng=-119.5383,
            primary_disciplines=['trad', 'bouldering']
        )
        self.destination3 = Destination.objects.create(
            slug='fontainebleau',
            name='Fontainebleau',
            country='France',
            lat=48.4040,
            lng=2.6990,
            primary_disciplines=['bouldering']
        )

        # Create users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO'
        )
        self.user3 = User.objects.create_user(
            email='user3@example.com',
            password='password123',
            display_name='User 3',
            home_location='Austin, TX'
        )

        # Create active trips
        self.trip1 = Trip.objects.create(
            user=self.user1,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            is_active=True,
            preferred_disciplines=['sport', 'trad']
        )
        self.trip2 = Trip.objects.create(
            user=self.user2,
            destination=self.destination1,
            start_date=date.today() + timedelta(days=12),
            end_date=date.today() + timedelta(days=18),
            is_active=True,
            preferred_disciplines=['sport']
        )
        self.trip3 = Trip.objects.create(
            user=self.user3,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=25),
            is_active=True,
            preferred_disciplines=['trad', 'bouldering']
        )

        # Create inactive trip (should be excluded)
        self.trip4 = Trip.objects.create(
            user=self.user1,
            destination=self.destination2,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=35),
            is_active=False,
            preferred_disciplines=['sport']
        )

    def test_map_destinations_returns_all_active(self):
        """Test GET without filters returns all destinations with active trips"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('destinations', response.data)

        destinations = response.data['destinations']
        self.assertEqual(len(destinations), 2)  # Only dest1 and dest2 have active trips

        # Verify destination3 not included (no trips)
        slugs = [d['slug'] for d in destinations]
        self.assertIn('red-river-gorge', slugs)
        self.assertIn('yosemite', slugs)
        self.assertNotIn('fontainebleau', slugs)

    def test_map_destinations_trip_count_accuracy(self):
        """Test active_trip_count is accurate"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        destinations = {d['slug']: d for d in response.data['destinations']}

        # Red River Gorge has 2 active trips
        self.assertEqual(destinations['red-river-gorge']['active_trip_count'], 2)

        # Yosemite has 1 active trip (inactive trip excluded)
        self.assertEqual(destinations['yosemite']['active_trip_count'], 1)

    def test_map_destinations_user_count_accuracy(self):
        """Test active_user_count counts distinct users"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        destinations = {d['slug']: d for d in response.data['destinations']}

        # Red River Gorge has 2 distinct users
        self.assertEqual(destinations['red-river-gorge']['active_user_count'], 2)

        # Yosemite has 1 user
        self.assertEqual(destinations['yosemite']['active_user_count'], 1)

    def test_map_destinations_disciplines_unique_sorted(self):
        """Test disciplines list is unique and sorted"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        destinations = {d['slug']: d for d in response.data['destinations']}

        # Red River Gorge should have unique sorted disciplines from both trips
        rrg_disciplines = destinations['red-river-gorge']['disciplines']
        self.assertEqual(rrg_disciplines, ['sport', 'trad'])

        # Yosemite should have disciplines from active trip only
        yose_disciplines = destinations['yosemite']['disciplines']
        self.assertEqual(yose_disciplines, ['bouldering', 'trad'])

    def test_map_destinations_date_range(self):
        """Test date_range shows correct earliest/latest dates"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        destinations = {d['slug']: d for d in response.data['destinations']}

        # Red River Gorge: earliest = trip1 start, latest = trip2 end
        rrg = destinations['red-river-gorge']
        self.assertEqual(
            rrg['date_range']['earliest_arrival'],
            str(date.today() + timedelta(days=10))
        )
        self.assertEqual(
            rrg['date_range']['latest_departure'],
            str(date.today() + timedelta(days=18))
        )

    def test_map_destinations_with_start_date_filter(self):
        """Test GET with start_date filter"""
        url = reverse('map_destinations')
        filter_date = str(date.today() + timedelta(days=15))
        response = self.client.get(url, {'start_date': filter_date})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # Only trips starting on/after filter_date
        # trip1 starts day 10 (excluded), trip2 starts day 12 (excluded), trip3 starts day 20 (included)
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0]['slug'], 'yosemite')

    def test_map_destinations_with_end_date_filter(self):
        """Test GET with end_date filter"""
        url = reverse('map_destinations')
        filter_date = str(date.today() + timedelta(days=20))
        response = self.client.get(url, {'end_date': filter_date})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # Only trips ending on/before filter_date
        # trip1 ends day 15 (included), trip2 ends day 18 (included), trip3 ends day 25 (excluded)
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0]['slug'], 'red-river-gorge')

    def test_map_destinations_with_both_date_filters(self):
        """Test GET with both start_date and end_date filters"""
        url = reverse('map_destinations')
        start = str(date.today() + timedelta(days=10))
        end = str(date.today() + timedelta(days=16))
        response = self.client.get(url, {'start_date': start, 'end_date': end})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # trip1: starts day 10, ends day 15 (included)
        # trip2: starts day 12, ends day 18 (excluded - ends after filter)
        # trip3: starts day 20, ends day 25 (excluded - starts after filter)
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0]['slug'], 'red-river-gorge')

    def test_map_destinations_with_single_discipline_filter(self):
        """Test GET with single discipline filter"""
        url = reverse('map_destinations')
        response = self.client.get(url, {'disciplines': 'bouldering'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # Only yosemite has bouldering in active trips
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0]['slug'], 'yosemite')

    def test_map_destinations_with_multiple_disciplines_filter(self):
        """Test GET with multiple disciplines filter"""
        url = reverse('map_destinations')
        response = self.client.get(url, {'disciplines': 'sport,trad'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # Both destinations should appear (have sport OR trad)
        slugs = [d['slug'] for d in destinations]
        self.assertIn('red-river-gorge', slugs)
        self.assertIn('yosemite', slugs)

    def test_map_destinations_with_combined_filters(self):
        """Test GET with combined date and discipline filters"""
        url = reverse('map_destinations')
        start = str(date.today() + timedelta(days=19))
        response = self.client.get(url, {
            'start_date': start,
            'disciplines': 'bouldering'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        destinations = response.data['destinations']

        # Only trip3 matches (starts day 20 and has bouldering)
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0]['slug'], 'yosemite')

    def test_map_destinations_inactive_trips_excluded(self):
        """Test that inactive trips are excluded from results"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        destinations = {d['slug']: d for d in response.data['destinations']}

        # Yosemite should only count 1 trip (inactive trip4 excluded)
        self.assertEqual(destinations['yosemite']['active_trip_count'], 1)

    def test_map_destinations_no_active_trips_excluded(self):
        """Test that destinations with no active trips are excluded"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        slugs = [d['slug'] for d in response.data['destinations']]

        # Fontainebleau has no trips at all
        self.assertNotIn('fontainebleau', slugs)

    def test_map_destinations_public_access(self):
        """Test public access (no authentication required)"""
        # Don't authenticate
        client = APIClient()
        url = reverse('map_destinations')
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('destinations', response.data)

    def test_map_destinations_empty_results(self):
        """Test edge case: filters with no matching trips"""
        url = reverse('map_destinations')
        # Filter for disciplines that don't exist
        response = self.client.get(url, {'disciplines': 'ice,alpine'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['destinations']), 0)

    def test_map_destinations_invalid_start_date_format(self):
        """Test invalid start_date format returns 400"""
        url = reverse('map_destinations')
        response = self.client.get(url, {'start_date': 'invalid-date'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_map_destinations_invalid_end_date_format(self):
        """Test invalid end_date format returns 400"""
        url = reverse('map_destinations')
        response = self.client.get(url, {'end_date': '2024/01/01'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_map_destinations_response_structure(self):
        """Test response format matches expected JSON structure"""
        url = reverse('map_destinations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('destinations', response.data)

        if len(response.data['destinations']) > 0:
            dest = response.data['destinations'][0]

            # Verify all required fields present
            required_fields = [
                'slug', 'name', 'location', 'lat', 'lng',
                'active_trip_count', 'active_user_count',
                'disciplines', 'date_range'
            ]
            for field in required_fields:
                self.assertIn(field, dest)

            # Verify date_range structure
            self.assertIn('earliest_arrival', dest['date_range'])
            self.assertIn('latest_departure', dest['date_range'])

            # Verify data types
            self.assertIsInstance(dest['active_trip_count'], int)
            self.assertIsInstance(dest['active_user_count'], int)
            self.assertIsInstance(dest['disciplines'], list)
