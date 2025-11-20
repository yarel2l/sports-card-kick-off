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
        description="Create a new sports card search and initiate scraping across configured sites.",
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
        description="Get the authenticated user's search history ordered by most recent.",
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
        description="Get detailed information about a specific search including all results.",
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
        description="Get detailed results from all sites for a specific search.",
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
        description="Cancel a search that is currently pending or in progress.",
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
        description="Get list of all active sites available for scraping.",
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
        description="Get comprehensive search statistics for the authenticated user.",
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
