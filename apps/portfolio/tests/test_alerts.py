from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.portfolio.models import PriceAlert
from apps.portfolio.services.alerts import evaluate_alerts_for_observation

User = get_user_model()


class AlertLogicTests(TestCase):
    def setUp(self):
        cs = CardSet.objects.create(year=2018, brand='Panini', name='Prizm', sport='BASKETBALL')
        self.card = Card.objects.create(card_set=cs, canonical_key='k-280', card_number='280')
        self.user = User.objects.create_user(
            email='u@example.com', username='u', password='pass12345'
        )

    def _alert(self, **kw):
        defaults = dict(
            user=self.user, card=self.card, direction=PriceAlert.Direction.BELOW,
            threshold_price=Decimal('200'),
        )
        defaults.update(kw)
        return PriceAlert.objects.create(**defaults)

    def test_matches_below(self):
        alert = self._alert(direction=PriceAlert.Direction.BELOW, threshold_price=Decimal('200'))
        self.assertTrue(alert.matches(Decimal('150')))
        self.assertTrue(alert.matches(Decimal('200')))
        self.assertFalse(alert.matches(Decimal('250')))

    def test_matches_above(self):
        alert = self._alert(direction=PriceAlert.Direction.ABOVE, threshold_price=Decimal('300'))
        self.assertTrue(alert.matches(Decimal('350')))
        self.assertFalse(alert.matches(Decimal('250')))

    def test_grade_restriction(self):
        alert = self._alert(grade='10', threshold_price=Decimal('200'))
        self.assertTrue(alert.matches(Decimal('150'), grade='10'))
        # Wrong grade should not match a grade-restricted alert.
        self.assertFalse(alert.matches(Decimal('150'), grade='9'))
        self.assertFalse(alert.matches(Decimal('150'), grade=''))

    def test_inactive_never_matches(self):
        alert = self._alert(is_active=False)
        self.assertFalse(alert.matches(Decimal('1')))

    def test_evaluate_fires_and_deactivates(self):
        alert = self._alert(threshold_price=Decimal('200'))
        obs = PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('180'), grade='10'
        )
        # The post_save signal already evaluated; the alert should be fired.
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
        self.assertEqual(alert.triggered_price, Decimal('180'))
        self.assertIsNotNone(alert.triggered_at)

        # Re-evaluating explicitly returns nothing (already inactive).
        self.assertEqual(evaluate_alerts_for_observation(obs), [])

    def test_signal_does_not_fire_when_above_threshold(self):
        alert = self._alert(threshold_price=Decimal('100'))
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('180'), grade='10'
        )
        alert.refresh_from_db()
        self.assertTrue(alert.is_active)
        self.assertIsNone(alert.triggered_at)
