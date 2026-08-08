"""Abstract base class for all external data source clients.

Every new source (BPS, data.go.id, World Bank, etc.) must subclass this
and implement search(), fetch(), and get_license_info().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd


@dataclass
class SearchResultItem:
    """Standardized search result from any external source."""
    id: str
    source_slug: str
    title: str
    description: str
    row_count: Optional[int] = None
    column_names: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    source_url: Optional[str] = None
    extra: dict = field(default_factory=dict)


class BaseExternalDataClient(ABC):
    """Contract that every external data source client must fulfill."""

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier for this source (e.g. 'bps', 'worldbank')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g. 'BPS - Badan Pusat Statistik')."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[SearchResultItem]:
        """Search this source for datasets matching the query."""
        ...

    @abstractmethod
    async def fetch(self, result_id: str) -> pd.DataFrame:
        """Fetch full data for a search result and return as DataFrame."""
        ...

    @abstractmethod
    def get_license_info(self) -> str:
        """Return a human-readable license/attribution note."""
        ...
