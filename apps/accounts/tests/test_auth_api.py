"""
Tests for authentication API endpoints.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


User = get_user_model()

REGISTER_URL = reverse('accounts:register')
LOGIN_URL = reverse('accounts:login')
LOGOUT_URL = reverse('accounts:logout')
TOKEN_REFRESH_URL = reverse('accounts:token_refresh')
ME_URL = reverse('accounts:current_user')


def create_user(**params):
    """Create and return a new user."""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'TestPass123!',
    }
    defaults.update(params)
    return User.objects.create_user(**defaults)


class PublicAuthAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_register_user_success(self):
        """Test registering a user is successful."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }

        res = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', res.data)
        self.assertIn('tokens', res.data)
        self.assertIn('access', res.data['tokens'])
        self.assertIn('refresh', res.data['tokens'])

        user = User.objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(user.username, payload['username'])
        self.assertNotIn('password', res.data['user'])

    def test_register_user_password_mismatch(self):
        """Test registration fails with password mismatch."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
            'password_confirm': 'DifferentPass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }

        res = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            User.objects.filter(email=payload['email']).exists()
        )

    def test_register_user_with_existing_email(self):
        """Test registration fails with existing email."""
        create_user(email='test@example.com', username='existinguser')

        payload = {
            'email': 'test@example.com',
            'username': 'newuser',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
        }

        res = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_with_existing_username(self):
        """Test registration fails with existing username."""
        create_user(email='existing@example.com', username='testuser')

        payload = {
            'email': 'new@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
        }

        res = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_with_short_password(self):
        """Test registration fails with password too short."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'short',
            'password_confirm': 'short',
        }

        res = self.client.post(REGISTER_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            User.objects.filter(email=payload['email']).exists()
        )

    def test_login_user_success(self):
        """Test login with valid credentials."""
        user_details = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }

        res = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('user', res.data)
        self.assertIn('tokens', res.data)
        self.assertIn('access', res.data['tokens'])
        self.assertIn('refresh', res.data['tokens'])
        self.assertEqual(res.data['user']['email'], user_details['email'])

    def test_login_user_with_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        create_user(email='test@example.com', username='testuser')

        payload = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!',
        }

        res = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('tokens', res.data)

    def test_login_user_with_nonexistent_email(self):
        """Test login fails with non-existent email."""
        payload = {
            'email': 'nonexistent@example.com',
            'password': 'TestPass123!',
        }

        res = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_user_with_blank_password(self):
        """Test login fails with blank password."""
        payload = {
            'email': 'test@example.com',
            'password': '',
        }

        res = self.client.post(LOGIN_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh_success(self):
        """Test refreshing access token is successful."""
        user_details = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
        }
        create_user(**user_details)

        # Login to get tokens
        login_payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }
        login_res = self.client.post(LOGIN_URL, login_payload, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        refresh_token = login_res.data['tokens']['refresh']

        # Refresh token
        refresh_payload = {'refresh': refresh_token}
        res = self.client.post(TOKEN_REFRESH_URL, refresh_payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)

    def test_token_refresh_with_invalid_token(self):
        """Test token refresh fails with invalid token."""
        payload = {'refresh': 'invalid_token'}

        res = self.client.post(TOKEN_REFRESH_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for retrieving user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateAuthAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], self.user.email)
        self.assertEqual(res.data['username'], self.user.username)
        self.assertIn('account_id', res.data)

    def test_post_me_not_allowed(self):
        """Test POST is not allowed on the me endpoint."""
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for authenticated user."""
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name',
        }

        res = self.client.patch(ME_URL, payload, format='json')

        self.user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.first_name, payload['first_name'])
        self.assertEqual(self.user.last_name, payload['last_name'])

    def test_update_username(self):
        """Test updating username."""
        payload = {'username': 'newusername'}

        res = self.client.patch(ME_URL, payload, format='json')

        self.user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.username, payload['username'])

    def test_update_email_not_allowed(self):
        """Test updating email is not allowed."""
        payload = {'email': 'newemail@example.com'}

        res = self.client.patch(ME_URL, payload, format='json')

        self.user.refresh_from_db()
        # Email should remain unchanged
        self.assertEqual(self.user.email, 'test@example.com')

    def test_logout_success(self):
        """Test logout successfully blacklists refresh token."""
        # Login to get tokens
        login_payload = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
        }
        login_res = self.client.post(LOGIN_URL, login_payload, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        refresh_token = login_res.data['tokens']['refresh']

        # Logout
        logout_payload = {'refresh': refresh_token}
        res = self.client.post(LOGOUT_URL, logout_payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Try to use the refresh token
        refresh_res = self.client.post(
            TOKEN_REFRESH_URL,
            {'refresh': refresh_token},
            format='json'
        )

        # Should fail as token is blacklisted
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_invalid_token(self):
        """Test logout fails with invalid refresh token."""
        payload = {'refresh': 'invalid_token'}

        res = self.client.post(LOGOUT_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
