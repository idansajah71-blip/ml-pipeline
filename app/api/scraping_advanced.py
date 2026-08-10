"""Advanced Scraping API — Extended endpoints for JS rendering, smart extraction,
export, templates, scheduling, dedup, and transformation."""
import logging
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, Field
import pandas as pd

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.scraper.js_scraper import JsRenderedScraper
from app.services.scraper.smart_extractor import SmartDataExtractor
from app.services.scraper.export_service import ExportService
from app.services.scraper.data_transformer import DataTransformer, TransformRule
from app.services.scraper.deduplicator import CrossPageDeduplicator
from app.services.scraper.templates import TemplateManager
from app.services.scraper.scheduler import ScrapeScheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraping", tags=["Advanced Scraping"])

js_scraper = JsRenderedScraper()
smart_extractor = SmartDataExtractor()
export_service = ExportService()
transformer = DataTransformer()
deduplicator = CrossPageDeduplicator()
template_manager = TemplateManager()
scheduler = ScrapeScheduler()


def _get_user_id(user) -> str:
    return str(user.id)


class JsScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    use_selenium: bool = Field(default=False)
    wait_seconds: int = Field(default=3, ge=1, le=30)


class SmartExtractRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    css_selector: Optional[str] = None
    use_selenium: bool = Field(default=False)


class ExportRequest(BaseModel):
    job_id: str
    formats: List[str] = Field(default=["csv", "json"], description="Export formats")
    sheet_name: str = Field(default="Sheet1")


class TransformRequest(BaseModel):
    job_id: str
    rules: List[dict] = Field(..., description="List of transform rules")


class DedupRequest(BaseModel):
    job_ids: List[str] = Field(..., min_length=1, description="Job IDs to merge and dedup")
    method: str = Field(default="exact", description="exact, fuzzy, semantic")
    key_columns: Optional[List[str]] = None
    threshold: float = Field(default=0.85, ge=0.5, le=1.0)


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    scrape_type: str = Field(default="single")
    urls: List[str] = Field(default=[])
    config: dict = Field(default={})
    transform_rules: List[dict] = Field(default=[])
    export_formats: List[str] = Field(default=["csv", "json"])
    tags: List[str] = Field(default=[])
    is_public: bool = Field(default=False)


class ScheduleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    urls: List[str] = Field(..., min_length=1)
    interval_minutes: int = Field(default=60, ge=5, le=1440)
    config: dict = Field(default={})


# ─── JS-Rendered Scraping ───────────────────────────────────────────────

@router.post("/js-scrape")
async def js_scrape(
    req: JsScrapeRequest,
    user=Depends(get_current_user),
):
    try:
        if req.use_selenium:
            page = await js_scraper.scrape_with_selenium(req.url, wait_seconds=req.wait_seconds)
        else:
            page = await js_scraper.smart_scrape(req.url)
        return {
            "url": page.url,
            "status_code": page.status_code,
            "is_spa": page.is_spa,
            "spa_framework": page.spa_framework,
            "has_infinite_scroll": page.has_infinite_scroll,
            "ajax_endpoints": page.ajax_endpoints,
            "lazy_loaded_elements": page.lazy_loaded_elements,
            "total_dom_nodes": page.total_dom_nodes,
            "render_time_ms": page.render_time_ms,
            "render_strategy": page.render_strategy,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Smart Data Extraction ──────────────────────────────────────────────

@router.post("/smart-extract")
async def smart_extract(
    req: SmartExtractRequest,
    user=Depends(get_current_user),
):
    try:
        if req.use_selenium:
            page = await js_scraper.scrape_with_selenium(req.url)
        else:
            page = await js_scraper.scrape(req.url)

        if req.css_selector:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.html, "lxml")
            elements = soup.select(req.css_selector)
            return {
                "url": req.url,
                "selector": req.css_selector,
                "element_count": len(elements),
                "elements": [
                    {"tag": el.name, "text": el.get_text(strip=True)[:500], "html": str(el)[:1000]}
                    for el in elements[:50]
                ],
            }

        result = smart_extractor.extract_all(page.html, url=req.url)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Multi-Format Export ─────────────────────────────────────────────────

