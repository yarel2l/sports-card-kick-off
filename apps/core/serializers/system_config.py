"""
Serializers for System Configuration.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import SystemConfiguration


class SystemConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for System Configuration (read-only).
    """
    llm_provider = serializers.SerializerMethodField()
    has_openai_configured = serializers.BooleanField(read_only=True)
    has_anthropic_configured = serializers.BooleanField(read_only=True)
    has_google_configured = serializers.BooleanField(read_only=True)
    has_huggingface_configured = serializers.BooleanField(read_only=True)

    class Meta:
        model = SystemConfiguration
        fields = (
            # Branding & Identity
            'site_name',
            'site_description',
            'apple_store_url',
            'google_play_url',

            # Meta Tags & SEO
            'meta_keywords',
            'meta_author',

            # Contact Information
            'contact_email',
            'support_email',
            'contact_phone',
            'address',

            # Social Media Links
            'facebook_url',
            'twitter_url',
            'instagram_url',
            'linkedin_url',

            # API Keys (masked for security)
            'has_openai_configured',
            'has_anthropic_configured',
            'has_google_configured',
            'has_huggingface_configured',

            # LLM Configuration
            'default_llm_model',
            'llm_provider',
            'llm_temperature',
            'llm_max_tokens',
            'use_llm_by_default',
            'use_traditional_fallback',

            # Scraping Configuration
            'scraping_timeout',
            'max_retries',

            # Feature Flags
            'enable_user_registration',
            'enable_email_notifications',
            'maintenance_mode',
            'maintenance_message',

            # Analytics & Tracking
            'google_analytics_id',
            'google_tag_manager_id',

            # Timestamps
            'updated_at',
        )
        read_only_fields = ('updated_at', 'has_openai_configured', 'has_anthropic_configured',
                           'has_google_configured', 'has_huggingface_configured')

    def get_llm_provider(self, obj):
        """Get the active LLM provider based on configured model."""
        return obj.get_active_llm_provider()


class SystemConfigurationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating System Configuration.
    Includes API keys for updates.
    """

    class Meta:
        model = SystemConfiguration
        fields = (
            # Branding & Identity
            'site_name',
            'site_description',
            'apple_store_url',
            'google_play_url',

            # Meta Tags & SEO
            'meta_keywords',
            'meta_author',

            # Contact Information
            'contact_email',
            'support_email',
            'contact_phone',
            'address',

            # Social Media Links
            'facebook_url',
            'twitter_url',
            'instagram_url',
            'linkedin_url',

            # API Keys
            'openai_api_key',
            'openai_org_id',
            'anthropic_api_key',
            'google_api_key',
            'huggingface_api_key',

            # LLM Configuration
            'default_llm_model',
            'llm_temperature',
            'llm_max_tokens',
            'use_llm_by_default',
            'use_traditional_fallback',

            # Scraping Configuration
            'scraping_timeout',
            'max_retries',

            # Feature Flags
            'enable_user_registration',
            'enable_email_notifications',
            'maintenance_mode',
            'maintenance_message',

            # Analytics & Tracking
            'google_analytics_id',
            'google_tag_manager_id',
        )
        extra_kwargs = {
            # Make all fields optional since this is a singleton update serializer
            'site_name': {'required': False},
            'site_description': {'required': False, 'allow_blank': True},
            'apple_store_url': {'required': False, 'allow_blank': True},
            'google_play_url': {'required': False, 'allow_blank': True},
            'meta_keywords': {'required': False, 'allow_blank': True},
            'meta_author': {'required': False, 'allow_blank': True},
            'contact_email': {'required': False, 'allow_blank': True},
            'support_email': {'required': False, 'allow_blank': True},
            'contact_phone': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'facebook_url': {'required': False, 'allow_blank': True},
            'twitter_url': {'required': False, 'allow_blank': True},
            'instagram_url': {'required': False, 'allow_blank': True},
            'linkedin_url': {'required': False, 'allow_blank': True},
            'default_llm_model': {'required': False},
            'llm_temperature': {'required': False},
            'llm_max_tokens': {'required': False},
            'use_llm_by_default': {'required': False},
            'use_traditional_fallback': {'required': False},
            'scraping_timeout': {'required': False},
            'max_retries': {'required': False},
            'enable_user_registration': {'required': False},
            'enable_email_notifications': {'required': False},
            'maintenance_mode': {'required': False},
            'maintenance_message': {'required': False, 'allow_blank': True},
            'google_analytics_id': {'required': False, 'allow_blank': True},
            'google_tag_manager_id': {'required': False, 'allow_blank': True},

            # Sensitive fields - write only
            'openai_api_key': {'write_only': True, 'required': False, 'allow_blank': True},
            'openai_org_id': {'write_only': True, 'required': False, 'allow_blank': True},
            'anthropic_api_key': {'write_only': True, 'required': False, 'allow_blank': True},
            'google_api_key': {'write_only': True, 'required': False, 'allow_blank': True},
            'huggingface_api_key': {'write_only': True, 'required': False, 'allow_blank': True},
        }

    def validate_llm_temperature(self, value):
        """Validate LLM temperature is between 0 and 2."""
        if not (0 <= value <= 2):
            raise serializers.ValidationError(
                _('Temperature must be between 0 and 2.')
            )
        return value

    def validate_llm_max_tokens(self, value):
        """Validate max tokens is reasonable."""
        if value < 1 or value > 100000:
            raise serializers.ValidationError(
                _('Max tokens must be between 1 and 100000.')
            )
        return value

    def validate_scraping_timeout(self, value):
        """Validate scraping timeout in milliseconds."""
        # Value is in milliseconds (1 to 300000 ms = 1 to 300 seconds)
        if value < 1000 or value > 300000:
            raise serializers.ValidationError(
                _('Timeout must be between 1000 and 300000 milliseconds (1 to 300 seconds).')
            )
        return value

    def validate_max_retries(self, value):
        """Validate max retries."""
        if value < 0 or value > 10:
            raise serializers.ValidationError(
                _('Max retries must be between 0 and 10.')
            )
        return value
