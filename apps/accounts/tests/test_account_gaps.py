"""
Tests for the account gaps closed from the original analysis:
email verification and account deletion (GDPR).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


def _uid_token(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


class EmailVerificationTests(APITestCase):
    def test_registration_sends_verification_email(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'new@example.com', 'username': 'new',
            'password': 'StrongPass123', 'password_confirm': 'StrongPass123',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verify', mail.outbox[0].subject.lower())

        user = User.objects.get(email='new@example.com')
        self.assertFalse(user.email_verified)

    def test_verify_email_with_valid_token(self):
        user = User.objects.create_user(email='u@example.com', username='u', password='pass12345')
        uid, token = _uid_token(user)

        resp = self.client.post(
            reverse('accounts:verify_email'), {'uid': uid, 'token': token}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_verify_email_via_link_get(self):
        user = User.objects.create_user(email='u2@example.com', username='u2', password='pass12345')
        uid, token = _uid_token(user)
        resp = self.client.get(reverse('accounts:verify_email_link', args=[uid, token]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_verify_email_invalid_token(self):
        user = User.objects.create_user(email='u3@example.com', username='u3', password='pass12345')
        uid, _ = _uid_token(user)
        resp = self.client.post(
            reverse('accounts:verify_email'), {'uid': uid, 'token': 'bad-token'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    @override_settings(REQUIRE_EMAIL_VERIFICATION=True)
    def test_login_blocked_until_verified_when_required(self):
        user = User.objects.create_user(
            email='gate@example.com', username='gate', password='StrongPass123'
        )
        login = self.client.post(reverse('accounts:login'), {
            'email': 'gate@example.com', 'password': 'StrongPass123',
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.save(update_fields=['email_verified'])
        login_ok = self.client.post(reverse('accounts:login'), {
            'email': 'gate@example.com', 'password': 'StrongPass123',
        }, format='json')
        self.assertEqual(login_ok.status_code, status.HTTP_200_OK)


class AccountDeletionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com', username='owner', password='StrongPass123'
        )
        self.url = reverse('accounts:delete_account')

    def test_requires_authentication(self):
        resp = self.client.delete(self.url, {'password': 'StrongPass123'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_with_correct_password(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.delete(self.url, {'password': 'StrongPass123'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_with_wrong_password(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.delete(self.url, {'password': 'nope'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_without_password(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.delete(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
