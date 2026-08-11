import logging
import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

import pandas as pd

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.scraper.html_scraper import HtmlScraper
from app.services.scraper.multi_scraper import MultiScraper
from app.services.scraper.export_service import ExportService
from app.services.scraper.shared import get_user_id, make_json_safe
from app.ml.scrape_processor import ScrapeDataProcessor
from app.models.dataset import Dataset
from app.schemas.scraping import (
    ScrapeRequest,
    UniversalScrapeRequest,
    UniversalScrapeResponse,
    ScrapeAndProcessRequest,
    BatchScrapeRequest,
    RecursiveScrapeRequest,
    SitemapScrapeRequest,
    DiscoverScrapeRequest,
    ScrapeJobResponse,
    ScrapePreviewResponse,
    ImportScrapeRequest,
    ImportScrapeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraping", tags=["Web Scraping"])

scraper = HtmlScraper()
processor = ScrapeDataProcessor()

MAX_URLS_PER_JOB = 20
MAX_ROWS_IMPORT = 500_000


def _build_preview_response(result) -> ScrapePreviewResponse:
    return ScrapePreviewResponse(
        title=result.title,
        tables=result.tables[:10],
        lists=result.text_blocks[:10],
        metadata=result.metadata,
        row_count=result.row_count,
        column_count=result.column_count,
        content_hash=result.content_hash,
        links=result.links[:50],
        images=result.images[:20],
        json_ld=result.json_ld,
        feeds=result.feeds,
        api_endpoints=result.api_endpoints,
        open_graph=result.open_graph,
        keywords=result.keywords,
        language=result.language,
        word_count=result.word_count,
        reading_time_minutes=result.reading_time_minutes,
        scrape_duration_ms=result.scrape_duration_ms,
    )


@router.post("/preview", response_model=ScrapePreviewResponse)
async def scrape_preview(
    req: ScrapeRequest,
    user=Depends(get_current_user),
):
    try:
        result = await scraper.scrape(
            url=req.url,
            extract_tables=req.extract_tables,
            extract_lists=req.extract_lists,
        )
        return _build_preview_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scrape preview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal scrape URL: {str(e)}")


@router.post("/universal", response_model=UniversalScrapeResponse)
async def universal_scrape(
    req: UniversalScrapeRequest,
    user=Depends(get_current_user),
):
    """Universal scraping — automatically adapts to any website:
    - Static HTML
    - SPA / JavaScript-rendered sites
    - JSON / XML API endpoints
    - Anti-bot protected sites (fingerprint bypass)
    """
    try:
        result = await scraper.scrape_universal(
            url=req.url,
            extract_tables=req.extract_tables,
            extract_lists=req.extract_lists,
            use_js=req.use_js,
            use_selenium=req.use_selenium,
            wait_seconds=req.wait_seconds,
        )
        return UniversalScrapeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Universal scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal universal scrape: {str(e)}")


@router.post("/scrape-and-process", response_model=ScrapeJobResponse)
async def scrape_and_process(
    req: ScrapeAndProcessRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    from app.core.websocket import emit_scrape_progress
    import uuid
    job_id = str(uuid.uuid4())

    await emit_scrape_progress(job_id, "scrape:start", {"url": req.url, "status": "starting"})

    try:
        scrape_result = await scraper.scrape(
            url=req.url,
            extract_tables=True,
            extract_lists=True,
        )
        await emit_scrape_progress(job_id, "scrape:progress", {"url": req.url, "status": "scraped", "rows": len(scrape_result.tables)})
    except ValueError as e:
        await emit_scrape_progress(job_id, "scrape:error", {"url": req.url, "error": str(e)})
        logger.error(f"Scrape validation error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await emit_scrape_progress(job_id, "scrape:error", {"url": req.url, "error": str(e)})
        logger.error(f"Scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal scrape: {str(e)}")

    all_rows = []
    for table in scrape_result.tables:
        all_rows.extend(table.get("rows", []))

    if not all_rows and scrape_result.text_blocks:
        for block in scrape_result.text_blocks:
            for item in block:
                all_rows.append({"value": item})

    processed = processor.process(
        rows=all_rows,
        auto_rename=req.auto_rename,
        deduplicate=req.deduplicate,
        detect_types=req.detect_types,
        cluster_text=req.cluster_text,
        run_advanced_analysis=req.run_advanced_analysis,
        run_sentiment=req.run_sentiment,
        run_patterns=req.run_patterns,
    )

    processed_data = processor.to_dict_list(processed)

    ml_applied = ["type_detection", "dedup", "quality_scoring"]
    if req.cluster_text:
        ml_applied.append("text_clustering")
    if req.run_advanced_analysis:
        ml_applied.append("advanced_analysis")
    if req.run_sentiment:
        ml_applied.append("sentiment_analysis")
    if req.run_patterns:
        ml_applied.append("pattern_detection")

    scrape_meta = {
        "links_count": len(scrape_result.links),
        "images_count": len(scrape_result.images),
        "json_ld_count": len(scrape_result.json_ld),
        "feeds_count": len(scrape_result.feeds),
        "api_endpoints_count": len(scrape_result.api_endpoints),
        "word_count": scrape_result.word_count,
        "reading_time_minutes": scrape_result.reading_time_minutes,
        "language": scrape_result.language,
        "keywords": scrape_result.keywords,
        "open_graph": scrape_result.open_graph,
        "scrape_duration_ms": scrape_result.scrape_duration_ms,
        "scrape_strategy": scrape_result.scrape_strategy,
    }

    job_id = None
    try:
        insert_result = await db.execute(
            text("""
                INSERT INTO scrape_jobs (
                    id, user_id, url, title, status,
                    raw_row_count, clean_row_count, column_count, duplicates_removed,
                    tables_data, lists_data, metadata,
                    processed_data, columns_typed, columns_renamed,
                    quality_score, quality_issues, clusters,
                    ml_processing_applied,
                    advanced_analysis, sentiment_analysis, pattern_analysis,
                    scrape_metadata,
                    content_hash, scrape_type,
                    created_at, scraped_at, processed_at
                ) VALUES (
                    gen_random_uuid(), :user_id, :url, :title, 'completed',
                    :raw_row_count, :clean_row_count, :column_count, :duplicates_removed,
                    :tables_data, :lists_data, :metadata,
                    :processed_data, :columns_typed, :columns_renamed,
                    :quality_score, :quality_issues, :clusters,
                    :ml_processing_applied,
                    :advanced_analysis, :sentiment_analysis, :pattern_analysis,
                    :scrape_metadata,
                    :content_hash, 'single',
                    NOW(), NOW(), NOW()
                ) RETURNING id
            """),
            {
                "user_id": user_id,
                "url": req.url,
                "title": scrape_result.title,
                "raw_row_count": processed.raw_row_count,
                "clean_row_count": processed.clean_row_count,
                "column_count": processed.column_count,
                "duplicates_removed": processed.duplicates_removed,
                "tables_data": make_json_safe(scrape_result.tables),
                "lists_data": make_json_safe(scrape_result.text_blocks),
                "metadata": make_json_safe(scrape_result.metadata),
                "processed_data": make_json_safe(processed_data),
                "columns_typed": make_json_safe(processed.columns_typed),
                "columns_renamed": make_json_safe(processed.columns_renamed),
                "quality_score": float(processed.quality_score),
                "quality_issues": make_json_safe(processed.quality_issues),
                "clusters": make_json_safe(processed.clusters),
                "ml_processing_applied": ml_applied,
                "advanced_analysis": make_json_safe(processed.advanced_analysis),
                "sentiment_analysis": make_json_safe(processed.sentiment_analysis),
                "pattern_analysis": make_json_safe(processed.pattern_analysis),
                "scrape_metadata": make_json_safe(scrape_meta),
                "content_hash": scrape_result.content_hash,
            },
        )
        await db.commit()
        row = insert_result.fetchone()
        job_id = str(row[0]) if row else None
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save scrape job: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal simpan hasil scrape: {str(e)}")

    return ScrapeJobResponse(
        id=job_id,
        url=req.url,
        title=scrape_result.title,
        status="completed",
        scrape_type="single",
        raw_row_count=processed.raw_row_count,
        clean_row_count=processed.clean_row_count,
        column_count=processed.column_count,
        duplicates_removed=processed.duplicates_removed,
        tables_data=scrape_result.tables,
        columns_typed=processed.columns_typed,
        columns_renamed=processed.columns_renamed,
        quality_score=processed.quality_score,
        quality_issues=processed.quality_issues,
        clusters=processed.clusters,
        ml_processing_applied=ml_applied,
        advanced_analysis=processed.advanced_analysis,
        sentiment_analysis=processed.sentiment_analysis,
        pattern_analysis=processed.pattern_analysis,
        scrape_metadata=scrape_meta,
        created_at=datetime.utcnow(),
        scraped_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )


@router.post("/batch", response_model=ScrapeJobResponse)
async def batch_scrape(
    req: BatchScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    multi = MultiScraper(max_concurrent=req.max_concurrent)

    try:
        batch_result = await multi.scrape_batch(
            urls=req.urls,
            extract_tables=req.extract_tables,
            extract_lists=req.extract_lists,
            max_retries=req.max_retries,
        )
    except Exception as e:
        logger.error(f"Batch scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal batch scrape: {str(e)}")

    all_rows = []
    for table in batch_result.combined_tables:
        all_rows.extend(table.get("rows", []))

    processed = processor.process(
        rows=all_rows,
        run_advanced_analysis=req.run_advanced_analysis,
        run_sentiment=req.run_sentiment,
        run_patterns=req.run_patterns,
    )

    processed_data = processor.to_dict_list(processed)

    ml_applied = ["type_detection", "dedup", "quality_scoring", "batch_scrape"]
    if req.run_advanced_analysis:
        ml_applied.append("advanced_analysis")
    if req.run_sentiment:
        ml_applied.append("sentiment_analysis")
    if req.run_patterns:
        ml_applied.append("pattern_detection")

    batch_meta = {
        "total_urls": batch_result.total_urls,
        "successful": batch_result.successful,
        "failed": batch_result.failed,
        "total_duration_ms": batch_result.total_duration_ms,
        "errors": batch_result.errors[:10],
    }

    job_id = None
    try:
        insert_result = await db.execute(
            text("""
                INSERT INTO scrape_jobs (
                    id, user_id, url, title, status,
                    raw_row_count, clean_row_count, column_count, duplicates_removed,
                    tables_data, lists_data, metadata,
                    processed_data, columns_typed, columns_renamed,
                    quality_score, quality_issues, clusters,
                    ml_processing_applied,
                    advanced_analysis, sentiment_analysis, pattern_analysis,
                    scrape_metadata,
                    batch_results, scrape_type,
                    created_at, scraped_at, processed_at
                ) VALUES (
                    gen_random_uuid(), :user_id, :url, :title, 'completed',
                    :raw_row_count, :clean_row_count, :column_count, :duplicates_removed,
                    :tables_data, :lists_data, :metadata,
                    :processed_data, :columns_typed, :columns_renamed,
                    :quality_score, :quality_issues, :clusters,
                    :ml_processing_applied,
                    :advanced_analysis, :sentiment_analysis, :pattern_analysis,
                    :scrape_metadata,
                    :batch_results, 'batch',
                    NOW(), NOW(), NOW()
                ) RETURNING id
            """),
            {
                "user_id": user_id,
                "url": f"batch:{len(req.urls)} URLs",
                "title": f"Batch scrape: {req.urls[0][:80]}..." if req.urls else "Batch",
                "raw_row_count": processed.raw_row_count,
                "clean_row_count": processed.clean_row_count,
                "column_count": processed.column_count,
                "duplicates_removed": processed.duplicates_removed,
                "tables_data": make_json_safe(batch_result.combined_tables[:50]),
                "lists_data": make_json_safe(batch_result.combined_text_blocks[:50]),
                "metadata": {},
                "processed_data": make_json_safe(processed_data),
                "columns_typed": make_json_safe(processed.columns_typed),
                "columns_renamed": make_json_safe(processed.columns_renamed),
                "quality_score": float(processed.quality_score),
                "quality_issues": make_json_safe(processed.quality_issues),
                "clusters": make_json_safe(processed.clusters),
                "ml_processing_applied": ml_applied,
                "advanced_analysis": make_json_safe(processed.advanced_analysis),
                "sentiment_analysis": make_json_safe(processed.sentiment_analysis),
                "pattern_analysis": make_json_safe(processed.pattern_analysis),
                "scrape_metadata": make_json_safe(batch_meta),
                "batch_results": make_json_safe([r.to_dict() for r in batch_result.results]),
            },
        )
        await db.commit()
        row = insert_result.fetchone()
        job_id = str(row[0]) if row else None
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save batch job: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal simpan batch job: {str(e)}")

    return ScrapeJobResponse(
        id=job_id,
        url=f"batch:{len(req.urls)} URLs",
        title=f"Batch scrape {batch_result.successful}/{batch_result.total_urls}",
        status="completed",
        scrape_type="batch",
        raw_row_count=processed.raw_row_count,
        clean_row_count=processed.clean_row_count,
        column_count=processed.column_count,
        duplicates_removed=processed.duplicates_removed,
        tables_data=batch_result.combined_tables[:20],
        columns_typed=processed.columns_typed,
        columns_renamed=processed.columns_renamed,
        quality_score=processed.quality_score,
        quality_issues=processed.quality_issues,
        clusters=processed.clusters,
        ml_processing_applied=ml_applied,
        advanced_analysis=processed.advanced_analysis,
        sentiment_analysis=processed.sentiment_analysis,
        pattern_analysis=processed.pattern_analysis,
        scrape_metadata=batch_meta,
        created_at=datetime.utcnow(),
        scraped_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )


@router.post("/recursive", response_model=ScrapeJobResponse)
async def recursive_scrape(
    req: RecursiveScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    multi = MultiScraper(max_concurrent=3)

    try:
        batch_result = await multi.scrape_with_recursive_links(
            start_url=req.url,
            max_depth=req.max_depth,
            max_pages=req.max_pages,
        )
    except Exception as e:
        logger.error(f"Recursive scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal recursive scrape: {str(e)}")

    all_rows = []
    for table in batch_result.combined_tables:
        all_rows.extend(table.get("rows", []))

    processed = processor.process(
        rows=all_rows,
        run_advanced_analysis=req.run_advanced_analysis,
    )

    processed_data = processor.to_dict_list(processed)

    ml_applied = ["recursive_scrape"]
    if req.run_advanced_analysis:
        ml_applied.append("advanced_analysis")

    meta = {
        "start_url": req.url,
        "pages_scraped": batch_result.successful,
        "max_depth": req.max_depth,
        "total_rows": batch_result.total_rows,
    }

    job_id = None
    try:
        insert_result = await db.execute(
            text("""
                INSERT INTO scrape_jobs (
                    id, user_id, url, title, status,
                    raw_row_count, clean_row_count, column_count, duplicates_removed,
                    tables_data, lists_data, metadata,
                    processed_data, columns_typed, columns_renamed,
                    quality_score, quality_issues, clusters,
                    ml_processing_applied,
                    advanced_analysis, sentiment_analysis, pattern_analysis,
                    scrape_metadata, batch_results, scrape_type,
                    created_at, scraped_at, processed_at
                ) VALUES (
                    gen_random_uuid(), :user_id, :url, :title, 'completed',
                    :raw_row_count, :clean_row_count, :column_count, :duplicates_removed,
                    :tables_data, :lists_data, :metadata,
                    :processed_data, :columns_typed, :columns_renamed,
                    :quality_score, :quality_issues, :clusters,
                    :ml_processing_applied,
                    :advanced_analysis, :sentiment_analysis, :pattern_analysis,
                    :scrape_metadata, :batch_results, 'recursive',
                    NOW(), NOW(), NOW()
                ) RETURNING id
            """),
            {
                "user_id": user_id,
                "url": req.url,
                "title": f"Recursive: {req.url[:100]}",
                "raw_row_count": processed.raw_row_count,
                "clean_row_count": processed.clean_row_count,
                "column_count": processed.column_count,
                "duplicates_removed": processed.duplicates_removed,
                "tables_data": make_json_safe(batch_result.combined_tables[:50]),
                "lists_data": make_json_safe(batch_result.combined_text_blocks[:50]),
                "metadata": {},
                "processed_data": make_json_safe(processed_data),
                "columns_typed": make_json_safe(processed.columns_typed),
                "columns_renamed": make_json_safe(processed.columns_renamed),
                "quality_score": float(processed.quality_score),
                "quality_issues": make_json_safe(processed.quality_issues),
                "clusters": make_json_safe(processed.clusters),
                "ml_processing_applied": ml_applied,
                "advanced_analysis": make_json_safe(processed.advanced_analysis),
                "sentiment_analysis": make_json_safe(processed.sentiment_analysis),
                "pattern_analysis": make_json_safe(processed.pattern_analysis),
                "scrape_metadata": make_json_safe(meta),
                "batch_results": make_json_safe([r.to_dict() for r in batch_result.results[:20]]),
            },
        )
        await db.commit()
        row = insert_result.fetchone()
        job_id = str(row[0]) if row else None
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save recursive job: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal simpan: {str(e)}")

    return ScrapeJobResponse(
        id=job_id,
        url=req.url,
        title=f"Recursive scrape: {batch_result.successful} pages",
        status="completed",
        scrape_type="recursive",
        raw_row_count=processed.raw_row_count,
        clean_row_count=processed.clean_row_count,
        column_count=processed.column_count,
        duplicates_removed=processed.duplicates_removed,
        tables_data=batch_result.combined_tables[:20],
        columns_typed=processed.columns_typed,
        columns_renamed=processed.columns_renamed,
        quality_score=processed.quality_score,
        quality_issues=processed.quality_issues,
        clusters=processed.clusters,
        ml_processing_applied=ml_applied,
        advanced_analysis=processed.advanced_analysis,
        sentiment_analysis=processed.sentiment_analysis,
        pattern_analysis=processed.pattern_analysis,
        scrape_metadata=meta,
        created_at=datetime.utcnow(),
        scraped_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )


@router.post("/discover", response_model=ScrapeJobResponse)
async def discover_and_scrape(
    req: DiscoverScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    multi = MultiScraper(max_concurrent=3)

    try:
        batch_result = await multi.discover_and_scrape(
            url=req.url,
            max_pages=req.max_pages,
        )
    except Exception as e:
        logger.error(f"Discover scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal discover: {str(e)}")

    all_rows = []
    for table in batch_result.combined_tables:
        all_rows.extend(table.get("rows", []))

    processed = processor.process(rows=all_rows, run_advanced_analysis=req.run_advanced_analysis)
    processed_data = processor.to_dict_list(processed)

    ml_applied = ["discover_scrape"]
    if req.run_advanced_analysis:
        ml_applied.append("advanced_analysis")

    meta = {"start_url": req.url, "pages_scraped": batch_result.successful}

    job_id = None
    try:
        insert_result = await db.execute(
            text("""
                INSERT INTO scrape_jobs (
                    id, user_id, url, title, status,
                    raw_row_count, clean_row_count, column_count,
                    processed_data, columns_typed, quality_score, quality_issues,
                    ml_processing_applied, advanced_analysis, scrape_metadata,
                    batch_results, scrape_type,
                    created_at, scraped_at, processed_at
                ) VALUES (
                    gen_random_uuid(), :user_id, :url, :title, 'completed',
                    :raw_row_count, :clean_row_count, :column_count,
                    :processed_data, :columns_typed, :quality_score, :quality_issues,
                    :ml_processing_applied, :advanced_analysis, :scrape_metadata,
                    :batch_results, 'discover',
                    NOW(), NOW(), NOW()
                ) RETURNING id
            """),
            {
                "user_id": user_id,
                "url": req.url,
                "title": f"Discover: {req.url[:100]}",
                "raw_row_count": processed.raw_row_count,
                "clean_row_count": processed.clean_row_count,
                "column_count": processed.column_count,
                "processed_data": make_json_safe(processed_data),
                "columns_typed": make_json_safe(processed.columns_typed),
                "quality_score": float(processed.quality_score),
                "quality_issues": make_json_safe(processed.quality_issues),
                "ml_processing_applied": ml_applied,
                "advanced_analysis": make_json_safe(processed.advanced_analysis),
                "scrape_metadata": make_json_safe(meta),
                "batch_results": make_json_safe([r.to_dict() for r in batch_result.results[:20]]),
            },
        )
        await db.commit()
        row = insert_result.fetchone()
        job_id = str(row[0]) if row else None
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal simpan: {str(e)}")

    return ScrapeJobResponse(
        id=job_id,
        url=req.url,
        title=f"Discover: {batch_result.successful} pages",
        status="completed",
        scrape_type="discover",
        raw_row_count=processed.raw_row_count,
        clean_row_count=processed.clean_row_count,
        column_count=processed.column_count,
        columns_typed=processed.columns_typed,
        quality_score=processed.quality_score,
        quality_issues=processed.quality_issues,
        ml_processing_applied=ml_applied,
        advanced_analysis=processed.advanced_analysis,
        scrape_metadata=meta,
        created_at=datetime.utcnow(),
        scraped_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )


@router.get("/sitemap/{url:path}")
async def discover_sitemaps(
    url: str,
    user=Depends(get_current_user),
):
    try:
        sitemaps = await scraper.discover_sitemaps(url)
        return {"url": url, "sitemaps": sitemaps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=list[ScrapeJobResponse])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    scrape_type: str = Query(None, description="Filter by type: single, batch, recursive, discover"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    query = """
        SELECT id, url, title, status, raw_row_count, clean_row_count,
               column_count, duplicates_removed, columns_typed, columns_renamed,
               quality_score, quality_issues, clusters, ml_processing_applied,
               advanced_analysis, sentiment_analysis, pattern_analysis,
               scrape_metadata, scrape_type,
               error_message, created_at, scraped_at, processed_at
        FROM scrape_jobs
        WHERE user_id = :user_id
    """
    params = {"user_id": user_id, "limit": limit}
    if scrape_type:
        query += " AND scrape_type = :scrape_type"
        params["scrape_type"] = scrape_type
    query += " ORDER BY created_at DESC LIMIT :limit"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    jobs = []
    for row in rows:
        jobs.append(ScrapeJobResponse(
            id=str(row[0]),
            url=row[1],
            title=row[2],
            status=row[3],
            raw_row_count=row[4] or 0,
            clean_row_count=row[5] or 0,
            column_count=row[6] or 0,
            duplicates_removed=row[7] or 0,
            columns_typed=row[8] or {},
            columns_renamed=row[9] or {},
            quality_score=row[10] or 0.0,
            quality_issues=row[11] or [],
            clusters=row[12] or {},
            ml_processing_applied=row[13] or [],
            advanced_analysis=row[14],
            sentiment_analysis=row[15],
            pattern_analysis=row[16],
            scrape_metadata=row[17],
            scrape_type=row[18] or "single",
            error_message=row[19],
            created_at=row[20],
            scraped_at=row[21],
            processed_at=row[22],
        ))
    return jobs


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)
    result = await db.execute(
        text("""
            SELECT id, url, title, status, raw_row_count, clean_row_count,
                   column_count, duplicates_removed, tables_data, lists_data, metadata,
                   processed_data, columns_typed, columns_renamed,
                   quality_score, quality_issues, clusters, ml_processing_applied,
                   advanced_analysis, sentiment_analysis, pattern_analysis,
                   scrape_metadata, batch_results, scrape_type,
                   error_message, created_at, scraped_at, processed_at
            FROM scrape_jobs
            WHERE id = :job_id AND user_id = :user_id
        """),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")

    return ScrapeJobResponse(
        id=str(row[0]),
        url=row[1],
        title=row[2],
        status=row[3],
        raw_row_count=row[4] or 0,
        clean_row_count=row[5] or 0,
        column_count=row[6] or 0,
        duplicates_removed=row[7] or 0,
        tables_data=row[8] or [],
        columns_typed=row[12] or {},
        columns_renamed=row[13] or {},
        quality_score=row[14] or 0.0,
        quality_issues=row[15] or [],
        clusters=row[16] or {},
        ml_processing_applied=row[17] or [],
        advanced_analysis=row[18],
        sentiment_analysis=row[19],
        pattern_analysis=row[20],
        scrape_metadata=row[21],
        batch_results=row[22] or [],
        scrape_type=row[23] or "single",
        error_message=row[24],
        created_at=row[25],
        scraped_at=row[26],
        processed_at=row[27],
    )


@router.post("/import", response_model=ImportScrapeResponse)
async def import_scrape_to_dataset(
    req: ImportScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = get_user_id(user)

    result = await db.execute(
        text("""
            SELECT id, title, processed_data, clean_row_count, column_count
            FROM scrape_jobs
            WHERE id = :job_id AND user_id = :user_id AND status = 'completed'
        """),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan atau belum selesai")

    dataset_name = req.dataset_name or row[1] or f"Scrape {row[0]}"
    processed_data = row[2] or []
    row_count = row[3] or 0
    column_count = row[4] or 0

    if not processed_data:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk di-import")

    if row_count > MAX_ROWS_IMPORT:
        raise HTTPException(
            status_code=400,
            detail=f"Data terlalu banyak ({row_count} rows). Batas maksimum adalah {MAX_ROWS_IMPORT:,} rows. Export/trim data terlebih dahulu.",
        )

    # Write the processed data to a JSON file on disk
    dataset_dir = os.path.join("ml_artifacts", "datasets", "scraped")
    os.makedirs(dataset_dir, exist_ok=True)
    job_id = row[0]
    json_filename = f"job_{job_id}.json"
    json_filepath = os.path.join(dataset_dir, json_filename)
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(make_json_safe(processed_data), f, indent=2, default=str, ensure_ascii=False)

    try:
        dataset = Dataset(
            name=dataset_name,
            description=req.description or "Data dari web scraping",
            file_path=json_filepath,
            file_size=os.path.getsize(json_filepath),
            rows_count=row_count,
            columns_count=column_count,
            column_names=list(df.columns) if (df := pd.DataFrame(processed_data)).shape[0] > 0 else [],
            column_types={col: str(df[col].dtype) for col in df.columns} if df.shape[0] > 0 else {},
            target_column=req.target_column,
            tags=["scraped"] + (req.tags or []),
            owner_id=user.id,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        dataset_id = str(dataset.id)
        ds_name = dataset.name
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to import scrape as dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal import: {str(e)}")

    return ImportScrapeResponse(
        dataset_id=dataset_id or "",
        name=ds_name,
        row_count=row_count,
        column_count=column_count,
    )


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
    await db.commit()
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    return {"message": "Job berhasil dihapus"}


@router.get("/export/{job_id}/{fmt}")
async def download_export(
    job_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Download an exported file for a given scrape job in the specified format.

    Supported formats: csv, json, excel, word, html, parquet, xml, sql
    """
    from fastapi.responses import FileResponse

    user_id = get_user_id(user)
    result = await db.execute(
        text("SELECT processed_data FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id"),
        {"job_id": job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan atau tidak ada data")

    try:
        df = pd.DataFrame(row[0])
        export_service = ExportService()

        export_map = {
            "csv": export_service.export_csv,
            "json": export_service.export_json,
            "excel": export_service.export_excel,
            "word": export_service.export_word,
            "html": export_service.export_html,
        }

        if fmt not in export_map:
            raise HTTPException(status_code=400, detail=f"Format tidak didukung: {fmt}")

        filename = f"job_{job_id}_{fmt}"
        if fmt == "csv":
            filename += ".csv"
        elif fmt == "json":
            filename += ".json"
        elif fmt == "excel":
            filename += ".xlsx"
        elif fmt == "word":
            filename += ".docx"
        elif fmt == "html":
            filename += ".html"

        result = export_map[fmt](df, filename=filename)
        filepath = result["filepath"]

        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="File gagal dibuat")

        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/octet-stream",
        )
    except Exception as e:
        logger.error(f"Export download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TrainFromScrapeRequest(BaseModel):
    job_id: str
    target_column: str
    task_type: str = Field("classification", description="classification, regression")
    test_size: float = Field(0.2, ge=0.05, le=0.5)
    algorithm: str = Field("random_forest", description="Algorithm to use for training")
    name: Optional[str] = None


class TrainFromScrapeResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    task_type: str
    target_column: str
    model_name: str
    model_id: str
    status: str
    metrics: dict
    message: str


@router.post("/train", response_model=TrainFromScrapeResponse)
async def train_from_scrape(
    req: TrainFromScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Import a completed scrape job as a dataset and immediately train an ML model.

    This is a one-shot endpoint: it creates the dataset, creates a model, kicks off
    training, and returns the model id and metrics.
    """
    from app.models.model import MLModel, ModelStatus
    import uuid

    user_id = get_user_id(user)

    # Fetch job data
    result = await db.execute(
        text("""
            SELECT id, title, processed_data, clean_row_count, column_count
            FROM scrape_jobs
            WHERE id = :job_id AND user_id = :user_id AND status = 'completed'
        """),
        {"job_id": req.job_id, "user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan atau belum selesai")

    jid, jtitle, processed_data, row_count, col_count = row[0], row[1], row[2], row[3], row[4]
    if not processed_data:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk dilatih")

    if row_count > MAX_ROWS_IMPORT:
        raise HTTPException(
            status_code=400,
            detail=f"Data terlalu banyak ({row_count} rows). Batas maksimum adalah {MAX_ROWS_IMPORT:,} rows.",
        )

    # Write JSON file for the dataset
    dataset_dir = os.path.join("ml_artifacts", "datasets", "scraped")
    os.makedirs(dataset_dir, exist_ok=True)
    json_filename = f"job_{jid}.json"
    json_filepath = os.path.join(dataset_dir, json_filename)
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(make_json_safe(processed_data), f, indent=2, default=str, ensure_ascii=False)

    df = pd.DataFrame(processed_data)
    if req.target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Kolom target '{req.target_column}' tidak ditemukan")

    # Create dataset
    try:
        dataset = Dataset(
            name=req.name or (jtitle or f"Scrape {jid}"),
            description=f"Dataset from scrape job {jid}",
            file_path=json_filepath,
            file_size=os.path.getsize(json_filepath),
            rows_count=len(df),
            columns_count=len(df.columns),
            column_names=list(df.columns),
            column_types={col: str(df[col].dtype) for col in df.columns},
            target_column=req.target_column,
            tags=["scraped", req.task_type],
            owner_id=user.id,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        dataset_id = str(dataset.id)
        ds_name = dataset.name
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create dataset from scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal membuat dataset: {str(e)}")

    # Create model
    try:
        model_name = req.name or f"Scrape Model {uuid.uuid4().hex[:8]}"
        model_obj = MLModel(
            name=model_name,
            description=f"Model trained from scrape job {jid}",
            algorithm=req.algorithm,
            target_column=req.target_column,
            tags=["scraped", req.task_type],
            owner_id=user.id,
        )
        db.add(model_obj)
        await db.commit()
        await db.refresh(model_obj)
        model_id = str(model_obj.id)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create model: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal membuat model: {str(e)}")

    # Run training
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
            model_dir = os.path.join(
                "ml_artifacts", f"model_{model_obj.id}_v{model_obj.version}"
            )
            artifacts = pipeline.save_artifacts(model_dir)

            model_obj.status = ModelStatus.TRAINED
            model_obj.file_path = artifacts["model_path"]
            model_obj.metrics = training_result.get("metrics", {})
            model_obj.parameters = training_result.get("parameters", {})
            model_obj.feature_names = training_result.get("data_info", {}).get("features", [])
        else:
            model_obj.status = ModelStatus.FAILED

        await db.commit()

        metrics = training_result.get("metrics", {})
        status = training_result.get("status", "failed")

        return TrainFromScrapeResponse(
            dataset_id=dataset_id,
            dataset_name=ds_name,
            task_type=req.task_type,
            target_column=req.target_column,
            model_name=model_name,
            model_id=model_id,
            status=status,
            metrics=metrics,
            message="Model berhasil dilatih dari data scraping" if status == "completed" else "Training gagal",
        )
    except Exception as e:
        logger.error(f"Training from scrape failed: {e}")
        model_obj.status = ModelStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Gagal melatih model: {str(e)}")
