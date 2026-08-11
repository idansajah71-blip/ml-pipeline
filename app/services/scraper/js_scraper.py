"""JS-Rendered Scraper — Uses httpx with JavaScript rendering fallback.
Supports static HTML, SPA detection, and dynamic content extraction."""
import re
import json
import hashlib
import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SPA_FRAMEWORKS = {
    "react": ["__NEXT_DATA__", "_app", "react", "__react", "_next/static"],
    "vue": ["__NUXT__", "vue", "_nuxt", "vue-router"],
    "angular": ["ng-version", "angular", "__zone", "ng-"],
    "svelte": ["__svelte", "svelte", "_app/immutable"],
    "nextjs": ["__NEXT_DATA__", "_next/data", "_next/static"],
    "nuxt": ["__NUXT__", "_nuxt"],
    "remix": ["__remix", "remix"],
}

DYNAMIC_CONTENT_INDICATORS = [
    "loading...", "please enable javascript", "you need to enable javascript",
    "javascript is required", "enable javascript to view",
    "noscript", "javascript-disabled",
]

INFINITE_SCROLL_SELECTORS = [
    "[data-infinite-scroll]", "[data-load-more]", "[data-next-page]",
    ".infinite-scroll", ".load-more", "[data-offset]",
    "[data-page]", ".pagination-next", "a[rel='next']",
]

AJAX_ENDPOINT_PATTERNS = [
    r'fetch\(["\']([^"\']+)["\']',
    r'axios\.[a-z]+\(["\']([^"\']+)["\']',
    r'\$\.ajax\({[^}]*url:\s*["\']([^"\']+)["\']',
    r'\$\.get\(["\']([^"\']+)["\']',
    r'\$\.post\(["\']([^"\']+)["\']',
    r'XMLHttpRequest.*?open\([^,]+,\s*["\']([^"\']+)["\']',
    r'new\s+Request\(["\']([^"\']+)["\']',
]


@dataclass
class RenderedPage:
    url: str
    html: str
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)
    rendered_content: str = ""
    is_spa: bool = False
    spa_framework: str = ""
    has_infinite_scroll: bool = False
    ajax_endpoints: list[str] = field(default_factory=list)
    lazy_loaded_elements: int = 0
    shadow_dom_elements: int = 0
    total_dom_nodes: int = 0
    render_time_ms: int = 0
    render_strategy: str = "static"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "is_spa": self.is_spa,
            "spa_framework": self.spa_framework,
            "has_infinite_scroll": self.has_infinite_scroll,
            "ajax_endpoints_count": len(self.ajax_endpoints),
            "lazy_loaded_elements": self.lazy_loaded_elements,
            "total_dom_nodes": self.total_dom_nodes,
            "render_time_ms": self.render_time_ms,
            "render_strategy": self.render_strategy,
        }


