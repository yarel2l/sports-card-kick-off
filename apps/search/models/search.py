import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Search(models.Model):
    """
    Represents a search query initiated by a user.
    Tracks the status and metadata of each search operation.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        PARTIAL = 'PARTIAL', _('Partial Success')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='searches',
        verbose_name=_('User')
    )

    query = models.CharField(
        max_length=500,
        verbose_name=_('Search Query')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Status')
    )

    # Parsed query components (populated by QueryProcessor)
    player_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Player Name')
    )

    card_year = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Card Year')
    )

    card_set = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Card Set')
    )

    grade = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_('PSA 10, BGS 9.5, etc.'),
        verbose_name=_('Grade')
    )

    # Execution metadata
    total_sites = models.IntegerField(
        default=0,
        help_text=_('Total number of sites queried'),
        verbose_name=_('Total Sites')
    )

    successful_sites = models.IntegerField(
        default=0,
        help_text=_('Number of sites that returned results'),
        verbose_name=_('Successful Sites')
    )

    failed_sites = models.IntegerField(
        default=0,
        help_text=_('Number of sites that failed'),
        verbose_name=_('Failed Sites')
    )

    total_items_found = models.IntegerField(
        default=0,
        help_text=_('Total number of items found across all sites'),
        verbose_name=_('Total Items Found')
    )

    execution_time_seconds = models.FloatField(
        blank=True,
        null=True,
        help_text=_('Total execution time in seconds'),
        verbose_name=_('Execution Time (s)')
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Error Message')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Completed At')
    )

    class Meta:
        db_table = 'searches'
        verbose_name = _('Search')
        verbose_name_plural = _('Searches')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['player_name']),
        ]

    def __str__(self):
        return f"Search: {self.query} ({self.status})"
