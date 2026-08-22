"""MultiScraper — Parallel scraping, multi-URL, proxy rotation, retry logic, batch processing."""
import asyncio
import logging
import random
import time
from typing import Optional
from dataclasses import dataclass, field

from app.services.scraper.html_scraper import HtmlScraper, ScrapeResult
from app.services.scraper.shared import USER_AGENTS

logger = logging.getLogger(__name__)


@dataclass
class ScrapeTask:
    url: str
    extract_tables: bool = True
    extract_lists: bool = True
    strategy: str = "auto"
    priority: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ScrapeTaskResult:
    url: str
    success: bool
    result: Optional[ScrapeResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    duration_ms: int = 0
    proxy_used: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "success": self.success,
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "proxy_used": self.proxy_used,
            "row_count": self.result.row_count if self.result else 0,
            "title": self.result.title if self.result else "",
        }


@dataclass
class BatchScrapeResult:
    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    results: list[ScrapeTaskResult] = field(default_factory=list)
    combined_tables: list[dict] = field(default_factory=list)
    combined_text_blocks: list[list[str]] = field(default_factory=list)
    total_rows: int = 0
    total_duration_ms: int = 0
    errors: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "total_urls": self.total_urls,
            "successful": self.successful,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "combined_tables_count": len(self.combined_tables),
            "combined_text_blocks_count": len(self.combined_text_blocks),
            "total_rows": self.total_rows,
            "total_duration_ms": self.total_duration_ms,
            "errors": self.errors,
            "summary": self.summary,
        }


class MultiScraper:

    def __init__(self, proxies: list[str] = None, max_concurrent: int = 5):
        self.proxies = proxies or []
        self.max_concurrent = max_concurrent
        self._proxy_index = 0
        self._rate_limit_delay = 1.0
        self._last_request_time = 0.0
        self._rate_lock = asyncio.Lock()

    def _get_next_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self._proxy_index % len(self.proxies)]
        self._proxy_index += 1
        return proxy

    def _get_random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    async def _rate_limit(self):
        async with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - elapsed)
            self._last_request_time = time.time()

    async def scrape_single(self, task: ScrapeTask, max_retries: int = 3) -> ScrapeTaskResult:
        task_result = ScrapeTaskResult(url=task.url, success=False)
        start = time.time()

        for attempt in range(max_retries + 1):
            proxy = self._get_next_proxy()
            task_result.proxy_used = proxy
            task_result.retry_count = attempt
            ua = self._get_random_ua()

            try:
                await self._rate_limit()
                scraper = HtmlScraper(proxy=proxy, user_agent=ua)
                result = await scraper.scrape(
                    url=task.url,
                    extract_tables=task.extract_tables,
                    extract_lists=task.extract_lists,
                    strategy=task.strategy,
                )
                task_result.result = result
                task_result.success = True
                task_result.duration_ms = int((time.time() - start) * 1000)
                return task_result

            except Exception as e:
                error_msg = str(e)
                task_result.error = error_msg
                logger.warning(f"Scrape attempt {attempt + 1} failed for {task.url}: {error_msg}")

                if attempt < max_retries:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)

        task_result.duration_ms = int((time.time() - start) * 1000)
        return task_result

    async def scrape_batch(self, urls: list[str], extract_tables: bool = True,
                           extract_lists: bool = True, max_retries: int = 3) -> BatchScrapeResult:
        batch_result = BatchScrapeResult(total_urls=len(urls))
        start = time.time()

        tasks = [
            ScrapeTask(url=url, extract_tables=extract_tables, extract_lists=extract_lists)
            for url in urls
        ]

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _limited_scrape(task):
            async with semaphore:
                return await self.scrape_single(task, max_retries=max_retries)

        results = await asyncio.gather(*[_limited_scrape(t) for t in tasks], return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                batch_result.results.append(ScrapeTaskResult(
                    url=urls[i], success=False, error=str(res)
                ))
                batch_result.errors.append(f"{urls[i]}: {str(res)}")
            else:
                batch_result.results.append(res)
                if res.success and res.result:
                    batch_result.successful += 1
                    batch_result.combined_tables.extend(res.result.tables)
                    batch_result.combined_text_blocks.extend(res.result.text_blocks)
                    batch_result.total_rows += res.result.row_count
                else:
                    batch_result.failed += 1
                    if res.error:
                        batch_result.errors.append(f"{urls[i]}: {res.error}")

        batch_result.total_duration_ms = int((time.time() - start) * 1000)
        batch_result.summary = (
            f"Scraped {batch_result.total_urls} URLs: "
            f"{batch_result.successful} succeeded, {batch_result.failed} failed. "
            f"Total rows: {batch_result.total_rows}. "
            f"Duration: {batch_result.total_duration_ms}ms."
        )
        return batch_result

    async def scrape_with_recursive_links(self, start_url: str, max_depth: int = 2,
                                          max_pages: int = 10) -> BatchScrapeResult:
        scraper = HtmlScraper(user_agent=self._get_random_ua())
        results_list = await scraper.scrape_recursive(
            url=start_url, max_depth=max_depth, max_pages=max_pages
        )

        batch_result = BatchScrapeResult(total_urls=len(results_list))
        for result in results_list:
            task_res = ScrapeTaskResult(url=result.url, success=True, result=result)
            batch_result.results.append(task_res)
            batch_result.successful += 1
            batch_result.combined_tables.extend(result.tables)
            batch_result.combined_text_blocks.extend(result.text_blocks)
            batch_result.total_rows += result.row_count
        batch_result.summary = (
            f"Recursive scrape from {start_url}: {batch_result.successful} pages, "
            f"{batch_result.total_rows} total rows."
        )
        return batch_result

    async def scrape_sitemap(self, sitemap_url: str, limit: int = 50) -> BatchScrapeResult:
        scraper = HtmlScraper(user_agent=self._get_random_ua())
        urls = await scraper.parse_sitemap(sitemap_url, limit=limit)
        if not urls:
            batch_result = BatchScrapeResult()
            batch_result.summary = "No URLs found in sitemap."
            return batch_result
        return await self.scrape_batch(urls[:limit])

    async def scrape_feeds(self, feed_urls: list[str]) -> BatchScrapeResult:
        return await self.scrape_batch(feed_urls, extract_tables=False, extract_lists=True)

    async def discover_and_scrape(self, url: str, max_pages: int = 20) -> BatchScrapeResult:
        from urllib.parse import urlparse as _urlparse
        scraper = HtmlScraper(user_agent=self._get_random_ua())
        discovered_urls = set()

        try:
            result = await scraper.scrape(url)
            internal_domain = _urlparse(url).netloc
            for link in result.links:
                parsed = _urlparse(link)
                if parsed.netloc == internal_domain:
                    discovered_urls.add(link)
        except Exception as e:
            logger.warning(f"Discovery scrape failed for {url}: {e}")

        sitemaps = await scraper.discover_sitemaps(url)
        for sm in sitemaps[:3]:
            try:
                sm_urls = await scraper.parse_sitemap(sm, limit=20)
                discovered_urls.update(sm_urls[:20])
            except Exception:
                pass

        all_urls = [url] + list(discovered_urls)[:max_pages - 1]
        return await self.scrape_batch(all_urls[:max_pages])
