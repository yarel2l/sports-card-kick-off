"""
Search and ScrapeResult Serializers.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import Search, ScrapeResult, TargetSite, SearchHistory


class ScrapeResultSerializer(serializers.ModelSerializer):
    """
    Serializer for ScrapeResult model.
    Contains detailed results from scraping a specific site for a search.
    """
    site_name = serializers.CharField(
        source='target_site.name',
        read_only=True,
        help_text="Name of the scraped site (e.g., 'eBay', 'PSA')"
    )
    site_type = serializers.CharField(
        source='target_site.site_type',
        read_only=True,
        help_text="Type of site: SALES, AUCTION, POPULATION, or MARKETPLACE"
    )
    status = serializers.CharField(help_text="Result status: SUCCESS, FAILED, TIMEOUT, or NO_RESULTS")
    data = serializers.JSONField(help_text="Scraped data containing items, metadata, and errors")
    items_count = serializers.IntegerField(help_text="Number of items found on this site")
    execution_time_seconds = serializers.FloatField(help_text="Time taken to scrape this site (in seconds)", allow_null=True)
    error_message = serializers.CharField(help_text="Error description if scraping failed", allow_null=True)
    
    class Meta:
        model = ScrapeResult
        fields = [
            'id',
            'target_site',
            'site_name',
            'site_type',
            'status',
            'data',
            'items_count',
            'execution_time_seconds',
            'error_message',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'site_name',
            'site_type',
            'status',
            'data',
            'items_count',
            'execution_time_seconds',
            'error_message',
            'created_at',
        ]


class SearchSerializer(serializers.ModelSerializer):
    """
    Basic serializer for Search model (list view).
    Provides summary information about a search without nested results.
    """
    query = serializers.CharField(help_text="Original search query entered by the user")
    status = serializers.CharField(help_text="Current search status: PENDING, PROCESSING, COMPLETED, FAILED, PARTIAL, CANCELLED")
    player_name = serializers.CharField(help_text="Extracted player name from query (if detected)", allow_null=True)
    card_year = serializers.IntegerField(help_text="Extracted card year from query (if detected)", allow_null=True)
    card_set = serializers.CharField(help_text="Extracted card set name from query (if detected)", allow_null=True)
    grade = serializers.CharField(help_text="Extracted grade information (e.g., 'PSA 10', 'BGS 9.5')", allow_null=True)
    total_items_found = serializers.IntegerField(help_text="Total number of items found across all successful sites")
    successful_sites = serializers.IntegerField(help_text="Number of sites that completed scraping successfully")
    failed_sites = serializers.IntegerField(help_text="Number of sites that failed to scrape")
    execution_time_seconds = serializers.FloatField(help_text="Total time taken to complete the search (in seconds)", allow_null=True)
    created_at = serializers.DateTimeField(help_text="When the search was created")
    completed_at = serializers.DateTimeField(help_text="When the search was completed", allow_null=True)
    
    class Meta:
        model = Search
        fields = [
            'id',
            'query',
            'status',
            'player_name',
            'card_year',
            'card_set',
            'grade',
            'total_items_found',
            'successful_sites',
            'failed_sites',
            'execution_time_seconds',
            'created_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'player_name',
            'card_year',
            'card_set',
            'grade',
            'total_items_found',
            'successful_sites',
            'failed_sites',
            'execution_time_seconds',
            'created_at',
            'completed_at',
        ]


class SearchCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new search.
    Validates query and triggers asynchronous scraping across configured sites.
    """
    query = serializers.CharField(
        min_length=3,
        max_length=500,
        help_text="Search query for sports cards. Include player name, year, set, and/or grade for best results. Example: 'Michael Jordan 1986 Fleer PSA 10'"
    )
    
    class Meta:
        model = Search
        fields = ['query']
    
    def validate_query(self, value):
        """Validate query is not empty and has minimum length."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                _('Query cannot be empty.')
            )
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                _('Query must be at least 3 characters long.')
            )
        
        return value.strip()


class SearchDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Search model (retrieve view) with nested results.
    """
    results = ScrapeResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = Search
        fields = [
            'id',
            'user',
            'query',
            'status',
            'player_name',
            'card_year',
            'card_set',
            'grade',
            'total_sites',
            'successful_sites',
            'failed_sites',
            'total_items_found',
            'execution_time_seconds',
            'error_message',
            'results',
            'created_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'status',
            'player_name',
            'card_year',
            'card_set',
            'grade',
            'total_sites',
            'successful_sites',
            'failed_sites',
            'total_items_found',
            'execution_time_seconds',
            'error_message',
            'results',
            'created_at',
            'completed_at',
        ]


class SearchHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for SearchHistory model - user's search history.
    Provides a record of past searches for quick access and re-execution.
    """
    id = serializers.UUIDField(help_text="Unique identifier for the search history entry")
    query = serializers.CharField(help_text="Original search query")
    was_successful = serializers.BooleanField(help_text="Whether the search completed successfully")
    total_results = serializers.IntegerField(help_text="Total number of items found in this search")
    accessed_at = serializers.DateTimeField(help_text="When the search was last accessed")
    
    class Meta:
        model = SearchHistory
        fields = [
            'id',
            'query',
            'was_successful',
            'total_results',
            'accessed_at',
        ]
        read_only_fields = [
            'id',
            'query',
            'was_successful',
            'total_results',
            'accessed_at',
        ]


class TargetSiteSerializer(serializers.ModelSerializer):
    """
    Serializer for TargetSite model - available scraping sites.
    Lists all marketplaces and data sources available for scraping.
    """
    id = serializers.UUIDField(help_text="Unique identifier for the site")
    name = serializers.CharField(help_text="Display name of the site (e.g., 'eBay', 'PSA', 'COMC')")
    slug = serializers.SlugField(help_text="URL-friendly identifier for the site")
    base_url = serializers.URLField(help_text="Base URL of the site")
    site_type = serializers.CharField(help_text="Type of site: SALES, AUCTION, POPULATION, or MARKETPLACE")
    priority = serializers.CharField(help_text="Scraping priority: HIGH, MEDIUM, or LOW")
    is_active = serializers.BooleanField(help_text="Whether the site is currently enabled for scraping")
    
    class Meta:
        model = TargetSite
        fields = [
            'id',
            'name',
            'slug',
            'base_url',
            'site_type',
            'priority',
            'is_active',
        ]
        read_only_fields = [
            'id',
            'name',
            'slug',
            'base_url',
            'site_type',
            'priority',
            'is_active',
        ]


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user search statistics.
    Provides comprehensive analytics about a user's search activity and performance.
    """
    total_searches = serializers.IntegerField(
        help_text="Total number of searches created by the user"
    )
    completed_searches = serializers.IntegerField(
        help_text="Number of searches that completed successfully"
    )
    failed_searches = serializers.IntegerField(
        help_text="Number of searches that failed"
    )
    total_items_found = serializers.IntegerField(
        help_text="Sum of all items found across all successful searches"
    )
    average_execution_time = serializers.FloatField(
        help_text="Average time (in seconds) to complete a search"
    )
    most_searched_players = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of most frequently searched players with their search counts"
    )
    recent_searches = SearchSerializer(
        many=True,
        help_text="Last 5 searches performed by the user"
    )
