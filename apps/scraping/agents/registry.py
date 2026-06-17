"""
Agent registry for multi-source scraping.

Agents register themselves here by a short ``slug`` (e.g. "ebay", "130point").
The orchestrator discovers and runs whatever is registered, so adding a new
marketplace is a matter of writing an agent and registering it — no changes to
the orchestrator are required.
"""

from __future__ import annotations

from typing import Dict, List, Type

from .base_agent import BaseScraperAgent

_REGISTRY: Dict[str, Type[BaseScraperAgent]] = {}


def register_agent(slug: str, agent_cls: Type[BaseScraperAgent]) -> None:
    """Register (or replace) the agent class responsible for ``slug``."""
    _REGISTRY[slug] = agent_cls


def unregister_agent(slug: str) -> None:
    """Remove an agent from the registry (mainly for tests)."""
    _REGISTRY.pop(slug, None)


def get_agent(slug: str) -> Type[BaseScraperAgent]:
    return _REGISTRY[slug]


def available_agents() -> Dict[str, Type[BaseScraperAgent]]:
    """Return a copy of the current registry."""
    return dict(_REGISTRY)


def available_slugs() -> List[str]:
    return list(_REGISTRY.keys())


def _register_builtin_agents() -> None:
    # Imported lazily to avoid circular imports at module import time.
    from .ebay_agent import EbayAgent
    from .point130_agent import Point130Agent
    from .comc_agent import ComcAgent

    register_agent('ebay', EbayAgent)
    register_agent('130point', Point130Agent)
    register_agent('comc', ComcAgent)


_register_builtin_agents()
