"""Scrape Scheduler — Celery-based periodic scraping with DB persistence."""
import asyncio
import logging
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_config import ScrapeSchedule as ScrapeScheduleModel

logger = logging.getLogger(__name__)

HAS_CELERY = False
celery_app = None

try:
    from celery import Celery as _CeleryClass
    from app.core.celery_app import celery_app as _celery
    if _celery is not None and isinstance(_celery, _CeleryClass):
        celery_app = _celery
        HAS_CELERY = True
except (ImportError, Exception):
    pass


def _run_async(coro):
    """Run async code in Celery task safely."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=300)
        else:
            return loop.run_until_complete(coro)
    except (RuntimeError, TimeoutError):
        return asyncio.run(coro)


def _make_task(func=None, task_name=None):
    """Create a Celery task or a simple wrapper."""
    def decorator(f):
        if HAS_CELERY and celery_app is not None:
            return celery_app.task(bind=True, name=task_name)(f)
        else:
            class SimpleTask:
                def __init__(self, fn):
                    self.fn = fn
                    self.name = task_name

                def delay(self, *args, **kwargs):
                    logger.warning(f"Celery not available, running {task_name} synchronously")
                    import inspect
                    sig = inspect.signature(self.fn)
                    params = list(sig.parameters.keys())
                    if params and params[0] == "self":
                        return self.fn(None, *args, **kwargs)
                    return self.fn(*args, **kwargs)

                def AsyncResult(self, task_id):
                    class FakeResult:
                        state = "UNAVAILABLE"
                        result = None
                        info = "Celery not installed"
                        def ready(self):
                            return True
                        def revoke(self, *args, **kwargs):
                            pass
                    return FakeResult()

                def revoke(self, *args, **kwargs):
                    pass

            return SimpleTask(f)

    if func is not None:
        return decorator(func)
    return decorator


@_make_task(task_name="scraper.run_scheduled_scrape")
def run_scheduled_scrape(self, schedule_id: str, urls: list[str], config: dict):
    from app.services.scraper.multi_scraper import MultiScraper
    from app.ml.scrape_processor import ScrapeDataProcessor

    task_id = self.request.id
    start = datetime.now()

    try:
        multi = MultiScraper(max_concurrent=config.get("max_concurrent", 3))

        async def _scrape():
            return await multi.scrape_batch(
                urls=urls,
                extract_tables=config.get("extract_tables", True),
                extract_lists=config.get("extract_lists", True),
                max_retries=config.get("max_retries", 3),
            )

        batch_result = _run_async(_scrape())

        all_rows = []
        for table in batch_result.combined_tables:
            all_rows.extend(table.get("rows", []))

        processor = ScrapeDataProcessor()

        processed = processor.process(
            rows=all_rows,
            run_advanced_analysis=config.get("run_advanced_analysis", True),
            run_sentiment=config.get("run_sentiment", False),
            run_patterns=config.get("run_patterns", False),
        )

        duration = (datetime.now() - start).total_seconds()
        return {
            "status": "completed",
            "schedule_id": schedule_id,
            "task_id": task_id,
            "rows_scraped": batch_result.total_rows,
            "pages_scraped": batch_result.successful,
            "pages_failed": batch_result.failed,
            "quality_score": processed.quality_score,
            "duration_seconds": round(duration, 2),
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "status": "failed",
            "schedule_id": schedule_id,
            "task_id": task_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
        }


@_make_task(task_name="scraper.cleanup_old_results")
def cleanup_old_results(self, days: int = 30):
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async def _cleanup():
        cutoff = datetime.now() - timedelta(days=days)
        async with async_session_factory() as session:
            result = await session.execute(
                text("DELETE FROM scrape_jobs WHERE created_at < :cutoff RETURNING id"),
                {"cutoff": cutoff},
            )
            deleted = result.fetchall()
            await session.commit()
            return len(deleted)

    count = _run_async(_cleanup())
    return {"deleted": count, "cutoff_days": days}


class ScrapeScheduler:

    def __init__(self, db: AsyncSession = None):
        self._db = db

    def _set_db(self, db: AsyncSession):
        self._db = db

    async def create_schedule(
        self,
        user_id: str,
        name: str,
        url: str,
        config: dict = None,
        cron_expression: str = "0 2 * * *",
        interval_minutes: int = 1440,
        template_id: str = None,
    ) -> Dict:
        now = datetime.now(timezone.utc)
        next_run = now + timedelta(minutes=interval_minutes)
        schedule = ScrapeScheduleModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if len(user_id) == 36 else user_id,
            name=name,
            url=url,
            config=config or {},
            cron_expression=cron_expression,
            interval_minutes=interval_minutes,
            is_active=True,
            next_run_at=next_run,
            template_id=uuid.UUID(template_id) if template_id else None,
        )
        self._db.add(schedule)
        await self._db.commit()
        await self._db.refresh(schedule)
        return schedule.to_dict()

    async def list_user_schedules(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeScheduleModel)
            .where(ScrapeScheduleModel.user_id == user_id)
            .order_by(ScrapeScheduleModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [s.to_dict() for s in result.scalars().all()]

    async def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeScheduleModel).where(ScrapeScheduleModel.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        return schedule.to_dict() if schedule else None

    async def update_schedule(self, schedule_id: str, **kwargs) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeScheduleModel).where(ScrapeScheduleModel.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None
        for key, value in kwargs.items():
            if hasattr(schedule, key) and key not in ("id", "user_id", "created_at"):
                setattr(schedule, key, value)
        await self._db.commit()
        await self._db.refresh(schedule)
        return schedule.to_dict()

    async def delete_schedule(self, schedule_id: str) -> bool:
        result = await self._db.execute(
            select(ScrapeScheduleModel).where(ScrapeScheduleModel.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return False
        await self._db.delete(schedule)
        await self._db.commit()
        return True

    async def toggle_active(self, schedule_id: str, is_active: bool) -> Optional[Dict]:
        return await self.update_schedule(schedule_id, is_active=is_active)

    def trigger_now(self, schedule_id: str, url: str, config: dict = None) -> dict:
        task = run_scheduled_scrape.delay(schedule_id, [url], config or {})
        return {
            "task_id": task.id,
            "schedule_id": schedule_id,
            "status": "triggered",
        }

    def get_task_status(self, task_id: str) -> dict:
        result = run_scheduled_scrape.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.state,
            "result": result.result if result.ready() else None,
            "info": str(result.info) if result.info else None,
        }

    def cancel_task(self, task_id: str) -> dict:
        try:
            run_scheduled_scrape.AsyncResult(task_id).revoke(terminate=True)
            return {"task_id": task_id, "status": "revoked"}
        except Exception as e:
            return {"task_id": task_id, "status": "error", "error": str(e)}
