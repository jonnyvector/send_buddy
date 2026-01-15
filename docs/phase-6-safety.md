# Phase 6: Trust & Safety

## Overview
Implement blocking, reporting, and post-session feedback systems. Critical for user safety and community quality.

## Dependencies
- Phase 1 (Block/Report/Feedback models) ✓
- Phase 2 (Authentication) ✓
- Phase 5 (Sessions) ✓

---

## 1. Safety Philosophy

**Core Principles:**
1. **Blocking is bilateral** — blocked users can never interact
2. **Reports are private** — only visible to admins
3. **Feedback is private in MVP** — no public ratings (prevents gaming)
4. **Low friction** — block/report should be 1-click accessible
5. **No retaliation** — users never know who reported them

---

## 2. Backend API Endpoints

### 2.1 Block User

**POST `/api/users/:user_id/block/`**

Request: (no body required)

Response (201):
```json
{
  "message": "User blocked successfully",
  "blocked_user": {
    "id": "uuid",
    "display_name": "User Name"
  }
}
```

**Error Responses:**
- 400: Cannot block yourself
- 404: User not found
- 429: Rate limit exceeded (10 blocks/hour)

**Validation:**
- Cannot block yourself
- Idempotent (blocking already-blocked user returns 201)

**Side Effects:**
- Create Block record (get_or_create for idempotency)
- Cancel any pending/accepted sessions between the two
- User will be excluded from all future matches (enforced by User.objects.visible_to())

**Rate Limiting:** 10/hour per user

---

### 2.2 Unblock User

**DELETE `/api/users/:user_id/block/`**

Response (200):
```json
{
  "message": "User unblocked successfully"
}
```

**Error Responses:**
- 404: User not blocked
- 429: Rate limit exceeded

**Rate Limiting:** 10/hour per user

---

### 2.3 List Blocked Users

**GET `/api/blocks/`**

Query Parameters:
- `page` (default: 1)
- `page_size` (default: 20, max: 100)

Response (200):
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "blocked_user": {
        "id": "uuid",
        "display_name": "User Name",
        "avatar": "https://..."
      },
      "blocked_at": "2026-01-10T12:00:00Z"
    }
  ]
}
```

**Pagination:** Standard DRF pagination with PageNumberPagination

---

### 2.4 Report User

**POST `/api/users/:user_id/report/`**

Request:
```json
{
  "reason": "harassment",
  "details": "Sent inappropriate messages in session chat.",
  "session_id": "uuid" // optional, provides context
}
```

Response (201):
```json
{
  "message": "Report submitted successfully. Our team will review it.",
  "report_id": "uuid"
}
```

**Error Responses:**
- 400: Invalid data (reason not in choices, details too short, cannot report self)
- 404: User not found or session not found
- 429: Rate limit exceeded (5 reports/hour)

**Validation:**
- reason must be valid choice (harassment, inappropriate, spam, safety, fake, other)
- details required (min 10 chars, max 2000)
- Cannot report yourself
- session_id must exist and involve both users (if provided)

**Side Effects:**
- Create Report record with status='open'
- Trigger admin notification (email/Slack webhook - see section 5.6)

**Rate Limiting:** 5/hour per user

---

### 2.5 List My Reports (User)

**GET `/api/reports/my/`**

Shows reports **made by** current user.

Query Parameters:
- `status` (open, investigating, resolved, dismissed)
- `page` (default: 1)
- `page_size` (default: 20, max: 100)

Response (200):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "reported_user": {
        "id": "uuid",
        "display_name": "User Name"
      },
      "reason": "harassment",
      "details": "...",
      "status": "investigating",
      "created_at": "2026-01-10T12:00:00Z",
      "updated_at": "2026-01-11T14:30:00Z"
    }
  ]
}
```

**Note:** User cannot see reports **about them** (privacy).

**Pagination:** Standard DRF pagination

---

### 2.6 Submit Feedback (Post-Session)

**POST `/api/sessions/:session_id/feedback/`**

Request:
```json
{
  "safety_rating": 5,
  "communication_rating": 4,
  "overall_rating": 5,
  "notes": "Great climbing partner! Very safe and fun."
}
```

