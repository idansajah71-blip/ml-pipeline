"""Tests for external data search & import feature (Phase 10)."""
import pytest
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem
from app.services.external_data.source_registry import (
    register_source, get_source, get_all_sources, get_active_slugs
)
from app.services.external_data.cache_service import _hash_query


# ── Base Client ──────────────────────────────────────────────────────────


class TestSearchResultItem:
    def test_defaults(self):
        item = SearchResultItem(id="test:1", source_slug="test", title="T", description="D")
        assert item.id == "test:1"
        assert item.source_slug == "test"
        assert item.row_count is None
        assert item.column_names == []
        assert item.extra == {}

    def test_with_values(self):
        item = SearchResultItem(
            id="bps:1", source_slug="bps", title="Harga",
            description="Harga beras", row_count=100,
            column_names=["year", "value"], last_updated="2024-01-01"
        )
        assert item.row_count == 100
        assert len(item.column_names) == 2


# ── Source Registry ──────────────────────────────────────────────────────


class TestSourceRegistry:
    def setup_method(self):
        # Clear registry
        from app.services.external_data import source_registry
        source_registry._registry.clear()

    def test_register_and_get(self):
        mock_client = MagicMock(spec=BaseExternalDataClient)
        mock_client.slug = "test_source"
        register_source(mock_client)
        assert get_source("test_source") is mock_client

    def test_get_nonexistent(self):
        assert get_source("nonexistent") is None

    def test_get_all_sources(self):
        c1 = MagicMock(spec=BaseExternalDataClient)
        c1.slug = "a"
        c2 = MagicMock(spec=BaseExternalDataClient)
        c2.slug = "b"
        register_source(c1)
        register_source(c2)
        sources = get_all_sources()
        assert len(sources) == 2

    def test_get_active_slugs(self):
        c1 = MagicMock(spec=BaseExternalDataClient)
        c1.slug = "x"
        register_source(c1)
        assert "x" in get_active_slugs()


# ── Cache Service ────────────────────────────────────────────────────────


class TestCacheService:
    def test_hash_query_deterministic(self):
        h1 = _hash_query("bps", "harga beras")
        h2 = _hash_query("bps", "harga beras")
        assert h1 == h2

    def test_hash_query_different_sources(self):
        h1 = _hash_query("bps", "test")
        h2 = _hash_query("worldbank", "test")
        assert h1 != h2

    def test_hash_query_case_insensitive(self):
        h1 = _hash_query("bps", "Harga Beras")
        h2 = _hash_query("bps", "harga beras")
        assert h1 == h2

    def test_hash_query_length(self):
        h = _hash_query("bps", "test")
        assert len(h) == 32  # sha256 truncated to 32 chars


# ── BPS Client ───────────────────────────────────────────────────────────


class TestBPSClient:
    @pytest.fixture
    def client(self):
        from app.services.external_data.bps_client import BPSClient
        return BPSClient()

    def test_slug(self, client):
        assert client.slug == "bps"

    def test_display_name(self, client):
        assert "BPS" in client.display_name

    def test_license_info(self, client):
        info = client.get_license_info()
        assert "BPS" in info
        assert "atribusi" in info.lower()

    @pytest.mark.asyncio
    async def test_search_no_api_key(self, client):
        import os
        from app.core.config import get_settings
        get_settings.cache_clear()
        with patch.dict(os.environ, {"BPS_API_KEY": ""}, clear=False):
            with pytest.raises(EnvironmentError, match="BPS_API_KEY"):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_search_with_mock(self, client):
        from app.core.config import get_settings
        # Real BPS envelope: data = [pagination_info, [items]]
        mock_response = {
            "data": [
                {"page": 1, "per_page": 20},
                [
                    {"id": 1, "name": "Harga Beras", "subject": 80},
                    {"id": 2, "name": "Populasi", "subject": 81},
                ],
            ]
        }
        get_settings.cache_clear()
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            with patch.dict("os.environ", {"BPS_API_KEY": "test-key"}):
                results = await client.search("harga")
                assert len(results) >= 1
                assert any("Harga" in r.title for r in results)

    @pytest.mark.asyncio
    async def test_fetch_invalid_id(self, client):
        with pytest.raises(ValueError, match="Invalid"):
            await client.fetch("invalid_id")


# ── World Bank Client ────────────────────────────────────────────────────


class TestWorldBankClient:
    @pytest.fixture
    def client(self):
        from app.services.external_data.worldbank_client import WorldBankClient
        return WorldBankClient()

    def test_slug(self, client):
        assert client.slug == "worldbank"

    def test_display_name(self, client):
        assert "World Bank" in client.display_name

    def test_license_info(self, client):
        info = client.get_license_info()
        assert "CC-BY" in info

    @pytest.mark.asyncio
    async def test_search_popular_indicator(self, client):
        results = await client.search("populasi")
        assert len(results) >= 1
        assert any("Populasi" in r.title for r in results)

    @pytest.mark.asyncio
    async def test_search_poverty(self, client):
        results = await client.search("kemiskinan")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_fetch_invalid_id(self, client):
        with pytest.raises(ValueError, match="Invalid"):
            await client.fetch("bad_id")


# ── Data.go.id Client ────────────────────────────────────────────────────


class TestDataGoIdClient:
    @pytest.fixture
    def client(self):
        from app.services.external_data.datagoid_client import DataGoIdClient
        return DataGoIdClient()

    def test_slug(self, client):
        assert client.slug == "datagoid"

    def test_display_name(self, client):
        assert "data.go.id" in client.display_name

    def test_license_info(self, client):
        info = client.get_license_info()
        assert "data.go.id" in info


# ── API Validation ───────────────────────────────────────────────────────


class TestExternalDataValidation:
    def test_result_id_pattern(self):
        import re
        # Dots are legal (e.g. World Bank indicator SP.POP.TOTL)
        pattern = re.compile(r'^[a-zA-Z0-9:._\-]+$')
        assert pattern.match("bps:var:123")
        assert pattern.match("worldbank:indicator:SP.POP.TOTL")
        assert not pattern.match("bps; DROP TABLE")
        assert not pattern.match("../../../etc/passwd")

    def test_source_slug_pattern(self):
        import re
        pattern = re.compile(r'^[a-z0-9_]+$')
        assert pattern.match("bps")
        assert pattern.match("worldbank")
        assert pattern.match("data_go_id")
        assert not pattern.match("BPS")
        assert not pattern.match("test;injection")
