#!/usr/bin/env python3
"""Small, dependency-free service for a controlled load-shedding experiment."""

from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


ROUTES = {
    "essential": {"rank": 0, "budget_ms": 250, "cpu_ms": 2},
    "standard": {"rank": 1, "budget_ms": 400, "cpu_ms": 4},
    "deferrable": {"rank": 2, "budget_ms": 900, "cpu_ms": 8},
}


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


MODE = os.environ.get("SHEDDING_MODE", "combined").lower()
if MODE not in {"none", "load", "p95", "combined"}:
    raise SystemExit("SHEDDING_MODE must be none, load, p95, or combined")

MIN_SAMPLES = env_int("MIN_SAMPLES", 0)
if MIN_SAMPLES < 1:
    raise SystemExit("Set MIN_SAMPLES for this experiment; there is no universal default")

PORT = env_int("PORT", 8080)
HOST = os.environ.get("HOST", "127.0.0.1")
MAX_IN_FLIGHT = env_int("MAX_IN_FLIGHT", 256)
DEPENDENCY_CONCURRENCY = env_int("DEPENDENCY_CONCURRENCY", 8)
DEPENDENCY_WORK_MS = env_float("DEPENDENCY_WORK_MS", 40)
P95_WINDOW_SECONDS = env_int("P95_WINDOW_SECONDS", 300)
P95_EVAL_SECONDS = env_int("P95_EVAL_SECONDS", 60)
LOAD_THRESHOLD_PCT = env_float("LOAD_THRESHOLD_PCT", 80)
SEVERE_LOAD_THRESHOLD_PCT = env_float("SEVERE_LOAD_THRESHOLD_PCT", 90)

for route_id, route in ROUTES.items():
    route["budget_ms"] = env_float(
        f"P95_BUDGET_{route_id.upper()}_MS", route["budget_ms"]
    )
    route["cpu_ms"] = env_float(
        f"CPU_WORK_{route_id.upper()}_MS", route["cpu_ms"]
    )


class SharedDependency:
    """A bounded shared dependency whose queue can raise route latency."""

    def __init__(self, concurrency: int, work_ms: float) -> None:
        self._slots = threading.BoundedSemaphore(concurrency)
        self._work_seconds = work_ms / 1000
        self._lock = threading.Lock()
        self.busy = 0
        self.waiting = 0

    def call(self) -> None:
        with self._lock:
            self.waiting += 1
        self._slots.acquire()
        with self._lock:
            self.waiting -= 1
            self.busy += 1
        try:
            time.sleep(self._work_seconds)
        finally:
            with self._lock:
                self.busy -= 1
            self._slots.release()

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {"busy": self.busy, "waiting": self.waiting}


dependency = SharedDependency(DEPENDENCY_CONCURRENCY, DEPENDENCY_WORK_MS)


class State:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.samples: dict[str, deque[tuple[float, float]]] = {
            route_id: deque() for route_id in ROUTES
        }
        self.counters: dict[str, Counter[str]] = {
            route_id: Counter() for route_id in ROUTES
        }
        self.in_flight = 0
        self.resource_cpu_pct = 0.0
        self.p95_ms: dict[str, float | None] = {route_id: None for route_id in ROUTES}
        self.sample_counts: dict[str, int] = {route_id: 0 for route_id in ROUTES}
        self.breach_streak: dict[str, int] = {route_id: 0 for route_id in ROUTES}
        self.healthy_streak: dict[str, int] = {route_id: 0 for route_id in ROUTES}
        self.active_breach: set[str] = set()
        self.last_evaluation = time.time()

    @staticmethod
    def percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        rank = max(1, math.ceil(percentile * len(ordered)))
        return ordered[rank - 1]

    def attempt(self, route_id: str, priority_id: str | None) -> None:
        with self.lock:
            self.counters[route_id]["attempted"] += 1
            classification = "classified" if priority_id in ROUTES else "unclassified"
            self.counters[route_id][classification] += 1

    def try_admit(self, route_id: str, priority_id: str | None) -> str | None:
        priority = ROUTES.get(priority_id) if priority_id else None
        rank = priority["rank"] if priority else None
        with self.lock:
            cpu_pct = self.resource_cpu_pct
            active = sorted(self.active_breach, key=lambda item: ROUTES[item]["rank"])

        if rank is not None and MODE in {"load", "combined"}:
            if cpu_pct >= SEVERE_LOAD_THRESHOLD_PCT and rank >= 1:
                return f"resource utilization {cpu_pct:.1f}% reached the {SEVERE_LOAD_THRESHOLD_PCT:.0f}% tier"
            if cpu_pct >= LOAD_THRESHOLD_PCT and rank >= 2:
                return f"resource utilization {cpu_pct:.1f}% reached the {LOAD_THRESHOLD_PCT:.0f}% tier"

        if rank is not None and MODE in {"p95", "combined"} and active:
            protected_route = active[0]
            protected_rank = ROUTES[protected_route]["rank"]
            if rank > protected_rank:
                return f"limited to protect {protected_route} after its p95 breach"
            if rank == protected_rank and rank == max(item["rank"] for item in ROUTES.values()):
                return f"this lowest-priority route breached its own p95 budget"

        with self.lock:
            if self.in_flight >= MAX_IN_FLIGHT:
                return "service concurrency capacity is full"
            self.in_flight += 1
            self.counters[route_id]["admitted"] += 1
        return None

    def record_shed(self, route_id: str, reason: str) -> None:
        with self.lock:
            self.counters[route_id]["shed"] += 1
            self.counters[route_id][f"shed:{reason.split()[0]}"] += 1

    def finish(self, route_id: str, duration_ms: float, success: bool) -> None:
        now = time.monotonic()
        with self.lock:
            self.in_flight = max(0, self.in_flight - 1)
            self.counters[route_id]["completed"] += 1
            if success:
                self.samples[route_id].append((now, duration_ms))
            else:
                self.counters[route_id]["errors"] += 1

    def evaluate_p95(self) -> None:
        now = time.monotonic()
        cutoff = now - P95_WINDOW_SECONDS
        with self.lock:
            for route_id, route in ROUTES.items():
                window = self.samples[route_id]
                while window and window[0][0] < cutoff:
                    window.popleft()
                values = [duration for _, duration in window]
                count = len(values)
                value = self.percentile(values, 0.95)
                self.sample_counts[route_id] = count
                self.p95_ms[route_id] = value

                if count < MIN_SAMPLES:
                    self.breach_streak[route_id] = 0
                    self.healthy_streak[route_id] = 0
                    continue

                if value is not None and value > route["budget_ms"]:
                    self.breach_streak[route_id] += 1
                    self.healthy_streak[route_id] = 0
                    if self.breach_streak[route_id] >= 2:
                        self.active_breach.add(route_id)
                else:
                    self.healthy_streak[route_id] += 1
                    self.breach_streak[route_id] = 0
                    if self.healthy_streak[route_id] >= 2:
                        self.active_breach.discard(route_id)

            self.last_evaluation = time.time()

    def snapshot(self) -> dict[str, Any]:
        dep = dependency.snapshot()
        with self.lock:
            route_metrics = {}
            for route_id, route in ROUTES.items():
                count = self.sample_counts[route_id]
                route_metrics[route_id] = {
                    "priority_rank": route["rank"],
                    "p95_ms": self.p95_ms[route_id],
                    "budget_ms": route["budget_ms"],
                    "sample_count": count,
                    "sample_status": "sufficient" if count >= MIN_SAMPLES else "insufficient",
                    "breach_checks": self.breach_streak[route_id],
                    "healthy_checks": self.healthy_streak[route_id],
                    "protected_by_p95": route_id in self.active_breach,
                    **dict(self.counters[route_id]),
                }
            return {
                "mode": MODE,
                "resource_signal": "service process CPU as percentage of one-core budget",
                "resource_cpu_pct": round(self.resource_cpu_pct, 2),
                "in_flight": self.in_flight,
                "max_in_flight": MAX_IN_FLIGHT,
                "shared_dependency": {
                    **dep,
                    "capacity": DEPENDENCY_CONCURRENCY,
                    "work_ms": DEPENDENCY_WORK_MS,
                },
                "load_threshold_pct": LOAD_THRESHOLD_PCT,
                "severe_load_threshold_pct": SEVERE_LOAD_THRESHOLD_PCT,
                "p95_window_seconds": P95_WINDOW_SECONDS,
                "p95_evaluation_seconds": P95_EVAL_SECONDS,
                "minimum_samples": MIN_SAMPLES,
                "last_p95_evaluation_epoch": self.last_evaluation,
                "routes": route_metrics,
            }


