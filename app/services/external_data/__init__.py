from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem
from app.services.external_data.source_registry import get_all_sources, get_source, register_source

# Import clients to trigger auto-registration
from app.services.external_data import bps_client
from app.services.external_data import worldbank_client
from app.services.external_data import datagoid_client

__all__ = ["BaseExternalDataClient", "SearchResultItem", "get_all_sources", "get_source", "register_source"]
