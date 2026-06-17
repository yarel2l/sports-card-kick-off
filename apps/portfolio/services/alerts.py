"""
Price-alert evaluation.

Given a new price observation, find the active alerts for that card whose
threshold is crossed and fire them (one-shot). Kept dependency-light so it can
be called from a signal handler on every ingested observation.
"""

from __future__ import annotations

import logging
from typing import List

from django.utils import timezone

from ..models import PriceAlert

logger = logging.getLogger(__name__)


def evaluate_alerts_for_observation(observation) -> List[PriceAlert]:
    """
    Evaluate active alerts against a single :class:`PriceObservation`.

    Returns the list of alerts that fired.
    """
    alerts = PriceAlert.objects.filter(card_id=observation.card_id, is_active=True)
    fired: List[PriceAlert] = []

    for alert in alerts:
        if alert.matches(observation.price, grade=observation.grade or ''):
            alert.is_active = False
            alert.triggered_at = timezone.now()
            alert.triggered_price = observation.price
            alert.save(update_fields=['is_active', 'triggered_at', 'triggered_price', 'updated_at'])
            fired.append(alert)
            logger.info(
                "Price alert %s fired at %s for card %s",
                alert.id, observation.price, observation.card_id,
            )
            # Notify the owner. Best-effort: never let a mail failure break
            # ingestion or the rest of the alert batch.
            try:
                from ..notifications import send_alert_notification
                send_alert_notification(alert)
            except Exception:
                logger.exception("Alert notification dispatch failed for %s", alert.id)

    return fired
