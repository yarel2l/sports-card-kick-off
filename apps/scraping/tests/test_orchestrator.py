"""
Tests for the source-agnostic, multi-agent ScraperOrchestrator.

Uses lightweight fake agents so the orchestration logic (parallel execution,
aggregation, per-agent failure isolation, registry discovery) is verified
without real network scraping.
"""

import asyncio
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.scraping.agents import registry
from apps.scraping.orchestrators import ScraperOrchestrator


class _FakeResult:
    def __init__(self, n_items):
        self.success = True
        self.items = list(range(n_items))
        self.metadata = SimpleNamespace(execution_time_seconds=0.1, errors=[])


class FakeAgentA:
    def __init__(self, use_llm=True):
        self.use_llm = use_llm

    async def scrape(self, query, **kwargs):
        return _FakeResult(2)


class FakeAgentB:
    def __init__(self, use_llm=True):
        self.use_llm = use_llm

    async def scrape(self, query, **kwargs):
        return _FakeResult(3)


class FailingAgent:
    def __init__(self, use_llm=True):
        pass

    async def scrape(self, query, **kwargs):
        raise RuntimeError('boom')


class MultiAgentOrchestratorTests(SimpleTestCase):
    def test_runs_all_agents_and_aggregates(self):
        orch = ScraperOrchestrator(
            use_llm=False, agents={'a': FakeAgentA, 'b': FakeAgentB}
        )
        result = asyncio.run(orch.orchestrate('luka doncic'))

        self.assertTrue(result['success'])
        self.assertEqual(set(result['results'].keys()), {'a', 'b'})
        self.assertEqual(result['metrics']['successful_agents'], 2)
        self.assertEqual(result['metrics']['total_items'], 5)

    def test_failure_is_isolated_per_agent(self):
        orch = ScraperOrchestrator(
            use_llm=False, agents={'a': FakeAgentA, 'bad': FailingAgent}
        )
        result = asyncio.run(orch.orchestrate('query'))

        self.assertIn('a', result['results'])
        self.assertIn('bad', result['errors'])
        self.assertEqual(result['metrics']['successful_agents'], 1)
        self.assertEqual(result['metrics']['failed_agents'], 1)

    def test_can_select_subset_of_agents(self):
        orch = ScraperOrchestrator(
            use_llm=False, agents={'a': FakeAgentA, 'b': FakeAgentB}
        )
        result = asyncio.run(orch.orchestrate('query', agents=['a']))
        self.assertEqual(set(result['results'].keys()), {'a'})

    def test_unknown_agent_yields_no_results(self):
        orch = ScraperOrchestrator(use_llm=False, agents={'a': FakeAgentA})
        result = asyncio.run(orch.orchestrate('query', agents=['does_not_exist']))
        self.assertFalse(result['success'])

    def test_orchestrator_discovers_registry_agents(self):
        registry.register_agent('tmp_fake', FakeAgentA)
        try:
            orch = ScraperOrchestrator(use_llm=False)
            self.assertIn('tmp_fake', orch.available_agents)
            # eBay remains registered as the built-in default.
            self.assertIn('ebay', orch.available_agents)
        finally:
            registry.unregister_agent('tmp_fake')

    def test_default_agents_run_when_none_specified(self):
        orch = ScraperOrchestrator(
            use_llm=False, agents={'a': FakeAgentA, 'b': FakeAgentB}
        )
        result = asyncio.run(orch.orchestrate('query', agents=None))
        self.assertEqual(set(result['results'].keys()), {'a', 'b'})
