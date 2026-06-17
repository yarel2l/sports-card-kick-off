"""
Signal wiring: evaluate price alerts whenever a new price observation lands.

Decoupled from the catalog/scraping ingest path — ingestion just creates
``PriceObservation`` rows and this receiver reacts. Failures are swallowed so
alert evaluation can never break ingestion.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.catalog.models import PriceObservation

from .services.alerts import evaluate_alerts_for_observation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PriceObservation, dispatch_uid='portfolio_eval_alerts')
def _evaluate_alerts(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        evaluate_alerts_for_observation(instance)
    except Exception:
        logger.exception("Price alert evaluation failed for observation %s", instance.pk)
