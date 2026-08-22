"""Unified Scraping API — Single gateway for all scraping operations.

Replaces the 3-tier system (basic/advanced/ultra) with a unified interface.
Auto-detects scraping strategy based on URL and parameters.
"""
import logging
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field
import pandas as pd

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.scraper.html_scraper import HtmlScraper
from app.services.scraper.multi_scraper import MultiScraper
from app.services.scraper.export_service import ExportService
from app.services.scraper.shared import get_user_id, make_json_safe
from app.ml.scrape_processor import ScrapeDataProcessor
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scrape", tags=["Scraping"])

MAX_URLS = 50
MAX_IMPORT_ROWS = 500_000


# ─── Request/Response Schemas ────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    extract_tables: bool = True
    extract_lists: bool = True
    use_playwright: bool = False
    wait_seconds: int = Field(default=3, ge=1, le=30)
    scroll: bool = False
    cache: bool = True

    model_config = {"extra": "ignore"}


class BatchScrapeRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, max_length=MAX_URLS)
    extract_tables: bool = True
    extract_lists: bool = True
    max_concurrent: int = Field(default=5, ge=1, le=10)
    use_playwright: bool = False

    model_config = {"extra": "ignore"}


class RecursiveScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    max_depth: int = Field(default=2, ge=1, le=5)
    max_pages: int = Field(default=10, ge=1, le=50)
    extract_tables: bool = True

    model_config = {"extra": "ignore"}


class ProcessAndStoreRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    auto_rename: bool = True
    deduplicate: bool = True
    detect_types: bool = True
    dataset_name: Optional[str] = None
    target_column: Optional[str] = None
    tags: Optional[List[str]] = None
    use_playwright: bool = False

    model_config = {"extra": "ignore"}


class ImportRequest(BaseModel):
    job_id: str
    dataset_name: Optional[str] = None
    description: Optional[str] = None
    target_column: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = {"extra": "ignore"}


class TrainFromScrapeRequest(BaseModel):
    job_id: str
    dataset_name: Optional[str] = None
    target_column: str
    algorithm: str = "random_forest"
    task_type: str = "classification"
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)

    model_config = {"extra": "ignore"}


# ─── Core Endpoints ──────────────────────────────────────────────────────

@router.post("")
async def scrape(
    req: ScrapeRequest,
    user=Depends(get_current_user),
):
    """Universal scrape — auto-detects static/SPA/API."""
    scraper = HtmlScraper(use_cache=req.cache)

    if req.use_playwright:
        result = await scraper.scrape_with_playwright(
            req.url, wait_seconds=req.wait_seconds, scroll=req.scroll,
        )
    else:
        result = await scraper.scrape(req.url, extract_tables=req.extract_tables, extract_lists=req.extract_lists)

    return result.to_dict()


@router.post("/batch")
async def batch_scrape(
    req: BatchScrapeRequest,
    user=Depends(get_current_user),
):
    """Scrape multiple URLs concurrently."""
    multi = MultiScraper(max_concurrent=req.max_concurrent)

    async def _scrape():
        return await multi.scrape_batch(
            urls=req.urls,
            extract_tables=req.extract_tables,
            extract_lists=req.extract_lists,
        )

    batch_result = await _scrape()

    return {
        "total_urls": len(req.urls),
        "successful": batch_result.successful,
        "failed": batch_result.failed,
        "total_rows": batch_result.total_rows,
        "results": [r.to_dict() for r in batch_result.results[:50]],
        "errors": batch_result.errors[:20],
    }


@router.post("/recursive")
async def recursive_scrape(
    req: RecursiveScrapeRequest,
    user=Depends(get_current_user),
):
    """Recursively crawl internal links."""
    scraper = HtmlScraper()
    urls = await scraper.scrape_recursive(
        req.url, max_depth=req.max_depth, max_pages=req.max_pages,
    )
    return {"url": req.url, "pages_found": len(urls), "urls": urls[:100]}


