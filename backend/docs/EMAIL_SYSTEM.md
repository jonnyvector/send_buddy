# Email Notification System

## Overview

Send Buddy's email notification system sends automated emails for user verification, session management, and safety reporting. All emails include both HTML and plain text versions for maximum compatibility.

## Email Types

### 1. Authentication Emails

#### Email Verification
- **Trigger**: User registration
- **Recipient**: New user
- **Template**: `verify_email.html` / `verify_email.txt`
- **Function**: `send_verification_email(user)`
- **Contains**:
  - Welcome message
  - Email verification link (24-hour expiration)
  - What to do next

#### Password Reset
- **Trigger**: User requests password reset
- **Recipient**: User requesting reset
- **Template**: `password_reset.html` / `password_reset.txt`
- **Function**: `send_password_reset_email(user)`
- **Contains**:
  - Password reset link (24-hour expiration)
  - Security notice

### 2. Session Emails

#### Session Invitation
- **Trigger**: User creates session invitation
- **Recipient**: Invitee
- **Template**: `session_invitation.html` / `session_invitation.txt`
- **Function**: `send_session_invitation(session)`
- **Contains**:
  - Inviter information
  - Session details (date, time, location, goal)
  - Trip context
  - Accept/Decline buttons
  - Link to view session and chat

#### Session Accepted
- **Trigger**: Invitee accepts invitation
- **Recipient**: Inviter
- **Template**: `session_accepted.html` / `session_accepted.txt`
- **Function**: `send_session_accepted(session)`
- **Contains**:
  - Confirmation of acceptance
  - Session details
  - Next steps for coordination
  - Link to session chat

#### Session Cancelled
- **Trigger**: Either party cancels session
- **Recipient**: Other party
- **Template**: `session_cancelled.html` / `session_cancelled.txt`
- **Function**: `send_session_cancelled(session, canceller, recipient, reason=None)`
- **Contains**:
  - Cancellation notice
  - Optional reason
  - Link to find other partners

#### Session Completed Reminder
- **Trigger**: Session marked as completed
- **Recipients**: Both participants
- **Template**: `session_completed_reminder.html` / `session_completed_reminder.txt`
- **Function**: `send_session_completed_reminder(session, user, partner)`
- **Contains**:
  - Request for feedback
  - Session details
  - Explanation of feedback system
  - Link to feedback form

### 3. Safety & Reporting Emails

#### Report Confirmation
- **Trigger**: User submits report
- **Recipient**: Reporter
- **Template**: `report_confirmation.html` / `report_confirmation.txt`
- **Function**: `send_report_confirmation(report)`
- **Contains**:
  - Report ID for reference
  - Report details
  - What happens next
  - Timeline expectations
  - Link to view report status

#### Report Status Update
- **Trigger**: Admin changes report status
- **Recipient**: Reporter
- **Template**: `report_update.html` / `report_update.txt`
- **Function**: `send_report_status_update(report)`
- **Contains**:
  - Status change notification
  - Admin notes (if provided)
  - Next steps based on status
  - Link to report details

## Configuration

### Development Setup

By default, emails are printed to the console in development:

```bash
# In terminal where Django is running, you'll see:
# Email output printed with full HTML and text content
```

No additional configuration needed!

### Production Setup

1. **Choose an Email Provider**:
   - SendGrid (recommended)
   - Mailgun
   - AWS SES
   - Gmail (for testing only)

2. **Update .env file**:

```bash
# SendGrid example
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_api_key_here
DEFAULT_FROM_EMAIL=noreply@sendbuddy.com
FRONTEND_URL=https://sendbuddy.com
```

3. **Verify DNS Settings**:
   - Add SPF record
   - Add DKIM record
   - Verify domain with email provider

## Template Structure

### Directory Layout

```
users/templates/emails/
├── base.html                          # Base template with branding
├── verify_email.html                  # HTML version
├── verify_email.txt                   # Plain text version
├── password_reset.html
├── password_reset.txt
├── session_invitation.html
├── session_invitation.txt
├── session_accepted.html
├── session_accepted.txt
├── session_cancelled.html
├── session_cancelled.txt
├── session_completed_reminder.html
├── session_completed_reminder.txt
├── report_confirmation.html
├── report_confirmation.txt
├── report_update.html
└── report_update.txt
```

