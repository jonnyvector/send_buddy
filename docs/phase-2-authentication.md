# Phase 2: Authentication & User Management

## Overview
Implement user registration, login, email verification, and profile management.

## Dependencies
- Phase 1 (User model) ✓

---

## 1. Backend API Endpoints

### 1.1 Registration

**POST `/api/auth/register/`**

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "display_name": "Alex Climber",
  "home_location": "Boulder, CO, USA"
}
```

Response (201):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "Alex Climber",
    "email_verified": false
  },
  "message": "Registration successful. Please check your email to verify your account."
}
```

**Validation:**
- Email must be unique (case-insensitive check)
- Email normalized to lowercase on save
- Password min 8 chars, must contain at least one letter AND one number
- display_name 3-100 chars
- home_location required

**Rate Limiting:**
- 5 registration attempts per IP per hour

**Side effects:**
- Send verification email with uid + token
- Create User record with `email_verified=False`
- Email normalized to lowercase to prevent duplicate accounts (user@x.com vs User@x.com)

---

### 1.2 Email Verification

**POST `/api/auth/verify-email/`**

Request:
```json
{
  "uid": "base64-encoded-user-id",
  "token": "verification-token-from-email"
}
```

Response (200):
```json
{
  "message": "Email verified successfully. You can now log in."
}
```

Error (400):
```json
{
  "error": "Invalid or expired verification link"
}
```

**Implementation:**
- Use Django's `default_token_generator` (24h expiry, invalidated if password changes)
- Encode user ID with `urlsafe_base64_encode()`
- Validate both uid AND token
- Set `user.email_verified = True` on success
- Token is single-use (checking `email_verified` prevents reuse)

**Rate Limiting:**
- 10 verification attempts per IP per hour

---

### 1.2a Resend Verification Email

**POST `/api/auth/resend-verification/`**

Request:
```json
{
  "email": "user@example.com"
}
```

Response (200):
```json
{
  "message": "If that email is registered and unverified, a new verification link has been sent."
}
```

**Security:**
- Always return 200 (don't leak email existence)
- Only send email if user exists AND `email_verified=False`
- Normalize email to lowercase before lookup

**Rate Limiting:**
- 3 resend attempts per IP per hour

---

### 1.3 Login

**POST `/api/auth/login/`**

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Response (200):
```json
{
  "access": "jwt-access-token",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "Alex Climber",
    "avatar": "url-or-null",
    "email_verified": true
  }
}
```

**Response Headers:**
```
Set-Cookie: refresh_token=<jwt-refresh-token>; HttpOnly; Secure; SameSite=Strict; Path=/api/auth/; Max-Age=604800
```

Error (401):
```json
{
  "error": "Invalid credentials"
}
```

Error (403):
```json
{
  "error": "Please verify your email before logging in"
}
```

**Business Logic:**
- Normalize email to lowercase for lookup
- Check `email_verified = True` before issuing tokens
- Return access token in response body
- Set refresh token in HttpOnly cookie (not accessible to JavaScript)
- Log failed login attempts for security monitoring

**Rate Limiting:**
- 5 login attempts per IP per 15 minutes
- Consider account-level lockout after 10 failed attempts

---

### 1.4 Token Refresh

**POST `/api/auth/token/refresh/`**

Request:
```
No body required - refresh token read from HttpOnly cookie
```

Response (200):
```json
{
  "access": "new-jwt-access-token"
}
```

**Response Headers:**
```
Set-Cookie: refresh_token=<new-jwt-refresh-token>; HttpOnly; Secure; SameSite=Strict; Path=/api/auth/; Max-Age=604800
```

Error (401):
```json
{
  "error": "Invalid or expired refresh token"
}
```

**Implementation:**
- Read refresh token from `refresh_token` cookie (not request body)
- Validate refresh token
- Issue new access token
- Rotate refresh token (issue new one for enhanced security)
- Set new refresh token in HttpOnly cookie

**Security:**
- Refresh token rotation prevents token replay attacks
- HttpOnly cookie prevents XSS token theft

---

### 1.5 Logout

**POST `/api/auth/logout/`**

Request (requires auth):
```
No body required - refresh token read from HttpOnly cookie
```

Response (200):
```json
{
  "message": "Logged out successfully"
}
```

**Response Headers:**
```
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Strict; Path=/api/auth/; Max-Age=0
```

**Implementation:**
- Read refresh token from cookie
- Blacklist refresh token (using `djangorestframework-simplejwt` blacklist app)
- Clear refresh token cookie (Max-Age=0)
- Client should also clear access token from memory

---

### 1.6 Get Current User Profile

**GET `/api/users/me/`**

Response (200):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Alex Climber",
  "avatar": "https://...",
  "bio": "Love sport climbing...",
  "home_location": "Boulder, CO, USA",
  "risk_tolerance": "balanced",
  "preferred_grade_system": "yds",
  "profile_visible": true,
  "disciplines": [
    {
      "id": "uuid",
      "discipline": "sport",
      "grade_system": "yds",
      "comfortable_grade_min_display": "5.10a",
      "comfortable_grade_max_display": "5.11c",
      "projecting_grade_display": "5.12a",
      "years_experience": 5,
      "can_lead": true,
      "can_belay": true
    }
  ],
  "experience_tags": ["lead_belay_certified", "has_rope", "has_car"]
}
```

---

### 1.7 Update Profile

**PATCH `/api/users/me/`**

Request:
```json
{
  "display_name": "New Name",
  "bio": "Updated bio",
  "risk_tolerance": "conservative",
  "gender": "female",
  "preferred_partner_gender": "prefer_female",
  "weight_kg": 65,
  "preferred_weight_difference": "similar"
}
```

Response (200):
```json
{
  "id": "uuid",
  "display_name": "New Name",
  "bio": "Updated bio",
  "risk_tolerance": "conservative",
  ...
}
```

**Allowed fields:**
- display_name
- bio
- home_location
- risk_tolerance
- preferred_grade_system
- profile_visible
- gender
- preferred_partner_gender
- weight_kg
- preferred_weight_difference

**Not allowed:**
- email (separate endpoint if needed)
- password (use change-password endpoint)
- avatar (use dedicated avatar upload endpoint)
- email_verified (admin only)

---

### 1.8 Upload Avatar

**POST `/api/users/me/avatar/`**

Request:
```
Content-Type: multipart/form-data

