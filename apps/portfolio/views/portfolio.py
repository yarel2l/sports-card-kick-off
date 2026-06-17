"""
Portfolio, watchlist and price-alert API views.

All endpoints are per-user: querysets are scoped to ``request.user`` and the
owning user is set on create, so users only ever see and mutate their own data.
"""

from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PortfolioHolding, PriceAlert, WatchlistItem
from ..serializers import (
    PortfolioHoldingSerializer,
    PriceAlertSerializer,
    WatchlistItemSerializer,
)
from ..services.valuation import value_portfolio


class _OwnedQuerysetMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistView(_OwnedQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = WatchlistItemSerializer
    queryset = WatchlistItem.objects.select_related('card', 'card__player', 'card__card_set')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Idempotent: following an already-followed card is a no-op.
        item, _created = WatchlistItem.objects.get_or_create(
            user=request.user, card=serializer.validated_data['card']
        )
        out = self.get_serializer(item)
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if _created else status.HTTP_200_OK,
        )


class WatchlistItemView(_OwnedQuerysetMixin, generics.RetrieveDestroyAPIView):
    serializer_class = WatchlistItemSerializer
    queryset = WatchlistItem.objects.select_related('card')


class HoldingListView(_OwnedQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = PortfolioHoldingSerializer
    queryset = PortfolioHolding.objects.select_related(
        'card', 'card__player', 'card__card_set', 'grading_company'
    )


class HoldingDetailView(_OwnedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioHoldingSerializer
    queryset = PortfolioHolding.objects.select_related('card', 'grading_company')


class AlertListView(_OwnedQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = PriceAlertSerializer
    queryset = PriceAlert.objects.select_related('card', 'card__player', 'card__card_set')

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get('active')
        if active in ('true', '1', 'yes'):
            qs = qs.filter(is_active=True)
        elif active in ('false', '0', 'no'):
            qs = qs.filter(is_active=False)
        return qs


class AlertDetailView(_OwnedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PriceAlertSerializer
    queryset = PriceAlert.objects.select_related('card')


class PortfolioSummaryView(APIView):
    """Mark-to-market valuation of the authenticated user's holdings."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        holdings = PortfolioHolding.objects.select_related(
            'card', 'grading_company'
        ).filter(user=request.user)
        return Response(value_portfolio(holdings))
