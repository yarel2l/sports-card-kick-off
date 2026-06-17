from django.urls import path

from .views import (
    AlertDetailView,
    AlertListView,
    HoldingDetailView,
    HoldingListView,
    PortfolioSummaryView,
    WatchlistItemView,
    WatchlistView,
)

app_name = 'portfolio'

urlpatterns = [
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
    path('watchlist/<uuid:pk>/', WatchlistItemView.as_view(), name='watchlist-item'),

    path('holdings/', HoldingListView.as_view(), name='holding-list'),
    path('holdings/<uuid:pk>/', HoldingDetailView.as_view(), name='holding-detail'),
    path('summary/', PortfolioSummaryView.as_view(), name='summary'),

    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<uuid:pk>/', AlertDetailView.as_view(), name='alert-detail'),
]
