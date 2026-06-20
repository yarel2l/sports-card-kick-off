"""
Discovery helpers that power the consumer-facing home page: trending cards,
a recent-sales feed, and lightweight autocomplete.
"""

from __future__ import annotations

from datetime import timedelta
from typing import List, Tuple

from django.db.models import Count, Q
from django.utils import timezone

from ..models import Card, Player, PriceObservation


def trending_cards(days: int = 30, limit: int = 12) -> List[Card]:
    """Cards with the most price observations in the recent window."""
    since = timezone.now() - timedelta(days=days)
    qs = (
        Card.objects.select_related("card_set", "player")
        .annotate(
            recent=Count(
                "price_observations",
                filter=Q(price_observations__observed_at__gte=since),
            )
        )
        .filter(recent__gt=0)
        .order_by("-recent", "-card_set__year")
    )
    return list(qs[:limit])


def recent_observations(limit: int = 20) -> List[PriceObservation]:
    """Most recent price observations across the catalog (the sales feed)."""
    return list(
        PriceObservation.objects.select_related(
            "card", "card__player", "card__card_set", "grading_company"
        ).order_by("-observed_at")[:limit]
    )


def autocomplete(q: str, limit: int = 8) -> Tuple[List[Player], List[Card]]:
    """Quick player + card suggestions for a partial query."""
    q = (q or "").strip()
    if len(q) < 2:
        return [], []
    players = list(Player.objects.filter(name__icontains=q)[:limit])
    cards = list(
        Card.objects.select_related("player", "card_set")
        .filter(
            Q(player__name__icontains=q)
            | Q(card_set__brand__icontains=q)
            | Q(card_set__name__icontains=q)
        )
        .order_by("-card_set__year")[:limit]
    )
    return players, cards
