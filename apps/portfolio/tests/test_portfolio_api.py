from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.portfolio.models import PortfolioHolding, PriceAlert, WatchlistItem

User = get_user_model()


def _user(email='a@example.com', username='a'):
    return User.objects.create_user(email=email, username=username, password='pass12345')


class PortfolioAPITests(APITestCase):
    def setUp(self):
        self.user = _user()
        self.other = _user(email='b@example.com', username='b')
        self.client.force_authenticate(user=self.user)

        cs = CardSet.objects.create(year=2018, brand='Panini', name='Prizm', sport='BASKETBALL')
        self.card = Card.objects.create(card_set=cs, canonical_key='k-280', card_number='280')
        self.psa = GradingCompany.objects.create(code='PSA', name='PSA')
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('400'), grade='10',
            grading_company=self.psa,
        )

    # --- auth ---------------------------------------------------------------
    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(reverse('portfolio:watchlist'))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- watchlist ----------------------------------------------------------
    def test_add_and_list_watchlist(self):
        resp = self.client.post(
            reverse('portfolio:watchlist'), {'card': str(self.card.id)}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # Idempotent second add.
        resp2 = self.client.post(
            reverse('portfolio:watchlist'), {'card': str(self.card.id)}, format='json'
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(WatchlistItem.objects.filter(user=self.user).count(), 1)

        listing = self.client.get(reverse('portfolio:watchlist'))
        self.assertEqual(listing.data['count'], 1)

    def test_watchlist_is_user_scoped(self):
        WatchlistItem.objects.create(user=self.other, card=self.card)
        listing = self.client.get(reverse('portfolio:watchlist'))
        self.assertEqual(listing.data['count'], 0)

    # --- holdings -----------------------------------------------------------
    def test_create_holding_and_summary(self):
        payload = {
            'card': str(self.card.id), 'grade': '10',
            'grading_company': str(self.psa.id), 'quantity': 2, 'cost_basis': '250.00',
        }
        resp = self.client.post(reverse('portfolio:holding-list'), payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        summary = self.client.get(reverse('portfolio:summary'))
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        totals = summary.data['totals']
        self.assertEqual(totals['holdings_count'], 1)
        self.assertEqual(Decimal(str(totals['total_market_value'])), Decimal('800.00'))
        self.assertEqual(Decimal(str(totals['total_unrealized_pl'])), Decimal('300.00'))

    def test_holding_detail_is_user_scoped(self):
        holding = PortfolioHolding.objects.create(
            user=self.other, card=self.card, quantity=1, cost_basis=Decimal('100')
        )
        resp = self.client.get(reverse('portfolio:holding-detail', args=[holding.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # --- alerts -------------------------------------------------------------
    def test_create_alert(self):
        payload = {
            'card': str(self.card.id), 'direction': 'BELOW',
            'threshold_price': '150.00', 'grade': '10',
        }
        resp = self.client.post(reverse('portfolio:alert-list'), payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['is_active'])

    def test_alert_rejects_non_positive_threshold(self):
        payload = {'card': str(self.card.id), 'direction': 'BELOW', 'threshold_price': '0'}
        resp = self.client.post(reverse('portfolio:alert-list'), payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alert_active_filter(self):
        PriceAlert.objects.create(
            user=self.user, card=self.card, threshold_price=Decimal('100'), is_active=True
        )
        PriceAlert.objects.create(
            user=self.user, card=self.card, threshold_price=Decimal('100'), is_active=False
        )
        active = self.client.get(reverse('portfolio:alert-list'), {'active': 'true'})
        self.assertEqual(active.data['count'], 1)
