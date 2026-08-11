"""Rate Limiter & Politeness — Per-domain delay, robots.txt respect, crawl delays."""
import re
import time
import asyncio
import random
import logging
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CrawlDelayConfig:
    default_delay_ms: int = 1000
    respect_robots_txt: bool = True
    per_domain_delay_ms: dict = field(default_factory=dict)


@dataclass
class DomainConfig:
    domain: str
    crawl_delay: float = 1.0
    max_concurrent: int = 2
    respect_robots: bool = True
    robots_rules: dict = field(default_factory=dict)
    last_request_time: float = 0.0
    request_count: int = 0
    error_count: int = 0
    blocked: bool = False
    blocked_until: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "crawl_delay": self.crawl_delay,
            "max_concurrent": self.max_concurrent,
            "respect_robots": self.respect_robots,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "blocked": self.blocked,
        }


@dataclass
class RateLimitStats:
    total_requests: int = 0
    total_blocked: int = 0
    total_robots_blocked: int = 0
    domains: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "total_robots_blocked": self.total_robots_blocked,
            "domain_count": len(self.domains),
            "domains": self.domains,
        }


class RateLimiter:

    def __init__(self, default_delay: float = 1.0, max_per_domain: int = 10):
        self.default_delay = default_delay
        self.max_per_domain = max_per_domain
        self._domains: Dict[str, DomainConfig] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._stats = RateLimitStats()
        self._blocked_ips: Dict[str, float] = {}
        self._global_delay = 0.0

    def configure(self, config: CrawlDelayConfig):
        self.default_delay = config.default_delay_ms / 1000.0
        for domain, delay_ms in config.per_domain_delay_ms.items():
            self.set_crawl_delay(domain, delay_ms / 1000.0)

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    async def fetch_robots(self, url: str) -> dict:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    return self._parse_robots(resp.text)
        except Exception:
            pass
        # Fallback: curl_cffi (run sync call off the event loop)
        try:
            from curl_cffi import requests as curl_requests
            resp = await asyncio.to_thread(
                curl_requests.get, robots_url, impersonate="chrome", timeout=10
            )
            if resp.status_code == 200:
                return self._parse_robots(resp.text)
        except Exception:
            pass
        return {}

    def _parse_robots(self, text: str) -> dict:
        rules = {"disallow": [], "allow": [], "crawl_delay": 1.0, "sitemap": []}
        current_agent = "*"
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path and current_agent in ("*", ""):
                    rules["disallow"].append(path)
            elif line.lower().startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                if path and current_agent in ("*", ""):
                    rules["allow"].append(path)
            elif line.lower().startswith("crawl-delay:"):
                try:
                    delay = float(line.split(":", 1)[1].strip())
                    if current_agent in ("*", ""):
                        rules["crawl_delay"] = delay
                except ValueError:
                    pass
            elif line.lower().startswith("sitemap:"):
                sitemap = line.split(":", 1)[1].strip()
                rules["sitemap"].append(sitemap)
        return rules

    def _is_allowed(self, url: str, domain_config: DomainConfig) -> bool:
        if not domain_config.respect_robots or not domain_config.robots_rules:
            return True
        parsed = urlparse(url)
        path = parsed.path
        for disallow in domain_config.robots_rules.get("disallow", []):
            if path.startswith(disallow):
                return False
        for allow in domain_config.robots_rules.get("allow", []):
            if path.startswith(allow):
                return True
        return True

    async def acquire(self, url: str) -> bool:
        domain = self._get_domain(url)
        if domain not in self._domains:
            self._domains[domain] = DomainConfig(domain=domain, crawl_delay=self.default_delay)
        config = self._domains[domain]

        if config.blocked:
            if config.blocked_until and time.time() < config.blocked_until:
                self._stats.total_blocked += 1
                return False
            config.blocked = False

        if not self._is_allowed(url, config):
            self._stats.total_robots_blocked += 1
            logger.debug(f"Blocked by robots.txt: {url}")
            return False

        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(config.max_concurrent)

        await self._semaphores[domain].acquire()

        elapsed = time.time() - config.last_request_time
        if elapsed < config.crawl_delay:
            await asyncio.sleep(config.crawl_delay - elapsed)

        config.last_request_time = time.time()
        config.request_count += 1
        self._stats.total_requests += 1

        return True

    def release(self, url: str):
        domain = self._get_domain(url)
        if domain in self._semaphores:
            self._semaphores[domain].release()

    def record_error(self, url: str, status_code: int = 0):
        domain = self._get_domain(url)
        if domain in self._domains:
            config = self._domains[domain]
            config.error_count += 1
            if status_code == 429:
                config.crawl_delay = min(config.crawl_delay * 2, 60)
                logger.warning(f"Rate limited on {domain}, delay increased to {config.crawl_delay}s")
            elif status_code == 403:
                config.error_count += 5
                if config.error_count > 10:
                    config.blocked = True
                    config.blocked_until = time.time() + 3600
                    logger.warning(f"Blocked on {domain} for 1 hour due to repeated 403s")

    def set_crawl_delay(self, domain: str, delay: float):
        if domain not in self._domains:
            self._domains[domain] = DomainConfig(domain=domain)
        self._domains[domain].crawl_delay = max(delay, 0.1)

    def get_stats(self) -> dict:
        self._stats.domains = {d: c.to_dict() for d, c in self._domains.items()}
        return self._stats.to_dict()

    async def smart_delay(self, url: str):
        domain = self._get_domain(url)
        config = self._domains.get(domain)
        if config:
            base_delay = config.crawl_delay
            jitter = base_delay * 0.3
            delay = base_delay + random.uniform(-jitter, jitter)
            await asyncio.sleep(max(delay, 0.1))
