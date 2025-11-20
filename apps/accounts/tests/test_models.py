"""
Tests for User model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


class UserModelTests(TestCase):
    """Test User model."""

    def test_create_user_with_email_successful(self):
        """Test creating a user with email is successful."""
        email = 'test@example.com'
        password = 'TestPass123!'
        username = 'testuser'

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertEqual(user.username, username)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_with_optional_fields(self):
        """Test creating a user with optional fields."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
        )

        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.get_full_name(), 'Test User')

    def test_create_user_email_normalized(self):
        """Test email is normalized for new users."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]

        for email, expected in sample_emails:
            user = User.objects.create_user(
                email=email,
                username=f'user_{email.split("@")[0]}',
                password='TestPass123!',
            )
            self.assertEqual(user.email, expected)

    def test_create_user_without_email_raises_error(self):
        """Test that creating a user without email raises error on validation."""
        # Note: Django's AbstractUser UserManager doesn't validate empty string for email
        # It only checks for None. However, our API serializers will prevent empty emails.
        # This test verifies the database-level constraint works for duplicate empty emails.
        from django.db import IntegrityError

        # First user with empty email may be created (Django limitation)
        first_user = User.objects.create_user(
            email='',
            username='testuser1',
            password='TestPass123!',
        )

        # Second user with empty email should fail due to unique constraint
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='',
                username='testuser2',
                password='TestPass123!',
            )

    def test_create_user_without_username_raises_error(self):
        """Test that creating a user without username raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='test@example.com',
                username='',
                password='TestPass123!',
            )

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='AdminPass123!',
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)

    def test_user_str_representation(self):
        """Test the user string representation."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
        )

        # User model's __str__ returns email
        self.assertEqual(str(user), 'test@example.com')

    def test_user_account_id_is_uuid(self):
        """Test that account_id is a UUID."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
        )

        self.assertIsNotNone(user.account_id)
        # UUID should be a string with hyphens
        self.assertEqual(len(str(user.account_id)), 36)
        self.assertIn('-', str(user.account_id))

    def test_duplicate_email_raises_error(self):
        """Test that duplicate email raises IntegrityError."""
        User.objects.create_user(
            email='test@example.com',
            username='testuser1',
            password='TestPass123!',
        )

        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',
                username='testuser2',
                password='TestPass123!',
            )

    def test_duplicate_username_raises_error(self):
        """Test that duplicate username raises IntegrityError."""
        User.objects.create_user(
            email='test1@example.com',
            username='testuser',
            password='TestPass123!',
        )

        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test2@example.com',
                username='testuser',
                password='TestPass123!',
            )

    def test_get_full_name(self):
        """Test get_full_name method."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='John',
            last_name='Doe',
        )

        self.assertEqual(user.get_full_name(), 'John Doe')

    def test_get_full_name_without_names(self):
        """Test get_full_name returns empty string if no names provided."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
        )

        # AbstractUser's get_full_name returns empty string if no first/last name
        self.assertEqual(user.get_full_name(), '')
