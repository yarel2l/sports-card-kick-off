"""
Authentication URLs.
"""

from django.urls import path

from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    TokenRefreshView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordChangeView,
    CurrentUserView,
    EmailVerificationView,
    AccountDeleteView,
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Password Management
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),

    # Email verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('verify-email/<str:uid>/<str:token>/', EmailVerificationView.as_view(), name='verify_email_link'),

    # User Profile
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('me/delete/', AccountDeleteView.as_view(), name='delete_account'),
]
