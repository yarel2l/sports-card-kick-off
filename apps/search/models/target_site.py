import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class TargetSite(models.Model):
    """
    Represents a target website for scraping sports card data.
    Each site has specific configuration for scraping.
    """

    class SiteType(models.TextChoices):
        SALES = 'SALES', _('Sales Platform')
        AUCTION = 'AUCTION', _('Auction House')
        POPULATION = 'POPULATION', _('Population Data')
        MARKETPLACE = 'MARKETPLACE', _('Marketplace')

    class Priority(models.TextChoices):
        CRITICAL = 'CRITICAL', _('Critical')
        HIGH = 'HIGH', _('High')
        MEDIUM = 'MEDIUM', _('Medium')
        LOW = 'LOW', _('Low')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Site Name')
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_('Slug')
    )

    base_url = models.URLField(
        verbose_name=_('Base URL')
    )

    site_type = models.CharField(
        max_length=20,
        choices=SiteType.choices,
        default=SiteType.SALES,
        verbose_name=_('Site Type')
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_('Priority')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )

    agent_class_name = models.CharField(
        max_length=100,
        help_text=_('Name of the agent class (e.g., EbayAgent)'),
        verbose_name=_('Agent Class Name')
    )

    timeout_seconds = models.IntegerField(
        default=30,
        help_text=_('Timeout in seconds for scraping this site'),
        verbose_name=_('Timeout (seconds)')
    )

    max_retries = models.IntegerField(
        default=3,
        help_text=_('Maximum number of retry attempts'),
        verbose_name=_('Max Retries')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'target_sites'
        verbose_name = _('Target Site')
        verbose_name_plural = _('Target Sites')
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.name} ({self.site_type})"
