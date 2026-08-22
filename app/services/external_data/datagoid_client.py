"""data.go.id (Satu Data Indonesia) API client.

Docs: https://data.go.id
No API key required for public datasets.
"""
from typing import List
import httpx
import pandas as pd

from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem


DATAGOID_BASE = "https://data.go.id/api/3/action"


class DataGoIdClient(BaseExternalDataClient):

    @property
    def slug(self) -> str:
        return "datagoid"

    @property
    def display_name(self) -> str:
        return "data.go.id - Satu Data Indonesia"

    async def _request(self, path: str, params: dict = None) -> dict:
        """Make request to data.go.id CKAN API.

        Note: As of mid-2025, data.go.id has been redesigned and the old
        CKAN API endpoints (/api/3/action/*) return 404. This client will
        raise an error with a helpful message when the API is unavailable.
        """
        url = f"{DATAGOID_BASE}/{path}"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, params=params or {})
            if resp.status_code == 404:
                raise ConnectionError(
                    "Portal data.go.id sedang dalam masa kurasi ulang. "
                    "API CKAN lama (/api/3/action/) sudah tidak tersedia. "
                    "Silakan unduh data manual di https://data.go.id/dataset"
                )
            resp.raise_for_status()
            return resp.json()

    async def search(self, query: str, limit: int = 20) -> List[SearchResultItem]:
        """Search data.go.id packages (datasets) matching the query."""
        results = []
        try:
            data = await self._request("package_search", {
                "q": query,
                "rows": min(limit, 50),
            })

            packages = data.get("result", {}).get("results", [])
            for pkg in packages:
                name = pkg.get("title", pkg.get("name", ""))
                pkg_id = pkg.get("id", "")
                notes = pkg.get("notes", "")
                org = pkg.get("organization", {})
                org_title = org.get("title", "") if org else ""

                # Get resources info
                resources = pkg.get("resources", [])
                formats = list(set(r.get("format", "") for r in resources if r.get("format")))

                # Try to get row count from resource
                row_count = None
                for r in resources:
                    if r.get("num_revisions"):
                        row_count = r.get("num_revisions")

                results.append(SearchResultItem(
                    id=f"datagoid:pkg:{pkg_id}",
                    source_slug="datagoid",
                    title=name,
                    description=f"{notes[:200]}..." if notes and len(notes) > 200 else notes,
                    row_count=row_count,
                    column_names=[],
                    last_updated=pkg.get("metadata_modified", "")[:10],
                    source_url=f"https://data.go.id/dataset/{pkg.get('name', '')}",
                    extra={
                        "org": org_title,
                        "formats": formats,
                        "num_resources": len(resources),
                    },
                ))

        except ConnectionError as e:
            # API endpoint is dead (portal redesigned) — return empty silently
            return []
        except Exception as e:
            # data.go.id API might be unreliable — don't crash
            return []

        return results[:limit]

    async def fetch(self, result_id: str) -> pd.DataFrame:
        """Fetch full data for a data.go.id dataset.

        Downloads the first CSV/JSON resource found in the package.
        """
        parts = result_id.split(":")
        if len(parts) != 3 or parts[0] != "datagoid":
            raise ValueError(f"Invalid data.go.id result_id: {result_id}")

        pkg_id = parts[2]

        # Get package details
        data = await self._request("package_show", {"id": pkg_id})
        pkg = data.get("result", {})
        resources = pkg.get("resources", [])

        if not resources:
            return pd.DataFrame()

        # Find best resource (prefer CSV, then JSON)
        target_resource = None
        for r in resources:
            fmt = (r.get("format") or "").upper()
            if fmt == "CSV":
                target_resource = r
                break
        if not target_resource:
            for r in resources:
                fmt = (r.get("format") or "").upper()
                if fmt in ("JSON", "XLS", "XLSX"):
                    target_resource = r
                    break
        if not target_resource:
            target_resource = resources[0]

        resource_url = target_resource.get("url", "")
        if not resource_url:
            return pd.DataFrame()

        # Download and parse
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(resource_url)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        fmt = (target_resource.get("format") or "").upper()

        if fmt == "CSV" or "csv" in content_type:
            from io import StringIO
            return pd.read_csv(StringIO(resp.text))
        elif fmt in ("JSON",) or "json" in content_type:
            from io import StringIO
            try:
                json_data = resp.json()
                if isinstance(json_data, list):
                    return pd.DataFrame(json_data)
                elif isinstance(json_data, dict) and "result" in json_data:
                    result = json_data["result"]
                    if isinstance(result, list):
                        return pd.DataFrame(result)
                return pd.DataFrame([json_data])
            except Exception:
                return pd.read_json(StringIO(resp.text))
        else:
            # Try CSV as fallback
            from io import StringIO
            try:
                return pd.read_csv(StringIO(resp.text))
            except Exception:
                return pd.DataFrame({"raw_content": [resp.text[:1000]]})

    def get_license_info(self) -> str:
        return (
            "Data dari Portal Satu Data Indonesia (data.go.id). "
            "Data pemerintah Indonesia yang tersedia untuk publik. "
            "https://data.go.id"
        )


# Register on import
from app.services.external_data.source_registry import register_source
_register_done = False
def _ensure_registered():
    global _register_done
    if not _register_done:
        register_source(DataGoIdClient())
        _register_done = True

_ensure_registered()
