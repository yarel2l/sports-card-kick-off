import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class WatchlistItem(models.Model):
    """A card a user follows (lightweight 'favorite')."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watchlist',
        verbose_name=_('User'),
    )
    card = models.ForeignKey(
        'catalog.Card',
        on_delete=models.CASCADE,
        related_name='watched_by',
        verbose_name=_('Card'),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portfolio_watchlist'
        verbose_name = _('Watchlist Item')
        verbose_name_plural = _('Watchlist Items')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'card'], name='uniq_user_card_watch'),
        ]
        indexes = [models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        return f"{self.user_id} watches {self.card_id}"
