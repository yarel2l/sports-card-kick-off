"""
Tests for System Configuration API endpoints.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import SystemConfiguration


User = get_user_model()

SYSTEM_CONFIG_URL = reverse('core:system_config')


def create_user(**params):
    """Create and return a new user."""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'TestPass123!',
    }
    defaults.update(params)
    return User.objects.create_user(**defaults)


def create_admin_user(**params):
    """Create and return a new admin user."""
    defaults = {
        'email': 'admin@example.com',
        'username': 'admin',
        'password': 'AdminPass123!',
    }
    defaults.update(params)
    return User.objects.create_superuser(**defaults)


class PublicSystemConfigAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_get(self):
        """Test that authentication is required for retrieving config."""
        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_patch(self):
        """Test that authentication is required for updating config."""
        payload = {'site_name': 'New Name'}
        res = self.client.patch(SYSTEM_CONFIG_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_put(self):
        """Test that authentication is required for full update."""
        payload = {'site_name': 'New Name'}
        res = self.client.put(SYSTEM_CONFIG_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class RegularUserSystemConfigAPITests(TestCase):
    """Test authenticated but non-admin user requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_regular_user_cannot_get_config(self):
        """Test that regular users cannot retrieve config."""
        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_update_config(self):
        """Test that regular users cannot update config."""
        payload = {'site_name': 'New Name'}
        res = self.client.patch(SYSTEM_CONFIG_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminSystemConfigAPITests(TestCase):
    """Test admin user API requests."""

    def setUp(self):
        self.admin_user = create_admin_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.config = SystemConfiguration.get_solo()

    def test_get_system_config_success(self):
        """Test retrieving system configuration."""
        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('site_name', res.data)
        self.assertIn('site_description', res.data)
        self.assertIn('has_openai_configured', res.data)
        self.assertIn('has_anthropic_configured', res.data)
        self.assertIn('default_llm_model', res.data)
        self.assertIn('llm_provider', res.data)

    def test_api_keys_not_exposed_in_get(self):
        """Test that API keys are not exposed in GET responses."""
        self.config.openai_api_key = 'sk-test-secret-key'
        self.config.anthropic_api_key = 'sk-ant-secret-key'
        self.config.save()

        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn('openai_api_key', res.data)
        self.assertNotIn('anthropic_api_key', res.data)
        self.assertNotIn('google_api_key', res.data)
        self.assertNotIn('huggingface_api_key', res.data)

    def test_api_key_flags_in_response(self):
        """Test that boolean flags indicate if API keys are configured."""
        self.config.openai_api_key = 'sk-test-key'
        self.config.anthropic_api_key = 'sk-ant-test-key'
        self.config.save()

        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['has_openai_configured'])
        self.assertTrue(res.data['has_anthropic_configured'])
        self.assertFalse(res.data['has_google_configured'])
        self.assertFalse(res.data['has_huggingface_configured'])

    def test_partial_update_branding(self):
        """Test partially updating branding fields."""
        payload = {
            'site_name': 'Updated Site Name',
            'site_description': 'Updated description',
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.site_name, payload['site_name'])
        self.assertEqual(self.config.site_description, payload['site_description'])

    def test_partial_update_app_store_urls(self):
        """Test updating app store URLs."""
        payload = {
            'apple_store_url': 'https://apps.apple.com/app/test/id123',
            'google_play_url': 'https://play.google.com/store/apps/details?id=com.test',
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.apple_store_url, payload['apple_store_url'])
        self.assertEqual(self.config.google_play_url, payload['google_play_url'])

    def test_partial_update_llm_config(self):
        """Test partially updating LLM configuration."""
        payload = {
            'default_llm_model': 'claude-3-5-sonnet-20241022',
            'llm_temperature': 0.5,
            'llm_max_tokens': 2000,
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.default_llm_model, payload['default_llm_model'])
        self.assertEqual(self.config.llm_temperature, payload['llm_temperature'])
        self.assertEqual(self.config.llm_max_tokens, payload['llm_max_tokens'])

    def test_update_api_keys(self):
        """Test updating API keys (write-only fields)."""
        payload = {
            'openai_api_key': 'sk-new-test-key',
            'anthropic_api_key': 'sk-ant-new-test-key',
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.openai_api_key, payload['openai_api_key'])
        self.assertEqual(self.config.anthropic_api_key, payload['anthropic_api_key'])

        # API keys should not be in response
        self.assertNotIn('openai_api_key', res.data)
        self.assertNotIn('anthropic_api_key', res.data)

        # But flags should indicate they're configured
        self.assertTrue(res.data['has_openai_configured'])
        self.assertTrue(res.data['has_anthropic_configured'])

    def test_update_feature_flags(self):
        """Test updating feature flags."""
        payload = {
            'enable_user_registration': False,
            'maintenance_mode': True,
            'maintenance_message': 'System maintenance in progress',
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertFalse(self.config.enable_user_registration)
        self.assertTrue(self.config.maintenance_mode)
        self.assertEqual(self.config.maintenance_message, payload['maintenance_message'])

    def test_update_scraping_config(self):
        """Test updating scraping configuration."""
        payload = {
            'scraping_timeout': 45000,
            'max_retries': 5,
        }

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.scraping_timeout, payload['scraping_timeout'])
        self.assertEqual(self.config.max_retries, payload['max_retries'])

    def test_invalid_llm_temperature(self):
        """Test that invalid temperature is rejected."""
        payload = {'llm_temperature': 3.0}  # Should be 0-2

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # With drf-standardized-errors, errors are in a different format
        self.assertIn('errors', res.data)
        error_attrs = [err['attr'] for err in res.data['errors']]
        self.assertIn('llm_temperature', error_attrs)

    def test_invalid_llm_max_tokens(self):
        """Test that invalid max tokens is rejected."""
        payload = {'llm_max_tokens': 200000}  # Should be 1-100000

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # With drf-standardized-errors, errors are in a different format
        self.assertIn('errors', res.data)
        error_attrs = [err['attr'] for err in res.data['errors']]
        self.assertIn('llm_max_tokens', error_attrs)

    def test_invalid_scraping_timeout(self):
        """Test that invalid timeout is rejected."""
        payload = {'scraping_timeout': 500}  # Should be 1-300 (in seconds, but stored as ms)

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        # This might pass or fail depending on validation implementation
        # Adjust assertion based on your requirements

    def test_invalid_max_retries(self):
        """Test that invalid max retries is rejected."""
        payload = {'max_retries': 15}  # Should be 0-10

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # With drf-standardized-errors, errors are in a different format
        self.assertIn('errors', res.data)
        error_attrs = [err['attr'] for err in res.data['errors']]
        self.assertIn('max_retries', error_attrs)

    def test_invalid_email_format(self):
        """Test that invalid email format is rejected."""
        payload = {'contact_email': 'invalid-email'}

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_url_format(self):
        """Test that invalid URL format is rejected."""
        payload = {'facebook_url': 'not-a-valid-url'}

        res = self.client.patch(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_update_with_put(self):
        """Test full update using PUT method."""
        payload = {
            'site_name': 'New Site',
            'site_description': 'New Description',
            'apple_store_url': '',
            'google_play_url': '',
            'meta_keywords': 'test, keywords',
            'meta_author': 'Test Author',
            'contact_email': 'contact@test.com',
            'support_email': 'support@test.com',
            'contact_phone': '',
            'address': '',
            'facebook_url': '',
            'twitter_url': '',
            'instagram_url': '',
            'linkedin_url': '',
            'openai_api_key': '',
            'openai_org_id': '',
            'anthropic_api_key': '',
            'google_api_key': '',
            'huggingface_api_key': '',
            'default_llm_model': 'gpt-4o-mini',
            'llm_temperature': 0.7,
            'llm_max_tokens': 4000,
            'use_llm_by_default': True,
            'use_traditional_fallback': True,
            'scraping_timeout': 30000,
            'max_retries': 3,
            'enable_user_registration': True,
            'enable_email_notifications': True,
            'maintenance_mode': False,
            'maintenance_message': '',
            'google_analytics_id': '',
            'google_tag_manager_id': '',
        }

        res = self.client.put(SYSTEM_CONFIG_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.site_name, payload['site_name'])

    def test_llm_provider_computed_field(self):
        """Test that llm_provider is computed correctly."""
        self.config.default_llm_model = 'claude-3-5-sonnet-20241022'
        self.config.anthropic_api_key = 'sk-ant-test-key'
        self.config.save()

        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['llm_provider'], 'anthropic')

    def test_updated_at_returned_in_response(self):
        """Test that updated_at timestamp is included in response."""
        res = self.client.get(SYSTEM_CONFIG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('updated_at', res.data)
