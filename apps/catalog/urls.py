from django.urls import path

from .views import (
    AutocompleteView,
    CardDetailView,
    CardHistoryView,
    CardListView,
    CardPricesView,
    CatalogSearchView,
    PlayerListView,
    RecentSalesFeedView,
    TrendingView,
)

app_name = 'catalog'

urlpatterns = [
    path('search/', CatalogSearchView.as_view(), name='search'),
    path('autocomplete/', AutocompleteView.as_view(), name='autocomplete'),
    path('trending/', TrendingView.as_view(), name='trending'),
    path('feed/', RecentSalesFeedView.as_view(), name='feed'),
    path('cards/', CardListView.as_view(), name='card-list'),
    path('cards/<uuid:pk>/', CardDetailView.as_view(), name='card-detail'),
    path('cards/<uuid:pk>/prices/', CardPricesView.as_view(), name='card-prices'),
    path('cards/<uuid:pk>/history/', CardHistoryView.as_view(), name='card-history'),
    path('players/', PlayerListView.as_view(), name='player-list'),
]
