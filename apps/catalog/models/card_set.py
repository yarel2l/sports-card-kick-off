import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from ..services import constants


class CardSet(models.Model):
    """
    A specific product release, e.g. "2018 Panini Prizm Basketball".

    This is the spine that individual canonical :class:`Card` rows hang from.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    year = models.PositiveSmallIntegerField(verbose_name=_('Year'))
    brand = models.CharField(max_length=80, verbose_name=_('Brand'))
    name = models.CharField(
        max_length=120,
        verbose_name=_('Set Name'),
        help_text=_('Product line, e.g. "Prizm", "Chrome"'),
    )
    sport = models.CharField(
        max_length=20,
        choices=constants.SPORT_CHOICES,
        default=constants.SPORT_OTHER,
        verbose_name=_('Sport'),
    )
    slug = models.SlugField(max_length=200, unique=True, verbose_name=_('Slug'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_card_sets'
        verbose_name = _('Card Set')
        verbose_name_plural = _('Card Sets')
        ordering = ['-year', 'brand', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['year', 'brand', 'name', 'sport'],
                name='uniq_card_set',
            ),
        ]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['year']),
            models.Index(fields=['brand']),
        ]

    @staticmethod
    def build_slug(year, brand, name, sport) -> str:
        return slugify(f"{year}-{brand}-{name}-{sport}")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.build_slug(self.year, self.brand, self.name, self.sport)
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return f"{self.year} {self.brand} {self.name}".strip()

    def __str__(self):
        return self.display_name
