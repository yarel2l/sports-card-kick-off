"""
Views package for accounts app.
"""

from .auth import (
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

__all__ = [
    'UserRegistrationView',
    'UserLoginView',
    'UserLogoutView',
    'TokenRefreshView',
    'PasswordResetRequestView',
    'PasswordResetConfirmView',
    'PasswordChangeView',
    'CurrentUserView',
    'EmailVerificationView',
    'AccountDeleteView',
]
