"""
Goldin Scraper Agent.

Goldin is a high-end auction house. This agent yields auction lots: open lots
are recorded as AUCTION observations (current bid) and closed lots as SOLD
(hammer price). Same LLM-with-traditional-fallback structure as the other
agents; registered in the scraping registry.

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
    GoldinItem,
    GoldinScrapeResult,
    PriceInfo,
    ScrapeMetadata,
    extract_grade_from_text,
    extract_price_from_text,
)

logger = logging.getLogger(__name__)


class GoldinItemExtraction(BaseModel):
    """Schema for the LLM to extract a single Goldin lot."""

    title: str = Field(description="Complete title of the lot")
    price: float = Field(description="Current bid or hammer price in USD (numeric only)")
    url: str = Field(default="", description="URL to the lot, if available")
    lot_number: str | None = Field(default=None, description="Lot number if shown")
    status: str | None = Field(default=None, description="'open'/'live' or 'closed'/'sold'")


class GoldinExtractionResult(BaseModel):
    items: List[GoldinItemExtraction] = Field(description="All auction lots on the page")
    total_results: int = Field(default=0, description="Total number of lots reported")


class GoldinAgent(ScraperAgent):
    """Scraper for Goldin auction lots."""

    def __init__(self, use_llm: bool = True):
        super().__init__(
            site_name="Goldin",
            base_url="https://goldin.co",
            use_llm=use_llm,
        )

    # --- LLM hooks ---------------------------------------------------------
    def get_extraction_schema(self) -> Type[BaseModel]:
        return GoldinExtractionResult

    def create_extraction_prompt(self, query: str) -> str:
        return f"""You are extracting auction lots from a Goldin results page \
for the query: "{query}".

For each lot extract:
1. Title: the full lot title
2. Price: the current bid (open lots) or hammer price (closed lots) in USD, numeric only
3. URL: link to the lot if present
4. Lot number: if shown
5. Status: 'open'/'live' or 'closed'/'sold'

Extract every lot on the page."""

    # --- URL ---------------------------------------------------------------
    def build_search_url(self, query: str, **kwargs) -> str:
        encoded = urllib.parse.quote_plus(query)
        url = f"{self.base_url}/search?query={encoded}"
        logger.info(f"Built Goldin search URL: {url}")
        return url

    # --- Traditional parsing ----------------------------------------------
    def _traditional_parse(self, html: str, query: str) -> Dict[str, Any]:
        soup = self.create_soup(html)
        items: List[GoldinItem] = []

        lot_selectors = [
            'div.lot-card',
            'div.auction-item',
            'li.lot',
            'div.item',
        ]
        lots = []
        for selector in lot_selectors:
            lots = soup.select(selector)
            if lots:
                logger.info(f"Found {len(lots)} Goldin lots using selector: {selector}")
                break

        if not lots:
            logger.warning("No Goldin lots found on page")
            return {'items': [], 'total_results': 0}

        for idx, lot in enumerate(lots):
            try:
                item = self._parse_lot(lot)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Error parsing Goldin lot {idx}: {e}")
                continue

        return {'items': items, 'total_results': len(items)}

    def _parse_lot(self, lot) -> Optional[GoldinItem]:
        link = lot.select_one('a')
        title = self.extract_text(lot.select_one('.lot-title') or lot.select_one('.title') or link)
        if not title:
            return None
        url = self.extract_attribute(link, 'href', '') if link else ''
        if url and url.startswith('/'):
            url = f"{self.base_url}{url}"

        price_elem = lot.select_one('.current-bid') or lot.select_one('.price')
        price_text = self.extract_text(price_elem) if price_elem else lot.get_text(" ", strip=True)
        amount = extract_price_from_text(price_text)
        if amount is None or amount <= 0:
            return None

        status_text = self.extract_text(lot.select_one('.lot-status')).lower()
        observation_kind = 'SOLD' if ('closed' in status_text or 'sold' in status_text) else 'AUCTION'

        lot_number = self.extract_text(lot.select_one('.lot-number')) or None
        grade = extract_grade_from_text(title)
        item_id = hashlib.md5(f"{title}|{lot_number}|{url}".encode('utf-8')).hexdigest()[:16]

        return GoldinItem(
            item_id=item_id,
            title=title,
            url=url or f"{self.base_url}/search",
            source='goldin',
            price=PriceInfo(amount=amount, currency='USD'),
            grade=grade,
            lot_number=lot_number,
            observation_kind=observation_kind,
            scraped_at=datetime.utcnow(),
        )

    # --- Scrape ------------------------------------------------------------
    async def scrape(self, query: str, **kwargs) -> GoldinScrapeResult:
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
    ) -> GoldinScrapeResult:
        items: List[GoldinItem] = []

        for item_data in parsed_data.get('items', []):
            try:
                if isinstance(item_data, GoldinItem):
                    items.append(item_data)
                    continue

                if isinstance(item_data, GoldinItemExtraction):
                    item_dict = item_data.model_dump()
                else:
                    item_dict = item_data

                title = item_dict.get('title', '')
                amount = item_dict.get('price', 0.0) or 0.0
                if not title or amount <= 0:
                    continue

                status = (item_dict.get('status') or '').lower()
                observation_kind = 'SOLD' if ('closed' in status or 'sold' in status) else 'AUCTION'
                lot_number = item_dict.get('lot_number')
                item_id = hashlib.md5(
                    f"{title}|{lot_number}|{item_dict.get('url', '')}".encode('utf-8')
                ).hexdigest()[:16]

                items.append(GoldinItem(
                    item_id=item_id,
                    title=title,
                    url=item_dict.get('url') or f"{self.base_url}/search",
                    source='goldin',
                    price=PriceInfo(amount=amount, currency='USD'),
                    grade=extract_grade_from_text(title),
                    lot_number=lot_number,
                    observation_kind=observation_kind,
                    scraped_at=datetime.utcnow(),
                ))
            except Exception as e:
                logger.warning(f"Error converting Goldin item: {e}")
                continue

        return GoldinScrapeResult(
            success=success,
            source='goldin',
            query=query,
            items=items,
            metadata=metadata,
            total_results=parsed_data.get('total_results', len(items)),
        )
