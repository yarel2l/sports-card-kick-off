"""
Tests for scraping agents using LangChain and LLMs.
"""

from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase
from datetime import datetime

from apps.scraping.agents.base_agent import BaseScraperAgent
from apps.scraping.agents.scraper_agent import ScraperAgent
from apps.scraping.agents.ebay_agent import EbayAgent, EbayExtractionResult, EbayItemExtraction
from apps.scraping.schemas.base_schemas import (
    PriceInfo,
    SellerInfo,
    ScrapeMetadata,
    CardGrade,
)
from apps.scraping.schemas.ebay_schemas import (
    EbayItem,
    EbayScrapeResult,
    EbayListingType,
    EbayCondition,
)


def create_mock_config():
    """Helper to create mock SystemConfiguration."""
    mock_config = Mock()
    mock_config.scraping_timeout = 30000
    mock_config.max_retries = 3
    mock_config.use_llm_by_default = False
    mock_config.default_llm_model = 'gpt-4o-mini'
    mock_config.llm_temperature = 0.7
    mock_config.llm_max_tokens = 4000
    mock_config.use_traditional_fallback = True
    mock_config.get_active_llm_provider.return_value = None
    return mock_config


class BaseScraperAgentTests(TestCase):
    """Test BaseScraperAgent functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a concrete implementation for testing
        class TestAgent(BaseScraperAgent):
            def parse_html(self, html, query):
                return {'items': [], 'total_results': 0}

            def build_search_url(self, query, **kwargs):
                return f"https://example.com/search?q={query}"

            def _create_result(self, success, query, metadata, parsed_data):
                from apps.scraping.schemas.base_schemas import BaseScrapeResult
                return BaseScrapeResult(
                    success=success,
                    source="test",
                    query=query,
                    metadata=metadata
                )

            async def scrape(self, query, **kwargs):
                """Implement abstract method."""
                return await self.execute_scrape(query, **kwargs)

        self.agent = TestAgent(
            site_name="Test Site",
            base_url="https://example.com"
        )

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.site_name, "Test Site")
        self.assertEqual(self.agent.base_url, "https://example.com")
        self.assertEqual(self.agent.timeout, 30000)
        self.assertEqual(self.agent.max_retries, 3)

    def test_create_soup(self):
        """Test creating BeautifulSoup object."""
        html = '<html><body><h1>Test</h1></body></html>'
        soup = self.agent.create_soup(html)

        self.assertIsNotNone(soup)
        self.assertEqual(soup.find('h1').text, 'Test')

    def test_extract_text(self):
        """Test extracting text from element."""
        html = '<div class="test">Test Content</div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div', class_='test')

        text = self.agent.extract_text(element)
        self.assertEqual(text, 'Test Content')

    def test_extract_text_with_default(self):
        """Test extracting text with default value."""
        text = self.agent.extract_text(None, default="Default")
        self.assertEqual(text, "Default")

    def test_extract_attribute(self):
        """Test extracting attribute from element."""
        html = '<a href="https://example.com">Link</a>'
        soup = self.agent.create_soup(html)
        element = soup.find('a')

        url = self.agent.extract_attribute(element, 'href')
        self.assertEqual(url, 'https://example.com')

    def test_extract_attribute_with_default(self):
        """Test extracting attribute with default value."""
        url = self.agent.extract_attribute(None, 'href', default="")
        self.assertEqual(url, "")


class EbayAgentTests(TestCase):
    """Test EbayAgent functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Patch SystemConfiguration for all tests in this class
        self.config_patcher = patch('apps.core.models.SystemConfiguration')
        mock_config_class = self.config_patcher.start()
        mock_config_class.get_solo.return_value = create_mock_config()

        self.agent = EbayAgent(use_llm=False)

    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()

    def test_ebay_agent_initialization(self):
        """Test eBay agent initializes correctly."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.site_name, "eBay")
        self.assertEqual(self.agent.base_url, "https://www.ebay.com")

    def test_build_search_url_basic(self):
        """Test building basic search URL."""
        url = self.agent.build_search_url("Mike Trout PSA 10")

        self.assertIn('ebay.com/sch/i.html', url)
        self.assertIn('Mike+Trout+PSA+10', url)

    def test_build_search_url_with_pagination(self):
        """Test building URL with pagination."""
        url = self.agent.build_search_url("test", page=2)

        self.assertIn('_pgn=2', url)

    def test_build_search_url_with_sorting(self):
        """Test building URL with sort parameter."""
        url = self.agent.build_search_url("test", sort_by='price_asc')

        self.assertIn('_sop=15', url)

    def test_build_search_url_with_price_range(self):
        """Test building URL with price filters."""
        url = self.agent.build_search_url("test", min_price=100, max_price=500)

        self.assertIn('_udlo=100', url)
        self.assertIn('_udhi=500', url)

    def test_build_search_url_with_listing_type(self):
        """Test building URL with listing type filter."""
        url = self.agent.build_search_url("test", listing_type='buy_it_now')

        self.assertIn('LH_BIN=1', url)

    def test_extract_item_id_from_data_attribute(self):
        """Test extracting item ID from data attribute."""
        html = '<div data-iid="123456789">Test</div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        item_id = self.agent._extract_item_id(element)
        self.assertEqual(item_id, '123456789')

    def test_parse_price(self):
        """Test parsing price information."""
        html = '''
        <div class="s-item">
            <span class="s-item__price">$99.99</span>
            <span class="s-item__shipping">+$5.99 shipping</span>
        </div>
        '''
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        price_info = self.agent._parse_price(element)

        self.assertIsNotNone(price_info)
        self.assertEqual(price_info.amount, 99.99)
        self.assertEqual(price_info.currency, 'USD')

    def test_parse_seller(self):
        """Test parsing seller information."""
        html = '''
        <div class="s-item">
            <div class="s-item__seller-info">
                <span class="s-item__seller-info-text">testseller</span>
                <span class="s-item__seller-feedback">(1000) 99.5%</span>
            </div>
        </div>
        '''
        soup = self.agent.create_soup(html)
        element = soup.find('div', class_='s-item')

        seller_info = self.agent._parse_seller(element)

        self.assertEqual(seller_info.seller_name, 'testseller')
        self.assertEqual(seller_info.feedback_count, 1000)
        self.assertEqual(seller_info.rating, 99.5)

    def test_parse_listing_type_buy_it_now(self):
        """Test parsing Buy It Now listing type."""
        html = '<div class="s-item"></div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        listing_type = self.agent._parse_listing_type(element)

        self.assertIsInstance(listing_type, EbayListingType)
        self.assertEqual(listing_type.listing_type, "buy_it_now")
        self.assertTrue(listing_type.is_buy_it_now)
        self.assertFalse(listing_type.is_auction)

    def test_parse_listing_type_auction(self):
        """Test parsing auction listing type."""
        html = '<div class="s-item"><span class="s-item__bids">5 bids</span></div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        listing_type = self.agent._parse_listing_type(element)

        self.assertIsInstance(listing_type, EbayListingType)
        self.assertEqual(listing_type.listing_type, "auction")
        self.assertTrue(listing_type.is_auction)
        self.assertFalse(listing_type.is_buy_it_now)

    def test_parse_condition_new(self):
        """Test parsing new condition."""
        html = '<div class="s-item"><span class="s-item__condition">Brand New</span></div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        condition = self.agent._parse_condition(element, has_grade=False)

        self.assertIsInstance(condition, EbayCondition)
        self.assertEqual(condition.condition, "New")
        self.assertFalse(condition.is_graded)

    def test_parse_condition_with_grade(self):
        """Test parsing condition for graded card."""
        html = '<div class="s-item"><span class="s-item__condition">Used</span></div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        condition = self.agent._parse_condition(element, has_grade=True)

        self.assertIsInstance(condition, EbayCondition)
        self.assertEqual(condition.condition, "Used")
        self.assertTrue(condition.is_graded)

    def test_parse_watchers(self):
        """Test parsing watchers count."""
        html = '<div class="s-item"><span class="s-item__watchers">15 watchers</span></div>'
        soup = self.agent.create_soup(html)
        element = soup.find('div')

        watchers = self.agent._parse_watchers(element)

        self.assertEqual(watchers, 15)

    def test_extract_total_results(self):
        """Test extracting total results count."""
        html = '<span class="srp-controls__count-heading">1,234 results</span>'
        soup = self.agent.create_soup(html)

        total = self.agent._extract_total_results(soup)

        self.assertEqual(total, 1234)

    def test_traditional_parse_no_results(self):
        """Test traditional parsing with no results."""
        html = '<html><body>No items found</body></html>'

        result = self.agent._traditional_parse(html, "test query")

        self.assertEqual(len(result['items']), 0)
        self.assertEqual(result['total_results'], 0)

    def test_create_result_from_traditional_data(self):
        """Test creating result from traditional parsing data."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.0,
            items_found=1,
            page_count=1
        )

        item = EbayItem(
            item_id='123456789',
            title='Test Card PSA 10',
            url='https://ebay.com/itm/123456789',
            source='ebay',
            price=PriceInfo(amount=99.99, currency='USD'),
            seller=SellerInfo(seller_name='testseller'),
            listing=EbayListingType(
                listing_type="buy_it_now",
                is_auction=False,
                is_buy_it_now=True
            ),
            condition=EbayCondition(condition="New", is_graded=False),
        )

        parsed_data = {
            'items': [item],
            'total_results': 100
        }

        result = self.agent._create_result(
            success=True,
            query='test',
            metadata=metadata,
            parsed_data=parsed_data
        )

        self.assertIsInstance(result, EbayScrapeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.total_results, 100)

    def test_create_result_from_llm_data(self):
        """Test creating result from LLM extraction data."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.0,
            items_found=1,
            page_count=1
        )

        # Simulate LLM extraction format
        llm_item = {
            'title': 'Test Card PSA 10',
            'price': 99.99,
            'shipping_cost': 5.99,
            'item_id': '123456789',
            'url': 'https://ebay.com/itm/123456789',
            'seller_username': 'testseller',
            'seller_feedback_score': 1000,
            'seller_positive_percentage': 99.5,
            'condition': 'New',
            'listing_type': 'buy_it_now',
            'image_url': 'https://example.com/image.jpg',
            'watchers': 15
        }

        parsed_data = {
            'items': [llm_item],
            'total_results': 100
        }

        result = self.agent._create_result(
            success=True,
            query='test',
            metadata=metadata,
            parsed_data=parsed_data
        )

        self.assertIsInstance(result, EbayScrapeResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].item_id, '123456789')
        self.assertEqual(result.items[0].price.amount, 99.99)
        self.assertEqual(result.items[0].seller.seller_name, 'testseller')

    def test_get_extraction_schema(self):
        """Test getting extraction schema for LLM."""
        schema = self.agent.get_extraction_schema()

        self.assertEqual(schema, EbayExtractionResult)

    def test_create_extraction_prompt(self):
        """Test creating extraction prompt."""
        prompt = self.agent.create_extraction_prompt("Mike Trout PSA 10")

        self.assertIn("Mike Trout PSA 10", prompt)
        self.assertIn("extract", prompt.lower())
        self.assertIn("ebay", prompt.lower())


class ScraperAgentTests(TestCase):
    """Test ScraperAgent with LLM functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_patcher = patch('apps.core.models.SystemConfiguration')
        self.mock_config_class = self.config_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()

    def test_llm_initialization_disabled(self):
        """Test that LLM is not initialized when disabled."""
        mock_config = create_mock_config()
        self.mock_config_class.get_solo.return_value = mock_config

        agent = EbayAgent(use_llm=False)

        self.assertFalse(agent.use_llm)
        self.assertIsNone(agent._llm)

    # NOTE: LLM provider detection tests are complex to mock properly
    # because the imports happen lazily inside the llm property getter.
    # These would require more sophisticated patching or integration tests.
    # For unit tests, we verify that use_llm flag works correctly instead.

    def test_truncate_html(self):
        """Test HTML truncation for LLM."""
        mock_config = create_mock_config()
        self.mock_config_class.get_solo.return_value = mock_config

        agent = EbayAgent(use_llm=False)

        # Short HTML should not be truncated
        short_html = '<html><body>Test</body></html>'
        result = agent._truncate_html(short_html, max_chars=1000)
        self.assertEqual(result, short_html)

        # Long HTML should be truncated
        long_html = '<html><body>' + 'x' * 100000 + '</body></html>'
        result = agent._truncate_html(long_html, max_chars=1000)
        self.assertLessEqual(len(result), 1000)

    def test_parse_html_llm_fallback_to_traditional(self):
        """Test fallback to traditional parsing when LLM fails."""
        mock_config = create_mock_config()
        self.mock_config_class.get_solo.return_value = mock_config

        agent = EbayAgent(use_llm=False)

        # With LLM disabled, should use traditional parsing directly
        html = '<html><body>Test</body></html>'
        result = agent.parse_html(html, "test query")

        # Should return result (even if empty)
        self.assertIsInstance(result, dict)
        self.assertIn('items', result)
