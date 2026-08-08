from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem
from app.services.external_data.source_registry import SourceRegistry

# Import clients to trigger auto-registration
from app.services.external_data import bps_client
from app.services.external_data import worldbank_client
from app.services.external_data import datagoid_client

__all__ = ["BaseExternalDataClient", "SearchResultItem", "SourceRegistry"]
