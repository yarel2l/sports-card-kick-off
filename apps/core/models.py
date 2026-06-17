"""
Core System Configuration Models.

Uses django-solo to ensure single instance configuration.
"""

from django.db import models
from django.core.validators import URLValidator, EmailValidator
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel

from .fields import EncryptedCharField


class SystemConfiguration(SingletonModel):
    """
    Global system configuration (Singleton).

    This model uses django-solo to ensure only one configuration instance exists.
    Stores all system-wide settings including API keys, branding, and contact info.
    """

    class LLMModel(models.TextChoices):
        """Available LLM models for scraping."""
        # OpenAI Models
        GPT_4O_MINI = 'gpt-4o-mini', _('GPT-4o Mini (Recommended)')
        GPT_4O = 'gpt-4o', _('GPT-4o (High Precision)')
        GPT_4_TURBO = 'gpt-4-turbo', _('GPT-4 Turbo')

        # Anthropic Models
        CLAUDE_35_SONNET = 'claude-3-5-sonnet-20241022', _('Claude 3.5 Sonnet')
        CLAUDE_3_OPUS = 'claude-3-opus-20240229', _('Claude 3 Opus')
        CLAUDE_3_HAIKU = 'claude-3-haiku-20240307', _('Claude 3 Haiku')

        # Google Models
        GEMINI_15_PRO = 'gemini-1.5-pro', _('Gemini 1.5 Pro')
        GEMINI_15_FLASH = 'gemini-1.5-flash', _('Gemini 1.5 Flash (Fast & Cheap)')
        GEMINI_10_PRO = 'gemini-1.0-pro', _('Gemini 1.0 Pro')

        # HuggingFace Models (Open Source)
        LLAMA_3_70B = 'meta-llama/Meta-Llama-3-70B-Instruct', _('Llama 3 70B')
        MISTRAL_7B = 'mistralai/Mistral-7B-Instruct-v0.2', _('Mistral 7B')

    # ========================================================================
    # Branding & Identity
    # ========================================================================

    site_name = models.CharField(
        max_length=100,
        default='Sports Card KickOff',
        verbose_name=_('Site Name'),
        help_text=_('Name of the application')
    )

    site_description = models.TextField(
        default=_('Professional sports card price aggregator and market analysis platform'),
        verbose_name=_('Site Description'),
        help_text=_('Brief description of the platform')
    )

    apple_store_url = models.URLField(
        blank=True,
        verbose_name=_('Apple App Store URL'),
        help_text=_('URL to the iOS app in Apple App Store'),
        validators=[URLValidator()]
    )

    google_play_url = models.URLField(
        blank=True,
        verbose_name=_('Google Play Store URL'),
        help_text=_('URL to the Android app in Google Play Store'),
        validators=[URLValidator()]
    )

    # ========================================================================
    # Meta Tags & SEO
    # ========================================================================

    meta_keywords = models.CharField(
        max_length=255,
        default='sports cards, PSA, grading, card prices, market analysis',
        verbose_name=_('Meta Keywords'),
        help_text=_('SEO keywords (comma separated)')
    )

    meta_author = models.CharField(
        max_length=100,
        default='Sports Card KickOff Team',
        verbose_name=_('Meta Author')
    )

    # ========================================================================
    # Contact Information
    # ========================================================================

    contact_email = models.EmailField(
        default='contact@sportscardkickoff.com',
        verbose_name=_('Contact Email'),
        validators=[EmailValidator()]
    )

    support_email = models.EmailField(
        default='support@sportscardkickoff.com',
        verbose_name=_('Support Email'),
        validators=[EmailValidator()]
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Contact Phone')
    )

    address = models.TextField(
        blank=True,
        verbose_name=_('Physical Address')
    )

    # ========================================================================
    # Social Media Links
    # ========================================================================

    twitter_url = models.URLField(
        blank=True,
        verbose_name=_('Twitter/X URL'),
        validators=[URLValidator()]
    )

    facebook_url = models.URLField(
        blank=True,
        verbose_name=_('Facebook URL'),
        validators=[URLValidator()]
    )

    instagram_url = models.URLField(
        blank=True,
        verbose_name=_('Instagram URL'),
        validators=[URLValidator()]
    )

    linkedin_url = models.URLField(
        blank=True,
        verbose_name=_('LinkedIn URL'),
        validators=[URLValidator()]
    )

    # ========================================================================
    # API Keys & External Services
    # ========================================================================

    # NOTE: these are encrypted at rest via EncryptedCharField. Application code
    # still reads/writes plain strings; only the database holds ciphertext.
    openai_api_key = EncryptedCharField(
        blank=True,
        verbose_name=_('OpenAI API Key'),
        help_text=_('API key for OpenAI/ChatGPT (for LLM-based scraping)')
    )

    openai_org_id = EncryptedCharField(
        blank=True,
        verbose_name=_('OpenAI Organization ID'),
        help_text=_('Optional: OpenAI organization ID')
    )

    anthropic_api_key = EncryptedCharField(
        blank=True,
        verbose_name=_('Anthropic API Key'),
        help_text=_('API key for Claude (alternative LLM)')
    )

    google_api_key = EncryptedCharField(
        blank=True,
        verbose_name=_('Google AI API Key'),
        help_text=_('API key for Google Gemini models')
    )

    huggingface_api_key = EncryptedCharField(
        blank=True,
        verbose_name=_('HuggingFace API Key'),
        help_text=_('API key for HuggingFace Inference API (optional)')
    )

    # ========================================================================
    # Scraping Configuration
    # ========================================================================

    default_llm_model = models.CharField(
        max_length=100,
        choices=LLMModel.choices,
        default=LLMModel.GPT_4O_MINI,
        verbose_name=_('Default LLM Model'),
        help_text=_('Default model for LLM-based scraping')
    )

    llm_temperature = models.FloatField(
        default=0.0,
        verbose_name=_('LLM Temperature'),
        help_text=_('Temperature for LLM (0 = deterministic, 1 = creative)')
    )

    llm_max_tokens = models.IntegerField(
        default=4000,
        verbose_name=_('LLM Max Tokens'),
        help_text=_('Maximum tokens for LLM output')
    )

    use_llm_by_default = models.BooleanField(
        default=True,
        verbose_name=_('Use LLM by Default'),
        help_text=_('Enable LLM extraction by default for scraping')
    )

    use_traditional_fallback = models.BooleanField(
        default=True,
        verbose_name=_('Use Traditional Fallback'),
        help_text=_('Fallback to BeautifulSoup if LLM fails')
    )

    scraping_timeout = models.IntegerField(
        default=30000,
        verbose_name=_('Scraping Timeout (ms)'),
        help_text=_('Timeout in milliseconds for scraping requests')
    )

    max_retries = models.IntegerField(
        default=3,
        verbose_name=_('Max Retries'),
        help_text=_('Maximum retry attempts for failed scraping')
    )

    # ========================================================================
    # Feature Flags
    # ========================================================================

    enable_user_registration = models.BooleanField(
        default=True,
        verbose_name=_('Enable User Registration'),
        help_text=_('Allow new users to register')
    )

    enable_email_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Enable Email Notifications'),
        help_text=_('Send email notifications to users')
    )

    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name=_('Maintenance Mode'),
        help_text=_('Enable maintenance mode (site unavailable)')
    )

    maintenance_message = models.TextField(
        default=_('Site is currently under maintenance. Please check back soon.'),
        verbose_name=_('Maintenance Message'),
        help_text=_('Message to show during maintenance mode')
    )

    # ========================================================================
    # Analytics & Tracking
    # ========================================================================

    google_analytics_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Google Analytics ID'),
        help_text=_('GA tracking ID (e.g., G-XXXXXXXXXX)')
    )

    google_tag_manager_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Google Tag Manager ID'),
        help_text=_('GTM container ID (e.g., GTM-XXXXXXX)')
    )

    # ========================================================================
    # Timestamps
    # ========================================================================

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Updated')
    )

    class Meta:
        verbose_name = _('System Configuration')
        verbose_name_plural = _('System Configuration')

    def __str__(self):
        return f'System Configuration (Last updated: {self.updated_at})'

    @property
    def has_openai_configured(self):
        """Check if OpenAI API is configured."""
        return bool(self.openai_api_key)

    @property
    def has_anthropic_configured(self):
        """Check if Anthropic API is configured."""
        return bool(self.anthropic_api_key)

    @property
    def has_google_configured(self):
        """Check if Google AI API is configured."""
        return bool(self.google_api_key)

    @property
    def has_huggingface_configured(self):
        """Check if HuggingFace API is configured."""
        return bool(self.huggingface_api_key)

    def get_active_llm_provider(self):
        """Get the active LLM provider based on configuration."""
        model_lower = self.default_llm_model.lower()

        if 'claude' in model_lower:
            return 'anthropic' if self.has_anthropic_configured else None
        elif 'gpt' in model_lower:
            return 'openai' if self.has_openai_configured else None
        elif 'gemini' in model_lower:
            return 'google' if self.has_google_configured else None
        elif 'llama' in model_lower or 'mistral' in model_lower:
            return 'huggingface' if self.has_huggingface_configured else None

        return None

    def get_scraping_config(self):
        """
        Get scraping configuration as a dictionary.

        Returns:
            dict: Scraping configuration parameters
        """
        return {
            'default_llm_model': self.default_llm_model,
            'llm_temperature': self.llm_temperature,
            'llm_max_tokens': self.llm_max_tokens,
            'use_llm_by_default': self.use_llm_by_default,
            'use_traditional_fallback': self.use_traditional_fallback,
            'scraping_timeout': self.scraping_timeout,
            'max_retries': self.max_retries,
        }
