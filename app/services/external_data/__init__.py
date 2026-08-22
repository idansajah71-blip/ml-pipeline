from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem
from app.services.external_data.source_registry import get_all_sources, get_source, register_source

# Import clients to trigger auto-registration

__all__ = ["BaseExternalDataClient", "SearchResultItem", "get_all_sources", "get_source", "register_source"]
