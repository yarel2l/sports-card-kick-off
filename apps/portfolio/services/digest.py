"""
Portfolio digest: a periodic summary of a user's holdings.

Builds the current mark-to-market valuation and compares it to the most recent
:class:`PortfolioSnapshot` so the digest can report how the portfolio's value
has moved since the last summary. Delivering a digest also records a fresh
snapshot, which becomes the baseline for the next one.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..models import PortfolioHolding, PortfolioSnapshot
from .valuation import value_portfolio

logger = logging.getLogger(__name__)


def build_digest(user) -> Dict[str, Any]:
    """Compute the current valuation and its change since the last snapshot."""
    holdings = PortfolioHolding.objects.select_related(
        'card', 'card__player', 'card__card_set', 'grading_company'
    ).filter(user=user)

    valuation = value_portfolio(holdings)
    totals = valuation['totals']

    previous: Optional[PortfolioSnapshot] = (
        PortfolioSnapshot.objects.filter(user=user).order_by('-captured_at').first()
    )

    value_change = None
    if (
        previous is not None
        and previous.total_market_value is not None
        and totals['total_market_value'] is not None
    ):
        value_change = totals['total_market_value'] - previous.total_market_value

    return {
        'valuation': valuation,
        'previous_snapshot': previous,
        'value_change': value_change,
    }


def record_snapshot(user, totals: Dict[str, Any]) -> PortfolioSnapshot:
    return PortfolioSnapshot.objects.create(
        user=user,
        holdings_count=totals['holdings_count'],
        total_cost=totals['total_cost'],
        total_market_value=totals['total_market_value'],
        total_unrealized_pl=totals['total_unrealized_pl'],
    )


def deliver_digest(user) -> bool:
    """
    Build, email, and snapshot a user's portfolio digest.

    Returns True if an email was sent. Users with no holdings are skipped (no
    email, no snapshot).
    """
    from ..notifications import send_portfolio_digest_email

    digest = build_digest(user)
    if digest['valuation']['totals']['holdings_count'] == 0:
        return False

    sent = send_portfolio_digest_email(user, digest)
    # Snapshot regardless of email outcome so the baseline advances.
    record_snapshot(user, digest['valuation']['totals'])
    return sent
