"""
Pydantic schemas for Goldin (auction house).

Goldin sells via timed/live auctions. An active lot is an in-progress auction
(current bid) and a closed lot is a realized sale. The ``observation_kind``
field carries this explicitly so ingestion records open lots as AUCTION and
closed lots as SOLD.
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from .base_schemas import BaseItem, CardGrade, PriceInfo, BaseScrapeResult


class GoldinItem(BaseItem):
    """A single auction lot on Goldin."""

    item_id: str = Field(..., description="Goldin lot identifier")
    price: PriceInfo = Field(..., description="Current bid (open) or hammer price (closed)")
    grade: Optional[CardGrade] = Field(None, description="Grading information if graded")

    lot_number: Optional[str] = Field(None, description="Auction lot number")
    auction_name: Optional[str] = Field(None, description="Name of the auction")
    end_date: Optional[datetime] = Field(None, description="Auction close date")
    bids: Optional[int] = Field(None, description="Number of bids", ge=0)

    # Maps directly to PriceObservation.Kind; 'AUCTION' for open lots, 'SOLD' for closed.
    observation_kind: str = Field(default='AUCTION', description="AUCTION (open) or SOLD (closed)")


class GoldinScrapeResult(BaseScrapeResult):
    """Result set of auction lots from Goldin."""

    items: List[GoldinItem] = Field(default_factory=list)
    total_results: Optional[int] = Field(None, description="Total lots found", ge=0)
