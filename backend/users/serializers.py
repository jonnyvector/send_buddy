from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, DisciplineProfile, ExperienceTag, Block, Report
import re


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    display_name = serializers.CharField(max_length=100, min_length=3)
    home_location = serializers.CharField(max_length=200)

    def validate_email(self, value):
        # Normalize email to lowercase
        normalized = value.lower()

        # Check uniqueness (case-insensitive)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Email already registered")

        return normalized

    def validate_password(self, value):
        # Must contain at least one letter AND one number
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("Password must contain at least one letter")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            email=validated_data['email'],  # Already normalized to lowercase
            password=password,
            display_name=validated_data['display_name'],
            home_location=validated_data['home_location'],
        )

        # Auto-verify for dev (email verification disabled)
        user.email_verified = True
        user.save(update_fields=['email_verified'])

        # Send verification email (disabled for dev - no email configured)
        # from .utils import send_verification_email
        # send_verification_email(user)

        return user


class DisciplineProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisciplineProfile
        fields = [
            'id', 'discipline', 'grade_system',
            'comfortable_grade_min_display', 'comfortable_grade_max_display',
            'projecting_grade_display', 'years_experience',
            'can_lead', 'can_belay', 'can_build_anchors', 'notes'
        ]


class UserSerializer(serializers.ModelSerializer):
    disciplines = DisciplineProfileSerializer(many=True, read_only=True)
    experience_tags = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name', 'avatar', 'bio',
            'home_location', 'home_lat', 'home_lng',
            'risk_tolerance', 'preferred_grade_system',
            'profile_visible', 'email_verified',
            'gender', 'preferred_partner_gender',
            'weight_kg', 'preferred_weight_difference',
            'disciplines', 'experience_tags', 'created_at'
        ]
        read_only_fields = ['id', 'email', 'email_verified', 'created_at']

    def get_experience_tags(self, obj):
        # Return list of tag slugs (not string representation)
        return [tag.tag.slug for tag in obj.experience_tags.all()]


class PublicUserSerializer(serializers.ModelSerializer):
    """Public profile view - excludes private information like email"""
    disciplines = DisciplineProfileSerializer(many=True, read_only=True)
    experience_tags = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'display_name', 'avatar', 'bio',
            'home_location',
            'risk_tolerance', 'preferred_grade_system',
            'gender',
            'disciplines', 'experience_tags', 'created_at'
        ]
        read_only_fields = fields

    def get_experience_tags(self, obj):
        # Return list of tag slugs
        return [tag.tag.slug for tag in obj.experience_tags.all()]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Separate serializer for profile updates (excludes sensitive fields)"""

    class Meta:
        model = User
        fields = [
            'display_name', 'bio', 'home_location', 'home_lat', 'home_lng',
            'risk_tolerance', 'preferred_grade_system', 'profile_visible',
            'gender', 'preferred_partner_gender',
            'weight_kg', 'preferred_weight_difference'
        ]

    def validate_weight_kg(self, value):
        if value is not None and (value < 30 or value > 200):
            raise serializers.ValidationError("Weight must be between 30 and 200 kg")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate_new_password(self, value):
        # Must contain at least one letter AND one number
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("Password must contain at least one letter")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Passwords don't match"})
        return data


class DisciplineProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating discipline profiles"""

    class Meta:
        model = DisciplineProfile
        fields = [
            'discipline', 'grade_system',
            'comfortable_grade_min_display', 'comfortable_grade_max_display',
            'projecting_grade_display', 'years_experience',
            'can_lead', 'can_belay', 'can_build_anchors', 'notes'
        ]

    def validate(self, data):
        # Ensure user doesn't have duplicate discipline profiles
        user = self.context['request'].user
        discipline = data.get('discipline')

        # Check for duplicates (exclude current instance if updating)
        existing = DisciplineProfile.objects.filter(user=user, discipline=discipline)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError({
                'discipline': f'You already have a {discipline} profile'
            })

        return data


class ExperienceTagSerializer(serializers.Serializer):
    """Serializer for adding/removing experience tags"""
    tag = serializers.CharField(required=True)

    def validate_tag(self, value):
        # Verify tag exists
        if not ExperienceTag.objects.filter(slug=value).exists():
            raise serializers.ValidationError(f"Tag '{value}' does not exist")
        return value


class ExperienceTagDetailSerializer(serializers.ModelSerializer):
    """Serializer for listing all available experience tags"""
    class Meta:
        model = ExperienceTag
        fields = ['slug', 'display_name', 'category', 'description']


# Phase 6: Trust & Safety Serializers

class BlockedUserSerializer(serializers.Serializer):
    """Minimal user info for block/report responses"""
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    avatar = serializers.ImageField(required=False, allow_null=True)


class BlockSerializer(serializers.ModelSerializer):
    """Serializer for Block model"""
    blocked_user = BlockedUserSerializer(source='blocked', read_only=True)

    class Meta:
        model = Block
        fields = ['id', 'blocked_user', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for user viewing their own reports"""
    reported_user = BlockedUserSerializer(source='reported', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reported_user', 'reason', 'details',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class CreateReportSerializer(serializers.Serializer):
    """Serializer for creating reports"""
    reason = serializers.ChoiceField(choices=Report.REASON_CHOICES)
    details = serializers.CharField(min_length=10, max_length=2000)
    session_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_session_id(self, value):
        """Validate session exists if provided"""
        if value:
            from climbing_sessions.models import Session
            if not Session.objects.filter(id=value).exists():
                raise serializers.ValidationError("Session not found")
        return value


class AdminReportSerializer(serializers.ModelSerializer):
    """Serializer for admin viewing all reports"""
    reporter = BlockedUserSerializer(read_only=True)
    reported = BlockedUserSerializer(read_only=True)
    session = serializers.SerializerMethodField()
    total_reports_against_user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reported', 'reason', 'details',
            'status', 'admin_notes', 'session',
            'created_at', 'updated_at', 'total_reports_against_user'
        ]

    def get_session(self, obj):
        """Get session info if report was about a session"""
        # Future: add session FK to Report model
        return None

    def get_total_reports_against_user(self, obj):
        """Count total reports against this user"""
        return Report.objects.filter(reported=obj.reported).count()


class UpdateReportSerializer(serializers.ModelSerializer):
    """Serializer for admin updating reports"""

    class Meta:
        model = Report
        fields = ['status', 'admin_notes']

    def validate_status(self, value):
        """Ensure status is valid choice"""
        valid_statuses = [choice[0] for choice in Report.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value
