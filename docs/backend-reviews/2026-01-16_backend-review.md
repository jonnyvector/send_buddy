# Backend Code Review

**Date:** 2026-01-16
**Reviewer:** backend-reviewer agent

---

## Summary

Comprehensive security and code quality review of the Send Buddy Django backend application. The application is a climbing matchmaking platform with features for user authentication, trip planning, partner matching, and real-time messaging. Overall, the codebase demonstrates good Django practices with proper use of ViewSets, serializers, and authentication. However, several critical security issues and areas for improvement were identified.

## Critical Issues

### 1. Bilateral Blocking Not Properly Enforced in Public Profile Endpoint
**File:** `backend/users/views.py` (Lines 321-349)

The `get_public_profile` function directly fetches users with `User.objects.get(pk=user_id)` instead of using the `User.objects.visible_to(viewer)` manager method.

**Current Code:**
```python
def get_public_profile(request, user_id):
    try:
        user = User.objects.get(pk=user_id)  # ISSUE: Not using visible_to()
    except User.DoesNotExist:
        return Response(...)
```

**Fix Required:**
```python
def get_public_profile(request, user_id):
    try:
        user = User.objects.visible_to(request.user).get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
```

### 2. Matching Service Doesn't Use visible_to() for Candidate Fetching
**File:** `backend/matching/services.py` (Lines 65-86)

The matching service manually excludes blocked users instead of using the `visible_to()` method, creating a parallel implementation that could diverge from the security model.

**Fix Required:**
```python
def _get_candidates(self):
    candidates = User.objects.visible_to(self.user).filter(
        trips__is_active=True,
        trips__start_date__lte=self.trip.end_date,
        trips__end_date__gte=self.trip.start_date,
        email_verified=True
    ).prefetch_related(
        'disciplines', 'experience_tags__tag'
    ).distinct()
```

### 3. Insecure Default SECRET_KEY in Settings
**File:** `backend/config/settings.py` (Line 25)

The default SECRET_KEY contains "insecure" prefix but is hardcoded. This could be accidentally deployed to production.

**Fix Required:**
```python
SECRET_KEY = config('DJANGO_SECRET_KEY')  # Remove default, force env var
```

### 4. Session Creation Doesn't Check Bilateral Blocks
**File:** `backend/climbing_sessions/views.py` (Lines 46-72)

Users can send session invitations to users who have blocked them or whom they've blocked.

**Fix Required:** Add block validation in CreateSessionSerializer:
```python
def validate_invitee(self, value):
    request = self.context.get('request')
    if not User.objects.visible_to(request.user).filter(id=value).exists():
        raise serializers.ValidationError("Cannot send invitation to this user")
    return value
```

## Improvements Required

### 1. Missing Database Indexes
Several frequently queried fields lack indexes:
- `Trip.start_date`, `Trip.end_date` - Used in date range queries
- `User.email_verified`, `User.profile_visible` - Used in filtering
- `Session.status` - Frequently filtered field
- `Block.blocker`, `Block.blocked` - Used in visibility checks

**Fix:** Add database indexes in models:
```python
class Trip(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['user', 'is_active', 'start_date']),
        ]
```

### 2. Missing CSRF and Security Headers Configuration
**File:** `backend/config/settings.py`

Add to settings.py:
```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SAMESITE = 'Strict'
```

### 3. N+1 Query Issues
**File:** `backend/users/views.py` (Lines 732-746)

```python
# Current:
queryset = Report.objects.filter(reporter=request.user).select_related('reported')

# Should be:
queryset = Report.objects.filter(
    reporter=request.user
).select_related('reported', 'reporter')
```

### 4. Inconsistent Error Handling
**File:** `backend/users/views.py` (Line 169)

```python
except Exception:  # Too broad
    return Response({'error': 'Invalid or expired refresh token'})
```

Should catch specific exceptions and log properly.

### 5. File Upload Size Validation Too Late
**File:** `backend/users/views.py` (Lines 354-374)

File size is checked after loading into memory. Use Django's `FILE_UPLOAD_MAX_MEMORY_SIZE` setting and validate in middleware.

## Suggestions

### 1. Add Request ID Tracking
```python
class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.id
        return response
```

### 2. Implement Comprehensive Logging
Add structured logging with context for critical operations.

### 3. Add API Versioning
```python
urlpatterns = [
    path('api/v1/', include('users.urls')),
]
```

### 4. Implement Pagination Consistently
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### 5. Add Database Connection Pooling
```python
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,
        'OPTIONS': {'connect_timeout': 10},
    }
}
```

## Positive Highlights

1. **Well-Structured Apps**: Clean separation of concerns with distinct apps
2. **Good Use of Django Patterns**: Proper use of ViewSets, serializers, and model managers
3. **UUID Primary Keys**: Good security practice
4. **Rate Limiting**: Properly implemented on sensitive endpoints
5. **JWT Authentication**: Well-configured with refresh token rotation
6. **Comprehensive Test Structure**: Good test organization
7. **Grade Normalization System**: Clever implementation
8. **Email Verification Flow**: Properly implemented
9. **WebSocket Support**: Channels properly configured
10. **Custom User Model**: Well-designed with climbing-specific fields

---

**Priority Actions:**
1. Fix all instances where users are fetched without using `visible_to()`
2. Add missing database indexes for performance
3. Configure security headers and CSRF settings
4. Remove default SECRET_KEY
5. Add comprehensive logging for security events
