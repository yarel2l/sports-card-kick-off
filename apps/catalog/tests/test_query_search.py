from django.test import TestCase

from apps.catalog.services import constants
from apps.catalog.services.query_search import search_cards
from apps.catalog.services.resolver import CardResolver


class QuerySearchTests(TestCase):
    def setUp(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        resolver.resolve('2018 Panini Prizm Luka Doncic #280 Silver Rookie')
        resolver.resolve('2018 Panini Prizm Luka Doncic #280')  # base
        resolver.resolve('2019 Panini Prizm Zion Williamson #248 Rookie')
        resolver.resolve('2003 Topps Chrome LeBron James #111 Refractor')

    def test_nl_query_filters_by_player_and_year(self):
        parsed, qs = search_cards('Luka Doncic 2018 Prizm')
        self.assertEqual(parsed.player_name, 'Luka Doncic')
        self.assertTrue(all(c.player.name == 'Luka Doncic' for c in qs))
        self.assertEqual(qs.count(), 2)

    def test_nl_query_rookie_flag(self):
        parsed, qs = search_cards('Luka Doncic 2018 Prizm rookie')
        self.assertTrue(parsed.is_rookie)
        self.assertTrue(all(c.is_rookie for c in qs))
        self.assertEqual(qs.count(), 1)

    def test_explicit_params_override_text(self):
        _parsed, qs = search_cards('Luka Doncic', year=2019)
        # year filter applied even though text said nothing about year.
        self.assertTrue(all(c.card_set.year == 2019 for c in qs))

    def test_parallel_filter(self):
        _parsed, qs = search_cards('LeBron James Refractor')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().parallel, 'Refractor')

    def test_empty_query_returns_all(self):
        _parsed, qs = search_cards('')
        self.assertEqual(qs.count(), 4)
