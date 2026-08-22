"""Playwright Scraper — Modern JS-rendered page scraping with Playwright.

Fallback chain: httpx (static) → curl_cffi (anti-detect) → Playwright (full JS)
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional, Dict, List, TYPE_CHECKING
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    try:
        from playwright.async_api import Browser, Page
    except ImportError:
        pass

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.info("Playwright not installed. Install with: pip install playwright && playwright install chromium")

from app.services.scraper.shared import USER_AGENTS


@dataclass
class PlaywrightScrapeResult:
    url: str = ""
    title: str = ""
    html: str = ""
    text: str = ""
    tables: List[Dict] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    console_errors: List[str] = field(default_factory=list)
    network_requests: List[Dict] = field(default_factory=list)
    screenshot_bytes: Optional[bytes] = None
    duration_ms: int = 0
    success: bool = False
    error: str = ""
    strategy: str = "playwright"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text_length": len(self.text),
            "tables_count": len(self.tables),
            "links_count": len(self.links),
            "images_count": len(self.images),
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "strategy": self.strategy,
        }


class PlaywrightScraper:
    """Playwright-based scraper for JS-rendered pages (SPAs, dynamic content)."""

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        timeout_ms: int = 30000,
        navigation_timeout_ms: int = 30000,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        proxy: Optional[str] = None,
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is required. Install with: "
                "pip install playwright && playwright install chromium"
            )
        self.headless = headless
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.navigation_timeout_ms = navigation_timeout_ms
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.proxy = proxy
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def _ensure_browser(self):
        """Lazily launch browser instance."""
        if self._browser and self._browser.is_connected():
            return self._browser

        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        }
        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(**launch_args)
        return self._browser

    async def _create_context(self):
        """Create a browser context with anti-detection settings."""
        browser = await self._ensure_browser()
        import random
        ua = random.choice(USER_AGENTS)

        context_args = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "user_agent": ua,
            "locale": "en-US",
            "timezone_id": "Asia/Jakarta",
            "bypass_csp": True,
            "java_script_enabled": True,
        }
        if self.proxy:
            context_args["proxy"] = {"server": self.proxy}

        context = await browser.new_context(**context_args)

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        return context

    async def scrape(
        self,
        url: str,
        wait_seconds: int = 3,
        wait_for_selector: Optional[str] = None,
        scroll: bool = False,
        max_scrolls: int = 5,
        capture_screenshot: bool = False,
        intercept_network: bool = False,
    ) -> PlaywrightScrapeResult:
        """Scrape a URL using Playwright with full JS rendering."""
        start = time.time()
        result = PlaywrightScrapeResult(url=url)

        context = None
        page = None
        try:
            context = await self._create_context()
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)

            console_errors = []
            network_requests = []

            page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)

            if intercept_network:
                page.on("request", lambda req: network_requests.append({
                    "url": req.url,
                    "method": req.method,
                    "resource_type": req.resource_type,
                }))

            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)

            if response:
                result.metadata["status_code"] = response.status
                result.metadata["content_type"] = response.headers.get("content-type", "")

            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=wait_seconds * 1000)
                except Exception:
                    logger.warning(f"Selector '{wait_for_selector}' not found within {wait_seconds}s")

            await asyncio.sleep(wait_seconds)

            if scroll:
                for _ in range(max_scrolls):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

            result.title = await page.title()
            result.html = await page.content()
            result.text = await page.inner_text("body")

            result.tables = await self._extract_tables(page)
            result.links = await self._extract_links(page)
            result.images = await self._extract_images(page)
            result.metadata.update(await self._extract_metadata(page))

            result.console_errors = console_errors
            result.network_requests = network_requests[:100]

            if capture_screenshot:
                result.screenshot_bytes = await page.screenshot(full_page=True)

            result.success = True

        except Exception as e:
            result.error = str(e)
            logger.error(f"Playwright scrape failed for {url}: {e}")
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

        result.duration_ms = int((time.time() - start) * 1000)
        return result

    async def _extract_tables(self, page: Page) -> List[Dict]:
        """Extract HTML tables from the page."""
        tables = []
        try:
            table_count = await page.locator("table").count()
            for i in range(min(table_count, 20)):
                table_el = page.locator("table").nth(i)
                rows = []
                headers = []

                header_els = table_el.locator("thead tr th, thead tr td")
                header_count = await header_els.count()
                for j in range(header_count):
                    text = await header_els.nth(j).inner_text()
                    headers.append(text.strip())

                if not headers:
                    first_row = table_el.locator("tr").first
                    cell_count = await first_row.locator("th, td").count()
                    for j in range(cell_count):
                        text = await first_row.locator("th, td").nth(j).inner_text()
                        headers.append(text.strip())

                body_rows = table_el.locator("tbody tr, tr")
                row_count = await body_rows.count()
                for r in range(1, min(row_count, 100)):
                    row = body_rows.nth(r)
                    cells = row.locator("td")
                    cell_count = await cells.count()
                    row_data = {}
                    for c in range(cell_count):
                        key = headers[c] if c < len(headers) else f"col_{c}"
                        row_data[key] = (await cells.nth(c).inner_text()).strip()
                    if any(row_data.values()):
                        rows.append(row_data)

                if rows:
                    tables.append({"headers": headers, "rows": rows[:500], "row_count": len(rows)})
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        return tables

    async def _extract_links(self, page: Page) -> List[str]:
        """Extract all links from the page."""
        links = []
        try:
            link_els = page.locator("a[href]")
            count = await link_els.count()
            for i in range(min(count, 500)):
                href = await link_els.nth(i).get_attribute("href")
                if href and href.startswith(("http://", "https://", "/")):
                    links.append(href)
        except Exception as e:
            logger.warning(f"Link extraction failed: {e}")
        return list(dict.fromkeys(links))

    async def _extract_images(self, page: Page) -> List[Dict]:
        """Extract images with metadata."""
        images = []
        try:
            img_els = page.locator("img")
            count = await img_els.count()
            for i in range(min(count, 100)):
                img = img_els.nth(i)
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                if src:
                    images.append({"src": src, "alt": alt})
        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")
        return images

    async def _extract_metadata(self, page: Page) -> Dict:
        """Extract page metadata (OG, meta tags, JSON-LD)."""
        metadata = {}
        try:
            metadata["og_title"] = await page.locator('meta[property="og:title"]').get_attribute("content") or ""
            metadata["og_description"] = await page.locator('meta[property="og:description"]').get_attribute("content") or ""
            metadata["og_image"] = await page.locator('meta[property="og:image"]').get_attribute("content") or ""
            metadata["description"] = await page.locator('meta[name="description"]').get_attribute("content") or ""
            metadata["keywords"] = await page.locator('meta[name="keywords"]').get_attribute("content") or ""

            json_ld_els = page.locator('script[type="application/ld+json"]')
            json_ld_count = await json_ld_els.count()
            json_ld_list = []
            for i in range(min(json_ld_count, 5)):
                try:
                    import json
                    content = await json_ld_els.nth(i).inner_text()
                    data = json.loads(content)
                    json_ld_list.append(data)
                except Exception:
                    pass
            if json_ld_list:
                metadata["json_ld"] = json_ld_list

            metadata["word_count"] = len((await page.inner_text("body")).split())
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
        return metadata

    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