avatar: <file>
```

Response (200):
```json
{
  "avatar": "https://media.sendbuddy.com/avatars/uuid.jpg"
}
```

**Validation:**
- Max size: 5MB
- Allowed types: jpg, png, webp
- Auto-resize to 400x400

---

### 1.9 Change Password

**POST `/api/users/me/change-password/`**

Request:
```json
{
  "old_password": "CurrentPass123!",
  "new_password": "NewSecurePass456!",
  "new_password_confirm": "NewSecurePass456!"
}
```

Response (200):
```json
{
  "message": "Password changed successfully"
}
```

---

### 1.10 Request Password Reset

**POST `/api/auth/password-reset/request/`**

Request:
```json
{
  "email": "user@example.com"
}
```

Response (200):
```json
{
  "message": "If that email exists, a password reset link has been sent."
}
```

**Security:**
- Always return 200 (don't leak email existence)
- Normalize email to lowercase before lookup
- Send email with uid + token (24h expiry)
- Only send if user exists

**Rate Limiting:**
- 3 password reset requests per IP per hour

---

### 1.11 Reset Password

**POST `/api/auth/password-reset/confirm/`**

Request:
```json
{
  "uid": "base64-encoded-user-id",
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass456!",
  "new_password_confirm": "NewSecurePass456!"
}
```

Response (200):
```json
{
  "message": "Password reset successfully. You can now log in."
}
```

Error (400):
```json
{
  "error": "Invalid or expired reset link"
}
```

**Implementation:**
- Use Django's `default_token_generator` (same as email verification)
- Validate both uid AND token
- Validate new password (min 8 chars, letter + number)
- Token is invalidated after password change (tokens are tied to password hash)

**Rate Limiting:**
- 5 password reset confirmation attempts per IP per hour

---

## 2. Frontend Implementation

### 2.1 Auth Context/Store

```typescript
// lib/auth.ts

interface User {
  id: string;
  email: string;
  display_name: string;
  avatar: string | null;
  email_verified: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;  // Stored in memory only, not persisted
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Using Zustand
import create from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,

      setAccessToken: (token: string | null) => {
        set({ accessToken: token, isAuthenticated: !!token });
      },

