"""
Catalog services.

NOTE: only modules that do NOT import Django models are re-exported here.
``resolver`` and ``ingest`` import ``catalog.models`` (which in turn import
``catalog.services.constants``), so importing them at package-init time would
create a circular import. Import those directly, e.g.::

    from apps.catalog.services.resolver import CardResolver
    from apps.catalog.services.ingest import ingest_items
"""

from . import constants
from .title_parser import ParsedCard, parse_title

__all__ = [
    'constants',
    'ParsedCard',
    'parse_title',
]
