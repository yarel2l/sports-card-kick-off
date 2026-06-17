"""
Server-side helpers to push real-time events to a user's WebSocket group.

All helpers are best-effort: if the channel layer is unavailable (e.g. Redis
down) the failure is swallowed so background tasks and signals are never broken
by a realtime-delivery problem.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def notify_user(user_pk, event: str, data: Dict[str, Any]) -> None:
    """Push ``{event, data}`` to the user's notification group."""
    try:
        from .consumers import user_group_name
        from .helpers import send_to_group

        send_to_group(
            user_group_name(user_pk),
            {'type': 'notify', 'event': event, 'data': data},
        )
    except Exception:
        logger.exception("Failed to push realtime event '%s' to user %s", event, user_pk)


def notify_search_update(search) -> None:
    """Push a search status update to its owner."""
    notify_user(search.user_id, 'search.status', {
        'search_id': str(search.id),
        'status': search.status,
        'total_items_found': search.total_items_found,
    })


def notify_alert_triggered(alert) -> None:
    """Push a triggered-alert event to its owner."""
    notify_user(alert.user_id, 'alert.triggered', {
        'alert_id': str(alert.id),
        'card_id': str(alert.card_id),
        'direction': alert.direction,
        'threshold_price': str(alert.threshold_price),
        'triggered_price': str(alert.triggered_price) if alert.triggered_price is not None else None,
    })
