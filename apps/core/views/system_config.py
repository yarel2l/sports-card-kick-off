"""
System Configuration Views.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from ..models import SystemConfiguration
from ..serializers import SystemConfigurationSerializer, SystemConfigurationUpdateSerializer


class SystemConfigurationView(APIView):
    """
    System Configuration endpoint.

    GET: Retrieve current system configuration
    PATCH: Partially update configuration
    PUT: Fully update configuration
    """
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['System Configuration'],
        summary="Get system configuration",
        description="""
        Retrieve current system configuration settings.

        **This endpoint returns:**
        - Branding and identity information
        - Meta tags and SEO settings
        - Contact information
        - Social media links
        - LLM configuration (without exposing API keys)
        - Scraping configuration
        - Feature flags status
        - Analytics tracking IDs

        **Security:**
        - API keys are never exposed in GET responses
        - Only boolean flags indicate if keys are configured
        - Requires admin authentication

        **Use Cases:**
        - Display current system settings in admin panel
        - Check which LLM provider is configured
        - Verify feature flags status
        - Audit system configuration

        **Authorization Required:**
        Must be authenticated as admin/staff user.
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        examples=[
            OpenApiExample(
                name='System Configuration Response',
                value={
                    'site_name': 'Sports Card Kickoff',
                    'site_description': 'Your premier sports card marketplace',
                    'apple_store_url': 'https://apps.apple.com/app/sportscards/id123456789',
                    'google_play_url': 'https://play.google.com/store/apps/details?id=com.sportscards',
                    'meta_keywords': 'sports cards, trading cards, collectibles',
                    'meta_author': 'Sports Card Kickoff Team',
                    'contact_email': 'support@sportscards.com',
                    'contact_phone': '+1-555-0123',
                    'facebook_url': 'https://facebook.com/sportscards',
                    'twitter_url': 'https://twitter.com/sportscards',
                    'has_openai_configured': True,
                    'has_anthropic_configured': True,
                    'has_google_configured': False,
                    'has_huggingface_configured': False,
                    'default_llm_model': 'gpt-4o-mini',
                    'llm_provider': 'openai',
                    'llm_temperature': 0.7,
                    'llm_max_tokens': 2000,
                    'use_llm_by_default': True,
                    'scraping_timeout': 30,
                    'max_retries': 3,
                    'enable_caching': True,
                    'cache_ttl': 3600,
                    'enable_rate_limiting': True,
                    'rate_limit_per_hour': 1000,
                    'maintenance_mode': False,
                    'updated_at': '2024-01-15T10:30:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
        responses={
            200: SystemConfigurationSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            403: OpenApiResponse(
                description="You do not have permission to access system configuration"
            )
        }
    )
    def get(self, request):
        """Get current system configuration."""
        config = SystemConfiguration.get_solo()
        serializer = SystemConfigurationSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['System Configuration'],
        summary="Update system configuration",
        description="""
        Update system configuration settings (partial update).

        **Updatable Settings:**

        **Branding & Identity:**
        - site_name, site_description, apple_store_url, google_play_url

        **Meta Tags & SEO:**
        - meta_keywords, meta_author

        **Contact Information:**
        - contact_email, contact_phone, contact_address

        **Social Media:**
        - facebook_url, twitter_url, instagram_url, linkedin_url, youtube_url

        **API Keys (sensitive):**
        - openai_api_key, openai_org_id
        - anthropic_api_key
        - google_api_key
        - huggingface_api_key

        **LLM Configuration:**
        - default_llm_model (from available choices)
        - llm_temperature (0.0 - 2.0)
        - llm_max_tokens (1 - 100000)
        - use_llm_by_default (boolean)

        **Scraping Configuration:**
        - scraping_timeout (1-300 seconds)
        - max_retries (0-10)
        - retry_delay (seconds)
        - user_agent (string)
        - enable_proxy, proxy_url

        **Feature Flags:**
        - enable_caching, cache_ttl
        - enable_rate_limiting, rate_limit_per_hour
        - enable_email_notifications
        - enable_sms_notifications
        - maintenance_mode

        **Analytics:**
        - google_analytics_id
        - facebook_pixel_id

        **Security Notes:**
        - API keys are write-only and never returned in responses
        - Changes take effect immediately
        - Configuration is singleton (only one instance exists)
        - All settings are optional for PATCH requests

        **Validation:**
        - Temperature must be between 0 and 2
        - Max tokens between 1 and 100000
        - Timeout between 1 and 300 seconds
        - Retries between 0 and 10
        - Email addresses must be valid format

        **Authorization Required:**
        Must be authenticated as admin/staff user.
        Include the access token in the Authorization header:
        `Authorization: Bearer <access_token>`
        """,
        request=SystemConfigurationUpdateSerializer,
        examples=[
            OpenApiExample(
                name='Update Branding',
                value={
                    'site_name': 'Sports Card Kickoff Pro',
                    'site_description': 'Premium sports card marketplace',
                    'apple_store_url': 'https://apps.apple.com/app/sportscards-pro/id987654321',
                    'google_play_url': 'https://play.google.com/store/apps/details?id=com.sportscards.pro'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Update LLM Configuration',
                value={
                    'default_llm_model': 'claude-3-5-sonnet-20241022',
                    'llm_temperature': 0.5,
                    'llm_max_tokens': 4000,
                    'use_llm_by_default': True,
                    'anthropic_api_key': 'sk-ant-xxxxx...'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Update Feature Flags',
                value={
                    'enable_caching': True,
                    'cache_ttl': 7200,
                    'enable_rate_limiting': True,
                    'rate_limit_per_hour': 500,
                    'maintenance_mode': False
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Update Scraping Config',
                value={
                    'scraping_timeout': 45,
                    'max_retries': 5,
                    'retry_delay': 2,
                    'user_agent': 'SportsCardBot/2.0'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Successful Update',
                value={
                    'site_name': 'Sports Card Kickoff Pro',
                    'site_description': 'Premium sports card marketplace',
                    'has_openai_configured': True,
                    'has_anthropic_configured': True,
                    'default_llm_model': 'claude-3-5-sonnet-20241022',
                    'llm_provider': 'anthropic',
                    'llm_temperature': 0.5,
                    'llm_max_tokens': 4000,
                    'updated_at': '2024-01-15T11:00:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Validation Error',
                value={
                    'llm_temperature': ['Temperature must be between 0 and 2.'],
                    'max_retries': ['Max retries must be between 0 and 10.']
                },
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={
            200: SystemConfigurationSerializer,
            400: OpenApiResponse(
                description="Validation error - Invalid configuration values"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            403: OpenApiResponse(
                description="You do not have permission to modify system configuration"
            )
        }
    )
    def patch(self, request):
        """Partially update system configuration."""
        config = SystemConfiguration.get_solo()
        serializer = SystemConfigurationUpdateSerializer(
            config,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return updated configuration (without sensitive data)
        response_serializer = SystemConfigurationSerializer(config)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['System Configuration'],
        summary="Update system configuration (full)",
        description="""
        Fully update system configuration settings.

        **Note:** This is a full update (PUT). All required fields must be provided.
        For partial updates, use PATCH method instead.

        **Authorization Required:**
        Must be authenticated as admin/staff user.
        """,
        request=SystemConfigurationUpdateSerializer,
        responses={
            200: SystemConfigurationSerializer,
            400: OpenApiResponse(
                description="Validation error - Invalid or missing required fields"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            403: OpenApiResponse(
                description="You do not have permission to modify system configuration"
            )
        }
    )
    def put(self, request):
        """Fully update system configuration."""
        config = SystemConfiguration.get_solo()
        serializer = SystemConfigurationUpdateSerializer(
            config,
            data=request.data,
            partial=False
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return updated configuration (without sensitive data)
        response_serializer = SystemConfigurationSerializer(config)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
