"""
Scraper Orchestrator using LangGraph for multi-agent coordination.

This orchestrator manages multiple scraping agents in parallel,
aggregates results, and handles failures gracefully.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from ..agents import EbayAgent, BaseScraperAgent
from ..schemas import BaseScrapeResult, EbayScrapeResult

logger = logging.getLogger(__name__)


class ScraperState(TypedDict):
    """
    State schema for the scraper orchestrator.

    This defines the data structure that flows through the LangGraph workflow.
    """
    query: str
    agents_to_run: List[str]
    results: Dict[str, BaseScrapeResult]
    errors: Dict[str, str]
    status: str  # 'pending', 'running', 'completed', 'failed'
    start_time: Optional[datetime]
    end_time: Optional[datetime]


class ScraperOrchestrator:
    """
    Orchestrates multiple scraping agents using LangGraph.

    Uses LangGraph's StateGraph to coordinate parallel execution of
    multiple scraping agents and aggregate their results.
    """

    def __init__(self, use_llm: bool = True):
        """
        Initialize the orchestrator with available agents.

        Args:
            use_llm: If True, agents will use LLM extraction with traditional fallback.
                    If False, agents will use only traditional parsing.
        """
        self.use_llm = use_llm

        # Available agent classes (all unified now)
        self.available_agents = {
            'ebay': EbayAgent,
            # Add more agents here as they're implemented:
            # 'psa': PsaAgent,
            # '130point': Point130Agent,
        }

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow for orchestrating scrapers.

        Returns:
            Compiled StateGraph workflow
        """
        # Create the graph
        workflow = StateGraph(ScraperState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("scrape_ebay", self._scrape_ebay_node)
        workflow.add_node("aggregate_results", self._aggregate_results_node)

        # Set entry point
        workflow.set_entry_point("initialize")

        # Add conditional edges
        workflow.add_conditional_edges(
            "initialize",
            self._route_after_init,
            {
                "scrape": "scrape_ebay",
                "end": END,
            }
        )

        # Connect scrape node to aggregation
        workflow.add_edge("scrape_ebay", "aggregate_results")
        workflow.add_edge("aggregate_results", END)

        # Compile the graph
        return workflow.compile()

    def _initialize_node(self, state: ScraperState) -> ScraperState:
        """
        Initialize the scraping workflow.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info(f"Initializing scraper orchestrator for query: {state['query']}")

        return {
            **state,
            "status": "initialized",
            "start_time": datetime.utcnow(),
            "results": {},
            "errors": {},
        }

    def _route_after_init(self, state: ScraperState) -> str:
        """
        Route after initialization based on available agents.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute
        """
        if state.get('agents_to_run'):
            return "scrape"
        return "end"

    async def _scrape_ebay_node(self, state: ScraperState) -> ScraperState:
        """
        Execute eBay scraping.

        Args:
            state: Current workflow state

        Returns:
            Updated state with eBay results
        """
        if 'ebay' not in state.get('agents_to_run', []):
            return state

        logger.info("Executing eBay scraping agent")

        try:
            agent = EbayAgent(use_llm=self.use_llm)
            result = await agent.scrape(state['query'])

            return {
                **state,
                "results": {
                    **state.get('results', {}),
                    'ebay': result
                },
                "status": "scraping_completed",
            }

        except Exception as e:
            error_msg = f"eBay scraping failed: {str(e)}"
            logger.error(error_msg)

            return {
                **state,
                "errors": {
                    **state.get('errors', {}),
                    'ebay': error_msg
                },
                "status": "scraping_completed_with_errors",
            }

    def _aggregate_results_node(self, state: ScraperState) -> ScraperState:
        """
        Aggregate results from all agents.

        Args:
            state: Current workflow state

        Returns:
            Final state with aggregated results
        """
        logger.info("Aggregating results from all agents")

        results = state.get('results', {})
        errors = state.get('errors', {})

        # Calculate metrics
        total_items = sum(
            len(result.items) if hasattr(result, 'items') else 0
            for result in results.values()
        )

        successful_agents = len(results)
        failed_agents = len(errors)

        logger.info(
            f"Aggregation complete: {successful_agents} successful, "
            f"{failed_agents} failed, {total_items} total items"
        )

        return {
            **state,
            "status": "completed",
            "end_time": datetime.utcnow(),
        }

    async def orchestrate(
        self,
        query: str,
        agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate scraping across multiple agents.

        Args:
            query: Search query
            agents: List of agent names to run (defaults to all available)

        Returns:
            Dictionary with aggregated results
        """
        # Default to all available agents if not specified
        if agents is None:
            agents = list(self.available_agents.keys())

        # Filter to only available agents
        agents_to_run = [
            agent for agent in agents
            if agent in self.available_agents
        ]

        if not agents_to_run:
            logger.warning("No valid agents specified")
            return {
                'success': False,
                'error': 'No valid agents specified',
                'results': {},
            }

        # Create initial state
        initial_state: ScraperState = {
            'query': query,
            'agents_to_run': agents_to_run,
            'results': {},
            'errors': {},
            'status': 'pending',
            'start_time': None,
            'end_time': None,
        }

        try:
            # Execute the workflow
            logger.info(f"Starting orchestration for query: {query}")
            final_state = await self.workflow.ainvoke(initial_state)

            # Calculate execution time
            execution_time = None
            if final_state.get('start_time') and final_state.get('end_time'):
                execution_time = (
                    final_state['end_time'] - final_state['start_time']
                ).total_seconds()

            # Prepare response
            return {
                'success': True,
                'query': query,
                'results': final_state.get('results', {}),
                'errors': final_state.get('errors', {}),
                'metrics': {
                    'successful_agents': len(final_state.get('results', {})),
                    'failed_agents': len(final_state.get('errors', {})),
                    'total_items': sum(
                        len(result.items) if hasattr(result, 'items') else 0
                        for result in final_state.get('results', {}).values()
                    ),
                    'execution_time_seconds': execution_time,
                },
                'status': final_state.get('status'),
            }

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': {},
                'metrics': {
                    'successful_agents': 0,
                    'failed_agents': len(agents_to_run),
                    'total_items': 0,
                },
            }

    async def scrape_parallel(
        self,
        query: str,
        agents: Optional[List[str]] = None
    ) -> Dict[str, BaseScrapeResult]:
        """
        Execute multiple agents in parallel without LangGraph.

        This is a simpler alternative to the full orchestration for
        cases where you just need parallel execution.

        Args:
            query: Search query
            agents: List of agent names to run

        Returns:
            Dictionary mapping agent names to their results
        """
        if agents is None:
            agents = list(self.available_agents.keys())

        # Create agent instances
        agent_instances = []
        agent_names = []

        for agent_name in agents:
            if agent_name in self.available_agents:
                agent_class = self.available_agents[agent_name]
                agent_instances.append(agent_class())
                agent_names.append(agent_name)

        if not agent_instances:
            return {}

        # Execute all agents in parallel
        logger.info(f"Executing {len(agent_instances)} agents in parallel")

        tasks = [
            agent.scrape(query)
            for agent in agent_instances
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to agent names
        result_dict = {}
        for agent_name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} failed: {result}")
            else:
                result_dict[agent_name] = result

        return result_dict
