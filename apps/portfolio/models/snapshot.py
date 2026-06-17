import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PortfolioSnapshot(models.Model):
    """
    A point-in-time valuation of a user's portfolio.

    Captured when a digest is sent so the next digest can report the change in
    market value since the previous one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portfolio_snapshots',
        verbose_name=_('User'),
    )

    holdings_count = models.PositiveIntegerField(default=0, verbose_name=_('Holdings Count'))
    total_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name=_('Total Cost')
    )
    total_market_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name=_('Total Market Value'),
    )
    total_unrealized_pl = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name=_('Total Unrealized P&L'),
    )

    captured_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Captured At'))

    class Meta:
        db_table = 'portfolio_snapshots'
        verbose_name = _('Portfolio Snapshot')
        verbose_name_plural = _('Portfolio Snapshots')
        ordering = ['-captured_at']
        indexes = [models.Index(fields=['user', '-captured_at'])]

    def __str__(self):
        return f"Snapshot {self.user_id} @ {self.captured_at:%Y-%m-%d}"
