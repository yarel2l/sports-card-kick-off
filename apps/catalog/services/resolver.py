"""
Entity resolution: map a noisy listing title to a canonical :class:`Card`.

The resolver is the bridge between the rule-based :func:`parse_title` pass and
the persistent catalog. It is intentionally conservative: it will create new
catalog rows when it is confident enough, and otherwise returns a result with a
low confidence score so callers can decide whether to persist or queue for
review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from django.db import transaction
from django.utils.text import slugify

from ..models import Card, CardSet, Player
from . import constants
from .title_parser import ParsedCard, parse_title

logger = logging.getLogger(__name__)

# Minimum similarity for two player names to be considered the same person.
PLAYER_MATCH_THRESHOLD = 0.86
# Minimum overall confidence required before the resolver will create/return a
# canonical card. Below this we still return a result, but ``card`` is None.
MIN_RESOLVE_CONFIDENCE = 0.45


@dataclass
class ResolutionResult:
    parsed: ParsedCard
    card: Optional[Card] = None
    player: Optional[Player] = None
    card_set: Optional[CardSet] = None
    confidence: float = 0.0
    created_card: bool = False
    created_player: bool = False
    created_set: bool = False


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _score(parsed: ParsedCard, player_matched: bool) -> float:
    """Heuristic confidence in [0, 1] based on how much structure we recovered."""
    score = 0.0
    if parsed.year:
        score += 0.20
    if parsed.brand:
        score += 0.15
    if parsed.set_name:
        score += 0.15
    if parsed.card_number:
        score += 0.15
    if parsed.player_name:
        score += 0.15
    if player_matched:
        score += 0.20
    return round(min(score, 1.0), 3)


def _find_player(name: str, sport: str) -> tuple[Optional[Player], bool]:
    """Return (player, matched_existing). Fuzzy-matches against name + aliases."""
    if not name:
        return None, False

    slug = slugify(name)
    if slug:
        exact = Player.objects.filter(slug=slug).first()
        if exact:
            return exact, True

    best: Optional[Player] = None
    best_ratio = 0.0
    # Scope the scan to the same sport when known to reduce false positives.
    qs = Player.objects.all()
    if sport and sport != constants.SPORT_OTHER:
        qs = qs.filter(sport__in=[sport, constants.SPORT_OTHER])
    for player in qs.iterator():
        candidates = [player.name, *(player.aliases or [])]
        ratio = max(_name_similarity(name, c) for c in candidates)
        if ratio > best_ratio:
            best_ratio, best = ratio, player

    if best and best_ratio >= PLAYER_MATCH_THRESHOLD:
        return best, True
    return None, False


def _infer_sport(parsed: ParsedCard) -> str:
    # Placeholder for richer inference (set-based, player-based). The parser
    # does not yet detect sport, so default to OTHER and let player records
    # carry the authoritative value over time.
    return constants.SPORT_OTHER


class CardResolver:
    """Resolves listing titles into canonical catalog cards."""

    def __init__(self, *, create_missing: bool = True, sport: Optional[str] = None):
        self.create_missing = create_missing
        self.sport = sport

    def resolve(self, title: str) -> ResolutionResult:
        parsed = parse_title(title)
        return self.resolve_parsed(parsed)

    @transaction.atomic
    def resolve_parsed(self, parsed: ParsedCard) -> ResolutionResult:
        sport = self.sport or _infer_sport(parsed)
        result = ResolutionResult(parsed=parsed)

        # --- Player -------------------------------------------------------
        player, matched = (None, False)
        if parsed.player_name:
            player, matched = _find_player(parsed.player_name, sport)
            result.player = player

        result.confidence = _score(parsed, matched)

        # Need at least a set signal (brand or set name) to anchor a card.
        if not (parsed.brand or parsed.set_name) or not parsed.year:
            return result
        if result.confidence < MIN_RESOLVE_CONFIDENCE and not self.create_missing:
            return result

        if not self.create_missing:
            # Read-only resolution: only return an existing exact card.
            result.card = self._find_existing_card(parsed, player, sport)
            return result

        # --- Create player on demand --------------------------------------
        if parsed.player_name and player is None:
            player = Player.objects.create(name=parsed.player_name, sport=sport)
            result.player = player
            result.created_player = True

        # --- Card set -----------------------------------------------------
        brand = parsed.brand or constants.SET_TO_BRAND.get(parsed.set_name or '', 'Unknown')
        set_name = parsed.set_name or brand
        card_set, created_set = CardSet.objects.get_or_create(
            year=parsed.year,
            brand=brand,
            name=set_name,
            sport=sport,
            defaults={'slug': CardSet.build_slug(parsed.year, brand, set_name, sport)},
        )
        result.card_set = card_set
        result.created_set = created_set

        # --- Card ---------------------------------------------------------
        canonical_key = Card.build_canonical_key(
            card_set.slug,
            parsed.card_number,
            parsed.parallel,
            player.slug if player else None,
        )
        card, created_card = Card.objects.get_or_create(
            canonical_key=canonical_key,
            defaults={
                'card_set': card_set,
                'player': player,
                'card_number': parsed.card_number or '',
                'parallel': parsed.parallel or '',
                'is_rookie': parsed.is_rookie,
                'is_autograph': parsed.is_autograph,
                'is_memorabilia': parsed.is_memorabilia,
                'serial_limit': parsed.serial_limit,
            },
        )
        result.card = card
        result.created_card = created_card
        return result

    def _find_existing_card(self, parsed, player, sport) -> Optional[Card]:
        if not parsed.year:
            return None
        brand = parsed.brand or constants.SET_TO_BRAND.get(parsed.set_name or '', 'Unknown')
        set_name = parsed.set_name or brand
        slug = CardSet.build_slug(parsed.year, brand, set_name, sport)
        canonical_key = Card.build_canonical_key(
            slug,
            parsed.card_number,
            parsed.parallel,
            player.slug if player else (slugify(parsed.player_name) if parsed.player_name else None),
        )
        return Card.objects.filter(canonical_key=canonical_key).first()
