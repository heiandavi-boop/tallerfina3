#!/usr/bin/env python3
"""Measure local FastAPI HTTP prediction latency under bounded concurrency.

This benchmark does not call external providers and must only target a local or
explicitly authorized PRUNIN API. It records individual results and a separate
controlled fallback/recovery probe.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import resource
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from operational_efficiency import ACADEMIC_FEATURES

THREAD_LOCAL = threading.local()


def _session() -> requests.Session:
    if not hasattr(THREAD_LOCAL, "session"):
        session = requests.Session()
        token = os.getenv("PRUNIN_API_TOKEN")
        if token:
            session.headers["Authorization"] = f"Bearer {token}"
        THREAD_LOCAL.session = session
    return THREAD_LOCAL.session


def _valid_prediction(body: dict[str, Any]) -> bool:
    prediction = body.get("prediction")
    return isinstance(prediction, dict) and all(
        prediction.get(name) is not None
        for name in ("health", "delay_days", "cost_overrun_ratio")
    )


def preflight(api_url: str, timeout: float) -> dict[str, Any]:
    session = _session()
    ready_response = session.get(f"{api_url}/api/ready", timeout=timeout)
    ready_response.raise_for_status()
    health_response = session.get(f"{api_url}/api/health", timeout=timeout)
    health_response.raise_for_status()
    genai_response = session.get(f"{api_url}/api/genai-status", timeout=timeout)
    genai_response.raise_for_status()
    ready, health, genai = ready_response.json(), health_response.json(), genai_response.json()
    if ready.get("status") != "ready" or health.get("version") != "0.9.0-academic":
        raise RuntimeError("Preflight failed: expected ready API serving 0.9.0-academic.")
    if genai.get("enabled") is not False:
        raise RuntimeError("Preflight failed: concurrency benchmark requires GenAI disabled.")
    if set(health.get("trained_features", [])) != set(ACADEMIC_FEATURES):
        raise RuntimeError("Preflight failed: API does not expose the seven academic features.")
    return {
        "artifact_version": health.get("version"),
        "dataset_source": health.get("dataset_source"),
        "api_mode": health.get("mode"),
        "genai_enabled": False,
        "trained_features": health.get("trained_features"),
    }


def _one_request(index: int, cases: pd.DataFrame, api_url: str, timeout: float) -> dict[str, Any]:
    row = cases.iloc[index % len(cases)]
    payload = {feature: row[feature] for feature in ACADEMIC_FEATURES}
    started = time.perf_counter()
    status: int | None = None
    error: str | None = None
    valid = False
    try:
        response = _session().post(
            f"{api_url}/api/predict?include_recommendations=false",
            json=payload,
            timeout=timeout,
        )
        status = response.status_code
        if status == 200:
            valid = _valid_prediction(response.json())
            if not valid:
                error = "invalid_prediction_shape"
        else:
            error = f"http_{status}"
    except (requests.RequestException, ValueError) as exc:
        error = type(exc).__name__
    return {
        "request_index": index,
        "case_index": index % len(cases),
        "latency_ms": (time.perf_counter() - started) * 1000,
        "http_status": status,
        "success": valid,
        "error": error,
    }


def _scenario(cases: pd.DataFrame, api_url: str, workers: int, requests_total: int, timeout: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _session().post(
        f"{api_url}/api/predict?include_recommendations=false",
        json={feature: cases.iloc[0][feature] for feature in ACADEMIC_FEATURES},
        timeout=timeout,
    ).raise_for_status()
    before_cpu = resource.getrusage(resource.RUSAGE_SELF)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        raw = list(executor.map(
            lambda index: _one_request(index, cases, api_url, timeout),
            range(requests_total),
        ))
    wall_s = time.perf_counter() - started
    after_cpu = resource.getrusage(resource.RUSAGE_SELF)
    latencies = [item["latency_ms"] for item in raw]
    successes = sum(item["success"] for item in raw)
    summary = {
        "workers": workers,
        "requests": requests_total,
        "successes": successes,
        "failures": requests_total - successes,
        "success_rate": successes / requests_total,
        "latency_p50_ms": float(np.quantile(latencies, 0.50)),
        "latency_p95_ms": float(np.quantile(latencies, 0.95)),
        "latency_mean_ms": statistics.fmean(latencies),
        "latency_max_ms": max(latencies),
        "throughput_requests_per_s": requests_total / wall_s,
        "wall_time_s": wall_s,
        "process_cpu_s": (
            after_cpu.ru_utime + after_cpu.ru_stime - before_cpu.ru_utime - before_cpu.ru_stime
        ),
        "process_peak_rss_bytes": after_cpu.ru_maxrss,
    }
    return summary, raw


def _recovery_probe(api_url: str, case: dict[str, Any], timeout: float) -> dict[str, Any]:
    session = _session()
    invalid = {**case, "project_type": "__invalid_for_recovery_probe__"}
    invalid_response = session.post(
        f"{api_url}/api/predict?include_recommendations=false", json=invalid, timeout=timeout
    )
    health_response = session.get(f"{api_url}/api/health", timeout=timeout)
    recovery_response = session.post(
        f"{api_url}/api/predict?include_recommendations=false", json=case, timeout=timeout
    )
    return {
        "controlled_invalid_input_status": invalid_response.status_code,
        "health_after_invalid_input_status": health_response.status_code,
        "valid_prediction_after_invalid_input_status": recovery_response.status_code,
        "recovered": (
            invalid_response.status_code == 422
            and health_response.status_code == 200
            and recovery_response.status_code == 200
            and _valid_prediction(recovery_response.json())
        ),
        "scope": "Recovery after a controlled request error; no API process or instance was stopped.",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    api_url = args.api_url.rstrip("/")
    metadata = preflight(api_url, args.timeout)
    cases = pd.read_csv(args.cases, low_memory=False)
    missing = set(ACADEMIC_FEATURES) - set(cases.columns)
    if cases.empty or missing:
        raise ValueError(f"Benchmark cases are empty or missing features: {sorted(missing)}")
    summaries, raw = [], []
    for workers in args.workers:
        summary, rows = _scenario(cases, api_url, workers, args.requests_per_level, args.timeout)
        summaries.append(summary)
        raw.extend({"workers": workers, **row} for row in rows)
    recovery = _recovery_probe(
        api_url,
        {feature: cases.iloc[0][feature] for feature in ACADEMIC_FEATURES},
        args.timeout,
    )
    return {
        "status": "complete" if all(item["failures"] == 0 for item in summaries) and recovery["recovered"] else "completed_with_failures",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "measurement": "real_local_http",
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "api_url": api_url,
            **metadata,
        },
        "cases_file": str(args.cases),
        "case_count": int(len(cases)),
        "requests_per_level": args.requests_per_level,
        "concurrency": summaries,
        "controlled_error_recovery": recovery,
        "limitations": [
            "Una sola máquina y un solo proceso API; no prueba balanceo ni escalabilidad horizontal.",
            "No se terminó ninguna instancia; la recuperación medida es tras una entrada inválida controlada.",
            "CPU y RSS son del proceso cliente, no del servidor API.",
            "GenAI estuvo desactivada; esta prueba no mide latencia/capacidad del motor Ollama.",
        ],
        "retraining_triggered": False,
    }, raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    parser.add_argument("--cases", type=Path, default=ROOT / "reports/efficiency/benchmark_cases.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/technical_closure/http_concurrency_2026")
    parser.add_argument("--workers", type=lambda value: [int(x) for x in value.split(",")], default=[1, 4, 8, 16])
    parser.add_argument("--requests-per-level", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    if any(workers <= 0 for workers in args.workers) or args.requests_per_level <= 0 or args.timeout <= 0:
        parser.error("workers, requests-per-level y timeout deben ser positivos")
    try:
        summary, raw = run(args)
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(json.dumps({"status": "unavailable_or_failed", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "http_concurrency_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pd.DataFrame(raw).to_csv(output / "http_concurrency_raw.csv", index=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
