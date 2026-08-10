import httpx
import re
import hashlib
import asyncio
import json
from typing import Optional, List, Dict, Any, Set
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    url: str
    title: str
    tables: list[dict] = field(default_factory=list)
    text_blocks: list[list[str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    row_count: int = 0
    column_count: int = 0
    content_hash: str = ""
    links: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    json_ld: list[dict] = field(default_factory=list)
    microdata: list[dict] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    api_endpoints: list[dict] = field(default_factory=list)
    open_graph: dict = field(default_factory=dict)
    twitter_card: dict = field(default_factory=dict)
    meta_tags: dict = field(default_factory=dict)
    schema_org: list[dict] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    language: str = ""
    word_count: int = 0
    reading_time_minutes: float = 0.0
    scrape_strategy: str = "static"
    scrape_duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "tables": self.tables,
            "text_blocks": self.text_blocks,
            "metadata": self.metadata,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "content_hash": self.content_hash,
            "links": self.links,
            "images": self.images,
            "json_ld": self.json_ld,
            "microdata": self.microdata,
            "feeds": self.feeds,
            "api_endpoints": self.api_endpoints,
            "open_graph": self.open_graph,
            "twitter_card": self.twitter_card,
            "meta_tags": self.meta_tags,
            "schema_org": self.schema_org,
            "keywords": self.keywords,
            "language": self.language,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
            "scrape_strategy": self.scrape_strategy,
            "scrape_duration_ms": self.scrape_duration_ms,
        }


class HtmlScraper:
    ALLOWED_SCHEMES = ("http://", "https://")
    MAX_SIZE_BYTES = 20 * 1024 * 1024
    TIMEOUT = 30
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    MAX_RECURSIVE_DEPTH = 3
    MAX_PAGES_PER_DOMAIN = 50

    def __init__(self, proxy: str = None, user_agent: str = None):
        self.proxy = proxy
        self.user_agent = user_agent or self.USER_AGENT
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
        }
        self._visited: Set[str] = set()

    def _validate_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(self.ALLOWED_SCHEMES):
            raise ValueError(f"URL harus dimulai dengan http:// atau https://")
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"URL tidak valid: {url}")
        blocked = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.", "10.", "192.168.", "172."]
        hostname = parsed.hostname or ""
        for b in blocked:
            if hostname.startswith(b) or hostname == b.rstrip("."):
                raise ValueError(f"URL internal/privat tidak diizinkan: {url}")
        return url

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_table(self, table: Tag) -> dict:
        headers = []
        rows = []
        thead = table.find("thead")
        if thead:
            for th in thead.find_all(["th", "td"]):
                headers.append(self._clean_text(th.get_text()))
        if not headers:
            first_row = table.find("tr")
            if first_row:
                for cell in first_row.find_all(["th", "td"]):
                    headers.append(self._clean_text(cell.get_text()))
                if not any(h for h in headers):
                    headers = []
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            if thead and tr in (thead.find_all("tr") if thead else []):
                continue
            cells = [self._clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
            if cells and any(c for c in cells):
                rows.append(cells)
        if headers and rows:
            max_cols = max(len(headers), max(len(r) for r in rows))
            while len(headers) < max_cols:
                headers.append(f"col_{len(headers)+1}")
            for row in rows:
                while len(row) < max_cols:
                    row.append("")
                while len(row) > max_cols:
                    row.pop()
        if not headers and rows:
            headers = [f"col_{i+1}" for i in range(len(rows[0]))] if rows else []
        if headers and rows:
            data = [dict(zip(headers, row)) for row in rows]
            return {"headers": headers, "rows": data, "row_count": len(rows)}
        return {"headers": [], "rows": [], "row_count": 0}

    def _extract_lists(self, soup: BeautifulSoup) -> list[list[str]]:
        results = []
        for ul in soup.find_all(["ul", "ol"]):
            items = [self._clean_text(li.get_text()) for li in ul.find_all("li", recursive=False)]
            if len(items) >= 3:
                results.append(items)
        return results

    def _extract_key_value_pairs(self, soup: BeautifulSoup) -> list[dict]:
        pairs = []
        for dl in soup.find_all("dl"):
            dts = [self._clean_text(dt.get_text()) for dt in dl.find_all("dt")]
            dds = [self._clean_text(dd.get_text()) for dd in dl.find_all("dd")]
            for dt, dd in zip(dts, dds):
                if dt and dd:
                    pairs.append({dt: dd})
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if len(cells) == 2:
                    key = self._clean_text(cells[0].get_text())
                    val = self._clean_text(cells[1].get_text())
                    if key and val and len(key) < 100:
                        pairs.append({key: val})
        return pairs

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return results

    def _extract_microdata(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        for item in soup.find_all(attrs={"itemscope": True}):
            itemtype = item.get("itemtype", "")
            props = {}
            for prop in item.find_all(attrs={"itemprop": True}):
                name = prop.get("itemprop", "")
                value = prop.get("content") or prop.get("href") or self._clean_text(prop.get_text())
                props[name] = value
            if props:
                results.append({"type": itemtype, "properties": props})
        return results

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ("http", "https") and full_url not in seen:
                seen.add(full_url)
                links.append(full_url)
        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src:
                images.append({
                    "src": urljoin(base_url, src),
                    "alt": alt,
                    "width": img.get("width", ""),
                    "height": img.get("height", ""),
                })
        return images[:100]

    def _extract_feeds(self, soup: BeautifulSoup) -> list[str]:
        feeds = []
        for link in soup.find_all("link", attrs={"type": re.compile(r"application/(rss|atom)\+xml")}):
            href = link.get("href", "")
            if href:
                feeds.append(href)
        return feeds

    def _extract_api_endpoints(self, soup: BeautifulSoup, page_text: str) -> list[dict]:
        endpoints = []
        patterns = [
            r'["\'](/api/[^"\']+)["\']',
            r'["\']https?://[^"\']*api[^"\']*["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.\w+\(["\']([^"\']+)["\']',
            r'XMLHttpRequest.*?open\([^,]+,\s*["\']([^"\']+)["\']',
        ]
        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, page_text):
                url = match.group(1) if match.lastindex else match.group(0)
                url = url.strip("'\"")
                if url not in seen and len(url) < 500:
                    seen.add(url)
                    endpoints.append({"url": url, "type": "discovered"})
        return endpoints[:20]

    def _extract_open_graph(self, soup: BeautifulSoup) -> dict:
        og = {}
        for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
            prop = meta.get("property", "").replace("og:", "")
            content = meta.get("content", "")
            if prop and content:
                og[prop] = content
        return og

    def _extract_twitter_card(self, soup: BeautifulSoup) -> dict:
        tc = {}
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = meta.get("name", "").replace("twitter:", "")
            content = meta.get("content", "")
            if name and content:
                tc[name] = content
        return tc

    def _extract_meta_tags(self, soup: BeautifulSoup) -> dict:
        meta = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name", tag.get("property", ""))
            content = tag.get("content", "")
            if name and content:
                meta[name] = content
        return meta

    def _extract_keywords(self, soup: BeautifulSoup) -> list[str]:
        keywords = []
        kw_meta = soup.find("meta", attrs={"name": "keywords"})
        if kw_meta and kw_meta.get("content"):
            keywords = [k.strip() for k in kw_meta["content"].split(",") if k.strip()]
        if not keywords:
            for tag in soup.find_all("meta", attrs={"name": "subject"}):
                if tag.get("content"):
                    keywords.append(tag["content"])
        return keywords[:20]

    def _detect_language(self, soup: BeautifulSoup) -> str:
        html_tag = soup.find("html")
        if html_tag:
            lang = html_tag.get("lang", "")
            if lang:
                return lang[:10]
        meta = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta and meta.get("content"):
            return meta["content"][:10]
        return ""

    def _calculate_word_count(self, soup: BeautifulSoup) -> int:
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text()
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    def _detect_data_patterns(self, soup: BeautifulSoup) -> dict:
        patterns = {
            "has_forms": bool(soup.find("form")),
            "has_pagination": bool(soup.find("nav", class_=re.compile(r"paginat|page", re.I)) or
                                  soup.find("a", class_=re.compile(r"paginat|page", re.I)) or
                                  soup.find("ul", class_=re.compile(r"paginat|page", re.I))),
            "has_search": bool(soup.find("input", {"type": "search"}) or
                              soup.find("form", attrs={"action": re.compile(r"search", re.I)})),
            "has_table_of_contents": bool(soup.find("nav", id=re.compile(r"toc|table.of.content", re.I)) or
                                         soup.find("div", class_=re.compile(r"toc|table.of.content", re.I))),
            "has_carousel": bool(soup.find(class_=re.compile(r"carousel|slider|swiper", re.I))),
            "has_modal": bool(soup.find(class_=re.compile(r"modal|popup|dialog", re.I))),
            "has_accordion": bool(soup.find(class_=re.compile(r"accordion|collapse|expand", re.I))),
            "has_tabs": bool(soup.find(class_=re.compile(r"tab-panel|tab-content|tab-pane", re.I))),
            "has_infinite_scroll": bool(soup.find(attrs={"data-infinite-scroll": True}) or
                                       soup.find(attrs={"data-load-more": True})),
            "has_lazy_images": bool(soup.find("img", attrs={"loading": "lazy"})),
        }
        return patterns

    def _extract_structured_data(self, soup: BeautifulSoup) -> dict:
        data = {"json_ld": [], "microdata": [], "rdfa": []}
        data["json_ld"] = self._extract_json_ld(soup)
        data["microdata"] = self._extract_microdata(soup)
        for tag in soup.find_all(attrs={"typeof": True}):
            props = {}
            for prop in tag.find_all(attrs={"property": True}):
                props[prop.get("property", "")] = prop.get("content") or self._clean_text(prop.get_text())
            if props:
                data["rdfa"].append({"type": tag.get("typeof", ""), "properties": props})
        return data

    async def _fetch_html(self, url: str) -> tuple[str, int, dict]:
        # Try httpx first
        try:
            transport = None
            if self.proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self.proxy)
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT,
                follow_redirects=True,
                headers=self.headers,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                transport=transport,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text, resp.status_code, dict(resp.headers)
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in (403, 406, 429):
                raise
            logger.warning(f"httpx got {e.response.status_code} for {url}, trying curl_cffi")
        except Exception as e:
            logger.warning(f"httpx failed for {url}: {e}, trying curl_cffi")

        # Fallback: curl_cffi (bypasses TLS fingerprint detection)
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(
                url,
                impersonate="chrome",
                headers=self.headers,
                timeout=self.TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.text, resp.status_code, dict(resp.headers)
        except Exception as e:
            logger.warning(f"curl_cffi also failed for {url}: {e}")
            raise

    async def scrape(self, url: str, extract_tables: bool = True, extract_lists: bool = True,
                     strategy: str = "auto") -> ScrapeResult:
        start_time = datetime.now()
        url = self._validate_url(url)

        html, status_code, response_headers = await self._fetch_html(url)
        content_type = response_headers.get("content-type", "")

        if "application/json" in content_type:
            return await self._scrape_json(url, html, status_code, start_time)
        elif "application/xml" in content_type or "text/xml" in content_type:
            return await self._scrape_xml(url, html, status_code, start_time)
        elif "text/html" not in content_type and "application/xhtml" not in content_type:
            return ScrapeResult(
                url=url, title="",
                metadata={"content_type": content_type, "non_html": True, "status_code": status_code},
                content_hash=hashlib.md5(html.encode()).hexdigest(),
                scrape_strategy="raw",
                scrape_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

        if len(html.encode()) > self.MAX_SIZE_BYTES:
            raise ValueError(f"Halaman terlalu besar ({len(html.encode()) // 1024}KB > {self.MAX_SIZE_BYTES // 1024}KB)")

        soup = BeautifulSoup(html, "lxml")
        result = ScrapeResult(url=url, title="", scrape_strategy="static")

        result.title = self._extract_title(soup, url)
        result.open_graph = self._extract_open_graph(soup)
        result.twitter_card = self._extract_twitter_card(soup)
        result.meta_tags = self._extract_meta_tags(soup)
        result.keywords = self._extract_keywords(soup)
        result.language = self._detect_language(soup)
        result.feeds = self._extract_feeds(soup)
        result.images = self._extract_images(soup, url)
        result.links = self._extract_links(soup, url)[:200]
        result.json_ld = self._extract_json_ld(soup)
        result.microdata = self._extract_microdata(soup)

        page_text = str(soup)
        result.api_endpoints = self._extract_api_endpoints(soup, page_text)

        result.metadata = {
            "status_code": status_code,
            "content_type": content_type,
            "structured_data": self._extract_structured_data(soup),
            "data_patterns": self._detect_data_patterns(soup),
            "response_headers": {k: v for k, v in response_headers.items()
                                 if k.lower() in ("server", "x-powered-by", "content-encoding", "cache-control")},
        }

        if extract_tables:
            tables = []
            for table in soup.find_all("table"):
                extracted = self._extract_table(table)
                if extracted["row_count"] > 0:
                    tables.append(extracted)
            result.tables = tables

        if extract_lists:
            result.text_blocks = self._extract_lists(soup)

        kv_pairs = self._extract_key_value_pairs(soup)
        if kv_pairs:
            result.metadata["key_value_pairs"] = kv_pairs

        soup_copy = BeautifulSoup(html, "lxml")
        result.word_count = self._calculate_word_count(soup_copy)
        result.reading_time_minutes = round(result.word_count / 200, 1)

        total_rows = sum(t["row_count"] for t in result.tables)
        result.row_count = total_rows
        if result.tables:
            result.column_count = max(len(t["headers"]) for t in result.tables)

        result.content_hash = hashlib.md5(html.encode()).hexdigest()
        result.scrape_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    async def _scrape_json(self, url: str, raw_text: str, status_code: int, start_time: datetime) -> ScrapeResult:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            data = {"raw": raw_text[:5000]}

        result = ScrapeResult(
            url=url, title="JSON Response", scrape_strategy="json",
            scrape_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        )
        result.metadata = {"status_code": status_code, "content_type": "application/json"}

        if isinstance(data, list):
            result.row_count = len(data)
            if data and isinstance(data[0], dict):
                result.column_count = len(data[0])
                result.tables = [{"headers": list(data[0].keys()), "rows": data, "row_count": len(data)}]
        elif isinstance(data, dict):
            result.metadata["json_keys"] = list(data.keys())[:50]
            for key, val in data.items():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    result.tables.append({
                        "headers": list(val[0].keys()),
                        "rows": val,
                        "row_count": len(val),
                    })
                    result.row_count += len(val)

        result.content_hash = hashlib.md5(raw_text.encode()).hexdigest()
        return result

    async def _scrape_xml(self, url: str, raw_text: str, status_code: int, start_time: datetime) -> ScrapeResult:
        soup = BeautifulSoup(raw_text, "lxml-xml")
        result = ScrapeResult(
            url=url, title="XML Response", scrape_strategy="xml",
            scrape_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        )
        result.metadata = {"status_code": status_code, "content_type": "application/xml"}

        items = soup.find_all(item=True) or soup.find_all()[:100]
        if items:
            first = items[0]
            if first.children:
                headers = [child.name for child in first.children if child.name]
                rows = []
                for item in items[:1000]:
                    row = {}
                    for h in headers:
                        tag = item.find(h)
                        row[h] = tag.get_text(strip=True) if tag else ""
                    rows.append(row)
                if rows:
                    result.tables = [{"headers": headers, "rows": rows, "row_count": len(rows)}]
                    result.row_count = len(rows)
                    result.column_count = len(headers)

        result.content_hash = hashlib.md5(raw_text.encode()).hexdigest()
        return result

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = self._clean_text(h1.get_text())
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "")
        if not title:
            title = url
        return title

    async def scrape_recursive(self, url: str, max_depth: int = 2, max_pages: int = 10,
                               extract_tables: bool = True) -> list[ScrapeResult]:
        results = []
        self._visited = set()
        parsed_base = urlparse(url)
        base_domain = parsed_base.netloc

        async def _crawl(current_url: str, depth: int):
            if depth > max_depth or len(results) >= max_pages or current_url in self._visited:
                return
            self._visited.add(current_url)
            try:
                result = await self.scrape(current_url, extract_tables=extract_tables)
                result.metadata["depth"] = depth
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to scrape {current_url}: {e}")
                return

            if depth < max_depth:
                internal_links = [
                    link for link in result.links
                    if urlparse(link).netloc == base_domain
                    and not any(ext in link.lower() for ext in [".pdf", ".jpg", ".png", ".gif", ".zip", ".mp4"])
                    and link not in self._visited
                ][:10]
                await asyncio.gather(*[_crawl(link, depth + 1) for link in internal_links])

        await _crawl(url, 0)
        return results

    async def discover_sitemaps(self, url: str) -> list[str]:
        sitemaps = []
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        try:
            robots_url = f"{base}/robots.txt"
            text, _, _ = await self._fetch_html(robots_url)
            for line in text.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemaps.append(sitemap_url)
        except Exception:
            pass

        common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-news.xml"]
        for path in common_paths:
            try:
                sitemap_url = base + path
                text, status, _ = await self._fetch_html(sitemap_url)
                if status == 200 and ("<urlset" in text or "<sitemapindex" in text):
                    sitemaps.append(sitemap_url)
            except Exception:
                pass

        return list(set(sitemaps))

    async def parse_sitemap(self, sitemap_url: str, limit: int = 100) -> list[str]:
        urls = []
        try:
            text, _, _ = await self._fetch_html(sitemap_url)
            soup = BeautifulSoup(text, "lxml-xml")

            for loc in soup.find_all("loc"):
                loc_text = loc.get_text(strip=True)
                if loc_text:
                    urls.append(loc_text)

            if not urls:
                for loc in soup.find_all("url"):
                    loc_tag = loc.find("loc")
                    if loc_tag:
                        urls.append(loc_tag.get_text(strip=True))
        except Exception as e:
            logger.warning(f"Failed to parse sitemap {sitemap_url}: {e}")

        return urls[:limit]