      setUser: (user: User | null) => {
        set({ user });
      },

      login: async (email: string, password: string) => {
        const response = await fetch('/api/auth/login/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
          credentials: 'include',  // Include cookies
        });

        if (!response.ok) {
          throw new Error('Login failed');
        }

        const data = await response.json();
        set({
          accessToken: data.access,
          user: data.user,
          isAuthenticated: true
        });
      },

      logout: async () => {
        await fetch('/api/auth/logout/', {
          method: 'POST',
          credentials: 'include',  // Send refresh cookie
        });

        set({
          accessToken: null,
          user: null,
          isAuthenticated: false
        });
      },

      register: async (data: RegisterData) => { ... },

      refreshAccessToken: async () => {
        try {
          const response = await fetch('/api/auth/token/refresh/', {
            method: 'POST',
            credentials: 'include',  // Send refresh cookie
          });

          if (!response.ok) {
            throw new Error('Refresh failed');
          }

          const data = await response.json();
          set({ accessToken: data.access });
          return true;
        } catch (error) {
          set({
            accessToken: null,
            user: null,
            isAuthenticated: false
          });
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        // Do NOT persist accessToken - keep in memory only
        // Refresh token is in HttpOnly cookie (managed by backend)
      }),
    }
  )
);
```

**Security Notes:**
- Access token kept in memory (lost on page refresh)
- Refresh token in HttpOnly cookie (not accessible to JavaScript)
- On page load, app should call `/api/auth/token/refresh/` to get new access token
- XSS attacks cannot steal refresh token
- CSRF protection via `SameSite=Strict` cookie attribute

---

### 2.2 Pages & Routes

#### `/signup` - Registration Page
- Form fields: email, password, password_confirm, display_name, home_location
- Client-side validation (email format, password strength)
- Show success message → redirect to email verification notice
- Link to `/login`

#### `/login` - Login Page
- Form fields: email, password
- "Forgot password?" link → `/forgot-password`
- "Resend verification email" link → `/resend-verification`
- On success: redirect to `/dashboard` or `/onboarding`
- Link to `/signup`

#### `/verify-email?uid=<uid>&token=<token>` - Email Verification
- Extract uid + token from URL params
- Auto-submit verification on page load
- Show loading state while verifying
- On success: redirect to `/login` with success message
- On error: show error + "Resend verification email" link

#### `/resend-verification` - Resend Verification Email
- Form field: email
- Show generic success message (don't leak email existence)
- Link back to `/login`

#### `/forgot-password` - Request Password Reset
- Form field: email
- Show generic success message (don't leak email existence)
- Link back to `/login`

#### `/reset-password?uid=<uid>&token=<token>` - Reset Password
- Extract uid + token from URL params
- Form fields: new_password, new_password_confirm
- Client-side password validation (min 8 chars, letter + number)
- On success: redirect to `/login` with success message
- On error: show error + link to `/forgot-password`

#### `/profile` - User Profile View (Protected)
- Display current user info
- "Edit Profile" button → `/profile/edit`
- "Change Password" button → `/profile/change-password`

#### `/profile/edit` - Edit Profile (Protected)
- Form with all editable fields (display_name, bio, location, preferences, gender, weight)
- Avatar upload via separate component/endpoint
- Save button
- Cancel button → `/profile`

#### `/profile/change-password` - Change Password (Protected)
- Form fields: old_password, new_password, new_password_confirm
- Client-side password validation
- On success: show success message, stay on page

---

### 2.3 Protected Routes

```typescript
// components/ProtectedRoute.tsx

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

---

### 2.4 API Client with Auth

