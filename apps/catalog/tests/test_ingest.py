from django.test import TestCase

from apps.catalog.models import Card, GradingCompany, PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.ingest import ingest_item, ingest_items
from apps.catalog.services.resolver import CardResolver


def _ebay_item(**overrides):
    item = {
        'item_id': '123456789012',
        'title': '2018-19 Panini Prizm Luka Doncic #280 Silver PSA 10 Rookie',
        'url': 'https://www.ebay.com/itm/123456789012',
        'source': 'ebay',
        'price': {'amount': 250.0, 'currency': 'USD', 'shipping': 5.99, 'total': 255.99},
        'grade': {'grading_company': 'PSA', 'grade': 'PSA 10', 'numeric_grade': 10.0},
        'listing': {'listing_type': 'buy_it_now', 'is_auction': False, 'is_buy_it_now': True},
    }
    item.update(overrides)
    return item


class IngestTests(TestCase):
    def setUp(self):
        self.resolver = CardResolver(sport=constants.SPORT_BASKETBALL)

    def test_ingest_single_item_creates_observation(self):
        obs = ingest_item(_ebay_item(), source='ebay', resolver=self.resolver)

        self.assertIsNotNone(obs)
        self.assertEqual(PriceObservation.objects.count(), 1)
        self.assertEqual(obs.source, 'ebay')
        self.assertEqual(str(obs.price), '255.99')
        self.assertEqual(obs.grade, '10')
        self.assertEqual(obs.grading_company.code, 'PSA')
        self.assertEqual(obs.card.player.name, 'Luka Doncic')
        self.assertGreater(obs.match_confidence, 0.0)

    def test_ingest_is_idempotent_by_external_id(self):
        ingest_item(_ebay_item(), source='ebay', resolver=self.resolver)
        ingest_item(_ebay_item(price={'amount': 300.0, 'currency': 'USD', 'total': 300.0}),
                    source='ebay', resolver=self.resolver)

        # Same item_id -> updated, not duplicated.
        self.assertEqual(PriceObservation.objects.count(), 1)
        obs = PriceObservation.objects.first()
        self.assertEqual(str(obs.price), '300.00')

    def test_ingest_skips_unpriced_item(self):
        item = _ebay_item()
        item['price'] = {'amount': 0, 'currency': 'USD'}
        obs = ingest_item(item, source='ebay', resolver=self.resolver)
        self.assertIsNone(obs)
        self.assertEqual(PriceObservation.objects.count(), 0)

    def test_ingest_skips_unresolved_title(self):
        item = _ebay_item(title='totally unparseable nonsense', item_id='999')
        obs = ingest_item(item, source='ebay', resolver=self.resolver)
        self.assertIsNone(obs)

    def test_ingest_batch_tolerates_bad_items(self):
        items = [
            _ebay_item(item_id='1'),
            {'title': None},  # malformed, must be skipped
            _ebay_item(item_id='2', title='2003 Topps Chrome LeBron James #111 Refractor PSA 9'),
        ]
        observations = ingest_items(items, source='ebay', resolver=self.resolver)
        self.assertEqual(len(observations), 2)
        self.assertEqual(Card.objects.count(), 2)

    def test_ingest_without_external_id_creates_each_time(self):
        item = _ebay_item(item_id='')
        item.pop('epid', None)
        ingest_item(item, source='ebay', resolver=self.resolver)
        ingest_item(item, source='ebay', resolver=self.resolver)
        # No external id -> cannot dedupe, both recorded.
        self.assertEqual(PriceObservation.objects.count(), 2)
