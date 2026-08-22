"""Ultra Scraping API — Auth, CAPTCHA, fingerprint, rate limit, diff, webhooks,
distributed, validation, AutoML, anomaly, forecast, cluster, dim reduce,
feature engineering, enrichment, target scrapers."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, Field
import pandas as pd

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.scraper.auth_scraper import AuthenticatedScraper, AuthConfig
from app.services.scraper.captcha_solver import CaptchaSolver
from app.services.scraper.rate_limiter import RateLimiter, CrawlDelayConfig
from app.services.scraper.fingerprint import FingerprintGenerator
from app.services.scraper.webhook_notifier import WebhookNotifier
from app.services.scraper.scrape_diff import ScrapeDiff
from app.services.scraper.distributed_scraper import DistributedScraper
from app.services.scraper.data_validator import DataValidator, ValidationRule
from app.services.scraper.automl import AutoMLRecommender
from app.services.scraper.anomaly_detector import AnomalyDetector
from app.services.scraper.forecaster import Forecaster
from app.services.scraper.clusterer import AutoClusterer
from app.services.scraper.dim_reducer import DimReducer
from app.services.scraper.feature_engineer import FeatureEngineer
from app.services.scraper.data_enricher import DataEnricher
from app.services.scraper.target_scrapers import (
    EcommerceScraper, NewsScraper, FinancialScraper,
    AcademicScraper, JobScraper, RealEstateScraper,
)
from app.services.scraper.shared import get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraping", tags=["Ultra Scraping"])

auth_scraper = AuthenticatedScraper()
captcha_solver = CaptchaSolver()
rate_limiter = RateLimiter()
fingerprint_gen = FingerprintGenerator()
webhook_notifier = WebhookNotifier()
scrape_diff = ScrapeDiff()
distributed = DistributedScraper()
validator = DataValidator()
automl = AutoMLRecommender()
anomaly_detector = AnomalyDetector()
forecaster = Forecaster()
clusterer = AutoClusterer()
dim_reducer = DimReducer()
feature_engineer = FeatureEngineer()
enricher = DataEnricher()
ecommerce = EcommerceScraper()
news_scraper = NewsScraper()
financial = FinancialScraper()
academic = AcademicScraper()
job_scraper = JobScraper()
real_estate = RealEstateScraper()


async def _get_job_data(db, job_id, user_id):
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found or no data")
    return pd.DataFrame(row[0])


class AuthScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5)
    login_url: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")
    auth_type: str = Field(default="session")
    api_key: str = Field(default="")
    api_header: str = Field(default="Authorization")
    max_pages: int = Field(default=1, ge=1, le=50)


class FingerprintScrapeRequest(BaseModel):
    url: str
    rotate: bool = Field(default=True)
    use_selenium: bool = Field(default=False)


class DiffRequest(BaseModel):
    job_id_old: str
    job_id_new: str
    key_columns: Optional[List[str]] = None


class WebhookConfigRequest(BaseModel):
    name: str
    webhook_urls: List[str] = Field(default=[])
    slack_webhook: str = Field(default="")
    discord_webhook: str = Field(default="")
    events: List[str] = Field(default=["completed", "failed"])
    include_data: bool = Field(default=False)


class DistributedRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1)
    strategy: str = Field(default="round_robin")
    max_per_worker: int = Field(default=10)
    proxies: List[str] = Field(default=[])


class ValidateRequest(BaseModel):
    job_id: str
    rules: Optional[List[dict]] = None
    remove_invalid: bool = Field(default=False)


class AutoMLRequest(BaseModel):
    job_id: str
    target_column: str
    task: Optional[str] = None
    max_models: int = Field(default=6, ge=2, le=10)


class AnomalyRequest(BaseModel):
    job_id: str
    method: str = Field(default="all")
    columns: Optional[List[str]] = None
    threshold: float = Field(default=3.0)


class ForecastRequest(BaseModel):
    job_id: str
    value_column: str
    time_column: Optional[str] = None
    periods: int = Field(default=10, ge=1, le=100)


class ClusterRequest(BaseModel):
    job_id: str
    method: str = Field(default="auto")
    n_clusters: Optional[int] = None


class DimReduceRequest(BaseModel):
    job_id: str
    method: str = Field(default="auto")
    n_components: int = Field(default=2, ge=2, le=50)


class FeatureEngRequest(BaseModel):
    job_id: str
    feature_types: List[str] = Field(default=["all"])


class EnrichRequest(BaseModel):
    job_id: str
    enrichments: List[str] = Field(default=["all"])


class TargetScrapeRequest(BaseModel):
    url: str
    target_type: str = Field(..., description="ecommerce, news, financial, academic, job, real_estate")


# ─── Auth Scraping ──────────────────────────────────────────────────────

@router.post("/auth-scrape")
async def auth_scrape(req: AuthScrapeRequest, user=Depends(get_current_user)):
    try:
        auth_config = AuthConfig(
            login_url=req.login_url, username=req.username, password=req.password,
            auth_type=req.auth_type, api_key=req.api_key, api_header=req.api_header,
        )
        if auth_config.login_url:
            session = await auth_scraper.login(auth_config)
        elif auth_config.api_key:
            session = await auth_scraper.api_key_auth(auth_config)
        else:
            session = await auth_scraper.session_auth(auth_config)

        if req.max_pages > 1:
            pages = await auth_scraper.scrape_multiple(session, [req.url], max_pages=req.max_pages)
            return {"pages_scraped": len(pages), "pages": [p.to_dict() for p in pages]}
        else:
            page = await auth_scraper.scrape(session, req.url)
            return page.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Fingerprint Rotation ───────────────────────────────────────────────

@router.post("/fingerprint-scrape")
async def fingerprint_scrape(req: FingerprintScrapeRequest, user=Depends(get_current_user)):
    try:
        fp = fingerprint_gen.generate()
        if req.use_selenium:
            from app.services.scraper.js_scraper import JsRenderedScraper
            js = JsRenderedScraper()
            page = await js.scrape_with_selenium(req.url)
        else:
            from app.services.scraper.html_scraper import HtmlScraper
            html_scraper = HtmlScraper()
            page = await html_scraper.scrape(req.url)
        return {
            "fingerprint": fp.to_dict(),
            "page": page.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fingerprint/generate")
async def generate_fingerprint(user=Depends(get_current_user)):
    fp = fingerprint_gen.generate()
    return fp.to_dict()


@router.post("/fingerprint/batch")
async def generate_fingerprints(count: int = Query(default=5, ge=1, le=20),
                                user=Depends(get_current_user)):
    fps = fingerprint_gen.generate_batch(count)
    return [fp.to_dict() for fp in fps]


# ─── Rate Limiting ──────────────────────────────────────────────────────

@router.post("/rate-limit/configure")
async def configure_rate_limit(
    domain: str, delay_ms: int = Body(default=1000, embed=True),
    respect_robots: bool = Body(default=True, embed=True),
    user=Depends(get_current_user),
):
    config = CrawlDelayConfig(
        default_delay_ms=delay_ms, respect_robots_txt=respect_robots,
        per_domain_delay_ms={domain: delay_ms},
    )
    rate_limiter.configure(config)
    return {"status": "configured", "domain": domain, "delay_ms": delay_ms}


@router.get("/rate-limit/stats")
async def rate_limit_stats(user=Depends(get_current_user)):
    return rate_limiter.get_stats()


# ─── Scrape Diff ────────────────────────────────────────────────────────

@router.post("/diff")
async def diff_scrapes(req: DiffRequest, db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    user_id = get_user_id(user)
    try:
        old_df = await _get_job_data(db, req.job_id_old, user_id)
        new_df = await _get_job_data(db, req.job_id_new, user_id)
        diff = scrape_diff.diff_dataframes(old_df, new_df, key_columns=req.key_columns)
        return diff.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Webhooks (DB-backed) ────────────────────────────────────────────────

@router.post("/webhooks/configure")
async def configure_webhook(
    req: WebhookConfigRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    notifier = WebhookNotifier(db)
    config = await notifier.configure(
        user_id=user_id, name=req.name, url=req.webhook_urls[0] if req.webhook_urls else "",
        webhook_type="generic", events=req.events, is_active=True,
    )
    return {"status": "configured", "config": config}


@router.get("/webhooks")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    notifier = WebhookNotifier(db)
    return await notifier.list_user_webhooks(user_id)


@router.post("/webhooks/test")
async def test_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    notifier = WebhookNotifier(db)
    result = await notifier.test_webhook(webhook_id)
    return result


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    notifier = WebhookNotifier(db)
    if not await notifier.delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}


# ─── Distributed Scraping ───────────────────────────────────────────────

@router.post("/distributed/create")
async def create_distributed_job(req: DistributedRequest, user=Depends(get_current_user)):
    distributed.set_proxies(req.proxies)
    job_id = distributed.create_job(req.urls, strategy=req.strategy,
                                     max_per_worker=req.max_per_worker)
    return {"job_id": job_id, "total_urls": len(req.urls), "strategy": req.strategy}


@router.post("/distributed/execute/{job_id}")
async def execute_distributed(job_id: str, user=Depends(get_current_user)):
    job = distributed.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job = await distributed.execute_job(job_id)
    return job.to_dict()


@router.get("/distributed/status/{job_id}")
async def distributed_status(job_id: str, user=Depends(get_current_user)):
    job = distributed.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/distributed/workers")
async def distributed_workers(user=Depends(get_current_user)):
    return distributed.get_workers()


@router.get("/distributed/queue")
async def distributed_queue(user=Depends(get_current_user)):
    return {"queue_size": distributed.get_queue_size()}


# ─── Data Validation ────────────────────────────────────────────────────

@router.post("/validate")
async def validate_data(req: ValidateRequest, db: AsyncSession = Depends(get_db),
                        user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    rules = [ValidationRule(**r) for r in req.rules] if req.rules else None
    clean_df, result = validator.validate(df, rules=rules, remove_invalid=req.remove_invalid)
    return {
        "validation": result.to_dict(),
        "preview": clean_df.head(20).to_dict(orient="records"),
    }


# ─── AutoML ─────────────────────────────────────────────────────────────

@router.post("/automl")
async def run_automl(req: AutoMLRequest, db: AsyncSession = Depends(get_db),
                     user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    if req.target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.target_column}' not found")
    X = df.drop(columns=[req.target_column])
    y = df[req.target_column]
    result = automl.auto_select(X, y, task=req.task, max_models=req.max_models)
    return result.to_dict()


@router.post("/automl/profile")
async def profile_data(job_id: str, db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, job_id, user_id)
    return automl.profile_data(df)


# ─── Anomaly Detection ──────────────────────────────────────────────────

@router.post("/anomaly")
async def detect_anomalies(req: AnomalyRequest, db: AsyncSession = Depends(get_db),
                           user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    if req.method == "all":
        return anomaly_detector.detect_all(df, req.columns)
    elif req.method == "zscore":
        return anomaly_detector.detect_zscore(df, req.columns, req.threshold).to_dict()
    elif req.method == "iqr":
        return anomaly_detector.detect_iqr(df, req.columns).to_dict()
    elif req.method == "isolation_forest":
        return anomaly_detector.detect_isolation_forest(df, req.columns).to_dict()
    elif req.method == "lof":
        return anomaly_detector.detect_lof(df, req.columns).to_dict()
    raise HTTPException(status_code=400, detail=f"Unknown method: {req.method}")


# ─── Forecasting ────────────────────────────────────────────────────────

@router.post("/forecast")
async def forecast_data(req: ForecastRequest, db: AsyncSession = Depends(get_db),
                        user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    if req.value_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.value_column}' not found")
    return forecaster.forecast_from_dataframe(df, req.value_column, req.time_column, req.periods)


# ─── Clustering ─────────────────────────────────────────────────────────

@router.post("/cluster")
async def cluster_data(req: ClusterRequest, db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    numeric = df.select_dtypes(include=["number"])
    if len(numeric.columns) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 numeric columns")
    if req.method == "auto":
        return clusterer.auto_cluster(numeric, max_k=req.n_clusters or 8)
    elif req.method == "kmeans":
        return clusterer.cluster_kmeans(numeric, req.n_clusters).to_dict()
    elif req.method == "dbscan":
        return clusterer.cluster_dbscan(numeric).to_dict()
    elif req.method == "agglomerative":
        return clusterer.cluster_agglomerative(numeric, req.n_clusters or 3).to_dict()
    elif req.method == "gmm":
        return clusterer.cluster_gmm(numeric, req.n_clusters or 3).to_dict()
    raise HTTPException(status_code=400, detail=f"Unknown method: {req.method}")


# ─── Dimensionality Reduction ───────────────────────────────────────────

@router.post("/dim-reduce")
async def reduce_dimensions(req: DimReduceRequest, db: AsyncSession = Depends(get_db),
                            user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    numeric = df.select_dtypes(include=["number"])
    if len(numeric.columns) <= req.n_components:
        raise HTTPException(status_code=400, detail="Already at target dimensionality")
    if req.method == "auto":
        return dim_reducer.auto_reduce(df, req.n_components)
    elif req.method == "pca":
        return dim_reducer.pca(df, req.n_components).to_dict()
    elif req.method == "tsne":
        return dim_reducer.tsne(df, req.n_components).to_dict()
    raise HTTPException(status_code=400, detail=f"Unknown method: {req.method}")


# ─── Feature Engineering ────────────────────────────────────────────────

@router.post("/feature-engineer")
async def engineer_features(req: FeatureEngRequest, db: AsyncSession = Depends(get_db),
                            user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    enriched_df, result = feature_engineer.create_all_features(df)
    return {
        "result": result.to_dict(),
        "preview": enriched_df.head(20).to_dict(orient="records"),
    }


# ─── Data Enrichment ────────────────────────────────────────────────────

@router.post("/enrich")
async def enrich_data(req: EnrichRequest, db: AsyncSession = Depends(get_db),
                      user=Depends(get_current_user)):
    user_id = get_user_id(user)
    df = await _get_job_data(db, req.job_id, user_id)
    enriched_df, result = enricher.enrich_all(df)
    return {
        "result": result.to_dict(),
        "preview": enriched_df.head(20).to_dict(orient="records"),
    }


# ─── Target Scrapers ────────────────────────────────────────────────────

@router.post("/target-scrape")
async def target_scrape(req: TargetScrapeRequest, user=Depends(get_current_user)):
    try:
        scrapers = {
            "ecommerce": ecommerce.scrape_product_page,
            "news": news_scraper.scrape_article,
            "financial": financial.scrape_stock,
            "academic": academic.scrape_paper,
            "job": job_scraper.scrape_job_listing,
            "real_estate": real_estate.scrape_listing,
        }
        scraper = scrapers.get(req.target_type)
        if not scraper:
            raise HTTPException(status_code=400, detail=f"Unknown target type: {req.target_type}")
        result = await scraper(req.url)
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/target-scrape/search")
async def target_search(
    url: str = Body(..., embed=True),
    target_type: str = Body(..., embed=True),
    max_items: int = Body(default=50, embed=True),
    user=Depends(get_current_user),
):
    try:
        if target_type == "ecommerce":
            result = await ecommerce.scrape_search_results(url, max_items)
        elif target_type == "news":
            result = await news_scraper.scrape_feed(url, max_items)
        else:
            raise HTTPException(status_code=400, detail=f"Search not supported for {target_type}")
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Proxy Management (DB-backed) ────────────────────────────────────────

class ProxyConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    proxy_url: str = Field(..., min_length=5, max_length=2000)
    proxy_type: str = Field(default="http")
    username: Optional[str] = None
    password: Optional[str] = None


@router.post("/proxies")
async def create_proxy(
    req: ProxyConfigRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    from app.models.scrape_config import ScrapeProxyConfig
    import uuid

    proxy = ScrapeProxyConfig(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id) if len(user_id) == 36 else user_id,
        name=req.name,
        proxy_url=req.proxy_url,
        proxy_type=req.proxy_type,
        username=req.username,
        is_active=True,
        is_healthy=True,
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy.to_dict()


@router.get("/proxies")
async def list_proxies(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    from app.models.scrape_config import ScrapeProxyConfig
    from sqlalchemy import select

    result = await db.execute(
        select(ScrapeProxyConfig)
        .where(ScrapeProxyConfig.user_id == user_id)
        .order_by(ScrapeProxyConfig.created_at.desc())
    )
    return [p.to_dict() for p in result.scalars().all()]


@router.delete("/proxies/{proxy_id}")
async def delete_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models.scrape_config import ScrapeProxyConfig
    from sqlalchemy import select

    result = await db.execute(
        select(ScrapeProxyConfig).where(ScrapeProxyConfig.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    await db.delete(proxy)
    await db.commit()
    return {"message": "Proxy deleted"}


@router.post("/proxies/{proxy_id}/test")
async def test_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models.scrape_config import ScrapeProxyConfig
    from sqlalchemy import select
    import httpx
    import time

    result = await db.execute(
        select(ScrapeProxyConfig).where(ScrapeProxyConfig.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    start = time.time()
    try:
        async with httpx.AsyncClient(
            proxy=proxy.proxy_url,
            timeout=httpx.Timeout(15.0),
        ) as client:
            resp = await client.get("https://httpbin.org/ip")
            latency_ms = int((time.time() - start) * 1000)
            proxy.is_healthy = resp.status_code == 200
            proxy.avg_response_ms = latency_ms
            proxy.last_checked_at = datetime.now(timezone.utc)
            proxy.total_requests = (proxy.total_requests or 0) + 1
            await db.commit()
            return {"healthy": True, "latency_ms": latency_ms, "ip": resp.json().get("origin", "")}
    except Exception as e:
        proxy.is_healthy = False
        proxy.failed_requests = (proxy.failed_requests or 0) + 1
        proxy.last_checked_at = datetime.now(timezone.utc)
        await db.commit()
        return {"healthy": False, "error": str(e)}