Response (201):
```json
{
  "message": "Feedback submitted successfully",
  "feedback_id": "uuid"
}
```

**Error Responses:**
- 400: Invalid ratings, session not completed, duplicate feedback
- 403: Not a participant in this session
- 404: Session not found
- 409: Feedback already submitted for this session
- 429: Rate limit exceeded

**Validation:**
- Session must be 'completed'
- Ratings must be integers 1-5 (validated by model)
- User must be inviter or invitee
- Cannot submit duplicate feedback (enforced by unique_together constraint)

**Privacy:**
- Feedback is **private** in MVP (not shown to ratee)
- Future: aggregate scores may be shown publicly

**Rate Limiting:** 20/hour per user

---

### 2.7 Get My Feedback Statistics (Private)

**GET `/api/feedback/stats/`**

Shows aggregate feedback **received by** current user.

Response (200):
```json
{
  "total_ratings": 12,
  "average_safety": 4.8,
  "average_communication": 4.5,
  "average_overall": 4.7,
  "distribution": {
    "1_stars": 0,
    "2_stars": 0,
    "3_stars": 1,
    "4_stars": 2,
    "5_stars": 9
  }
}
```

**Note:** Distribution keys are consistently named (all plural "stars")

**Future Enhancement:** May show this publicly as "reputation score"

---

## 3. Admin Moderation Endpoints

### 3.1 List All Reports (Admin Only)

**GET `/api/admin/reports/`**

Query params:
- `status` (open, investigating, resolved, dismissed)
- `ordering` (-created_at, created_at, -updated_at, updated_at)
- `page` (default: 1)
- `page_size` (default: 20, max: 100)

Response (200):
```json
{
  "count": 45,
  "next": "http://...",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "reporter": {
        "id": "uuid",
        "display_name": "Reporter Name",
        "email": "reporter@example.com"
      },
      "reported": {
        "id": "uuid",
        "display_name": "Reported User",
        "email": "reported@example.com"
      },
      "reason": "harassment",
      "details": "...",
      "status": "open",
      "admin_notes": "",
      "session": {
        "id": "uuid",
        "proposed_date": "2026-03-16"
      },
      "created_at": "2026-01-10T12:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z",
      "total_reports_against_user": 3
    }
  ]
}
```

**Note:** `total_reports_against_user` shows how many times reported user has been reported in total.

**Pagination:** Standard DRF pagination

---

### 3.2 Update Report Status (Admin Only)

**PATCH `/api/admin/reports/:id/`**

Request:
```json
{
  "status": "resolved",
  "admin_notes": "Warned user. No further action needed."
}
```

Response (200):
```json
{
  "id": "uuid",
  "reporter": { "id": "uuid", "display_name": "..." },
  "reported": { "id": "uuid", "display_name": "..." },
  "reason": "harassment",
  "details": "...",
  "status": "resolved",
  "admin_notes": "Warned user. No further action needed.",
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-11T10:00:00Z"
}
```

**Error Responses:**
- 400: Invalid status value
- 404: Report not found

---

### 3.3 Disable User Account (Admin Only)

**POST `/api/admin/users/:user_id/disable/`**

Request:
```json
{
  "reason": "Multiple harassment reports",
  "duration_days": 30  // null or 0 for permanent
}
```

Response (200):
```json
{
  "message": "User account disabled",
  "user_id": "uuid",
  "disabled_until": "2026-02-10T12:00:00Z"  // null if permanent
}
```

**Error Responses:**
- 400: Invalid duration_days
- 404: User not found

**Side Effects:**
- Set `user.is_active = False`
- Store disable reason and expiration in user model (future: add DisableLog model)
- Cancel all pending/accepted sessions
- User cannot log in until re-enabled

**Note:** In future, add scheduled task to auto-re-enable users after duration expires

---

## 4. Frontend Implementation

### 4.1 Block/Report Actions

**Where to show:**
- User profile page (top right menu)
- Match detail page
- Session chat (top right menu)

**UI:**
- "Block User" button (with confirmation modal)
- "Report User" button (opens report modal)

---

### 4.2 Report Modal

