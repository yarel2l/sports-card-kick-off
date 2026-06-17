from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

# Tight per-scope limits for the test. DRF binds THROTTLE_RATES as a class
# attribute at import time, so override_settings does not reach it; patch the
# shared rates dict directly instead. An isolated in-memory cache keeps throttle
# state from leaking across tests.
_TIGHT_RATES = {
    'auth_login': '1/min',
    'auth_register': '1/min',
    'auth_password_reset': '1/min',
}
_LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'throttle-tests',
    }
}


@override_settings(CACHES=_LOCMEM_CACHE)
class AuthThrottlingTests(APITestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, _TIGHT_RATES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_login_is_rate_limited(self):
        url = reverse('accounts:login')
        payload = {'email': 'nobody@example.com', 'password': 'whatever123'}

        first = self.client.post(url, payload, format='json')
        self.assertNotEqual(first.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        second = self.client.post(url, payload, format='json')
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_password_reset_is_rate_limited(self):
        url = reverse('accounts:password_reset')
        payload = {'email': 'nobody@example.com'}

        self.client.post(url, payload, format='json')
        throttled = self.client.post(url, payload, format='json')
        self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_register_is_rate_limited(self):
        url = reverse('accounts:register')
        payload = {
            'email': 'a@example.com', 'username': 'a',
            'password': 'StrongPass123', 'password_confirm': 'StrongPass123',
        }
        self.client.post(url, payload, format='json')
        throttled = self.client.post(
            url, {**payload, 'email': 'b@example.com', 'username': 'b'}, format='json'
        )
        self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_not_throttled_under_limit(self):
        # Sanity: a single request is always allowed.
        url = reverse('accounts:login')
        resp = self.client.post(
            url, {'email': 'x@example.com', 'password': 'whatever123'}, format='json'
        )
        self.assertNotEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
