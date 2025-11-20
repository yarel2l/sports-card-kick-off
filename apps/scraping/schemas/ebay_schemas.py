"""
Pydantic schemas for eBay scraping.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from .base_schemas import BaseItem, CardGrade, PriceInfo, SellerInfo, BaseScrapeResult, ScrapeMetadata


class EbayListingType(BaseModel):
    """Schema for eBay listing type information."""

    listing_type: str = Field(..., description="Type of listing (auction, buy_it_now, classified)")
    is_auction: bool = Field(default=False, description="Whether item is an auction")
    is_buy_it_now: bool = Field(default=False, description="Whether item has Buy It Now")
    bids_count: Optional[int] = Field(None, description="Number of bids (for auctions)", ge=0)
    time_left: Optional[str] = Field(None, description="Time remaining for auction")
    end_date: Optional[datetime] = Field(None, description="Auction end date")

    class Config:
        json_schema_extra = {
            "example": {
                "listing_type": "buy_it_now",
                "is_auction": False,
                "is_buy_it_now": True,
                "bids_count": None,
                "time_left": None,
                "end_date": None
            }
        }


class EbayCondition(BaseModel):
    """Schema for eBay item condition."""

    condition: str = Field(..., description="Item condition")
    condition_description: Optional[str] = Field(None, description="Detailed condition description")
    is_graded: bool = Field(default=False, description="Whether item is graded")

    class Config:
        json_schema_extra = {
            "example": {
                "condition": "New",
                "condition_description": "Professionally graded PSA 10",
                "is_graded": True
            }
        }


class EbayItem(BaseItem):
    """
    Schema for eBay item data.

    Extends BaseItem with eBay-specific fields.
    """

    # eBay specific identifiers
    item_id: str = Field(..., description="eBay item ID")
    epid: Optional[str] = Field(None, description="eBay Product ID (ePID)")

    # Pricing
    price: PriceInfo = Field(..., description="Price information")

    # Card details
    grade: Optional[CardGrade] = Field(None, description="Grading information")

    # Seller
    seller: SellerInfo = Field(..., description="Seller information")

    # Listing details
    listing: EbayListingType = Field(..., description="Listing type information")
    condition: EbayCondition = Field(..., description="Item condition")

    # Images
    image_url: Optional[HttpUrl] = Field(None, description="Primary image URL")
    gallery_urls: List[HttpUrl] = Field(default_factory=list, description="Additional gallery image URLs")

    # Additional info
    watchers: Optional[int] = Field(None, description="Number of watchers", ge=0)
    sold_count: Optional[int] = Field(None, description="Number sold (if available)", ge=0)
    availability: Optional[str] = Field(None, description="Availability status")

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "123456789012",
                "epid": "28056789123",
                "title": "2023 Topps Chrome Mike Trout PSA 10 Gem Mint",
                "url": "https://www.ebay.com/itm/123456789012",
                "source": "ebay",
                "price": {
                    "amount": 250.00,
                    "currency": "USD",
                    "shipping": 5.99,
                    "total": 255.99
                },
                "grade": {
                    "grading_company": "PSA",
                    "grade": "PSA 10",
                    "numeric_grade": 10.0
                },
                "seller": {
                    "seller_name": "sports_cards_pro",
                    "rating": 99.8,
                    "feedback_count": 15234,
                    "location": "California, USA"
                },
                "listing": {
                    "listing_type": "buy_it_now",
                    "is_auction": False,
                    "is_buy_it_now": True
                },
                "condition": {
                    "condition": "New",
                    "condition_description": "Professionally graded PSA 10",
                    "is_graded": True
                },
                "image_url": "https://i.ebayimg.com/images/example.jpg",
                "watchers": 45,
                "scraped_at": "2025-01-15T10:30:00Z"
            }
        }


class EbayScrapeResult(BaseScrapeResult):
    """
    Schema for eBay scrape results.

    Contains list of EbayItem objects and metadata.
    """

    items: List[EbayItem] = Field(default_factory=list, description="List of scraped eBay items")

    # eBay-specific metadata
    total_results: Optional[int] = Field(None, description="Total number of results on eBay", ge=0)
    page_number: int = Field(default=1, description="Page number scraped", ge=1)
    results_per_page: int = Field(default=50, description="Results per page", ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "source": "ebay",
                "query": "Mike Trout PSA 10",
                "items": [],
                "total_results": 1234,
                "page_number": 1,
                "results_per_page": 50,
                "metadata": {
                    "execution_time_seconds": 3.45,
                    "items_found": 25,
                    "page_count": 1,
                    "errors": [],
                    "warnings": []
                }
            }
        }


class EbaySearchFilters(BaseModel):
    """
    Schema for eBay search filters.
    """

    # Price filters
    min_price: Optional[float] = Field(None, description="Minimum price", ge=0)
    max_price: Optional[float] = Field(None, description="Maximum price", ge=0)

    # Listing type filters
    listing_type: Optional[str] = Field(None, description="Listing type (all, auction, buy_it_now)")

    # Condition filters
    condition: Optional[str] = Field(None, description="Item condition")

    # Grading filters
    grading_company: Optional[str] = Field(None, description="Grading company (PSA, BGS, etc.)")
    min_grade: Optional[float] = Field(None, description="Minimum grade", ge=1.0, le=10.0)

    # Sorting
    sort_by: str = Field(default="best_match", description="Sort order")

    # Pagination
    page_number: int = Field(default=1, description="Page number to fetch", ge=1)
    results_per_page: int = Field(default=50, description="Results per page", ge=1, le=200)

    class Config:
        json_schema_extra = {
            "example": {
                "min_price": 100.0,
                "max_price": 500.0,
                "listing_type": "buy_it_now",
                "grading_company": "PSA",
                "min_grade": 9.0,
                "sort_by": "price_asc",
                "page_number": 1,
                "results_per_page": 50
            }
        }
