import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PortfolioHolding(models.Model):
    """A card a user owns, with cost basis, used for portfolio valuation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='holdings',
        verbose_name=_('User'),
    )
    card = models.ForeignKey(
        'catalog.Card',
        on_delete=models.CASCADE,
        related_name='holdings',
        verbose_name=_('Card'),
    )

    grading_company = models.ForeignKey(
        'catalog.GradingCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='holdings',
        verbose_name=_('Grading Company'),
    )
    grade = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('Grade owned, e.g. "10". Blank for raw.'),
        verbose_name=_('Grade'),
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name=_('Quantity'))
    cost_basis = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_('Per-unit acquisition cost'),
        verbose_name=_('Cost Basis (per unit)'),
    )
    currency = models.CharField(max_length=3, default='USD', verbose_name=_('Currency'))

    acquired_at = models.DateField(null=True, blank=True, verbose_name=_('Acquired At'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portfolio_holdings'
        verbose_name = _('Portfolio Holding')
        verbose_name_plural = _('Portfolio Holdings')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['card']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.card_id} @ {self.cost_basis}"
