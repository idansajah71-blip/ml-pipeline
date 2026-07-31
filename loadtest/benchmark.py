import asyncio
import aiohttp
import time
import json
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import statistics


@dataclass
class BenchmarkResult:
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float


class APIBenchmark:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.results: List[Dict] = []

    def _get_headers(self) -> Dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        **kwargs
    ) -> Dict:
        start_time = time.time()
        try:
            async with session.request(
                method,
                url,
                headers=self._get_headers(),
                **kwargs
            ) as response:
                await response.read()
                duration = time.time() - start_time
                return {
                    "status": response.status,
                    "duration": duration,
                    "success": 200 <= response.status < 400,
                }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "status": 0,
                "duration": duration,
                "success": False,
                "error": str(e),
            }

    async def benchmark_endpoint(
        self,
        method: str,
        endpoint: str,
        num_requests: int = 100,
        concurrency: int = 10,
        **kwargs
    ) -> BenchmarkResult:
        url = f"{self.base_url}{endpoint}"
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_request(session):
            async with semaphore:
                return await self._make_request(session, method, url, **kwargs)

        async with aiohttp.ClientSession() as session:
            tasks = [limited_request(session) for _ in range(num_requests)]
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

        durations = [r["duration"] for r in results]
        successful = sum(1 for r in results if r["success"])

        return BenchmarkResult(
            endpoint=endpoint,
            method=method,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=num_requests - successful,
            avg_response_time=statistics.mean(durations) if durations else 0,
            min_response_time=min(durations) if durations else 0,
            max_response_time=max(durations) if durations else 0,
            p50_response_time=statistics.median(durations) if durations else 0,
            p95_response_time=sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            p99_response_time=sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
            requests_per_second=num_requests / total_time if total_time > 0 else 0,
            error_rate=(num_requests - successful) / num_requests if num_requests > 0 else 0,
        )

    async def run_full_benchmark(self) -> List[BenchmarkResult]:
        endpoints = [
            ("GET", "/health", 100, 10),
            ("GET", "/api/v1/algorithms", 100, 10),
            ("GET", "/api/v1/datasets", 50, 5),
            ("GET", "/api/v1/models", 50, 5),
            ("GET", "/api/v1/experiments", 50, 5),
            ("GET", "/api/v1/monitoring/stats", 50, 5),
            ("GET", "/docs", 100, 10),
        ]

        results = []
        for method, endpoint, num_requests, concurrency in endpoints:
            print(f"Benchmarking {method} {endpoint}...")
            result = await self.benchmark_endpoint(
                method, endpoint, num_requests, concurrency
            )
            results.append(result)

        return results


def print_results(results: List[BenchmarkResult]):
    print("\n" + "=" * 100)
    print("BENCHMARK RESULTS")
    print("=" * 100)
    print(f"{'Endpoint':<40} {'Reqs':<8} {'Avg(ms)':<10} {'P50(ms)':<10} {'P95(ms)':<10} {'RPS':<10} {'Errors':<8}")
    print("-" * 100)

    for result in results:
        print(
            f"{result.method} {result.endpoint:<37} "
            f"{result.total_requests:<8} "
            f"{result.avg_response_time*1000:<10.2f} "
            f"{result.p50_response_time*1000:<10.2f} "
            f"{result.p95_response_time*1000:<10.2f} "
            f"{result.requests_per_second:<10.2f} "
            f"{result.error_rate*100:<7.2f}%"
        )

    print("=" * 100)


async def main():
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        login_data = {
            "email": "admin@mlpipeline.com",
            "password": "admin123",
        }
        async with session.post(f"{base_url}/api/v1/auth/login", json=login_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("access_token")
            else:
                token = None

    benchmark = APIBenchmark(base_url, token)
    results = await benchmark.run_full_benchmark()
    print_results(results)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"loadtest/benchmark_{timestamp}.json", "w") as f:
        json.dump(
            [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "total_requests": r.total_requests,
                    "avg_response_time_ms": r.avg_response_time * 1000,
                    "p95_response_time_ms": r.p95_response_time * 1000,
                    "requests_per_second": r.requests_per_second,
                    "error_rate": r.error_rate,
                }
                for r in results
            ],
            f,
            indent=2,
        )
    print(f"\nResults saved to loadtest/benchmark_{timestamp}.json")


if __name__ == "__main__":
    asyncio.run(main())
