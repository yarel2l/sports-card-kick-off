from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from apps.catalog.models import Card, CardSet, PriceObservation
from apps.core.models import SystemConfiguration
from apps.portfolio.models import PriceAlert
from apps.portfolio.notifications import send_alert_notification

User = get_user_model()


class AlertNotificationTests(TestCase):
    def setUp(self):
        cs = CardSet.objects.create(year=2018, brand='Panini', name='Prizm', sport='BASKETBALL')
        self.card = Card.objects.create(card_set=cs, canonical_key='k-280', card_number='280')
        self.user = User.objects.create_user(
            email='collector@example.com', username='collector', password='pass12345'
        )

    def _alert(self, **kw):
        defaults = dict(
            user=self.user, card=self.card, direction=PriceAlert.Direction.BELOW,
            threshold_price=Decimal('200'),
        )
        defaults.update(kw)
        return PriceAlert.objects.create(**defaults)

    def test_email_sent_when_alert_triggers(self):
        self._alert(threshold_price=Decimal('200'))
        # Creating a qualifying observation triggers the signal -> evaluation -> email.
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('180'), grade='10'
        )
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['collector@example.com'])
        self.assertIn('Price alert', msg.subject)
        self.assertIn('180', msg.body)

    def test_no_email_when_not_triggered(self):
        self._alert(threshold_price=Decimal('100'))
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('180'), grade='10'
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_respects_global_notifications_flag(self):
        config = SystemConfiguration.get_solo()
        config.enable_email_notifications = False
        config.save()

        alert = self._alert(threshold_price=Decimal('200'))
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('180'), grade='10'
        )
        # Alert still fires (deactivated), but no email is sent.
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_without_recipient(self):
        # A user without an email address should be skipped gracefully.
        user = User.objects.create_user(email='', username='noemail', password='pass12345')
        alert = self._alert(user=user, threshold_price=Decimal('200'))
        self.assertFalse(send_alert_notification(alert))
        self.assertEqual(len(mail.outbox), 0)
