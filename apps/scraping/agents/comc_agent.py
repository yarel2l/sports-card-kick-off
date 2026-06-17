"""
COMC (Check Out My Cards) Scraper Agent.

COMC is a fixed-price consignment marketplace, so this agent yields active
listings (asking prices). Same LLM-with-traditional-fallback structure as the
other agents; registered in the scraping registry so the orchestrator runs it
alongside eBay and 130Point.

NOTE: parsing is covered by tests with representative fixtures; selectors will
need tuning against the live site.
"""

import hashlib
import logging
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from .scraper_agent import ScraperAgent
from ..schemas import (
    ComcItem,
    ComcScrapeResult,
    PriceInfo,
    ScrapeMetadata,
    extract_grade_from_text,
    extract_price_from_text,
)

logger = logging.getLogger(__name__)


class ComcItemExtraction(BaseModel):
    """Schema for the LLM to extract a single COMC listing."""

    title: str = Field(description="Complete title of the card")
    price: float = Field(description="Asking price in USD (numeric only)")
    url: str = Field(default="", description="URL to the listing, if available")
    condition: str | None = Field(default=None, description="Condition text if shown")


class ComcExtractionResult(BaseModel):
    items: List[ComcItemExtraction] = Field(description="All listings on the page")
    total_results: int = Field(default=0, description="Total number of listings reported")


class ComcAgent(ScraperAgent):
    """Scraper for COMC fixed-price listings."""

    def __init__(self, use_llm: bool = True):
        super().__init__(
            site_name="COMC",
            base_url="https://www.comc.com",
            use_llm=use_llm,
        )

    # --- LLM hooks ---------------------------------------------------------
    def get_extraction_schema(self) -> Type[BaseModel]:
        return ComcExtractionResult

    def create_extraction_prompt(self, query: str) -> str:
        return f"""You are extracting fixed-price card listings from a COMC results page \
for the query: "{query}".

For each listing extract:
1. Title: the full card title
2. Price: the asking price in USD (numeric only, no symbols)
3. URL: link to the listing if present
4. Condition: condition text if shown

Extract every listing on the page."""

    # --- URL ---------------------------------------------------------------
    def build_search_url(self, query: str, **kwargs) -> str:
        encoded = urllib.parse.quote_plus(query)
        url = f"{self.base_url}/Cards?search={encoded}"
        logger.info(f"Built COMC search URL: {url}")
        return url

    # --- Traditional parsing ----------------------------------------------
    def _traditional_parse(self, html: str, query: str) -> Dict[str, Any]:
        soup = self.create_soup(html)
        items: List[ComcItem] = []

        card_selectors = [
            'div.product-card',
            'div.card-listing',
            'li.product',
            'div.item',
        ]
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                logger.info(f"Found {len(cards)} COMC listings using selector: {selector}")
                break

        if not cards:
            logger.warning("No COMC listings found on page")
            return {'items': [], 'total_results': 0}

        for idx, card in enumerate(cards):
            try:
                item = self._parse_card(card)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Error parsing COMC card {idx}: {e}")
                continue

        return {'items': items, 'total_results': len(items)}

    def _parse_card(self, card) -> Optional[ComcItem]:
        link = card.select_one('a')
        title = self.extract_text(card.select_one('.title') or link)
        if not title:
            return None
        url = self.extract_attribute(link, 'href', '') if link else ''
        if url and url.startswith('/'):
            url = f"{self.base_url}{url}"

        price_elem = card.select_one('.price') or card.select_one('.product-price')
        price_text = self.extract_text(price_elem) if price_elem else card.get_text(" ", strip=True)
        amount = extract_price_from_text(price_text)
        if amount is None or amount <= 0:
            return None

        condition = self.extract_text(card.select_one('.condition')) or None
        grade = extract_grade_from_text(title)
        item_id = hashlib.md5(f"{title}|{amount}|{url}".encode('utf-8')).hexdigest()[:16]

        return ComcItem(
            item_id=item_id,
            title=title,
            url=url or f"{self.base_url}/Cards",
            source='comc',
            price=PriceInfo(amount=amount, currency='USD'),
            grade=grade,
            condition=condition,
            scraped_at=datetime.utcnow(),
        )

    # --- Scrape ------------------------------------------------------------
    async def scrape(self, query: str, **kwargs) -> ComcScrapeResult:
        if not self.use_llm:
            original = self.use_traditional_fallback
            self.use_traditional_fallback = False
            try:
                return await self.execute_scrape(query, **kwargs)
            finally:
                self.use_traditional_fallback = original
        return await self.execute_scrape(query, **kwargs)

    # --- Result building ---------------------------------------------------
    def _create_result(
        self,
        success: bool,
        query: str,
        metadata: ScrapeMetadata,
        parsed_data: Dict[str, Any],
    ) -> ComcScrapeResult:
        items: List[ComcItem] = []

        for item_data in parsed_data.get('items', []):
            try:
                if isinstance(item_data, ComcItem):
                    items.append(item_data)
                    continue

                if isinstance(item_data, ComcItemExtraction):
                    item_dict = item_data.model_dump()
                else:
                    item_dict = item_data

                title = item_dict.get('title', '')
                amount = item_dict.get('price', 0.0) or 0.0
                if not title or amount <= 0:
                    continue

                item_id = hashlib.md5(
                    f"{title}|{amount}|{item_dict.get('url', '')}".encode('utf-8')
                ).hexdigest()[:16]
                items.append(ComcItem(
                    item_id=item_id,
                    title=title,
                    url=item_dict.get('url') or f"{self.base_url}/Cards",
                    source='comc',
                    price=PriceInfo(amount=amount, currency='USD'),
                    grade=extract_grade_from_text(title),
                    condition=item_dict.get('condition'),
                    scraped_at=datetime.utcnow(),
                ))
            except Exception as e:
                logger.warning(f"Error converting COMC item: {e}")
                continue

        return ComcScrapeResult(
            success=success,
            source='comc',
            query=query,
            items=items,
            metadata=metadata,
            total_results=parsed_data.get('total_results', len(items)),
        )
