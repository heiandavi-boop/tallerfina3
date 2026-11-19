#!/usr/bin/env python3
"""In-process technical efficiency benchmark (R6.2-Cr6).

Runs the real FastAPI application through Starlette's TestClient (ASGI, no sockets):
it measures model + application latency and throughput, excluding network/HTTP server
overhead. It complements reports/efficiency/ (live HTTP) and never measures human productivity.

Scenarios: individual predictions (1/10/50/100), CSV batches (10/50/100), what-if,
concurrency (1/4/8/16 workers), validation failures, and GenAI timeout fault injection
(provider call replaced by a local Timeout, so no external service is contacted).
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DEFAULT_CASES = ROOT / "reports" / "efficiency" / "benchmark_cases.csv"
DEFAULT_OUTPUT = ROOT / "reports" / "efficiency" / "inprocess_2026"
INDIVIDUAL_SIZES = (1, 10, 50, 100)
CSV_SIZES = (10, 50, 100)
CONCURRENCY = (1, 4, 8, 16)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def latency_stats(latencies: list[float]) -> dict[str, float]:
    return {
        "p50_ms": round(percentile(latencies, 0.5), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "mean_ms": round(statistics.fmean(latencies), 3),
        "max_ms": round(max(latencies), 3),
    }


def load_cases(path: Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path)
    return frame.drop(columns=["case_order", "project_id"], errors="ignore").to_dict("records")


def timed(call: Callable[[], Any]) -> tuple[float, Any]:
    started = time.perf_counter()
    result = call()
    return (time.perf_counter() - started) * 1000, result


def _resources_before() -> tuple[float, float]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime, time.perf_counter()


def _resources_after(before: tuple[float, float]) -> dict[str, float]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu = usage.ru_utime + usage.ru_stime - before[0]
    wall = time.perf_counter() - before[1]
    # ru_maxrss is bytes on macOS and KiB on Linux.
    rss_mb = usage.ru_maxrss / (1024 * 1024) if sys.platform == "darwin" else usage.ru_maxrss / 1024
    return {"cpu_seconds": round(cpu, 3), "cpu_utilization_pct_of_one_core": round(cpu / wall * 100, 1) if wall else 0.0, "peak_rss_mb": round(rss_mb, 1)}


def scenario_individual(client, cases: list[dict[str, Any]], size: int) -> dict[str, Any]:
    before = _resources_before()
    latencies, failures = [], 0
    started = time.perf_counter()
    for case in cases[:size]:
        ms, response = timed(lambda: client.post("/api/predict?include_recommendations=false", json=case))
        latencies.append(ms)
        failures += response.status_code != 200
    total = (time.perf_counter() - started) * 1000
    return {"scenario": f"individual_{size}", "requests": size, "successes": size - failures, "failures": failures,
            "total_ms": round(total, 3), "throughput_rps": round(size / (total / 1000), 2), **latency_stats(latencies), **_resources_after(before)}


def scenario_with_recommendations(client, cases: list[dict[str, Any]], size: int) -> dict[str, Any]:
    """Deterministic grounded recommendations (provider none): the path used when GenAI is off or fails."""
    before = _resources_before()
    latencies, failures = [], 0
    for case in cases[:size]:
        ms, response = timed(lambda: client.post("/api/predict", json=case, headers={"X-PRUNIN-Provider": "none"}))
        latencies.append(ms)
        failures += response.status_code != 200
    total = sum(latencies)
    return {"scenario": f"deterministic_recommendations_{size}", "requests": size, "successes": size - failures, "failures": failures,
            "total_ms": round(total, 3), "throughput_rps": round(size / (total / 1000), 2), **latency_stats(latencies), **_resources_after(before)}


def scenario_csv(client, cases: list[dict[str, Any]], size: int, repetitions: int = 3) -> dict[str, Any]:
    payload = pd.DataFrame(cases[:size]).to_csv(index=False).encode("utf-8")
    before = _resources_before()
    latencies, failures, row_errors = [], 0, 0
    for _ in range(repetitions):
        ms, response = timed(lambda: client.post("/api/predict-csv", files={"file": ("bench.csv", io.BytesIO(payload), "text/csv")}))
        latencies.append(ms)
        failures += response.status_code != 200
        if response.status_code == 200:
            row_errors += sum(row["error"] is not None for row in response.json()["rows"])
    median = percentile(latencies, 0.5)
    return {"scenario": f"csv_{size}", "requests": repetitions, "rows_per_request": size, "successes": repetitions - failures, "failures": failures,
            "row_errors": row_errors, "total_ms": round(sum(latencies), 3), "throughput_rows_per_s": round(size / (median / 1000), 2),
            **latency_stats(latencies), **_resources_after(before)}


def scenario_concurrency(client, cases: list[dict[str, Any]], workers: int, requests_total: int = 100) -> dict[str, Any]:
    def one(index: int) -> tuple[float, int]:
        ms, response = timed(lambda: client.post("/api/predict?include_recommendations=false", json=cases[index % len(cases)]))
        return ms, response.status_code

    before = _resources_before()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, range(requests_total)))
    total = (time.perf_counter() - started) * 1000
    latencies = [ms for ms, _ in results]
    failures = sum(status != 200 for _, status in results)
    return {"scenario": f"concurrency_{workers}", "workers": workers, "requests": requests_total, "successes": requests_total - failures,
            "failures": failures, "total_ms": round(total, 3), "throughput_rps": round(requests_total / (total / 1000), 2),
            **latency_stats(latencies), **_resources_after(before)}


def scenario_invalid_inputs(client, case: dict[str, Any]) -> dict[str, Any]:
    probes = {
        # 5/7 trained features (71 %) is accepted by design; 3/7 (43 %) must hit the 60 % coverage gate.
        "partial_coverage_accepted": {k: v for k, v in case.items() if k not in {"spi", "cpi"}},
        "insufficient_coverage": {k: v for k, v in case.items() if k not in {"spi", "cpi", "true_progress", "planned_budget"}},
        "wrong_type": {**case, "spi": "alto"},
        "unknown_provider": None,
    }
    expected = {"partial_coverage_accepted": 200}
    outcomes = {}
    for name, payload in probes.items():
        if payload is None:
            response = client.post("/api/predict", json=case, headers={"X-PRUNIN-Provider": "desconocido"})
        else:
            response = client.post("/api/predict?include_recommendations=false", json=payload)
        outcomes[name] = response.status_code
    as_expected = {name: (status == expected[name]) if name in expected else 400 <= status < 500 for name, status in outcomes.items()}
    return {"scenario": "invalid_inputs", "requests": len(outcomes), "status_codes": outcomes, "controlled_rejections": all(as_expected.values()),
            "successes": sum(as_expected.values()), "failures": sum(not ok for ok in as_expected.values())}


def scenario_genai_timeout(client, cases: list[dict[str, Any]], size: int = 10) -> dict[str, Any]:
    """Injects requests.Timeout into the local Ollama transport; predictions must still succeed via fallback."""
    import requests
    from prunin_ai.api import recommendations as ai

    original = ai.requests.post
    old_enabled = os.environ.get("PRUNIN_ENABLE_OLLAMA")
    os.environ["PRUNIN_ENABLE_OLLAMA"] = "1"

    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("injected timeout")

    ai.requests.post = raise_timeout
    try:
        latencies, fallbacks, failures = [], 0, 0
        for case in cases[:size]:
            ms, response = timed(lambda: client.post("/api/predict", json=case, headers={"X-PRUNIN-Provider": "ollama"}))
            latencies.append(ms)
            if response.status_code != 200:
                failures += 1
                continue
            recommendation = response.json()["recommendations"]
            fallbacks += recommendation.get("genai_used") is False and recommendation.get("failure_code") == "ollama_timeout"
    finally:
        ai.requests.post = original
        if old_enabled is None:
            os.environ.pop("PRUNIN_ENABLE_OLLAMA", None)
        else:
            os.environ["PRUNIN_ENABLE_OLLAMA"] = old_enabled
    return {"scenario": "genai_timeout_fault_injection", "requests": size, "successes": size - failures, "failures": failures,
            "deterministic_fallbacks": fallbacks, "fallback_rate": round(fallbacks / size, 3), **latency_stats(latencies)}


def git_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run(cases: list[dict[str, Any]]) -> dict[str, Any]:
    os.environ.setdefault("PRUNIN_ENABLE_OLLAMA", "0")
    from fastapi.testclient import TestClient

    from prunin_ai.api import app as app_module
    with TestClient(app_module.app) as client:
        for case in cases[:3]:
            client.post("/api/predict?include_recommendations=false", json=case)  # warm-up, excluded
        scenarios = [scenario_individual(client, cases, size) for size in INDIVIDUAL_SIZES]
        scenarios += [scenario_with_recommendations(client, cases, 50)]
        scenarios += [scenario_csv(client, cases, size) for size in CSV_SIZES]
        scenarios += [scenario_concurrency(client, cases, workers) for workers in CONCURRENCY]
        scenarios.append(scenario_invalid_inputs(client, cases[0]))
        scenarios.append(scenario_genai_timeout(client, cases))
        model_version = app_module.runtime.version
    base = next(s for s in scenarios if s["scenario"] == "concurrency_1")
    degradation = {
        s["scenario"]: {"p95_ratio_vs_1_worker": round(s["p95_ms"] / base["p95_ms"], 2), "throughput_ratio_vs_1_worker": round(s["throughput_rps"] / base["throughput_rps"], 2)}
        for s in scenarios if s["scenario"].startswith("concurrency_")
    }
    individual_100 = next(s for s in scenarios if s["scenario"] == "individual_100")
    csv_100 = next(s for s in scenarios if s["scenario"] == "csv_100")
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "measurement": "in_process_asgi_testclient",
        "scope_note": "Mide la aplicación FastAPI y los modelos sin red ni servidor HTTP; no mide productividad humana ni escalabilidad de clúster.",
        "git_commit": git_sha(),
        "model_version": model_version,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count()},
        "cases_file": str(DEFAULT_CASES.relative_to(ROOT)),
        "scenarios": scenarios,
        "concurrency_degradation": degradation,
        "csv_vs_individual_100": {
            "individual_total_ms": individual_100["total_ms"],
            "csv_median_ms": csv_100["p50_ms"],
            "time_reduction_pct": round((individual_100["total_ms"] - csv_100["p50_ms"]) / individual_100["total_ms"] * 100, 1),
        },
        "genai_live_latency": "NO MEDIDA en esta ejecución: proveedores generativos no accesibles desde el entorno; ver reports/genai/provider_comparison_2026/.",
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Benchmark técnico en proceso (ASGI)",
        "",
        f"Generado: {summary['generated_at']} · commit `{summary['git_commit']}` · modelo `{summary['model_version']}` · {summary['environment']['platform']}",
        "",
        summary["scope_note"],
        "",
        "| Escenario | Solicitudes | Éxitos | Fallos | p50 ms | p95 ms | Throughput |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summary["scenarios"]:
        throughput = s.get("throughput_rps", s.get("throughput_rows_per_s", "—"))
        unit = " filas/s" if "throughput_rows_per_s" in s else (" req/s" if "throughput_rps" in s else "")
        lines.append(f"| {s['scenario']} | {s['requests']} | {s['successes']} | {s['failures']} | {s.get('p50_ms', '—')} | {s.get('p95_ms', '—')} | {throughput}{unit} |")
    comparison = summary["csv_vs_individual_100"]
    lines += [
        "",
        f"CSV de 100 filas frente a 100 solicitudes individuales: {comparison['csv_median_ms']} ms frente a {comparison['individual_total_ms']} ms ({comparison['time_reduction_pct']} % menos tiempo de máquina).",
        "",
        "Degradación por concurrencia (relativa a 1 worker): " + "; ".join(f"{k}: p95×{v['p95_ratio_vs_1_worker']}, throughput×{v['throughput_ratio_vs_1_worker']}" for k, v in summary["concurrency_degradation"].items()),
        "",
        "Interpretación: si el throughput se mantiene casi constante mientras el p95 crece con los workers, la inferencia está limitada por un único proceso (GIL/CPU). La capacidad debe escalar horizontalmente (más procesos o réplicas), no con más hilos; esto motiva las réplicas y el HPA de deploy/k8s/.",
        "",
        f"IA generativa en vivo: {summary['genai_live_latency']}",
        "",
        "Limitaciones: un solo proceso y una sola máquina; TestClient serializa parte del trabajo en el event loop; los valores no son extrapolables a un clúster.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    summary = run(load_cases(args.cases))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(render_markdown(summary), encoding="utf-8")
    print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
