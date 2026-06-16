"""
Authentication Views.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample

from ..serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserLogoutSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        tags=['Authentication'],
        summary="Register new user",
        description="""
        Register a new user account in the system.

        **Process:**
        1. Validates user input (email, username, password)
        2. Creates new user account
        3. Generates JWT access and refresh tokens
        4. Returns user data and authentication tokens

        **Password Requirements:**
        - Minimum 8 characters
        - Cannot be too similar to personal information
        - Cannot be entirely numeric
        - Cannot be a commonly used password

        **Response includes:**
        - User profile data
        - JWT access token (valid for 1 day)
        - JWT refresh token (valid for 7 days)
        """,
        examples=[
            OpenApiExample(
                name='Registration Example',
                value={
                    'email': 'user@example.com',
                    'username': 'johndoe',
                    'password': 'SecureP@ssw0rd',
                    'password_confirm': 'SecureP@ssw0rd',
                    'first_name': 'John',
                    'last_name': 'Doe'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Registration',
                value={
                    'user': {
                        'account_id': '123e4567-e89b-12d3-a456-426614174000',
                        'email': 'user@example.com',
                        'username': 'johndoe',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'is_active': True,
                        'date_joined': '2024-01-15T10:30:00Z',
                        'created_at': '2024-01-15T10:30:00Z'
                    },
                    'tokens': {
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                    },
                    'message': 'User registered successfully.'
                },
                response_only=True,
                status_codes=['201']
            ),
        ],
        responses={
            201: OpenApiResponse(
                description="User created successfully with authentication tokens"
            ),
            400: OpenApiResponse(
                description="Validation error - Invalid input data"
            )
        }
    )
)
class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint.

    Creates a new user account and returns JWT tokens.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': _('User registered successfully.')
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    """
    User login endpoint.

    Authenticates user and returns JWT tokens.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer

    @extend_schema(
        tags=['Authentication'],
        summary="Login user",
        description="""
        Authenticate a user and obtain JWT tokens for API access.

        **Process:**
        1. Validates user credentials (email and password)
        2. Authenticates user against the database
        3. Generates new JWT access and refresh tokens
        4. Returns user data and authentication tokens

        **Authentication:**
        - Uses email address as username
        - Password is verified securely using Django's password hashing
        - Account must be active (is_active=True)

        **Token Information:**
        - Access Token: Valid for 1 day, used for API authentication
        - Refresh Token: Valid for 7 days, used to obtain new access tokens
        - Tokens are signed using RS256 algorithm

        **Security Notes:**
        - Failed login attempts do not reveal whether email exists
        - Inactive accounts cannot login
        - Tokens are blacklisted on logout
        """,
        request=UserLoginSerializer,
        examples=[
            OpenApiExample(
                name='Login Request',
                value={
                    'email': 'user@example.com',
                    'password': 'SecureP@ssw0rd'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Login',
                value={
                    'user': {
                        'account_id': '123e4567-e89b-12d3-a456-426614174000',
                        'email': 'user@example.com',
                        'username': 'johndoe',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'is_active': True,
                        'date_joined': '2024-01-15T10:30:00Z',
                        'created_at': '2024-01-15T10:30:00Z'
                    },
                    'tokens': {
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                    },
                    'message': 'Login successful.'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Invalid Credentials',
                value={
                    'non_field_errors': ['Unable to log in with provided credentials.']
                },
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Login successful - Returns user data and JWT tokens"
            ),
            400: OpenApiResponse(
                description="Invalid credentials or inactive account"
            )
        }
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': _('Login successful.')
        }, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    User logout endpoint.

    Blacklists the refresh token to prevent further use.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserLogoutSerializer

    @extend_schema(
        tags=['Authentication'],
        summary="Logout user",
        description="""
        Logout a user by blacklisting their refresh token.

        **Process:**
        1. Validates the provided refresh token
        2. Adds token to blacklist database
        3. Prevents token from being used to generate new access tokens
        4. Returns success confirmation

        **Security:**
        - Requires valid JWT access token in Authorization header
        - Blacklisted tokens cannot be used again
        - Token blacklisting is permanent and cannot be reversed
        - Access tokens remain valid until expiration (max 1 day)

        **Best Practices:**
        - Always logout users when they close the application
        - Clear stored tokens from client after logout
        - Implement token refresh before expiration for active sessions

        **Authorization Required:**
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        request=UserLogoutSerializer,
        examples=[
            OpenApiExample(
                name='Logout Request',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Logout',
                value={
                    'message': 'Logout successful.'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Invalid Token',
                value={
                    'error': 'Invalid token.'
                },
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Logout successful - Token has been blacklisted"
            ),
            400: OpenApiResponse(
                description="Invalid or expired refresh token"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            )
        }
    )
    def post(self, request):
        serializer = UserLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({
                'message': _('Logout successful.')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': _('Invalid token.')},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(APIView):
    """
    Request password reset.

    Sends password reset email to user.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        tags=['Password Management'],
        summary="Request password reset",
        description="""
        Initiate password reset process by requesting a reset token.

        **Process:**
        1. User provides their email address
        2. System validates email format
        3. If email exists and account is active, generates reset token
        4. Sends password reset email with token and UID
        5. Returns success message (regardless of email existence for security)

        **Security Features:**
        - Does not reveal whether email exists in system
        - Token is single-use and expires after a period
        - Only active accounts can reset passwords
        - Rate limiting prevents abuse

        **Email Content:**
        - Reset link with embedded token and UID
        - Token expiration information
        - Instructions for completing reset

        **Note for Development:**
        Currently returns token and UID in response for testing.
        In production, these are only sent via email.

        **No Authentication Required**
        """,
        request=PasswordResetRequestSerializer,
        examples=[
            OpenApiExample(
                name='Reset Request',
                value={
                    'email': 'user@example.com'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Request',
                value={
                    'message': 'Password reset email has been sent.',
                    'reset_url': '/api/v1/auth/password-reset-confirm/MTIz/5ab-a1b2c3d4e5f6/',
                    'uid': 'MTIz',
                    'token': '5ab-a1b2c3d4e5f6'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Password reset initiated - Check email for reset link"
            ),
            400: OpenApiResponse(
                description="Invalid email format"
            )
        }
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Reset link format: /reset-password/{uid}/{token}/
            reset_url = f"{request.build_absolute_uri('/api/v1/auth/password-reset-confirm/')}{uid}/{token}/"

            # Send the reset link by email. Never expose the token in the API
            # response in non-debug environments (it would let anyone who can
            # read the response take over the account).
            try:
                send_mail(
                    subject=str(_('Password reset request')),
                    message=str(_(
                        'Use the following link to reset your password: %(url)s'
                    )) % {'url': reset_url},
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception('Failed to send password reset email')

            response_data = {
                'message': _('Password reset email has been sent.'),
            }
            # Only expose the raw token/uid when running with DEBUG enabled,
            # to keep local development convenient without leaking secrets.
            if settings.DEBUG:
                response_data.update({
                    'reset_url': reset_url,
                    'uid': uid,
                    'token': token,
                })

            return Response(response_data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            # Don't reveal that user doesn't exist (security)
            # Still return success message
            return Response({
                'message': _('Password reset email has been sent.')
            }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset.

    Validates token and sets new password.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        tags=['Password Management'],
        summary="Confirm password reset",
        description="""
        Complete password reset by validating token and setting new password.

        **Process:**
        1. Validates reset token and UID
        2. Checks token hasn't expired or been used
        3. Validates new password meets requirements
        4. Confirms password and confirmation match
        5. Updates user password
        6. Invalidates reset token

        **Password Requirements:**
        - Minimum 8 characters
        - Cannot be too similar to personal information
        - Cannot be entirely numeric
        - Cannot be a commonly used password

        **Token Security:**
        - Single-use tokens (cannot be reused)
        - Time-limited validity
        - Cryptographically secure generation
        - Invalidated after successful reset

        **Error Handling:**
        - Invalid token returns generic error (security)
        - Expired tokens are rejected
        - Password validation errors are detailed

        **No Authentication Required**
        """,
        request=PasswordResetConfirmSerializer,
        examples=[
            OpenApiExample(
                name='Reset Confirm Request',
                value={
                    'uid': 'MTIz',
                    'token': '5ab-a1b2c3d4e5f6',
                    'new_password': 'NewSecureP@ssw0rd',
                    'new_password_confirm': 'NewSecureP@ssw0rd'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Reset',
                value={
                    'message': 'Password has been reset successfully.'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Invalid Token',
                value={
                    'error': 'Invalid or expired token.'
                },
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                name='Password Mismatch',
                value={
                    'new_password_confirm': ['Passwords do not match.']
                },
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Password reset successful - User can now login with new password"
            ),
            400: OpenApiResponse(
                description="Invalid token, expired token, or validation error"
            )
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Decode UID
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)

            # Validate token
            token = serializer.validated_data['token']
            if not default_token_generator.check_token(user, token):
                return Response(
                    {'error': _('Invalid or expired token.')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({
                'message': _('Password has been reset successfully.')
            }, status=status.HTTP_200_OK)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': _('Invalid token.')},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordChangeView(APIView):
    """
    Change password for authenticated users.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        tags=['Password Management'],
        summary="Change password",
        description="""
        Change password for currently authenticated user.

        **Process:**
        1. Verifies user's current password
        2. Validates new password meets requirements
        3. Confirms new password and confirmation match
        4. Updates user password in database
        5. Returns success confirmation

        **Requirements:**
        - User must be authenticated (valid access token)
        - Must provide correct current password
        - New password must meet security requirements
        - New password must match confirmation

        **Password Requirements:**
        - Minimum 8 characters
        - Cannot be too similar to personal information
        - Cannot be entirely numeric
        - Cannot be a commonly used password
        - Cannot be the same as old password

        **Security Features:**
        - Requires current password verification
        - Invalidates all existing sessions after change (recommended)
        - Password is hashed using Django's secure password hashing
        - Failed attempts are logged

        **Post-Change Actions:**
        Consider implementing:
        - Force re-login after password change
        - Send email notification of password change
        - Invalidate all refresh tokens

        **Authorization Required:**
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        request=PasswordChangeSerializer,
        examples=[
            OpenApiExample(
                name='Change Password Request',
                value={
                    'old_password': 'CurrentP@ssw0rd',
                    'new_password': 'NewSecureP@ssw0rd',
                    'new_password_confirm': 'NewSecureP@ssw0rd'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Change',
                value={
                    'message': 'Password changed successfully.'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Incorrect Old Password',
                value={
                    'old_password': ['Old password is incorrect.']
                },
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                name='Password Mismatch',
                value={
                    'new_password_confirm': ['Passwords do not match.']
                },
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                name='Weak Password',
                value={
                    'new_password': [
                        'This password is too short. It must contain at least 8 characters.',
                        'This password is too common.'
                    ]
                },
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Password changed successfully"
            ),
            400: OpenApiResponse(
                description="Validation error - Incorrect old password or invalid new password"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            )
        }
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': _('Password changed successfully.')
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=['User Profile'],
        summary="Get current user profile",
        description="""
        Retrieve the authenticated user's profile information.

        **Response includes:**
        - account_id (UUID primary key)
        - email address
        - username
        - first and last name
        - account status (is_active)
        - account creation date

        **Authorization Required:**
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        examples=[
            OpenApiExample(
                name='Get Profile Response',
                value={
                    'account_id': '123e4567-e89b-12d3-a456-426614174000',
                    'email': 'user@example.com',
                    'username': 'johndoe',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'is_active': True,
                    'date_joined': '2024-01-15T10:30:00Z',
                    'created_at': '2024-01-15T10:30:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
        responses={
            200: UserSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            )
        }
    ),
    put=extend_schema(
        tags=['User Profile'],
        summary="Update current user profile (full)",
        description="""
        Update all modifiable fields of the authenticated user's profile.

        **Modifiable Fields:**
        - username (must be unique)
        - first_name
        - last_name

        **Read-Only Fields:**
        - account_id, email, is_active, date_joined, created_at

        **Authorization Required:**
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        examples=[
            OpenApiExample(
                name='Update Profile Request (PUT)',
                value={
                    'username': 'johnsmith',
                    'first_name': 'John',
                    'last_name': 'Smith'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Update Profile Response',
                value={
                    'account_id': '123e4567-e89b-12d3-a456-426614174000',
                    'email': 'user@example.com',
                    'username': 'johnsmith',
                    'first_name': 'John',
                    'last_name': 'Smith',
                    'is_active': True,
                    'date_joined': '2024-01-15T10:30:00Z',
                    'created_at': '2024-01-15T10:30:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Validation error - Invalid data or username already exists"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            )
        }
    ),
    patch=extend_schema(
        tags=['User Profile'],
        summary="Update current user profile (partial)",
        description="""
        Partially update the authenticated user's profile (only specified fields).

        **Modifiable Fields:**
        - username (must be unique)
        - first_name
        - last_name

        **Read-Only Fields:**
        - account_id, email, is_active, date_joined, created_at

        **Authorization Required:**
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        examples=[
            OpenApiExample(
                name='Partial Update Request (PATCH)',
                value={
                    'first_name': 'John',
                    'last_name': 'Smith'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Partial Update Response',
                value={
                    'account_id': '123e4567-e89b-12d3-a456-426614174000',
                    'email': 'user@example.com',
                    'username': 'johndoe',
                    'first_name': 'John',
                    'last_name': 'Smith',
                    'is_active': True,
                    'date_joined': '2024-01-15T10:30:00Z',
                    'created_at': '2024-01-15T10:30:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Validation error - Invalid data or username already exists"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            )
        }
    )
)
class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class TokenRefreshView(BaseTokenRefreshView):
    """
    Refresh JWT access token using refresh token.
    """

    @extend_schema(
        tags=['Authentication'],
        summary="Refresh access token",
        description="""
        Obtain a new access token using a valid refresh token.

        **Process:**
        1. Validates the provided refresh token
        2. Checks token is not blacklisted
        3. Generates new access token
        4. Optionally rotates refresh token (if ROTATE_REFRESH_TOKENS=True)
        5. Returns new access token and optionally new refresh token

        **Token Rotation:**
        - When enabled, a new refresh token is issued
        - Old refresh token is automatically blacklisted
        - Provides enhanced security by limiting token lifetime

        **Use Cases:**
        - Maintain user session without re-authentication
        - Refresh expired access tokens
        - Implement seamless user experience

        **Security Notes:**
        - Refresh tokens are valid for 7 days
        - Access tokens are valid for 1 day
        - Blacklisted tokens cannot be used
        - Token rotation prevents token theft

        **Best Practices:**
        - Refresh tokens proactively before expiration
        - Store refresh tokens securely
        - Implement automatic refresh in client applications
        - Handle refresh failures by redirecting to login

        **No Authentication Required:**
        This endpoint does not require the Authorization header.
        Only a valid refresh token in the request body.
        """,
        request=TokenRefreshSerializer,
        examples=[
            OpenApiExample(
                name='Refresh Token Request',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Refresh',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Invalid or Expired Token',
                value={
                    'detail': 'Token is invalid or expired',
                    'code': 'token_not_valid'
                },
                response_only=True,
                status_codes=['401']
            ),
            OpenApiExample(
                name='Blacklisted Token',
                value={
                    'detail': 'Token is blacklisted',
                    'code': 'token_not_valid'
                },
                response_only=True,
                status_codes=['401']
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Token refreshed successfully - Returns new access token and optionally new refresh token"
            ),
            401: OpenApiResponse(
                description="Invalid, expired, or blacklisted refresh token"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Handle token refresh request."""
        return super().post(request, *args, **kwargs)
