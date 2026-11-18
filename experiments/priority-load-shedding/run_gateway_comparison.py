#!/usr/bin/env python3
"""Run paired direct-service and gateway-classified load experiments on Linux."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
WEIGHTS = "essential:10,standard:30,deferrable:60"
SEED = "7"
MAX_WORKERS = "2048"


def affinity(cpu: int):
    def apply() -> None:
        os.sched_setaffinity(0, {cpu})

    return apply


def wait_for_health(url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"process exited before becoming healthy: {url}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (TimeoutError, URLError, OSError):
            time.sleep(0.25)
    raise TimeoutError(f"service did not become healthy: {url}")


def read_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def run_load(
    name: str,
    base_url: str,
    metrics_url: str,
    rate: int,
    duration: int,
    output_dir: Path,
) -> dict[str, Any]:
    output_file = output_dir / f"{name}.json"
    command = [
        sys.executable,
        str(HERE / "loadgen.py"),
        "--base-url",
        base_url,
        "--rate",
        str(rate),
        "--duration",
        str(duration),
        "--weights",
        WEIGHTS,
        "--max-workers",
        MAX_WORKERS,
        "--timeout",
        "90",
        "--seed",
        SEED,
        "--output",
        str(output_file),
    ]
    process = subprocess.Popen(
        command,
        cwd=HERE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=affinity(1),
    )
    started = time.monotonic()
    samples: list[dict[str, Any]] = []
    while process.poll() is None:
        try:
            metrics = read_json(metrics_url)
            samples.append(
                {
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "resource_cpu_pct": metrics["resource_cpu_pct"],
                    "in_flight": metrics["in_flight"],
                    "shared_dependency": metrics["shared_dependency"],
                    "routes": {
                        route: {
                            key: metrics["routes"][route].get(key)
                            for key in (
                                "attempted",
                                "classified",
                                "unclassified",
                                "shed",
                                "p95_ms",
                                "sample_count",
                                "protected_by_p95",
                            )
                        }
                        for route in ("essential", "standard", "deferrable")
                    },
                }
            )
        except (KeyError, TimeoutError, URLError, OSError):
            pass
        time.sleep(1)

    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"load generator failed ({process.returncode}): {stderr or stdout}")
    result = json.loads(output_file.read_text(encoding="utf-8"))
    monitor_path = output_dir / f"{name}-monitor.json"
    monitor_path.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    essential_activation = next(
        (
            sample["elapsed_seconds"]
            for sample in samples
            if sample["routes"]["essential"]["protected_by_p95"]
        ),
        None,
    )
    result["service_monitor"] = {
        "samples": len(samples),
        "max_service_cpu_pct": max(
            (sample["resource_cpu_pct"] for sample in samples), default=None
        ),
        "max_in_flight": max((sample["in_flight"] for sample in samples), default=None),
        "essential_protection_activated_seconds": essential_activation,
        "samples_file": monitor_path.name,
    }
    output_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_case(
    name: str,
    mode: str,
    gateway_enabled: bool,
    rate: int,
    duration: int,
    post_duration: int,
    service_settings: dict[str, str],
    output_dir: Path,
) -> dict[str, Any]:
    print(f"Starting {name}: {rate} requests/s for {duration}s; gateway={gateway_enabled}.", flush=True)
    env = os.environ.copy()
    env.update(service_settings)
    env.update({"HOST": "127.0.0.1", "PORT": "8080", "SHEDDING_MODE": mode})
    service_log_path = output_dir / f"{name}-service.log"
    gateway_log_path = output_dir / f"{name}-gateway.log"
    service_log = service_log_path.open("w", encoding="utf-8")
    gateway_log = gateway_log_path.open("w", encoding="utf-8")
    service: subprocess.Popen[bytes] | None = None
    gateway: subprocess.Popen[bytes] | None = None
    try:
        service = subprocess.Popen(
            [sys.executable, str(HERE / "service.py")],
            cwd=HERE,
            env=env,
            stdout=service_log,
            stderr=subprocess.STDOUT,
            preexec_fn=affinity(0),
        )
        wait_for_health("http://127.0.0.1:8080/healthz", service)
        target = "http://127.0.0.1:8080"
        if gateway_enabled:
            gateway_env = os.environ.copy()
            gateway_env.update(
                {"GATEWAY_HOST": "127.0.0.1", "GATEWAY_PORT": "8081", "BACKEND_URL": target}
            )
            gateway = subprocess.Popen(
                [sys.executable, str(HERE / "gateway.py")],
                cwd=HERE,
                env=gateway_env,
                stdout=gateway_log,
                stderr=subprocess.STDOUT,
                preexec_fn=affinity(2),
            )
            wait_for_health("http://127.0.0.1:8081/healthz", gateway)
            target = "http://127.0.0.1:8081"

        measured = run_load(
            name,
            target,
            "http://127.0.0.1:8080/metrics",
            rate,
            duration,
            output_dir,
        )
        metrics = read_json("http://127.0.0.1:8080/metrics")
        metrics_path = output_dir / f"{name}-metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        result: dict[str, Any] = {
            "path": "through local priority gateway" if gateway_enabled else "direct to service; no priority header",
            "mode": mode,
            "configured_rate_per_second": rate,
            "duration_seconds": duration,
            "load_summary": measured,
            "service_metrics": metrics,
        }

        if post_duration:
            post_name = f"{name}-post-activation"
            result["post_activation"] = run_load(
                post_name,
                target,
                "http://127.0.0.1:8080/metrics",
                rate,
                post_duration,
                output_dir,
            )
            post_metrics = read_json("http://127.0.0.1:8080/metrics")
            (output_dir / f"{post_name}-metrics.json").write_text(
                json.dumps(post_metrics, indent=2) + "\n", encoding="utf-8"
            )
            result["post_activation_service_metrics"] = post_metrics
        return result
    finally:
        for process in (gateway, service):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        service_log.close()
        gateway_log.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("cpu", "p95", "all"), default="all")
    parser.add_argument("--output-dir", type=Path, default=HERE / "results/gateway-comparison")
    args = parser.parse_args()
    if not hasattr(os, "sched_setaffinity"):
        raise SystemExit("Run this comparison on Linux with taskset/CPU affinity support.")
    args.output_dir.mkdir(parents=True, exist_ok=False)

    comparison: dict[str, Any] = {
        "question": "Does a trusted priority signal let the service protect Essential requests under overload?",
        "control": "Requests reach the service directly without a priority header; all work is treated equally.",
        "treatment": "A local gateway overwrites any client priority header and assigns one from the workload route.",
        "weights": WEIGHTS,
        "seed": int(SEED),
        "max_workers": int(MAX_WORKERS),
        "cases": {},
    }

    if args.scenario in {"cpu", "all"}:
        cpu_settings = {
            "MIN_SAMPLES": "100",
            "MAX_IN_FLIGHT": "512",
            "DEPENDENCY_CONCURRENCY": "64",
            "DEPENDENCY_WORK_MS": "40",
        }
        comparison["cases"]["cpu_direct"] = run_case(
            "cpu-direct", "load", False, 180, 60, 0, cpu_settings, args.output_dir
        )
        comparison["cases"]["cpu_gateway"] = run_case(
            "cpu-gateway", "load", True, 180, 60, 0, cpu_settings, args.output_dir
        )

    if args.scenario in {"p95", "all"}:
        p95_settings = {
            "MIN_SAMPLES": "100",
            "MAX_IN_FLIGHT": "512",
            "DEPENDENCY_CONCURRENCY": "2",
            "DEPENDENCY_WORK_MS": "100",
            "P95_WINDOW_SECONDS": "300",
            "P95_EVAL_SECONDS": "60",
            "CPU_WORK_ESSENTIAL_MS": "0",
            "CPU_WORK_STANDARD_MS": "0",
            "CPU_WORK_DEFERRABLE_MS": "0",
        }
        comparison["cases"]["p95_direct"] = run_case(
            "p95-direct", "p95", False, 23, 300, 0, p95_settings, args.output_dir
        )
        comparison["cases"]["p95_gateway"] = run_case(
            "p95-gateway", "p95", True, 23, 300, 60, p95_settings, args.output_dir
        )

    summary_path = args.output_dir / "comparison-summary.json"
    summary_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "summary": str(summary_path)}, indent=2))


if __name__ == "__main__":
    main()
