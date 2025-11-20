from django.contrib import admin
from .models import TargetSite, Search, ScrapeResult, SearchHistory


@admin.register(TargetSite)
class TargetSiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'site_type', 'priority', 'is_active', 'created_at']
    list_filter = ['site_type', 'priority', 'is_active']
    search_fields = ['name', 'base_url']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['priority', 'name']


@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display = ['query', 'user', 'status', 'total_sites', 'successful_sites', 'total_items_found', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['query', 'player_name', 'card_set']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']


@admin.register(ScrapeResult)
class ScrapeResultAdmin(admin.ModelAdmin):
    list_display = ['search', 'target_site', 'status', 'items_count', 'execution_time_seconds', 'created_at']
    list_filter = ['status', 'target_site', 'created_at']
    search_fields = ['search__query']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'was_successful', 'total_results', 'accessed_at']
    list_filter = ['was_successful', 'accessed_at']
    search_fields = ['query', 'user__email']
    readonly_fields = ['accessed_at']
    ordering = ['-accessed_at']
