from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.portfolio.models import PortfolioHolding, PortfolioSnapshot
from apps.portfolio.services.digest import build_digest, deliver_digest
from apps.portfolio.tasks import send_portfolio_digests

User = get_user_model()


class DigestTests(TestCase):
    def setUp(self):
        cs = CardSet.objects.create(year=2018, brand='Panini', name='Prizm', sport='BASKETBALL')
        self.card = Card.objects.create(card_set=cs, canonical_key='k-280', card_number='280')
        self.psa = GradingCompany.objects.create(code='PSA', name='PSA')
        self.user = User.objects.create_user(
            email='owner@example.com', username='owner', password='pass12345'
        )
        PriceObservation.objects.create(
            card=self.card, source='ebay', price=Decimal('400'), grade='10',
            grading_company=self.psa,
        )
        self.holding = PortfolioHolding.objects.create(
            user=self.user, card=self.card, grade='10', grading_company=self.psa,
            quantity=2, cost_basis=Decimal('250'),
        )

    def test_build_digest_without_prior_snapshot(self):
        digest = build_digest(self.user)
        self.assertEqual(digest['valuation']['totals']['total_market_value'], Decimal('800.00'))
        self.assertIsNone(digest['value_change'])

    def test_build_digest_reports_change(self):
        PortfolioSnapshot.objects.create(
            user=self.user, holdings_count=1, total_cost=Decimal('500'),
            total_market_value=Decimal('700'), total_unrealized_pl=Decimal('200'),
        )
        digest = build_digest(self.user)
        # 800 now vs 700 previously => +100.
        self.assertEqual(digest['value_change'], Decimal('100.00'))

    def test_deliver_sends_email_and_records_snapshot(self):
        sent = deliver_digest(self.user)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('portfolio summary', mail.outbox[0].subject.lower())
        self.assertEqual(PortfolioSnapshot.objects.filter(user=self.user).count(), 1)

    def test_deliver_skips_user_without_holdings(self):
        empty_user = User.objects.create_user(
            email='empty@example.com', username='empty', password='pass12345'
        )
        sent = deliver_digest(empty_user)
        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PortfolioSnapshot.objects.filter(user=empty_user).count(), 0)

    def test_task_processes_only_users_with_holdings(self):
        User.objects.create_user(email='noheld@example.com', username='noheld', password='pass12345')
        result = send_portfolio_digests()
        self.assertEqual(result['users'], 1)
        self.assertEqual(result['emails_sent'], 1)
        self.assertEqual(len(mail.outbox), 1)
