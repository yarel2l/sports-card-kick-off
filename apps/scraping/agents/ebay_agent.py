"""
eBay Scraper Agent with LLM extraction and traditional fallback.

This unified agent can scrape eBay using:
1. LLM-based extraction (primary, adaptive to HTML changes)
2. Traditional BeautifulSoup parsing (fallback, faster)
"""

import logging
import urllib.parse
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel, Field

from .scraper_agent import ScraperAgent
from ..schemas import (
    EbayItem,
    EbayScrapeResult,
    EbayListingType,
    EbayCondition,
    PriceInfo,
    SellerInfo,
    CardGrade,
    ScrapeMetadata,
    extract_grade_from_text,
    extract_price_from_text,
)

logger = logging.getLogger(__name__)


# ============================================================================
# LLM Extraction Schemas
# ============================================================================

class EbayItemExtraction(BaseModel):
    """Schema for LLM to extract individual eBay items."""

    title: str = Field(description="Complete title of the listing")
    price: float = Field(description="Price in USD (numeric value only)")
    shipping_cost: float = Field(default=0.0, description="Shipping cost in USD, 0 if free shipping")
    item_id: str = Field(description="eBay item ID")
    url: str = Field(description="Full URL to the listing")
    seller_username: str = Field(description="Seller's username")
    seller_feedback_score: int = Field(default=0, description="Seller's feedback score")
    seller_positive_percentage: float = Field(default=100.0, description="Seller's positive feedback percentage")
    condition: str = Field(description="Item condition (e.g., 'New', 'Used', 'Certified')")
    listing_type: str = Field(description="Type of listing: 'buy_it_now', 'auction', or 'best_offer'")
    image_url: str | None = Field(default=None, description="URL of the primary image")
    watchers: int | None = Field(default=None, description="Number of watchers if shown")


class EbayExtractionResult(BaseModel):
    """Complete extraction result with all items."""

    items: List[EbayItemExtraction] = Field(
        description="List of all product listings found on the page"
    )
    total_results: int = Field(
        description="Total number of search results reported by eBay"
    )


# ============================================================================
# Unified eBay Agent
# ============================================================================

