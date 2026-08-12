"""Service layer for scraping operations — eliminates DB insert duplication."""
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional

from app.services.scraper.shared import make_json_safe
from app.ml.scrape_processor import ScrapeDataProcessor

logger = logging.getLogger(__name__)

processor = ScrapeDataProcessor()


class ScrapingService:
    """Centralized scraping persistence logic shared by all scrape endpoints."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def build_ml_applied_list(
        run_advanced_analysis: bool = False,
        run_sentiment: bool = False,
        run_patterns: bool = False,
        extra: Optional[List[str]] = None,
    ) -> List[str]:
        ml_applied = ["type_detection", "dedup", "quality_scoring"]
        if run_advanced_analysis:
            ml_applied.append("advanced_analysis")
        if run_sentiment:
            ml_applied.append("sentiment_analysis")
        if run_patterns:
            ml_applied.append("pattern_detection")
        if extra:
            ml_applied.extend(extra)
        return ml_applied

    @staticmethod
    def build_scrape_metadata(**fields: Any) -> Dict[str, Any]:
        return make_json_safe(fields)

    @staticmethod
    def process_rows(
        rows: List[Dict[str, Any]],
        **process_kwargs: Any,
    ) -> Dict[str, Any]:
        """Run the scrape data processor on collected rows."""
        return processor.process(rows=rows, **process_kwargs)

    def _build_insert_sql(self, scrape_type: str) -> str:
        """Build INSERT statement; batch_results is only inserted for non-discover types."""
        batch_col_clause = (
            ", batch_results" if scrape_type in ("batch", "recursive") else ""
        )
        batch_val_clause = (
            ", :batch_results" if scrape_type in ("batch", "recursive") else ""
        )
        return f"""
            INSERT INTO scrape_jobs (
                id, user_id, url, title, status,
                raw_row_count, clean_row_count, column_count, duplicates_removed,
                tables_data, lists_data, metadata,
                processed_data, columns_typed, columns_renamed,
                quality_score, quality_issues, clusters,
                ml_processing_applied,
                advanced_analysis, sentiment_analysis, pattern_analysis,
                scrape_metadata,
                {batch_col_clause}
                content_hash, scrape_type,
                created_at, scraped_at, processed_at
            ) VALUES (
                gen_random_uuid(), :user_id, :url, :title, :status,
                :raw_row_count, :clean_row_count, :column_count, :duplicates_removed,
                :tables_data, :lists_data, :metadata,
                :processed_data, :columns_typed, :columns_renamed,
                :quality_score, :quality_issues, :clusters,
                :ml_processing_applied,
                :advanced_analysis, :sentiment_analysis, :pattern_analysis,
                :scrape_metadata,
                {batch_val_clause}
                :content_hash, :scrape_type,
                NOW(), NOW(), NOW()
            ) RETURNING id
        """

    async def save_scrape_job(
        self,
        user_id: str,
        url: str,
        title: str,
        status: str,
        processed: Any,
        tables_data: Any = None,
        lists_data: Any = None,
        metadata: Optional[Dict] = None,
        ml_applied: Optional[List[str]] = None,
        scrape_metadata: Optional[Dict] = None,
        scrape_type: str = "single",
        batch_results: Optional[List] = None,
        content_hash: str = "",
    ) -> Optional[str]:
        """Insert a scrape job record and return the generated UUID string."""
        insert_sql = self._build_insert_sql(scrape_type)
        params: Dict[str, Any] = {
            "user_id": user_id,
            "url": url,
            "title": title,
            "status": status,
            "scrape_type": scrape_type,
            "raw_row_count": processed.raw_row_count,
            "clean_row_count": processed.clean_row_count,
            "column_count": processed.column_count,
            "duplicates_removed": processed.duplicates_removed,
            "tables_data": make_json_safe(tables_data) if tables_data is not None else [],
            "lists_data": make_json_safe(lists_data) if lists_data is not None else [],
            "metadata": make_json_safe(metadata) if metadata is not None else {},
            "processed_data": make_json_safe(processor.to_dict_list(processed)),
            "columns_typed": make_json_safe(processed.columns_typed),
            "columns_renamed": make_json_safe(processed.columns_renamed),
            "quality_score": float(processed.quality_score),
            "quality_issues": make_json_safe(processed.quality_issues),
            "clusters": make_json_safe(processed.clusters),
            "ml_processing_applied": ml_applied or [],
            "advanced_analysis": make_json_safe(processed.advanced_analysis),
            "sentiment_analysis": make_json_safe(processed.sentiment_analysis),
            "pattern_analysis": make_json_safe(processed.pattern_analysis),
            "scrape_metadata": make_json_safe(scrape_metadata) if scrape_metadata is not None else {},
            "content_hash": content_hash,
        }
        if scrape_type in ("batch", "recursive"):
            params["batch_results"] = make_json_safe(batch_results) if batch_results is not None else []

        try:
            result = await self.db.execute(text(insert_sql), params)
            await self.db.commit()
            row = result.fetchone()
            return str(row[0]) if row else None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save scrape job: {e}")
            raise

    async def fetch_job_by_id(
        self,
        job_id: str,
        user_id: str,
    ) -> Optional[Any]:
        """Fetch a single scrape job row by id and user_id."""
        result = await self.db.execute(
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
        return result.fetchone()

    async def list_jobs(
        self,
        user_id: str,
        limit: int = 20,
        scrape_type: Optional[str] = None,
    ) -> List[Any]:
        """List scrape jobs for a user with optional type filter."""
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
        params: Dict[str, Any] = {"user_id": user_id, "limit": limit}
        if scrape_type:
            query += " AND scrape_type = :scrape_type"
            params["scrape_type"] = scrape_type
        query += " ORDER BY created_at DESC LIMIT :limit"
        result = await self.db.execute(text(query), params)
        return result.fetchall()

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a scrape job. Returns True if a row was deleted."""
        result = await self.db.execute(
            text("DELETE FROM scrape_jobs WHERE id = :job_id AND user_id = :user_id RETURNING id"),
            {"job_id": job_id, "user_id": user_id},
        )
        await self.db.commit()
        return result.fetchone() is not None

    async def fetch_processed_data(
        self,
        job_id: str,
        user_id: str,
    ) -> Optional[Any]:
        """Fetch processed_data, row_count, and column_count for import."""
        result = await self.db.execute(
            text("""
                SELECT id, title, processed_data, clean_row_count, column_count
                FROM scrape_jobs
                WHERE id = :job_id AND user_id = :user_id AND status = 'completed'
            """),
            {"job_id": job_id, "user_id": user_id},
        )
        return result.fetchone()
