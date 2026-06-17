"""
Catalog API views.

These are public, read-only endpoints (the catalog and price data are
non-sensitive aggregate information and power the consumer-facing search
experience). Write paths into the catalog happen through ingestion, not the API.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Card, Player
from ..serializers import (
    CardSerializer,
    PlayerSerializer,
    PriceObservationSerializer,
)
from ..services import pricing
from ..services.query_search import search_cards


class CardListView(generics.ListAPIView):
    """List/filter canonical cards."""

    serializer_class = CardSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['canonical_key', 'card_number', 'player__name', 'card_set__brand', 'card_set__name']
    ordering_fields = ['card_set__year', 'card_number']
    ordering = ['-card_set__year', 'card_number']

    def get_queryset(self):
        qs = Card.objects.select_related('card_set', 'player')
        params = self.request.query_params
        if params.get('player'):
            qs = qs.filter(player__name__icontains=params['player'])
        if params.get('year'):
            qs = qs.filter(card_set__year=params['year'])
        if params.get('brand'):
            qs = qs.filter(card_set__brand__icontains=params['brand'])
        if params.get('set'):
            qs = qs.filter(card_set__name__icontains=params['set'])
        if params.get('rookie') in ('true', '1', 'yes'):
            qs = qs.filter(is_rookie=True)
        return qs


class CardDetailView(generics.RetrieveAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Card.objects.select_related('card_set', 'player')


class PlayerListView(generics.ListAPIView):
    serializer_class = PlayerSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Player.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']


class CardPricesView(APIView):
    """Market value for a card: overall summary + per-grade breakdown."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('grade', str, description='Filter by grade, e.g. "10"'),
            OpenApiParameter('grading_company', str, description='Filter by company, e.g. "PSA"'),
            OpenApiParameter('source', str, description='Filter by source, e.g. "ebay"'),
            OpenApiParameter('window_days', int, description='Only observations from the last N days'),
        ],
        responses=dict,
    )
    def get(self, request, pk):
        card = get_object_or_404(Card.objects.select_related('card_set', 'player'), pk=pk)
        filters = self._filters(request)
        recent = (
            card.price_observations.select_related('grading_company')
            .order_by('-observed_at')[:20]
        )
        return Response({
            'card': CardSerializer(card).data,
            'market': pricing.card_market(card, **filters),
            'recent_observations': PriceObservationSerializer(recent, many=True).data,
        })

    @staticmethod
    def _filters(request):
        params = request.query_params
        filters = {}
        if params.get('grade'):
            filters['grade'] = params['grade']
        if params.get('grading_company'):
            filters['grading_company'] = params['grading_company'].upper()
        if params.get('source'):
            filters['source'] = params['source']
        if params.get('window_days'):
            try:
                filters['window_days'] = int(params['window_days'])
            except (TypeError, ValueError):
                pass
        return filters


class CardHistoryView(APIView):
    """Price history time series for a card."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('interval', str, description='Bucket size: day|week|month'),
            OpenApiParameter('grade', str),
            OpenApiParameter('grading_company', str),
        ],
        responses=dict,
    )
    def get(self, request, pk):
        card = get_object_or_404(Card, pk=pk)
        params = request.query_params
        interval = params.get('interval', 'day')
        if interval not in ('day', 'week', 'month'):
            interval = 'day'
        filters = {}
        if params.get('grade'):
            filters['grade'] = params['grade']
        if params.get('grading_company'):
            filters['grading_company'] = params['grading_company'].upper()
        return Response({
            'card_id': str(card.id),
            'interval': interval,
            'history': pricing.price_history(card, interval=interval, **filters),
        })


class CatalogSearchView(generics.ListAPIView):
    """
    Natural-language catalog search.

    Parses ``q`` (e.g. "Luka Doncic 2018 Prizm rookie PSA 10") into structured
    filters and returns matching cards, each annotated with a market summary.
    """

    serializer_class = CardSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        params = self.request.query_params
        rookie = None
        if params.get('rookie') in ('true', '1', 'yes'):
            rookie = True
        year = None
        if params.get('year'):
            try:
                year = int(params['year'])
            except (TypeError, ValueError):
                year = None
        self._parsed, qs = search_cards(
            params.get('q'),
            player=params.get('player'),
            year=year,
            brand=params.get('brand'),
            set_name=params.get('set'),
            parallel=params.get('parallel'),
            card_number=params.get('card_number'),
            rookie=rookie,
        )
        self._grade = params.get('grade')
        self._grading_company = (
            params['grading_company'].upper() if params.get('grading_company') else None
        )
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        cards = page if page is not None else queryset

        price_filters = {}
        if self._grade:
            price_filters['grade'] = self._grade
        if self._grading_company:
            price_filters['grading_company'] = self._grading_company

        results = []
        for card in cards:
            results.append({
                'card': CardSerializer(card).data,
                'market': pricing.market_summary(card, **price_filters),
            })

        interpreted = {
            'player_name': self._parsed.player_name,
            'year': self._parsed.year,
            'brand': self._parsed.brand,
            'set_name': self._parsed.set_name,
            'parallel': self._parsed.parallel,
            'card_number': self._parsed.card_number,
            'grading_company': self._parsed.grading_company,
            'grade': self._parsed.grade,
            'is_rookie': self._parsed.is_rookie,
        }

        if page is not None:
            response = self.get_paginated_response(results)
            response.data['interpreted_query'] = interpreted
            return response
        return Response({'results': results, 'interpreted_query': interpreted})