class EbayAgent(ScraperAgent):
    """
    Unified eBay scraper with LLM extraction and traditional fallback.

    Features:
    - Primary: LLM-based extraction (adapts to HTML changes)
    - Fallback: Traditional BeautifulSoup parsing (faster, reliable)
    - Automatic switching between methods
    - Structured output with Pydantic validation
    - Dynamic configuration from database (API keys, model selection, timeouts)
    - Supports multiple LLM providers: OpenAI, Anthropic, Google, HuggingFace
    """

    def __init__(self, use_llm: bool = True):
        """
        Initialize eBay agent.

        Configuration (timeout, retries, model, API keys) is loaded automatically
        from SystemConfiguration in the database.

        Args:
            use_llm: If True, use LLM extraction (default: True, can be overridden by DB config)
        """
        super().__init__(
            site_name="eBay",
            base_url="https://www.ebay.com",
            use_llm=use_llm,
        )

    # ========================================================================
    # LLM Extraction Methods (from ScraperAgent)
    # ========================================================================

    def get_extraction_schema(self) -> Type[BaseModel]:
        """Get the Pydantic schema for eBay data extraction."""
        return EbayExtractionResult

    def create_extraction_prompt(self, query: str) -> str:
        """Create extraction prompt for eBay listings."""
        return f"""You are extracting product listings from eBay search results for the query: "{query}"

Your task is to extract ALL product listings visible on the page. For each listing, extract:

1. **Title**: The complete product title
2. **Price**: The current price in USD (numeric value, no currency symbols)
3. **Shipping**: Shipping cost (0 if free shipping)
4. **Item ID**: The eBay item number/ID
5. **URL**: The complete URL to the listing
6. **Seller Info**: Username, feedback score, and positive percentage
7. **Condition**: Item condition (New, Used, Certified, etc.)
8. **Listing Type**: Whether it's "buy_it_now", "auction", or "best_offer"
9. **Image URL**: URL of the main product image
10. **Watchers**: Number of people watching (if shown)

IMPORTANT:
- Extract ALL listings, not just the first few
- Skip sponsored ads or promotional content
- For prices, extract only the numeric value (e.g., "29.99" not "$29.99")
- For auction items, extract the current bid price
- If information is missing, use appropriate defaults (0 for numbers, empty string for text)
- The total_results should be the number shown by eBay (e.g., "1,234 results")

Be thorough and accurate. Extract every listing you can find on the page."""

    # ========================================================================
    # Traditional Parsing Methods
    # ========================================================================

    def _traditional_parse(self, html: str, query: str) -> Dict[str, Any]:
        """
        Traditional BeautifulSoup parsing as fallback.

        Args:
            html: HTML content
            query: Search query

        Returns:
            Dictionary with parsed items and metadata
        """
        soup = self.create_soup(html)
        items: List[EbayItem] = []

        # Find all listing items using multiple selectors
        item_selectors = [
            'div.s-card',  # New card-based layout (2024+)
            'div.su-card-container',  # Alternative card container
            'li.s-item',  # Legacy standard search results
            'div.s-item',  # Legacy alternative layout
            'div.s-item__wrapper',  # Legacy wrapper selector
            'ul.srp-results li',  # Results list items
        ]

        listing_elements = []
        for selector in item_selectors:
            listing_elements = soup.select(selector)
            if listing_elements:
                logger.info(f"Found {len(listing_elements)} items using selector: {selector}")
                break

        if not listing_elements:
            logger.warning("No listing elements found on page")
            return {'items': [], 'total_results': 0}

        # Parse each listing
        for idx, item_elem in enumerate(listing_elements):
            try:
                # Skip sponsored/ad items
                if item_elem.select_one('.s-item__title--tag'):
                    continue

                parsed_item = self._parse_listing_item(item_elem, query)
                if parsed_item:
                    items.append(parsed_item)

            except Exception as e:
                logger.warning(f"Error parsing item {idx}: {e}")
                continue

        # Extract total results count
        total_results = self._extract_total_results(soup)

        logger.info(f"Successfully parsed {len(items)} items from eBay (traditional)")

        return {
            'items': items,
            'total_results': total_results,
        }

    def _parse_listing_item(self, item_elem, query: str) -> Optional[EbayItem]:
        """Parse a single eBay listing item using traditional selectors."""
        try:
            # Extract item ID
            item_id = self._extract_item_id(item_elem)
            if not item_id:
                return None

            # Title - support both s-card and s-item layouts
            title_elem = (
                item_elem.select_one('.s-card__title') or
                item_elem.select_one('.s-item__title')
            )
            title = self.extract_text(title_elem, "")
            if not title or title.lower() == "shop on ebay":
                return None

            # URL - support both layouts
            link_elem = (
                item_elem.select_one('a.s-card__link') or
                item_elem.select_one('.su-card-container__header') or
                item_elem.select_one('a.s-item__link')
            )
            url = self.extract_attribute(link_elem, 'href', "")
            if not url:
                return None

            # Price
            price_info = self._parse_price(item_elem)
            if not price_info:
                return None

            # Image - support both layouts
            image_elem = (
                item_elem.select_one('.s-card__image img') or
                item_elem.select_one('img.s-item__image-img')
            )
            image_url = self.extract_attribute(image_elem, 'src', None)

            # Extract grade from title
            grade = extract_grade_from_text(title)

            # Seller info
            seller_info = self._parse_seller(item_elem)

            # Listing type
            listing_type = self._parse_listing_type(item_elem)

            # Condition
            condition = self._parse_condition(item_elem, bool(grade))

            # Watchers
            watchers = self._parse_watchers(item_elem)

            # Create EbayItem
            return EbayItem(
                item_id=item_id,
                title=title,
                url=url,
                source="ebay",
                price=price_info,
                grade=grade,
                seller=seller_info,
                listing=listing_type,
                condition=condition,
                image_url=image_url,
                watchers=watchers,
                scraped_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error parsing listing item: {e}")
            return None

    def _extract_item_id(self, item_elem) -> Optional[str]:
        """Extract eBay item ID."""
        # Try data attribute
        item_id = item_elem.get('data-iid')
        if item_id:
            return str(item_id)

        # Try extracting from URL
        link_elem = (
            item_elem.select_one('a.s-card__link') or
            item_elem.select_one('.su-card-container__header') or
            item_elem.select_one('a.s-item__link')
        )
        if link_elem:
            url = link_elem.get('href', '')
            parts = url.split('/itm/')
            if len(parts) > 1:
                item_id_part = parts[1].split('?')[0].split('/')[-1]
                return item_id_part

        return None

    def _parse_price(self, item_elem) -> Optional[PriceInfo]:
        """Parse price information."""
        try:
            # Price - support both layouts
            price_elem = (
                item_elem.select_one('.s-card__price') or
                item_elem.select_one('.su-styled-text.primary') or
                item_elem.select_one('.s-item__price')
            )
            if not price_elem:
                return None

            price_text = self.extract_text(price_elem)
            price_amount = extract_price_from_text(price_text)

            if price_amount is None:
                return None

            # Shipping - support both layouts
            shipping_elem = (
                item_elem.select_one('.s-card__sep + span') or
                item_elem.select_one('.s-item__shipping')
            )
            shipping_text = self.extract_text(shipping_elem, "")
            shipping_amount = 0.0

            if shipping_text and 'free' not in shipping_text.lower():
                shipping_amount = extract_price_from_text(shipping_text) or 0.0

            return PriceInfo(
                amount=price_amount,
                currency='USD',
                shipping=shipping_amount,
            )

        except Exception as e:
            logger.error(f"Error parsing price: {e}")
            return None

    def _parse_seller(self, item_elem) -> SellerInfo:
        """Parse seller information."""
        seller_elem = item_elem.select_one('.s-item__seller-info')
        seller_name = ""
        feedback_score = 0
        positive_percentage = 100.0

        if seller_elem:
            username_elem = seller_elem.select_one('.s-item__seller-info-text')
            seller_name = self.extract_text(username_elem, "Unknown")

            feedback_elem = seller_elem.select_one('.s-item__seller-feedback')
            if feedback_elem:
                feedback_text = self.extract_text(feedback_elem)
                # Extract numbers from feedback text (including decimals)
                import re
                # Match integers and decimals
                numbers = re.findall(r'\d+\.?\d*', feedback_text)
                if numbers:
                    feedback_score = int(float(numbers[0]))
                if len(numbers) > 1:
                    positive_percentage = float(numbers[1])

        return SellerInfo(
            seller_name=seller_name or "Unknown",
            rating=positive_percentage,
            feedback_count=feedback_score,
        )

    def _parse_listing_type(self, item_elem) -> EbayListingType:
        """Parse listing type."""
        # Check for auction indicators
        if item_elem.select_one('.s-item__bids') or item_elem.select_one('.s-item__time-left'):
            return EbayListingType(
                listing_type="auction",
                is_auction=True,
                is_buy_it_now=False
            )

        # Check for best offer
        if item_elem.select_one('.s-item__purchase-options'):
            purchase_text = self.extract_text(item_elem.select_one('.s-item__purchase-options'))
            if 'or best offer' in purchase_text.lower():
                return EbayListingType(
                    listing_type="best_offer",
                    is_auction=False,
                    is_buy_it_now=True
                )

        return EbayListingType(
            listing_type="buy_it_now",
            is_auction=False,
            is_buy_it_now=True
        )

    def _parse_condition(self, item_elem, has_grade: bool) -> EbayCondition:
        """Parse item condition."""
        condition_elem = item_elem.select_one('.s-item__condition')
        condition_text = self.extract_text(condition_elem, "").lower()

        condition_str = "Used"
        is_graded = has_grade

        if 'new' in condition_text:
            condition_str = "New"
        elif 'certified' in condition_text or 'refurbished' in condition_text:
            condition_str = "Certified Refurbished"
        elif has_grade:
            condition_str = "Used"  # Graded cards are typically "used"

        return EbayCondition(
            condition=condition_str,
            is_graded=is_graded
        )

    def _parse_watchers(self, item_elem) -> Optional[int]:
        """Parse number of watchers."""
        watchers_elem = item_elem.select_one('.s-item__watchers')
        if watchers_elem:
            watchers_text = self.extract_text(watchers_elem)
            import re
            numbers = re.findall(r'\d+', watchers_text)
            if numbers:
                return int(numbers[0])
        return None

    def _extract_total_results(self, soup) -> int:
        """Extract total results count from page."""
        result_count_elem = soup.select_one('.srp-controls__count-heading')
        if result_count_elem:
            text = self.extract_text(result_count_elem)
            import re
            numbers = re.findall(r'[\d,]+', text)
            if numbers:
                # Remove commas and convert to int
                return int(numbers[-1].replace(',', ''))
        return 0

    # ========================================================================
    # URL Building
    # ========================================================================

    def build_search_url(self, query: str, **kwargs) -> str:
        """
        Build eBay search URL.

        Args:
            query: Search query
            **kwargs: Optional parameters:
                - page: Page number (default 1)
                - sort_by: Sort order (best_match, price_asc, price_desc, etc.)
                - listing_type: Filter by type (buy_it_now, auction)
                - min_price: Minimum price
                - max_price: Maximum price
                - results_per_page: Results per page (default 50)

        Returns:
            Complete search URL
        """
        # Encode query
        encoded_query = urllib.parse.quote_plus(query)
        url = f"{self.base_url}/sch/i.html?_nkw={encoded_query}"

        # Pagination
        page = kwargs.get('page', 1)
        if page > 1:
            url += f"&_pgn={page}"

        # Sorting
        sort_by = kwargs.get('sort_by')
        sort_mapping = {
            'best_match': '12',
            'price_asc': '15',
            'price_desc': '16',
            'newly_listed': '10',
            'ending_soonest': '1',
        }
        if sort_by in sort_mapping:
            url += f"&_sop={sort_mapping[sort_by]}"

        # Listing type filter
        listing_type = kwargs.get('listing_type')
        if listing_type == 'buy_it_now':
            url += "&LH_BIN=1"
        elif listing_type == 'auction':
            url += "&LH_Auction=1"

        # Price range
        min_price = kwargs.get('min_price')
        max_price = kwargs.get('max_price')
        if min_price is not None:
            url += f"&_udlo={min_price}"
        if max_price is not None:
            url += f"&_udhi={max_price}"

        # Results per page (default 50)
        results_per_page = kwargs.get('results_per_page', 50)
        url += f"&_ipg={results_per_page}"

        logger.info(f"Built eBay search URL: {url}")
        return url

    # ========================================================================
    # Main Scraping Method
    # ========================================================================

    async def scrape(self, query: str, **kwargs) -> EbayScrapeResult:
        """
        Scrape eBay using LLM extraction with traditional fallback.

        Args:
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            EbayScrapeResult with scraped items
        """
        # Override parse_html method to use LLM or traditional based on setting
        if not self.use_llm:
            # Force traditional parsing
            original_use_fallback = self.use_traditional_fallback
            self.use_traditional_fallback = False
            try:
                result = await self.execute_scrape(query, **kwargs)
            finally:
                self.use_traditional_fallback = original_use_fallback
            return result

        # Use default behavior (LLM with traditional fallback)
        return await self.execute_scrape(query, **kwargs)

    # ========================================================================
    # Result Creation
    # ========================================================================

    def _create_result(
        self,
        success: bool,
        query: str,
        metadata: ScrapeMetadata,
        parsed_data: Dict[str, Any]
    ) -> EbayScrapeResult:
        """
        Create EbayScrapeResult from parsed data.

        Handles both LLM extraction format and traditional parsing format.
        """
        items: List[EbayItem] = []

        for item_data in parsed_data.get('items', []):
            try:
                # If already an EbayItem (from traditional parsing)
                if isinstance(item_data, EbayItem):
                    items.append(item_data)
                    continue

                # Convert from LLM extraction format
                if isinstance(item_data, EbayItemExtraction):
                    item_dict = item_data.model_dump()
                else:
                    item_dict = item_data

                # Extract grade from title
                title = item_dict.get('title', '')
                grade = extract_grade_from_text(title)

                # Create price info
                price_info = PriceInfo(
                    amount=item_dict.get('price', 0.0),
                    currency='USD',
                    shipping=item_dict.get('shipping_cost', 0.0),
                )

                # Create seller info
                seller_info = SellerInfo(
                    seller_name=item_dict.get('seller_username', 'Unknown'),
                    rating=item_dict.get('seller_positive_percentage', 100.0),
                    feedback_count=item_dict.get('seller_feedback_score', 0),
                )

                # Map condition
                condition_str = item_dict.get('condition', 'used').lower()
                condition_display = "Used"
                if 'new' in condition_str:
                    condition_display = "New"
                elif 'certified' in condition_str or 'refurbished' in condition_str:
                    condition_display = "Certified Refurbished"

                condition = EbayCondition(
                    condition=condition_display,
                    is_graded=bool(grade)
                )

                # Map listing type
                listing_str = item_dict.get('listing_type', 'buy_it_now').lower()
                if 'auction' in listing_str:
                    listing_type = EbayListingType(
                        listing_type="auction",
                        is_auction=True,
                        is_buy_it_now=False
                    )
                elif 'offer' in listing_str:
                    listing_type = EbayListingType(
                        listing_type="best_offer",
                        is_auction=False,
                        is_buy_it_now=True
                    )
                else:
                    listing_type = EbayListingType(
                        listing_type="buy_it_now",
                        is_auction=False,
                        is_buy_it_now=True
                    )

                # Create EbayItem
                ebay_item = EbayItem(
                    item_id=item_dict.get('item_id', ''),
                    title=title,
                    url=item_dict.get('url', ''),
                    source='ebay',
                    price=price_info,
                    grade=grade,
                    seller=seller_info,
                    listing=listing_type,
                    condition=condition,
                    image_url=item_dict.get('image_url'),
                    watchers=item_dict.get('watchers'),
                    scraped_at=datetime.utcnow(),
                )

                items.append(ebay_item)

            except Exception as e:
                logger.warning(f"Error converting item data: {e}")
                continue

        return EbayScrapeResult(
            success=success,
            source="ebay",
            query=query,
            items=items,
            metadata=metadata,
            total_results=parsed_data.get('total_results', len(items)),
        )
