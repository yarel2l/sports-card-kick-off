"""
Tests for Search API endpoints.
"""

from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.search.models import Search, ScrapeResult, TargetSite, SearchHistory

User = get_user_model()


def create_user(**params):
    """Helper function to create test user."""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'testpass123'
    }
    defaults.update(params)
    return User.objects.create_user(**defaults)


def create_target_site(**params):
    """Helper function to create test target site."""
    defaults = {
        'name': 'eBay',
        'slug': 'ebay',
        'base_url': 'https://www.ebay.com',
        'site_type': TargetSite.SiteType.SALES,
        'priority': TargetSite.Priority.HIGH,
        'is_active': True,
        'agent_class_name': 'EbayAgent',
    }
    defaults.update(params)
    return TargetSite.objects.create(**defaults)


class PublicSearchAPITests(APITestCase):
    """Test unauthenticated API access."""

    def test_auth_required_create_search(self):
        """Test authentication is required for creating searches."""
        url = reverse('search:create_search')
        response = self.client.post(url, {'query': 'Test Query'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_auth_required_search_history(self):
        """Test authentication is required for search history."""
        url = reverse('search:search_history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_auth_required_search_detail(self):
        """Test authentication is required for search details."""
        url = reverse('search:search_detail', kwargs={'search_id': '123e4567-e89b-12d3-a456-426614174000'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CreateSearchAPITests(APITestCase):
    """Test search creation endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('search:create_search')

    @patch('apps.search.views.search.execute_search_task')
    def test_create_search_success(self, mock_task):
        """Test successful search creation."""
        mock_task.delay.return_value = MagicMock()
        
        payload = {'query': 'Michael Jordan 1986 Fleer PSA 10'}
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['query'], payload['query'])
        self.assertEqual(response.data['status'], Search.Status.PENDING)
        self.assertIn('id', response.data)
        
        # Verify search was created
        self.assertTrue(
            Search.objects.filter(
                user=self.user,
                query=payload['query']
            ).exists()
        )
        
        # Verify task was triggered
        mock_task.delay.assert_called_once()

    def test_create_search_empty_query_fails(self):
        """Test creating search with empty query fails."""
        payload = {'query': ''}
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Error can be in 'query' key or in 'errors' array
        self.assertTrue(
            'query' in response.data or 
            ('errors' in response.data and any(err['attr'] == 'query' for err in response.data['errors']))
        )

    def test_create_search_short_query_fails(self):
        """Test creating search with too short query fails."""
        payload = {'query': 'ab'}
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Error can be in 'query' key or in 'errors' array
        self.assertTrue(
            'query' in response.data or 
            ('errors' in response.data and any(err['attr'] == 'query' for err in response.data['errors']))
        )


class SearchHistoryAPITests(APITestCase):
    """Test search history endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('search:search_history')

    def test_get_empty_history(self):
        """Test retrieving empty search history."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRF pagination returns results in 'results' key
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 0)

    def test_get_user_history(self):
        """Test retrieving user's search history."""
        # Create searches
        search1 = Search.objects.create(
            user=self.user,
            query='Michael Jordan',
            status=Search.Status.COMPLETED
        )
        search2 = Search.objects.create(
            user=self.user,
            query='LeBron James',
            status=Search.Status.COMPLETED
        )
        
        # Create history entries
        SearchHistory.objects.create(
            user=self.user,
            search=search1,
            query='Michael Jordan',
            was_successful=True,
            total_results=45
        )
        SearchHistory.objects.create(
            user=self.user,
            search=search2,
            query='LeBron James',
            was_successful=True,
            total_results=78
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 2)

    def test_history_isolation_between_users(self):
        """Test users only see their own history."""
        other_user = create_user(email='other@example.com', username='otheruser')
        
        # Create history for current user
        search1 = Search.objects.create(user=self.user, query='Query 1')
        SearchHistory.objects.create(
            user=self.user,
            search=search1,
            query='Query 1',
            was_successful=True,
            total_results=10
        )
        
        # Create history for other user
        search2 = Search.objects.create(user=other_user, query='Query 2')
        SearchHistory.objects.create(
            user=other_user,
            search=search2,
            query='Query 2',
            was_successful=True,
            total_results=20
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        # Should only see own history (1 item)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['query'], 'Query 1')


class SearchDetailAPITests(APITestCase):
    """Test search detail endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.target_site = create_target_site()

    def test_get_search_detail(self):
        """Test retrieving search details."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.COMPLETED,
            total_items_found=45,
            successful_sites=1
        )
        
        url = reverse('search:search_detail', kwargs={'search_id': search.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(search.id))
        self.assertEqual(response.data['query'], 'Test Query')
        self.assertEqual(response.data['status'], Search.Status.COMPLETED)

    def test_get_search_detail_with_results(self):
        """Test retrieving search details with results."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.COMPLETED
        )
        ScrapeResult.objects.create(
            search=search,
            target_site=self.target_site,
            status=ScrapeResult.Status.SUCCESS,
            data={'items': []},
            items_count=10
        )
        
        url = reverse('search:search_detail', kwargs={'search_id': search.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_search_detail_other_user_fails(self):
        """Test retrieving another user's search fails."""
        other_user = create_user(email='other@example.com', username='otheruser')
        search = Search.objects.create(
            user=other_user,
            query='Other Query',
            status=Search.Status.COMPLETED
        )
        
        url = reverse('search:search_detail', kwargs={'search_id': search.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SearchResultsAPITests(APITestCase):
    """Test search results endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.target_site = create_target_site()

    def test_get_search_results(self):
        """Test retrieving search results."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.COMPLETED
        )
        ScrapeResult.objects.create(
            search=search,
            target_site=self.target_site,
            status=ScrapeResult.Status.SUCCESS,
            data={'items': [{'title': 'Card 1', 'price': 100.00}]},
            items_count=1
        )
        
        url = reverse('search:search_results', kwargs={'search_id': search.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['items_count'], 1)

    def test_get_search_results_other_user_fails(self):
        """Test retrieving another user's results fails."""
        other_user = create_user(email='other@example.com', username='otheruser')
        search = Search.objects.create(
            user=other_user,
            query='Other Query'
        )
        
        url = reverse('search:search_results', kwargs={'search_id': search.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CancelSearchAPITests(APITestCase):
    """Test cancel search endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def test_cancel_pending_search(self):
        """Test cancelling a pending search."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.PENDING
        )
        
        url = reverse('search:cancel_search', kwargs={'search_id': search.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify search was cancelled
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.CANCELLED)
        self.assertIsNotNone(search.error_message)

    def test_cancel_processing_search(self):
        """Test cancelling a processing search."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.PROCESSING
        )
        
        url = reverse('search:cancel_search', kwargs={'search_id': search.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.CANCELLED)

    def test_cancel_completed_search_fails(self):
        """Test cannot cancel completed search."""
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.COMPLETED
        )

        url = reverse('search:cancel_search', kwargs={'search_id': search.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_revokes_celery_task(self):
        """Cancelling a search with a task id revokes the Celery task."""
        search = Search.objects.create(
            user=self.user, query='Test Query',
            status=Search.Status.PROCESSING, celery_task_id='task-abc-123',
        )
        url = reverse('search:cancel_search', kwargs={'search_id': search.id})
        with patch('config.celery.app.control.revoke') as mock_revoke:
            response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_revoke.assert_called_once_with('task-abc-123', terminate=True)
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.CANCELLED)


class AvailableSitesAPITests(APITestCase):
    """Test available sites endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('search:available_sites')

    def test_get_available_sites(self):
        """Test retrieving available sites."""
        create_target_site()
        create_target_site(
            name='COMC',
            slug='comc',
            base_url='https://www.comc.com'
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_only_active_sites_returned(self):
        """Test only active sites are returned."""
        create_target_site(is_active=True)
        create_target_site(
            name='Inactive',
            slug='inactive',
            base_url='https://www.inactive.com',
            is_active=False
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'eBay')


class UserStatsAPITests(APITestCase):
    """Test user statistics endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('search:user_stats')

    def test_get_empty_stats(self):
        """Test retrieving stats with no searches."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_searches'], 0)
        self.assertEqual(response.data['completed_searches'], 0)
        self.assertEqual(response.data['total_items_found'], 0)

    def test_get_user_stats(self):
        """Test retrieving user statistics."""
        # Create completed search
        Search.objects.create(
            user=self.user,
            query='Michael Jordan',
            status=Search.Status.COMPLETED,
            player_name='Michael Jordan',
            total_items_found=45,
            execution_time_seconds=10.5
        )
        
        # Create failed search
        Search.objects.create(
            user=self.user,
            query='Unknown Player',
            status=Search.Status.FAILED
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_searches'], 2)
        self.assertEqual(response.data['completed_searches'], 1)
        self.assertEqual(response.data['failed_searches'], 1)
        self.assertEqual(response.data['total_items_found'], 45)

    def test_most_searched_players(self):
        """Test most searched players are returned."""
        for i in range(3):
            Search.objects.create(
                user=self.user,
                query=f'Michael Jordan {i}',
                player_name='Michael Jordan'
            )
        
        Search.objects.create(
            user=self.user,
            query='LeBron James',
            player_name='LeBron James'
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['most_searched_players']), 2)
        self.assertEqual(response.data['most_searched_players'][0]['player'], 'Michael Jordan')
        self.assertEqual(response.data['most_searched_players'][0]['count'], 3)
