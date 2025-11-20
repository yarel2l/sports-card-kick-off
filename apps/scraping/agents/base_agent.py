"""
Base Agent for scraping using LangChain.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from bs4 import BeautifulSoup
from ..fetchers import BaseFetcher
from ..schemas import BaseScrapeResult, ScrapeMetadata

logger = logging.getLogger(__name__)


class BaseScraperAgent(ABC):
    """
    Base class for scraping agents.

    Each agent is responsible for scraping a specific website and
    returning structured data according to Pydantic schemas.
    """

    def __init__(
        self,
        site_name: str,
        base_url: str,
        timeout: int = 30000,
        max_retries: int = 3,
    ):
        """
        Initialize the scraper agent.

        Args:
            site_name: Name of the target site
            base_url: Base URL of the target site
            timeout: Request timeout in milliseconds
            max_retries: Maximum number of retry attempts
        """
        self.site_name = site_name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    async def scrape(self, query: str, **kwargs) -> BaseScrapeResult:
        """
        Scrape data from the target site.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            BaseScrapeResult with scraped data
        """
        pass

    @abstractmethod
    def parse_html(self, html: str, query: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract structured data.

        Args:
            html: HTML content to parse
            query: Original search query

        Returns:
            Dictionary with parsed data
        """
        pass

    def create_soup(self, html: str) -> BeautifulSoup:
        """
        Create BeautifulSoup object from HTML.

        Args:
            html: HTML content

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'lxml')

    def build_search_url(self, query: str, **kwargs) -> str:
        """
        Build search URL from query and parameters.

        Args:
            query: Search query
            **kwargs: Additional URL parameters

        Returns:
            Complete search URL
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement build_search_url")

    async def execute_scrape(
        self,
        query: str,
        fetcher: Optional[BaseFetcher] = None,
        **kwargs
    ) -> BaseScrapeResult:
        """
        Execute the scraping operation.

        Args:
            query: Search query
            fetcher: Optional BaseFetcher instance (creates new if not provided)
            **kwargs: Additional parameters

        Returns:
            BaseScrapeResult with scraped data
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Build search URL
            url = self.build_search_url(query, **kwargs)
            logger.info(f"Scraping URL: {url}")

            # Use provided fetcher or create new one
            should_close_fetcher = fetcher is None
            if fetcher is None:
                fetcher = BaseFetcher(
                    headless=True,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )

            try:
                # Start fetcher if not already started
                if not fetcher._page:
                    await fetcher.start()

                # Fetch page content
                html = await fetcher.fetch_page(url)

                # Parse HTML
                parsed_data = self.parse_html(html, query)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Create metadata
                metadata = ScrapeMetadata(
                    execution_time_seconds=round(execution_time, 2),
                    items_found=len(parsed_data.get('items', [])),
                    page_count=1,
                    errors=errors,
                    warnings=warnings
                )

                # Return successful result
                return self._create_result(
                    success=True,
                    query=query,
                    metadata=metadata,
                    parsed_data=parsed_data
                )

            finally:
                # Close fetcher if we created it
                if should_close_fetcher and fetcher:
                    await fetcher.close()

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error scraping {self.site_name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            metadata = ScrapeMetadata(
                execution_time_seconds=round(execution_time, 2),
                items_found=0,
                page_count=1,
                errors=errors,
                warnings=warnings
            )

            return self._create_result(
                success=False,
                query=query,
                metadata=metadata,
                parsed_data={}
            )

    @abstractmethod
    def _create_result(
        self,
        success: bool,
        query: str,
        metadata: ScrapeMetadata,
        parsed_data: Dict[str, Any]
    ) -> BaseScrapeResult:
        """
        Create result object from parsed data.

        Args:
            success: Whether scraping was successful
            query: Original query
            metadata: Scraping metadata
            parsed_data: Parsed data dictionary

        Returns:
            BaseScrapeResult subclass instance
        """
        pass

    def extract_text(self, element, default: str = "") -> str:
        """
        Safely extract text from BeautifulSoup element.

        Args:
            element: BeautifulSoup element
            default: Default value if extraction fails

        Returns:
            Extracted text or default value
        """
        if element:
            text = element.get_text(strip=True)
            return text if text else default
        return default

    def extract_attribute(self, element, attr: str, default: str = "") -> str:
        """
        Safely extract attribute from BeautifulSoup element.

        Args:
            element: BeautifulSoup element
            attr: Attribute name
            default: Default value if extraction fails

        Returns:
            Attribute value or default value
        """
        if element and element.has_attr(attr):
            return element[attr]
        return default
