from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.portfolio.models import PortfolioHolding
from apps.portfolio.services.valuation import value_holding, value_portfolio

User = get_user_model()


class ValuationTests(TestCase):
    def setUp(self):
        cs = CardSet.objects.create(year=2018, brand='Panini', name='Prizm', sport='BASKETBALL')
        self.card = Card.objects.create(card_set=cs, canonical_key='k-280', card_number='280')
        self.psa = GradingCompany.objects.create(code='PSA', name='PSA')
        self.user = User.objects.create_user(
            email='u@example.com', username='u', password='pass12345'
        )
        # Latest PSA 10 observation is 400.
        for price in ('200', '300', '400'):
            PriceObservation.objects.create(
                card=self.card, source='ebay', price=Decimal(price),
                grade='10', grading_company=self.psa,
            )

    def test_value_holding_uses_last_market_price(self):
        holding = PortfolioHolding.objects.create(
            user=self.user, card=self.card, grade='10', grading_company=self.psa,
            quantity=2, cost_basis=Decimal('250'),
        )
        valued = value_holding(holding)
        self.assertEqual(valued['market_unit_price'], Decimal('400.00'))
        self.assertEqual(valued['market_value'], Decimal('800.00'))
        self.assertEqual(valued['total_cost'], Decimal('500.00'))
        self.assertEqual(valued['unrealized_pl'], Decimal('300.00'))

    def test_value_holding_without_market_data(self):
        holding = PortfolioHolding.objects.create(
            user=self.user, card=self.card, grade='9', quantity=1, cost_basis=Decimal('100'),
        )
        valued = value_holding(holding)
        self.assertIsNone(valued['market_value'])
        self.assertIsNone(valued['unrealized_pl'])
        self.assertEqual(valued['total_cost'], Decimal('100.00'))

    def test_portfolio_aggregation(self):
        PortfolioHolding.objects.create(
            user=self.user, card=self.card, grade='10', grading_company=self.psa,
            quantity=1, cost_basis=Decimal('300'),
        )
        PortfolioHolding.objects.create(
            user=self.user, card=self.card, grade='10', grading_company=self.psa,
            quantity=2, cost_basis=Decimal('250'),
        )
        summary = value_portfolio(
            PortfolioHolding.objects.filter(user=self.user)
        )
        totals = summary['totals']
        self.assertEqual(totals['holdings_count'], 2)
        self.assertEqual(totals['total_cost'], Decimal('800.00'))  # 300 + 500
        self.assertEqual(totals['total_market_value'], Decimal('1200.00'))  # 400 + 800
        self.assertEqual(totals['total_unrealized_pl'], Decimal('400.00'))