class JsRenderedScraper:
    TIMEOUT = 45
    MAX_SIZE = 25 * 1024 * 1024
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

    def __init__(self, proxy: str = None):
        self.proxy = proxy

    def _detect_spa(self, html: str, headers: dict) -> tuple[bool, str]:
        for framework, indicators in SPA_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator.lower() in html.lower():
                    return True, framework
        server = headers.get("server", "").lower()
        x_powered = headers.get("x-powered-by", "").lower()
        if "next" in server or "next" in x_powered:
            return True, "nextjs"
        if "nuxt" in server or "nuxt" in x_powered:
            return True, "nuxt"
        return False, ""

    def _detect_infinite_scroll(self, html: str) -> bool:
        for selector in INFINITE_SCROLL_SELECTORS:
            if selector.lower() in html.lower():
                return True
        if re.search(r'infinite.?scroll|load.?more|scroll.?load', html, re.I):
            return True
        return False

    def _detect_ajax_endpoints(self, html: str) -> list[str]:
        endpoints = []
        seen = set()
        for pattern in AJAX_ENDPOINT_PATTERNS:
            for match in re.finditer(pattern, html):
                url = match.group(1) if match.lastindex else match.group(0)
                url = url.strip("'\"")
                if url and url not in seen and len(url) < 500:
                    seen.add(url)
                    endpoints.append(url)
        return endpoints[:30]

    def _count_lazy_elements(self, html: str) -> int:
        soup = BeautifulSoup(html, "lxml")
        lazy = soup.find_all("img", {"loading": "lazy"})
        lazy += soup.find_all(attrs={"data-src": True})
        lazy += soup.find_all(attrs={"data-lazy": True})
        lazy += soup.find_all(class_=re.compile(r"lazy|defer|delayed", re.I))
        count = len(lazy)
        soup.decompose()
        return count

    def _needs_js_rendering(self, html: str) -> bool:
        html_lower = html.lower()
        for indicator in DYNAMIC_CONTENT_INDICATORS:
            if indicator in html_lower:
                return True
        soup = BeautifulSoup(html, "lxml")
        body = soup.find("body")
        if body:
            text = body.get_text(strip=True)
            if len(text) < 100:
                return True
        noscript_tags = soup.find_all("noscript")
        if len(noscript_tags) > 3:
            return True
        return False

    def _extract_api_from_network(self, html: str, scripts: list[str]) -> list[dict]:
        endpoints = []
        seen = set()
        for script in scripts:
            for pattern in AJAX_ENDPOINT_PATTERNS:
                for match in re.finditer(pattern, script):
                    url = match.group(1) if match.lastindex else match.group(0)
                    url = url.strip("'\"")
                    if url and url not in seen and len(url) < 500:
                        seen.add(url)
                        method = "GET"
                        if "post" in match.group(0).lower():
                            method = "POST"
                        elif "put" in match.group(0).lower():
                            method = "PUT"
                        elif "delete" in match.group(0).lower():
                            method = "DELETE"
                        endpoints.append({"url": url, "method": method, "source": "script"})
        return endpoints

    def _extract_inline_data(self, html: str) -> list[dict]:
        data = []
        patterns = [
            (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', "initial_state"),
            (r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', "preloaded_state"),
            (r'window\.__DATA__\s*=\s*({.*?});', "data"),
            (r'window\.pageData\s*=\s*({.*?});', "page_data"),
            (r'var\s+data\s*=\s*({.*?});', "var_data"),
            (r'"props":\s*({.*?})\s*[,}]', "next_props"),
            (r'"pageProps":\s*({.*?})\s*[,}]', "next_page_props"),
        ]
        for pattern, name in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches[:3]:
                try:
                    parsed = json.loads(match)
                    data.append({"name": name, "data": parsed, "size": len(match)})
                except json.JSONDecodeError:
                    data.append({"name": name, "raw": match[:500], "size": len(match)})
        return data

    def _extract_shadow_dom_hosts(self, html: str) -> list[str]:
        hosts = []
        patterns = [
            r'customElements\.define\(["\']([^"\']+)["\']',
            r'class\s+\w+\s+extends\s+HTMLElement',
            r'attachShadow\(',
            r'shadowRoot',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, html):
                hosts.append(match.group(0)[:100])
        return list(set(hosts))[:20]

    async def scrape(self, url: str) -> RenderedPage:
        start = datetime.now()
        html = None
        resp_status = 200
        resp_headers = {}
        resp = None  # keep in scope for RenderedPage construction

        # Try httpx first
        try:
            transport = None
            if self.proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self.proxy)

            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            }

            async with httpx.AsyncClient(
                timeout=self.TIMEOUT, follow_redirects=True, headers=headers,
                limits=httpx.Limits(max_connections=5),
                transport=transport,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
                resp_status = resp.status_code
                resp_headers = dict(resp.headers)
        except Exception as e:
            logger.warning(f"httpx failed for {url}: {e}, trying curl_cffi")

        # Fallback: curl_cffi
        if html is None:
            try:
                from curl_cffi import requests as curl_requests
                curl_resp = curl_requests.get(
                    url, impersonate="chrome", timeout=self.TIMEOUT, allow_redirects=True
                )
                curl_resp.raise_for_status()
                html = curl_resp.text
                resp_status = curl_resp.status_code
                resp_headers = dict(curl_resp.headers)
                resp = None  # httpx resp is not available; use resp_status below
            except Exception as e2:
                logger.warning(f"curl_cffi also failed for {url}: {e2}")
                raise

        if len(html.encode("utf-8")) > self.MAX_SIZE:
            raise ValueError(f"Page too large: {len(html.encode('utf-8')) // 1024}KB")

        is_spa, framework = self._detect_spa(html, resp_headers)
        has_scroll = self._detect_infinite_scroll(html)
        ajax_eps = self._detect_ajax_endpoints(html)
        lazy_count = self._count_lazy_elements(html)
        needs_js = self._needs_js_rendering(html)

        scripts = []
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script"):
            if script.string:
                scripts.append(script.string)
        script_ajax = self._extract_api_from_network(html, scripts)
        ajax_eps.extend([e["url"] for e in script_ajax if e["url"] not in ajax_eps])

        inline_data = self._extract_inline_data(html)
        shadow_hosts = self._extract_shadow_dom_hosts(html)

        dom_nodes = len(soup.find_all(True))

        render_strategy = "static"
        if needs_js:
            render_strategy = "needs_js_rendering"
        if is_spa:
            render_strategy = "spa"
        if has_scroll:
            render_strategy = "infinite_scroll"

        elapsed = int((datetime.now() - start).total_seconds() * 1000)

        return RenderedPage(
            url=url, html=html, status_code=resp.status_code,
            headers=resp_headers, is_spa=is_spa, spa_framework=framework,
            has_infinite_scroll=has_scroll, ajax_endpoints=ajax_eps,
            lazy_loaded_elements=lazy_count, total_dom_nodes=dom_nodes,
            render_time_ms=elapsed, render_strategy=render_strategy,
        )

    async def scrape_with_selenium(self, url: str, wait_seconds: int = 3) -> RenderedPage:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={self.USER_AGENT}")
            if self.proxy:
                options.add_argument(f"--proxy-server={self.proxy}")

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.TIMEOUT)

            start = datetime.now()
            driver.get(url)
            WebDriverWait(driver, wait_seconds).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            html = driver.page_source
            title = driver.title
            current_url = driver.current_url
            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}

            script_ajax = []
            try:
                logs = driver.get_log("performance")
                for log in logs:
                    try:
                        msg = json.loads(log["message"])["message"]
                        if msg["method"] == "Network.requestWillBeSent":
                            req_url = msg["params"]["request"]["url"]
                            if "/api/" in req_url or "ajax" in req_url.lower():
                                script_ajax.append(req_url)
                    except Exception:
                        pass
            except Exception:
                pass

            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            driver.quit()

            soup = BeautifulSoup(html, "lxml")
            is_spa, framework = self._detect_spa(html, {})
            dom_nodes = len(soup.find_all(True))

            return RenderedPage(
                url=current_url or url, html=html, status_code=200,
                cookies=cookies, is_spa=is_spa, spa_framework=framework,
                ajax_endpoints=list(set(script_ajax))[:30],
                total_dom_nodes=dom_nodes, render_time_ms=elapsed,
                render_strategy="selenium",
            )

        except ImportError:
            logger.warning("Selenium not installed, falling back to httpx")
            return await self.scrape(url)
        except Exception as e:
            logger.warning(f"Selenium scrape failed: {e}, falling back to httpx")
            return await self.scrape(url)

    async def smart_scrape(self, url: str, use_selenium: bool = False) -> RenderedPage:
        if use_selenium:
            return await self.scrape_with_selenium(url)
        page = await self.scrape(url)
        if page.render_strategy == "needs_js_rendering":
            logger.info(f"Page needs JS rendering, trying Selenium for {url}")
            return await self.scrape_with_selenium(url)
        return page
