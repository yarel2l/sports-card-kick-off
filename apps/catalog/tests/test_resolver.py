from django.test import TestCase

from apps.catalog.models import Card, CardSet, Player
from apps.catalog.services import constants
from apps.catalog.services.resolver import CardResolver


class CardResolverTests(TestCase):
    def test_creates_full_catalog_entry(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        result = resolver.resolve(
            '2018-19 Panini Prizm Luka Doncic #280 Silver PSA 10 Rookie'
        )

        self.assertIsNotNone(result.card)
        self.assertTrue(result.created_card)
        self.assertTrue(result.created_player)
        self.assertTrue(result.created_set)
        self.assertGreaterEqual(result.confidence, 0.8)

        card = result.card
        self.assertEqual(card.card_number, '280')
        self.assertEqual(card.parallel, 'Silver')
        self.assertTrue(card.is_rookie)
        self.assertEqual(card.player.name, 'Luka Doncic')
        self.assertEqual(card.card_set.brand, 'Panini')
        self.assertEqual(card.card_set.year, 2018)

    def test_idempotent_resolution(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        title = '2018-19 Panini Prizm Luka Doncic #280 Silver'
        first = resolver.resolve(title)
        second = resolver.resolve(title)

        self.assertEqual(first.card.id, second.card.id)
        self.assertTrue(first.created_card)
        self.assertFalse(second.created_card)
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(Player.objects.count(), 1)

    def test_different_parallels_are_distinct_cards(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        base = resolver.resolve('2018 Panini Prizm Luka Doncic #280')
        silver = resolver.resolve('2018 Panini Prizm Luka Doncic #280 Silver')

        self.assertNotEqual(base.card.id, silver.card.id)
        self.assertEqual(Card.objects.count(), 2)
        # Same set + player reused.
        self.assertEqual(CardSet.objects.count(), 1)
        self.assertEqual(Player.objects.count(), 1)

    def test_fuzzy_player_match_reuses_player(self):
        Player.objects.create(name='Luka Doncic', sport=constants.SPORT_BASKETBALL)
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        # Slight misspelling should still match the existing player.
        result = resolver.resolve('2018 Panini Prizm Luka Doncicc #280')

        self.assertEqual(Player.objects.count(), 1)
        self.assertFalse(result.created_player)
        self.assertEqual(result.player.name, 'Luka Doncic')

    def test_low_signal_title_not_resolved(self):
        resolver = CardResolver()
        result = resolver.resolve('Random junk title with no card info')
        self.assertIsNone(result.card)
        self.assertEqual(Card.objects.count(), 0)

    def test_missing_year_not_resolved(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        result = resolver.resolve('Panini Prizm Luka Doncic #280 Silver')
        self.assertIsNone(result.card)

    def test_read_only_resolver_does_not_create(self):
        resolver = CardResolver(create_missing=False, sport=constants.SPORT_BASKETBALL)
        result = resolver.resolve('2018 Panini Prizm Luka Doncic #280')
        self.assertIsNone(result.card)
        self.assertEqual(Card.objects.count(), 0)

        # Once it exists, the read-only resolver can find it.
        CardResolver(sport=constants.SPORT_BASKETBALL).resolve(
            '2018 Panini Prizm Luka Doncic #280'
        )
        found = resolver.resolve('2018 Panini Prizm Luka Doncic #280')
        self.assertIsNotNone(found.card)
