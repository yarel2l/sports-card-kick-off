"""
LIVE integration tests — they hit the real marketplace sites.

These are SKIPPED by default so the normal suite/CI never depend on outbound
network, a Playwright browser, or a third-party site being up. They are the
intended way to validate parsing against real HTML (not fixtures).

Run them only where network + a browser are available::

    playwright install chromium
    RUN_LIVE_SCRAPE_TESTS=1 python manage.py test apps.scraping.tests.test_live_scraping

Each test asserts only loose structural expectations, because live results vary:
a successful scrape that returns at least one well-formed item.
"""

import asyncio
import os
import unittest

from django.test import TestCase

from apps.scraping.agents import registry

RUN_LIVE = os.environ.get('RUN_LIVE_SCRAPE_TESTS') == '1'
_SKIP_REASON = (
    "Live scraping tests are disabled. Set RUN_LIVE_SCRAPE_TESTS=1 (and install "
    "a Playwright browser + have network access) to run them."
)

# A query that should reliably return graded modern cards across sources.
LIVE_QUERY = os.environ.get('LIVE_SCRAPE_QUERY', '2018 Prizm Luka Doncic PSA 10')


def _scrape(source: str, query: str):
    agent = registry.get_agent(source)(use_llm=False)
    return asyncio.run(agent.scrape(query))


@unittest.skipUnless(RUN_LIVE, _SKIP_REASON)
class LiveScrapingTests(TestCase):
    """Structural smoke tests against real sites (opt-in)."""

    def _assert_well_formed(self, result, source):
        self.assertTrue(getattr(result, 'success', False), f"{source} scrape did not succeed")
        items = getattr(result, 'items', []) or []
        self.assertGreater(len(items), 0, f"{source} returned no items for live query")
        first = items[0]
        self.assertTrue(getattr(first, 'title', ''), f"{source} item has empty title")
        self.assertGreater(first.price.amount, 0, f"{source} item has non-positive price")
        self.assertEqual(first.source, source)

    def test_ebay_live(self):
        self._assert_well_formed(_scrape('ebay', LIVE_QUERY), 'ebay')

    def test_130point_live(self):
        self._assert_well_formed(_scrape('130point', LIVE_QUERY), '130point')

    def test_comc_live(self):
        self._assert_well_formed(_scrape('comc', LIVE_QUERY), 'comc')

    def test_goldin_live(self):
        self._assert_well_formed(_scrape('goldin', LIVE_QUERY), 'goldin')


class LiveScrapingHarnessTests(TestCase):
    """Always-on guards for the live harness wiring itself (no network)."""

    def test_all_sources_registered(self):
        for slug in ('ebay', '130point', 'comc', 'goldin'):
            self.assertIn(slug, registry.available_slugs())

    def test_scrape_live_command_importable(self):
        from apps.scraping.management.commands import scrape_live
        self.assertTrue(hasattr(scrape_live, 'Command'))
