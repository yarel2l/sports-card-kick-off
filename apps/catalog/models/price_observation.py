import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PriceObservation(models.Model):
    """
    A single observed price for a canonical card from some source.

    This is the raw material for pricing intelligence: each scraped/aggregated
    listing or sale becomes one observation tied to a :class:`Card` and an
    optional grade. Aggregations (market value, trends) are built on top of
    these rows.
    """

    class Kind(models.TextChoices):
        LISTING = 'LISTING', _('Active Listing')
        SOLD = 'SOLD', _('Sold / Completed')
        AUCTION = 'AUCTION', _('Auction')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    card = models.ForeignKey(
        'catalog.Card',
        on_delete=models.CASCADE,
        related_name='price_observations',
        verbose_name=_('Card'),
    )

    source = models.CharField(
        max_length=40,
        help_text=_('Source identifier, e.g. "ebay"'),
        verbose_name=_('Source'),
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.LISTING,
        verbose_name=_('Kind'),
    )

    grading_company = models.ForeignKey(
        'catalog.GradingCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_observations',
        verbose_name=_('Grading Company'),
    )
    grade = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('Grade value, e.g. "10", "9.5". Blank for raw.'),
        verbose_name=_('Grade'),
    )

    price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_('Price')
    )
    currency = models.CharField(max_length=3, default='USD', verbose_name=_('Currency'))

    url = models.URLField(max_length=600, blank=True, verbose_name=_('Source URL'))
    external_id = models.CharField(
        max_length=120, blank=True, verbose_name=_('External ID')
    )
    raw_title = models.TextField(blank=True, verbose_name=_('Raw Title'))
    match_confidence = models.FloatField(
        default=0.0,
        help_text=_('Resolver confidence that this observation maps to the card'),
        verbose_name=_('Match Confidence'),
    )

    observed_at = models.DateTimeField(
        default=timezone.now, verbose_name=_('Observed At')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_price_observations'
        verbose_name = _('Price Observation')
        verbose_name_plural = _('Price Observations')
        ordering = ['-observed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                condition=models.Q(external_id__gt=''),
                name='uniq_source_external_id',
            ),
        ]
        indexes = [
            models.Index(fields=['card', '-observed_at']),
            models.Index(fields=['source']),
            models.Index(fields=['grade']),
        ]

    def __str__(self):
        grade = f" {self.grade}" if self.grade else ""
        return f"{self.source}{grade}: {self.price} {self.currency}"