@router.post("/process")
async def process_and_store(
    req: ProcessAndStoreRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Scrape + process + store as job."""
    user_id = get_user_id(user)
    scraper = HtmlScraper()
    processor = ScrapeDataProcessor()

    try:
        if req.use_playwright:
            scrape_result = await scraper.scrape_with_playwright(req.url)
        else:
            scrape_result = await scraper.scrape(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")

    all_rows = []
    for table in scrape_result.tables:
        headers = table.get("headers", [])
        for row in table.get("rows", []):
            if isinstance(row, dict):
                all_rows.append(row)
            elif isinstance(row, list) and len(row) == len(headers):
                all_rows.append(dict(zip(headers, row)))

    if not all_rows:
        raise HTTPException(status_code=400, detail="No tabular data found")

    processed = processor.process(
        rows=all_rows,
        auto_rename=req.auto_rename,
        deduplicate=req.deduplicate,
        detect_types=req.detect_types,
    )

    job_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO scrape_jobs (id, user_id, url, title, status, raw_row_count, clean_row_count,
                column_count, duplicates_removed, tables_data, columns_typed, columns_renamed,
                quality_score, quality_issues, processed_data, scrape_type)
            VALUES (:id, :user_id, :url, :title, 'completed', :raw_rows, :clean_rows,
                :col_count, :dupes, :tables, :typed, :renamed, :quality, :issues, :data, 'unified')
        """),
        {
            "id": job_id, "user_id": user_id, "url": req.url,
            "title": scrape_result.title, "raw_rows": len(all_rows),
            "clean_rows": len(processed.df) if processed.df is not None else 0,
            "col_count": processed.column_count, "dupes": processed.duplicates_removed,
            "tables": json.dumps(scrape_result.tables[:5], default=str),
            "typed": json.dumps(processed.columns_typed, default=str),
            "renamed": json.dumps(processed.columns_renamed, default=str),
            "quality": processed.quality_score,
            "issues": json.dumps(processed.quality_issues, default=str),
            "data": json.dumps(make_json_safe(processed.df.to_dict(orient="records") if processed.df is not None else []), default=str),
        },
    )
    await db.commit()

    return {
        "job_id": job_id,
        "url": req.url,
        "title": scrape_result.title,
        "raw_rows": len(all_rows),
        "clean_rows": len(processed.df) if processed.df is not None else 0,
        "columns": processed.column_count,
        "quality_score": processed.quality_score,
        "quality_issues": processed.quality_issues,
    }


