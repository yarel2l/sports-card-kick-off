"""
Pricing intelligence built on top of :class:`PriceObservation` rows.

These helpers turn the stream of raw price observations into the aggregates a
buyer/investor actually cares about: current market value per grade, spread,
last sale, and a historical time series. Everything is computed with the ORM so
it scales with the database rather than loading every observation into memory
(the only in-Python step is the median, over a single card's prices).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from statistics import median as _median
from typing import Any, Dict, List, Optional

from django.db.models import Avg, Count, Max, Min, QuerySet
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from ..models import Card, PriceObservation

_TRUNC = {
    'day': TruncDay,
    'week': TruncWeek,
    'month': TruncMonth,
}


def _filtered(
    card: Card,
    *,
    grade: Optional[str] = None,
    grading_company: Optional[str] = None,
    source: Optional[str] = None,
    kind: Optional[str] = None,
    window_days: Optional[int] = None,
) -> QuerySet:
    qs = PriceObservation.objects.filter(card=card)
    if grade is not None:
        qs = qs.filter(grade=grade)
    if grading_company is not None:
        qs = qs.filter(grading_company__code=grading_company)
    if source:
        qs = qs.filter(source=source)
    if kind:
        qs = qs.filter(kind=kind)
    if window_days:
        qs = qs.filter(observed_at__gte=timezone.now() - timedelta(days=window_days))
    return qs


def _round(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal('0.01'))


def market_summary(card: Card, **filters) -> Dict[str, Any]:
    """Aggregate stats for a card (optionally narrowed by grade/source/window)."""
    qs = _filtered(card, **filters)
    agg = qs.aggregate(
        count=Count('id'), min=Min('price'), max=Max('price'), avg=Avg('price')
    )
    prices = list(qs.values_list('price', flat=True))
    last_obs = qs.order_by('-observed_at').first()

    return {
        'count': agg['count'] or 0,
        'min': _round(agg['min']),
        'max': _round(agg['max']),
        'avg': _round(agg['avg']),
        'median': _round(_median(prices)) if prices else None,
        'last': last_obs.price if last_obs else None,
        'last_observed_at': last_obs.observed_at if last_obs else None,
        'currency': last_obs.currency if last_obs else 'USD',
    }


def market_by_grade(card: Card, **filters) -> List[Dict[str, Any]]:
    """Per-grade aggregates for a card, one row per (grading company, grade)."""
    qs = _filtered(card, **filters)
    rows = (
        qs.values('grading_company__code', 'grade')
        .annotate(count=Count('id'), min=Min('price'), max=Max('price'), avg=Avg('price'))
        .order_by('grading_company__code', 'grade')
    )
    return [
        {
            'grading_company': row['grading_company__code'],
            'grade': row['grade'] or None,
            'count': row['count'],
            'min': _round(row['min']),
            'max': _round(row['max']),
            'avg': _round(row['avg']),
        }
        for row in rows
    ]


def price_history(
    card: Card, *, interval: str = 'day', **filters
) -> List[Dict[str, Any]]:
    """Time series of average price per bucket (day/week/month)."""
    trunc = _TRUNC.get(interval, TruncDay)
    qs = _filtered(card, **filters)
    rows = (
        qs.annotate(bucket=trunc('observed_at'))
        .values('bucket')
        .annotate(avg=Avg('price'), min=Min('price'), max=Max('price'), count=Count('id'))
        .order_by('bucket')
    )
    return [
        {
            'bucket': row['bucket'],
            'avg': _round(row['avg']),
            'min': _round(row['min']),
            'max': _round(row['max']),
            'count': row['count'],
        }
        for row in rows
    ]


def card_market(card: Card, **filters) -> Dict[str, Any]:
    """Convenience bundle: overall summary + per-grade breakdown."""
    return {
        'overall': market_summary(card, **filters),
        'by_grade': market_by_grade(card, **filters),
    }
