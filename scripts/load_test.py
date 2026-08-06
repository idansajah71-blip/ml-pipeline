"""
ML Pipeline Load Test Script
============================
Uses httpx + asyncio to simulate concurrent users hitting key API endpoints.

Usage:
    python scripts/load_test.py [--base-url http://localhost:8000] [--users 20] [--duration 30]
"""

import asyncio
import argparse
import time
import statistics
from dataclasses import dataclass, field
from typing import List

import httpx


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    latency_ms: float
    error: str = ""


@dataclass
class LoadTestReport:
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    by_endpoint: dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_s: float = 0

    @property
    def rps(self) -> float:
        return self.total_requests / self.duration_s if self.duration_s > 0 else 0

    @property
    def p50(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0

    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0
        s = sorted(self.latencies)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0
        s = sorted(self.latencies)
        idx = int(len(s) * 0.99)
        return s[min(idx, len(s) - 1)]

    @property
    def error_rate(self) -> float:
        return (self.failed / self.total_requests * 100) if self.total_requests > 0 else 0


async def register_and_login(client: httpx.AsyncClient) -> str:
    email = f"loadtest_{int(time.time()*1000)}@test.com"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "username": email.split("@")[0],
        "password": "loadtest123",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "loadtest123",
    })
    return res.json().get("access_token", "")


async def worker(
    worker_id: int,
    base_url: str,
    duration_s: float,
    report: LoadTestReport,
):
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        try:
            token = await register_and_login(client)
        except Exception as e:
            report.errors.append(f"Worker {worker_id}: Auth failed: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}
        end_time = time.time() + duration_s

        while time.time() < end_time:
            # Rotate through endpoints
            endpoints = [
                ("GET", "/api/v1/quota", None),
                ("GET", "/api/v1/quota/check", None),
                ("GET", "/api/v1/models", None),
                ("GET", "/api/v1/datasets", None),
                ("GET", "/api/v1/experiments", None),
            ]

            for method, path, body in endpoints:
                if time.time() >= end_time:
                    break
                start = time.time()
                try:
                    if method == "GET":
                        res = await client.get(path, headers=headers)
                    else:
                        res = await client.post(path, headers=headers, json=body)
                    latency = (time.time() - start) * 1000

                    result = RequestResult(
                        endpoint=f"{method} {path}",
                        status_code=res.status_code,
                        latency_ms=latency,
                    )
                except Exception as e:
                    latency = (time.time() - start) * 1000
                    result = RequestResult(
                        endpoint=f"{method} {path}",
                        status_code=0,
                        latency_ms=latency,
                        error=str(e),
                    )

                report.total_requests += 1
                report.latencies.append(result.latency_ms)

                if result.endpoint not in report.by_endpoint:
                    report.by_endpoint[result.endpoint] = {"total": 0, "success": 0, "fail": 0, "latencies": []}
                report.by_endpoint[result.endpoint]["total"] += 1
                report.by_endpoint[result.endpoint]["latencies"].append(result.latency_ms)

                if 200 <= result.status_code < 400:
                    report.successful += 1
                    report.by_endpoint[result.endpoint]["success"] += 1
                else:
                    report.failed += 1
                    report.by_endpoint[result.endpoint]["fail"] += 1
                    if result.error:
                        report.errors.append(f"Worker {worker_id}: {result.endpoint} -> {result.error}")

            await asyncio.sleep(0.1)


def print_report(report: LoadTestReport):
    print("\n" + "=" * 60)
    print("  ML PIPELINE LOAD TEST RESULTS")
    print("=" * 60)

    print(f"\n  Duration:           {report.duration_s:.1f}s")
    print(f"  Total Requests:     {report.total_requests}")
    print(f"  Successful:         {report.successful}")
    print(f"  Failed:             {report.failed}")
    print(f"  Error Rate:         {report.error_rate:.1f}%")
    print(f"  Requests/sec:       {report.rps:.1f}")

    print(f"\n  Latency (ms):")
    print(f"    P50:              {report.p50:.1f}")
    print(f"    P95:              {report.p95:.1f}")
    print(f"    P99:              {report.p99:.1f}")
    if report.latencies:
        print(f"    Min:              {min(report.latencies):.1f}")
        print(f"    Max:              {max(report.latencies):.1f}")
        print(f"    Avg:              {statistics.mean(report.latencies):.1f}")

    print(f"\n  By Endpoint:")
    print(f"  {'Endpoint':<30} {'Reqs':>6} {'OK':>6} {'Fail':>6} {'Avg(ms)':>10}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*6} {'-'*10}")
    for ep, data in sorted(report.by_endpoint.items()):
        avg = statistics.mean(data["latencies"]) if data["latencies"] else 0
        print(f"  {ep:<30} {data['total']:>6} {data['success']:>6} {data['fail']:>6} {avg:>10.1f}")

    if report.errors:
        print(f"\n  Errors (first 10):")
        for err in report.errors[:10]:
            print(f"    - {err[:80]}")

    print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="ML Pipeline Load Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=15, help="Test duration in seconds")
    args = parser.parse_args()

    print(f"Starting load test: {args.users} users, {args.duration}s duration")
    print(f"Target: {args.base_url}")

    report = LoadTestReport()
    start_time = time.time()

    tasks = [worker(i, args.base_url, args.duration, report) for i in range(args.users)]
    await asyncio.gather(*tasks)

    report.duration_s = time.time() - start_time
    print_report(report)


if __name__ == "__main__":
    asyncio.run(main())
