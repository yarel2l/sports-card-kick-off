"""
Scraper Agent using LangChain and LLMs with traditional fallback.

This agent uses LLMs to extract structured data from web pages,
making it adaptable to HTML structure changes and new websites.
Falls back to traditional BeautifulSoup parsing when needed.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from ..fetchers import BaseFetcher
from ..schemas import BaseScrapeResult, ScrapeMetadata
from .base_agent import BaseScraperAgent

logger = logging.getLogger(__name__)


class ScraperAgent(BaseScraperAgent):
    """
    Scraper agent with LLM extraction and traditional fallback.

    This agent automatically adapts to different HTML structures by using
    LLMs to understand and extract the required information. Falls back
    to traditional BeautifulSoup parsing when LLM extraction fails.

    Configuration is loaded dynamically from SystemConfiguration (database),
    allowing API keys and model selection to be changed without restart.
    """

    def __init__(
        self,
        site_name: str,
        base_url: str,
        use_llm: bool = True,
    ):
        """
        Initialize the intelligent scraper agent.

        Args:
            site_name: Name of the target site
            base_url: Base URL of the target site
            use_llm: Enable LLM extraction (can be disabled for traditional-only mode)
        """
        # Load configuration from database
        from apps.core.models import SystemConfiguration
        self._config = SystemConfiguration.get_solo()

        # Initialize base with configuration values
        super().__init__(
            site_name,
            base_url,
            timeout=self._config.scraping_timeout,
            max_retries=self._config.max_retries
        )

        # LLM settings from configuration
        self.use_llm = use_llm and self._config.use_llm_by_default
        self.model_name = self._config.default_llm_model
        self.temperature = self._config.llm_temperature
        self.use_traditional_fallback = self._config.use_traditional_fallback

        # Lazy initialize LLM (only when needed)
        self._llm = None

    @property
    def llm(self):
        """
        Lazy initialization of LLM based on configuration.

        Loads the appropriate LLM provider (OpenAI, Anthropic, Google, HuggingFace)
        based on the configured model and sets up API keys from database.

        Returns:
            Initialized LLM instance or None if configuration is missing
        """
        if self._llm is None and self.use_llm:
            provider = self._config.get_active_llm_provider()

            if not provider:
                logger.warning(f"No API key configured for model: {self.model_name}")
                return None

            try:
                if provider == 'openai':
                    # Set API key in environment for LangChain
                    os.environ['OPENAI_API_KEY'] = self._config.openai_api_key
                    if self._config.openai_org_id:
                        os.environ['OPENAI_ORG_ID'] = self._config.openai_org_id

                    self._llm = ChatOpenAI(
                        model=self.model_name,
                        temperature=self.temperature,
                        max_tokens=self._config.llm_max_tokens,
                    )
                    logger.info(f"Initialized OpenAI LLM: {self.model_name}")

                elif provider == 'anthropic':
                    os.environ['ANTHROPIC_API_KEY'] = self._config.anthropic_api_key

                    self._llm = ChatAnthropic(
                        model=self.model_name,
                        temperature=self.temperature,
                        max_tokens=self._config.llm_max_tokens,
                    )
                    logger.info(f"Initialized Anthropic LLM: {self.model_name}")

                elif provider == 'google':
                    os.environ['GOOGLE_API_KEY'] = self._config.google_api_key

                    self._llm = ChatGoogleGenerativeAI(
                        model=self.model_name,
                        temperature=self.temperature,
                        max_output_tokens=self._config.llm_max_tokens,
                    )
                    logger.info(f"Initialized Google Gemini LLM: {self.model_name}")

                elif provider == 'huggingface':
                    os.environ['HUGGINGFACEHUB_API_TOKEN'] = self._config.huggingface_api_key

                    self._llm = HuggingFaceEndpoint(
                        repo_id=self.model_name,
                        temperature=self.temperature,
                        max_new_tokens=self._config.llm_max_tokens,
                    )
                    logger.info(f"Initialized HuggingFace LLM: {self.model_name}")

            except Exception as e:
                logger.error(f"Failed to initialize LLM ({provider}): {e}")
                return None

        return self._llm

    @abstractmethod
    def get_extraction_schema(self) -> Type[BaseModel]:
        """
        Get the Pydantic schema for data extraction.

        Returns:
            Pydantic model class defining the expected structure
        """
        pass

    @abstractmethod
    def create_extraction_prompt(self, query: str) -> str:
        """
        Create the prompt for LLM extraction.

        Args:
            query: Original search query

        Returns:
            Prompt template for the LLM
        """
        pass

    def parse_html(self, html: str, query: str) -> Dict[str, Any]:
        """
        Parse HTML using LLM extraction.

        This method is called by execute_scrape from BaseScraperAgent.

        Args:
            html: HTML content to parse
            query: Original search query

        Returns:
            Dictionary with parsed data
        """
        try:
            # Use LLM extraction
            result = self._llm_extract(html, query)
            return result
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

            # Try traditional parsing as fallback if enabled
            if self.use_traditional_fallback:
                logger.info("Attempting traditional parsing as fallback")
                try:
                    return self._traditional_parse(html, query)
                except Exception as fallback_error:
                    logger.error(f"Traditional parsing also failed: {fallback_error}")

            # Return empty result if all methods fail
            return {'items': [], 'total_results': 0}

    def _llm_extract(self, html: str, query: str) -> Dict[str, Any]:
        """
        Extract structured data using LLM.

        Args:
            html: HTML content
            query: Search query

        Returns:
            Extracted data dictionary
        """
        # Get the schema and parser
        schema = self.get_extraction_schema()
        parser = PydanticOutputParser(pydantic_object=schema)

        # Create the prompt
        extraction_prompt = self.create_extraction_prompt(query)

        # Build the full prompt with format instructions
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert web scraper that extracts structured data from HTML."),
            ("human", """{extraction_prompt}

