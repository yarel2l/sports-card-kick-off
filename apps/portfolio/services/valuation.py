"""
Portfolio valuation built on the catalog pricing service.

Each holding is marked to market using the most recent observed price for its
card/grade (falling back to the average), producing per-holding and aggregate
cost / value / unrealized P&L figures.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from apps.catalog.services import pricing


def _market_price(holding) -> Decimal | None:
    company = holding.grading_company.code if holding.grading_company_id else None
    summary = pricing.market_summary(
        holding.card,
        grade=holding.grade or None,
        grading_company=company,
    )
    price = summary['last'] if summary['last'] is not None else summary['avg']
    return price


def value_holding(holding) -> Dict[str, Any]:
    """Mark a single holding to market."""
    unit_price = _market_price(holding)
    quantity = holding.quantity or 0
    cost = (holding.cost_basis or Decimal('0')) * quantity

    if unit_price is None:
        market_value = None
        unrealized = None
    else:
        market_value = Decimal(unit_price) * quantity
        unrealized = market_value - cost

    return {
        'holding_id': str(holding.id),
        'card_id': str(holding.card_id),
        'quantity': quantity,
        'grade': holding.grade or None,
        'cost_basis': holding.cost_basis,
        'total_cost': cost,
        'market_unit_price': unit_price,
        'market_value': market_value,
        'unrealized_pl': unrealized,
        'currency': holding.currency,
    }


def value_portfolio(holdings) -> Dict[str, Any]:
    """Aggregate valuation across a user's holdings."""
    items: List[Dict[str, Any]] = []
    total_cost = Decimal('0')
    total_value = Decimal('0')
    has_market_data = False

    for holding in holdings:
        valued = value_holding(holding)
        items.append(valued)
        total_cost += valued['total_cost'] or Decimal('0')
        if valued['market_value'] is not None:
            total_value += valued['market_value']
            has_market_data = True

    total_unrealized = (total_value - total_cost) if has_market_data else None
    return {
        'holdings': items,
        'totals': {
            'holdings_count': len(items),
            'total_cost': total_cost,
            'total_market_value': total_value if has_market_data else None,
            'total_unrealized_pl': total_unrealized,
        },
    }