# ─── Job Management ──────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("""
            SELECT id, url, title, status, raw_row_count, clean_row_count, column_count,
                   quality_score, scrape_type, created_at
            FROM scrape_jobs WHERE user_id = :user_id
            ORDER BY created_at DESC OFFSET :skip LIMIT :limit
        """),
        {"user_id": user_id, "skip": skip, "limit": limit},
    )
    rows = result.mappings().all()
    return [{"id": str(r["id"]), **{k: v for k, v in r.items() if k != "id"}} for r in rows]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT * FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("DELETE FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id RETURNING id"),
        {"job_id": job_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Job not found")
    await db.commit()
    return {"message": "Job deleted"}


# ─── Import & Train ──────────────────────────────────────────────────────

@router.post("/import")
async def import_to_dataset(
    req: ImportRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data, clean_row_count, column_count FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found or no data")

    processed_data = row[0]
    row_count = row[1] or len(processed_data) if isinstance(processed_data, list) else 0
    column_count = row[2] or 0

    dataset_name = req.dataset_name or f"Scrape {datetime.now().strftime('%Y%m%d_%H%M%S')}"

    dataset_dir = os.path.join("ml_artifacts", "datasets", "scraped")
    os.makedirs(dataset_dir, exist_ok=True)
    json_filename = f"job_{req.job_id[:8]}.json"
    json_filepath = os.path.join(dataset_dir, json_filename)
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(make_json_safe(processed_data), f, indent=2, default=str, ensure_ascii=False)

    df = pd.DataFrame(processed_data) if isinstance(processed_data, list) else pd.DataFrame()

    dataset = Dataset(
        name=dataset_name,
        description=req.description or "Data dari web scraping",
        file_path=json_filepath,
        file_size=os.path.getsize(json_filepath),
        rows_count=row_count,
        columns_count=column_count,
        column_names=list(df.columns) if len(df) > 0 else [],
        column_types={col: str(df[col].dtype) for col in df.columns} if len(df) > 0 else {},
        target_column=req.target_column,
        tags=["scraped"] + (req.tags or []),
        owner_id=user.id,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    return {
        "dataset_id": str(dataset.id),
        "name": dataset.name,
        "row_count": row_count,
        "column_count": column_count,
        "message": "Dataset berhasil dibuat dari data scraping",
    }


# ─── Export ──────────────────────────────────────────────────────────────

@router.get("/export/{job_id}/{fmt}")
async def export_job(
    job_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data, title FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")

    df = pd.DataFrame(row[0])
    title = row[1] or job_id[:8]
    export_service = ExportService()

    try:
        if fmt == "csv":
            filepath = export_service.export_csv(df, f"{title}.csv")
        elif fmt == "json":
            filepath = export_service.export_json(df, f"{title}.json")
        elif fmt == "excel":
            filepath = export_service.export_excel(df, f"{title}.xlsx")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

        from fastapi.responses import FileResponse
        return FileResponse(filepath, filename=os.path.basename(filepath))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Train from Scrape ──────────────────────────────────────────────────

@router.post("/train")
async def train_from_scrape(
    req: TrainFromScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """One-shot: scrape job → dataset → ML training."""
    from app.models.model import MLModel, ModelStatus
    from app.ml.pipeline import MLPipeline

    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data, title FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job not found")

    dataset_name = req.dataset_name or f"Scrape Train {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_filename = f"job_{req.job_id[:8]}.json"
    dataset_dir = os.path.join("ml_artifacts", "datasets", "scraped")
    json_filepath = os.path.join(dataset_dir, json_filename)

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(make_json_safe(row[0]), f, indent=2, default=str, ensure_ascii=False)

    model_obj = MLModel(
        name=dataset_name,
        algorithm=req.algorithm,
        owner_id=user.id,
    )
    db.add(model_obj)
    await db.commit()
    await db.refresh(model_obj)

    try:
        pipeline = MLPipeline()
        with open(json_filepath, "rb") as f:
            file_content = f.read()
        training_result = pipeline.run_training(
            file_content=file_content,
            filename=json_filename,
            target_column=req.target_column,
            algorithm=req.algorithm,
            test_size=req.test_size,
            problem_type=req.task_type,
        )

        if training_result.get("status") == "completed":
            model_dir = os.path.join("ml_artifacts", f"model_{model_obj.id}_v{model_obj.version}")
            artifacts = pipeline.save_artifacts(model_dir)
            model_obj.status = ModelStatus.TRAINED
            model_obj.file_path = artifacts["model_path"]
            model_obj.metrics = training_result.get("metrics", {})
            model_obj.parameters = training_result.get("parameters", {})
            model_obj.feature_names = training_result.get("data_info", {}).get("features", [])
        else:
            model_obj.status = ModelStatus.FAILED

        await db.commit()

        return {
            "model_id": str(model_obj.id),
            "model_name": model_obj.name,
            "algorithm": req.algorithm,
            "task_type": req.task_type,
            "status": model_obj.status.value if hasattr(model_obj.status, 'value') else str(model_obj.status),
            "metrics": training_result.get("metrics", {}),
            "message": "Model berhasil dilatih dari data scraping",
        }
    except Exception as e:
        model_obj.status = ModelStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")
