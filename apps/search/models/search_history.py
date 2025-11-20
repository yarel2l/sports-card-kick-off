import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SearchHistory(models.Model):
    """
    Tracks user search history for analytics and quick re-search functionality.
    Lightweight model to store frequently searched queries per user.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history',
        verbose_name=_('User')
    )

    search = models.ForeignKey(
        'search.Search',
        on_delete=models.CASCADE,
        related_name='history_entries',
        verbose_name=_('Search')
    )

    query = models.CharField(
        max_length=500,
        verbose_name=_('Search Query')
    )

    was_successful = models.BooleanField(
        default=False,
        help_text=_('Whether the search completed successfully'),
        verbose_name=_('Was Successful')
    )

    total_results = models.IntegerField(
        default=0,
        help_text=_('Total number of results found'),
        verbose_name=_('Total Results')
    )

    accessed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Accessed At')
    )

    class Meta:
        db_table = 'search_history'
        verbose_name = _('Search History Entry')
        verbose_name_plural = _('Search History')
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['user', '-accessed_at']),
            models.Index(fields=['query']),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.query}"
