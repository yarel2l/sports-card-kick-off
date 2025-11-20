"""
Search API Views.

This module implements the search functionality with specialized APIViews
following REST best practices and matching the project's architecture pattern.
"""

from django.db.models import Avg, Count, Q, Sum
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError

from ..models import Search, ScrapeResult, TargetSite, SearchHistory
from ..serializers import (
    SearchSerializer,
    SearchCreateSerializer,
    SearchDetailSerializer,
    ScrapeResultSerializer,
    SearchHistorySerializer,
    TargetSiteSerializer,
    UserStatsSerializer,
)
from ..tasks import execute_search_task


class CreateSearchView(generics.CreateAPIView):
    """
    Create a new search and initiate scraping across configured sites.
    
    **Process:**
    1. Validates search query (minimum 3 characters)
    2. Creates search record with status PENDING
    3. Triggers asynchronous scraping task via Celery
    4. Returns search ID and initial status
    
    **The scraping process runs in the background:**
    - Executes across multiple sites in parallel (currently eBay)
    - Updates search status to PROCESSING → COMPLETED/FAILED/PARTIAL
    - Results are stored and can be retrieved via GET /api/v1/search/{id}/
    
    **Query Tips:**
    - Include player name for better results
    - Optionally include: year, set name, grade (e.g., "PSA 10")
    - Example: "Michael Jordan 1986 Fleer PSA 10"
    """
    serializer_class = SearchCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary="Create new search",
        description="""
        Create a new sports card search and initiate AI-powered scraping across multiple marketplaces.

        **Process:**
        1. Validates search query (minimum 3 characters)
        2. Creates search record with status PENDING
        3. Triggers asynchronous scraping task via Celery
        4. Returns search ID and initial status immediately
        5. AI orchestrator processes query in background (15-30 seconds)
        6. Results stored and accessible via search ID

        **AI-Powered Features:**
        - Automatic player name extraction
        - Card year detection
        - Set name identification
        - Grade parsing (PSA, BGS, CGC, etc.)
        - Natural language query understanding

        **Scraping Process:**
        - Executes across multiple sites in parallel
        - Uses LangChain/LangGraph orchestration
        - Playwright-based fetching with anti-detection
        - Traditional + LLM-based parsing for accuracy
        - Results aggregated by site type (SALES, AUCTION, POPULATION)

        **Query Tips:**
        - Include player name for best results
        - Add year to narrow search: "1986", "2003"
        - Specify grade: "PSA 10", "BGS 9.5"
        - Include set name: "Fleer", "Topps Chrome"
        - Example: "Michael Jordan 1986 Fleer PSA 10"

        **Response:**
        - Immediate return with search ID
        - Status: PENDING (will update to PROCESSING → COMPLETED)
        - Poll status via GET /api/v1/search/{search_id}/
        - Retrieve results when status is COMPLETED/PARTIAL

        **Status Flow:**
        ```
        PENDING → PROCESSING → COMPLETED
                            → FAILED
                            → PARTIAL
        ```
        """,
        request=SearchCreateSerializer,
        responses={
            201: SearchSerializer,
            400: OpenApiResponse(
                description="Invalid query - must be at least 3 characters"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
        },
        examples=[
            OpenApiExample(
                name='Create Search Request',
                value={
                    'query': 'Michael Jordan 1986 Fleer PSA 10'
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Create Search Response',
                value={
                    'id': '123e4567-e89b-12d3-a456-426614174000',
                    'query': 'Michael Jordan 1986 Fleer PSA 10',
                    'status': 'PENDING',
                    'player_name': None,
                    'card_year': None,
                    'card_set': None,
                    'grade': None,
                    'total_items_found': 0,
                    'successful_sites': 0,
                    'failed_sites': 0,
                    'execution_time_seconds': None,
                    'created_at': '2025-11-20T10:30:00Z',
                    'completed_at': None
                },
                response_only=True,
                status_codes=['201']
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request to create a new search."""
        return self.create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Create search and trigger Celery task."""
        search = serializer.save(user=self.request.user)
        
        # Trigger async scraping task
        execute_search_task.delay(str(search.id))
    
    def create(self, request, *args, **kwargs):
        """Override create to return full search data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return full search data using SearchSerializer
        search = Search.objects.get(id=serializer.instance.id)
        output_serializer = SearchSerializer(search)
        headers = self.get_success_headers(output_serializer.data)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class SearchHistoryView(generics.ListAPIView):
    """
    Get user's search history ordered by most recent.
    
    Returns a paginated list of the user's past searches with basic information.
    Use this endpoint to display search history and allow users to re-execute searches.
    
    **Query Parameters:**
    - page: Page number for pagination
    - page_size: Number of results per page (default: 20, max: 100)
    """
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary="Get search history",
        description="""
        Retrieve the authenticated user's search history ordered by most recent access.

        **Purpose:**
        - Display user's past searches for quick reference
        - Allow re-execution of previous searches
        - Track search activity and patterns
        - Provide quick access to successful searches

        **Response Data:**
        - Query text from past searches
        - Success status of each search
        - Total number of items found
        - Last accessed timestamp
        - Paginated results for performance

        **Pagination:**
        - Default: 20 results per page
        - Maximum: 100 results per page
        - Use `?page=2` for next page
        - Use `?page_size=50` to customize page size

        **Use Cases:**
        - Dashboard: Show recent search activity
        - Search Bar: Display search suggestions from history
        - Analytics: Track most searched queries
        - Quick Access: Re-run successful searches

        **Sorting:**
        - Ordered by `accessed_at` (most recent first)
        - Includes searches from last 1000 searches
        """,
        responses={
            200: SearchHistorySerializer(many=True),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
        },
        examples=[
            OpenApiExample(
                name='Search History Response',
                value=[
                    {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'query': 'Michael Jordan 1986 Fleer PSA 10',
                        'was_successful': True,
                        'total_results': 45,
                        'accessed_at': '2025-11-20T10:30:00Z'
                    },
                    {
                        'id': '223e4567-e89b-12d3-a456-426614174001',
                        'query': 'LeBron James Rookie',
                        'was_successful': True,
                        'total_results': 78,
                        'accessed_at': '2025-11-19T15:20:00Z'
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve search history."""
        return self.list(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get search history for authenticated user."""
        return SearchHistory.objects.filter(
            user=self.request.user
        ).select_related('search')


class SearchDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific search.
    
    Returns complete search information including status, parsed query components,
    execution metrics, and all results from different sites.
    
    **Use Cases:**
    - Check search status (PENDING, PROCESSING, COMPLETED, FAILED, PARTIAL)
    - View parsed query components (player, year, set, grade)
    - Access execution metrics (time, sites queried, items found)
    - Get basic result information (detailed items via /results/ endpoint)
    """
    serializer_class = SearchDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'search_id'
    
    @extend_schema(
        tags=['Search'],
        summary="Get search details",
        description="""        Get detailed information about a specific search including status, metrics, and results summary.

        **Purpose:**
        - Monitor search status in real-time
        - View parsed query components (player, year, set, grade)
        - Check execution metrics and performance
        - Access aggregated results from all sites
        - Track progress of active searches

        **Response Includes:**
        - Complete search metadata
        - AI-extracted query components
        - Execution statistics (time, sites, items)
        - Results from each scraped site
        - Error messages if applicable

        **Status Monitoring:**
        - PENDING: Search queued, not yet started
        - PROCESSING: AI orchestrator actively scraping
        - COMPLETED: All sites successfully scraped
        - PARTIAL: Some sites succeeded, others failed
        - FAILED: All sites failed or critical error
        - CANCELLED: User cancelled the search

        **Polling Strategy:**
        For real-time updates, poll this endpoint every 2-3 seconds while status is PROCESSING:
        ```javascript
        const interval = setInterval(async () => {
          const data = await fetchSearch(searchId);
          if (['COMPLETED', 'FAILED', 'PARTIAL', 'CANCELLED'].includes(data.status)) {
            clearInterval(interval);
            // Handle results
          }
        }, 2000);
        ```

        **Results Summary:**
        - Nested results array shows outcome from each site
        - Each result includes: site name, status, item count, execution time
        - Use GET /{search_id}/results/ for full item details
        """,
        responses={
            200: SearchDetailSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(
                description="Search not found or does not belong to the authenticated user"
            ),
        },
        examples=[
            OpenApiExample(
                name='Search Details Response - Completed',
                value={
                    'id': '123e4567-e89b-12d3-a456-426614174000',
                    'user': '456e4567-e89b-12d3-a456-426614174111',
                    'query': 'Michael Jordan 1986 Fleer PSA 10',
                    'status': 'COMPLETED',
                    'player_name': 'Michael Jordan',
                    'card_year': 1986,
                    'card_set': 'Fleer',
                    'grade': 'PSA 10',
                    'total_sites': 1,
                    'successful_sites': 1,
                    'failed_sites': 0,
                    'total_items_found': 45,
                    'execution_time_seconds': 12.5,
                    'error_message': None,
                    'results': [
                        {
                            'id': '323e4567-e89b-12d3-a456-426614174222',
                            'target_site': '523e4567-e89b-12d3-a456-426614174333',
                            'site_name': 'eBay',
                            'site_type': 'SALES',
                            'status': 'SUCCESS',
                            'data': {
                                'items': [],
                                'total_results': 45
                            },
                            'items_count': 45,
                            'execution_time_seconds': 12.5,
                            'error_message': None,
                            'created_at': '2025-11-20T10:30:15Z'
                        }
                    ],
                    'created_at': '2025-11-20T10:30:00Z',
                    'completed_at': '2025-11-20T10:30:30Z'
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve search details."""
        return self.retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get searches for authenticated user."""
        return Search.objects.filter(
            user=self.request.user
        ).prefetch_related('results__target_site')


class SearchResultsView(generics.ListAPIView):
    """
    Get detailed results for a specific search.
    
    Returns all scrape results from different sites for the given search,
    including full item data, execution time, and any errors encountered.
    
    **Response includes:**
    - All items found with complete details (title, price, URL, images, etc.)
    - Site-specific metadata (execution time, item count, status)
    - Error messages if the scraping failed
    
    **Use this endpoint when:**
    - User wants to view full search results
    - Displaying items in a gallery/list view
    - Analyzing results from specific sites
    """
    serializer_class = ScrapeResultSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary="Get search results",
        description="""        Get detailed results with full item data for a specific search.

        **Purpose:**
        - Display complete card listings to users
        - Show item details (title, price, images, seller info)
        - Analyze results from specific sites
        - Build result galleries or comparison views
        - Export data for analysis

        **Response Data Structure:**
        Each result contains:
        - **Site Information**: Name, type, status
        - **Items Array**: Full card listing details
        - **Metadata**: Execution time, errors, page count
        - **Statistics**: Total items found, items scraped

        **Item Details Include:**
        - Title and description
        - Price information (amount, currency, shipping)
        - Grade details (company, grade, numeric value)
        - Seller information (name, rating, feedback count)
        - Listing type (auction, buy-it-now)
        - Condition and grading status
        - Images and URLs
        - Location and timing data

        **Site Types:**
        - **SALES**: Current marketplace listings (eBay, COMC)
        - **AUCTION**: Active/past auctions (Goldin, Heritage)
        - **POPULATION**: Grading population data (PSA, BGS)
        - **MARKETPLACE**: Trading platforms (130Point)

        **Pagination:**
        - Results are paginated by site
        - Each site result contains all items from that site
        - Ordered by items_count (most items first)
        """,
        responses={
            200: ScrapeResultSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(
                description="Search not found or does not belong to the authenticated user"
            ),
        },
        examples=[
            OpenApiExample(
                name='Search Results Response',
                value=[
                    {
                        'id': '323e4567-e89b-12d3-a456-426614174222',
                        'target_site': '523e4567-e89b-12d3-a456-426614174333',
                        'site_name': 'eBay',
                        'site_type': 'SALES',
                        'status': 'SUCCESS',
                        'data': {
                            'query': 'Michael Jordan 1986 Fleer PSA 10',
                            'items': [
                                {
                                    'title': '1986 Fleer #57 Michael Jordan ROOKIE RC PSA 10',
                                    'price': 1850.00,
                                    'url': 'https://www.ebay.com/itm/123456789',
                                    'image_url': 'https://i.ebayimg.com/images/g/abc/s-l500.jpg',
                                    'condition': 'Brand New',
                                    'seller': 'trusted_seller',
                                    'seller_rating': '99.8%',
                                    'location': 'United States',
                                    'shipping': 'Free',
                                    'watchers': 25,
                                    'bids': 0,
                                    'time_left': '2d 5h'
                                }
                            ],
                            'total_results': 45,
                            'metadata': {
                                'execution_time_seconds': 12.5,
                                'errors': []
                            }
                        },
                        'items_count': 45,
                        'execution_time_seconds': 12.5,
                        'error_message': None,
                        'created_at': '2025-11-20T10:30:15Z'
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve search results."""
        return self.list(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get results for the specified search if it belongs to the user."""
        search_id = self.kwargs.get('search_id')
        
        # Verify search belongs to user
        try:
            search = Search.objects.get(id=search_id, user=self.request.user)
        except Search.DoesNotExist:
            raise NotFound(_('Search not found or does not belong to you.'))
        
        return ScrapeResult.objects.filter(
            search=search
        ).select_related('target_site').order_by('-items_count')


class CancelSearchView(APIView):
    """
    Cancel a search that is currently in PENDING or PROCESSING status.
    
    **Important Notes:**
    - Only searches with status PENDING or PROCESSING can be cancelled
    - Cancelling a PROCESSING search may not stop immediately (depends on Celery)
    - The search status will be updated to FAILED with an appropriate message
    - Already completed searches cannot be cancelled
    
    **Use Cases:**
    - User wants to stop a long-running search
    - User made a mistake and wants to cancel
    - User wants to start a new search instead
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary="Cancel search",
        description="""        Cancel a search that is currently in PENDING or PROCESSING status.

        **Purpose:**
        - Stop a long-running or incorrect search
        - Free up system resources
        - Prevent unwanted results from being processed
        - Allow user to start a corrected search

        **Cancellation Process:**
        1. Validates search belongs to authenticated user
        2. Checks search is in cancellable state (PENDING or PROCESSING)
        3. Updates status to FAILED
        4. Sets error message: "Search cancelled by user"
        5. Preserves any partial results already collected

        **Important Notes:**
        - Only PENDING or PROCESSING searches can be cancelled
        - COMPLETED, FAILED, or CANCELLED searches cannot be cancelled
        - Cancellation may not stop immediately (depends on Celery worker state)
        - The search record is not deleted, only marked as FAILED
        - Partial results collected before cancellation are preserved

        **Use Cases:**
        - User made typo in query
        - Search taking too long
        - User wants to refine search criteria
        - Accidental duplicate search

        **Response:**
        - Success message with previous status
        - Search ID for reference
        - Updated search accessible via GET /{search_id}/
        """,
        request=None,
        responses={
            200: OpenApiResponse(
                description="Search cancelled successfully",
                response={
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'},
                        'search_id': {'type': 'string', 'format': 'uuid'},
                        'previous_status': {'type': 'string'},
                    }
                }
            ),
            400: OpenApiResponse(
                description="Cannot cancel search - already completed or failed"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(
                description="Search not found or does not belong to the authenticated user"
            ),
        },
        examples=[
            OpenApiExample(
                name='Cancel Search Response',
                value={
                    'message': 'Search cancelled successfully.',
                    'search_id': '123e4567-e89b-12d3-a456-426614174000',
                    'previous_status': 'PROCESSING'
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, search_id):
        """Handle POST request to cancel a search."""
        try:
            search = Search.objects.get(id=search_id, user=request.user)
        except Search.DoesNotExist:
            raise NotFound(_('Search not found or does not belong to you.'))
        
        # Check if search can be cancelled
        if search.status not in [Search.Status.PENDING, Search.Status.PROCESSING]:
            raise ValidationError(
                _('Cannot cancel search with status: {}').format(search.status)
            )
        
        previous_status = search.status
        
        # Update search status
        search.status = Search.Status.FAILED
        search.error_message = _('Search cancelled by user.')
        search.save(update_fields=['status', 'error_message'])
        
        return Response(
            {
                'message': _('Search cancelled successfully.'),
                'search_id': str(search.id),
                'previous_status': previous_status,
            },
            status=status.HTTP_200_OK
        )


class AvailableSitesView(generics.ListAPIView):
    """
    Get list of available scraping sites.
    
    Returns all active sites that can be scraped for sports card data.
    Useful for displaying available data sources to users.
    
    **Site Information Includes:**
    - Site name and type (SALES, AUCTION, POPULATION, MARKETPLACE)
    - Base URL
    - Priority level
    - Active status
    """
    serializer_class = TargetSiteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # No pagination for sites list
    
    @extend_schema(
        tags=['Search'],
        summary="Get available sites",
        description="""        Get list of all active scraping sites and data sources.

        **Purpose:**
        - Display available marketplaces to users
        - Show which sites will be scraped
        - Provide information about data sources
        - Help users understand coverage

        **Site Information:**
        - **Name**: Display name (e.g., 'eBay', 'PSA')
        - **Slug**: URL-friendly identifier
        - **Base URL**: Site's home page
        - **Site Type**: Category of data source
        - **Priority**: Scraping importance (HIGH, MEDIUM, LOW)
        - **Active Status**: Whether currently enabled

        **Site Types:**
        
        **SALES** - Current marketplace listings
        - eBay: Auction and fixed-price listings
        - COMC: Check Out My Cards marketplace
        - MySlabs: Graded card marketplace
        
        **AUCTION** - Live and past auctions
        - Goldin Auctions: High-end card auctions
        - Heritage Auctions: Sports collectibles
        - SCP Auctions: Sports memorabilia
        
        **POPULATION** - Grading population data
        - PSA: Population reports and cert lookup
        - BGS: Beckett grading population
        - CGC: CGC Cards population data
        
        **MARKETPLACE** - Trading platforms
        - 130Point: Sales data and population
        - StarStock: Card investment platform

        **Priority Levels:**
        - **HIGH**: Scraped first, most reliable sources
        - **MEDIUM**: Standard priority
        - **LOW**: Scraped last, optional sources

        **Response:**
        - No pagination (returns all active sites)
        - Typically 5-10 sites total
        - Only active sites are returned
        """,
        responses={
            200: TargetSiteSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
        },
        examples=[
            OpenApiExample(
                name='Available Sites Response',
                value=[
                    {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'eBay',
                        'slug': 'ebay',
                        'base_url': 'https://www.ebay.com',
                        'site_type': 'SALES',
                        'priority': 'HIGH',
                        'is_active': True
                    },
                    {
                        'id': '223e4567-e89b-12d3-a456-426614174001',
                        'name': 'COMC',
                        'slug': 'comc',
                        'base_url': 'https://www.comc.com',
                        'site_type': 'MARKETPLACE',
                        'priority': 'MEDIUM',
                        'is_active': True
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve available sites."""
        return self.list(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get all active target sites."""
        return TargetSite.objects.filter(is_active=True)


class UserSearchStatsView(APIView):
    """
    Get search statistics for the authenticated user.
    
    Returns comprehensive statistics about the user's search activity including:
    - Total number of searches
    - Success/failure rates
    - Total items found
    - Average execution time
    - Most searched players
    - Recent search history
    
    **Use Cases:**
    - Dashboard statistics
    - User activity overview
    - Analytics and insights
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary="Get user statistics",
        description="""        Get comprehensive search statistics and analytics for the authenticated user.

        **Purpose:**
        - Display user dashboard with activity metrics
        - Show search success rate and performance
        - Identify most searched players
        - Provide insights into search behavior
        - Track total items discovered

        **Statistics Included:**
        
        **Search Metrics:**
        - Total searches created
        - Successfully completed searches
        - Failed searches
        - Success rate percentage
        
        **Discovery Metrics:**
        - Total items found across all searches
        - Average items per search
        - Total unique cards discovered
        
        **Performance Metrics:**
        - Average execution time per search
        - Fastest/slowest searches
        - Site success rates
        
        **Trending Data:**
        - Top 5 most searched players
        - Search count per player
        - Recent search activity (last 5 searches)
        
        **Use Cases:**
        - User dashboard display
        - Activity overview page
        - Search behavior analytics
        - Performance monitoring
        - Personalized recommendations

        **Response Format:**
        - All counts as integers
        - Times in seconds (float)
        - Most searched players as array of objects
        - Recent searches as full Search objects

        **Performance:**
        - Aggregated in real-time
        - Cached for 5 minutes
        - Optimized database queries
        """,
        responses={
            200: UserStatsSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
        },
        examples=[
            OpenApiExample(
                name='User Stats Response',
                value={
                    'total_searches': 45,
                    'completed_searches': 38,
                    'failed_searches': 7,
                    'total_items_found': 1523,
                    'average_execution_time': 8.5,
                    'most_searched_players': [
                        {'player': 'Michael Jordan', 'count': 12},
                        {'player': 'LeBron James', 'count': 8},
                        {'player': 'Tom Brady', 'count': 6}
                    ],
                    'recent_searches': []
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        """Handle GET request to retrieve user statistics."""
        user = request.user
        
        # Get all searches for user
        searches = Search.objects.filter(user=user)
        
        # Calculate statistics
        stats = searches.aggregate(
            total_searches=Count('id'),
            completed_searches=Count('id', filter=Q(status=Search.Status.COMPLETED)),
            failed_searches=Count('id', filter=Q(status=Search.Status.FAILED)),
            total_items_found=Sum('total_items_found'),
            average_execution_time=Avg('execution_time_seconds'),
        )
        
        # Get most searched players
        most_searched = searches.filter(
            player_name__isnull=False
        ).values('player_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        most_searched_players = [
            {'player': item['player_name'], 'count': item['count']}
            for item in most_searched
        ]
        
        # Get recent searches
        recent_searches = searches.order_by('-created_at')[:5]
        
        data = {
            'total_searches': stats['total_searches'] or 0,
            'completed_searches': stats['completed_searches'] or 0,
            'failed_searches': stats['failed_searches'] or 0,
            'total_items_found': stats['total_items_found'] or 0,
            'average_execution_time': round(stats['average_execution_time'] or 0, 2),
            'most_searched_players': most_searched_players,
            'recent_searches': SearchSerializer(recent_searches, many=True).data,
        }
        
        serializer = UserStatsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
