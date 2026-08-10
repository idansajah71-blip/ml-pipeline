"""Smart Data Extractor — Automatically detects and extracts structured data
from any webpage using heuristics, patterns, and content analysis."""
import re
import json
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter

from bs4 import BeautifulSoup, Tag


@dataclass
class ExtractedDataset:
    name: str
    headers: list[str]
    rows: list[dict]
    row_count: int = 0
    confidence: float = 0.0
    extraction_method: str = ""
    source_element: str = ""
    quality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "headers": self.headers,
            "rows": self.rows[:100],
            "row_count": self.row_count,
            "confidence": round(self.confidence, 4),
            "extraction_method": self.extraction_method,
            "source_element": self.source_element,
            "quality_score": round(self.quality_score, 2),
        }


@dataclass
class ExtractionResult:
    url: str
    title: str
    datasets: list[ExtractedDataset] = field(default_factory=list)
    lists: list[dict] = field(default_factory=list)
    key_value_pairs: list[dict] = field(default_factory=list)
    json_data: list[dict] = field(default_factory=list)
    total_rows: int = 0
    total_datasets: int = 0
    extraction_quality: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "datasets": [d.to_dict() for d in self.datasets],
            "lists": self.lists,
            "key_value_pairs": self.key_value_pairs[:50],
            "json_data": self.json_data[:10],
            "total_rows": self.total_rows,
            "total_datasets": self.total_datasets,
            "extraction_quality": round(self.extraction_quality, 2),
            "summary": self.summary,
        }


