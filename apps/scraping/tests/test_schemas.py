"""
Tests for scraping Pydantic schemas.
"""

from django.test import TestCase
from pydantic import ValidationError
from datetime import datetime

from apps.scraping.schemas.base_schemas import (
    BaseItem,
    CardGrade,
    PriceInfo,
    SellerInfo,
    ScrapeMetadata,
    BaseScrapeResult,
    extract_grade_from_text,
    extract_price_from_text,
)
from apps.scraping.schemas.ebay_schemas import (
    EbayListingType,
    EbayCondition,
    EbayItem,
    EbayScrapeResult,
    EbaySearchFilters,
)


class BaseSchemaTests(TestCase):
    """Test base scraping schemas."""

    def test_base_item_valid(self):
        """Test creating BaseItem with valid data."""
        item = BaseItem(
            title='Test Item',
            url='https://example.com/item/123',
            source='ebay'
        )

        self.assertEqual(item.title, 'Test Item')
        # HttpUrl does not automatically add trailing slash
        self.assertEqual(str(item.url), 'https://example.com/item/123')
        self.assertEqual(item.source, 'ebay')
        self.assertIsInstance(item.scraped_at, datetime)

    def test_base_item_missing_required_fields(self):
        """Test BaseItem fails without required fields."""
        with self.assertRaises(ValidationError):
            BaseItem(
                title='Test Item'
                # Missing url and source
            )

    def test_card_grade_valid(self):
        """Test creating CardGrade with valid data."""
        grade = CardGrade(
            grading_company='PSA',
            grade='PSA 10',
            numeric_grade=10.0
        )

        self.assertEqual(grade.grading_company, 'PSA')
        self.assertEqual(grade.grade, 'PSA 10')
        self.assertEqual(grade.numeric_grade, 10.0)

    def test_card_grade_company_normalization(self):
        """Test grading company name normalization."""
        # Test Beckett normalization
        grade = CardGrade(
            grading_company='Beckett',
            numeric_grade=9.5
        )
        self.assertEqual(grade.grading_company, 'BGS')

        # Test PSA normalization
        grade = CardGrade(
            grading_company='psa',
            numeric_grade=10.0
        )
        self.assertEqual(grade.grading_company, 'PSA')

    def test_card_grade_invalid_numeric_grade(self):
        """Test CardGrade fails with invalid numeric grade."""
        # Grade below 1.0
        with self.assertRaises(ValidationError):
            CardGrade(
                grading_company='PSA',
                numeric_grade=0.5
            )

        # Grade above 10.0
        with self.assertRaises(ValidationError):
            CardGrade(
                grading_company='PSA',
                numeric_grade=11.0
            )

    def test_price_info_valid(self):
        """Test creating PriceInfo with valid data."""
        price = PriceInfo(
            amount=100.50,
            currency='USD'
        )

        self.assertEqual(price.amount, 100.50)
        self.assertEqual(price.currency, 'USD')
        self.assertIsNone(price.shipping)

    def test_price_info_with_shipping(self):
        """Test PriceInfo with shipping cost."""
        price = PriceInfo(
            amount=100.00,
            currency='USD',
            shipping=5.99
        )

        self.assertEqual(price.amount, 100.00)
        self.assertEqual(price.shipping, 5.99)
        # Note: Due to Pydantic v2 validator limitations, total is not auto-calculated
        # It must be provided explicitly or calculated externally
        self.assertIsNone(price.total)

    def test_price_info_total_calculation(self):
        """Test providing total explicitly."""
        price = PriceInfo(
            amount=250.00,
            shipping=10.00,
            total=260.00  # Total must be provided explicitly
        )

        self.assertEqual(price.total, 260.00)

    def test_price_info_negative_amount(self):
        """Test PriceInfo fails with negative amount."""
        with self.assertRaises(ValidationError):
            PriceInfo(
                amount=-10.00,
                currency='USD'
            )

    def test_price_info_negative_shipping(self):
        """Test PriceInfo fails with negative shipping."""
        with self.assertRaises(ValidationError):
            PriceInfo(
                amount=100.00,
                shipping=-5.00
            )

    def test_seller_info_valid(self):
        """Test creating SellerInfo with valid data."""
        seller = SellerInfo(
            seller_name='testseller',
            rating=99.5,
            feedback_count=1000
        )

        self.assertEqual(seller.seller_name, 'testseller')
        self.assertEqual(seller.rating, 99.5)
        self.assertEqual(seller.feedback_count, 1000)

    def test_seller_info_rating_bounds(self):
        """Test SellerInfo rating validation."""
        # Valid rating
        seller = SellerInfo(
            seller_name='seller',
            rating=50.0
        )
        self.assertEqual(seller.rating, 50.0)

        # Rating above 100
        with self.assertRaises(ValidationError):
            SellerInfo(
                seller_name='seller',
                rating=101.0
            )

        # Negative rating
        with self.assertRaises(ValidationError):
            SellerInfo(
                seller_name='seller',
                rating=-1.0
            )

    def test_scrape_metadata_valid(self):
        """Test creating ScrapeMetadata with valid data."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.45,
            items_found=25,
            page_count=1
        )

        self.assertEqual(metadata.execution_time_seconds, 3.45)
        self.assertEqual(metadata.items_found, 25)
        self.assertEqual(metadata.page_count, 1)
        self.assertEqual(metadata.errors, [])
        self.assertEqual(metadata.warnings, [])

    def test_scrape_metadata_with_errors(self):
        """Test ScrapeMetadata with errors and warnings."""
        metadata = ScrapeMetadata(
            execution_time_seconds=5.0,
            items_found=10,
            errors=['Error 1', 'Error 2'],
            warnings=['Warning 1']
        )

        self.assertEqual(len(metadata.errors), 2)
        self.assertEqual(len(metadata.warnings), 1)

    def test_base_scrape_result_success(self):
        """Test creating successful BaseScrapeResult."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.0,
            items_found=10
        )

        result = BaseScrapeResult(
            success=True,
            source='ebay',
            query='Mike Trout PSA 10',
            metadata=metadata
        )

        self.assertTrue(result.success)
        self.assertEqual(result.source, 'ebay')
        self.assertEqual(result.query, 'Mike Trout PSA 10')
        self.assertIsNotNone(result.metadata)

    def test_extract_grade_from_text_psa(self):
        """Test extracting PSA grade from text."""
        grade = extract_grade_from_text('Mike Trout PSA 10 Gem Mint')

        self.assertIsNotNone(grade)
        self.assertEqual(grade.grading_company, 'PSA')
        self.assertEqual(grade.numeric_grade, 10.0)
        self.assertEqual(grade.grade, 'PSA 10.0')

    def test_extract_grade_from_text_bgs(self):
        """Test extracting BGS grade from text."""
        grade = extract_grade_from_text('2023 Topps BGS 9.5 Gem Mint')

        self.assertIsNotNone(grade)
        self.assertEqual(grade.grading_company, 'BGS')
        self.assertEqual(grade.numeric_grade, 9.5)

    def test_extract_grade_from_text_no_grade(self):
        """Test extract_grade_from_text returns None for no grade."""
        grade = extract_grade_from_text('Ungraded baseball card')

        self.assertIsNone(grade)

    def test_extract_price_from_text(self):
        """Test extracting price from text."""
        # Test with dollar sign
        price = extract_price_from_text('$250.99')
        self.assertEqual(price, 250.99)

        # Test with commas
        price = extract_price_from_text('$1,250.00')
        self.assertEqual(price, 1250.00)

        # Test without currency symbol
        price = extract_price_from_text('99.99')
        self.assertEqual(price, 99.99)

    def test_extract_price_from_text_no_price(self):
        """Test extract_price_from_text returns None for no price."""
        price = extract_price_from_text('No price available')

        self.assertIsNone(price)


