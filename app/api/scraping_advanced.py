"""Advanced Scraping API — Extended endpoints for JS rendering, smart extraction,
export, templates, scheduling, dedup, and transformation (DB-backed)."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.services.scraper.shared import get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraping", tags=["Advanced Scraping"])

js_scraper = JsRenderedScraper()
smart_extractor = SmartDataExtractor()
export_service = ExportService()
transformer = DataTransformer()
deduplicator = CrossPageDeduplicator()


class JsScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    use_selenium: bool = Field(default=False)
    wait_seconds: int = Field(default=3, ge=1, le=30)


class SmartExtractRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    css_selector: Optional[str] = None
    use_selenium: bool = Field(default=False)


class TransformRequest(BaseModel):
    job_id: str
    rules: List[dict]
    export_formats: List[str] = Field(default=["csv", "json"])


class DedupRequest(BaseModel):
    job_ids: List[str] = Field(..., min_length=1, max_length=10)
    method: str = Field(default="exact")
    key_columns: Optional[List[str]] = None
    threshold: float = Field(default=0.85, ge=0, le=1)


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    scrape_type: str = "single"
    config: dict = {}
    tags: List[str] = []
    is_public: bool = False


class ScheduleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=5, max_length=2000)
    config: dict = {}
    cron_expression: str = "0 2 * * *"
    interval_minutes: int = Field(default=1440, ge=1)
    template_id: Optional[str] = None


@router.post("/js-scrape")
async def js_scrape(
    req: JsScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        page = await js_scraper.smart_scrape(req.url)
        return {
            "url": req.url,
            "title": page.title,
            "html_length": len(page.html),
            "tables": page.tables,
            "text_length": len(page.text),
            "metadata": page.metadata,
            "duration_ms": page.duration_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-extract")
async def smart_extract(
    req: SmartExtractRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        page = await js_scraper.smart_scrape(req.url)
        extraction = smart_extractor.extract_all(page.html, url=req.url)
        return {
            "url": req.url,
            "extraction": extraction.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-stats/{job_id}")
async def export_stats(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data, column_count, clean_row_count FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")

    data = row[0]
    row_count = len(data) if isinstance(data, list) else 0
    col_count = row[2] or 0

    estimates = {}
    for fmt in ["csv", "json", "excel", "parquet"]:
        try:
            stats = export_service.estimate_size(row_count, col_count, fmt)
            estimates[fmt] = stats
        except Exception:
            estimates[fmt] = {"estimated_bytes": row_count * col_count * 10}

    return {"job_id": job_id, "row_count": row_count, "column_count": col_count, "estimates": estimates}


@router.get("/operations")
async def list_operations():
    return {"operations": transformer.list_operations()}


@router.post("/transform")
async def transform_data(
    req: TransformRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
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
    user_id = get_user_id(user)
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


@router.post("/dedup")
async def dedup_cross_page(
    req: DedupRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
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


# ─── Templates (DB-backed) ──────────────────────────────────────────────

@router.post("/templates")
async def create_template(
    req: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    template_manager = TemplateManager(db)
    template = await template_manager.create(
        user_id=user_id, name=req.name, description=req.description,
        scrape_type=req.scrape_type, config=req.config,
        tags=req.tags, is_public=req.is_public,
    )
    return template


@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    q: str = Query(None, description="Search query"),
):
    user_id = get_user_id(user)
    template_manager = TemplateManager(db)
    if q:
        return await template_manager.search(q, user_id)
    return await template_manager.list_user(user_id)


@router.get("/templates/popular")
async def popular_templates(db: AsyncSession = Depends(get_db)):
    template_manager = TemplateManager(db)
    return await template_manager.get_popular(10)


@router.get("/templates/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    template_manager = TemplateManager(db)
    template = await template_manager.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    req: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    template_manager = TemplateManager(db)
    template = await template_manager.update(
        template_id, name=req.name, description=req.description,
        scrape_type=req.scrape_type, config=req.config,
        tags=req.tags, is_public=req.is_public,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    template_manager = TemplateManager(db)
    if not await template_manager.delete(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted"}


@router.post("/templates/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: str = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    template_manager = TemplateManager(db)
    cloned = await template_manager.clone(template_id, new_name)
    if not cloned:
        raise HTTPException(status_code=404, detail="Template not found")
    return cloned


# ─── Scheduling (DB-backed) ──────────────────────────────────────────────

@router.post("/schedules")
async def create_schedule(
    req: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    scheduler = ScrapeScheduler(db)
    schedule = await scheduler.create_schedule(
        user_id=user_id, name=req.name, url=req.url,
        config=req.config, cron_expression=req.cron_expression,
        interval_minutes=req.interval_minutes, template_id=req.template_id,
    )
    return schedule


@router.get("/schedules")
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    scheduler = ScrapeScheduler(db)
    return await scheduler.list_user_schedules(user_id)


@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    scheduler = ScrapeScheduler(db)
    schedule = await scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return scheduler.trigger_now(schedule_id, schedule["url"], schedule.get("config", {}))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, user=Depends(get_current_user)):
    scheduler = ScrapeScheduler()
    return scheduler.get_task_status(task_id)


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, user=Depends(get_current_user)):
    scheduler = ScrapeScheduler()
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
