"""Target Scrapers — Specialized scrapers for E-commerce, News, Financial, Academic, Job, Real Estate."""
import re
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ScrapeTargetResult:
    source: str = ""
    target_type: str = ""
    items_found: int = 0
    items: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source, "target_type": self.target_type,
            "items_found": self.items_found,
            "items": self.items[:100],
            "errors": self.errors[:20],
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
        }


class BaseTargetScraper:
    """Base class for target scrapers with shared HTTP client."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        import asyncio
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
                    },
                )
            return self._client

    async def _fetch(self, url: str) -> httpx.Response:
        """Fetch URL with httpx, fallback to curl_cffi on 403/406/429."""
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in (403, 406, 429):
                raise
            logger.warning(f"httpx got {e.response.status_code} for {url}, trying curl_cffi")
        except Exception as e:
            logger.warning(f"httpx failed for {url}: {e}, trying curl_cffi")

        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(url, impersonate="chrome", timeout=30, allow_redirects=True)
            resp.raise_for_status()
            # Return a duck-typed response compatible with callers expecting .text
            return resp
        except Exception as e2:
            logger.warning(f"curl_cffi also failed for {url}: {e2}")
            raise

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class EcommerceScraper(BaseTargetScraper):

    async def scrape_product_page(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="ecommerce")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            product = {}

            title_el = soup.select_one("h1, [data-testid='product-title'], .product-title, .product_name")
            product["title"] = title_el.get_text(strip=True) if title_el else ""

            price_el = soup.select_one("[data-testid='price'], .price, .product-price, [itemprop='price']")
            product["price"] = price_el.get_text(strip=True) if price_el else ""
            if price_el and price_el.get("content"):
                product["price_raw"] = price_el["content"]

            desc_el = soup.select_one("[data-testid='description'], .description, .product-description, [itemprop='description']")
            product["description"] = desc_el.get_text(strip=True)[:500] if desc_el else ""

            img_el = soup.select_one("[data-testid='product-image'] img, .product-image img, [itemprop='image']")
            product["image_url"] = img_el.get("src", "") if img_el else ""

            rating_el = soup.select_one("[data-testid='rating'], .rating, .stars, [itemprop='ratingValue']")
            product["rating"] = rating_el.get_text(strip=True) if rating_el else ""

            review_el = soup.select_one("[data-testid='review-count'], .review-count, [itemprop='reviewCount']")
            product["review_count"] = review_el.get_text(strip=True) if review_el else ""

            sku_el = soup.select_one("[itemprop='sku'], .sku, [data-testid='sku']")
            product["sku"] = sku_el.get_text(strip=True) if sku_el else ""

            avail_el = soup.select_one("[itemprop='availability'], .availability, .stock")
            product["availability"] = avail_el.get_text(strip=True) if avail_el else ""

            brand_el = soup.select_one("[itemprop='brand'], .brand, .product-brand")
            product["brand"] = brand_el.get_text(strip=True) if brand_el else ""

            specs = {}
            for row in soup.select(".spec-row, .specification-row, tr, dt, dl"):
                label = row.select_one("td:first-child, dt, th, .spec-label")
                value = row.select_one("td:last-child, dd, .spec-value")
                if label and value:
                    specs[label.get_text(strip=True)] = value.get_text(strip=True)
            product["specifications"] = specs

            json_ld = soup.select('script[type="application/ld+json"]')
            for script in json_ld:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "Product":
                        product["json_ld"] = data
                        break
                except Exception:
                    pass

            breadcrumbs = [a.get_text(strip=True) for a in soup.select(".breadcrumb a, nav[aria-label='breadcrumb'] a")]
            product["breadcrumbs"] = breadcrumbs

            result.items = [product]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Product: {result.items[0].get('title', 'N/A')[:50]}" if result.items else "Product: N/A"
        return result

    async def scrape_search_results(self, url: str, max_items: int = 50) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="ecommerce_search")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            items = []
            selectors = [
                ".product-card", ".product-item", "[data-testid='product']",
                ".search-result-item", ".item", "article",
            ]
            for sel in selectors:
                cards = soup.select(sel)[:max_items]
                if len(cards) >= 3:
                    for card in cards:
                        item = {}
                        title_el = card.select_one("h2, h3, .title, .product-name, a")
                        item["title"] = title_el.get_text(strip=True)[:200] if title_el else ""
                        price_el = card.select_one(".price, .product-price, [data-testid='price']")
                        item["price"] = price_el.get_text(strip=True) if price_el else ""
                        link_el = card.select_one("a[href]")
                        item["url"] = link_el.get("href", "") if link_el else ""
                        img_el = card.select_one("img")
                        item["image_url"] = img_el.get("src", "") if img_el else ""
                        if item.get("title"):
                            items.append(item)
                    break

            result.items = items[:max_items]
            result.items_found = len(result.items)
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Found {result.items_found} products"
        return result


class NewsScraper(BaseTargetScraper):

    async def scrape_article(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="news_article")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            article = {}

            title_el = soup.select_one("h1, .headline, .article-title, [itemprop='headline']")
            article["title"] = title_el.get_text(strip=True) if title_el else ""

            author_el = soup.select_one("[itemprop='author'], .author, .byline, .author-name")
            article["author"] = author_el.get_text(strip=True) if author_el else ""

            date_el = soup.select_one("time, [itemprop='datePublished'], .date, .publish-date")
            article["date"] = date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""

            desc_el = soup.select_one("[itemprop='description'], .summary, .lead, meta[name='description']")
            article["description"] = ""
            if desc_el:
                article["description"] = desc_el.get("content", desc_el.get_text(strip=True))[:500]

            body_parts = soup.select("article p, .article-body p, .content p, [itemprop='articleBody'] p")
            article["body"] = " ".join(p.get_text(strip=True) for p in body_parts[:20])[:2000]

            img_el = soup.select_one("article img, .article-image img, [itemprop='image']")
            article["image_url"] = img_el.get("src", "") if img_el else ""

            tags = [a.get_text(strip=True) for a in soup.select(".tag, .category, [rel='tag']")]
            article["tags"] = tags[:10]

            source_el = soup.select_one(".source, .publisher, [itemprop='publisher']")
            article["source"] = source_el.get_text(strip=True) if source_el else ""

            result.items = [article]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Article: {result.items[0].get('title', 'N/A')[:50]}" if result.items else "Article: N/A"
        return result

    async def scrape_feed(self, url: str, max_items: int = 30) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="news_feed")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            items = []
            for item in soup.select("item, entry")[:max_items]:
                entry = {}
                title_el = item.select_one("title")
                entry["title"] = title_el.get_text(strip=True) if title_el else ""
                link_el = item.select_one("link")
                entry["url"] = link_el.get_text(strip=True) if link_el else (link_el.get("href", "") if link_el else "")
                desc_el = item.select_one("description, summary, content")
                entry["description"] = desc_el.get_text(strip=True)[:500] if desc_el else ""
                pub_el = item.select_one("pubDate, published, updated")
                entry["date"] = pub_el.get_text(strip=True) if pub_el else ""
                author_el = item.select_one("author, creator")
                entry["author"] = author_el.get_text(strip=True) if author_el else ""
                items.append(entry)

            result.items = items
            result.items_found = len(items)
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Feed: {result.items_found} articles"
        return result


class FinancialScraper(BaseTargetScraper):

    async def scrape_stock(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="financial")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            stock = {}

            name_el = soup.select_one("h1, .company-name, .stock-name")
            stock["company"] = name_el.get_text(strip=True) if name_el else ""

            price_el = soup.select_one("[data-field='regularMarketPrice'], .price, .current-price")
            stock["price"] = price_el.get_text(strip=True) if price_el else ""

            change_el = soup.select_one("[data-field='regularMarketChange'], .change, .price-change")
            stock["change"] = change_el.get_text(strip=True) if change_el else ""

            cap_el = soup.select_one("[data-field='marketCap'], .market-cap")
            stock["market_cap"] = cap_el.get_text(strip=True) if cap_el else ""

            vol_el = soup.select_one("[data-field='regularMarketVolume'], .volume")
            stock["volume"] = vol_el.get_text(strip=True) if vol_el else ""

            tables = pd.read_html(resp.text)
            if tables:
                stock["data_tables"] = [t.head(10).to_dict(orient="records") for t in tables[:2]]

            result.items = [stock]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Stock: {result.items[0].get('company', 'N/A')}" if result.items else "Stock: N/A"
        return result


class AcademicScraper(BaseTargetScraper):

    async def scrape_paper(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="academic")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            paper = {}

            title_el = soup.select_one("h1, .paper-title, .title, [itemprop='name']")
            paper["title"] = title_el.get_text(strip=True) if title_el else ""

            authors = [a.get_text(strip=True) for a in soup.select(".author-name, [itemprop='author'], .author")]
            paper["authors"] = authors

            abstract_el = soup.select_one(".abstract, [itemprop='description'], #abstract")
            paper["abstract"] = abstract_el.get_text(strip=True)[:1000] if abstract_el else ""

            date_el = soup.select_one("time, .pub-date, .publication-date")
            paper["date"] = date_el.get_text(strip=True) if date_el else ""

            doi_el = soup.select_one("[itemprop='doi'], .doi, a[href*='doi.org']")
            paper["doi"] = doi_el.get_text(strip=True) if doi_el else ""

            journal_el = soup.select_one("[itemprop='journal'], .journal-name, .publication")
            paper["journal"] = journal_el.get_text(strip=True) if journal_el else ""

            keywords = [k.get_text(strip=True) for k in soup.select(".keyword, .tag, [itemprop='keywords']")]
            paper["keywords"] = keywords[:15]

            citations_el = soup.select_one(".citation-count, .cited-by")
            paper["citations"] = citations_el.get_text(strip=True) if citations_el else ""

            result.items = [paper]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Paper: {result.items[0].get('title', 'N/A')[:50]}" if result.items else "Paper: N/A"
        return result


class JobScraper(BaseTargetScraper):

    async def scrape_job_listing(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="job")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            job = {}

            title_el = soup.select_one("h1, .job-title, [itemprop='title']")
            job["title"] = title_el.get_text(strip=True) if title_el else ""

            company_el = soup.select_one("[itemprop='hiringOrganization'], .company-name, .employer")
            job["company"] = company_el.get_text(strip=True) if company_el else ""

            location_el = soup.select_one("[itemprop='jobLocation'], .location, .job-location")
            job["location"] = location_el.get_text(strip=True) if location_el else ""

            salary_el = soup.select_one("[itemprop='baseSalary'], .salary, .compensation")
            job["salary"] = salary_el.get_text(strip=True) if salary_el else ""

            desc_el = soup.select_one("[itemprop='description'], .job-description, .description")
            job["description"] = desc_el.get_text(strip=True)[:2000] if desc_el else ""

            date_el = soup.select_one("[itemprop='datePosted'], time, .post-date")
            job["posted_date"] = date_el.get_text(strip=True) if date_el else ""

            type_el = soup.select_one("[itemprop='employmentType'], .employment-type")
            job["employment_type"] = type_el.get_text(strip=True) if type_el else ""

            reqs = [r.get_text(strip=True) for r in soup.select(".requirement, .qualification, li")]
            job["requirements"] = reqs[:15]

            result.items = [job]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Job: {result.items[0].get('title', 'N/A')[:50]}" if result.items else "Job: N/A"
        return result


class RealEstateScraper(BaseTargetScraper):

    async def scrape_listing(self, url: str) -> ScrapeTargetResult:
        start = datetime.now()
        result = ScrapeTargetResult(source=url, target_type="real_estate")
        try:
            resp = await self._fetch(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            listing = {}

            title_el = soup.select_one("h1, .listing-title, .property-title")
            listing["title"] = title_el.get_text(strip=True) if title_el else ""

            price_el = soup.select_one("[itemprop='price'], .price, .listing-price")
            listing["price"] = price_el.get_text(strip=True) if price_el else ""

            addr_el = soup.select_one("[itemprop='address'], .address, .property-address")
            listing["address"] = addr_el.get_text(strip=True) if addr_el else ""

            beds_el = soup.select_one(".beds, .bedrooms, [data-testid='beds']")
            listing["bedrooms"] = beds_el.get_text(strip=True) if beds_el else ""

            baths_el = soup.select_one(".baths, .bathrooms, [data-testid='baths']")
            listing["bathrooms"] = baths_el.get_text(strip=True) if baths_el else ""

            sqft_el = soup.select_one(".sqft, .square-feet, [data-testid='sqft']")
            listing["sqft"] = sqft_el.get_text(strip=True) if sqft_el else ""

            desc_el = soup.select_one("[itemprop='description'], .description, .property-description")
            listing["description"] = desc_el.get_text(strip=True)[:1000] if desc_el else ""

            features = [f.get_text(strip=True) for f in soup.select(".feature, .amenity, .property-feature")]
            listing["features"] = features[:20]

            imgs = [img.get("src", "") for img in soup.select(".gallery img, .property-images img")]
            listing["images"] = imgs[:10]

            result.items = [listing]
            result.items_found = 1
        except Exception as e:
            result.errors.append(str(e))

        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Property: {result.items[0].get('title', 'N/A')[:50]}" if result.items else "Property: N/A"
        return result
