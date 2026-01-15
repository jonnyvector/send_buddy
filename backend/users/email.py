"""
Email notification functions for Send Buddy.

This module handles all email notifications for sessions, reports, and other user interactions.
"""

from django.conf import settings
from .utils import send_templated_email


# ============================================================================
# SESSION EMAILS
# ============================================================================

def send_session_invitation(session):
    """
    Send invitation email to invitee when a new session is created.

    Args:
        session: Session instance
    """
    inviter = session.inviter
    invitee = session.invitee

    # Build URLs
    session_url = f"{settings.FRONTEND_URL}/sessions/{session.id}"
    accept_url = f"{settings.FRONTEND_URL}/sessions/{session.id}/accept"
    decline_url = f"{settings.FRONTEND_URL}/sessions/{session.id}/decline"

    context = {
        'inviter': inviter,
        'invitee': invitee,
        'session': session,
        'session_url': session_url,
        'accept_url': accept_url,
        'decline_url': decline_url,
    }

    send_templated_email(
        subject=f'Climbing invitation from {inviter.display_name}',
        template_name='session_invitation',
        context=context,
        recipient_list=[invitee.email]
    )


def send_session_accepted(session):
    """
    Send notification to inviter when their invitation is accepted.

    Args:
        session: Session instance
    """
    inviter = session.inviter
    invitee = session.invitee

    session_url = f"{settings.FRONTEND_URL}/sessions/{session.id}"

    context = {
        'inviter': inviter,
        'invitee': invitee,
        'session': session,
        'session_url': session_url,
    }

    send_templated_email(
        subject=f'{invitee.display_name} accepted your climbing invitation!',
        template_name='session_accepted',
        context=context,
        recipient_list=[inviter.email]
    )


def send_session_cancelled(session, canceller, recipient, reason=None):
    """
    Send notification when a session is cancelled.

    Args:
        session: Session instance
        canceller: User who cancelled the session
        recipient: User receiving the notification
        reason: Optional cancellation reason
    """
    browse_url = f"{settings.FRONTEND_URL}/browse"

    context = {
        'session': session,
        'canceller': canceller,
        'recipient': recipient,
        'reason': reason,
        'browse_url': browse_url,
    }

    send_templated_email(
        subject=f'Climbing session cancelled',
        template_name='session_cancelled',
        context=context,
        recipient_list=[recipient.email]
    )


def send_session_completed_reminder(session, user, partner):
    """
    Send reminder to provide feedback after completing a session.

    Args:
        session: Session instance
        user: User receiving the reminder
        partner: The other participant in the session
    """
    feedback_url = f"{settings.FRONTEND_URL}/sessions/{session.id}/feedback"

    context = {
        'session': session,
        'user': user,
        'partner': partner,
        'feedback_url': feedback_url,
    }

    send_templated_email(
        subject=f'How was your climb with {partner.display_name}?',
        template_name='session_completed_reminder',
        context=context,
        recipient_list=[user.email]
    )


# ============================================================================
# SAFETY & REPORTING EMAILS
# ============================================================================

def send_report_confirmation(report):
    """
    Send confirmation to user when they submit a report.

    Args:
        report: Report instance
    """
    reporter = report.reporter
    report_url = f"{settings.FRONTEND_URL}/reports/{report.id}"

    context = {
        'reporter': reporter,
        'report': report,
        'report_url': report_url,
    }

    send_templated_email(
        subject='Your report has been received',
        template_name='report_confirmation',
        context=context,
        recipient_list=[reporter.email]
    )


def send_report_status_update(report):
    """
    Send notification when a report's status is updated by admin.

    Args:
        report: Report instance
    """
    reporter = report.reporter
    report_url = f"{settings.FRONTEND_URL}/reports/{report.id}"

    context = {
        'reporter': reporter,
        'report': report,
        'report_url': report_url,
    }

    # Subject varies by status
    subject_map = {
        'investigating': 'Update on your report',
        'resolved': 'Your report has been resolved',
        'dismissed': 'Update on your report',
    }
    subject = subject_map.get(report.status, 'Update on your report')

    send_templated_email(
        subject=subject,
        template_name='report_update',
        context=context,
        recipient_list=[reporter.email]
    )


# ============================================================================
# MESSAGE NOTIFICATIONS (Future Enhancement)
# ============================================================================

def send_new_message_notification(message):
    """
    Send notification when a user receives a new message.
    This is a placeholder for future implementation.

    Args:
        message: Message instance
    """
    # TODO: Implement in future phase
    # Could batch messages and send digest emails
    pass
