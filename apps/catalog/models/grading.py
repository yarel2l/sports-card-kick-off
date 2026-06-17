import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class GradingCompany(models.Model):
    """A third-party grading company (PSA, BGS, SGC, ...)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        max_length=10, unique=True, verbose_name=_('Code')
    )
    name = models.CharField(max_length=120, verbose_name=_('Name'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_grading_companies'
        verbose_name = _('Grading Company')
        verbose_name_plural = _('Grading Companies')
        ordering = ['code']

    def __str__(self):
        return self.code
