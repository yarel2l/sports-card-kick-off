"""
Celery tasks for search app.

These tasks handle asynchronous scraping operations initiated by search requests.
"""

import asyncio
import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_search_task(self, search_id: str) -> Dict[str, Any]:
    """
    Execute scraping for a search across configured sites.
    
    This task:
    1. Updates search status to PROCESSING
    2. Invokes the scraping orchestrator with the search query
    3. Saves results from each site to ScrapeResult records
    4. Updates search status to COMPLETED, FAILED, or PARTIAL based on results
    
    Args:
        search_id: UUID of the search to process
    
    Returns:
        Dictionary with task execution summary
        
    Raises:
        Exception: Re-raised after updating search status to FAILED
    """
    from apps.search.models import Search, ScrapeResult, TargetSite, SearchHistory
    from apps.scraping.orchestrators import ScraperOrchestrator
    
    try:
        # Fetch search object
        try:
            search = Search.objects.select_related('user').get(id=search_id)
        except Search.DoesNotExist:
            logger.error(f"Search with id {search_id} not found")
            return {
                'success': False,
                'error': 'Search not found',
                'search_id': search_id
            }
        
        # Update status to PROCESSING
        search.status = Search.Status.PROCESSING
        search.save(update_fields=['status'])
        
        logger.info(f"Starting scraping task for search {search_id}: '{search.query}'")
        
        # Create orchestrator and execute scraping
        # We need to run async code in sync context
        orchestrator = ScraperOrchestrator(use_llm=False)  # Using traditional parsing for stability
        
        # Run async orchestrator in sync context
        result = asyncio.run(
            orchestrator.orchestrate(
                query=search.query,
                agents=['ebay']  # Currently only eBay is implemented
            )
        )
        
        logger.info(f"Scraping completed for search {search_id}. Success: {result['success']}")
        
        # Process and save results
        successful_sites = 0
        failed_sites = 0
        total_items = 0
        
        if result['success'] and result['results']:
            for agent_name, agent_result in result['results'].items():
                try:
                    # Get or create target site
                    target_site, _ = TargetSite.objects.get_or_create(
                        slug=agent_name,
                        defaults={
                            'name': agent_name.capitalize(),
                            'base_url': f'https://www.{agent_name}.com',
                            'site_type': TargetSite.SiteType.SALES,
                            'priority': TargetSite.Priority.HIGH,
                            'is_active': True,
                        }
                    )
                    
                    # Determine result status
                    result_status = (
                        ScrapeResult.Status.SUCCESS
                        if agent_result.success
                        else ScrapeResult.Status.FAILED
                    )
                    
                    # Prepare data for storage
                    result_data = {
                        'query': search.query,
                        'items': [
                            item.model_dump(mode='json')
                            for item in agent_result.items
                        ],
                        'total_results': agent_result.total_results if hasattr(agent_result, 'total_results') else len(agent_result.items),
                        'metadata': agent_result.metadata.model_dump(mode='json'),
                    }
                    
                    # Create or update scrape result
                    scrape_result, created = ScrapeResult.objects.update_or_create(
                        search=search,
                        target_site=target_site,
                        defaults={
                            'status': result_status,
                            'data': result_data,
                            'items_count': len(agent_result.items),
                            'execution_time_seconds': agent_result.metadata.execution_time_seconds,
                            'error_message': (
                                agent_result.metadata.errors[0]
                                if agent_result.metadata.errors
                                else None
                            ),
                        }
                    )

                    # Resolve each listing into the canonical catalog and record
                    # price observations. Best-effort: never let catalog ingestion
                    # break the search flow.
                    try:
                        from apps.catalog.services.ingest import ingest_items
                        observations = ingest_items(
                            result_data['items'], source=agent_name
                        )
                        logger.info(
                            f"Catalog: ingested {len(observations)} price "
                            f"observations from {agent_name}"
                        )
                    except Exception as ingest_error:
                        logger.error(
                            f"Catalog ingestion failed for {agent_name}: {ingest_error}",
                            exc_info=True,
                        )
                    
                    if result_status == ScrapeResult.Status.SUCCESS:
                        successful_sites += 1
                        total_items += len(agent_result.items)
                    else:
                        failed_sites += 1
                    
                    logger.info(
                        f"Saved {'new' if created else 'updated'} result for {agent_name}: "
                        f"{len(agent_result.items)} items"
                    )
                    
                except Exception as e:
                    logger.error(f"Error saving result for {agent_name}: {e}", exc_info=True)
                    failed_sites += 1
        
        # Handle errors from orchestrator
        if result.get('errors'):
            for agent_name, error_msg in result['errors'].items():
                try:
                    target_site, _ = TargetSite.objects.get_or_create(
                        slug=agent_name,
                        defaults={
                            'name': agent_name.capitalize(),
                            'base_url': f'https://www.{agent_name}.com',
                            'site_type': TargetSite.SiteType.SALES,
                            'is_active': True,
                        }
                    )
                    
                    ScrapeResult.objects.update_or_create(
                        search=search,
                        target_site=target_site,
                        defaults={
                            'status': ScrapeResult.Status.FAILED,
                            'data': {},
                            'items_count': 0,
                            'execution_time_seconds': 0,
                            'error_message': str(error_msg),
                        }
                    )
                    failed_sites += 1
                    
                except Exception as e:
                    logger.error(f"Error saving error result for {agent_name}: {e}")
        
        # Determine final search status
        if successful_sites > 0 and failed_sites == 0:
            final_status = Search.Status.COMPLETED
        elif successful_sites > 0 and failed_sites > 0:
            final_status = Search.Status.PARTIAL
        elif failed_sites > 0 and successful_sites == 0:
            final_status = Search.Status.FAILED
        else:
            # No results at all
            final_status = Search.Status.FAILED
        
        # Calculate total execution time from metrics if available
        execution_time = result.get('metrics', {}).get('execution_time_seconds', 0)
        
        # Update search with final status and metrics
        search.status = final_status
        search.total_sites = successful_sites + failed_sites
        search.successful_sites = successful_sites
        search.failed_sites = failed_sites
        search.total_items_found = total_items
        search.execution_time_seconds = execution_time
        search.completed_at = timezone.now()
        search.save(update_fields=[
            'status', 'total_sites', 'successful_sites', 'failed_sites',
            'total_items_found', 'execution_time_seconds', 'completed_at'
        ])
        
        # Create search history entry
        SearchHistory.objects.create(
            user=search.user,
            search=search,
            query=search.query,
            was_successful=(final_status == Search.Status.COMPLETED),
            total_results=total_items,
        )
        
        logger.info(
            f"Search {search_id} completed with status {final_status}. "
            f"Successful: {successful_sites}, Failed: {failed_sites}, Total items: {total_items}"
        )
        
        return {
            'success': True,
            'search_id': search_id,
            'status': final_status,
            'successful_sites': successful_sites,
            'failed_sites': failed_sites,
            'total_items': total_items,
        }
        
    except Exception as e:
        logger.error(f"Error executing search task for {search_id}: {e}", exc_info=True)
        
        # Update search status to failed
        try:
            search = Search.objects.get(id=search_id)
            search.status = Search.Status.FAILED
            search.completed_at = timezone.now()
            search.save(update_fields=['status', 'completed_at'])
        except Exception as update_error:
            logger.error(f"Failed to update search status: {update_error}")
        
        # Retry task if possible
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for search {search_id}")
            return {
                'success': False,
                'error': str(e),
                'search_id': search_id
            }
