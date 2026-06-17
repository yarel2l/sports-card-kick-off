"""
Email notifications for portfolio events.

Currently: notifying a user when one of their price alerts triggers. Sending is
best-effort — failures are logged and never propagated, so a mail outage can't
break price ingestion (this runs inside the alert-evaluation signal, which in
turn runs inside the scraping worker).
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _notifications_enabled() -> bool:
    """Respect the global email-notifications feature flag."""
    try:
        from apps.core.models import SystemConfiguration
        return bool(SystemConfiguration.get_solo().enable_email_notifications)
    except Exception:
        # If configuration can't be read, default to sending.
        return True


def send_alert_notification(alert) -> bool:
    """
    Email the owner of a triggered price alert.

    Returns True if an email was dispatched, False otherwise (no recipient,
    notifications disabled, or send failure).
    """
    email = getattr(alert.user, 'email', '') or ''
    if not email:
        return False
    if not _notifications_enabled():
        logger.info("Email notifications disabled; skipping alert %s", alert.id)
        return False

    direction = (
        'dropped to or below'
        if alert.direction == alert.Direction.BELOW
        else 'rose to or above'
    )
    card = str(alert.card)
    grade_note = f" (grade {alert.grade})" if alert.grade else ""

    subject = f"Price alert: {card} {direction} ${alert.threshold_price}"
    message = "\n".join([
        "One of your Sports Card Kickoff price alerts just triggered.",
        "",
        f"Card: {card}{grade_note}",
        f"Condition: price {direction} ${alert.threshold_price}",
        f"Triggered price: ${alert.triggered_price}",
        "",
        "Log in to review the latest comps and manage your alerts.",
    ])

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Sent price-alert email for alert %s to %s", alert.id, email)
        return True
    except Exception:
        logger.exception("Failed to send price-alert email for alert %s", alert.id)
        return False


def _fmt(value) -> str:
    return f"${value:,.2f}" if value is not None else "n/a"


def send_portfolio_digest_email(user, digest) -> bool:
    """Email a user their portfolio digest. Best-effort, returns success."""
    email = getattr(user, 'email', '') or ''
    if not email:
        return False
    if not _notifications_enabled():
        logger.info("Email notifications disabled; skipping digest for %s", user.pk)
        return False

    totals = digest['valuation']['totals']
    change = digest['value_change']

    lines = [
        "Here is your Sports Card Kickoff portfolio summary.",
        "",
        f"Holdings: {totals['holdings_count']}",
        f"Total cost: {_fmt(totals['total_cost'])}",
        f"Market value: {_fmt(totals['total_market_value'])}",
        f"Unrealized P&L: {_fmt(totals['total_unrealized_pl'])}",
    ]
    if change is not None:
        direction = "up" if change >= 0 else "down"
        lines.append(f"Change since last summary: {direction} {_fmt(abs(change))}")

    try:
        send_mail(
            subject="Your Sports Card Kickoff portfolio summary",
            message="\n".join(lines),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Sent portfolio digest to %s", email)
        return True
    except Exception:
        logger.exception("Failed to send portfolio digest for user %s", user.pk)
        return False
