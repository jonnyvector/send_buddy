#!/usr/bin/env python
"""
Quick test script to verify email system is working.

Run with: python test_emails.py

This will test email sending using the console backend.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from users.models import User
from users.utils import send_verification_email, send_password_reset_email
from users.email import (
    send_session_invitation,
    send_session_accepted,
    send_session_cancelled,
    send_session_completed_reminder,
    send_report_confirmation,
    send_report_status_update
)

print("=" * 80)
print("EMAIL SYSTEM TEST")
print("=" * 80)
print()

# Test 1: Verification Email
print("Test 1: Email Verification")
print("-" * 40)
try:
    # Get or create a test user
    user, created = User.objects.get_or_create(
        email='test@sendbuddy.com',
        defaults={
            'display_name': 'Test User',
            'home_location': 'Boulder, CO',
            'email_verified': False
        }
    )

    send_verification_email(user)
    print("✓ Verification email sent successfully")
    print(f"  To: {user.email}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

# Test 2: Password Reset Email
print("Test 2: Password Reset")
print("-" * 40)
try:
    send_password_reset_email(user)
    print("✓ Password reset email sent successfully")
    print(f"  To: {user.email}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

# Test 3: Report Confirmation
print("Test 3: Report Confirmation")
print("-" * 40)
try:
    from users.models import Report

    # Create test users if needed
    reporter, _ = User.objects.get_or_create(
        email='reporter@sendbuddy.com',
        defaults={
            'display_name': 'Reporter',
            'home_location': 'Denver, CO',
        }
    )

    reported, _ = User.objects.get_or_create(
        email='reported@sendbuddy.com',
        defaults={
            'display_name': 'Reported User',
            'home_location': 'Boulder, CO',
        }
    )

    # Create test report
    report = Report.objects.create(
        reporter=reporter,
        reported=reported,
        reason='safety',
        details='Test report for email system',
        status='open'
    )

    send_report_confirmation(report)
    print("✓ Report confirmation email sent successfully")
    print(f"  To: {reporter.email}")
    print(f"  Report ID: {report.id}")

    # Clean up
    report.delete()
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

print("=" * 80)
print("EMAIL TEMPLATES AVAILABLE:")
print("-" * 80)

import os
from pathlib import Path

template_dir = Path(__file__).resolve().parent / 'users' / 'templates' / 'emails'
templates = sorted([f.name for f in template_dir.iterdir() if f.is_file()])

for template in templates:
    print(f"  • {template}")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print()
print("Check the console output above for email content.")
print("In development, emails are printed to the terminal.")
print()
print("To configure SMTP for production:")
print("  1. Update .env with email provider settings")
print("  2. See docs/EMAIL_SYSTEM.md for details")
print()
