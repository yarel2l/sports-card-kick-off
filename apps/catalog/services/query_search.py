"""
Natural-language catalog search.

Reuses :func:`parse_title` to interpret a free-text query the same way it
interprets a listing title, then turns the structured result into a Card
queryset. Explicit keyword arguments (from query-string filters) always win
over what was parsed from the text.
"""

from __future__ import annotations

from typing import Optional, Tuple

from django.db.models import Count, QuerySet

from ..models import Card
from .title_parser import ParsedCard, parse_title


def search_cards(
    q: Optional[str] = None,
    *,
    player: Optional[str] = None,
    year: Optional[int] = None,
    brand: Optional[str] = None,
    set_name: Optional[str] = None,
    parallel: Optional[str] = None,
    card_number: Optional[str] = None,
    rookie: Optional[bool] = None,
    autograph: Optional[bool] = None,
) -> Tuple[ParsedCard, QuerySet]:
    """Return (parsed_query, ordered Card queryset) for a NL query + filters."""
    parsed = parse_title(q) if q else ParsedCard(raw_title=q or '')

    player = player or parsed.player_name
    year = year or parsed.year
    brand = brand or parsed.brand
    set_name = set_name or parsed.set_name
    parallel = parallel if parallel is not None else parsed.parallel
    card_number = card_number or parsed.card_number
    if rookie is None and parsed.is_rookie:
        rookie = True
    if autograph is None and parsed.is_autograph:
        autograph = True

    qs = Card.objects.select_related('card_set', 'player')

    if player:
        qs = qs.filter(player__name__icontains=player)
    if year:
        qs = qs.filter(card_set__year=year)
    if brand:
        qs = qs.filter(card_set__brand__icontains=brand)
    if set_name:
        qs = qs.filter(card_set__name__icontains=set_name)
    if parallel:
        qs = qs.filter(parallel__icontains=parallel)
    if card_number:
        qs = qs.filter(card_number__iexact=card_number)
    if rookie:
        qs = qs.filter(is_rookie=True)
    if autograph:
        qs = qs.filter(is_autograph=True)

    # Rank cards with more market data first; newest sets break ties.
    qs = qs.annotate(observation_count=Count('price_observations')).order_by(
        '-observation_count', '-card_set__year', 'card_number'
    )
    return parsed, qs
