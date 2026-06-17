from django.urls import path

from .views import (
    CardDetailView,
    CardHistoryView,
    CardListView,
    CardPricesView,
    CatalogSearchView,
    PlayerListView,
)

app_name = 'catalog'

urlpatterns = [
    path('search/', CatalogSearchView.as_view(), name='search'),
    path('cards/', CardListView.as_view(), name='card-list'),
    path('cards/<uuid:pk>/', CardDetailView.as_view(), name='card-detail'),
    path('cards/<uuid:pk>/prices/', CardPricesView.as_view(), name='card-prices'),
    path('cards/<uuid:pk>/history/', CardHistoryView.as_view(), name='card-history'),
    path('players/', PlayerListView.as_view(), name='player-list'),
]
