from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db.models import Q
from django.core.mail import mail_admins
from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer, PublicUserSerializer,
    ChangePasswordSerializer, DisciplineProfileCreateSerializer,
    ExperienceTagSerializer, ExperienceTagDetailSerializer, BlockSerializer, BlockedUserSerializer,
    ReportSerializer, CreateReportSerializer
)
from .models import User, DisciplineProfile, UserExperienceTag, ExperienceTag, Block, Report
import re


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/h', method='POST')
def register(request):
    """User registration with email verification"""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    return Response({
        'user': UserSerializer(user).data,
        'message': 'Registration successful. Please check your email to verify your account.'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='POST')
def verify_email(request):
    """Verify email with uid + token"""
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


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST')
def resend_verification(request):
    """Resend verification email"""
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


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/15m', method='POST')
def login(request):
    """Login with email + password, returns access token and sets HttpOnly refresh cookie"""
    email = request.data.get('email', '').lower()
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    # Email verification disabled for dev
    # if not user.email_verified:
    #     return Response({'error': 'Please verify your email before logging in'}, status=status.HTTP_403_FORBIDDEN)

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


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """Refresh access token using HttpOnly cookie refresh token"""
    refresh_token = request.COOKIES.get('refresh_token')

    if not refresh_token:
        return Response({'error': 'No refresh token provided'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)

        # Get user from token
        user_id = refresh.get('user_id')
        user = User.objects.get(pk=user_id)

        # Generate new tokens (rotate refresh token for security)
        new_refresh = RefreshToken.for_user(user)
        access = new_refresh.access_token

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout and clear refresh token cookie"""
    refresh_token = request.COOKIES.get('refresh_token')

    # Note: Token blacklisting requires additional configuration
    # For now, we just clear the cookie
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            # token.blacklist()  # Uncomment when blacklist is configured
        except Exception:
            pass

    response = Response({'message': 'Logged out successfully'})

    # Clear refresh token cookie
    response.delete_cookie('refresh_token', path='/api/auth/')

    return response


# ============================================================================
# PASSWORD RESET VIEWS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST')
def password_reset_request(request):
    """Request password reset email"""
    email = request.data.get('email', '').lower()

    # Always return success to prevent email enumeration
    try:
        user = User.objects.get(email__iexact=email)
        from .utils import send_password_reset_email
        send_password_reset_email(user)
    except User.DoesNotExist:
        pass

    return Response({
        'message': 'If that email exists, a password reset link has been sent.'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='GET')
def password_reset_validate(request):
    """Validate password reset token without consuming it"""
    uid = request.query_params.get('uid')
    token = request.query_params.get('token')

    if not uid or not token:
        return Response({
            'valid': False,
            'message': 'Missing uid or token'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({
            'valid': False,
            'message': 'Invalid or expired reset link'
        })

    if not default_token_generator.check_token(user, token):
        return Response({
            'valid': False,
            'message': 'Invalid or expired reset link'
        })

    return Response({
        'valid': True
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/h', method='POST')
def password_reset_confirm(request):
    """Confirm password reset with token + new password"""
    token = request.data.get('token')
    password = request.data.get('password')

    # Support both formats: token-based and uid+token-based
    uid = request.data.get('uid')

    # If token contains both uid and token (legacy format)
    if not uid and token and '.' in token:
        # Assume token is in format "uid.token"
        try:
            uid, token = token.split('.', 1)
        except ValueError:
            pass

    if not token or not password:
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate password
    if len(password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return Response({'error': 'Password must contain at least one letter and one number'}, status=status.HTTP_400_BAD_REQUEST)

    # Decode uid if provided
    if uid:
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Token-only format - validate token and extract user
        return Response({'error': 'Invalid request format'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()

    return Response({'message': 'Password reset successfully. You can now log in.'})


# ============================================================================
# USER PROFILE VIEWS
# ============================================================================

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """Get or update current user profile"""
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_public_profile(request, user_id):
    """Get another user's public profile"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if profile is visible
    if not user.profile_visible:
        return Response(
            {'detail': 'This profile is private'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check if blocked
    if Block.objects.filter(
        Q(blocker=request.user, blocked=user) | Q(blocker=user, blocked=request.user)
    ).exists():
        return Response(
            {'detail': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Pass request context to get absolute URLs for images
    serializer = PublicUserSerializer(user, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """Upload user avatar (multipart/form-data)"""
    if 'avatar' not in request.FILES:
        return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    avatar_file = request.FILES['avatar']

    # Validate file size (5MB max)
    if avatar_file.size > 5 * 1024 * 1024:
        return Response({'error': 'Avatar file too large (max 5MB)'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if avatar_file.content_type not in allowed_types:
        return Response({'error': 'Invalid file type (allowed: jpg, png, webp)'}, status=status.HTTP_400_BAD_REQUEST)

    user.avatar = avatar_file
    user.save(update_fields=['avatar'])

    return Response({'avatar': user.avatar.url if user.avatar else None})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user

    # Verify old password
    if not user.check_password(serializer.validated_data['old_password']):
        return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

    # Set new password
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    return Response({'message': 'Password changed successfully'})


# ============================================================================
# DISCIPLINE PROFILE VIEWS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='30/h', method='POST')
def manage_disciplines(request):
    """List or create discipline profiles"""

    if request.method == 'GET':
        # List all discipline profiles for current user
        from .serializers import DisciplineProfileSerializer
        profiles = DisciplineProfile.objects.filter(user=request.user)
        serializer = DisciplineProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Create new discipline profile
        serializer = DisciplineProfileCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Save with current user
        profile = serializer.save(user=request.user)

        # Return full profile data
        from .serializers import DisciplineProfileSerializer
        return Response(
            DisciplineProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED
        )


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='30/h', method=['PATCH', 'DELETE'])
def manage_discipline_detail(request, pk):
    """Get, update, or delete a specific discipline profile"""

    # Get profile (must belong to current user)
    try:
        profile = DisciplineProfile.objects.get(pk=pk, user=request.user)
    except DisciplineProfile.DoesNotExist:
        return Response(
            {'detail': 'Discipline profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        from .serializers import DisciplineProfileSerializer
        serializer = DisciplineProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        serializer = DisciplineProfileCreateSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        from .serializers import DisciplineProfileSerializer
        return Response(DisciplineProfileSerializer(profile).data)

    elif request.method == 'DELETE':
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# EXPERIENCE TAG VIEWS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_all_experience_tags(request):
    """List all available experience tags"""
    tags = ExperienceTag.objects.all().order_by('category', 'display_name')
    serializer = ExperienceTagDetailSerializer(tags, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='30/h', method='POST')
def manage_experience_tags(request):
    """List or add experience tags"""

    if request.method == 'GET':
        # List all experience tags for current user
        tags = [tag.tag.slug for tag in request.user.experience_tags.all()]
        return Response({'tags': tags})

    elif request.method == 'POST':
        # Add experience tag
        serializer = ExperienceTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag_slug = serializer.validated_data['tag']
        tag = ExperienceTag.objects.get(slug=tag_slug)

        # Create if doesn't exist (avoid duplicates)
        user_tag, created = UserExperienceTag.objects.get_or_create(
            user=request.user,
            tag=tag
        )

        if created:
            return Response(
                {'message': f'Tag "{tag_slug}" added', 'tag': tag_slug},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'message': f'Tag "{tag_slug}" already exists', 'tag': tag_slug},
                status=status.HTTP_200_OK
            )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_experience_tag(request, tag_slug):
    """Remove an experience tag"""

    try:
        tag = ExperienceTag.objects.get(slug=tag_slug)
        user_tag = UserExperienceTag.objects.get(user=request.user, tag=tag)
        user_tag.delete()

        return Response(
            {'message': f'Tag "{tag_slug}" removed'},
            status=status.HTTP_204_NO_CONTENT
        )
    except ExperienceTag.DoesNotExist:
        return Response(
            {'detail': f'Tag "{tag_slug}" does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )
    except UserExperienceTag.DoesNotExist:
        return Response(
            {'detail': f'Tag "{tag_slug}" not found in your profile'},
            status=status.HTTP_404_NOT_FOUND
        )


# ============================================================================
# PHASE 6: TRUST & SAFETY VIEWS
# ============================================================================

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method='POST')
@ratelimit(key='user', rate='10/h', method='DELETE')
@never_cache
def block_user(request, user_id):
    """Block or unblock a user"""
    # Check rate limit
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Rate limit exceeded. Try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    if request.method == 'POST':
        # Block user
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
        from climbing_sessions.models import Session
        Session.objects.filter(
            Q(inviter=request.user, invitee=blocked_user) |
            Q(inviter=blocked_user, invitee=request.user),
            status__in=['pending', 'accepted']
        ).update(status='cancelled')

        return Response({
            'message': 'User blocked successfully',
            'blocked_user': BlockedUserSerializer(blocked_user).data
        }, status=status.HTTP_201_CREATED)

    elif request.method == 'DELETE':
        # Unblock user
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
        from climbing_sessions.models import Session
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

    # Send confirmation email to reporter
    from .email import send_report_confirmation
    try:
        send_report_confirmation(report)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send report confirmation email: {e}")

    # Send admin notification
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
