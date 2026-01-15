"""Grade conversion utilities"""
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
    from .models import GradeConversion

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
    from .models import GradeConversion

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


# Email utilities for authentication

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings


def send_templated_email(subject, template_name, context, recipient_list):
    """
    Send an email using HTML and plain text templates.

    Args:
        subject: Email subject line
        template_name: Base template name (without .html/.txt extension)
        context: Dictionary of template context variables
        recipient_list: List of recipient email addresses
    """
    # Render both HTML and plain text versions
    html_content = render_to_string(f'emails/{template_name}.html', context)
    text_content = render_to_string(f'emails/{template_name}.txt', context)

    # Create email with both versions
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_verification_email(user):
    """Send email verification link with uid + token"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    verification_url = f"{settings.FRONTEND_URL}/verify-email?uid={uid}&token={token}"

    context = {
        'user': user,
        'verification_url': verification_url,
    }

    send_templated_email(
        subject='Verify your Send Buddy account',
        template_name='verify_email',
        context=context,
        recipient_list=[user.email]
    )


def send_password_reset_email(user):
    """Send password reset link with uid + token"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    context = {
        'user': user,
        'reset_url': reset_url,
    }

    send_templated_email(
        subject='Reset your Send Buddy password',
        template_name='password_reset',
        context=context,
        recipient_list=[user.email]
    )