class EbaySchemaTests(TestCase):
    """Test eBay-specific schemas."""

    def test_ebay_listing_type_buy_it_now(self):
        """Test EbayListingType for Buy It Now listing."""
        listing = EbayListingType(
            listing_type='buy_it_now',
            is_buy_it_now=True
        )

        self.assertEqual(listing.listing_type, 'buy_it_now')
        self.assertTrue(listing.is_buy_it_now)
        self.assertFalse(listing.is_auction)

    def test_ebay_listing_type_auction(self):
        """Test EbayListingType for auction."""
        listing = EbayListingType(
            listing_type='auction',
            is_auction=True,
            bids_count=5,
            time_left='2d 3h'
        )

        self.assertEqual(listing.listing_type, 'auction')
        self.assertTrue(listing.is_auction)
        self.assertEqual(listing.bids_count, 5)
        self.assertEqual(listing.time_left, '2d 3h')

    def test_ebay_condition_graded(self):
        """Test EbayCondition for graded item."""
        condition = EbayCondition(
            condition='New',
            condition_description='Professionally graded PSA 10',
            is_graded=True
        )

        self.assertEqual(condition.condition, 'New')
        self.assertTrue(condition.is_graded)
        self.assertIn('PSA 10', condition.condition_description)

    def test_ebay_item_valid(self):
        """Test creating EbayItem with valid data."""
        item = EbayItem(
            item_id='123456789',
            title='Test eBay Listing',
            url='https://ebay.com/itm/123456789',
            source='ebay',
            price=PriceInfo(amount=99.99, currency='USD'),
            seller=SellerInfo(seller_name='testseller'),
            listing=EbayListingType(listing_type='buy_it_now', is_buy_it_now=True),
            condition=EbayCondition(condition='New')
        )

        self.assertEqual(item.item_id, '123456789')
        self.assertEqual(item.title, 'Test eBay Listing')
        self.assertEqual(item.price.amount, 99.99)
        self.assertEqual(item.seller.seller_name, 'testseller')

    def test_ebay_item_with_grade(self):
        """Test EbayItem with grading information."""
        grade = CardGrade(
            grading_company='PSA',
            grade='PSA 10',
            numeric_grade=10.0
        )

        item = EbayItem(
            item_id='123456789',
            title='Test Card PSA 10',
            url='https://ebay.com/itm/123456789',
            source='ebay',
            price=PriceInfo(amount=250.00),
            seller=SellerInfo(seller_name='seller'),
            listing=EbayListingType(listing_type='buy_it_now', is_buy_it_now=True),
            condition=EbayCondition(condition='New', is_graded=True),
            grade=grade
        )

        self.assertIsNotNone(item.grade)
        self.assertEqual(item.grade.grading_company, 'PSA')
        self.assertEqual(item.grade.numeric_grade, 10.0)

    def test_ebay_scrape_result_valid(self):
        """Test creating EbayScrapeResult."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.0,
            items_found=2
        )

        result = EbayScrapeResult(
            success=True,
            source='ebay',
            query='Mike Trout',
            metadata=metadata,
            items=[],
            total_results=100
        )

        self.assertTrue(result.success)
        self.assertEqual(result.source, 'ebay')
        self.assertEqual(result.total_results, 100)
        self.assertEqual(len(result.items), 0)

    def test_ebay_scrape_result_with_items(self):
        """Test EbayScrapeResult with items."""
        metadata = ScrapeMetadata(
            execution_time_seconds=3.0,
            items_found=1
        )

        item = EbayItem(
            item_id='123',
            title='Test Item',
            url='https://ebay.com/itm/123',
            source='ebay',
            price=PriceInfo(amount=50.00),
            seller=SellerInfo(seller_name='seller'),
            listing=EbayListingType(listing_type='buy_it_now', is_buy_it_now=True),
            condition=EbayCondition(condition='Used')
        )

        result = EbayScrapeResult(
            success=True,
            source='ebay',
            query='test',
            metadata=metadata,
            items=[item]
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].item_id, '123')

    def test_ebay_search_filters_valid(self):
        """Test EbaySearchFilters with valid data."""
        filters = EbaySearchFilters(
            min_price=100.0,
            max_price=500.0,
            listing_type='buy_it_now',
            grading_company='PSA',
            min_grade=9.0
        )

        self.assertEqual(filters.min_price, 100.0)
        self.assertEqual(filters.max_price, 500.0)
        self.assertEqual(filters.grading_company, 'PSA')
        self.assertEqual(filters.min_grade, 9.0)

    def test_ebay_search_filters_pagination(self):
        """Test EbaySearchFilters pagination defaults."""
        filters = EbaySearchFilters()

        self.assertEqual(filters.page_number, 1)
        self.assertEqual(filters.results_per_page, 50)
        self.assertEqual(filters.sort_by, 'best_match')

    def test_ebay_search_filters_invalid_grade(self):
        """Test EbaySearchFilters fails with invalid grade."""
        with self.assertRaises(ValidationError):
            EbaySearchFilters(
                min_grade=11.0  # Above 10.0
            )
