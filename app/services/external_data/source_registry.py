"""Registry of all active external data sources.

Clients register themselves here. The API layer queries this registry
to fan out searches to all active sources in parallel.
"""
from typing import Dict, List, Type
from app.services.external_data.base_client import BaseExternalDataClient


_registry: Dict[str, BaseExternalDataClient] = {}


def register_source(client: BaseExternalDataClient) -> None:
    """Register a source client instance."""
    _registry[client.slug] = client


def get_source(slug: str) -> BaseExternalDataClient | None:
    """Get a registered source client by slug."""
    return _registry.get(slug)


def get_all_sources() -> List[BaseExternalDataClient]:
    """Return all registered source clients."""
    return list(_registry.values())


def get_active_slugs() -> List[str]:
    """Return slugs of all registered sources."""
    return list(_registry.keys())
