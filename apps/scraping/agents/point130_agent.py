"""
130Point Scraper Agent.

130Point (https://130point.com) aggregates *completed* sales — primarily eBay
sold/auction comps — which makes it one of the highest-value sources for market
value (realized prices, not asking prices). This agent follows the same
LLM-with-traditional-fallback pattern as the eBay agent and is registered in the
scraping registry so the orchestrator runs it alongside other sources.

NOTE: the live 130Point search submits a form; ``build_search_url`` produces the
GET approximation. The parsing layer is what carries the value and is fully
covered by tests with representative fixtures.
"""

import hashlib
import logging
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from .scraper_agent import ScraperAgent
from ..schemas import (
    CardGrade,
    PriceInfo,
    Point130Item,
    Point130ScrapeResult,
    ScrapeMetadata,
    extract_grade_from_text,
    extract_price_from_text,
)

logger = logging.getLogger(__name__)


# ============================================================================
# LLM Extraction Schemas
# ============================================================================

class Point130ItemExtraction(BaseModel):
    """Schema for the LLM to extract a single completed sale."""

    title: str = Field(description="Complete title of the card sold")
    price: float = Field(description="Final sale price in USD (numeric only)")
    url: str = Field(default="", description="URL to the sale, if available")
    sale_type: str = Field(default="sold", description="'sold', 'auction', 'best_offer' or 'fixed'")
    sold_date: str | None = Field(default=None, description="Date the sale completed, if shown")


class Point130ExtractionResult(BaseModel):
    """Complete extraction result with all sales."""

    items: List[Point130ItemExtraction] = Field(description="All completed sales on the page")
    total_results: int = Field(default=0, description="Total number of sales reported")


# ============================================================================
# Agent
# ============================================================================

class Point130Agent(ScraperAgent):
    """Scraper for 130Point completed-sales comps."""

    def __init__(self, use_llm: bool = True):
        super().__init__(
            site_name="130Point",
            base_url="https://130point.com",
            use_llm=use_llm,
        )

    # --- LLM hooks ---------------------------------------------------------
    def get_extraction_schema(self) -> Type[BaseModel]:
        return Point130ExtractionResult

    def create_extraction_prompt(self, query: str) -> str:
        return f"""You are extracting COMPLETED card sales from a 130Point results page \
for the query: "{query}".

For each sale, extract:
1. Title: the full card title
2. Price: the final sale price in USD (numeric only, no symbols)
3. URL: link to the sale if present
4. Sale type: 'auction', 'best_offer', 'fixed' or 'sold'
5. Sold date: the date the sale completed, if shown

These are realized sales, not active listings. Extract every sale on the page."""

    # --- URL ---------------------------------------------------------------
    def build_search_url(self, query: str, **kwargs) -> str:
        """Build the 130Point sales search URL (GET approximation)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"{self.base_url}/sales/?query={encoded}"
        logger.info(f"Built 130Point search URL: {url}")
        return url

    # --- Traditional parsing ----------------------------------------------
    def _traditional_parse(self, html: str, query: str) -> Dict[str, Any]:
        soup = self.create_soup(html)
        items: List[Point130Item] = []

        row_selectors = [
            'tr.sale',
            'table.sales tbody tr',
            'div.sale-row',
            'tbody tr',
        ]
        rows = []
        for selector in row_selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Found {len(rows)} sale rows using selector: {selector}")
                break

        if not rows:
            logger.warning("No sale rows found on 130Point page")
            return {'items': [], 'total_results': 0}

        for idx, row in enumerate(rows):
            try:
                item = self._parse_sale_row(row)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Error parsing 130Point row {idx}: {e}")
                continue

        return {'items': items, 'total_results': len(items)}

    def _parse_sale_row(self, row) -> Optional[Point130Item]:
        link = row.select_one('a')
        title = self.extract_text(
            row.select_one('.sale-title') or link
        )
        if not title:
            return None
        url = self.extract_attribute(link, 'href', '') if link else ''

        price_elem = row.select_one('.sale-price') or row.select_one('.price')
        price_text = self.extract_text(price_elem) if price_elem else row.get_text(" ", strip=True)
        amount = extract_price_from_text(price_text)
        if amount is None or amount <= 0:
            return None

        sale_type_text = self.extract_text(row.select_one('.sale-type')).lower()
        sale_type = 'sold'
        for candidate in ('auction', 'best_offer', 'best offer', 'fixed'):
            if candidate in sale_type_text:
                sale_type = candidate.replace(' ', '_')
                break

        grade = extract_grade_from_text(title)
        item_id = self._stable_id(title, amount, url)

        return Point130Item(
            item_id=item_id,
            title=title,
            url=url or f"{self.base_url}/sales/",
            source='130point',
            price=PriceInfo(amount=amount, currency='USD'),
            grade=grade,
            sale_type=sale_type,
            scraped_at=datetime.utcnow(),
        )

    @staticmethod
    def _stable_id(title: str, amount: float, url: str) -> str:
        basis = f"{title}|{amount}|{url}".encode('utf-8')
        return hashlib.md5(basis).hexdigest()[:16]

    # --- Scrape ------------------------------------------------------------
    async def scrape(self, query: str, **kwargs) -> Point130ScrapeResult:
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
    ) -> Point130ScrapeResult:
        items: List[Point130Item] = []

        for item_data in parsed_data.get('items', []):
            try:
                if isinstance(item_data, Point130Item):
                    items.append(item_data)
                    continue

                if isinstance(item_data, Point130ItemExtraction):
                    item_dict = item_data.model_dump()
                else:
                    item_dict = item_data

                title = item_dict.get('title', '')
                if not title:
                    continue
                amount = item_dict.get('price', 0.0) or 0.0
                if amount <= 0:
                    continue

                items.append(Point130Item(
                    item_id=self._stable_id(title, amount, item_dict.get('url', '')),
                    title=title,
                    url=item_dict.get('url') or f"{self.base_url}/sales/",
                    source='130point',
                    price=PriceInfo(amount=amount, currency='USD'),
                    grade=extract_grade_from_text(title),
                    sale_type=item_dict.get('sale_type', 'sold'),
                    scraped_at=datetime.utcnow(),
                ))
            except Exception as e:
                logger.warning(f"Error converting 130Point item: {e}")
                continue

        return Point130ScrapeResult(
            success=success,
            source='130point',
            query=query,
            items=items,
            metadata=metadata,
            total_results=parsed_data.get('total_results', len(items)),
        )
