"""
Admin configuration for Core app.
"""

from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import SystemConfiguration


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(SingletonModelAdmin):
    """
    Admin interface for System Configuration (Singleton).

    Uses django-solo's SingletonModelAdmin to ensure only one instance.
    """

    fieldsets = (
        ('Branding & Identity', {
            'fields': (
                'site_name',
                'site_description',
                'apple_store_url',
                'google_play_url',
            ),
            'description': 'Configure site branding and identity'
        }),
        ('SEO & Meta Tags', {
            'fields': (
                'meta_keywords',
                'meta_author',
            ),
            'description': 'SEO and social media meta tags'
        }),
        ('Contact Information', {
            'fields': (
                'contact_email',
                'support_email',
                'contact_phone',
                'address',
            ),
            'description': 'Contact details for the organization'
        }),
        ('Social Media', {
            'fields': (
                'twitter_url',
                'facebook_url',
                'instagram_url',
                'linkedin_url',
            ),
            'description': 'Social media profile links',
            'classes': ('collapse',),
        }),
        ('API Keys & Services', {
            'fields': (
                'openai_api_key',
                'openai_org_id',
                'anthropic_api_key',
                'google_api_key',
                'huggingface_api_key',
            ),
            'description': '⚠️ Sensitive: API keys for external services',
            'classes': ('collapse',),
        }),
        ('Scraping Configuration', {
            'fields': (
                'default_llm_model',
                'llm_temperature',
                'llm_max_tokens',
                'use_llm_by_default',
                'use_traditional_fallback',
                'scraping_timeout',
                'max_retries',
            ),
            'description': 'Configure scraping and LLM extraction behavior'
        }),
        ('Feature Flags', {
            'fields': (
                'enable_user_registration',
                'enable_email_notifications',
                'maintenance_mode',
                'maintenance_message',
            ),
            'description': 'Enable/disable features and maintenance mode'
        }),
        ('Analytics & Tracking', {
            'fields': (
                'google_analytics_id',
                'google_tag_manager_id',
            ),
            'description': 'Analytics and tracking configuration',
            'classes': ('collapse',),
        }),
        ('System Info', {
            'fields': (
                'updated_at',
            ),
            'description': 'Read-only system information'
        }),
    )

    readonly_fields = ('updated_at',)

    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }
