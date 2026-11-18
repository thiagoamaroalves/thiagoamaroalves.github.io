#!/usr/bin/env python3
"""Fixed-arrival-rate load generator using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any


ROUTES = ("essential", "standard", "deferrable")


def parse_weights(raw: str) -> tuple[list[str], list[int]]:
    weights: dict[str, int] = {}
    for item in raw.split(","):
        name, value = item.split(":", 1)
        if name not in ROUTES:
            raise argparse.ArgumentTypeError(f"unknown route in weights: {name}")
        weights[name] = int(value)
    for route in ROUTES:
        weights.setdefault(route, 0)
    if any(value < 0 for value in weights.values()) or sum(weights.values()) <= 0:
        raise argparse.ArgumentTypeError("route weights must be non-negative and sum above zero")
    return list(weights), list(weights.values())


def request_once(url: str, route: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    status = 0
    message = ""
    try:
        request = urllib.request.Request(
            f"{url.rstrip('/')}/{route}",
            headers={"User-Agent": "priority-shedding-lab/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        message = str(error.reason)
        error.read()
    except Exception as error:  # Keep one failed request from ending the run.
        message = f"{type(error).__name__}: {error}"
    return {
        "route": route,
        "status": status,
        "duration_ms": (time.perf_counter() - started) * 1000,
        "message": message,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return round(ordered[index], 2)


def run(args: argparse.Namespace) -> dict[str, Any]:
    names, weights = parse_weights(args.weights)
    chooser = random.Random(args.seed)
    request_interval = 1 / args.rate
    deadline = time.perf_counter() + args.duration
    next_start = time.perf_counter()
    pending: set[Future[dict[str, Any]]] = set()
    results: list[dict[str, Any]] = []
    schedule_drops = 0

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        while time.perf_counter() < deadline or pending:
            now = time.perf_counter()
            if now < deadline and now >= next_start:
                if now - next_start >= request_interval:
                    missed = int((now - next_start) / request_interval)
                    schedule_drops += missed
                    next_start += missed * request_interval
                if len(pending) < args.max_workers:
                    route = chooser.choices(names, weights=weights, k=1)[0]
                    pending.add(executor.submit(request_once, args.base_url, route, args.timeout))
                else:
                    schedule_drops += 1
                next_start += request_interval
                continue

            timeout = 0.05
            if now < deadline:
                timeout = min(timeout, max(0, next_start - now))
            if pending:
                done, pending = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
                results.extend(future.result() for future in done)
            elif timeout > 0:
                time.sleep(timeout)

    per_route: dict[str, Any] = {}
    for route in ROUTES:
        route_results = [item for item in results if item["route"] == route]
        statuses = Counter(str(item["status"]) for item in route_results)
        served_latencies = [item["duration_ms"] for item in route_results if item["status"] == 200]
        per_route[route] = {
            "responses": len(route_results),
            "served": statuses.get("200", 0),
            "shed_429": statuses.get("429", 0),
            "other_errors": sum(count for status, count in statuses.items() if status not in {"200", "429"}),
            "p95_served_ms": percentile(served_latencies, 0.95),
        }

    return {
        "target": args.base_url,
        "configured_rate_per_second": args.rate,
        "duration_seconds": args.duration,
        "weights": args.weights,
        "max_workers": args.max_workers,
        "seed": args.seed,
        "completed_responses": len(results),
        "client_schedule_drops": schedule_drops,
        "routes": per_route,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--rate", type=float, required=True, help="total offered requests per second")
    parser.add_argument("--duration", type=float, default=60, help="test duration in seconds")
    parser.add_argument("--weights", default="essential:10,standard:30,deferrable:60")
    parser.add_argument("--max-workers", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, help="optional path for the JSON summary")
    args = parser.parse_args()
    if args.rate <= 0 or args.duration <= 0 or args.max_workers < 1:
        parser.error("rate and duration must be positive; max-workers must be at least 1")

    result = run(args)
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
