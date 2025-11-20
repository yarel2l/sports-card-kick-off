"""
Search URLs.
"""

from django.urls import path

from .views import (
    CreateSearchView,
    SearchHistoryView,
    SearchDetailView,
    SearchResultsView,
    CancelSearchView,
    AvailableSitesView,
    UserSearchStatsView,
)

app_name = 'search'

urlpatterns = [
    # Create new search
    path('', CreateSearchView.as_view(), name='create_search'),
    
    # Search history and statistics
    path('history/', SearchHistoryView.as_view(), name='search_history'),
    path('stats/', UserSearchStatsView.as_view(), name='user_stats'),
    
    # Available sites
    path('sites/', AvailableSitesView.as_view(), name='available_sites'),
    
    # Search detail and operations
    path('<uuid:search_id>/', SearchDetailView.as_view(), name='search_detail'),
    path('<uuid:search_id>/results/', SearchResultsView.as_view(), name='search_results'),
    path('<uuid:search_id>/cancel/', CancelSearchView.as_view(), name='cancel_search'),
]