```typescript
interface ReportModalProps {
  reportedUser: User;
  sessionId?: string;  // optional context
  onSubmit: (data: ReportData) => Promise<void>;
  onClose: () => void;
}

// Form fields:
// - Reason (dropdown: harassment, inappropriate, spam, safety, fake, other)
// - Details (textarea, required, min 10 chars)
// - Optional: "Also block this user" checkbox (default checked)
```

**UX:**
- Clear, supportive language
- "Your report is confidential"
- "Thank you for helping keep our community safe"

---

### 4.3 Block Confirmation Modal

```typescript
interface BlockConfirmationProps {
  userToBlock: User;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}

// Warning:
// "Blocking [Name] will:
// - Remove them from your matches
// - Cancel any upcoming sessions
// - Prevent all future interactions
// This action can be undone from Settings."
```

---

### 4.4 Feedback Modal (Post-Session)

```typescript
interface FeedbackModalProps {
  session: Session;
  otherUser: User;
  onSubmit: (feedback: FeedbackData) => Promise<void>;
  onSkip: () => void;
}

// Form fields:
// - Safety (1-5 stars): "How safe did you feel climbing with [Name]?"
// - Communication (1-5 stars): "How was their communication?"
// - Overall (1-5 stars): "Overall experience?"
// - Notes (textarea, optional): "Any additional feedback?"
```

**Trigger:**
- Show modal when user opens app after session date has passed
- Or when user marks session as completed

---

### 4.5 Pages & Routes

#### `/settings/blocked-users` - Blocked Users List
- List of blocked users with unblock buttons
- Empty state: "You haven't blocked anyone"
- Pagination

#### `/settings/reports` - My Reports
- List of reports submitted by user
- Show status updates
- Filter by status
- Pagination

#### `/settings/safety` - Safety Guidelines
- Static page with safety best practices
- "How to stay safe while climbing with strangers"
- Emergency contact info
- Reporting process

---

## 5. Backend Implementation Details

### 5.0 Serializers

```python
# users/serializers.py (add to existing file)

from rest_framework import serializers
from .models import Block, Report

class BlockedUserSerializer(serializers.Serializer):
    """Minimal user info for block responses"""
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
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value
```

```python
# climbing_sessions/serializers.py (add to existing file)

from rest_framework import serializers
from .models import Feedback
from django.db import IntegrityError

class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for creating feedback"""

    class Meta:
        model = Feedback
        fields = [
            'safety_rating', 'communication_rating',
            'overall_rating', 'notes'
        ]

    def validate(self, data):
        """Validate feedback data"""
        session = self.context.get('session')
        user = self.context.get('user')

        if not session:
            raise serializers.ValidationError("Session required")

        # Check session status
        if session.status != 'completed':
            raise serializers.ValidationError(
                "Can only provide feedback for completed sessions"
            )

        # Check for duplicate
        if Feedback.objects.filter(session=session, rater=user).exists():
            raise serializers.ValidationError(
                "Feedback already submitted for this session"
            )

        return data

    def create(self, validated_data):
        """Create feedback with atomic duplicate check"""
        session = self.context['session']
        user = self.context['user']

        # Determine who is being rated
        ratee = session.invitee if user == session.inviter else session.inviter

        try:
            feedback = Feedback.objects.create(
                session=session,
                rater=user,
                ratee=ratee,
                **validated_data
            )
            return feedback
        except IntegrityError:
            raise serializers.ValidationError(
                "Feedback already submitted for this session"
            )


class FeedbackStatsSerializer(serializers.Serializer):
    """Serializer for feedback statistics"""
    total_ratings = serializers.IntegerField()
    average_safety = serializers.FloatField()
    average_communication = serializers.FloatField()
    average_overall = serializers.FloatField()
    distribution = serializers.DictField()
```

---

### 5.1 User Safety Views

