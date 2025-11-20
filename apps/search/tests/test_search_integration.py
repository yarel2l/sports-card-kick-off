"""
Integration tests for Search functionality.
Tests the complete flow from search creation to result retrieval.
"""

from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.search.models import Search, ScrapeResult, TargetSite, SearchHistory
from apps.search.tasks import execute_search_task

User = get_user_model()


class SearchFlowIntegrationTests(TestCase):
    """Test complete search workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        # Create target site
        self.ebay = TargetSite.objects.create(
            name='eBay',
            slug='ebay',
            base_url='https://www.ebay.com',
            site_type=TargetSite.SiteType.SALES,
            priority=TargetSite.Priority.HIGH,
            is_active=True,
            agent_class_name='EbayAgent',
        )

    @patch('apps.scraping.orchestrators.ScraperOrchestrator')
    def test_successful_search_flow(self, mock_orchestrator_class):
        """Test complete successful search flow."""
        query = 'Michael Jordan 1986 Fleer PSA 10'
        
        # Mock orchestrator to return successful result
        mock_orchestrator = mock_orchestrator_class.return_value
        
        async def mock_orchestrate(*args, **kwargs):
            return {
                'success': True,
                'results': {
                    'ebay': MagicMock(
                        success=True,
                        items=[MagicMock(
                            model_dump=MagicMock(return_value={
                                'title': '1986 Fleer #57 Michael Jordan PSA 10',
                                'price': 1850.00,
                                'url': 'https://www.ebay.com/itm/123456789'
                            })
                        )],
                        total_results=10,
                        metadata=MagicMock(
                            execution_time_seconds=10.5,
                            errors=[],
                            model_dump=MagicMock(return_value={
                                'execution_time_seconds': 10.5,
                                'errors': []
                            })
                        )
                    )
                },
                'errors': {},
                'metrics': {
                    'successful_agents': 1,
                    'failed_agents': 0,
                    'total_items': 10,
                    'execution_time_seconds': 10.5
                }
            }
        
        mock_orchestrator.orchestrate = mock_orchestrate
        
        # Create search
        search = Search.objects.create(
            user=self.user,
            query=query,
            status=Search.Status.PENDING
        )
        
        # Execute task
        result = execute_search_task(str(search.id))
        
        # Verify task result
        self.assertTrue(result['success'])
        self.assertEqual(result['successful_sites'], 1)
        self.assertEqual(result['failed_sites'], 0)
        # total_items is len(items), not total_results
        self.assertEqual(result['total_items'], 1)
        
        # Verify search was updated
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.COMPLETED)
        self.assertEqual(search.total_items_found, 1)  # Based on items.length
        self.assertEqual(search.successful_sites, 1)
        self.assertEqual(search.failed_sites, 0)
        self.assertIsNotNone(search.completed_at)
        
        # Verify scrape result was created
        scrape_results = ScrapeResult.objects.filter(search=search)
        self.assertEqual(scrape_results.count(), 1)
        
        scrape_result = scrape_results.first()
        self.assertEqual(scrape_result.status, ScrapeResult.Status.SUCCESS)
        self.assertEqual(scrape_result.items_count, 1)
        self.assertEqual(scrape_result.target_site, self.ebay)
        
        # Verify search history was created
        history = SearchHistory.objects.filter(user=self.user, search=search)
        self.assertEqual(history.count(), 1)
        self.assertTrue(history.first().was_successful)
        self.assertEqual(history.first().total_results, 1)  # Based on actual items found

    @patch('apps.scraping.orchestrators.ScraperOrchestrator')
    def test_partial_search_flow(self, mock_orchestrator_class):
        """Test search with partial success (some sites fail)."""
        # Create second site
        comc = TargetSite.objects.create(
            name='COMC',
            slug='comc',
            base_url='https://www.comc.com',
            site_type=TargetSite.SiteType.MARKETPLACE,
            is_active=True,
            agent_class_name='ComcAgent',
        )
        
        query = 'LeBron James Rookie'
        
        # Mock orchestrator to return partial success
        mock_orchestrator = mock_orchestrator_class.return_value
        
        async def mock_orchestrate(*args, **kwargs):
            return {
                'success': True,
                'results': {
                    'ebay': MagicMock(
                        success=True,
                        items=[MagicMock(
                            model_dump=MagicMock(return_value={'title': 'Card', 'price': 100.00})
                        )],
                        total_results=5,
                        metadata=MagicMock(
                            execution_time_seconds=5.0,
                            errors=[],
                            model_dump=MagicMock(return_value={'execution_time_seconds': 5.0, 'errors': []})
                        )
                    )
                },
                'errors': {
                    'comc': 'Connection timeout'
                },
                'metrics': {
                    'successful_agents': 1,
                    'failed_agents': 1,
                    'total_items': 5,
                    'execution_time_seconds': 5.0
                }
            }
        
        mock_orchestrator.orchestrate = mock_orchestrate
        
        # Create search
        search = Search.objects.create(
            user=self.user,
            query=query,
            status=Search.Status.PENDING
        )
        
        # Execute task
        result = execute_search_task(str(search.id))
        
        # Verify partial success
        self.assertTrue(result['success'])
        self.assertEqual(result['successful_sites'], 1)
        self.assertEqual(result['failed_sites'], 1)
        
        # Verify search status is PARTIAL
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.PARTIAL)
        self.assertEqual(search.successful_sites, 1)
        self.assertEqual(search.failed_sites, 1)
        
        # Verify both results were created
        self.assertEqual(ScrapeResult.objects.filter(search=search).count(), 2)
        
        # Verify one success and one failure
        success_results = ScrapeResult.objects.filter(
            search=search,
            status=ScrapeResult.Status.SUCCESS
        )
        failed_results = ScrapeResult.objects.filter(
            search=search,
            status=ScrapeResult.Status.FAILED
        )
        self.assertEqual(success_results.count(), 1)
        self.assertEqual(failed_results.count(), 1)

    @patch('apps.scraping.orchestrators.ScraperOrchestrator')
    def test_failed_search_flow(self, mock_orchestrator_class):
        """Test complete search failure."""
        query = 'Invalid Query'
        
        # Mock orchestrator to return failure
        mock_orchestrator = mock_orchestrator_class.return_value
        
        async def mock_orchestrate(*args, **kwargs):
            return {
                'success': False,
                'results': {},
                'errors': {
                    'ebay': 'Failed to connect to eBay'
                },
                'metrics': {
                    'successful_agents': 0,
                    'failed_agents': 1,
                    'total_items': 0,
                    'execution_time_seconds': 2.0
                }
            }
        
        mock_orchestrator.orchestrate = mock_orchestrate
        
        # Create search
        search = Search.objects.create(
            user=self.user,
            query=query,
            status=Search.Status.PENDING
        )
        
        # Execute task
        result = execute_search_task(str(search.id))
        
        # Verify failure
        self.assertTrue(result['success'])  # Task executed successfully
        self.assertEqual(result['successful_sites'], 0)
        self.assertEqual(result['failed_sites'], 1)
        
        # Verify search status is FAILED
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.FAILED)
        self.assertEqual(search.successful_sites, 0)
        self.assertEqual(search.failed_sites, 1)
        
        # Verify history entry
        history = SearchHistory.objects.filter(user=self.user, search=search)
        self.assertEqual(history.count(), 1)
        self.assertFalse(history.first().was_successful)

    def test_search_not_found(self):
        """Test task with non-existent search ID."""
        result = execute_search_task('00000000-0000-0000-0000-000000000000')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Search not found')


class SearchTaskRetryTests(TestCase):
    """Test Celery task retry behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    @patch('apps.scraping.orchestrators.ScraperOrchestrator')
    def test_task_exception_handling(self, mock_orchestrator_class):
        """Test that task handles exceptions properly."""
        # Mock orchestrator to raise exception
        mock_orchestrator = mock_orchestrator_class.return_value
        
        # Create an async mock that raises an exception
        async def mock_orchestrate(*args, **kwargs):
            raise Exception('Unexpected error')
        
        mock_orchestrator.orchestrate = mock_orchestrate
        
        # Create search
        search = Search.objects.create(
            user=self.user,
            query='Test Query',
            status=Search.Status.PENDING
        )
        
        # Execute task - should not crash
        with patch('apps.search.tasks.execute_search_task.retry') as mock_retry:
            mock_retry.side_effect = Exception('Max retries exceeded')
            
            try:
                execute_search_task(str(search.id))
            except Exception:
                pass
        
        # Verify search was marked as failed
        search.refresh_from_db()
        self.assertEqual(search.status, Search.Status.FAILED)
