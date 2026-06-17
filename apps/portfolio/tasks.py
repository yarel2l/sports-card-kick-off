"""
Celery tasks for the portfolio app.

``send_portfolio_digests`` is intended to run on a schedule (see
CELERY_BEAT_SCHEDULE) and emails every user who holds at least one card a
summary of their portfolio's current value and its change since the last digest.
"""

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_portfolio_digests() -> Dict[str, Any]:
    """Send a portfolio digest to every user that currently holds cards."""
    from .models import PortfolioHolding
    from .services.digest import deliver_digest
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user_ids = (
        PortfolioHolding.objects.values_list('user_id', flat=True).distinct()
    )

    sent = 0
    processed = 0
    for user in User.objects.filter(pk__in=list(user_ids)):
        processed += 1
        try:
            if deliver_digest(user):
                sent += 1
        except Exception:
            logger.exception("Failed to deliver portfolio digest to user %s", user.pk)

    logger.info("Portfolio digests: %s sent / %s users", sent, processed)
    return {'users': processed, 'emails_sent': sent}
