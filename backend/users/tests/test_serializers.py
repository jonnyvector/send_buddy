from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError
from users.models import User, DisciplineProfile, Block, Report, GradeConversion, Discipline, GradeSystem
from users.serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, DisciplineProfileCreateSerializer,
    BlockSerializer, ReportSerializer
)


class RegisterSerializerTest(TestCase):
    """Test RegisterSerializer"""

    def test_valid_registration(self):
        """Test registering with valid data"""
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'Test User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_password_must_contain_letter_and_number(self):
        """Test password must have at least one letter and one number"""
        data = {
            'email': 'test@example.com',
            'password': 'onlyletters',
            'password_confirm': 'onlyletters',
            'display_name': 'Test User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

        data['password'] = '12345678'
        data['password_confirm'] = '12345678'
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_password_min_length(self):
        """Test password must be at least 8 characters"""
        data = {
            'email': 'test@example.com',
            'password': 'pass1',
            'password_confirm': 'pass1',
            'display_name': 'Test User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_passwords_must_match(self):
        """Test password confirmation must match"""
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'password_confirm': 'different456',
            'display_name': 'Test User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)

    def test_email_normalized_to_lowercase(self):
        """Test email is normalized to lowercase"""
        data = {
            'email': 'Test@EXAMPLE.COM',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'Test User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], 'test@example.com')

    def test_duplicate_email_rejected(self):
        """Test cannot register with existing email"""
        User.objects.create_user(
            email='existing@example.com',
            password='password123',
            display_name='Existing User',
            home_location='Denver, CO'
        )

        data = {
            'email': 'existing@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'New User',
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_display_name_min_length(self):
        """Test display_name must be at least 3 characters"""
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'display_name': 'AB',  # Too short
            'home_location': 'Boulder, CO'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('display_name', serializer.errors)


class UserSerializerTest(TestCase):
    """Test UserSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )

    def test_serialize_user(self):
        """Test serializing user data"""
        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['display_name'], 'Test User')
        self.assertEqual(data['home_location'], 'Boulder, CO')
        self.assertFalse(data['email_verified'])
        self.assertIn('id', data)
        self.assertIn('created_at', data)

    def test_email_read_only(self):
        """Test email cannot be updated via serializer"""
        self.assertIn('email', UserSerializer.Meta.read_only_fields)

    def test_email_verified_read_only(self):
        """Test email_verified cannot be updated via serializer"""
        self.assertIn('email_verified', UserSerializer.Meta.read_only_fields)


class UserUpdateSerializerTest(TestCase):
    """Test UserUpdateSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )

    def test_update_profile(self):
        """Test updating user profile"""
        data = {
            'display_name': 'Updated Name',
            'bio': 'New bio',
            'home_location': 'Denver, CO'
        }
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_user = serializer.save()
        self.assertEqual(updated_user.display_name, 'Updated Name')
        self.assertEqual(updated_user.bio, 'New bio')
        self.assertEqual(updated_user.home_location, 'Denver, CO')

    def test_weight_validation(self):
        """Test weight must be between 30-200 kg"""
        # Too low
        data = {'weight_kg': 25}
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('weight_kg', serializer.errors)

        # Too high
        data = {'weight_kg': 250}
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('weight_kg', serializer.errors)

        # Valid
        data = {'weight_kg': 70}
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())


class ChangePasswordSerializerTest(TestCase):
    """Test ChangePasswordSerializer"""

    def test_valid_password_change(self):
        """Test valid password change data"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        serializer = ChangePasswordSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_new_password_validation(self):
        """Test new password must contain letter and number"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'onlyletters',
            'new_password_confirm': 'onlyletters'
        }
        serializer = ChangePasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('new_password', serializer.errors)

    def test_new_passwords_must_match(self):
        """Test new password confirmation must match"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'different789'
        }
        serializer = ChangePasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('new_password_confirm', serializer.errors)


class DisciplineProfileCreateSerializerTest(TestCase):
    """Test DisciplineProfileCreateSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )

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

        # Create mock request
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/')
        self.request.user = self.user

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
        serializer = DisciplineProfileCreateSerializer(
            data=data,
            context={'request': self.request}
        )
        self.assertTrue(serializer.is_valid())

    def test_duplicate_discipline_rejected(self):
        """Test cannot create duplicate discipline profile"""
        # Create first profile
        DisciplineProfile.objects.create(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        # Try to create duplicate
        data = {
            'discipline': Discipline.SPORT,
            'grade_system': GradeSystem.YDS,
            'comfortable_grade_min_display': '5.10a',
            'comfortable_grade_max_display': '5.10d'
        }
        serializer = DisciplineProfileCreateSerializer(
            data=data,
            context={'request': self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('discipline', serializer.errors)


class BlockSerializerTest(TestCase):
    """Test BlockSerializer"""

    def setUp(self):
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
        self.block = Block.objects.create(
            blocker=self.user1,
            blocked=self.user2
        )

    def test_serialize_block(self):
        """Test serializing block data"""
        serializer = BlockSerializer(self.block)
        data = serializer.data

        self.assertIn('blocked_user', data)
        self.assertEqual(data['blocked_user']['id'], str(self.user2.id))
        self.assertEqual(data['blocked_user']['display_name'], 'User 2')
        self.assertIn('created_at', data)


class ReportSerializerTest(TestCase):
    """Test ReportSerializer"""

    def setUp(self):
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
        self.report = Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='harassment',
            details='Test harassment details'
        )

    def test_serialize_report(self):
        """Test serializing report data"""
        serializer = ReportSerializer(self.report)
        data = serializer.data

        self.assertIn('reported_user', data)
        self.assertEqual(data['reported_user']['id'], str(self.reported.id))
        self.assertEqual(data['reason'], 'harassment')
        self.assertEqual(data['details'], 'Test harassment details')
        self.assertEqual(data['status'], 'open')
        self.assertIn('created_at', data)

    def test_status_read_only(self):
        """Test status is read-only for users"""
        self.assertIn('status', ReportSerializer.Meta.read_only_fields)
