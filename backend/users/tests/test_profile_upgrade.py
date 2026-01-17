"""Tests for Profile Page Upgrade features"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User, UserMedia, Recommendation
from climbing_sessions.models import Session, SessionStatus
from friendships.models import Friendship
from trips.models import Trip, TimeBlock
import uuid
from datetime import date, timedelta
from io import BytesIO
from PIL import Image


class UserMediaTests(APITestCase):
    """Test UserMedia model and endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='climber@test.com',
            password='TestPass123',
            display_name='Test Climber',
            home_location='Denver, CO'
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='TestPass123',
            display_name='Other Climber',
            home_location='Boulder, CO'
        )
        self.client.force_authenticate(self.user)

    def create_test_image(self):
        """Helper to create test image file"""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), 'red')
        image.save(file, 'JPEG')
        file.seek(0)
        return SimpleUploadedFile(
            'test.jpg',
            file.read(),
            content_type='image/jpeg'
        )

    def test_upload_media(self):
        """Test uploading media to own profile"""
        image = self.create_test_image()

        response = self.client.post(
            '/api/users/me/media/',
            {
                'media_type': 'photo',
                'file': image,
                'caption': 'Sending my project',
                'location': 'Clear Creek Canyon',
                'climb_name': 'The Project'
            },
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserMedia.objects.count(), 1)

        media = UserMedia.objects.first()
        self.assertEqual(media.user, self.user)
        self.assertEqual(media.caption, 'Sending my project')
        self.assertEqual(media.location, 'Clear Creek Canyon')

    def test_cannot_upload_to_other_profile(self):
        """Test that users cannot upload media to another user's profile"""
        image = self.create_test_image()

        response = self.client.post(
            f'/api/users/{self.other_user.id}/media/',
            {
                'media_type': 'photo',
                'file': image,
                'caption': 'Hacked upload'
            },
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_view_public_media(self):
        """Test viewing another user's public media"""
        # Create public and private media for other user
        public_media = UserMedia.objects.create(
            user=self.other_user,
            media_type='photo',
            file='test.jpg',
            caption='Public photo',
            is_public=True
        )
        private_media = UserMedia.objects.create(
            user=self.other_user,
            media_type='photo',
            file='private.jpg',
            caption='Private photo',
            is_public=False
        )

        response = self.client.get(f'/api/users/{self.other_user.id}/media/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['caption'], 'Public photo')

    def test_delete_own_media(self):
        """Test deleting own media"""
        media = UserMedia.objects.create(
            user=self.user,
            media_type='photo',
            file='test.jpg',
            caption='My photo'
        )

        response = self.client.delete(f'/api/users/me/media/{media.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserMedia.objects.count(), 0)

    def test_cannot_delete_others_media(self):
        """Test that users cannot delete another user's media"""
        media = UserMedia.objects.create(
            user=self.other_user,
            media_type='photo',
            file='test.jpg',
            caption='Other photo'
        )

        response = self.client.delete(f'/api/users/{self.other_user.id}/media/{media.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(UserMedia.objects.count(), 1)


class RecommendationTests(APITestCase):
    """Test Recommendation model and endpoints"""

    def setUp(self):
        self.author = User.objects.create_user(
            email='author@test.com',
            password='TestPass123',
            display_name='Author User',
            home_location='Denver, CO'
        )
        self.recipient = User.objects.create_user(
            email='recipient@test.com',
            password='TestPass123',
            display_name='Recipient User',
            home_location='Boulder, CO'
        )
        self.third_user = User.objects.create_user(
            email='third@test.com',
            password='TestPass123',
            display_name='Third User',
            home_location='Golden, CO'
        )

    def test_write_recommendation(self):
        """Test writing a recommendation for another user"""
        self.client.force_authenticate(self.author)

        response = self.client.post(
            f'/api/users/{self.recipient.id}/recommendations/',
            {
                'body': 'Amazing climbing partner! Super safe belayer and great route reader.'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Recommendation.objects.count(), 1)

        rec = Recommendation.objects.first()
        self.assertEqual(rec.author, self.author)
        self.assertEqual(rec.recipient, self.recipient)
        self.assertEqual(rec.status, 'pending')

    def test_cannot_recommend_self(self):
        """Test that users cannot write recommendations for themselves"""
        self.client.force_authenticate(self.author)

        response = self.client.post(
            f'/api/users/{self.author.id}/recommendations/',
            {
                'body': 'I am the best climber ever!'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_write_duplicate_recommendation(self):
        """Test that users can only write one recommendation per recipient"""
        self.client.force_authenticate(self.author)

        # First recommendation
        Recommendation.objects.create(
            author=self.author,
            recipient=self.recipient,
            body='First recommendation'
        )

        # Try to write second
        response = self.client.post(
            f'/api/users/{self.recipient.id}/recommendations/',
            {
                'body': 'Second recommendation attempt'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_recommendation(self):
        """Test approving a recommendation"""
        rec = Recommendation.objects.create(
            author=self.author,
            recipient=self.recipient,
            body='Great partner!',
            status='pending'
        )

        self.client.force_authenticate(self.recipient)
        response = self.client.post(f'/api/users/me/recommendations/{rec.id}/approve/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rec.refresh_from_db()
        self.assertEqual(rec.status, 'approved')
        self.assertIsNotNone(rec.approved_at)

    def test_only_recipient_can_approve(self):
        """Test that only the recipient can approve recommendations"""
        rec = Recommendation.objects.create(
            author=self.author,
            recipient=self.recipient,
            body='Great partner!',
            status='pending'
        )

        # Try as author
        self.client.force_authenticate(self.author)
        response = self.client.post(f'/api/users/{self.recipient.id}/recommendations/{rec.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try as third party
        self.client.force_authenticate(self.third_user)
        response = self.client.post(f'/api/users/{self.recipient.id}/recommendations/{rec.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_only_sees_approved(self):
        """Test that public profiles only show approved recommendations"""
        # Create recommendations with different statuses
        Recommendation.objects.create(
            author=self.author,
            recipient=self.recipient,
            body='Approved rec',
            status='approved'
        )

        # Create a fourth user to avoid unique constraint violation
        fourth_user = User.objects.create_user(
            email='fourth@test.com',
            password='TestPass123',
            display_name='Fourth User',
            home_location='Arvada, CO'
        )

        Recommendation.objects.create(
            author=self.third_user,
            recipient=self.recipient,
            body='Pending rec',
            status='pending'
        )
        Recommendation.objects.create(
            author=fourth_user,
            recipient=self.recipient,
            body='Rejected rec',
            status='rejected'
        )

        self.client.force_authenticate(self.author)
        response = self.client.get(f'/api/users/{self.recipient.id}/recommendations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['body'], 'Approved rec')

    def test_sessions_together_computed(self):
        """Test that sessions_together is computed from completed sessions"""
        # Create a destination and trip for testing
        from trips.models import Destination
        destination = Destination.objects.create(
            name='Test Area',
            slug='test-area',
            region='Test Region',
            country='USA',
            lat=40.0,
            lng=-105.0
        )

        trip = Trip.objects.create(
            user=self.author,
            destination=destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            visibility_status='friends_only'
        )

        # Create completed sessions between users
        for _ in range(3):
            Session.objects.create(
                inviter=self.author,
                invitee=self.recipient,
                trip=trip,
                proposed_date=date.today(),
                time_block=TimeBlock.MORNING,
                status=SessionStatus.COMPLETED
            )

        rec = Recommendation.objects.create(
            author=self.author,
            recipient=self.recipient,
            body='Great climbing partner!'
        )

        rec.compute_sessions_together()

        self.assertEqual(rec.sessions_together, 3)
        self.assertTrue(rec.is_verified)


class ProfileStatsTests(APITestCase):
    """Test profile statistics endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='TestPass123',
            display_name='Test User',
            home_location='Denver, CO'
        )
        self.viewer = User.objects.create_user(
            email='viewer@test.com',
            password='TestPass123',
            display_name='Viewer User',
            home_location='Boulder, CO'
        )
        self.friend = User.objects.create_user(
            email='friend@test.com',
            password='TestPass123',
            display_name='Friend User',
            home_location='Golden, CO'
        )
        self.client.force_authenticate(self.viewer)

    def test_get_profile_stats(self):
        """Test getting profile statistics"""
        # Create some test data
        # Add friendship
        Friendship.objects.create(
            requester=self.user,
            addressee=self.friend,
            status='accepted'
        )

        # Add media
        UserMedia.objects.create(
            user=self.user,
            media_type='photo',
            file='test.jpg',
            is_public=True
        )

        # Add approved recommendation
        Recommendation.objects.create(
            author=self.friend,
            recipient=self.user,
            body='Great climber!',
            status='approved'
        )

        # Create a destination and trip for sessions
        from trips.models import Destination
        destination = Destination.objects.create(
            name='Test Area',
            slug='test-area',
            region='Test Region',
            country='USA',
            lat=40.0,
            lng=-105.0
        )

        trip = Trip.objects.create(
            user=self.user,
            destination=destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            visibility_status='friends_only'
        )

        # Add completed session
        Session.objects.create(
            inviter=self.user,
            invitee=self.friend,
            trip=trip,
            proposed_date=date.today(),
            time_block=TimeBlock.MORNING,
            status=SessionStatus.COMPLETED
        )

        response = self.client.get(f'/api/users/{self.user.id}/profile-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completed_sessions_count'], 1)
        self.assertEqual(response.data['connections_count'], 1)
        self.assertEqual(response.data['recommendations_count'], 1)
        self.assertEqual(response.data['media_count'], 1)
        self.assertIn('member_since_year', response.data)

    def test_mutual_friends_count(self):
        """Test mutual friends calculation"""
        # Create mutual friend
        mutual = User.objects.create_user(
            email='mutual@test.com',
            password='TestPass123',
            display_name='Mutual Friend',
            home_location='Littleton, CO'
        )

        # User is friends with mutual
        Friendship.objects.create(
            requester=self.user,
            addressee=mutual,
            status='accepted'
        )

        # Viewer is friends with mutual
        Friendship.objects.create(
            requester=self.viewer,
            addressee=mutual,
            status='accepted'
        )

        response = self.client.get(f'/api/users/{self.user.id}/profile-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mutual_friends_count'], 1)

    def test_stats_respect_blocking(self):
        """Test that stats are not available for blocked users"""
        from users.models import Block

        # User blocks viewer
        Block.objects.create(
            blocker=self.user,
            blocked=self.viewer
        )

        response = self.client.get(f'/api/users/{self.user.id}/profile-stats/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProfileEnhancementFieldsTests(TestCase):
    """Test new User model fields"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='climber@test.com',
            password='TestPass123',
            display_name='Test Climber',
            home_location='Denver, CO'
        )

    def test_climber_attributes_defaults(self):
        """Test that climber attributes have correct defaults"""
        self.assertEqual(self.user.attr_endurance, 5)
        self.assertEqual(self.user.attr_power, 5)
        self.assertEqual(self.user.attr_technique, 5)
        self.assertEqual(self.user.attr_mental, 5)
        self.assertEqual(self.user.attr_flexibility, 5)

    def test_update_climber_attributes(self):
        """Test updating climber attributes"""
        self.user.attr_endurance = 8
        self.user.attr_power = 6
        self.user.attr_technique = 9
        self.user.attr_mental = 7
        self.user.attr_flexibility = 4
        self.user.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.attr_endurance, 8)
        self.assertEqual(self.user.attr_technique, 9)

    def test_profile_enhancement_fields(self):
        """Test new profile enhancement fields"""
        self.user.first_notable_send = 'The Diamond'
        self.user.first_send_year = 2019
        self.user.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_notable_send, 'The Diamond')
        self.assertEqual(self.user.first_send_year, 2019)

    def test_user_serializer_includes_new_fields(self):
        """Test that UserSerializer includes new fields"""
        from users.serializers import UserSerializer

        self.user.first_notable_send = 'El Capitan'
        self.user.first_send_year = 2020
        self.user.attr_endurance = 9
        self.user.save()

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data['first_notable_send'], 'El Capitan')
        self.assertEqual(data['first_send_year'], 2020)
        self.assertIn('attributes', data)
        self.assertEqual(data['attributes']['endurance'], 9)
        self.assertEqual(data['attributes']['power'], 5)