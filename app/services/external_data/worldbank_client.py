"""World Bank Open Data API client.

Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
No API key required. License: CC-BY 4.0.
"""
from typing import List
import httpx
import pandas as pd

from app.services.external_data.base_client import BaseExternalDataClient, SearchResultItem


WORLD_BANK_BASE = "https://api.worldbank.org/v2"

# Indonesian → English query translation dictionary
# Maps common Indonesian search terms to English indicator keywords/codes
INDO_ENGLISH_MAP = {
    "harga": "price",
    "inflasi": "inflation",
    "penduduk": "population",
    "jumlah penduduk": "population, total",
    "pertumbuhan": "growth",
    "gdp": "gdp",
    "ekonomi": "economic",
    "kemiskinan": "poverty",
    "pengangguran": "unemployment",
    "pendidikan": "education",
    "sekolah": "school",
    "kesehatan": "health",
    "harapan hidup": "life expectancy",
    "fertilitas": "fertility",
    "perdagangan": "trade",
    "ekspor": "export",
    "impor": "import",
    "investasi": "investment",
    "listrik": "electricity",
    "energi": "energy",
    "internet": "internet",
    "teknologi": "technology",
    "air": "water",
    "pangan": "food",
    "beras": "rice",
    "jagung": "corn",
    "sapi": "cattle",
    "pertanian": "agriculture",
    "industri": "industry",
    "manufaktur": "manufacturing",
    "konstruksi": "construction",
    "transportasi": "transport",
    "pariwisata": "tourism",
    "deflasi": "deflasi",
    "nilai tukar": "exchange rate",
    "kurs": "exchange rate",
    "utang": "debt",
    "anggaran": "budget",
    "belanja": "expenditure",
    "pendapatan": "income",
    "upah": "wage",
    "tenaga kerja": "labor force",
    "lapangan kerja": "employment",
    "iklim": "climate",
    "cuaca": "weather",
    "curah hujan": "rainfall",
    "tanaman": "crop",
    "luas lahan": "land area",
    "provinsi": "province",
    "kabupaten": "regency",
    "kota": "city",
}

# Common indicators relevant to Indonesia / UMKM / Education
POPULAR_INDICATORS = {
    "SP.POP.TOTL": "Total Populasi",
    "NY.GDP.PCAP.CD": "GDP per Capita (USD)",
    "SI.POV.DDAY": "Kemiskinan ($2.15/hari)",
    "SE.ADT.LITR.ZS": "Tingkat Melek Huruf (15+)",
    "SE.ENR.PRSC.FM": "Enrolmen Sekolah Dasar",
    "IC.REG.DURS": "Hari untuk Mendirikan Usaha",
    "FP.CPI.TOTL.ZG": "Inflasi (CPI)",
    "BN.CAB.XOKA.CD": "Neraca Perdagangan",
    "EG.USE.ELEC.KH.PC": "Konsumsi Listrik per Kapita",
    "SP.DYN.LE00.IN": "Harapan Hidup",
    "SP.DYN.TFRT.IN": "Total Fertility Rate",
    "IT.NET.USER.ZS": "Pengguna Internet (%)",
    "SL.UEM.TOTL.ZS": "Tingkat Pengangguran",
    "NE.TRD.GNFS.ZS": "Perdagangan (% GDP)",
    "GC.XPN.TOTL.GD.ZS": "Pengeluaran Pemerintah (% GDP)",
}


class WorldBankClient(BaseExternalDataClient):

    @property
    def slug(self) -> str:
        return "worldbank"

    @property
    def display_name(self) -> str:
        return "World Bank Open Data"

    def _translate_query(self, query: str) -> list[str]:
        """Translate Indonesian query terms to English keywords for matching.

        Returns a list of English keywords to search for.
        """
        query_lower = query.lower().strip()
        keywords = [query_lower]  # always include original query

        # Direct translation lookup
        if query_lower in INDO_ENGLISH_MAP:
            translated = INDO_ENGLISH_MAP[query_lower]
            if translated not in keywords:
                keywords.append(translated)

        # Partial/compound match: try each word
        for indo, eng in INDO_ENGLISH_MAP.items():
            if indo in query_lower and eng not in keywords:
                keywords.append(eng)

        return keywords

    async def search(self, query: str, limit: int = 20) -> List[SearchResultItem]:
        """Search World Bank indicators matching the query."""
        results = []
        keywords = self._translate_query(query)

        # First: match against known popular indicators using translated keywords
        for code, name in POPULAR_INDICATORS.items():
            name_lower = name.lower()
            code_lower = code.lower()
            for kw in keywords:
                if kw in name_lower or kw in code_lower:
                    results.append(SearchResultItem(
                        id=f"wb:indicator:{code}",
                        source_slug="worldbank",
                        title=f"{name} — Indonesia",
                        description=f"World Bank indicator: {name} ({code})",
                        column_names=["year", "value"],
                        last_updated="Terkini",
                        source_url=f"https://data.worldbank.org/indicator/{code}?locations=ID",
                        extra={"indicator_code": code, "country": "IDN"},
                    ))
                    break

        # Second: query the World Bank indicators API with translated keywords
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{WORLD_BANK_BASE}/indicator",
                    params={"format": "json", "per_page": 100, "page": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    indicators = data[1] if len(data) > 1 else []
                    existing_ids = {r.id for r in results}
                    for ind in indicators:
                        code = ind.get("id", "")
                        name = ind.get("name", "")
                        name_lower = name.lower()
                        for kw in keywords:
                            if kw in name_lower:
                                if f"wb:indicator:{code}" not in existing_ids:
                                    results.append(SearchResultItem(
                                        id=f"wb:indicator:{code}",
                                        source_slug="worldbank",
                                        title=f"{name} — Indonesia",
                                        description=f"World Bank: {name}",
                                        column_names=["year", "value"],
                                        last_updated="Terkini",
                                        source_url=f"https://data.worldbank.org/indicator/{code}?locations=ID",
                                        extra={"indicator_code": code, "country": "IDN"},
                                    ))
                                    existing_ids.add(f"wb:indicator:{code}")
                                break
                                if len(results) >= limit:
                                    break
        except Exception:
            pass

        return results[:limit]

    async def fetch(self, result_id: str) -> pd.DataFrame:
        """Fetch full time-series data for a World Bank indicator (Indonesia)."""
        parts = result_id.split(":")
        if len(parts) != 3 or parts[0] != "wb":
            raise ValueError(f"Invalid World Bank result_id: {result_id}")

        indicator_code = parts[2]
        country = "IDN"  # Default to Indonesia

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{WORLD_BANK_BASE}/country/{country}/indicator/{indicator_code}",
                params={"format": "json", "per_page": 500},
            )
            resp.raise_for_status()
            data = resp.json()

        # World Bank returns [metadata, data[]]
        records = []
        if len(data) > 1 and data[1]:
            for item in data[1]:
                records.append({
                    "year": item.get("date", ""),
                    "value": item.get("value"),
                    "indicator": item.get("indicator", {}).get("value", ""),
                    "country": item.get("country", {}).get("value", ""),
                })

        return pd.DataFrame(records) if records else pd.DataFrame()

    def get_license_info(self) -> str:
        return (
            "Data dari World Bank Open Data. "
            "Licensed under CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/). "
            "Atribusi: 'Data from World Bank Open Data, https://data.worldbank.org/'"
        )


# Register on import
from app.services.external_data.source_registry import register_source
_register_done = False
def _ensure_registered():
    global _register_done
    if not _register_done:
        register_source(WorldBankClient())
        _register_done = True

_ensure_registered()