```python
# users/views.py (add to existing file)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db.models import Q
from .models import User, Block, Report
from .serializers import (
    BlockSerializer, BlockedUserSerializer, ReportSerializer,
    CreateReportSerializer
)
from climbing_sessions.models import Session


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method='POST')
@never_cache
def block_user(request, user_id):
    """Block a user"""
    # Check rate limit
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        blocked_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if blocked_user == request.user:
        return Response(
            {'error': 'Cannot block yourself'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create block (idempotent with get_or_create)
    block, created = Block.objects.get_or_create(
        blocker=request.user,
        blocked=blocked_user
    )

    # Cancel pending/accepted sessions between users
    Session.objects.filter(
        Q(inviter=request.user, invitee=blocked_user) |
        Q(inviter=blocked_user, invitee=request.user),
        status__in=['pending', 'accepted']
    ).update(status='cancelled')

    return Response({
        'message': 'User blocked successfully',
        'blocked_user': BlockedUserSerializer(blocked_user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method='DELETE')
@never_cache
def unblock_user(request, user_id):
    """Unblock a user"""
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        block = Block.objects.get(
            blocker=request.user,
            blocked_id=user_id
        )
        block.delete()
        return Response(
            {'message': 'User unblocked successfully'},
            status=status.HTTP_200_OK
        )
    except Block.DoesNotExist:
        return Response(
            {'error': 'User not blocked'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def list_blocked_users(request):
    """List users blocked by current user"""
    blocks = Block.objects.filter(
        blocker=request.user
    ).select_related('blocked').order_by('-created_at')

    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.max_page_size = 100
    page = paginator.paginate_queryset(blocks, request)

    serializer = BlockSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/h', method='POST')
@never_cache
def report_user(request, user_id):
    """Report a user"""
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        reported_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if reported_user == request.user:
        return Response(
            {'error': 'Cannot report yourself'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate input
    serializer = CreateReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Validate session context if provided
    session_id = serializer.validated_data.get('session_id')
    if session_id:
        try:
            session = Session.objects.get(id=session_id)
            # Verify both users are participants
            if request.user not in [session.inviter, session.invitee]:
                return Response(
                    {'error': 'You are not a participant in this session'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if reported_user not in [session.inviter, session.invitee]:
                return Response(
                    {'error': 'Reported user is not in this session'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Session.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Create report
    report = Report.objects.create(
        reporter=request.user,
        reported=reported_user,
        reason=serializer.validated_data['reason'],
        details=serializer.validated_data['details'],
        status='open'
    )

    # Send admin notification (implement based on your notification system)
    # Example: send_admin_notification(report)
    # For now, could use Django signals or Celery task
    from django.core.mail import mail_admins
    mail_admins(
        subject=f'New Report: {report.get_reason_display()}',
        message=f'User {request.user.display_name} reported {reported_user.display_name}\n\n'
                f'Reason: {report.get_reason_display()}\n'
                f'Details: {report.details}\n\n'
                f'View in admin: /admin/users/report/{report.id}/',
        fail_silently=True
    )

    return Response({
        'message': 'Report submitted successfully. Our team will review it.',
        'report_id': str(report.id)
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def list_my_reports(request):
    """List reports made by current user"""
    status_filter = request.query_params.get('status')

    queryset = Report.objects.filter(
        reporter=request.user
    ).select_related('reported').order_by('-created_at')

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.max_page_size = 100
    page = paginator.paginate_queryset(queryset, request)

    serializer = ReportSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
```

---

### 5.2 Feedback Views