### Template Features

All HTML email templates include:
- **Responsive design** - Mobile-friendly layouts
- **Send Buddy branding** - Consistent purple gradient theme
- **Clear CTAs** - Prominent action buttons
- **Plain text fallback** - For email clients without HTML support
- **Accessibility** - Proper heading structure and alt text

## Email Functions

### Location

- **Authentication emails**: `/users/utils.py`
- **Session & report emails**: `/users/email.py`

### Usage Examples

```python
# Send verification email
from users.utils import send_verification_email
send_verification_email(user)

# Send session invitation
from users.email import send_session_invitation
send_session_invitation(session)

# Send report confirmation
from users.email import send_report_confirmation
send_report_confirmation(report)
```

### Error Handling

All email functions are wrapped in try-except blocks in views:
- Email failures are logged but don't break the user flow
- Users still see success messages even if email fails
- Admins can monitor email failures in logs

## Integration Points

### User Registration
- **File**: `/users/views.py` - `register()`
- **Email**: Verification email sent after user creation

### Session Management
- **File**: `/climbing_sessions/views.py` - `SessionViewSet`
- **Emails**:
  - `create()` - Invitation email
  - `accept()` - Acceptance email
  - `cancel()` - Cancellation email
  - `complete()` - Feedback reminder emails (both users)

### Safety Reporting
- **Files**: `/users/views.py`, `/users/admin_views.py`
- **Emails**:
  - `report_user()` - Confirmation email
  - `update_report()` - Status update email (when admin changes status)

## Testing

### Console Backend (Development)

1. Start Django server:
```bash
python manage.py runserver
```

2. Trigger an action (e.g., register, create session)

3. Check terminal output for email content:
```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Verify your Send Buddy account
From: noreply@sendbuddy.com
To: user@example.com
Date: Mon, 13 Jan 2026 12:00:00 -0000
Message-ID: <...>

Welcome to Send Buddy, John!
...
```

### SMTP Backend (Production)

1. Configure SMTP settings in `.env`
2. Send test email:
```bash
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
1  # Success!
```

3. Check recipient inbox

## Monitoring

### Email Delivery

- Check email provider dashboard for:
  - Delivery rates
  - Bounce rates
  - Spam complaints
  - Opens and clicks

### Error Logs

```bash
# View Django logs for email errors
tail -f logs/django.log | grep "Failed to send"
```

## Future Enhancements

### Planned Features

1. **Email Preferences**:
   - User settings to control email frequency
   - Opt-out for non-critical emails
   - Digest mode for session invitations

2. **Rich Notifications**:
   - In-app notification system
   - Push notifications for mobile
   - SMS for critical safety alerts

3. **Async Email Sending**:
   - Use Celery or Django-Q for background processing
   - Batch email sending
   - Retry logic for failures

4. **Email Analytics**:
   - Track open rates
   - Track click-through rates
   - A/B testing for subject lines

### Template Improvements

- Multi-language support
- User-customizable templates
- Dark mode support
- Embedded images and branding assets

## Troubleshooting

### Emails Not Sending in Production

1. **Check SMTP credentials**:
   ```bash
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.EMAIL_HOST)
   >>> print(settings.EMAIL_HOST_USER)
   ```

2. **Test SMTP connection**:
   ```bash
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```

3. **Check firewall/security groups**:
   - Ensure port 587 (TLS) or 465 (SSL) is open
   - Check provider's IP whitelist settings

### Emails Going to Spam

1. **Verify DNS records**:
   - SPF: `v=spf1 include:sendgrid.net ~all`
   - DKIM: Get from email provider
   - DMARC: `v=DMARC1; p=none; rua=mailto:admin@sendbuddy.com`

2. **Check content**:
   - Avoid spam trigger words
   - Include unsubscribe link
   - Use authenticated domain

### Template Rendering Issues

1. **Missing context variables**:
   - Check template context in email function
   - Verify all required variables are passed

2. **Template not found**:
   - Ensure templates are in `users/templates/emails/`
   - Check template name matches function call

## Support

For questions or issues with the email system:
- Email: dev@sendbuddy.com
- Docs: Check `/docs/` directory
- Logs: Review Django error logs
