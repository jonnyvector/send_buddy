from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, DisciplineProfile, Block, Report, GradeConversion, Discipline, GradeSystem
from unittest.mock import patch


class RegistrationViewTest(TestCase):
    """Test user registration endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:register')

    @patch('users.serializers.send_verification_email')
    def test_register_success(self, mock_send_email):
        """Test successful registration"""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'New User',
            'home_location': 'Boulder, CO'
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('message', response.data)

        # Verify user created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.display_name, 'New User')
        self.assertFalse(user.email_verified)

        # Verify email sent
        mock_send_email.assert_called_once()

    def test_register_missing_email(self):
        """Test registration with missing email"""
        data = {
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'New User',
            'home_location': 'Boulder, CO'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_display_name(self):
        """Test registration with short display_name"""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'AB',  # Too short
            'home_location': 'Boulder, CO'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(TestCase):
    """Test login endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:login')
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO',
            email_verified=True
        )

    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('user', response.data)
        self.assertIn('refresh_token', response.cookies)

    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unverified_email(self):
        """Test login with unverified email"""
        unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='password123',
            display_name='Unverified User',
            home_location='Denver, CO',
            email_verified=False
        )

        data = {
            'email': 'unverified@example.com',
            'password': 'password123'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_case_insensitive_email(self):
        """Test login with uppercase email"""
        data = {
            'email': 'TEST@EXAMPLE.COM',
            'password': 'password123'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileViewTest(TestCase):
    """Test profile view and update"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO',
            email_verified=True
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('users:current_user')

    def test_get_profile(self):
        """Test getting current user profile"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['display_name'], 'Test User')

    def test_update_profile(self):
        """Test updating profile"""
        data = {
            'display_name': 'Updated Name',
            'bio': 'New bio text',
            'home_location': 'Denver, CO'
        }
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, 'Updated Name')
        self.assertEqual(self.user.bio, 'New bio text')

    def test_update_profile_unauthenticated(self):
        """Test updating profile without authentication"""
        self.client.force_authenticate(user=None)
        data = {'display_name': 'Hacker'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_visible(self):
        """Test updating profile_visible field"""
        data = {'profile_visible': False}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_visible)

        # Set it back to True
        data = {'profile_visible': True}
        response = self.client.patch(self.url, data, format='json')
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_visible)

    def test_update_weight_kg_with_valid_value(self):
        """Test updating weight_kg with valid value"""
        data = {'weight_kg': 70}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.weight_kg, 70)

    def test_update_weight_kg_boundary_values(self):
        """Test updating weight_kg with boundary values"""
        # Minimum valid (30kg)
        data = {'weight_kg': 30}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.weight_kg, 30)

        # Maximum valid (200kg)
        data = {'weight_kg': 200}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.weight_kg, 200)

    def test_update_weight_kg_invalid_too_low(self):
        """Test updating weight_kg with value too low fails"""
        data = {'weight_kg': 29}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_weight_kg_invalid_too_high(self):
        """Test updating weight_kg with value too high fails"""
        data = {'weight_kg': 201}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_risk_tolerance_with_valid_choice(self):
        """Test updating risk_tolerance with valid choice"""
        data = {'risk_tolerance': 'aggressive'}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.risk_tolerance, 'aggressive')

    def test_update_risk_tolerance_all_valid_choices(self):
        """Test all valid risk_tolerance choices"""
        valid_choices = ['conservative', 'balanced', 'aggressive']

        for choice in valid_choices:
            data = {'risk_tolerance': choice}
            response = self.client.patch(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.user.refresh_from_db()
            self.assertEqual(self.user.risk_tolerance, choice)

    def test_update_risk_tolerance_invalid_choice(self):
        """Test updating risk_tolerance with invalid choice fails"""
        data = {'risk_tolerance': 'invalid_choice'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_preferred_grade_system_with_valid_choice(self):
        """Test updating preferred_grade_system with valid choice"""
        data = {'preferred_grade_system': 'french'}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_grade_system, 'french')

    def test_update_preferred_grade_system_all_valid_choices(self):
        """Test all valid preferred_grade_system choices"""
        valid_choices = ['yds', 'french', 'v_scale']

        for choice in valid_choices:
            data = {'preferred_grade_system': choice}
            response = self.client.patch(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.user.refresh_from_db()
            self.assertEqual(self.user.preferred_grade_system, choice)

    def test_update_preferred_grade_system_invalid_choice(self):
        """Test updating preferred_grade_system with invalid choice fails"""
        data = {'preferred_grade_system': 'invalid_system'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_gender_with_valid_choice(self):
        """Test updating gender with valid choice"""
        data = {'gender': 'female'}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.gender, 'female')

    def test_update_gender_all_valid_choices(self):
        """Test all valid gender choices"""
        valid_choices = ['male', 'female', 'non_binary', 'prefer_not_to_say']

        for choice in valid_choices:
            data = {'gender': choice}
            response = self.client.patch(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.user.refresh_from_db()
            self.assertEqual(self.user.gender, choice)

    def test_update_gender_invalid_choice(self):
        """Test updating gender with invalid choice fails"""
        data = {'gender': 'invalid_gender'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_preferred_partner_gender_with_valid_choice(self):
        """Test updating preferred_partner_gender with valid choice"""
        data = {'preferred_partner_gender': 'female_only'}
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_partner_gender, 'female_only')

    def test_update_preferred_partner_gender_all_valid_choices(self):
        """Test all valid preferred_partner_gender choices"""
        valid_choices = ['no_preference', 'male_only', 'female_only', 'non_binary_only']

        for choice in valid_choices:
            data = {'preferred_partner_gender': choice}
            response = self.client.patch(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.user.refresh_from_db()
            self.assertEqual(self.user.preferred_partner_gender, choice)

    def test_update_preferred_partner_gender_invalid_choice(self):
        """Test updating preferred_partner_gender with invalid choice fails"""
        data = {'preferred_partner_gender': 'invalid_preference'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_profile_returns_all_fields(self):
        """Test getting profile returns all user fields including new ones"""
        # Set some values first
        self.user.risk_tolerance = 'balanced'
        self.user.preferred_grade_system = 'yds'
        self.user.weight_kg = 75
        self.user.gender = 'male'
        self.user.preferred_partner_gender = 'no_preference'
        self.user.profile_visible = True
        self.user.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all new fields are returned
        self.assertIn('risk_tolerance', response.data)
        self.assertIn('preferred_grade_system', response.data)
        self.assertIn('weight_kg', response.data)
        self.assertIn('gender', response.data)
        self.assertIn('preferred_partner_gender', response.data)
        self.assertIn('profile_visible', response.data)

        # Verify values
        self.assertEqual(response.data['risk_tolerance'], 'balanced')
        self.assertEqual(response.data['preferred_grade_system'], 'yds')
        self.assertEqual(response.data['weight_kg'], 75)
        self.assertEqual(response.data['gender'], 'male')
        self.assertEqual(response.data['preferred_partner_gender'], 'no_preference')
        self.assertTrue(response.data['profile_visible'])


class ChangePasswordViewTest(TestCase):
    """Test password change endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpass123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('users:change_password')

    def test_change_password_success(self):
        """Test successful password change"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        data = {
            'old_password': 'wrongold123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DisciplineProfileViewTest(TestCase):
    """Test discipline profile endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('users:manage_disciplines')

        # Create grade conversions
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=60,
            yds_grade='5.10d',
            french_grade='6b'
        )

    def test_create_discipline_profile(self):
        """Test creating a discipline profile"""
        data = {
            'discipline': Discipline.SPORT,
            'grade_system': GradeSystem.YDS,
            'comfortable_grade_min_display': '5.10a',
            'comfortable_grade_max_display': '5.10d',
            'can_lead': True,
            'can_belay': True
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DisciplineProfile.objects.filter(user=self.user).count(), 1)

    def test_list_discipline_profiles(self):
        """Test listing user's discipline profiles"""
        DisciplineProfile.objects.create(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class BlockUserViewTest(TestCase):
    """Test block/unblock endpoints"""

    def setUp(self):
        self.client = APIClient()
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
        self.client.force_authenticate(user=self.user1)

    def test_block_user_success(self):
        """Test blocking a user"""
        url = reverse('users:block_user', kwargs={'user_id': str(self.user2.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Block.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_block_self_rejected(self):
        """Test cannot block yourself"""
        url = reverse('users:block_user', kwargs={'user_id': str(self.user1.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_block_nonexistent_user(self):
        """Test blocking nonexistent user"""
        url = reverse('users:block_user', kwargs={'user_id': '00000000-0000-0000-0000-000000000000'})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unblock_user_success(self):
        """Test unblocking a user"""
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        url = reverse('users:block_user', kwargs={'user_id': str(self.user2.id)})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Block.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_unblock_not_blocked_user(self):
        """Test unblocking user that isn't blocked"""
        url = reverse('users:block_user', kwargs={'user_id': str(self.user2.id)})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_cancels_pending_sessions(self):
        """Test blocking cancels pending sessions"""
        from trips.models import Trip, Destination
        from climbing_sessions.models import Session
        from datetime import date, timedelta

        # Create destination
        destination = Destination.objects.create(
            slug='red-river-gorge',
            name='Red River Gorge, KY',
            country='USA',
            lat=37.7,
            lng=-83.6
        )

        # Create trip
        trip = Trip.objects.create(
            user=self.user1,
            destination=destination,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )

        # Create session
        session = Session.objects.create(
            inviter=self.user1,
            invitee=self.user2,
            trip=trip,
            proposed_date=date.today(),
            time_block='morning',
            status='pending'
        )

        # Block user
        url = reverse('users:block_user', kwargs={'user_id': str(self.user2.id)})
        self.client.post(url)

        # Verify session cancelled
        session.refresh_from_db()
        self.assertEqual(session.status, 'cancelled')


class ReportUserViewTest(TestCase):
    """Test report user endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.reporter = User.objects.create_user(
            email='reporter@example.com',
            password='password123',
            display_name='Reporter',
            home_location='Boulder, CO'
        )
        self.reported = User.objects.create_user(
            email='reported@example.com',
            password='password123',
            display_name='Reported',
            home_location='Denver, CO'
        )
        self.client.force_authenticate(user=self.reporter)

    @patch('users.views.mail_admins')
    def test_report_user_success(self, mock_mail):
        """Test reporting a user"""
        url = reverse('users:report_user', kwargs={'user_id': str(self.reported.id)})
        data = {
            'reason': 'harassment',
            'details': 'User was harassing me during our climb'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Report.objects.filter(
            reporter=self.reporter,
            reported=self.reported
        ).exists())

        # Verify admin email sent
        mock_mail.assert_called_once()

    def test_report_self_rejected(self):
        """Test cannot report yourself"""
        url = reverse('users:report_user', kwargs={'user_id': str(self.reporter.id)})
        data = {
            'reason': 'harassment',
            'details': 'Reporting myself'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_requires_details(self):
        """Test report requires details"""
        url = reverse('users:report_user', kwargs={'user_id': str(self.reported.id)})
        data = {
            'reason': 'harassment',
            'details': 'Too short'  # Less than 10 chars
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_my_reports(self):
        """Test listing user's reports"""
        Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='harassment',
            details='Test harassment report'
        )

        url = reverse('users:list_my_reports')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)


class ListBlockedUsersViewTest(TestCase):
    """Test list blocked users endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            display_name='User',
            home_location='Boulder, CO'
        )
        self.blocked1 = User.objects.create_user(
            email='blocked1@example.com',
            password='password123',
            display_name='Blocked 1',
            home_location='Denver, CO'
        )
        self.blocked2 = User.objects.create_user(
            email='blocked2@example.com',
            password='password123',
            display_name='Blocked 2',
            home_location='Austin, TX'
        )
        self.client.force_authenticate(user=self.user)

        Block.objects.create(blocker=self.user, blocked=self.blocked1)
        Block.objects.create(blocker=self.user, blocked=self.blocked2)

    def test_list_blocked_users(self):
        """Test listing blocked users"""
        url = reverse('users:list_blocked_users')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


class PasswordResetAPITestCase(TestCase):
    """Test password reset API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpassword123',
            display_name='Test User',
            home_location='Boulder, CO',
            email_verified=True
        )

    @patch('users.utils.send_password_reset_email')
    def test_password_reset_request_with_valid_email(self, mock_send_email):
        """Test requesting password reset with valid email sends email"""
        url = reverse('users:password_reset_request')
        data = {'email': 'test@example.com'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        mock_send_email.assert_called_once()

    @patch('users.utils.send_password_reset_email')
    def test_password_reset_request_with_invalid_email(self, mock_send_email):
        """Test requesting password reset with invalid email still returns success"""
        url = reverse('users:password_reset_request')
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(url, data, format='json')

        # Should still return success to prevent email enumeration
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        # Email should not be sent
        mock_send_email.assert_not_called()

    @patch('users.utils.send_password_reset_email')
    def test_password_reset_request_case_insensitive(self, mock_send_email):
        """Test password reset request is case-insensitive for email"""
        url = reverse('users:password_reset_request')
        data = {'email': 'TEST@EXAMPLE.COM'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()

    @patch('users.utils.send_password_reset_email')
    def test_password_reset_request_returns_same_message(self, mock_send_email):
        """Test password reset always returns same message (security)"""
        url = reverse('users:password_reset_request')

        # Valid email
        response1 = self.client.post(url, {'email': 'test@example.com'}, format='json')
        message1 = response1.data.get('message')

        # Invalid email
        response2 = self.client.post(url, {'email': 'fake@example.com'}, format='json')
        message2 = response2.data.get('message')

        # Messages should be identical
        self.assertEqual(message1, message2)
        self.assertEqual(response1.status_code, response2.status_code)

    def test_password_reset_validate_with_valid_token(self):
        """Test validating password reset token with valid uid and token"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_validate')
        response = self.client.get(url, {'uid': uid, 'token': token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_password_reset_validate_with_invalid_uid(self):
        """Test validating with invalid uid returns valid: false"""
        url = reverse('users:password_reset_validate')
        response = self.client.get(url, {'uid': 'invalid', 'token': 'sometoken'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])

    def test_password_reset_validate_with_invalid_token(self):
        """Test validating with invalid token returns valid: false"""
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_validate')
        response = self.client.get(url, {'uid': uid, 'token': 'invalidtoken'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])

    def test_password_reset_validate_missing_uid(self):
        """Test validating without uid parameter returns 400"""
        url = reverse('users:password_reset_validate')
        response = self.client.get(url, {'token': 'sometoken'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['valid'])

    def test_password_reset_validate_missing_token(self):
        """Test validating without token parameter returns 400"""
        url = reverse('users:password_reset_validate')
        response = self.client.get(url, {'uid': 'someuid'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['valid'])

    def test_password_reset_validate_does_not_consume_token(self):
        """Test validating token multiple times works (doesn't consume)"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_validate')

        # First validation
        response1 = self.client.get(url, {'uid': uid, 'token': token})
        self.assertTrue(response1.data['valid'])

        # Second validation should still work
        response2 = self.client.get(url, {'uid': uid, 'token': token})
        self.assertTrue(response2.data['valid'])

    def test_password_reset_confirm_with_valid_credentials(self):
        """Test confirming password reset with valid uid, token, and password"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Verify password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))

    def test_password_reset_confirm_with_invalid_uid(self):
        """Test confirming with invalid uid fails"""
        url = reverse('users:password_reset_confirm')
        data = {
            'uid': 'invaliduid',
            'token': 'sometoken',
            'password': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_with_invalid_token(self):
        """Test confirming with invalid token fails"""
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': 'invalidtoken',
            'password': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_password_too_short(self):
        """Test confirming with password < 8 chars fails"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'short1'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_password_reset_confirm_password_without_number(self):
        """Test confirming with password without number fails"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'nodigitshere'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_password_reset_confirm_password_without_letter(self):
        """Test confirming with password without letter fails"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': '12345678'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_password_reset_confirm_updates_database(self):
        """Test successful reset actually updates password in database"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        old_password_hash = self.user.password

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'brandnewpass123'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password hash changed
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old_password_hash)
        self.assertTrue(self.user.check_password('brandnewpass123'))

    def test_password_reset_confirm_invalidates_token(self):
        """Test successful reset invalidates the token (cannot reuse)"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse('users:password_reset_confirm')
        data = {
            'uid': uid,
            'token': token,
            'password': 'firstnewpass123'
        }

        # First reset succeeds
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Try to reuse same token (should fail because password changed)
        data['password'] = 'secondnewpass456'
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_allows_login_with_new_password(self):
        """Test successful reset allows login with new password"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        # Reset password
        reset_url = reverse('users:password_reset_confirm')
        reset_data = {
            'uid': uid,
            'token': token,
            'password': 'mynewpassword789'
        }
        response = self.client.post(reset_url, reset_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to login with new password
        login_url = reverse('users:login')
        login_data = {
            'email': 'test@example.com',
            'password': 'mynewpassword789'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)

    def test_password_reset_confirm_missing_required_fields(self):
        """Test confirming without required fields returns 400"""
        url = reverse('users:password_reset_confirm')

        # Missing password
        response1 = self.client.post(url, {'uid': 'someuid', 'token': 'sometoken'}, format='json')
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing token
        response2 = self.client.post(url, {'uid': 'someuid', 'password': 'newpass123'}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
