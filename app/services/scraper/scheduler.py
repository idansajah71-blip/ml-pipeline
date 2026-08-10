"""Scrape Scheduler — Celery-based periodic scraping with monitoring."""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

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


@dataclass
class ScrapeSchedule:
    id: str
    user_id: str
    name: str
    urls: list[str]
    cron_expression: str = "0 * * * *"
    interval_minutes: int = 60
    is_active: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    config: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "urls": self.urls,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "is_active": self.is_active,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "config": self.config,
            "created_at": self.created_at,
        }


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
            # Create a simple wrapper for non-Celery environments
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

    def create_schedule(self, user_id: str, name: str, urls: list[str],
                       interval_minutes: int = 60, config: dict = None) -> dict:
        import uuid
        schedule_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        next_run = now + timedelta(minutes=interval_minutes)
        schedule = ScrapeSchedule(
            id=schedule_id, user_id=user_id, name=name, urls=urls,
            interval_minutes=interval_minutes,
            next_run=next_run.isoformat(),
            config=config or {},
            created_at=now.isoformat(),
        )
        return schedule.to_dict()

    def trigger_now(self, schedule_id: str, urls: list[str], config: dict = None) -> dict:
        task = run_scheduled_scrape.delay(schedule_id, urls, config or {})
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
