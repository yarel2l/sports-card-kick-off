"""
Pydantic schemas for 130Point (sales-comp aggregator).

130Point surfaces *completed* sales (mostly eBay sold/auction comps), so these
items represent realized prices rather than active listings. The ``sale_type``
field carries how the sale closed; ingestion records all of them as SOLD price
observations, which are the most valuable signal for market value.
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from .base_schemas import BaseItem, CardGrade, PriceInfo, BaseScrapeResult


class Point130Item(BaseItem):
    """A single completed sale recorded by 130Point."""

    item_id: str = Field(..., description="Stable identifier for the sale")
    price: PriceInfo = Field(..., description="Sale price information")
    grade: Optional[CardGrade] = Field(None, description="Grading information if graded")

    sale_type: str = Field(
        default='sold',
        description="How the sale closed: 'sold', 'auction', 'best_offer', 'fixed'",
    )
    sold_date: Optional[datetime] = Field(None, description="Date the sale completed")
    bids: Optional[int] = Field(None, description="Number of bids (auctions)", ge=0)


class Point130ScrapeResult(BaseScrapeResult):
    """Result set of completed sales from 130Point."""

    items: List[Point130Item] = Field(default_factory=list)
    total_results: Optional[int] = Field(None, description="Total sales found", ge=0)