class SmartDataExtractor:

    MIN_TABLE_ROWS = 2
    MIN_LIST_ITEMS = 3
    MAX_KEY_LENGTH = 100

    def extract_all(self, html: str, url: str = "") -> ExtractionResult:
        soup = BeautifulSoup(html, "lxml")
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        result = ExtractionResult(url=url, title=title)

        result.datasets = self._extract_tables_smart(soup)
        result.lists = self._extract_lists_smart(soup)
        result.key_value_pairs = self._extract_kv_pairs_smart(soup)
        result.json_data = self._extract_json_data(html)

        result.total_datasets = len(result.datasets)
        result.total_rows = sum(d.row_count for d in result.datasets)

        if result.datasets:
            qualities = [d.quality_score for d in result.datasets]
            result.extraction_quality = sum(qualities) / len(qualities)
        result.summary = (
            f"Extracted {result.total_datasets} datasets ({result.total_rows} rows), "
            f"{len(result.lists)} lists, {len(result.key_value_pairs)} key-value pairs, "
            f"{len(result.json_data)} JSON objects."
        )
        return result

    def _extract_tables_smart(self, soup: BeautifulSoup) -> list[ExtractedDataset]:
        datasets = []
        tables = soup.find_all("table")
        for i, table in enumerate(tables):
            dataset = self._analyze_table(table, index=i)
            if dataset and dataset.row_count >= self.MIN_TABLE_ROWS:
                datasets.append(dataset)
        datasets.sort(key=lambda d: d.quality_score, reverse=True)
        return datasets[:20]

    def _analyze_table(self, table: Tag, index: int = 0) -> Optional[ExtractedDataset]:
        rows_data = []
        headers = []

        thead = table.find("thead")
        if thead:
            for th in thead.find_all(["th", "td"]):
                text = th.get_text(strip=True)
                if text:
                    headers.append(text)

        if not headers:
            first_row = table.find("tr")
            if first_row:
                for cell in first_row.find_all(["th", "td"]):
                    text = cell.get_text(strip=True)
                    if text:
                        headers.append(text)

        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            if thead and tr in (thead.find_all("tr") if thead else []):
                continue
            cells = []
            for td in tr.find_all(["td", "th"]):
                text = td.get_text(strip=True)
                cells.append(text)
            if cells and any(c for c in cells):
                rows_data.append(cells)

        if not headers and rows_data:
            headers = [f"col_{i+1}" for i in range(len(rows_data[0]))]

        if not headers or not rows_data:
            return None

        max_cols = max(len(headers), max(len(r) for r in rows_data))
        while len(headers) < max_cols:
            headers.append(f"col_{len(headers)+1}")
        for row in rows_data:
            while len(row) < max_cols:
                row.append("")
            while len(row) > max_cols:
                row.pop()

        rows = [dict(zip(headers, row)) for row in rows_data]
        confidence = self._calculate_table_confidence(headers, rows_data, table)
        quality = self._calculate_table_quality(headers, rows_data)

        table_id = table.get("id", "")
        table_class = " ".join(table.get("class", []))
        name = table_id or table_class or f"table_{index}"

        return ExtractedDataset(
            name=name, headers=headers, rows=rows,
            row_count=len(rows), confidence=confidence,
            extraction_method="html_table",
            source_element=f"table#{table_id}" if table_id else f"table.{table_class}" if table_class else f"table[{index}]",
            quality_score=quality,
        )

    def _calculate_table_confidence(self, headers: list, rows: list, table: Tag) -> float:
        score = 0.5
        if table.find("thead"):
            score += 0.15
        if all(h.strip() for h in headers):
            score += 0.1
        has_th = bool(table.find("th"))
        if has_th:
            score += 0.1
        if len(rows) >= 5:
            score += 0.1
        if len(set(tuple(r) for r in rows)) == len(rows):
            score += 0.05
        avg_cell_len = sum(len(str(c)) for r in rows for c in r) / max(sum(len(r) for r in rows), 1)
        if 2 < avg_cell_len < 100:
            score += 0.05
        return min(score, 1.0)

    def _calculate_table_quality(self, headers: list, rows: list) -> float:
        score = 100.0
        if not headers:
            score -= 30
        empty_cells = sum(1 for r in rows for c in r if not str(c).strip())
        total_cells = len(rows) * len(headers) if headers else 1
        empty_pct = empty_cells / total_cells
        if empty_pct > 0.5:
            score -= 25
        elif empty_pct > 0.2:
            score -= 10
        if len(rows) < 3:
            score -= 15
        unique_rows = len(set(tuple(r) for r in rows))
        if unique_rows < len(rows) * 0.8:
            score -= 10
        numeric_count = 0
        for r in rows[:10]:
            for c in r:
                if re.match(r'^[\d,.\-+%]+$', str(c).strip()):
                    numeric_count += 1
        if numeric_count > total_cells * 0.3:
            score += 5
        return max(min(score, 100), 0)

    def _extract_lists_smart(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        for ul in soup.find_all(["ul", "ol"]):
            items = []
            for li in ul.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text:
                    items.append(text)
            if len(items) >= self.MIN_LIST_ITEMS:
                list_id = ul.get("id", "")
                list_class = " ".join(ul.get("class", []))
                has_links = bool(ul.find("a"))
                has_images = bool(ul.find("img"))
                has_nested = bool(ul.find(["ul", "ol"]))
                list_type = "ordered" if ul.name == "ol" else "unordered"
                if has_links:
                    list_type = "navigation"
                elif has_images:
                    list_type = "gallery"
                elif has_nested:
                    list_type = "nested"
                results.append({
                    "name": list_id or list_class or f"list_{len(results)}",
                    "type": list_type,
                    "items": items[:100],
                    "item_count": len(items),
                    "has_links": has_links,
                    "has_images": has_images,
                })
        return results[:20]

    def _extract_kv_pairs_smart(self, soup: BeautifulSoup) -> list[dict]:
        pairs = []
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and val and len(key) < self.MAX_KEY_LENGTH:
                    pairs.append({"key": key, "value": val, "source": "dl"})
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val and len(key) < self.MAX_KEY_LENGTH:
                        pairs.append({"key": key, "value": val, "source": "table"})
        for card in soup.find_all(class_=re.compile(r"card|info|detail|profile|meta", re.I)):
            card_key = card.find(class_=re.compile(r"title|name|label|header", re.I))
            card_val = card.find(class_=re.compile(r"value|content|desc|body|text", re.I))
            if card_key and card_val:
                key = card_key.get_text(strip=True)
                val = card_val.get_text(strip=True)
                if key and val and len(key) < self.MAX_KEY_LENGTH:
                    pairs.append({"key": key, "value": val, "source": "card"})
        seen = set()
        unique_pairs = []
        for p in pairs:
            k = f"{p['key']}:{p['value']}"
            if k not in seen:
                seen.add(k)
                unique_pairs.append(p)
        return unique_pairs[:100]

    def _extract_json_data(self, html: str) -> list[dict]:
        json_objects = []
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'window\.__DATA__\s*=\s*({.*?});',
            r'application/ld\+json["\']>\s*({.*?})\s*</script>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches[:5]:
                try:
                    data = json.loads(match)
                    json_objects.append({
                        "source": pattern[:30],
                        "data": data if isinstance(data, dict) else {"items": data},
                        "size": len(match),
                    })
                except json.JSONDecodeError:
                    pass
        return json_objects[:10]

    def extract_by_selector(self, html: str, selector: str, url: str = "") -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        elements = soup.select(selector)
        results = []
        for el in elements[:500]:
            results.append({
                "tag": el.name,
                "text": el.get_text(strip=True)[:500],
                "attributes": {k: v for k, v in el.attrs.items()},
                "html": str(el)[:1000],
            })
        return results

    def extract_by_xpath_like(self, html: str, path: str, url: str = "") -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        parts = [p for p in path.split("/") if p]
        current_elements = [soup]
        for part in parts:
            next_elements = []
            for el in current_elements:
                if isinstance(el, BeautifulSoup):
                    found = el.find_all(part)
                elif hasattr(el, "find_all"):
                    found = el.find_all(part)
                else:
                    found = []
                next_elements.extend(found)
            current_elements = next_elements
        results = []
        for el in current_elements[:500]:
            if hasattr(el, "get_text"):
                results.append({
                    "tag": el.name if hasattr(el, "name") else "",
                    "text": el.get_text(strip=True)[:500],
                    "attributes": dict(el.attrs) if hasattr(el, "attrs") else {},
                })
        return results
