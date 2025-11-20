"""
Tests for password management API endpoints.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


User = get_user_model()

PASSWORD_RESET_URL = reverse('accounts:password_reset')
PASSWORD_RESET_CONFIRM_URL = reverse('accounts:password_reset_confirm')
PASSWORD_CHANGE_URL = reverse('accounts:password_change')


def create_user(**params):
    """Create and return a new user."""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'TestPass123!',
    }
    defaults.update(params)
    return User.objects.create_user(**defaults)


class PasswordResetAPITests(TestCase):
    """Test password reset functionality."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()

    def test_password_reset_request_success(self):
        """Test requesting password reset is successful."""
        payload = {'email': self.user.email}

        res = self.client.post(PASSWORD_RESET_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('message', res.data)

    def test_password_reset_request_nonexistent_email(self):
        """Test password reset with non-existent email still returns success."""
        payload = {'email': 'nonexistent@example.com'}

        res = self.client.post(PASSWORD_RESET_URL, payload, format='json')

        # Should return success for security reasons (don't reveal if email exists)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_password_reset_request_invalid_email(self):
        """Test password reset with invalid email format."""
        payload = {'email': 'invalid-email'}

        res = self.client.post(PASSWORD_RESET_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_success(self):
        """Test confirming password reset is successful."""
        # Generate valid token and UID
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        payload = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_RESET_CONFIRM_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))

    def test_password_reset_confirm_password_mismatch(self):
        """Test password reset fails with mismatched passwords."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        payload = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'DifferentPass123!',
        }

        res = self.client.post(PASSWORD_RESET_CONFIRM_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('TestPass123!'))

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset fails with invalid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            'uid': uid,
            'token': 'invalid-token',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_RESET_CONFIRM_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_invalid_uid(self):
        """Test password reset fails with invalid UID."""
        token = default_token_generator.make_token(self.user)

        payload = {
            'uid': 'invalid-uid',
            'token': token,
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_RESET_CONFIRM_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_weak_password(self):
        """Test password reset fails with weak password."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        payload = {
            'uid': uid,
            'token': token,
            'new_password': 'weak',
            'new_password_confirm': 'weak',
        }

        res = self.client.post(PASSWORD_RESET_CONFIRM_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordChangeAPITests(TestCase):
    """Test password change functionality."""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            username='testuser',
            password='OldPass123!',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_password_change_success(self):
        """Test changing password is successful."""
        payload = {
            'old_password': 'OldPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))
        self.assertFalse(self.user.check_password('OldPass123!'))

    def test_password_change_incorrect_old_password(self):
        """Test password change fails with incorrect old password."""
        payload = {
            'old_password': 'WrongOldPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_password_change_password_mismatch(self):
        """Test password change fails with mismatched new passwords."""
        payload = {
            'old_password': 'OldPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'DifferentPass123!',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_weak_password(self):
        """Test password change fails with weak password."""
        payload = {
            'old_password': 'OldPass123!',
            'new_password': 'weak',
            'new_password_confirm': 'weak',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_requires_authentication(self):
        """Test password change requires authentication."""
        self.client.force_authenticate(user=None)

        payload = {
            'old_password': 'OldPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_same_as_old(self):
        """Test password change with same password as old."""
        payload = {
            'old_password': 'OldPass123!',
            'new_password': 'OldPass123!',
            'new_password_confirm': 'OldPass123!',
        }

        res = self.client.post(PASSWORD_CHANGE_URL, payload, format='json')

        # This might be allowed or rejected depending on requirements
        # Adjust assertion based on your implementation
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
