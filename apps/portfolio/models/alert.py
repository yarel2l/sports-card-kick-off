import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PriceAlert(models.Model):
    """
    A user-defined price threshold for a card.

    When a new price observation crosses the threshold (below or above), the
    alert fires: it records the triggering price/time and deactivates itself
    (one-shot), so the user can re-arm it if desired.
    """

    class Direction(models.TextChoices):
        BELOW = 'BELOW', _('Price drops to or below')
        ABOVE = 'ABOVE', _('Price rises to or above')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        verbose_name=_('User'),
    )
    card = models.ForeignKey(
        'catalog.Card',
        on_delete=models.CASCADE,
        related_name='price_alerts',
        verbose_name=_('Card'),
    )

    grade = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('Restrict to a grade, e.g. "10". Blank matches any grade.'),
        verbose_name=_('Grade'),
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.BELOW,
        verbose_name=_('Direction'),
    )
    threshold_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_('Threshold Price')
    )

    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    triggered_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Triggered At'))
    triggered_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name=_('Triggered Price'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portfolio_price_alerts'
        verbose_name = _('Price Alert')
        verbose_name_plural = _('Price Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['card', 'is_active']),
        ]

    def matches(self, price, grade: str = '') -> bool:
        """Return True if ``price`` (at ``grade``) crosses this alert."""
        if not self.is_active:
            return False
        if self.grade and grade and self.grade != grade:
            return False
        if self.grade and not grade:
            return False
        if self.direction == self.Direction.BELOW:
            return price <= self.threshold_price
        return price >= self.threshold_price

    def __str__(self):
        return f"Alert {self.direction} {self.threshold_price} on {self.card_id}"
