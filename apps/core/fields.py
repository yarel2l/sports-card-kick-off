"""
Transparent application-level encryption for sensitive model fields.

``EncryptedCharField`` stores its value encrypted at rest (Fernet / AES-128-CBC
+ HMAC) and decrypts it on load, so application code keeps reading and writing
plain strings while the database only ever holds ciphertext.

Key management:
- Set ``FIELD_ENCRYPTION_KEY`` (one or more comma-separated urlsafe-base64
  Fernet keys) in the environment for production. Multiple keys enable
  rotation: the first encrypts, all are tried on decrypt.
- If unset, a key is derived from ``SECRET_KEY`` so development/tests work with
  no extra setup. This derived key is NOT suitable for production.

Legacy plaintext values (written before encryption was enabled) are detected by
the absence of the version prefix and returned as-is, so enabling encryption is
a no-downtime change.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.db import models

_PREFIX = 'enc:v1:'
_fernet = None


def _derive_key_from_secret() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _build_fernet():
    raw_keys = getattr(settings, 'FIELD_ENCRYPTION_KEYS', None)
    if raw_keys:
        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in raw_keys]
    else:
        fernets = [Fernet(_derive_key_from_secret())]
    return MultiFernet(fernets) if len(fernets) > 1 else fernets[0]


def get_fernet():
    global _fernet
    if _fernet is None:
        _fernet = _build_fernet()
    return _fernet


def reset_fernet_cache():
    """Clear the cached cipher (used by tests that swap encryption keys)."""
    global _fernet
    _fernet = None


class EncryptedCharField(models.TextField):
    """A text field encrypted at rest, transparent to application code."""

    description = "Application-encrypted text field"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        # Idempotent: never double-encrypt an already-encrypted value.
        if isinstance(value, str) and value.startswith(_PREFIX):
            return value
        token = get_fernet().encrypt(str(value).encode()).decode()
        return _PREFIX + token

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        if value.startswith(_PREFIX):
            try:
                return get_fernet().decrypt(value[len(_PREFIX):].encode()).decode()
            except InvalidToken:
                # Wrong/rotated-out key: return raw rather than crash reads.
                return value
        # Legacy plaintext written before encryption was enabled.
        return value
