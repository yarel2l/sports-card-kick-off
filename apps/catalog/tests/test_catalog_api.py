from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Card, GradingCompany, PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.resolver import CardResolver


class CatalogAPITests(APITestCase):
    def setUp(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        self.luka = resolver.resolve(
            '2018 Panini Prizm Luka Doncic #280 Silver Rookie'
        ).card
        resolver.resolve('2019 Panini Prizm Zion Williamson #248 Rookie')

        psa = GradingCompany.objects.create(code='PSA', name='PSA')
        for price in ('200', '300', '400'):
            PriceObservation.objects.create(
                card=self.luka, source='ebay', price=Decimal(price),
                grade='10', grading_company=psa,
            )

    def test_endpoints_are_public(self):
        # No authentication provided; catalog reads must still succeed.
        resp = self.client.get(reverse('catalog:card-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_card_list(self):
        resp = self.client.get(reverse('catalog:card-list'))
        self.assertEqual(resp.data['count'], 2)

    def test_card_list_filter_by_player(self):
        resp = self.client.get(reverse('catalog:card-list'), {'player': 'Luka'})
        self.assertEqual(resp.data['count'], 1)

    def test_card_detail(self):
        resp = self.client.get(reverse('catalog:card-detail', args=[self.luka.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['card_number'], '280')
        self.assertEqual(resp.data['player']['name'], 'Luka Doncic')

    def test_card_prices(self):
        resp = self.client.get(reverse('catalog:card-prices', args=[self.luka.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['market']['overall']['count'], 3)
        self.assertEqual(Decimal(str(resp.data['market']['overall']['max'])), Decimal('400.00'))
        self.assertEqual(len(resp.data['recent_observations']), 3)
        by_grade = resp.data['market']['by_grade']
        self.assertEqual(by_grade[0]['grade'], '10')

    def test_card_prices_filtered_by_grade(self):
        resp = self.client.get(
            reverse('catalog:card-prices', args=[self.luka.id]), {'grade': '9'}
        )
        self.assertEqual(resp.data['market']['overall']['count'], 0)

    def test_card_history(self):
        resp = self.client.get(
            reverse('catalog:card-history', args=[self.luka.id]), {'interval': 'month'}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['interval'], 'month')
        self.assertGreaterEqual(len(resp.data['history']), 1)

    def test_nl_search_endpoint(self):
        resp = self.client.get(
            reverse('catalog:search'), {'q': 'Luka Doncic 2018 Prizm rookie'}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['interpreted_query']['player_name'], 'Luka Doncic')
        self.assertTrue(resp.data['interpreted_query']['is_rookie'])
        self.assertEqual(resp.data['count'], 1)
        first = resp.data['results'][0]
        self.assertIn('card', first)
        self.assertIn('market', first)
        self.assertEqual(first['market']['count'], 3)

    def test_nl_search_no_match(self):
        resp = self.client.get(reverse('catalog:search'), {'q': 'Nonexistent Player 1999'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 0)

    def test_players_endpoint(self):
        resp = self.client.get(reverse('catalog:player-list'), {'search': 'Luka'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)

    def test_card_detail_404(self):
        resp = self.client.get(
            reverse('catalog:card-detail', args=['00000000-0000-0000-0000-000000000000'])
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
