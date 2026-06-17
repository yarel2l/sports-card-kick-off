"""Tests for the 130Point sales-comp agent."""

from django.test import TestCase

from apps.scraping.agents.point130_agent import Point130Agent
from apps.scraping.agents import registry
from apps.scraping.schemas import Point130ScrapeResult, ScrapeMetadata


SAMPLE_HTML = """
<html><body>
<table class="sales"><tbody>
  <tr class="sale">
    <td class="sale-title"><a href="https://130point.com/s/1">2018 Panini Prizm Luka Doncic #280 PSA 10</a></td>
    <td class="sale-price">$450.00</td>
    <td class="sale-type">Auction</td>
  </tr>
  <tr class="sale">
    <td class="sale-title"><a href="https://130point.com/s/2">2003 Topps Chrome LeBron James #111 BGS 9.5</a></td>
    <td class="sale-price">$1,200.00</td>
    <td class="sale-type">Best Offer</td>
  </tr>
  <tr class="sale">
    <td class="sale-title"><a href="https://130point.com/s/3">Empty row no price</a></td>
    <td class="sale-price"></td>
    <td class="sale-type">Sold</td>
  </tr>
</tbody></table>
</body></html>
"""


class Point130AgentTests(TestCase):
    def setUp(self):
        self.agent = Point130Agent(use_llm=False)

    def test_build_search_url(self):
        url = self.agent.build_search_url('Luka Doncic Prizm')
        self.assertIn('130point.com/sales/', url)
        self.assertIn('query=Luka+Doncic+Prizm', url)

    def test_traditional_parse_extracts_sales(self):
        parsed = self.agent._traditional_parse(SAMPLE_HTML, 'luka')
        items = parsed['items']
        # Third row has no price and must be skipped.
        self.assertEqual(len(items), 2)

        first = items[0]
        self.assertIn('Luka Doncic', first.title)
        self.assertEqual(first.price.amount, 450.0)
        self.assertEqual(first.sale_type, 'auction')
        self.assertEqual(first.grade.grading_company, 'PSA')
        self.assertEqual(first.grade.numeric_grade, 10.0)
        self.assertEqual(first.source, '130point')

    def test_parse_handles_thousands_separator_and_best_offer(self):
        items = self.agent._traditional_parse(SAMPLE_HTML, 'lebron')['items']
        lebron = items[1]
        self.assertEqual(lebron.price.amount, 1200.0)
        self.assertEqual(lebron.sale_type, 'best_offer')
        self.assertEqual(lebron.grade.grading_company, 'BGS')

    def test_stable_id_is_deterministic(self):
        a = Point130Agent._stable_id('title', 10.0, 'url')
        b = Point130Agent._stable_id('title', 10.0, 'url')
        self.assertEqual(a, b)
        self.assertNotEqual(a, Point130Agent._stable_id('other', 10.0, 'url'))

    def test_create_result(self):
        parsed = self.agent._traditional_parse(SAMPLE_HTML, 'luka')
        meta = ScrapeMetadata(execution_time_seconds=0.1, items_found=2)
        result = self.agent._create_result(True, 'luka', meta, parsed)
        self.assertIsInstance(result, Point130ScrapeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.source, '130point')

    def test_no_rows_returns_empty(self):
        parsed = self.agent._traditional_parse('<html><body>nothing</body></html>', 'q')
        self.assertEqual(parsed['items'], [])

    def test_registered_in_registry(self):
        self.assertIn('130point', registry.available_slugs())
        self.assertIs(registry.get_agent('130point'), Point130Agent)
