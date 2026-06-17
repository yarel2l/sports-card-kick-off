from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.ingest import ingest_item, ingest_items
from apps.catalog.services.resolver import CardResolver


def _point130_item(**overrides):
    """A 130Point-style completed-sale item (as produced by Point130Item)."""
    item = {
        'item_id': 'abc123',
        'title': '2018 Panini Prizm Luka Doncic #280 PSA 10',
        'url': 'https://130point.com/s/1',
        'source': '130point',
        'price': {'amount': 450.0, 'currency': 'USD', 'shipping': None, 'total': 450.0},
        'grade': {'grading_company': 'PSA', 'grade': 'PSA 10', 'numeric_grade': 10.0},
        'sale_type': 'auction',
    }
    item.update(overrides)
    return item


class SoldIngestTests(TestCase):
    def setUp(self):
        self.resolver = CardResolver(sport=constants.SPORT_BASKETBALL)

    def test_sale_type_recorded_as_sold(self):
        obs = ingest_item(_point130_item(), source='130point', resolver=self.resolver)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.kind, PriceObservation.Kind.SOLD)
        self.assertEqual(obs.source, '130point')
        self.assertEqual(Decimal(obs.price), Decimal('450.00'))
        self.assertEqual(obs.grade, '10')

    def test_mixed_sources_record_distinct_kinds(self):
        ebay_listing = {
            'item_id': 'e1',
            'title': '2018 Panini Prizm Luka Doncic #280 PSA 10',
            'url': 'https://ebay.com/itm/e1',
            'source': 'ebay',
            'price': {'amount': 500.0, 'currency': 'USD', 'total': 500.0},
            'grade': {'grading_company': 'PSA', 'grade': 'PSA 10', 'numeric_grade': 10.0},
            'listing': {'is_auction': False, 'is_buy_it_now': True},
        }
        ingest_items([_point130_item(), ebay_listing], source='multi', resolver=self.resolver)

        kinds = set(PriceObservation.objects.values_list('kind', flat=True))
        self.assertEqual(
            kinds,
            {PriceObservation.Kind.SOLD, PriceObservation.Kind.LISTING},
        )
        # Both resolved to the same canonical card.
        self.assertEqual(
            PriceObservation.objects.values('card').distinct().count(), 1
        )