```python
# climbing_sessions/views.py (add to existing file)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db.models import Avg
from .models import Session, Feedback
from .serializers import FeedbackSerializer, FeedbackStatsSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
@never_cache
def submit_feedback(request, session_id):
    """Submit post-session feedback"""
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        session = Session.objects.select_related(
            'inviter', 'invitee'
        ).get(id=session_id)
    except Session.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    if request.user not in [session.inviter, session.invitee]:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Use serializer for validation and creation
    serializer = FeedbackSerializer(
        data=request.data,
        context={'session': session, 'user': request.user}
    )

    try:
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()

        return Response({
            'message': 'Feedback submitted successfully',
            'feedback_id': str(feedback.id)
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Handle duplicate feedback
        if 'already submitted' in str(e):
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT
            )
        raise


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def feedback_stats(request):
    """Get aggregate feedback stats for current user"""
    feedbacks = Feedback.objects.filter(ratee=request.user)

    if not feedbacks.exists():
        stats_data = {
            'total_ratings': 0,
            'average_safety': 0.0,
            'average_communication': 0.0,
            'average_overall': 0.0,
            'distribution': {
                '1_stars': 0,
                '2_stars': 0,
                '3_stars': 0,
                '4_stars': 0,
                '5_stars': 0
            }
        }
        serializer = FeedbackStatsSerializer(stats_data)
        return Response(serializer.data)

    # Calculate aggregates
    total = feedbacks.count()
    aggregates = feedbacks.aggregate(
        avg_safety=Avg('safety_rating'),
        avg_comm=Avg('communication_rating'),
        avg_overall=Avg('overall_rating')
    )

    # Calculate distribution (consistent naming: all plural)
    distribution = {}
    for i in range(1, 6):
        count = feedbacks.filter(overall_rating=i).count()
        distribution[f'{i}_stars'] = count

    stats_data = {
        'total_ratings': total,
        'average_safety': round(aggregates['avg_safety'], 2),
        'average_communication': round(aggregates['avg_comm'], 2),
        'average_overall': round(aggregates['avg_overall'], 2),
        'distribution': distribution
    }

    serializer = FeedbackStatsSerializer(stats_data)
    return Response(serializer.data)
```

---

### 5.3 Admin Moderation Views

```python
# users/admin_views.py (new file)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from .models import User, Report
from .serializers import AdminReportSerializer, UpdateReportSerializer
from climbing_sessions.models import Session


@api_view(['GET'])
@permission_classes([IsAdminUser])
@never_cache
def list_reports(request):
    """List all reports (admin only)"""
    status_filter = request.query_params.get('status')
    ordering = request.query_params.get('ordering', '-created_at')

    queryset = Report.objects.select_related(
        'reporter', 'reported'
    ).all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Validate and apply ordering
    allowed_ordering = ['created_at', '-created_at', 'updated_at', '-updated_at']
    if ordering in allowed_ordering:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-created_at')

    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.max_page_size = 100
    page = paginator.paginate_queryset(queryset, request)

    serializer = AdminReportSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@never_cache
def update_report(request, report_id):
    """Update report status (admin only)"""
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = UpdateReportSerializer(
        report,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # Return full report data
    response_serializer = AdminReportSerializer(report)
    return Response(response_serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
@never_cache
def disable_user(request, user_id):
    """Disable user account (admin only)"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get duration from request
    duration_days = request.data.get('duration_days')
    reason = request.data.get('reason', 'Admin action')

    # Validate duration
    disabled_until = None
    if duration_days:
        try:
            days = int(duration_days)
            if days > 0:
                disabled_until = timezone.now() + timedelta(days=days)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid duration_days. Must be a positive integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Disable user
    user.is_active = False
    user.save()

    # Future: Store disable info in user model or separate DisableLog table
    # For now, we could add fields to User model:
    # user.disabled_until = disabled_until
    # user.disable_reason = reason
    # user.save()

    # Cancel all pending/accepted sessions
    Session.objects.filter(
        Q(inviter=user) | Q(invitee=user),
        status__in=['pending', 'accepted']
    ).update(status='cancelled')

    return Response({
        'message': 'User account disabled',
        'user_id': str(user.id),
        'disabled_until': disabled_until.isoformat() if disabled_until else None
    }, status=status.HTTP_200_OK)
```

---

### 5.4 URL Configuration

```python
# users/urls.py (add to existing patterns)

from django.urls import path
from . import views, admin_views

urlpatterns = [
    # ... existing patterns ...

    # Blocking
    path('users/<uuid:user_id>/block/', views.block_user, name='block_user'),
    path('users/<uuid:user_id>/block/', views.unblock_user, name='unblock_user'),  # DELETE
    path('blocks/', views.list_blocked_users, name='list_blocked_users'),

    # Reporting
    path('users/<uuid:user_id>/report/', views.report_user, name='report_user'),
    path('reports/my/', views.list_my_reports, name='list_my_reports'),

    # Admin moderation
    path('admin/reports/', admin_views.list_reports, name='admin_list_reports'),
    path('admin/reports/<uuid:report_id>/', admin_views.update_report, name='admin_update_report'),
    path('admin/users/<uuid:user_id>/disable/', admin_views.disable_user, name='admin_disable_user'),
]
```

