"""
Tests for scraping fetchers using Playwright.
"""

from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase
import asyncio

from apps.scraping.fetchers.base_fetcher import BaseFetcher


class BaseFetcherTests(TestCase):
    """Test BaseFetcher functionality with Playwright."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = BaseFetcher()

    def test_fetcher_initialization(self):
        """Test that fetcher initializes correctly."""
        self.assertIsNotNone(self.fetcher)
        self.assertIsInstance(self.fetcher, BaseFetcher)
        self.assertTrue(self.fetcher.headless)
        self.assertEqual(self.fetcher.timeout, 30000)
        self.assertEqual(self.fetcher.max_retries, 3)
        self.assertEqual(self.fetcher.viewport_width, 1920)
        self.assertEqual(self.fetcher.viewport_height, 1080)

    def test_fetcher_custom_initialization(self):
        """Test fetcher with custom parameters."""
        fetcher = BaseFetcher(
            headless=False,
            timeout=60000,
            max_retries=5,
            viewport_width=1024,
            viewport_height=768
        )

        self.assertFalse(fetcher.headless)
        self.assertEqual(fetcher.timeout, 60000)
        self.assertEqual(fetcher.max_retries, 5)
        self.assertEqual(fetcher.viewport_width, 1024)
        self.assertEqual(fetcher.viewport_height, 768)

    def test_get_random_user_agent(self):
        """Test random user agent generation."""
        ua1 = self.fetcher.get_random_user_agent()
        ua2 = self.fetcher.get_random_user_agent()

        self.assertIsNotNone(ua1)
        self.assertIsInstance(ua1, str)
        self.assertGreater(len(ua1), 0)

        # User agents should be strings
        self.assertIsInstance(ua2, str)

    def test_get_anti_detection_args(self):
        """Test anti-detection browser arguments."""
        args = self.fetcher.get_anti_detection_args()

        self.assertIsInstance(args, list)
        self.assertIn('--disable-blink-features=AutomationControlled', args)
        self.assertIn('--no-sandbox', args)
        self.assertIn('--disable-dev-shm-usage', args)

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_start_browser_success(self, mock_playwright):
        """Test starting Playwright browser successfully."""
        # Mock the entire Playwright chain
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.set_default_timeout = Mock()

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        # Start the fetcher
        await self.fetcher.start()

        # Verify browser was launched
        self.assertIsNotNone(self.fetcher._playwright)
        self.assertIsNotNone(self.fetcher._browser)
        self.assertIsNotNone(self.fetcher._context)
        self.assertIsNotNone(self.fetcher._page)

        # Clean up
        await self.fetcher.close()

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_context_manager(self, mock_playwright):
        """Test using fetcher as async context manager."""
        # Mock Playwright
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_page.set_default_timeout = Mock()
        mock_page.close = AsyncMock()

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        # Use as context manager
        async with self.fetcher as fetcher:
            self.assertIsNotNone(fetcher._page)

        # After exit, resources should be cleaned
        # (We can't easily test this without real Playwright)

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_fetch_page_success(self, mock_playwright):
        """Test fetching a page successfully."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status = 200

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.content = AsyncMock(return_value='<html><body>Test Content</body></html>')
        mock_page.set_default_timeout = Mock()

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        # Initialize and fetch
        await self.fetcher.start()
        content = await self.fetcher.fetch_page('https://example.com')

        self.assertEqual(content, '<html><body>Test Content</body></html>')
        mock_page.goto.assert_called_once()

        await self.fetcher.close()

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_fetch_page_with_wait_selector(self, mock_playwright):
        """Test fetching page with wait for selector."""
        mock_response = Mock()
        mock_response.status = 200

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.content = AsyncMock(return_value='<html><body>Test</body></html>')
        mock_page.set_default_timeout = Mock()

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        await self.fetcher.start()
        await self.fetcher.fetch_page(
            'https://example.com',
            wait_for_selector='.content'
        )

        mock_page.wait_for_selector.assert_called_once_with(
            '.content',
            timeout=self.fetcher.timeout
        )

        await self.fetcher.close()

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_fetch_page_timeout(self, mock_playwright):
        """Test fetch handles timeout with retries."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError('Timeout'))
        mock_page.set_default_timeout = Mock()

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        await self.fetcher.start()

        with self.assertRaises(PlaywrightTimeoutError):
            await self.fetcher.fetch_page('https://example.com')

        # Should have retried max_retries times
        self.assertEqual(mock_page.goto.call_count, self.fetcher.max_retries)

        await self.fetcher.close()

    async def test_fetch_page_without_start(self):
        """Test that fetch_page raises error when browser not started."""
        with self.assertRaises(RuntimeError):
            await self.fetcher.fetch_page('https://example.com')

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_screenshot(self, mock_playwright):
        """Test taking a screenshot."""
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock()
        mock_page.set_default_timeout = Mock()

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        await self.fetcher.start()
        await self.fetcher.screenshot('/tmp/test.png', full_page=True)

        mock_page.screenshot.assert_called_once_with(
            path='/tmp/test.png',
            full_page=True
        )

        await self.fetcher.close()

    @patch('apps.scraping.fetchers.base_fetcher.async_playwright')
    async def test_evaluate_js(self, mock_playwright):
        """Test executing JavaScript."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={'result': 'success'})
        mock_page.set_default_timeout = Mock()

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.stop = AsyncMock()

        mock_playwright_start = AsyncMock()
        mock_playwright_start.start = AsyncMock(return_value=mock_pw_instance)
        mock_playwright.return_value = mock_playwright_start

        await self.fetcher.start()
        result = await self.fetcher.evaluate_js('return document.title')

        self.assertEqual(result, {'result': 'success'})
        mock_page.evaluate.assert_called_once_with('return document.title')

        await self.fetcher.close()


# Helper function to run async tests in Django TestCase
def async_test(coro):
    """Decorator to run async tests."""
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


# Apply async_test decorator to all async test methods
for attr_name in dir(BaseFetcherTests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(BaseFetcherTests, attr_name)):
        setattr(
            BaseFetcherTests,
            attr_name,
            async_test(getattr(BaseFetcherTests, attr_name))
        )
