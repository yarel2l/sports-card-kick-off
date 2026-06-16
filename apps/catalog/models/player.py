import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from ..services import constants


class Player(models.Model):
    """A canonical athlete that cards depict."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=150, verbose_name=_('Name'))
    slug = models.SlugField(max_length=180, unique=True, verbose_name=_('Slug'))

    sport = models.CharField(
        max_length=20,
        choices=constants.SPORT_CHOICES,
        default=constants.SPORT_OTHER,
        verbose_name=_('Sport'),
    )

    aliases = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Alternate spellings/nicknames used in listings'),
        verbose_name=_('Aliases'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_players'
        verbose_name = _('Player')
        verbose_name_plural = _('Players')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sport']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.sport}") or str(self.id)
            self.slug = base
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