```typescript
// lib/api.ts

class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;  // Refresh mutex

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isRetry = false  // Prevent infinite retry loops
  ): Promise<T> {
    const { accessToken } = useAuthStore.getState();

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
        ...options.headers,
      },
      credentials: 'include',  // Always include cookies for refresh token
    };

    const response = await fetch(`${API_URL}${endpoint}`, config);

    // Handle 401 - try to refresh token (but only once per request)
    if (response.status === 401 && !isRetry) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        // Retry request with new token (isRetry=true prevents loops)
        return this.request(endpoint, options, true);
      } else {
        // Refresh failed - logout and redirect
        useAuthStore.getState().logout();
        window.location.href = '/login';
        throw new Error('Session expired');
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData);
    }

    return response.json();
  }

  private async refreshToken(): Promise<boolean> {
    // If refresh is already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    // Create refresh promise (mutex to prevent concurrent refresh calls)
    this.refreshPromise = (async () => {
      try {
        // Raw fetch (no interceptor) to avoid infinite loops
        const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
          method: 'POST',
          credentials: 'include',  // Send refresh cookie
        });

        if (!response.ok) {
          return false;
        }

        const data = await response.json();
        useAuthStore.getState().setAccessToken(data.access);
        return true;
      } catch (error) {
        return false;
      } finally {
        this.refreshPromise = null;  // Clear mutex
      }
    })();

    return this.refreshPromise;
  }

  async register(data: RegisterData) {
    return this.post('/api/auth/register/', data);
  }

  async login(email: string, password: string) {
    return this.post('/api/auth/login/', { email, password });
  }

  async getCurrentUser() {
    return this.get('/api/users/me/');
  }

  // ... other methods
}

export const apiClient = new ApiClient();
```

**Key Security Features:**
1. **Refresh Mutex** - Prevents multiple concurrent refresh calls
2. **Retry Flag** - Prevents infinite retry loops on persistent 401s
3. **Separate Refresh Logic** - Uses raw fetch to avoid interceptor recursion
4. **Credentials: 'include'** - Always sends HttpOnly cookies
5. **Auto-logout on refresh failure** - Redirects to login page

---

## 3. Backend Implementation Details

### 3.1 Serializers

```python
# users/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, DisciplineProfile, ExperienceTag
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

        # Send verification email
        from .utils import send_verification_email
        send_verification_email(user)

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
```

---

### 3.2 Views

```python
# users/views.py

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer
from .models import User

# Register
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/h', method='POST')
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    return Response({
        'user': UserSerializer(user).data,
        'message': 'Registration successful. Please check your email to verify your account.'
    }, status=status.HTTP_201_CREATED)


# Email Verification
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='POST')
def verify_email(request):
    uid = request.data.get('uid')
    token = request.data.get('token')

    if not uid or not token:
        return Response({'error': 'Missing uid or token'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'error': 'Invalid or expired verification link'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'error': 'Invalid or expired verification link'}, status=status.HTTP_400_BAD_REQUEST)

    if user.email_verified:
        return Response({'message': 'Email already verified'}, status=status.HTTP_200_OK)

    user.email_verified = True
    user.save(update_fields=['email_verified'])

    return Response({'message': 'Email verified successfully. You can now log in.'})


# Resend Verification Email
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST')
def resend_verification(request):
    email = request.data.get('email', '').lower()

    # Always return success (don't leak email existence)
    try:
        user = User.objects.get(email__iexact=email)
        if not user.email_verified:
            from .utils import send_verification_email
            send_verification_email(user)
    except User.DoesNotExist:
        pass

    return Response({
        'message': 'If that email is registered and unverified, a new verification link has been sent.'
    })


# Login
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/15m', method='POST')
def login(request):
    email = request.data.get('email', '').lower()
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.email_verified:
        return Response({'error': 'Please verify your email before logging in'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    response = Response({
        'access': str(access),
        'user': UserSerializer(user).data
    })

    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite='Strict',
        max_age=60 * 60 * 24 * 7,  # 7 days
        path='/api/auth/'
    )

    return response


# Token Refresh
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh_token = request.COOKIES.get('refresh_token')

    if not refresh_token:
        return Response({'error': 'No refresh token provided'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        access = refresh.access_token

        # Rotate refresh token for enhanced security
        new_refresh = RefreshToken.for_user(refresh.user)

        response = Response({'access': str(access)})

        # Set new refresh token
        response.set_cookie(
            key='refresh_token',
            value=str(new_refresh),
            httponly=True,
            secure=True,
            samesite='Strict',
            max_age=60 * 60 * 24 * 7,
            path='/api/auth/'
        )

        return response

    except Exception:
        return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


# Logout
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.COOKIES.get('refresh_token')

    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Requires djangorestframework-simplejwt[blacklist]
        except Exception:
            pass

    response = Response({'message': 'Logged out successfully'})

    # Clear refresh token cookie
    response.delete_cookie('refresh_token', path='/api/auth/')

    return response


# Get/Update Current User
class CurrentUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


# Password Reset Request
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST')
def password_reset_request(request):
    email = request.data.get('email', '').lower()

    try:
        user = User.objects.get(email__iexact=email)
        from .utils import send_password_reset_email
        send_password_reset_email(user)
    except User.DoesNotExist:
        pass

    return Response({
        'message': 'If that email exists, a password reset link has been sent.'
    })


# Password Reset Confirm
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/h', method='POST')
def password_reset_confirm(request):
    uid = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    new_password_confirm = request.data.get('new_password_confirm')

    if not all([uid, token, new_password, new_password_confirm]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    if new_password != new_password_confirm:
        return Response({'error': "Passwords don't match"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate password
    import re
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password):
        return Response({'error': 'Password must contain at least one letter and one number'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    return Response({'message': 'Password reset successfully. You can now log in.'})
```

