"""
Base Pydantic schemas for scraping data validation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re


class BaseItem(BaseModel):
    """Base schema for scraped items."""

    title: str = Field(..., description="Item title")
    url: HttpUrl = Field(..., description="Item URL")
    source: str = Field(..., description="Source website")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when item was scraped")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "2023 Topps Chrome Mike Trout PSA 10",
                "url": "https://example.com/item/123",
                "source": "ebay",
                "scraped_at": "2025-01-15T10:30:00Z"
            }
        }


class CardGrade(BaseModel):
    """Schema for card grading information."""

    grading_company: Optional[str] = Field(None, description="Grading company (PSA, BGS, SGC, etc.)")
    grade: Optional[str] = Field(None, description="Card grade (e.g., PSA 10, BGS 9.5)")
    numeric_grade: Optional[float] = Field(None, description="Numeric grade value", ge=1.0, le=10.0)

    @field_validator('grading_company')
    @classmethod
    def validate_grading_company(cls, v):
        """Validate and normalize grading company names."""
        if v:
            v_upper = v.upper()
            # Map common variations to standard names
            mapping = {
                'PSA': 'PSA',
                'BGS': 'BGS',
                'BECKETT': 'BGS',
                'SGC': 'SGC',
                'CGC': 'CGC',
                'HGA': 'HGA',
            }
            for key, value in mapping.items():
                if key in v_upper:
                    return value
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "grading_company": "PSA",
                "grade": "PSA 10",
                "numeric_grade": 10.0
            }
        }


class PriceInfo(BaseModel):
    """Schema for pricing information."""

    amount: float = Field(..., description="Price amount", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    shipping: Optional[float] = Field(None, description="Shipping cost", ge=0)
    total: Optional[float] = Field(None, description="Total price including shipping", gt=0)

    @field_validator('total', mode='before')
    @classmethod
    def calculate_total(cls, v, info):
        """Calculate total if not provided."""
        if v is None:
            amount = info.data.get('amount', 0)
            shipping = info.data.get('shipping', 0) or 0
            return amount + shipping
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 250.00,
                "currency": "USD",
                "shipping": 5.99,
                "total": 255.99
            }
        }


class SellerInfo(BaseModel):
    """Schema for seller information."""

    seller_name: str = Field(..., description="Seller username or name")
    rating: Optional[float] = Field(None, description="Seller rating", ge=0, le=100)
    feedback_count: Optional[int] = Field(None, description="Number of feedback reviews", ge=0)
    location: Optional[str] = Field(None, description="Seller location")

    class Config:
        json_schema_extra = {
            "example": {
                "seller_name": "sports_cards_pro",
                "rating": 99.8,
                "feedback_count": 15234,
                "location": "California, USA"
            }
        }


class ScrapeMetadata(BaseModel):
    """Metadata about the scraping operation."""

    execution_time_seconds: float = Field(..., description="Execution time in seconds", ge=0)
    items_found: int = Field(..., description="Number of items found", ge=0)
    page_count: int = Field(default=1, description="Number of pages scraped", ge=1)
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_time_seconds": 3.45,
                "items_found": 25,
                "page_count": 1,
                "errors": [],
                "warnings": ["Item 5 had incomplete data"]
            }
        }


class BaseScrapeResult(BaseModel):
    """Base schema for scrape results."""

    success: bool = Field(..., description="Whether the scrape was successful")
    source: str = Field(..., description="Source website identifier")
    query: str = Field(..., description="Original search query")
    metadata: ScrapeMetadata = Field(..., description="Scraping metadata")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw scraped data for debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "source": "ebay",
                "query": "Mike Trout PSA 10",
                "metadata": {
                    "execution_time_seconds": 3.45,
                    "items_found": 25,
                    "page_count": 1,
                    "errors": [],
                    "warnings": []
                }
            }
        }


def extract_grade_from_text(text: str) -> Optional[CardGrade]:
    """
    Extract grading information from text.

    Args:
        text: Text to parse for grading information

    Returns:
        CardGrade object or None if no grade found

    Examples:
        >>> extract_grade_from_text("PSA 10 Mike Trout")
        CardGrade(grading_company='PSA', grade='PSA 10', numeric_grade=10.0)

        >>> extract_grade_from_text("BGS 9.5 Gem Mint")
        CardGrade(grading_company='BGS', grade='BGS 9.5', numeric_grade=9.5)
    """
    if not text:
        return None

    text_upper = text.upper()

    # Common grading patterns
    patterns = [
        # PSA grades
        (r'PSA\s*(\d+(?:\.\d+)?)', 'PSA'),
        # BGS/Beckett grades
        (r'(?:BGS|BECKETT)\s*(\d+(?:\.\d+)?)', 'BGS'),
        # SGC grades
        (r'SGC\s*(\d+(?:\.\d+)?)', 'SGC'),
        # CGC grades
        (r'CGC\s*(\d+(?:\.\d+)?)', 'CGC'),
        # HGA grades
        (r'HGA\s*(\d+(?:\.\d+)?)', 'HGA'),
    ]

    for pattern, company in patterns:
        match = re.search(pattern, text_upper)
        if match:
            grade_value = float(match.group(1))
            return CardGrade(
                grading_company=company,
                grade=f"{company} {grade_value}",
                numeric_grade=grade_value
            )

    return None


def extract_price_from_text(text: str) -> Optional[float]:
    """
    Extract price from text.

    Args:
        text: Text to parse for price

    Returns:
        Price as float or None if no price found

    Examples:
        >>> extract_price_from_text("$250.99")
        250.99

        >>> extract_price_from_text("Price: 1,250.00 USD")
        1250.0
    """
    if not text:
        return None

    # Remove currency symbols and commas
    text = text.replace('$', '').replace(',', '').strip()

    # Extract number
    match = re.search(r'(\d+(?:\.\d{1,2})?)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None