@router.post("/export")
async def export_data(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found or no data")

    try:
        df = pd.DataFrame(row[0])
        export_results = export_service.export_multiple(df, formats=req.formats)
        return export_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-stats/{job_id}")
async def export_stats(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")
    df = pd.DataFrame(row[0])
    return export_service.get_export_stats(df)


@router.get("/operations")
async def list_operations(user=Depends(get_current_user)):
    return transformer.get_available_operations()


# ─── Data Transformation ─────────────────────────────────────────────────

@router.post("/transform")
async def transform_data(
    req: TransformRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        df = pd.DataFrame(row[0])
        rules = [TransformRule(**r) for r in req.rules]
        transformed_df, transform_result = transformer.apply_rules(df, rules)

        export_results = {}
        for fmt in ["csv", "json"]:
            try:
                if fmt == "csv":
                    export_results[fmt] = export_service.export_csv(transformed_df, f"transformed_{req.job_id[:8]}.csv")
                elif fmt == "json":
                    export_results[fmt] = export_service.export_json(transformed_df, f"transformed_{req.job_id[:8]}.json")
            except Exception as e:
                export_results[fmt] = {"error": str(e)}

        return {
            "transform": transform_result.to_dict(),
            "exports": export_results,
            "preview": transformed_df.head(20).to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-clean")
async def auto_clean(
    job_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")

    df = pd.DataFrame(row[0])
    cleaned_df, clean_result = transformer.auto_clean(df)
    return {
        "result": clean_result.to_dict(),
        "preview": cleaned_df.head(20).to_dict(orient="records"),
    }


# ─── Cross-Page Deduplication ───────────────────────────────────────────

@router.post("/dedup")
async def dedup_cross_page(
    req: DedupRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    dfs = []
    source_names = []

    for job_id in req.job_ids[:10]:
        result = await db.execute(
            text("SELECT title, processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
            {"job_id": job_id, "user_id": user_id},
        )
        row = result.fetchone()
        if row and row[1]:
            dfs.append(pd.DataFrame(row[1]))
            source_names.append(row[0] or job_id[:8])

    if not dfs:
        raise HTTPException(status_code=404, detail="No data found for given job IDs")

    try:
        if req.method == "exact":
            merged_df, dedup_result = deduplicator.dedup_exact(
                pd.concat(dfs, ignore_index=True), key_columns=req.key_columns
            )
        elif req.method == "fuzzy":
            merged_df, dedup_result = deduplicator.dedup_fuzzy(
                pd.concat(dfs, ignore_index=True), threshold=req.threshold
            )
        elif req.method == "semantic":
            merged_df, dedup_result = deduplicator.dedup_semantic(
                pd.concat(dfs, ignore_index=True), similarity_threshold=req.threshold
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {req.method}")

        duplicates = deduplicator.find_duplicates(
            pd.concat(dfs, ignore_index=True), threshold=req.threshold
        ) if req.method != "exact" else []

        export_results = {}
        for fmt in ["csv", "json"]:
            try:
                if fmt == "csv":
                    export_results[fmt] = export_service.export_csv(merged_df, f"deduped.{fmt}")
                elif fmt == "json":
                    export_results[fmt] = export_service.export_json(merged_df, f"deduped.{fmt}")
            except Exception as e:
                export_results[fmt] = {"error": str(e)}

        return {
            "dedup": dedup_result.to_dict(),
            "duplicates_preview": duplicates[:20],
            "exports": export_results,
            "preview": merged_df.head(20).to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Templates ───────────────────────────────────────────────────────────

@router.post("/templates")
async def create_template(
    req: TemplateCreateRequest,
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    template = template_manager.create(
        user_id=user_id, name=req.name, description=req.description,
        scrape_type=req.scrape_type, urls=req.urls, config=req.config,
        transform_rules=req.transform_rules, export_formats=req.export_formats,
        tags=req.tags, is_public=req.is_public,
    )
    return template.to_dict()


@router.get("/templates")
async def list_templates(
    user=Depends(get_current_user),
    q: str = Query(None, description="Search query"),
):
    user_id = _get_user_id(user)
    if q:
        return [t.to_dict() for t in template_manager.search(q, user_id)]
    return [t.to_dict() for t in template_manager.list_user(user_id)]


@router.get("/templates/popular")
async def popular_templates():
    return [t.to_dict() for t in template_manager.get_popular(10)]


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    template = template_manager.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    req: TemplateCreateRequest,
    user=Depends(get_current_user),
):
    template = template_manager.update(
        template_id, name=req.name, description=req.description,
        scrape_type=req.scrape_type, urls=req.urls, config=req.config,
        transform_rules=req.transform_rules, export_formats=req.export_formats,
        tags=req.tags, is_public=req.is_public,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user=Depends(get_current_user)):
    if not template_manager.delete(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted"}


@router.post("/templates/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: str = Query(None),
    user=Depends(get_current_user),
):
    cloned = template_manager.clone(template_id, new_name)
    if not cloned:
        raise HTTPException(status_code=404, detail="Template not found")
    return cloned.to_dict()


# ─── Scheduling ──────────────────────────────────────────────────────────

@router.post("/schedules")
async def create_schedule(
    req: ScheduleCreateRequest,
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    schedule = scheduler.create_schedule(
        user_id=user_id, name=req.name, urls=req.urls,
        interval_minutes=req.interval_minutes, config=req.config,
    )
    return schedule


@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    urls: List[str] = Body(...),
    config: dict = Body(default={}),
    user=Depends(get_current_user),
):
    return scheduler.trigger_now(schedule_id, urls, config)


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, user=Depends(get_current_user)):
    return scheduler.get_task_status(task_id)


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, user=Depends(get_current_user)):
    return scheduler.cancel_task(task_id)


# ─── Utility ─────────────────────────────────────────────────────────────

@router.get("/analyze-url")
async def analyze_url(
    url: str = Query(..., description="URL to analyze"),
    user=Depends(get_current_user),
):
    try:
        page = await js_scraper.smart_scrape(url)
        extraction = smart_extractor.extract_all(page.html, url=url)
        return {
            "url": url,
            "page_info": page.to_dict(),
            "extraction": extraction.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
