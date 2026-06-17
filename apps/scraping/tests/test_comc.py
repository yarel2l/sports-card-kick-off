"""Tests for the COMC fixed-price marketplace agent."""

from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.ingest import ingest_item
from apps.catalog.services.resolver import CardResolver
from apps.scraping.agents import registry
from apps.scraping.agents.comc_agent import ComcAgent
from apps.scraping.schemas import ComcScrapeResult, ScrapeMetadata


SAMPLE_HTML = """
<html><body>
<div class="results">
  <div class="product-card">
    <a href="/Cards/1"><span class="title">2018 Panini Prizm Luka Doncic #280 PSA 10</span></a>
    <span class="price">$425.00</span>
    <span class="condition">Graded</span>
  </div>
  <div class="product-card">
    <a href="https://www.comc.com/Cards/2"><span class="title">2003 Topps Chrome LeBron James #111</span></a>
    <span class="price">$899.99</span>
  </div>
  <div class="product-card">
    <a href="/Cards/3"><span class="title">No price card</span></a>
    <span class="price"></span>
  </div>
</div>
</body></html>
"""


class ComcAgentTests(TestCase):
    def setUp(self):
        self.agent = ComcAgent(use_llm=False)

    def test_build_search_url(self):
        url = self.agent.build_search_url('Luka Doncic')
        self.assertIn('comc.com/Cards', url)
        self.assertIn('search=Luka+Doncic', url)

    def test_traditional_parse(self):
        items = self.agent._traditional_parse(SAMPLE_HTML, 'luka')['items']
        self.assertEqual(len(items), 2)  # third has no price
        first = items[0]
        self.assertIn('Luka Doncic', first.title)
        self.assertEqual(first.price.amount, 425.0)
        self.assertEqual(first.grade.grading_company, 'PSA')
        self.assertEqual(first.source, 'comc')
        # Relative URL is absolutized.
        self.assertTrue(str(first.url).startswith('https://www.comc.com/'))

    def test_create_result(self):
        parsed = self.agent._traditional_parse(SAMPLE_HTML, 'luka')
        meta = ScrapeMetadata(execution_time_seconds=0.1, items_found=2)
        result = self.agent._create_result(True, 'luka', meta, parsed)
        self.assertIsInstance(result, ComcScrapeResult)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.source, 'comc')

    def test_registered(self):
        self.assertIn('comc', registry.available_slugs())
        self.assertIs(registry.get_agent('comc'), ComcAgent)

    def test_ingested_as_listing(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        items = self.agent._traditional_parse(SAMPLE_HTML, 'luka')['items']
        obs = ingest_item(items[0].model_dump(mode='json'), source='comc', resolver=resolver)
        self.assertIsNotNone(obs)
        # COMC asking prices are active listings, not sales.
        self.assertEqual(obs.kind, PriceObservation.Kind.LISTING)
        self.assertEqual(Decimal(obs.price), Decimal('425.00'))
