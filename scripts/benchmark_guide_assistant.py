#!/usr/bin/env python3
"""Benchmark script for /ai/guide/assistant with fixed-rate load."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any

import httpx

from _bootstrap import PROJECT_ROOT  # noqa: F401


DEFAULT_URL = "http://127.0.0.1:8000/ai/guide/assistant"


@dataclass
class RequestResult:
    ok: bool
    status_code: int | None
    latency_ms: float
    error: str | None = None


@dataclass
class BenchmarkSummary:
    results: list[RequestResult]
    elapsed_s: float


def build_payload(mode: str, top_k: int) -> dict[str, Any]:
    if mode == "vector_search":
        return {
            "query": "帮我找几款通勤外套",
            "guide_id": "guide_001",
            "user_id": None,
            "sku": None,
            "top_k": top_k,
            "use_custom_plan": False,
        }

    return {
        "query": "这个用户看了这款商品很久，我该怎么回",
        "guide_id": "guide_001",
        "user_id": "user_001",
        "sku": "8WZ01CM1",
        "top_k": top_k,
        "use_custom_plan": True,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lower = int(k)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = k - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def single_request(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        start = time.perf_counter()
        try:
            response = await client.post(url, json=payload)
            latency_ms = (time.perf_counter() - start) * 1000
            return RequestResult(
                ok=response.status_code < 400,
                status_code=response.status_code,
                latency_ms=latency_ms,
                error=None if response.status_code < 400 else response.text[:200],
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            return RequestResult(
                ok=False,
                status_code=None,
                latency_ms=latency_ms,
                error=str(exc),
            )


async def run_benchmark(
    *,
    url: str,
    mode: str,
    qps: float,
    duration: int,
    concurrency: int,
    top_k: int,
    warmup: int,
    timeout: float,
) -> BenchmarkSummary:
    payload = build_payload(mode, top_k)
    semaphore = asyncio.Semaphore(concurrency)
    interval = 1.0 / qps
    results: list[RequestResult] = []
    benchmark_start = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout) as client:
        if warmup > 0:
            print(f"[warmup] running for {warmup}s at {qps} qps")
            warmup_end = time.perf_counter() + warmup
            while time.perf_counter() < warmup_end:
                await single_request(client, url, payload, semaphore)
                await asyncio.sleep(interval)

        print(f"[benchmark] mode={mode} qps={qps} duration={duration}s concurrency={concurrency}")
        tasks: list[asyncio.Task[RequestResult]] = []
        start = time.perf_counter()
        end = start + duration
        next_tick = start

        while True:
            now = time.perf_counter()
            if now >= end:
                break
            if now >= next_tick:
                tasks.append(
                    asyncio.create_task(
                        single_request(client, url, payload, semaphore)
                    )
                )
                next_tick += interval
            else:
                await asyncio.sleep(min(0.01, next_tick - now))

        if tasks:
            results.extend(await asyncio.gather(*tasks))

    return BenchmarkSummary(results=results, elapsed_s=time.perf_counter() - benchmark_start)


async def run_burst_benchmark(
    *,
    url: str,
    mode: str,
    concurrency: int,
    top_k: int,
    timeout: float,
) -> BenchmarkSummary:
    """Fire a single burst of N concurrent requests."""
    payload = build_payload(mode, top_k)
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=timeout) as client:
        print(f"[burst] mode={mode} concurrent_requests={concurrency}")
        start = time.perf_counter()
        tasks = [
            asyncio.create_task(single_request(client, url, payload, semaphore))
            for _ in range(concurrency)
        ]
        results = await asyncio.gather(*tasks)
        elapsed_s = time.perf_counter() - start
    return BenchmarkSummary(results=results, elapsed_s=elapsed_s)


def print_report(results: list[RequestResult], elapsed_s: float) -> None:
    total = len(results)
    success = sum(1 for item in results if item.ok)
    failed = total - success
    latencies = [item.latency_ms for item in results]
    actual_qps = total / elapsed_s if elapsed_s > 0 else 0.0

    print("=" * 72)
    print("Guide Assistant Benchmark Report")
    print("=" * 72)
    print(f"total_requests : {total}")
    print(f"success        : {success}")
    print(f"failed         : {failed}")
    print(f"elapsed_s      : {elapsed_s:.2f}")
    print(f"actual_qps     : {actual_qps:.2f}")
    if latencies:
        print(f"avg_ms         : {statistics.mean(latencies):.2f}")
        print(f"p50_ms         : {percentile(latencies, 0.50):.2f}")
        print(f"p95_ms         : {percentile(latencies, 0.95):.2f}")
        print(f"p99_ms         : {percentile(latencies, 0.99):.2f}")
        print(f"max_ms         : {max(latencies):.2f}")
    if failed:
        sample_errors = [item.error for item in results if item.error][:5]
        print("sample_errors  :")
        for error in sample_errors:
            print(f"  - {error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark /ai/guide/assistant safely.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target URL")
    parser.add_argument(
        "--mode",
        choices=["vector_search", "sales_graph"],
        default="vector_search",
        help="Guide assistant route to benchmark",
    )
    parser.add_argument("--qps", type=float, default=5.0, help="Target QPS")
    parser.add_argument("--duration", type=int, default=30, help="Benchmark duration in seconds")
    parser.add_argument("--concurrency", type=int, default=10, help="Max in-flight requests")
    parser.add_argument(
        "--burst-concurrency",
        type=int,
        default=0,
        help="Send one burst of N concurrent requests; if > 0, qps/duration are ignored",
    )
    parser.add_argument("--top-k", type=int, default=5, help="top_k payload value")
    parser.add_argument("--warmup", type=int, default=5, help="Warmup duration in seconds")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.burst_concurrency > 0:
        summary = await run_burst_benchmark(
            url=args.url,
            mode=args.mode,
            concurrency=args.burst_concurrency,
            top_k=args.top_k,
            timeout=args.timeout,
        )
    else:
        summary = await run_benchmark(
            url=args.url,
            mode=args.mode,
            qps=args.qps,
            duration=args.duration,
            concurrency=args.concurrency,
            top_k=args.top_k,
            warmup=args.warmup,
            timeout=args.timeout,
        )
    print_report(summary.results, summary.elapsed_s)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
