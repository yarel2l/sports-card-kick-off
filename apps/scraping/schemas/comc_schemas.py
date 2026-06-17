"""
Pydantic schemas for COMC (Check Out My Cards).

COMC is a fixed-price consignment marketplace, so its items are *active
listings* (asking prices). Ingestion records them as LISTING observations.
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from .base_schemas import BaseItem, CardGrade, PriceInfo, BaseScrapeResult


class ComcItem(BaseItem):
    """A single fixed-price listing on COMC."""

    item_id: str = Field(..., description="COMC listing identifier")
    price: PriceInfo = Field(..., description="Asking price")
    grade: Optional[CardGrade] = Field(None, description="Grading information if graded")
    condition: Optional[str] = Field(None, description="Condition text if shown")


class ComcScrapeResult(BaseScrapeResult):
    """Result set of active listings from COMC."""

    items: List[ComcItem] = Field(default_factory=list)
    total_results: Optional[int] = Field(None, description="Total listings found", ge=0)
