import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class ScrapeResult(models.Model):
    """
    Stores the results of scraping from a specific site for a specific search.
    One record per (search, target_site) combination.
    """

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')
        TIMEOUT = 'TIMEOUT', _('Timeout')
        NO_RESULTS = 'NO_RESULTS', _('No Results')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    search = models.ForeignKey(
        'search.Search',
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('Search')
    )

    target_site = models.ForeignKey(
        'search.TargetSite',
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('Target Site')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        verbose_name=_('Status')
    )

    # Result data stored as JSON
    data = models.JSONField(
        default=dict,
        help_text=_('Scraped data in JSON format'),
        verbose_name=_('Data')
    )

    items_count = models.IntegerField(
        default=0,
        help_text=_('Number of items found'),
        verbose_name=_('Items Count')
    )

    execution_time_seconds = models.FloatField(
        blank=True,
        null=True,
        help_text=_('Execution time for this site in seconds'),
        verbose_name=_('Execution Time (s)')
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Error Message')
    )

    retry_count = models.IntegerField(
        default=0,
        help_text=_('Number of retry attempts made'),
        verbose_name=_('Retry Count')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    class Meta:
        db_table = 'scrape_results'
        verbose_name = _('Scrape Result')
        verbose_name_plural = _('Scrape Results')
        ordering = ['-created_at']
        unique_together = [['search', 'target_site']]
        indexes = [
            models.Index(fields=['search', '-created_at']),
            models.Index(fields=['target_site', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.target_site.name}: {self.status} ({self.items_count} items)"
