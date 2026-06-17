"""
Ingestion: turn scraped marketplace items into catalog rows.

This is the glue between the scraping layer (which produces source-specific
dicts/Pydantic models) and the canonical catalog. It is deliberately tolerant:
a single malformed item must never break a batch, so every item is processed
defensively and failures are logged and skipped.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

from ..models import GradingCompany, PriceObservation
from . import constants
from .resolver import CardResolver, ResolutionResult

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _get(item: Dict[str, Any], *path, default=None):
    """Safely walk nested dict keys."""
    current: Any = item
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _grading_company(code: Optional[str]) -> Optional[GradingCompany]:
    if not code:
        return None
    code = constants.GRADING_COMPANY_ALIASES.get(code.upper(), code.upper())
    company, _ = GradingCompany.objects.get_or_create(
        code=code,
        defaults={'name': constants.GRADING_COMPANY_NAMES.get(code, code)},
    )
    return company


def ingest_item(
    item: Dict[str, Any],
    *,
    source: str,
    resolver: Optional[CardResolver] = None,
) -> Optional[PriceObservation]:
    """
    Resolve a single scraped item to a canonical card and record its price.

    ``item`` is expected to be a plain dict (e.g. ``EbayItem.model_dump()``).
    Returns the created/updated :class:`PriceObservation`, or None if the item
    could not be resolved or priced.
    """
    resolver = resolver or CardResolver()

    title = item.get('title') or ''
    if not title.strip():
        return None

    result: ResolutionResult = resolver.resolve(title)
    if result.card is None:
        logger.debug("Ingest: unresolved title (conf=%.2f): %s", result.confidence, title)
        return None

    amount = _to_decimal(_get(item, 'price', 'total')) or _to_decimal(_get(item, 'price', 'amount'))
    if amount is None or amount <= 0:
        logger.debug("Ingest: item has no usable price: %s", title)
        return None

    currency = _get(item, 'price', 'currency', default='USD') or 'USD'
    grade_value = _get(item, 'grade', 'numeric_grade')
    grade_str = ('' if grade_value is None else (
        str(int(grade_value)) if float(grade_value).is_integer() else str(grade_value)
    ))
    company = _grading_company(_get(item, 'grade', 'grading_company'))

    # Determine the observation kind. An explicit ``observation_kind`` on the
    # item wins (e.g. Goldin auction lots); otherwise sources that report
    # completed sales carry a ``sale_type`` and are recorded as SOLD (the most
    # valuable signal); otherwise fall back to listing/auction detection.
    valid_kinds = {k.value for k in PriceObservation.Kind}
    explicit_kind = item.get('observation_kind')
    if explicit_kind in valid_kinds:
        kind = explicit_kind
    elif item.get('sale_type'):
        kind = PriceObservation.Kind.SOLD
    elif bool(_get(item, 'listing', 'is_auction', default=False)):
        kind = PriceObservation.Kind.AUCTION
    else:
        kind = PriceObservation.Kind.LISTING

    external_id = str(item.get('item_id') or item.get('epid') or '')
    url = str(item.get('url') or '')

    defaults = {
        'card': result.card,
        'kind': kind,
        'grading_company': company,
        'grade': grade_str,
        'price': amount,
        'currency': currency,
        'url': url,
        'raw_title': title,
        'match_confidence': result.confidence,
    }

    if external_id:
        obs, _created = PriceObservation.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults=defaults,
        )
    else:
        obs = PriceObservation.objects.create(
            source=source, external_id='', **defaults
        )
    return obs


def ingest_items(
    items: Iterable[Dict[str, Any]],
    *,
    source: str,
    resolver: Optional[CardResolver] = None,
) -> List[PriceObservation]:
    """Ingest a batch of items, skipping (and logging) any that fail."""
    resolver = resolver or CardResolver()
    observations: List[PriceObservation] = []
    for item in items:
        try:
            obs = ingest_item(item, source=source, resolver=resolver)
            if obs is not None:
                observations.append(obs)
        except Exception:  # never let one bad item break the batch
            logger.exception("Ingest failed for item: %s", str(item)[:200])
    return observations
