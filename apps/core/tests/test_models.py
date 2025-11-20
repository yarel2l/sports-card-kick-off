"""
Tests for SystemConfiguration model.
"""

from django.test import TestCase
from apps.core.models import SystemConfiguration


class SystemConfigurationModelTests(TestCase):
    """Test SystemConfiguration model."""

    def setUp(self):
        """Set up test configuration."""
        # Get or create singleton instance
        self.config = SystemConfiguration.get_solo()

    def test_singleton_instance(self):
        """Test that only one instance exists (Singleton pattern)."""
        config1 = SystemConfiguration.get_solo()
        config2 = SystemConfiguration.get_solo()

        self.assertEqual(config1.pk, config2.pk)
        self.assertEqual(SystemConfiguration.objects.count(), 1)

    def test_default_values(self):
        """Test default configuration values."""
        config = SystemConfiguration.get_solo()

        self.assertEqual(config.site_name, 'Sports Card KickOff')
        self.assertEqual(config.default_llm_model, 'gpt-4o-mini')
        self.assertEqual(config.llm_temperature, 0.0)
        self.assertEqual(config.llm_max_tokens, 4000)
        self.assertTrue(config.use_llm_by_default)
        self.assertTrue(config.use_traditional_fallback)
        self.assertEqual(config.scraping_timeout, 30000)
        self.assertEqual(config.max_retries, 3)
        self.assertTrue(config.enable_user_registration)
        self.assertTrue(config.enable_email_notifications)
        self.assertFalse(config.maintenance_mode)

    def test_has_openai_configured(self):
        """Test has_openai_configured property."""
        config = SystemConfiguration.get_solo()

        # Initially should be False
        self.assertFalse(config.has_openai_configured)

        # Set API key
        config.openai_api_key = 'sk-test-key-123'
        config.save()

        self.assertTrue(config.has_openai_configured)

    def test_has_anthropic_configured(self):
        """Test has_anthropic_configured property."""
        config = SystemConfiguration.get_solo()

        self.assertFalse(config.has_anthropic_configured)

        config.anthropic_api_key = 'sk-ant-test-key-123'
        config.save()

        self.assertTrue(config.has_anthropic_configured)

    def test_has_google_configured(self):
        """Test has_google_configured property."""
        config = SystemConfiguration.get_solo()

        self.assertFalse(config.has_google_configured)

        config.google_api_key = 'google-test-key-123'
        config.save()

        self.assertTrue(config.has_google_configured)

    def test_has_huggingface_configured(self):
        """Test has_huggingface_configured property."""
        config = SystemConfiguration.get_solo()

        self.assertFalse(config.has_huggingface_configured)

        config.huggingface_api_key = 'hf-test-key-123'
        config.save()

        self.assertTrue(config.has_huggingface_configured)

    def test_get_active_llm_provider_openai(self):
        """Test getting active LLM provider for OpenAI models."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'gpt-4o-mini'
        config.openai_api_key = 'sk-test-key'
        config.save()

        self.assertEqual(config.get_active_llm_provider(), 'openai')

    def test_get_active_llm_provider_anthropic(self):
        """Test getting active LLM provider for Anthropic models."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'claude-3-5-sonnet-20241022'
        config.anthropic_api_key = 'sk-ant-test-key'
        config.save()

        self.assertEqual(config.get_active_llm_provider(), 'anthropic')

    def test_get_active_llm_provider_google(self):
        """Test getting active LLM provider for Google models."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'gemini-1.5-pro'
        config.google_api_key = 'google-test-key'
        config.save()

        self.assertEqual(config.get_active_llm_provider(), 'google')

    def test_get_active_llm_provider_huggingface(self):
        """Test getting active LLM provider for HuggingFace models."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'meta-llama/Meta-Llama-3-70B-Instruct'
        config.huggingface_api_key = 'hf-test-key'
        config.save()

        self.assertEqual(config.get_active_llm_provider(), 'huggingface')

    def test_get_active_llm_provider_not_configured(self):
        """Test getting provider returns None when API key not configured."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'gpt-4o-mini'
        config.openai_api_key = ''
        config.save()

        self.assertIsNone(config.get_active_llm_provider())

    def test_get_scraping_config(self):
        """Test getting scraping configuration as dictionary."""
        config = SystemConfiguration.get_solo()
        config.default_llm_model = 'gpt-4o-mini'
        config.llm_temperature = 0.7
        config.llm_max_tokens = 2000
        config.use_llm_by_default = True
        config.use_traditional_fallback = False
        config.scraping_timeout = 45000
        config.max_retries = 5
        config.save()

        scraping_config = config.get_scraping_config()

        self.assertEqual(scraping_config['default_llm_model'], 'gpt-4o-mini')
        self.assertEqual(scraping_config['llm_temperature'], 0.7)
        self.assertEqual(scraping_config['llm_max_tokens'], 2000)
        self.assertTrue(scraping_config['use_llm_by_default'])
        self.assertFalse(scraping_config['use_traditional_fallback'])
        self.assertEqual(scraping_config['scraping_timeout'], 45000)
        self.assertEqual(scraping_config['max_retries'], 5)

    def test_update_branding_fields(self):
        """Test updating branding fields."""
        config = SystemConfiguration.get_solo()
        config.site_name = 'New Site Name'
        config.site_description = 'New description'
        config.apple_store_url = 'https://apps.apple.com/app/test/id123'
        config.google_play_url = 'https://play.google.com/store/apps/details?id=com.test'
        config.save()

        config.refresh_from_db()
        self.assertEqual(config.site_name, 'New Site Name')
        self.assertEqual(config.site_description, 'New description')
        self.assertEqual(config.apple_store_url, 'https://apps.apple.com/app/test/id123')
        self.assertEqual(config.google_play_url, 'https://play.google.com/store/apps/details?id=com.test')

    def test_update_contact_information(self):
        """Test updating contact information."""
        config = SystemConfiguration.get_solo()
        config.contact_email = 'new@example.com'
        config.support_email = 'support@example.com'
        config.contact_phone = '+1-555-1234'
        config.address = '123 Test St, City, State 12345'
        config.save()

        config.refresh_from_db()
        self.assertEqual(config.contact_email, 'new@example.com')
        self.assertEqual(config.support_email, 'support@example.com')
        self.assertEqual(config.contact_phone, '+1-555-1234')
        self.assertEqual(config.address, '123 Test St, City, State 12345')

    def test_update_social_media_links(self):
        """Test updating social media links."""
        config = SystemConfiguration.get_solo()
        config.facebook_url = 'https://facebook.com/testpage'
        config.twitter_url = 'https://twitter.com/testuser'
        config.instagram_url = 'https://instagram.com/testuser'
        config.linkedin_url = 'https://linkedin.com/company/test'
        config.save()

        config.refresh_from_db()
        self.assertEqual(config.facebook_url, 'https://facebook.com/testpage')
        self.assertEqual(config.twitter_url, 'https://twitter.com/testuser')
        self.assertEqual(config.instagram_url, 'https://instagram.com/testuser')
        self.assertEqual(config.linkedin_url, 'https://linkedin.com/company/test')

    def test_maintenance_mode(self):
        """Test maintenance mode configuration."""
        config = SystemConfiguration.get_solo()
        config.maintenance_mode = True
        config.maintenance_message = 'System is under maintenance'
        config.save()

        config.refresh_from_db()
        self.assertTrue(config.maintenance_mode)
        self.assertEqual(config.maintenance_message, 'System is under maintenance')

    def test_str_representation(self):
        """Test string representation of configuration."""
        config = SystemConfiguration.get_solo()
        str_repr = str(config)

        self.assertIn('System Configuration', str_repr)
        self.assertIn('Last updated:', str_repr)

    def test_llm_model_choices(self):
        """Test that LLM model choices are valid."""
        config = SystemConfiguration.get_solo()

        # Test OpenAI models
        config.default_llm_model = SystemConfiguration.LLMModel.GPT_4O_MINI
        config.save()
        self.assertEqual(config.default_llm_model, 'gpt-4o-mini')

        # Test Anthropic models
        config.default_llm_model = SystemConfiguration.LLMModel.CLAUDE_35_SONNET
        config.save()
        self.assertEqual(config.default_llm_model, 'claude-3-5-sonnet-20241022')

        # Test Google models
        config.default_llm_model = SystemConfiguration.LLMModel.GEMINI_15_PRO
        config.save()
        self.assertEqual(config.default_llm_model, 'gemini-1.5-pro')

    def test_updated_at_timestamp(self):
        """Test that updated_at timestamp is set automatically."""
        config = SystemConfiguration.get_solo()
        initial_updated_at = config.updated_at

        # Update configuration
        config.site_name = 'Updated Name'
        config.save()

        config.refresh_from_db()
        self.assertGreater(config.updated_at, initial_updated_at)
