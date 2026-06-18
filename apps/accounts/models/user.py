import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Uses UUID as primary key for better security and scalability.
    """

    account_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Account ID')
    )

    email = models.EmailField(
        unique=True,
        verbose_name=_('Email Address')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )

    email_verified = models.BooleanField(
        default=False,
        help_text=_('Whether the user has confirmed their email address'),
        verbose_name=_('Email Verified')
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return self.email
