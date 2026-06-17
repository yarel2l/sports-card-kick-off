from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.catalog.services import pricing


class PricingTests(TestCase):
    def setUp(self):
        self.card_set = CardSet.objects.create(
            year=2018, brand='Panini', name='Prizm', sport='BASKETBALL'
        )
        self.card = Card.objects.create(
            card_set=self.card_set, canonical_key='k-luka-280', card_number='280'
        )
        self.psa = GradingCompany.objects.create(code='PSA', name='PSA')
        now = timezone.now()

        def obs(price, grade, days_ago=0, company=self.psa):
            PriceObservation.objects.create(
                card=self.card, source='ebay', price=Decimal(price), grade=grade,
                grading_company=company, observed_at=now - timedelta(days=days_ago),
            )

        # PSA 10: 200, 300, 400 (avg 300, median 300)
        obs('200', '10', days_ago=10)
        obs('300', '10', days_ago=5)
        obs('400', '10', days_ago=1)
        # PSA 9: 100, 150
        obs('100', '9', days_ago=8)
        obs('150', '9', days_ago=2)

    def test_overall_summary(self):
        s = pricing.market_summary(self.card)
        self.assertEqual(s['count'], 5)
        self.assertEqual(s['min'], Decimal('100.00'))
        self.assertEqual(s['max'], Decimal('400.00'))
        self.assertEqual(s['last'], Decimal('400.00'))  # most recent observation
        self.assertEqual(s['currency'], 'USD')

    def test_summary_filtered_by_grade(self):
        s = pricing.market_summary(self.card, grade='10')
        self.assertEqual(s['count'], 3)
        self.assertEqual(s['avg'], Decimal('300.00'))
        self.assertEqual(s['median'], Decimal('300.00'))

    def test_summary_window(self):
        s = pricing.market_summary(self.card, window_days=3)
        # Only the 400 (1d) and 150 (2d) observations fall in the window.
        self.assertEqual(s['count'], 2)
        self.assertEqual(s['max'], Decimal('400.00'))

    def test_by_grade_breakdown(self):
        rows = pricing.market_by_grade(self.card)
        by_grade = {r['grade']: r for r in rows}
        self.assertEqual(by_grade['10']['count'], 3)
        self.assertEqual(by_grade['9']['count'], 2)
        self.assertEqual(by_grade['10']['grading_company'], 'PSA')

    def test_price_history_buckets(self):
        history = pricing.price_history(self.card, interval='day', grade='10')
        self.assertEqual(len(history), 3)  # three distinct days
        self.assertTrue(all('avg' in row and 'bucket' in row for row in history))
        # Buckets are ordered ascending.
        buckets = [row['bucket'] for row in history]
        self.assertEqual(buckets, sorted(buckets))

    def test_card_market_bundle(self):
        bundle = pricing.card_market(self.card)
        self.assertIn('overall', bundle)
        self.assertIn('by_grade', bundle)
        self.assertEqual(bundle['overall']['count'], 5)

    def test_empty_card_summary(self):
        empty = Card.objects.create(
            card_set=self.card_set, canonical_key='k-empty', card_number='1'
        )
        s = pricing.market_summary(empty)
        self.assertEqual(s['count'], 0)
        self.assertIsNone(s['avg'])
        self.assertIsNone(s['last'])