```python
# climbing_sessions/urls.py (add to existing patterns)

from django.urls import path
from . import views

# Add to existing router patterns:
urlpatterns += [
    path('sessions/<uuid:session_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('feedback/stats/', views.feedback_stats, name='feedback_stats'),
]
```

---

### 5.5 Block Enforcement Implementation

Update existing files to enforce blocking:

```python
# matching/services.py (update _get_candidates method)

def _get_candidates(self):
    """Get all eligible candidate users (excluding blocked users)"""

    # Get IDs of users blocked by me or who blocked me
    blocked_by_me = self.user.blocks_given.values_list('blocked_id', flat=True)
    blocked_me = self.user.blocks_received.values_list('blocker_id', flat=True)
    excluded_ids = set(blocked_by_me) | set(blocked_me) | {self.user.id}

    # Get all users with active trips overlapping my trip's dates
    candidates = User.objects.filter(
        trips__is_active=True,
        trips__start_date__lte=self.trip.end_date,
        trips__end_date__gte=self.trip.start_date,
        email_verified=True,
        profile_visible=True
    ).exclude(
        id__in=excluded_ids
    ).prefetch_related(
        'disciplines', 'experience_tags__tag'
    ).distinct()

    return candidates
```

```python
# climbing_sessions/serializers.py (update CreateSessionSerializer validate method)

def validate(self, data):
    user = self.context['request'].user

    # Check invitee exists
    try:
        invitee = User.objects.get(id=data['invitee_id'])
    except User.DoesNotExist:
        raise serializers.ValidationError({'invitee_id': 'User not found'})

    # Prevent self-invites
    if invitee == user:
        raise serializers.ValidationError("Cannot invite yourself")

    # Check if blocked (Phase 6: Trust & Safety)
    from users.models import Block
    if Block.objects.filter(
        Q(blocker=user, blocked=invitee) | Q(blocker=invitee, blocked=user)
    ).exists():
        raise serializers.ValidationError(
            "Cannot send invitation to this user"
        )

    # ... rest of validation ...

    return data
```

---

### 5.6 Admin Notification System

For production, implement one of these strategies:

**Option 1: Django Signals + Email**
```python
# users/signals.py (new file)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import mail_admins
from .models import Report

@receiver(post_save, sender=Report)
def notify_admins_new_report(sender, instance, created, **kwargs):
    """Send email to admins when new report is created"""
    if created:
        mail_admins(
            subject=f'New Report: {instance.get_reason_display()}',
            message=f'User {instance.reporter.display_name} reported {instance.reported.display_name}\n\n'
                    f'Reason: {instance.get_reason_display()}\n'
                    f'Details: {instance.details}\n\n'
                    f'View in admin: /admin/users/report/{instance.id}/',
            fail_silently=False
        )
```

**Option 2: Celery Task (recommended for production)**
```python
# users/tasks.py (new file)

from celery import shared_task
from django.core.mail import mail_admins
import requests

@shared_task
def notify_admins_report(report_id):
    """Send notification to admins about new report"""
    from .models import Report
    report = Report.objects.select_related('reporter', 'reported').get(id=report_id)

    # Email
    mail_admins(
        subject=f'New Report: {report.get_reason_display()}',
        message=f'User {report.reporter.display_name} reported {report.reported.display_name}\n\n'
                f'Reason: {report.get_reason_display()}\n'
                f'Details: {report.details}',
        fail_silently=True
    )

    # Slack webhook (optional)
    # slack_webhook = settings.SLACK_ADMIN_WEBHOOK
    # if slack_webhook:
    #     requests.post(slack_webhook, json={
    #         'text': f'🚨 New Report: {report.reporter.display_name} → {report.reported.display_name}',
    #         'blocks': [...]
    #     })
```

---

## 6. Implementation Checklist

