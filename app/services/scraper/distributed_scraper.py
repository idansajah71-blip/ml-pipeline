"""Distributed Scraper — Celery-based multi-worker parallel scraping with coordination."""
import asyncio
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class WorkerStatus:
    worker_id: str = ""
    status: str = "idle"
    current_task: str = ""
    tasks_completed: int = 0
    errors: int = 0
    last_heartbeat: str = ""
    avg_response_time_ms: float = 0.0
    proxy_used: str = ""

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id, "status": self.status,
            "current_task": self.current_task, "tasks_completed": self.tasks_completed,
            "errors": self.errors, "avg_response_time_ms": self.avg_response_time_ms,
        }


@dataclass
class DistributedJob:
    job_id: str = ""
    urls: list[str] = field(default_factory=list)
    total_urls: int = 0
    completed_urls: int = 0
    failed_urls: int = 0
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    workers_used: int = 0
    strategy: str = "round_robin"
    results: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    avg_time_per_url: float = 0.0

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id, "total_urls": self.total_urls,
            "completed_urls": self.completed_urls, "failed_urls": self.failed_urls,
            "status": self.status, "progress": round(self.completed_urls / max(self.total_urls, 1) * 100, 1),
            "workers_used": self.workers_used, "strategy": self.strategy,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "avg_time_per_url": round(self.avg_time_per_url, 2),
        }


class DistributedScraper:

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._jobs: Dict[str, DistributedJob] = {}
        self._workers: Dict[str, WorkerStatus] = {}
        self._proxies: list[str] = []
        self._task_queue: list[dict] = []
        self._results: Dict[str, list[dict]] = {}
        self._init_workers()

    def _init_workers(self):
        for i in range(self.max_workers):
            worker_id = f"worker_{i}"
            self._workers[worker_id] = WorkerStatus(worker_id=worker_id)

    def set_proxies(self, proxies: list[str]):
        self._proxies = proxies

    def create_job(self, urls: list[str], strategy: str = "round_robin",
                   max_per_worker: int = None) -> str:
        import uuid
        job_id = uuid.uuid4().hex[:12]
        job = DistributedJob(
            job_id=job_id, urls=urls, total_urls=len(urls),
            status="pending", strategy=strategy, started_at=datetime.now().isoformat(),
        )
        self._jobs[job_id] = job
        self._results[job_id] = []

        chunks = self._distribute_urls(urls, strategy, max_per_worker)
        for worker_id, chunk in chunks.items():
            self._task_queue.append({
                "job_id": job_id, "worker_id": worker_id, "urls": chunk,
            })

        return job_id

    def _distribute_urls(self, urls: list[str], strategy: str,
                         max_per_worker: int = None) -> Dict[str, list[str]]:
        chunks = {f"worker_{i}": [] for i in range(self.max_workers)}
        per = max_per_worker or (len(urls) // self.max_workers + 1)

        if strategy == "round_robin":
            for i, url in enumerate(urls):
                worker = f"worker_{i % self.max_workers}"
                if max_per_worker and len(chunks[worker]) >= max_per_worker:
                    continue
                chunks[worker].append(url)

        elif strategy == "chunk":
            for i in range(0, len(urls), per):
                worker_idx = min(i // per, self.max_workers - 1)
                chunks[f"worker_{worker_idx}"].extend(urls[i:i + per])

        elif strategy == "least_loaded":
            for url in urls:
                min_worker = min(chunks.keys(), key=lambda w: len(chunks[w]))
                chunks[min_worker].append(url)

        elif strategy == "priority":
            for url in urls:
                chunks["worker_0"].append(url)

        elif strategy == "hash":
            for url in urls:
                h = int(hashlib.md5(url.encode()).hexdigest()[:8], 16)
                worker_idx = h % self.max_workers
                chunks[f"worker_{worker_idx}"].append(url)

        return {w: u for w, u in chunks.items() if u}

    async def execute_job(self, job_id: str, scrape_fn=None) -> DistributedJob:
        job = self._jobs[job_id]
        job.status = "running"
        job.started_at = datetime.now().isoformat()

        if scrape_fn is None:
            scrape_fn = self._default_scrape

        tasks = self._task_queue.copy()
        self._task_queue.clear()
        job.workers_used = len(tasks)

        all_results = []
        all_errors = []
        completed = 0

        async def _process_url(url: str, worker_id: str, proxy: str):
            nonlocal completed
            worker = self._workers[worker_id]
            worker.status = "busy"
            try:
                start = datetime.now()
                result = await scrape_fn(url, proxy)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                worker.avg_response_time_ms = (worker.avg_response_time_ms * worker.tasks_completed + elapsed) / (worker.tasks_completed + 1)
                worker.tasks_completed += 1
                completed += 1
                job.completed_urls = completed
                result["worker_id"] = worker_id
                result["elapsed_ms"] = elapsed
                all_results.append(result)
            except Exception as e:
                worker.errors += 1
                job.failed_urls += 1
                all_errors.append({"url": url, "worker": worker_id, "error": str(e)})
            finally:
                worker.status = "idle"

        for task in tasks:
            worker_id = task["worker_id"]
            proxy = self._proxies[int(worker_id.split("_")[1]) % len(self._proxies)] if self._proxies else ""
            await asyncio.gather(*[_process_url(url, worker_id, proxy) for url in task["urls"]])

        job.results = all_results
        job.errors = all_errors
        job.status = "completed"
        job.completed_at = datetime.now().isoformat()
        total_ms = sum(r.get("elapsed_ms", 0) for r in all_results)
        job.avg_time_per_url = total_ms / max(len(all_results), 1)
        return job

    async def _default_scrape(self, url: str, proxy: str = "") -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        }
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
                resp = await client.get(url, proxy=proxy or None)
                resp.raise_for_status()
                return {"url": url, "status_code": resp.status_code, "content_length": len(resp.content)}
        except Exception:
            try:
                from curl_cffi import requests as curl_requests
                resp = curl_requests.get(url, impersonate="chrome", timeout=30, allow_redirects=True)
                return {"url": url, "status_code": resp.status_code, "content_length": len(resp.text)}
            except Exception as e:
                return {"url": url, "status_code": 0, "content_length": 0, "error": str(e)}

    def get_job(self, job_id: str) -> Optional[DistributedJob]:
        return self._jobs.get(job_id)

    def get_workers(self) -> list[dict]:
        return [w.to_dict() for w in self._workers.values()]

    def get_queue_size(self) -> int:
        return len(self._task_queue)
