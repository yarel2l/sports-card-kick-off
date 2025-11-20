"""
Base Fetcher for web scraping using Playwright.
Provides anti-detection features and common scraping utilities.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from fake_useragent import UserAgent
import logging

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """
    Base class for fetching web pages using Playwright with anti-detection features.

    Features:
    - Random user agents
    - Headless browser mode
    - Configurable timeouts
    - Anti-bot detection bypasses
    - Automatic retry logic
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,  # 30 seconds
        max_retries: int = 3,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
    ):
        """
        Initialize the BaseFetcher.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
            max_retries: Maximum number of retry attempts
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        self.headless = headless
        self.timeout = timeout
        self.max_retries = max_retries
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.ua = UserAgent()

        # Playwright instances
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def get_random_user_agent(self) -> str:
        """
        Get a random user agent string.

        Returns:
            Random user agent string
        """
        return self.ua.random

    def get_anti_detection_args(self) -> List[str]:
        """
        Get Chromium arguments to reduce bot detection.

        Returns:
            List of browser arguments
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-infobars',
            '--window-size=1920,1080',
        ]

    async def start(self):
        """Start the Playwright browser instance."""
        try:
            self._playwright = await async_playwright().start()

            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=self.get_anti_detection_args()
            )

            # Create context with random user agent
            self._context = await self._browser.new_context(
                user_agent=self.get_random_user_agent(),
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                locale='en-US',
                timezone_id='America/New_York',
            )

            # Add anti-detection scripts
            await self._context.add_init_script("""
                // Override the navigator.webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.timeout)

            logger.info("Playwright browser started successfully")

        except Exception as e:
            logger.error(f"Failed to start Playwright browser: {e}")
            await self.close()
            raise

    async def close(self):
        """Close the Playwright browser instance."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()

            logger.info("Playwright browser closed successfully")

        except Exception as e:
            logger.error(f"Error closing Playwright browser: {e}")

    async def fetch_page(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_time: Optional[int] = None,
    ) -> str:
        """
        Fetch a page and return its HTML content.

        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for before returning
            wait_time: Additional time to wait in milliseconds

        Returns:
            Page HTML content

        Raises:
            PlaywrightTimeoutError: If page load times out
            Exception: For other errors
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first or use as context manager.")

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                logger.info(f"Fetching URL: {url} (attempt {retry_count + 1}/{self.max_retries})")

                # Navigate to the page
                response = await self._page.goto(url, wait_until='domcontentloaded')

                if response and response.status >= 400:
                    logger.warning(f"Received HTTP {response.status} for {url}")

                # Wait for specific selector if provided
                if wait_for_selector:
                    await self._page.wait_for_selector(wait_for_selector, timeout=self.timeout)

                # Additional wait time if specified
                if wait_time:
                    await asyncio.sleep(wait_time / 1000)

                # Get page content
                content = await self._page.content()

                logger.info(f"Successfully fetched {url} ({len(content)} bytes)")
                return content

            except PlaywrightTimeoutError as e:
                last_error = e
                retry_count += 1
                logger.warning(f"Timeout fetching {url} (attempt {retry_count}/{self.max_retries}): {e}")

                if retry_count < self.max_retries:
                    # Exponential backoff
                    wait_seconds = 2 ** retry_count + random.uniform(0, 1)
                    logger.info(f"Retrying in {wait_seconds:.2f} seconds...")
                    await asyncio.sleep(wait_seconds)

            except Exception as e:
                last_error = e
                retry_count += 1
                logger.error(f"Error fetching {url} (attempt {retry_count}/{self.max_retries}): {e}")

                if retry_count < self.max_retries:
                    wait_seconds = 2 ** retry_count + random.uniform(0, 1)
                    await asyncio.sleep(wait_seconds)

        # All retries exhausted
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        raise last_error

    async def screenshot(self, path: str, full_page: bool = True):
        """
        Take a screenshot of the current page.

        Args:
            path: Path to save the screenshot
            full_page: Capture full page or just viewport
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first or use as context manager.")

        await self._page.screenshot(path=path, full_page=full_page)
        logger.info(f"Screenshot saved to {path}")

    async def evaluate_js(self, script: str) -> Any:
        """
        Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute

        Returns:
            Result of the JavaScript execution
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first or use as context manager.")

        return await self._page.evaluate(script)