### Backend
- [ ] Add serializers (BlockSerializer, ReportSerializer, FeedbackSerializer, etc.)
- [ ] Implement block/unblock endpoints with rate limiting
- [ ] Implement list blocked users with pagination
- [ ] Implement report user endpoint with rate limiting
- [ ] Implement list my reports with pagination
- [ ] Implement submit feedback endpoint with duplicate prevention
- [ ] Implement feedback stats endpoint
- [ ] Implement admin report list/update with pagination
- [ ] Implement admin disable user with duration support
- [ ] Add blocking enforcement in match queries (matching/services.py)
- [ ] Add blocking enforcement in session invites (climbing_sessions/serializers.py)
- [ ] Add URL patterns for all endpoints
- [ ] Set up admin notification system (email/Slack)
- [ ] Write unit tests for all endpoints
- [ ] Test rate limiting behavior

### Frontend
- [ ] Build ReportModal component
- [ ] Build BlockConfirmationModal component
- [ ] Build FeedbackModal component
- [ ] Add block/report buttons to user profiles
- [ ] Add block/report to match detail page
- [ ] Add block/report to session chat
- [ ] Build blocked users settings page with pagination
- [ ] Build my reports page with status filters and pagination
- [ ] Build safety guidelines static page
- [ ] Add feedback prompt after completed sessions
- [ ] Handle all error responses (400, 403, 404, 409, 429)

### Testing
- [ ] Test block flow (user disappears from matches)
- [ ] Test blocked user cannot send session invites
- [ ] Test unblock restores functionality
- [ ] Test report submission with/without session context
- [ ] Test report rate limiting
- [ ] Test feedback submission (happy path)
- [ ] Test feedback duplicate prevention (409 response)
- [ ] Test feedback for non-completed session (400 response)
- [ ] Test admin can view all reports
- [ ] Test admin can update report status
- [ ] Test admin can disable user (temporary and permanent)
- [ ] Test disabled user cannot log in
- [ ] Test pagination on all list endpoints
- [ ] Test admin notification delivery

---

## 7. Safety Guidelines Content

Create a static page (`/safety`) with:

### Before Meeting:
- Always verify identity (video call, social media)
- Share your plans with a friend
- Meet in public areas first
- Trust your instincts

### While Climbing:
- Start with easy routes to assess skills
- Communicate clearly about comfort levels
- Use proper safety equipment
- Never feel pressured to climb beyond your limits

### After the Session:
- Provide honest feedback
- Report any concerning behavior

### Red Flags:
- Refuses to use safety equipment
- Pressures you to climb harder grades
- Makes you uncomfortable
- Lacks basic belay skills

### Emergency:
- If you feel unsafe, end the session immediately
- Contact local authorities if necessary
- Report the user in the app

---

## 8. Database Migrations

Run migrations for any model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

**Note:** Block, Report, and Feedback models already exist from Phase 1. No new migrations needed unless adding fields like `disabled_until` to User model.

---

## 9. Estimated Timeline

- Backend serializers: 2 hours
- Backend block/report views: 3 hours
- Backend feedback views: 2 hours
- Admin moderation views: 2 hours
- URL configuration: 0.5 hours
- Block enforcement updates: 1 hour
- Admin notifications: 1 hour
- Frontend modals: 3 hours
- Settings pages: 2 hours
- Safety guidelines page: 1 hour
- Testing: 3 hours
- **Total: ~20 hours**

---

## MVP Complete! 🎉

After Phase 6, the core MVP is **fully functional**:
- ✅ User authentication & profiles
- ✅ Trip management
- ✅ Matchmaking algorithm
- ✅ Session invitations & chat
- ✅ Trust & safety features
- ✅ Blocking & reporting system
- ✅ Post-session feedback
- ✅ Admin moderation tools

---

## Phase 2+ Enhancements

### Trust & Safety
- Public reputation scores (aggregate feedback)
- Verified climber badges (gym verification)
- Reference/vouch system
- Auto-moderation for reported users (auto-disable after N reports)
- Safety tips based on user level
- Permanent disable log table with audit trail

### Notifications
- Push notifications (web + mobile)
- Email digests for admins
- SMS for urgent safety alerts
- Real-time Slack integration for admin reports

### Analytics
- User engagement tracking
- Match quality metrics
- Session completion rates
- Feedback sentiment analysis
- Report trend analysis

### Performance
- Cache feedback stats with Redis
- Denormalize total_reports_against_user field
- Add database indexes on Block (blocker, blocked) and Report (status, created_at)
