import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Card(models.Model):
    """
    A canonical, ungraded card entity.

    Identity is the combination of (set, card number, parallel, player). The
    ``canonical_key`` is a deterministic slug derived from those parts so the
    resolver can de-duplicate listings into a single catalog row regardless of
    how noisy the source title was.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    card_set = models.ForeignKey(
        'catalog.CardSet',
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name=_('Card Set'),
    )
    player = models.ForeignKey(
        'catalog.Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cards',
        verbose_name=_('Player'),
    )

    card_number = models.CharField(
        max_length=20, blank=True, verbose_name=_('Card Number')
    )
    parallel = models.CharField(
        max_length=80,
        blank=True,
        help_text=_('Parallel/variation, e.g. "Silver", "Refractor"'),
        verbose_name=_('Parallel'),
    )

    is_rookie = models.BooleanField(default=False, verbose_name=_('Rookie'))
    is_autograph = models.BooleanField(default=False, verbose_name=_('Autograph'))
    is_memorabilia = models.BooleanField(default=False, verbose_name=_('Memorabilia'))
    serial_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Print run limit, e.g. 99 for a /99 parallel'),
        verbose_name=_('Serial Limit'),
    )

    attributes = models.JSONField(
        default=dict, blank=True, verbose_name=_('Extra Attributes')
    )

    canonical_key = models.SlugField(
        max_length=255, unique=True, verbose_name=_('Canonical Key')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_cards'
        verbose_name = _('Card')
        verbose_name_plural = _('Cards')
        ordering = ['card_set', 'card_number']
        indexes = [
            models.Index(fields=['canonical_key']),
            models.Index(fields=['card_set', 'card_number']),
            models.Index(fields=['player']),
        ]

    @staticmethod
    def build_canonical_key(set_slug, card_number, parallel, player_slug) -> str:
        parts = [
            set_slug or 'unknown-set',
            (card_number or 'na').lower(),
            slugify(parallel) if parallel else 'base',
            player_slug or 'unknown-player',
        ]
        return slugify('-'.join(parts))[:255]

    def __str__(self):
        bits = [self.card_set.display_name if self.card_set_id else '', self.player.name if self.player_id else '']
        if self.card_number:
            bits.append(f"#{self.card_number}")
        if self.parallel:
            bits.append(self.parallel)
        return ' '.join(b for b in bits if b).strip() or self.canonical_key
