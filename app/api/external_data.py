"""External Data Search & Import API.

Phase 8: Security hardening — rate limiting, audit logging, size limits.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, field_validator
import uuid
import re
import logging

from app.core.database import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external-data", tags=["External Data"])

# Security constants
MAX_SEARCH_PER_MINUTE = 30
MAX_IMPORT_PER_HOUR = 20
MAX_ROWS_FETCH = 500_000  # max rows to fetch from external source
MAX_QUERY_LENGTH = 200

# Whitelist pattern for result_id (prevent injection)
RESULT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9:_\-]+$')


class SearchResultResponse(BaseModel):
    id: str
    source_slug: str
    title: str
    description: str
    row_count: Optional[int] = None
    column_names: List[str] = []
    last_updated: Optional[str] = None
    source_url: Optional[str] = None


class DataSourceResponse(BaseModel):
    id: str
    name: str
    slug: str
    source_type: str
    license: Optional[str] = None
    is_active: bool


class ImportRequest(BaseModel):
    result_id: str
    source_slug: str
    title: str
    description: Optional[str] = None

    @field_validator("result_id")
    @classmethod
    def validate_result_id(cls, v):
        if not RESULT_ID_PATTERN.match(v):
            raise ValueError("Invalid result_id format")
        if len(v) > 200:
            raise ValueError("result_id too long")
        return v

    @field_validator("source_slug")
    @classmethod
    def validate_source_slug(cls, v):
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError("Invalid source_slug format")
        return v


class ImportResponse(BaseModel):
    dataset_id: str
    message: str


async def _check_rate_limit(
    db: AsyncSession,
    user_id: str,
    action: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """Check if user has exceeded rate limit for an action. Returns True if OK."""
    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM external_data_search_logs
            WHERE user_id = :uid
            AND created_at > NOW() - INTERVAL ':window seconds'
        """),
        {"uid": user_id, "window": window_seconds},
    )
    count = result.scalar() or 0
    return count < limit


async def _log_audit(
    db: AsyncSession,
    user_id: str,
    action: str,
    detail: str,
) -> None:
    """Write audit log entry for external data operations."""
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (id, user_id, action, resource_type, details, created_at)
                VALUES (:id, :uid, :action, 'external_data', :detail, NOW())
            """),
            {"id": str(uuid.uuid4()), "uid": user_id, "action": action, "detail": detail}
        )
        await db.commit()
    except Exception:
        pass


@router.get("/sources", response_model=List[DataSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all active external data sources."""
    result = await db.execute(
        text("SELECT id, name, slug, source_type, license, is_active "
             "FROM external_data_sources WHERE is_active = true ORDER BY name")
    )
    rows = result.fetchall()
    return [
        DataSourceResponse(
            id=str(r[0]), name=r[1], slug=r[2], source_type=r[3],
            license=r[4], is_active=r[5]
        )
        for r in rows
    ]


