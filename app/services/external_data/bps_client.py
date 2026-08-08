"""BPS (Badan Pusat Statistik) Web API client.

Docs: https://webapi.bps.go.id/documentation
Requires: BPS_API_KEY environment variable (free registration)
"""
import os
import hashlib
from typing import List, Optional
import httpx
import pandas as pd

from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem


BPS_BASE_URL = "https://webapi.bps.go.id/v1/api"


class BPSClient(BaseExternalDataClient):

    @property
    def slug(self) -> str:
        return "bps"

    @property
    def display_name(self) -> str:
        return "BPS - Badan Pusat Statistik"

    def _get_api_key(self) -> str:
        key = os.environ.get("BPS_API_KEY", "")
        if not key:
            raise EnvironmentError(
                "BPS_API_KEY not set. Register for free at "
                "https://webapi.bps.go.id/developer/register"
            )
        return key

    async def _request(self, params: dict) -> dict:
        """Make authenticated request to BPS API."""
        params["key"] = self._get_api_key()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(BPS_BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    async def search(self, query: str, limit: int = 20) -> List[SearchResultItem]:
        """Search BPS subjects and variables matching the query.

        Strategy: list all subjects for national domain (0000), filter by keyword match.
        BPS doesn't have a full-text search endpoint, so we search subject titles.
        """
        results = []
        try:
            # Fetch all subjects for national domain
            data = await self._request({
                "model": "subject",
                "domain": "0000",
                "page": 1,
            })

            subjects = data.get("data", []) or []
            for subj in subjects:
                title = subj.get("name", "") or subj.get("subject", "")
                subj_id = subj.get("id", "")

                # Fuzzy keyword match
                if query.lower() in title.lower() or title.lower() in query.lower():
                    # Fetch variables for this subject to get more detail
                    try:
                        var_data = await self._request({
                            "model": "var",
                            "domain": "0000",
                            "subject": subj_id,
                        })
                        variables = var_data.get("data", []) or []
                        for var in variables[:5]:  # limit per subject
                            var_title = var.get("title", "")
                            var_id = var.get("id", "")
                            results.append(SearchResultItem(
                                id=f"bps:var:{var_id}",
                                source_slug="bps",
                                title=f"{title} — {var_title}",
                                description=f"BPS dataset: {title} | Variable: {var_title}",
                                column_names=["period", "value"],
                                last_updated="Terkini",
                                source_url=f"https://webapi.bps.go.id/v1/api/list?model=data&domain=0000&var={var_id}",
                                extra={"subject_id": str(subj_id), "var_id": str(var_id)},
                            ))
                    except Exception:
                        # If variable fetch fails, still add the subject
                        results.append(SearchResultItem(
                            id=f"bps:subj:{subj_id}",
                            source_slug="bps",
                            title=title,
                            description=f"BPS subject: {title}",
                            column_names=[],
                            last_updated="Terkini",
                            extra={"subject_id": str(subj_id)},
                        ))

                    if len(results) >= limit:
                        break

            # If subject search didn't find enough, also try direct variable search
            if len(results) < limit:
                try:
                    var_data = await self._request({
                        "model": "var",
                        "domain": "0000",
                        "page": 1,
                    })
                    variables = var_data.get("data", []) or []
                    for var in variables:
                        var_title = var.get("title", "")
                        var_id = var.get("id", "")
                        if query.lower() in var_title.lower():
                            # Check not already in results
                            existing_ids = {r.id for r in results}
                            if f"bps:var:{var_id}" not in existing_ids:
                                results.append(SearchResultItem(
                                    id=f"bps:var:{var_id}",
                                    source_slug="bps",
                                    title=var_title,
                                    description=f"BPS indicator: {var_title}",
                                    column_names=["period", "value"],
                                    last_updated="Terkini",
                                    source_url=f"https://webapi.bps.go.id/v1/api/list?model=data&domain=0000&var={var_id}",
                                    extra={"var_id": str(var_id)},
                                ))
                                if len(results) >= limit:
                                    break
                except Exception:
                    pass

        except Exception as e:
            # Return empty on error — don't crash the search
            return []

        return results[:limit]

    async def fetch(self, result_id: str) -> pd.DataFrame:
        """Fetch full data for a BPS search result.

        result_id format: "bps:var:{var_id}" or "bps:subj:{subject_id}"
        """
        parts = result_id.split(":")
        if len(parts) != 3 or parts[0] != "bps":
            raise ValueError(f"Invalid BPS result_id: {result_id}")

        id_type = parts[1]  # "var" or "subj"
        raw_id = parts[2]

        if id_type == "var":
            # Fetch data for this variable
            data = await self._request({
                "model": "data",
                "domain": "0000",
                "var": raw_id,
            })
        elif id_type == "subj":
            # For subjects, we need to find the first variable
            var_data = await self._request({
                "model": "var",
                "domain": "0000",
                "subject": raw_id,
            })
            variables = var_data.get("data", []) or []
            if not variables:
                return pd.DataFrame()
            var_id = variables[0].get("id")
            data = await self._request({
                "model": "data",
                "domain": "0000",
                "var": str(var_id),
            })
        else:
            raise ValueError(f"Unknown BPS id_type: {id_type}")

        # Parse BPS response into DataFrame
        records = []
        data_items = data.get("data", []) or []
        for item in data_items:
            if isinstance(item, dict):
                time_label = item.get("label", item.get("time", ""))
                value = item.get("value", item.get("data", ""))
                records.append({"period": time_label, "value": value})
            elif isinstance(item, list) and len(item) >= 2:
                records.append({"period": str(item[0]), "value": item[1]})

        # Also check nested data structure
        if not records and data_items:
            for item in data_items:
                if isinstance(item, dict) and "data" in item:
                    inner = item["data"]
                    if isinstance(inner, list):
                        for row in inner:
                            if isinstance(row, dict):
                                records.append({
                                    "period": row.get("label", row.get("time", "")),
                                    "value": row.get("value", ""),
                                })

        return pd.DataFrame(records) if records else pd.DataFrame()

    def get_license_info(self) -> str:
        return (
            "Data publik pemerintah Indonesia dari Badan Pusat Statistik (BPS). "
            "Boleh digunakan dengan atribusi sumber. "
            "https://webapi.bps.go.id"
        )


# Register on import
from app.services.external_data.source_registry import register_source
_register_done = False
def _ensure_registered():
    global _register_done
    if not _register_done:
        register_source(BPSClient())
        _register_done = True

_ensure_registered()