state = State()


def burn_cpu(milliseconds: float) -> None:
    if milliseconds <= 0:
        return
    deadline = time.perf_counter() + milliseconds / 1000
    value = 1
    while time.perf_counter() < deadline:
        value = (value * 33 + 17) & 0xFFFFFFFF
    if value == 0:
        raise RuntimeError("unreachable workload guard")


def cpu_monitor() -> None:
    previous_cpu = time.process_time()
    previous_wall = time.monotonic()
    while True:
        time.sleep(0.25)
        current_cpu = time.process_time()
        current_wall = time.monotonic()
        elapsed_wall = current_wall - previous_wall
        cpu_pct = ((current_cpu - previous_cpu) / elapsed_wall * 100) if elapsed_wall else 0
        with state.lock:
            state.resource_cpu_pct = min(100.0, max(0.0, cpu_pct))
        previous_cpu = current_cpu
        previous_wall = current_wall


def p95_controller() -> None:
    while True:
        time.sleep(P95_EVAL_SECONDS)
        state.evaluate_p95()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self.send_json(200, {"status": "ok"})
            return
        if path == "/metrics":
            self.send_json(200, state.snapshot())
            return

        route_id = path.removeprefix("/")
        if route_id not in ROUTES:
            self.send_json(404, {"error": "unknown route", "routes": list(ROUTES)})
            return

        priority_id = self.headers.get("X-Request-Priority")
        if priority_id not in ROUTES:
            priority_id = None

        started = time.perf_counter()
        state.attempt(route_id, priority_id)
        reason = state.try_admit(route_id, priority_id)
        if reason:
            state.record_shed(route_id, reason)
            self.send_json(429, {"route": route_id, "status": "shed", "reason": reason})
            return

        finalized = False
        try:
            dependency.call()
            burn_cpu(ROUTES[route_id]["cpu_ms"])
            duration_ms = (time.perf_counter() - started) * 1000
            self.send_json(
                200,
                {
                    "route": route_id,
                    "status": "served",
                    "duration_ms": round(duration_ms, 2),
                    "resource_cpu_pct": round(state.resource_cpu_pct, 2),
                },
            )
            state.finish(route_id, duration_ms, success=True)
            finalized = True
        except (BrokenPipeError, ConnectionResetError):
            duration_ms = (time.perf_counter() - started) * 1000
            if not finalized:
                state.finish(route_id, duration_ms, success=False)
        except Exception as error:
            duration_ms = (time.perf_counter() - started) * 1000
            if not finalized:
                state.finish(route_id, duration_ms, success=False)
            try:
                self.send_json(500, {"route": route_id, "error": str(error)})
            except (BrokenPipeError, ConnectionResetError):
                pass


class LabHTTPServer(ThreadingHTTPServer):
    # Keep overload decisions inside the service policy, rather than rejecting
    # TCP connections at the base server's very small accept backlog.
    request_queue_size = 2048


def configure_cpu_budget() -> None:
    if not hasattr(os, "sched_getaffinity") or os.environ.get("PIN_ONE_CORE", "1") != "1":
        return
    available = sorted(os.sched_getaffinity(0))
    if available:
        os.sched_setaffinity(0, {available[0]})


def main() -> None:
    configure_cpu_budget()
    threading.Thread(target=cpu_monitor, daemon=True, name="cpu-monitor").start()
    threading.Thread(target=p95_controller, daemon=True, name="p95-controller").start()
    server = LabHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print(
        f"service listening on :{PORT}; mode={MODE}; min_samples={MIN_SAMPLES}; "
        f"p95_window={P95_WINDOW_SECONDS}s; eval={P95_EVAL_SECONDS}s",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
