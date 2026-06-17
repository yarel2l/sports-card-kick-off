from django.db import connection
from django.test import TestCase

from apps.core.fields import EncryptedCharField, get_fernet
from apps.core.models import SystemConfiguration


class EncryptedFieldTests(TestCase):
    def test_field_roundtrip_helper(self):
        field = EncryptedCharField()
        stored = field.get_prep_value('sk-secret-123')
        self.assertTrue(stored.startswith('enc:v1:'))
        self.assertNotIn('sk-secret-123', stored)
        decrypted = field.from_db_value(stored, None, connection)
        self.assertEqual(decrypted, 'sk-secret-123')

    def test_empty_values_pass_through(self):
        field = EncryptedCharField()
        self.assertEqual(field.get_prep_value(''), '')
        self.assertIsNone(field.get_prep_value(None))

    def test_idempotent_encryption(self):
        field = EncryptedCharField()
        once = field.get_prep_value('token')
        twice = field.get_prep_value(once)
        self.assertEqual(once, twice)

    def test_api_key_encrypted_at_rest(self):
        cfg = SystemConfiguration.get_solo()
        cfg.openai_api_key = 'sk-live-supersecret'
        cfg.save()

        # Through the ORM the value is transparently decrypted.
        reloaded = SystemConfiguration.objects.get(pk=cfg.pk)
        self.assertEqual(reloaded.openai_api_key, 'sk-live-supersecret')
        self.assertTrue(reloaded.has_openai_configured)

        # In the database it is ciphertext, not the plaintext key.
        table = SystemConfiguration._meta.db_table
        with connection.cursor() as cur:
            cur.execute(f'SELECT openai_api_key FROM {table} WHERE id = %s', [cfg.pk])
            raw = cur.fetchone()[0]
        self.assertTrue(raw.startswith('enc:v1:'))
        self.assertNotIn('sk-live-supersecret', raw)

    def test_legacy_plaintext_is_readable(self):
        # Simulate a value written before encryption was enabled.
        cfg = SystemConfiguration.get_solo()
        table = SystemConfiguration._meta.db_table
        with connection.cursor() as cur:
            cur.execute(
                f'UPDATE {table} SET anthropic_api_key = %s WHERE id = %s',
                ['legacy-plaintext-key', cfg.pk],
            )
        reloaded = SystemConfiguration.objects.get(pk=cfg.pk)
        self.assertEqual(reloaded.anthropic_api_key, 'legacy-plaintext-key')

    def test_decrypt_matches_fernet(self):
        field = EncryptedCharField()
        stored = field.get_prep_value('abc')
        token = stored[len('enc:v1:'):]
        self.assertEqual(get_fernet().decrypt(token.encode()).decode(), 'abc')
