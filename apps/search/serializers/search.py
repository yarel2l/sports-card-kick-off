"""
Search and ScrapeResult Serializers.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import Search, ScrapeResult, TargetSite, SearchHistory


class ScrapeResultSerializer(serializers.ModelSerializer):
    """
    Serializer for ScrapeResult model.
    """
    site_name = serializers.CharField(source='target_site.name', read_only=True)
    site_type = serializers.CharField(source='target_site.site_type', read_only=True)
    
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
    """
    
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
    """
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
    """
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
    """
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
    """
    total_searches = serializers.IntegerField()
    completed_searches = serializers.IntegerField()
    failed_searches = serializers.IntegerField()
    total_items_found = serializers.IntegerField()
    average_execution_time = serializers.FloatField()
    most_searched_players = serializers.ListField(
        child=serializers.DictField()
    )
    recent_searches = SearchSerializer(many=True)
