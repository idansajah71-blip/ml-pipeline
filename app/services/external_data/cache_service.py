"""Cache service for external data search & fetch results.

Caches search results and fetched data in the database to avoid
redundant API calls to external sources.
"""
import hashlib
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pandas as pd

from app.core.database import async_session_factory


# Cache TTL by source (in days)
SOURCE_CACHE_TTL = {
    "bps": 30,        # BPS data rarely changes
    "worldbank": 7,   # World Bank updates more frequently
    "datagoid": 14,   # data.go.id moderate update frequency
}
DEFAULT_CACHE_TTL = 7


def _hash_query(source_slug: str, query: str) -> str:
    """Generate a hash key for a search query."""
    raw = f"{source_slug}:{query.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def get_cached_search(
    source_slug: str,
    query: str,
) -> Optional[List[dict]]:
    """Check if search results are already cached and not expired."""
    query_hash = _hash_query(source_slug, query)
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, title, description, preview_data, row_count,
                       columns, source_url, license_note, fetched_at, expires_at
                FROM external_dataset_cache
                WHERE source_id = (
                    SELECT id FROM external_data_sources WHERE slug = :slug
                )
                AND query_hash = :hash
                AND expires_at > NOW()
                ORDER BY fetched_at DESC
                LIMIT 50
            """),
            {"slug": source_slug, "hash": query_hash},
        )
        rows = result.fetchall()
        if not rows:
            return None
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "description": r[2],
                "preview_data": r[3],
                "row_count": r[4],
                "columns": r[5],
                "source_url": r[6],
                "license_note": r[7],
                "fetched_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]


async def cache_search_results(
    source_slug: str,
    query: str,
    results: list,
    ttl_days: Optional[int] = None,
) -> None:
    """Store search results in cache."""
    query_hash = _hash_query(source_slug, query)
    ttl = ttl_days or SOURCE_CACHE_TTL.get(source_slug, DEFAULT_CACHE_TTL)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl)

    async with async_session_factory() as session:
        for r in results:
            await session.execute(
                text("""
                    INSERT INTO external_dataset_cache
                    (id, source_id, query_hash, title, description, row_count,
                     columns, source_url, license_note, fetched_at, expires_at)
                    SELECT
                        gen_random_uuid(),
                        (SELECT id FROM external_data_sources WHERE slug = :slug),
                        :hash, :title, :desc, :row_count,
                        :columns, :source_url, :license, NOW(), :expires
                """),
                {
                    "slug": source_slug,
                    "hash": query_hash,
                    "title": r.get("title", ""),
                    "desc": r.get("description", ""),
                    "row_count": r.get("row_count"),
                    "columns": r.get("column_names", []),
                    "source_url": r.get("source_url"),
                    "license": r.get("license_note"),
                    "expires": expires_at,
                },
            )
        await session.commit()


async def cache_fetched_data(
    source_slug: str,
    result_id: str,
    title: str,
    df: pd.DataFrame,
    license_note: str = "",
    ttl_days: Optional[int] = None,
) -> str:
    """Cache fetched data (full DataFrame) to disk + DB. Returns the file path."""
    ttl = ttl_days or SOURCE_CACHE_TTL.get(source_slug, DEFAULT_CACHE_TTL)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl)

    # Save to disk
    cache_dir = os.path.join("ml_artifacts", "external_cache")
    os.makedirs(cache_dir, exist_ok=True)
    safe_id = result_id.replace(":", "_").replace("/", "_")
    filename = f"{source_slug}_{safe_id}.csv"
    filepath = os.path.join(cache_dir, filename)
    df.to_csv(filepath, index=False)

    # Store metadata in DB
    async with async_session_factory() as session:
        await session.execute(
            text("""
                INSERT INTO external_dataset_cache
                (id, source_id, query_hash, title, full_data_path, row_count,
                 column_count, columns, fetched_at, expires_at)
                SELECT
                    gen_random_uuid(),
                    (SELECT id FROM external_data_sources WHERE slug = :slug),
                    :hash, :title, :path, :rows, :cols, :col_names, NOW(), :expires
            """),
            {
                "slug": source_slug,
                "hash": hashlib.sha256(result_id.encode()).hexdigest()[:32],
                "title": title,
                "path": filepath,
                "rows": len(df),
                "cols": len(df.columns),
                "col_names": list(df.columns),
                "expires": expires_at,
            },
        )
        await session.commit()

    return filepath


async def cleanup_expired_cache() -> int:
    """Delete expired cache entries. Returns count of deleted entries."""
    async with async_session_factory() as session:
        # Delete expired entries
        result = await session.execute(
            text("""
                DELETE FROM external_dataset_cache
                WHERE expires_at < NOW()
                RETURNING id
            """)
        )
        deleted = result.fetchall()
        await session.commit()
        return len(deleted)