---

### 3.3 Email Utilities

```python
# users/utils.py

from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

def send_verification_email(user):
    """Send email verification link with uid + token"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    verification_url = f"{settings.FRONTEND_URL}/verify-email?uid={uid}&token={token}"

    send_mail(
        subject='Verify your Send Buddy account',
        message=f'''Hi {user.display_name},

Welcome to Send Buddy! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Happy climbing!
The Send Buddy Team''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    """Send password reset link with uid + token"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    send_mail(
        subject='Reset your Send Buddy password',
        message=f'''Hi {user.display_name},

We received a request to reset your password. Click the link below to choose a new password:

{reset_url}

This link will expire in 24 hours.

If you didn't request a password reset, please ignore this email. Your password will not be changed.

The Send Buddy Team''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
```

**Token Security:**
- Tokens are tied to user's password hash and last_login
- Tokens expire after 24 hours (Django default)
- Changing password invalidates all existing tokens
- uid is base64-encoded for URL safety
- Using Django's built-in `default_token_generator` (secure and battle-tested)

---

## 4. Implementation Checklist

### Backend
- [ ] Install `django-ratelimit` dependency
- [ ] Install `djangorestframework-simplejwt[blacklist]` for token blacklisting
- [ ] Create RegisterSerializer with email normalization + password validation
- [ ] Create UserSerializer with experience_tags as slug array
- [ ] Create UserUpdateSerializer (separate from read serializer)
- [ ] Create DisciplineProfileSerializer
- [ ] Implement register view with rate limiting (5/hour)
- [ ] Implement login view with HttpOnly cookie + rate limiting (5/15min)
- [ ] Implement email verification view (uid + token validation)
- [ ] Implement resend verification view with rate limiting (3/hour)
- [ ] Implement token refresh view (cookie-based, with rotation)
- [ ] Implement logout view (blacklist token, clear cookie)
- [ ] Implement password reset request view with rate limiting (3/hour)
- [ ] Implement password reset confirm view (uid + token validation)
- [ ] Create CurrentUserView (GET/PATCH `/api/users/me/`)
- [ ] Add avatar upload endpoint
- [ ] Add change password endpoint
- [ ] Create email utility functions (send_verification_email, send_password_reset_email)
- [ ] Configure email backend (console for dev, SMTP for prod)
- [ ] Add FRONTEND_URL to settings
- [ ] Configure CORS to allow credentials (cookies)
- [ ] Configure JWT settings (access token TTL, blacklist)
- [ ] Create URL routes for all auth endpoints
- [ ] Write unit tests for auth endpoints
- [ ] Write unit tests for email utilities
- [ ] Write unit tests for serializers

### Frontend
- [ ] Create auth store (Zustand) with cookie-based auth
- [ ] Implement refresh mutex in API client
- [ ] Build signup page
- [ ] Build login page with "Resend verification" link
- [ ] Build email verification page (auto-submit on load)
- [ ] Build resend verification page
- [ ] Build forgot password page
- [ ] Build reset password page
- [ ] Build profile view page
- [ ] Build profile edit page (exclude avatar)
- [ ] Build avatar upload component (multipart)
- [ ] Build change password page
- [ ] Create ProtectedRoute component
- [ ] Add token refresh logic to API client (with retry flag)
- [ ] Handle 401 errors globally
- [ ] Add page load refresh token call

