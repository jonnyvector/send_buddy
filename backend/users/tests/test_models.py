from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from users.models import (
    User, DisciplineProfile, Block, Report, GradeConversion,
    Discipline, GradeSystem, RiskTolerance, Gender
)


class UserModelTest(TestCase):
    """Test User model"""

    def setUp(self):
        """Create test grade conversions"""
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

    def test_create_user(self):
        """Test creating a user with required fields"""
        user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.display_name, 'Test User')
        self.assertFalse(user.email_verified)
        self.assertTrue(user.check_password('password123'))

    def test_email_unique(self):
        """Test email must be unique"""
        User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO'
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',
                password='different123',
                display_name='User 2',
                home_location='Denver, CO'
            )

    def test_email_verified_default_false(self):
        """Test email_verified defaults to False"""
        user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.assertFalse(user.email_verified)

    def test_profile_visible_default_true(self):
        """Test profile_visible defaults to True"""
        user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.assertTrue(user.profile_visible)

    def test_risk_tolerance_default(self):
        """Test risk_tolerance defaults to balanced"""
        user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )
        self.assertEqual(user.risk_tolerance, RiskTolerance.BALANCED)

    def test_user_queryset_visible_to(self):
        """Test visible_to queryset method excludes blocks"""
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO'
        )
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO'
        )
        user3 = User.objects.create_user(
            email='user3@example.com',
            password='password123',
            display_name='User 3',
            home_location='Austin, TX',
            profile_visible=False
        )

        # user1 blocks user2
        Block.objects.create(blocker=user1, blocked=user2)

        # Visible users to user1 should exclude user2 (blocked) and user3 (not visible)
        visible = User.objects.visible_to(user1)
        self.assertIn(user1, visible)
        self.assertNotIn(user2, visible)
        self.assertNotIn(user3, visible)

    def test_user_queryset_bilateral_blocking(self):
        """Test visible_to excludes bilateral blocks"""
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            display_name='User 1',
            home_location='Boulder, CO'
        )
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            display_name='User 2',
            home_location='Denver, CO'
        )

        # user2 blocks user1
        Block.objects.create(blocker=user2, blocked=user1)

        # user1 should not see user2 (who blocked them)
        visible = User.objects.visible_to(user1)
        self.assertNotIn(user2, visible)