HTML Content (truncated to relevant section):
{html_content}

{format_instructions}

Extract all relevant items from the HTML and return them in the specified format.""")
        ])

        # Truncate HTML to avoid token limits (keep relevant sections)
        truncated_html = self._truncate_html(html)

        # Create the chain
        chain = prompt_template | self.llm | parser

        # Run extraction
        logger.info(f"Running LLM extraction for {self.site_name}")
        result = chain.invoke({
            "extraction_prompt": extraction_prompt,
            "html_content": truncated_html,
            "format_instructions": parser.get_format_instructions(),
        })

        # Convert Pydantic model to dict
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()

        logger.info(f"LLM extracted {len(result_dict.get('items', []))} items")

        return result_dict

    def _traditional_parse(self, html: str, query: str) -> Dict[str, Any]:
        """
        Traditional HTML parsing fallback.

        Subclasses can override this to provide traditional parsing
        when LLM extraction fails.

        Args:
            html: HTML content
            query: Search query

        Returns:
            Parsed data dictionary
        """
        # Default implementation returns empty
        # Subclasses should override with BeautifulSoup parsing
        logger.warning(f"Traditional parsing not implemented for {self.site_name}")
        return {'items': [], 'total_results': 0}

    def _truncate_html(self, html: str, max_chars: int = 50000) -> str:
        """
        Truncate HTML to fit within token limits while keeping relevant content.

        Args:
            html: Full HTML content
            max_chars: Maximum characters to keep

        Returns:
            Truncated HTML
        """
        if len(html) <= max_chars:
            return html

        # Try to find main content area
        soup = self.create_soup(html)

        # Common content selectors
        content_selectors = [
            'main',
            '[role="main"]',
            '#main',
            '.main-content',
            '.search-results',
            '.results',
            'article',
        ]

        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                content_html = str(content)
                if len(content_html) <= max_chars:
                    logger.info(f"Truncated HTML using selector: {selector}")
                    return content_html

        # Fallback: just truncate from the start
        logger.warning(f"Using simple truncation for HTML (original: {len(html)} chars)")
        return html[:max_chars]

    async def scrape_with_metadata(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scrape with additional metadata about extraction method.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            Dictionary with results and metadata
        """
        start_time = time.time()

        try:
            result = await self.execute_scrape(query, **kwargs)
            execution_time = time.time() - start_time

            return {
                'result': result,
                'extraction_method': 'llm',
                'model_used': self.model_name,
                'execution_time': execution_time,
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Scraping failed: {e}")

            return {
                'result': None,
                'extraction_method': 'failed',
                'error': str(e),
                'execution_time': execution_time,
            }
