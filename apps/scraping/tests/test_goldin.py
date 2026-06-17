"""Tests for the Goldin auction-house agent."""

from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.ingest import ingest_item
from apps.catalog.services.resolver import CardResolver
from apps.scraping.agents import registry
from apps.scraping.agents.goldin_agent import GoldinAgent
from apps.scraping.schemas import GoldinScrapeResult, ScrapeMetadata


SAMPLE_HTML = """
<html><body>
<div class="lots">
  <div class="lot-card">
    <a href="/lot/1"><span class="lot-title">2018 Panini Prizm Luka Doncic #280 PSA 10</span></a>
    <span class="current-bid">$5,200.00</span>
    <span class="lot-number">Lot 101</span>
    <span class="lot-status">Open</span>
  </div>
  <div class="lot-card">
    <a href="https://goldin.co/lot/2"><span class="lot-title">2003 Topps Chrome LeBron James #111 BGS 9.5</span></a>
    <span class="current-bid">$12,000.00</span>
    <span class="lot-number">Lot 102</span>
    <span class="lot-status">Closed</span>
  </div>
  <div class="lot-card">
    <a href="/lot/3"><span class="lot-title">No price lot</span></a>
    <span class="current-bid"></span>
  </div>
</div>
</body></html>
"""


class GoldinAgentTests(TestCase):
    def setUp(self):
        self.agent = GoldinAgent(use_llm=False)

    def test_build_search_url(self):
        url = self.agent.build_search_url('Luka Doncic')
        self.assertIn('goldin.co/search', url)
        self.assertIn('query=Luka+Doncic', url)

    def test_traditional_parse_open_and_closed(self):
        items = self.agent._traditional_parse(SAMPLE_HTML, 'luka')['items']
        self.assertEqual(len(items), 2)  # third has no price

        open_lot = items[0]
        self.assertIn('Luka Doncic', open_lot.title)
        self.assertEqual(open_lot.price.amount, 5200.0)
        self.assertEqual(open_lot.observation_kind, 'AUCTION')
        self.assertEqual(open_lot.lot_number, 'Lot 101')
        self.assertEqual(open_lot.grade.grading_company, 'PSA')

        closed_lot = items[1]
        self.assertEqual(closed_lot.observation_kind, 'SOLD')

    def test_create_result(self):
        parsed = self.agent._traditional_parse(SAMPLE_HTML, 'luka')
        meta = ScrapeMetadata(execution_time_seconds=0.1, items_found=2)
        result = self.agent._create_result(True, 'luka', meta, parsed)
        self.assertIsInstance(result, GoldinScrapeResult)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.source, 'goldin')

    def test_registered(self):
        self.assertIn('goldin', registry.available_slugs())
        self.assertIs(registry.get_agent('goldin'), GoldinAgent)

    def test_open_lot_ingested_as_auction(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        items = self.agent._traditional_parse(SAMPLE_HTML, 'luka')['items']
        obs = ingest_item(items[0].model_dump(mode='json'), source='goldin', resolver=resolver)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.kind, PriceObservation.Kind.AUCTION)
        self.assertEqual(Decimal(obs.price), Decimal('5200.00'))

    def test_closed_lot_ingested_as_sold(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        items = self.agent._traditional_parse(SAMPLE_HTML, 'lebron')['items']
        obs = ingest_item(items[1].model_dump(mode='json'), source='goldin', resolver=resolver)
        self.assertEqual(obs.kind, PriceObservation.Kind.SOLD)