class DisciplineProfileModelTest(TestCase):
    """Test DisciplineProfile model"""

    def setUp(self):
        """Create test user and grade conversions"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            display_name='Test User',
            home_location='Boulder, CO'
        )

        # Create grade conversions for testing
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
        GradeConversion.objects.create(
            discipline=Discipline.BOULDERING,
            score=50,
            v_scale_grade='V3'
        )

    def test_grade_conversion_on_save(self):
        """Test grade scores are automatically computed on save"""
        profile = DisciplineProfile(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d'
        )
        profile.save()

        self.assertEqual(profile.comfortable_grade_min_score, 50)
        self.assertEqual(profile.comfortable_grade_max_score, 60)

    def test_validate_bouldering_must_use_v_scale(self):
        """Test bouldering discipline must use V-Scale"""
        profile = DisciplineProfile(
            user=self.user,
            discipline=Discipline.BOULDERING,
            grade_system=GradeSystem.YDS,  # Invalid
            comfortable_grade_min_display='V2',
            comfortable_grade_max_display='V4'
        )
        # Should raise ValueError during grade conversion (before validation)
        with self.assertRaises((ValidationError, ValueError)):
            profile.save()

    def test_validate_sport_cannot_use_v_scale(self):
        """Test sport climbing cannot use V-Scale"""
        profile = DisciplineProfile(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.V_SCALE,  # Invalid
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d'
        )
        # Should raise ValueError during grade conversion (before validation)
        with self.assertRaises((ValidationError, ValueError)):
            profile.save()

    def test_validate_min_max_grade_order(self):
        """Test max grade must be >= min grade"""
        # This will fail because 5.10d (60) is mapped before 5.10a (50)
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=40,
            yds_grade='5.9',
            french_grade='5c'
        )

        profile = DisciplineProfile(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10d',  # 60
            comfortable_grade_max_display='5.9'     # 40
        )
        with self.assertRaises(ValidationError) as context:
            profile.save()
        self.assertIn('Maximum grade must be >= minimum grade', str(context.exception))

    def test_unique_user_discipline_profile(self):
        """Test user can only have one profile per discipline"""
        DisciplineProfile.objects.create(
            user=self.user,
            discipline=Discipline.SPORT,
            grade_system=GradeSystem.YDS,
            comfortable_grade_min_display='5.10a',
            comfortable_grade_max_display='5.10d',
            comfortable_grade_min_score=50,
            comfortable_grade_max_score=60
        )

        # Try to create duplicate - will raise ValidationError from full_clean() in save()
        with self.assertRaises((IntegrityError, ValidationError)):
            DisciplineProfile.objects.create(
                user=self.user,
                discipline=Discipline.SPORT,
                grade_system=GradeSystem.FRENCH,
                comfortable_grade_min_display='6a',
                comfortable_grade_max_display='6b',
                comfortable_grade_min_score=50,
                comfortable_grade_max_score=60
            )


class BlockModelTest(TestCase):
    """Test Block model"""

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

    def test_create_block(self):
        """Test creating a block"""
        block = Block.objects.create(
            blocker=self.user1,
            blocked=self.user2,
            reason='Test reason'
        )
        self.assertEqual(block.blocker, self.user1)
        self.assertEqual(block.blocked, self.user2)
        self.assertEqual(block.reason, 'Test reason')

    def test_block_unique_constraint(self):
        """Test cannot block same user twice"""
        Block.objects.create(blocker=self.user1, blocked=self.user2)

        with self.assertRaises(IntegrityError):
            Block.objects.create(blocker=self.user1, blocked=self.user2)

    def test_bilateral_blocking_allowed(self):
        """Test both users can block each other"""
        Block.objects.create(blocker=self.user1, blocked=self.user2)
        Block.objects.create(blocker=self.user2, blocked=self.user1)

        # Should create successfully
        self.assertEqual(Block.objects.count(), 2)

    def test_cannot_block_self(self):
        """Test user cannot block themselves"""
        # Note: This is enforced by DB constraint, but the constraint
        # might not raise ValidationError in tests depending on DB backend
        with self.assertRaises((ValidationError, IntegrityError)):
            Block.objects.create(blocker=self.user1, blocked=self.user1)


class ReportModelTest(TestCase):
    """Test Report model"""

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

    def test_create_report(self):
        """Test creating a report"""
        report = Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='harassment',
            details='Test details'
        )
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.reported, self.reported)
        self.assertEqual(report.reason, 'harassment')
        self.assertEqual(report.status, 'open')

    def test_report_status_transitions(self):
        """Test report status can be updated"""
        report = Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='harassment',
            details='Test details'
        )

        # Transition to investigating
        report.status = 'investigating'
        report.save()
        self.assertEqual(report.status, 'investigating')

        # Transition to resolved
        report.status = 'resolved'
        report.admin_notes = 'Issue resolved'
        report.save()
        self.assertEqual(report.status, 'resolved')
        self.assertEqual(report.admin_notes, 'Issue resolved')

    def test_multiple_reports_allowed(self):
        """Test user can make multiple reports"""
        Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='harassment',
            details='First report'
        )
        Report.objects.create(
            reporter=self.reporter,
            reported=self.reported,
            reason='spam',
            details='Second report'
        )

        self.assertEqual(Report.objects.filter(reporter=self.reporter).count(), 2)


class GradeConversionModelTest(TestCase):
    """Test GradeConversion model"""

    def test_create_grade_conversion(self):
        """Test creating a grade conversion"""
        conversion = GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )
        self.assertEqual(conversion.discipline, Discipline.SPORT)
        self.assertEqual(conversion.score, 50)
        self.assertEqual(conversion.yds_grade, '5.10a')
        self.assertEqual(conversion.french_grade, '6a')

    def test_unique_discipline_score_constraint(self):
        """Test discipline+score must be unique"""
        GradeConversion.objects.create(
            discipline=Discipline.SPORT,
            score=50,
            yds_grade='5.10a',
            french_grade='6a'
        )

        with self.assertRaises(IntegrityError):
            GradeConversion.objects.create(
                discipline=Discipline.SPORT,
                score=50,  # Duplicate
                yds_grade='5.10b',
                french_grade='6a+'
            )

    def test_bouldering_grade_conversion(self):
        """Test bouldering uses V-scale"""
        conversion = GradeConversion.objects.create(
            discipline=Discipline.BOULDERING,
            score=50,
            v_scale_grade='V3'
        )
        self.assertEqual(conversion.v_scale_grade, 'V3')
        self.assertEqual(conversion.yds_grade, '')
        self.assertEqual(conversion.french_grade, '')