### Testing
- [ ] Test registration flow end-to-end
- [ ] Test email verification with valid/invalid tokens
- [ ] Test resend verification email
- [ ] Test login flow (with cookies)
- [ ] Test login failure cases (unverified email, invalid credentials)
- [ ] Test token refresh flow (cookie-based)
- [ ] Test logout (cookie clearing)
- [ ] Test password reset request
- [ ] Test password reset confirm with valid/invalid tokens
- [ ] Test profile update (allowed fields only)
- [ ] Test avatar upload
- [ ] Test change password
- [ ] Test protected routes redirect
- [ ] Test rate limiting on all endpoints
- [ ] Test email normalization (case-insensitive)

---

## 5. Security Checklist

### Authentication
- [ ] Passwords hashed with Django's default (PBKDF2)
- [ ] Password validation (min 8 chars, letter + number required)
- [ ] Email normalization to lowercase (prevents duplicate accounts)
- [ ] Case-insensitive email lookup
- [ ] Email verification required before login
- [ ] Refresh tokens in HttpOnly cookies (XSS-proof)
- [ ] Access tokens in memory only (not persisted in localStorage)
- [ ] Refresh token rotation on each refresh
- [ ] Token blacklisting on logout

### Tokens & Sessions
- [ ] Short access token TTL (15 minutes recommended)
- [ ] Longer refresh token TTL (7 days)
- [ ] Email verification tokens expire in 24h
- [ ] Password reset tokens expire in 24h
- [ ] Tokens invalidated on password change
- [ ] uid + token validation (not token alone)
- [ ] Base64-encoded uid for URL safety

### HTTP Security
- [ ] HTTPS in production (required for secure cookies)
- [ ] CSRF protection enabled (Django default)
- [ ] SameSite=Strict on cookies (CSRF protection)
- [ ] Secure flag on cookies in production
- [ ] CORS configured to allow credentials
- [ ] CORS restricted to frontend domain only

### Rate Limiting
- [ ] Registration: 5 attempts/hour per IP
- [ ] Login: 5 attempts/15min per IP
- [ ] Email verification: 10 attempts/hour per IP
- [ ] Resend verification: 3 attempts/hour per IP
- [ ] Password reset request: 3 attempts/hour per IP
- [ ] Password reset confirm: 5 attempts/hour per IP

### API Security
- [ ] Refresh mutex prevents concurrent refresh calls
- [ ] Retry flag prevents infinite 401 loops
- [ ] Separate refresh logic (raw fetch, no interceptor)
- [ ] Auto-logout on refresh failure
- [ ] Always return 200 for password reset/resend (don't leak email existence)

### Email Security
- [ ] Don't leak email existence on resend/password reset
- [ ] Email templates include expiry warnings
- [ ] From address configured properly (SPF/DKIM in production)

### Testing & Monitoring
- [ ] Log failed login attempts
- [ ] Monitor rate limit hits
- [ ] Test all error cases
- [ ] Test token expiry scenarios
- [ ] Test concurrent requests with refresh mutex

---

## 6. Estimated Timeline

- Backend auth endpoints: 5 hours
  - Register, login, logout (with HttpOnly cookies)
  - Email verification (uid + token)
  - Resend verification endpoint
  - Token refresh (cookie-based with rotation)
- Password reset flow: 2 hours
  - Request reset endpoint
  - Confirm reset endpoint (uid + token)
- Rate limiting setup: 1 hour
- Email utilities: 1 hour
- User profile endpoints: 2 hours
  - GET/PATCH current user
  - Avatar upload
  - Change password
- Frontend auth pages: 5 hours
  - Signup, login, email verification
  - Resend verification, forgot password, reset password
- Auth store & API client: 3 hours
  - Cookie-based auth
  - Refresh mutex
  - Retry logic with flag
- Profile pages: 2 hours
  - View/edit profile
  - Avatar upload component
  - Change password
- Testing: 3 hours
  - Backend unit tests
  - Frontend integration tests
  - Security testing (rate limits, token validation)
- **Total: ~24 hours**

**Note:** Timeline increased from original 14 hours due to security enhancements (HttpOnly cookies, rate limiting, refresh mutex, uid+token validation, resend verification endpoint)

---

## Next Phase
**Phase 3: Trip & Availability Management**
