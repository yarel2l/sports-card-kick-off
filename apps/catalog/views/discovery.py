"""
Discovery endpoints for the home page: autocomplete, trending, recent-sales feed.
All public read-only.
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import CardSerializer, FeedObservationSerializer
from ..services import discovery, pricing


class AutocompleteView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "")
        players, cards = discovery.autocomplete(q)
        return Response(
            {
                "players": [
                    {"id": str(p.id), "name": p.name, "slug": p.slug, "sport": p.sport}
                    for p in players
                ],
                "cards": [
                    {
                        "id": str(c.id),
                        "label": str(c),
                        "card_number": c.card_number,
                    }
                    for c in cards
                ],
            }
        )


class TrendingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 12)), 50)
        except (TypeError, ValueError):
            limit = 12
        cards = discovery.trending_cards(limit=limit)
        results = [
            {"card": CardSerializer(card).data, "market": pricing.market_summary(card)}
            for card in cards
        ]
        return Response({"count": len(results), "results": results})


class RecentSalesFeedView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 20)), 100)
        except (TypeError, ValueError):
            limit = 20
        observations = discovery.recent_observations(limit=limit)
        return Response(
            {
                "count": len(observations),
                "results": FeedObservationSerializer(observations, many=True).data,
            }
        )