@router.get("/search", response_model=List[SearchResultResponse])
async def search_external_data(
    q: str = Query(..., min_length=2, max_length=MAX_QUERY_LENGTH, description="Search query"),
    source: Optional[str] = Query(None, description="Filter by source slug"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Search all active external data sources for datasets matching the query."""
    # Rate limit check
    user_id = str(current_user.id)
    if not await _check_rate_limit(db, user_id, "search", MAX_SEARCH_PER_MINUTE, 60):
        raise HTTPException(
            status_code=429,
            detail=f"Batas pencarian terlampaui. Maksimal {MAX_SEARCH_PER_MINUTE} pencarian per menit."
        )

    from app.services.external_data.source_registry import get_all_sources, get_source

    sources = get_all_sources()
    if source:
        client = get_source(source)
        if not client:
            raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
        sources = [client]

    if not sources:
        return []

    # Search all sources
    all_results = []
    for client in sources:
        try:
            results = await client.search(q, limit=limit)
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Search failed for source {client.slug}: {e}")
            continue

    # Log the search
    try:
        await db.execute(
            text("INSERT INTO external_data_search_logs (id, user_id, query_text, created_at) "
                 "VALUES (:id, :user_id, :query, NOW())"),
            {"id": str(uuid.uuid4()), "user_id": user_id, "query": q}
        )
        await db.commit()
    except Exception:
        pass

    return [
        SearchResultResponse(
            id=r.id, source_slug=r.source_slug, title=r.title,
            description=r.description, row_count=r.row_count,
            column_names=r.column_names, last_updated=r.last_updated,
            source_url=r.source_url
        )
        for r in all_results[:limit]
    ]


@router.get("/{result_id}/preview")
async def preview_external_data(
    result_id: str,
    source_slug: str = Query(..., description="Source slug"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Preview data for a search result (first 10 rows)."""
    # Validate result_id format
    if not RESULT_ID_PATTERN.match(result_id):
        raise HTTPException(status_code=400, detail="Invalid result_id format")

    from app.services.external_data.source_registry import get_source

    client = get_source(source_slug)
    if not client:
        raise HTTPException(status_code=404, detail=f"Source '{source_slug}' not found")

    try:
        df = await client.fetch(result_id)
    except Exception as e:
        logger.error(f"Fetch failed for {result_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from source")

    # Enforce row limit
    if len(df) > MAX_ROWS_FETCH:
        df = df.head(MAX_ROWS_FETCH)

    preview = df.head(10).to_dict(orient="records")
    return {
        "columns": list(df.columns),
        "row_count": len(df),
        "preview": preview,
        "license": client.get_license_info(),
    }


@router.post("/import", response_model=ImportResponse)
async def import_external_data(
    req: ImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Import external data as a new Dataset in the platform."""
    user_id = str(current_user.id)

    # Rate limit check (per hour)
    if not await _check_rate_limit(db, user_id, "import", MAX_IMPORT_PER_HOUR, 3600):
        raise HTTPException(
            status_code=429,
            detail=f"Batas impor terlampaui. Maksimal {MAX_IMPORT_PER_HOUR} impor per jam."
        )

    from app.services.external_data.source_registry import get_source
    import pandas as pd
    import os
    import hashlib

    client = get_source(req.source_slug)
    if not client:
        raise HTTPException(status_code=404, detail=f"Source '{req.source_slug}' not found")

    try:
        df = await client.fetch(req.result_id)
    except Exception as e:
        logger.error(f"Import fetch failed for {req.result_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from source")

    if df.empty:
        raise HTTPException(status_code=400, detail="No data returned from source")

    # Enforce size limit
    if len(df) > MAX_ROWS_FETCH:
        df = df.head(MAX_ROWS_FETCH)

    # Save as CSV
    datasets_dir = os.path.join("ml_artifacts", "datasets")
    os.makedirs(datasets_dir, exist_ok=True)
    file_hash = hashlib.md5(f"{req.source_slug}:{req.result_id}".encode()).hexdigest()[:12]
    filename = f"external_{req.source_slug}_{file_hash}.csv"
    filepath = os.path.join(datasets_dir, filename)
    df.to_csv(filepath, index=False)

    # Create dataset record
    dataset_id = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO datasets (id, name, description, file_path, owner_id, created_at) "
             "VALUES (:id, :name, :desc, :path, :owner, NOW())"),
        {"id": dataset_id, "name": f"[{req.source_slug.upper()}] {req.title}",
         "desc": req.description or f"Imported from {req.source_slug}", "path": filepath,
         "owner": user_id}
    )
    await db.commit()

    # Audit log
    await _log_audit(db, user_id, "external_data_import",
                     f"Imported {len(df)} rows from {req.source_slug}: {req.title[:100]}")

    # Update search log
    try:
        await db.execute(
            text("UPDATE external_data_search_logs SET imported = true, "
                 "selected_result_id = :result_id WHERE query_text LIKE :q "
                 "AND user_id = :uid ORDER BY created_at DESC LIMIT 1"),
            {"result_id": req.result_id, "q": f"%{req.title[:50]}%", "uid": user_id}
        )
        await db.commit()
    except Exception:
        pass

    logger.info(f"User {user_id} imported {len(df)} rows from {req.source_slug}")
    return ImportResponse(dataset_id=dataset_id, message="Dataset imported successfully")
