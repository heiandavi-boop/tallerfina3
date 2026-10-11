#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from prunin_ai.api.schema import ProjectInput
from operational_efficiency import (
    ACADEMIC_FEATURES,
    BATCH_SIZES,
    REPETITIONS_BY_SIZE,
    build_summary,
    project_case_hash,
    sample_test_cases,
)


RAW_FIELDS = [
    "mode", "batch_size", "repetition", "total_ms", "server_total_ms",
    "client_overhead_ms", "success_count", "error_count", "success_rate",
    "projects_per_second", "ms_per_project", "timestamp", "environment",
    "case_ids_sha256", "task", "http_status", "request_error_count",
    "response_error_count", "http_failure_count", "timeout_count",
    "coverage_block_count", "errors",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def current_git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def api_preflight(session: requests.Session, api_url: str, expected_artifact: str, timeout: float) -> tuple[dict[str, Any] | None, str | None, str | None]:
    base = api_url.rstrip("/")
    try:
        ready_response = session.get(f"{base}/api/ready", timeout=timeout)
        ready_response.raise_for_status()
        health_response = session.get(f"{base}/api/health", timeout=timeout)
        health_response.raise_for_status()
        genai_response = session.get(f"{base}/api/genai-status", timeout=timeout)
        genai_response.raise_for_status()
        ready = ready_response.json()
        health = health_response.json()
        genai = genai_response.json()
    except (requests.RequestException, ValueError) as exc:
        return None, None, f"No se pudo verificar la API académica: {type(exc).__name__}: {exc}"

    metadata = {
        "api_url": base,
        "api_status": ready.get("status"),
        "artifact_version": health.get("version"),
        "artifact_mode": health.get("mode"),
        "dataset_source": health.get("dataset_source"),
        "dataset_type": health.get("dataset_type"),
        "model_type": health.get("model_type"),
        "trained_features": health.get("trained_features", []),
        "genai_enabled": genai.get("enabled"),
        "genai_available": genai.get("available"),
    }
    if health.get("version") != expected_artifact:
        return health, metadata, f"API sirve artifact {health.get('version')!r}, se requiere {expected_artifact!r}."
    if health.get("dataset_source") != "Mendeley Data 2p5sz57wh2 version 2":
        return health, metadata, f"Fuente inesperada para benchmark académico: {health.get('dataset_source')!r}."
    if set(health.get("trained_features", [])) != set(ACADEMIC_FEATURES):
        return health, metadata, "El API no expone exactamente las siete features académicas requeridas."
    if genai.get("enabled") is not False:
        return health, metadata, "GenAI debe estar deshabilitada en el API usado por los modos individual y batch."
    return health, metadata, None


def environment_metadata(api_metadata: dict[str, Any], artifact_version: str) -> dict[str, Any]:
    return {
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_architecture": platform.machine(),
        "git_sha": current_git_sha(),
        "date_utc": utc_now(),
        "artifact_version": artifact_version,
        "api_mode": api_metadata.get("artifact_mode"),
        "api_url": api_metadata.get("api_url"),
        "dataset_source": api_metadata.get("dataset_source"),
        "dataset_type": api_metadata.get("dataset_type"),
        "model_type": api_metadata.get("model_type"),
        "ollama_enabled": api_metadata.get("genai_enabled"),
        "genai_enabled": api_metadata.get("genai_enabled"),
        "workers": os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS"),
        "workers_note": "API no expone workers; null significa no determinado por el proceso cliente.",
    }


def _validate_response_prediction(body: dict[str, Any]) -> tuple[bool, str | None, float | None]:
    prediction = body.get("prediction")
    if not isinstance(prediction, dict):
        return False, "missing_prediction", None
    required = ("health", "health_probabilities", "delay_days", "cost_overrun_ratio")
    if any(prediction.get(key) is None for key in required):
        return False, "missing_predictive_output", None
    quality = prediction.get("input_quality") or {}
    if quality.get("coverage") != 1.0 or quality.get("missing_count") != 0:
        return False, "incomplete_feature_coverage", None
    recommendations = body.get("recommendations") or {}
    if recommendations.get("engine") != "not_requested" or recommendations.get("genai_attempted") is not False:
        return False, "recommendations_not_disabled", None
    timing = body.get("timing") or {}
    server_ms = timing.get("total_ms")
    return True, None, float(server_ms) if isinstance(server_ms, (int, float)) else None


def _individual_run(
    session: requests.Session,
    api_url: str,
    cases: pd.DataFrame,
    *,
    batch_size: int,
    repetition: int,
    timeout: float,
    environment_json: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    server_total_ms = 0.0
    success_count = 0
    error_count = 0
    request_error_count = 0
    response_error_count = 0
    errors: list[str] = []
    http_statuses: list[int] = []
    for row in cases.to_dict("records"):
        payload = {feature: row[feature] for feature in ACADEMIC_FEATURES}
        try:
            response = session.post(
                f"{api_url.rstrip('/')}/api/predict?include_recommendations=false",
                json=payload,
                timeout=timeout,
            )
            http_statuses.append(response.status_code)
            if response.status_code != 200:
                error_count += 1
                response_error_count += 1
                errors.append(f"HTTP {response.status_code}: {response.text[:300]}")
                continue
            body = response.json()
            valid, error, server_ms = _validate_response_prediction(body)
            if server_ms is not None:
                server_total_ms += server_ms
            if valid:
                success_count += 1
            else:
                error_count += 1
                response_error_count += 1
                errors.append(error or "invalid_response")
        except (requests.RequestException, ValueError) as exc:
            error_count += 1
            request_error_count += 1
            errors.append(f"{type(exc).__name__}: {str(exc)[:250]}")
    total_ms = (time.perf_counter() - started) * 1000
    return _raw_record(
        mode="individual", batch_size=batch_size, repetition=repetition,
        total_ms=total_ms, server_total_ms=server_total_ms,
        success_count=success_count, error_count=error_count,
        request_error_count=request_error_count, response_error_count=response_error_count,
        http_status=max(http_statuses) if http_statuses else None,
        errors=errors, cases=cases, environment_json=environment_json,
    )


def _batch_run(
    session: requests.Session,
    api_url: str,
    cases: pd.DataFrame,
    *,
    batch_size: int,
    repetition: int,
    timeout: float,
    environment_json: str,
) -> dict[str, Any]:
    csv_bytes = cases.loc[:, ACADEMIC_FEATURES].to_csv(index=False).encode("utf-8")
    started = time.perf_counter()
    server_total_ms = 0.0
    success_count = 0
    error_count = 0
    request_error_count = 0
    response_error_count = 0
    errors: list[str] = []
    http_status: int | None = None
    try:
        response = session.post(
            f"{api_url.rstrip('/')}/api/predict-csv",
            files={"file": ("operational-cases.csv", csv_bytes, "text/csv")},
            timeout=timeout,
        )
        http_status = response.status_code
        if response.status_code != 200:
            error_count = batch_size
            response_error_count = batch_size
            errors.append(f"HTTP {response.status_code}: {response.text[:300]}")
        else:
            body = response.json()
            returned_rows = body.get("rows", [])
            if body.get("count") != batch_size or len(returned_rows) != batch_size:
                errors.append(f"row_count_mismatch:{body.get('count')}:{len(returned_rows)}")
                response_error_count += abs(batch_size - len(returned_rows)) or 1
            for result_row in returned_rows:
                if result_row.get("error") or not isinstance(result_row.get("prediction"), dict):
                    error_count += 1
                    response_error_count += 1
                    errors.append(str(result_row.get("error") or "missing_prediction")[:300])
                    continue
                valid, error, server_ms = _validate_response_prediction(result_row["prediction"])
                if server_ms is not None:
                    server_total_ms += server_ms
                if valid:
                    success_count += 1
                else:
                    error_count += 1
                    response_error_count += 1
                    errors.append(error or "invalid_response")
            if len(returned_rows) < batch_size:
                error_count += batch_size - len(returned_rows)
    except (requests.RequestException, ValueError) as exc:
        error_count = batch_size
        request_error_count = batch_size
        errors.append(f"{type(exc).__name__}: {str(exc)[:250]}")
    total_ms = (time.perf_counter() - started) * 1000
    return _raw_record(
        mode="batch", batch_size=batch_size, repetition=repetition,
        total_ms=total_ms, server_total_ms=server_total_ms,
        success_count=success_count, error_count=error_count,
        request_error_count=request_error_count, response_error_count=response_error_count,
        http_status=http_status, errors=errors, cases=cases,
        environment_json=environment_json,
    )


def _raw_record(
    *, mode: str, batch_size: int, repetition: int, total_ms: float,
    server_total_ms: float | None, success_count: int, error_count: int,
    request_error_count: int, response_error_count: int,
    http_status: int | None, errors: list[str], cases: pd.DataFrame,
    environment_json: str,
) -> dict[str, Any]:
    throughput = batch_size / (total_ms / 1000) if total_ms > 0 else None
    return {
        "mode": mode,
        "batch_size": batch_size,
        "repetition": repetition,
        "total_ms": round(total_ms, 3),
        "server_total_ms": round(server_total_ms, 3) if server_total_ms is not None else None,
        "client_overhead_ms": round(max(0.0, total_ms - server_total_ms), 3) if server_total_ms is not None else None,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": success_count / batch_size,
        "projects_per_second": throughput,
        "ms_per_project": total_ms / batch_size,
        "timestamp": utc_now(),
        "environment": environment_json,
        "case_ids_sha256": project_case_hash(cases["project_id"].tolist()),
        "task": "ml_and_drivers_without_recommendations",
        "http_status": http_status,
        "request_error_count": request_error_count,
        "response_error_count": response_error_count,
        "http_failure_count": sum(error.startswith("HTTP ") for error in errors),
        "timeout_count": sum("timeout" in error.lower() for error in errors),
        "coverage_block_count": sum("cobertura insuficiente" in error.lower() for error in errors),
        "errors": json.dumps(errors[:20], ensure_ascii=False),
    }


def run_warmup(session: requests.Session, api_url: str, case: pd.Series, timeout: float, count: int = 3) -> list[dict[str, Any]]:
    warmups = []
    payload = {feature: case[feature] for feature in ACADEMIC_FEATURES}
    for index in range(count):
        response = session.post(
            f"{api_url.rstrip('/')}/api/predict?include_recommendations=false",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        valid, error, server_ms = _validate_response_prediction(body)
        if not valid:
            raise RuntimeError(f"Warm-up {index + 1} was invalid: {error}")
        warmups.append({"warmup": index + 1, "server_total_ms": server_ms})
    return warmups


def run_robustness_checks(session: requests.Session, api_url: str, valid_case: dict[str, Any], timeout: float) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check_api(name: str, payload: dict[str, Any], expected_status: int, expected_fragment: str | None = None):
        try:
            response = session.post(
                f"{api_url.rstrip('/')}/api/predict?include_recommendations=false",
                json=payload,
                timeout=timeout,
            )
            try:
                body = response.json()
            except ValueError:
                body = {}
            text = json.dumps(body, ensure_ascii=False)
            passed = response.status_code == expected_status and (expected_fragment is None or expected_fragment.lower() in text.lower())
            checks.append({"case": name, "transport": "POST /api/predict", "expected_status": expected_status, "observed_status": response.status_code, "passed": passed, "detail": body.get("detail")})
        except requests.RequestException as exc:
            checks.append({"case": name, "transport": "POST /api/predict", "expected_status": expected_status, "observed_status": None, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})

    incomplete = dict(valid_case)
    incomplete.pop("methodology", None)
    try:
        response = session.post(
            f"{api_url.rstrip('/')}/api/predict?include_recommendations=false",
            json=incomplete,
            timeout=timeout,
        )
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        quality = body.get("prediction", {}).get("input_quality", {})
        passed = response.status_code == 200 and quality.get("missing_count") == 1 and "methodology" in quality.get("missing_trained_features", [])
        checks.append({"case": "one_missing_feature_imputed_by_training_policy", "transport": "POST /api/predict", "expected_status": 200, "observed_status": response.status_code, "passed": passed, "detail": quality})
    except (requests.RequestException, ValueError) as exc:
        checks.append({"case": "one_missing_feature_imputed_by_training_policy", "transport": "POST /api/predict", "expected_status": 200, "observed_status": None, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})

    below_coverage = {"planned_duration_weeks": valid_case["planned_duration_weeks"]}
    check_api("coverage_below_minimum", below_coverage, 422, "cobertura insuficiente")
    invalid_category = {**valid_case, "project_type": "invalid_project_type"}
    check_api("invalid_category", invalid_category, 422, "project_type")
    invalid_progress = {**valid_case, "true_progress": 1.2}
    check_api("true_progress_out_of_range", invalid_progress, 422, "true_progress")

    invalid_csv_row = {**valid_case, "project_type": "invalid_project_type"}
    csv_payload = pd.DataFrame([invalid_csv_row], columns=ACADEMIC_FEATURES).to_csv(index=False).encode("utf-8")
    try:
        response = session.post(
            f"{api_url.rstrip('/')}/api/predict-csv",
            files={"file": ("invalid-category.csv", csv_payload, "text/csv")},
            timeout=timeout,
        )
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        row_error = body.get("rows", [{}])[0].get("error") if body.get("rows") else None
        checks.append({"case": "csv_invalid_category_controlled_row_error", "transport": "POST /api/predict-csv", "expected_status": 200, "observed_status": response.status_code, "passed": response.status_code == 200 and bool(row_error), "detail": row_error})
    except requests.RequestException as exc:
        checks.append({"case": "csv_invalid_category_controlled_row_error", "transport": "POST /api/predict-csv", "expected_status": 200, "observed_status": None, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})

    return {
        "status": "complete" if all(check["passed"] for check in checks) else "completed_with_failures",
        "checks": checks,
        "successful_checks": sum(check["passed"] for check in checks),
        "failed_checks": sum(not check["passed"] for check in checks),
        "timeout_failures_observed": sum("timeout" in str(check.get("detail", "")).lower() for check in checks),
        "http_failures_observed": sum(check.get("observed_status") not in (200, 422, None) for check in checks),
        "coverage_blocks_observed": sum(check["case"] == "coverage_below_minimum" and check.get("observed_status") == 422 for check in checks),
        "normal_throughput_cases_included": False,
    }


def run_optional_genai_sample(
    session: requests.Session,
    api_url: str | None,
    cases: pd.DataFrame,
    official_report_path: Path,
    output_path: Path,
    timeout: float,
) -> dict[str, Any]:
    official: dict[str, Any] = {}
    if official_report_path.exists():
        try:
            official = json.loads(official_report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            official = {}
    if not api_url:
        result = {
            "status": "official_report_only" if official.get("status") == "complete" else "unavailable",
            "source_report": str(official_report_path.relative_to(ROOT)) if official_report_path.is_relative_to(ROOT) else str(official_report_path),
            "official_metrics": official.get("metrics"),
            "additional_sample_executed": False,
            "note": "El benchmark operacional principal se ejecuta con GenAI deshabilitada; esta sección no forma parte de throughput ML/batch.",
        }
    else:
        result = _run_genai_sample(session, api_url, cases.head(min(5, len(cases))), official, timeout)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def _run_genai_sample(session: requests.Session, api_url: str, cases: pd.DataFrame, official: dict[str, Any], timeout: float) -> dict[str, Any]:
    try:
        status = session.get(f"{api_url.rstrip('/')}/api/genai-status", timeout=5).json()
        health = session.get(f"{api_url.rstrip('/')}/api/health", timeout=5).json()
    except (requests.RequestException, ValueError) as exc:
        return {"status": "official_report_only", "source_report": "reports/genai/qwen3-8b-evaluation.json", "official_metrics": official.get("metrics"), "additional_sample_executed": False, "note": f"No se pudo consultar API GenAI separada: {type(exc).__name__}: {exc}"}
    if not status.get("enabled") or not status.get("available") or health.get("version") != "0.9.0-academic":
        return {"status": "official_report_only", "source_report": "reports/genai/qwen3-8b-evaluation.json", "official_metrics": official.get("metrics"), "additional_sample_executed": False, "note": "El endpoint complementario no confirma Ollama/modelo académico disponibles."}

    samples = []
    for row in cases.to_dict("records"):
        payload = {feature: row[feature] for feature in ACADEMIC_FEATURES}
        started = time.perf_counter()
        try:
            response = session.post(f"{api_url.rstrip('/')}/api/predict", json=payload, timeout=timeout)
            elapsed_ms = (time.perf_counter() - started) * 1000
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            rec = body.get("recommendations") or {}
            samples.append({
                "project_id": row["project_id"],
                "http_status": response.status_code,
                "total_ms": round(elapsed_ms, 2),
                "genai_ms": rec.get("genai_latency_ms"),
                "genai_attempted": rec.get("genai_attempted"),
                "genai_used": rec.get("genai_used"),
                "engine": rec.get("engine"),
                "failure_code": rec.get("failure_code"),
            })
        except (requests.RequestException, ValueError) as exc:
            samples.append({"project_id": row["project_id"], "http_status": None, "total_ms": round((time.perf_counter() - started) * 1000, 2), "error": f"{type(exc).__name__}: {exc}"})
    genai_latencies = [float(item["genai_ms"]) for item in samples if isinstance(item.get("genai_ms"), (int, float))]
    successes = sum(item.get("genai_used") is True for item in samples)
    return {
        "status": "complete",
        "source": "additional local API sample; separate from primary operational benchmark",
        "model": status.get("model"),
        "artifact_version": health.get("version"),
        "cases_requested": len(cases),
        "cases_completed": len(samples),
        "genai_successes": successes,
        "genai_fallbacks": sum(item.get("genai_attempted") is True and item.get("genai_used") is False for item in samples),
        "genai_success_rate": successes / len(samples) if samples else None,
        "genai_latency_ms_median": float(pd.Series(genai_latencies).median()) if genai_latencies else None,
        "genai_latency_ms_p95": float(pd.Series(genai_latencies).quantile(0.95)) if genai_latencies else None,
        "official_benchmark_reference": official.get("metrics"),
        "cases": samples,
        "note": "Muestra complementaria de cinco casos; no sobrescribe el benchmark GenAI oficial ni participa en las métricas de throughput ML/batch.",
    }


def render_figures(summary: dict[str, Any], output_dir: Path) -> list[str]:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    sizes = summary["batch_sizes"]
    if not sizes or summary.get("status") != "complete":
        return []
    individual = summary["individual"]
    batch = summary["batch"]
    generated: list[str] = []

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(sizes, [individual[str(size)]["median_ms"] for size in sizes], marker="o", label="Individual secuencial")
    ax.plot(sizes, [batch[str(size)]["median_ms"] for size in sizes], marker="o", label="Batch CSV")
    ax.set(title="Latencia total observada por tamaño", xlabel="Proyectos por ejecución", ylabel="Mediana de latencia (ms)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = figure_dir / "latency_vs_batch_size.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(sizes, [individual[str(size)]["throughput_projects_per_second"] for size in sizes], marker="o", label="Individual secuencial")
    ax.plot(sizes, [batch[str(size)]["throughput_projects_per_second"] for size in sizes], marker="o", label="Batch CSV")
    ax.set(title="Throughput observado por tamaño", xlabel="Proyectos por ejecución", ylabel="Proyectos por segundo")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = figure_dir / "throughput_vs_batch_size.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(sizes, [individual[str(size)]["ms_per_project"] for size in sizes], marker="o", label="Individual secuencial")
    ax.plot(sizes, [batch[str(size)]["ms_per_project"] for size in sizes], marker="o", label="Batch CSV")
    ax.set(title="Costo temporal mediano por proyecto", xlabel="Proyectos por ejecución", ylabel="Milisegundos por proyecto")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = figure_dir / "ms_per_project_vs_batch_size.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(str(path.relative_to(ROOT)))

    x = list(range(len(sizes)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar([value - width / 2 for value in x], [individual[str(size)]["median_ms"] for size in sizes], width, label="Individual secuencial")
    ax.bar([value + width / 2 for value in x], [batch[str(size)]["median_ms"] for size in sizes], width, label="Batch CSV")
    ax.set(title="Mediana individual frente a batch", xlabel="Tamaño N", ylabel="Latencia (ms)", xticks=x, xticklabels=[str(size) for size in sizes])
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = figure_dir / "sequential_vs_batch.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(str(path.relative_to(ROOT)))
    return generated


def render_markdown(summary: dict[str, Any], robustness: dict[str, Any], genai_sample: dict[str, Any], figures: list[str]) -> str:
    if summary.get("status") != "complete":
        return f"# Benchmark operacional\n\nEstado: `{summary.get('status')}`.\n\n{summary.get('detail', 'No se ejecutó una comparación completa.')}\n"
    genai_rate = genai_sample.get("genai_success_rate")
    if genai_rate is None:
        genai_rate = (genai_sample.get("official_metrics") or {}).get("generation_success_rate")
    genai_rate_text = f"{float(genai_rate):.1%}" if isinstance(genai_rate, (int, float)) and math.isfinite(float(genai_rate)) else "N/D"
    genai_median = genai_sample.get("genai_latency_ms_median")
    genai_p95 = genai_sample.get("genai_latency_ms_p95")
    if genai_median is None:
        official_metrics = genai_sample.get("official_metrics") or {}
        genai_median = official_metrics.get("latency_ms_median")
        genai_p95 = official_metrics.get("latency_ms_p95")
    genai_latency_text = f"mediana {float(genai_median):.2f} ms, p95 {float(genai_p95):.2f} ms" if isinstance(genai_median, (int, float)) and isinstance(genai_p95, (int, float)) else "latencia N/D"
    lines = [
        "# Benchmark de eficiencia operacional",
        "",
        f"Estado: **{summary['status']}**. Artifact: `{summary['environment']['artifact_version']}`. Dataset: {summary['environment']['dataset_source']}.",
        f"HEAD medido: `{summary['environment']['git_sha']}`. Fecha UTC: {summary['environment']['date_utc']}.",
        f"Entorno observado: {summary['environment']['os']}, Python {summary['environment']['python_version']}, arquitectura {summary['environment']['cpu_architecture']}; API mode `{summary['environment']['api_mode']}`, workers {summary['environment']['workers'] or 'no determinados por API'}.",
        "",
        "Medición local end-to-end sobre TEST académico. `individual` son llamadas secuenciales sin recomendaciones; `batch` es una llamada CSV secuencial. No es prueba productiva ni productividad humana.",
        "",
        "## Resultados",
        "",
        "| N | Rep. | Individual mediana (ms) | Batch mediana (ms) | Speedup | Reducción | Throughput batch (proy/s; proy/min) | Batch ms/proyecto | Éxito individual/batch |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for size in summary["batch_sizes"]:
        n = str(size)
        ind, bat, comp = summary["individual"][n], summary["batch"][n], summary["comparison"][n]
        speed = f"{comp['speedup_batch_vs_sequential']:.3f}×" if comp["speedup_batch_vs_sequential"] is not None else "N/D"
        reduction = f"{comp['time_reduction_percent']:.1f}%" if comp["time_reduction_percent"] is not None else "N/D"
        throughput = bat["throughput_projects_per_second"]
        throughput_text = f"{throughput:.3f}; {bat['throughput_projects_per_minute']:.1f}" if throughput is not None else "N/D"
        lines.append(f"| {size} | {bat['repetitions']} | {ind['median_ms']:.2f} | {bat['median_ms']:.2f} | {speed} | {reduction} | {throughput_text} | {bat['ms_per_project']:.2f} | {ind['success_rate']:.1%} / {bat['success_rate']:.1%} |")
    lines.extend([
        "",
        "## Interpretación",
        "",
        f"- El batch alcanzó su mayor throughput medido en N={max(summary['batch_sizes'], key=lambda size: summary['batch'][str(size)]['throughput_projects_per_second'] or 0)} dentro de los tamaños probados; no se extrapola más allá de 100.",
        f"- Patrón de escalamiento local relativo a la referencia batch N=1: " + "; ".join(f"N={item['batch_size']}: {item['observed_pattern']}" for item in summary["scaling"]) + ".",
        "- Si el speedup es >1, se interpreta como menor overhead por agrupar proyectos en un endpoint secuencial, no como paralelización.",
        "- GenAI estuvo apagada durante ambos modos. La latencia de ML+drivers en respuestas API se conserva separada del total; no se atribuye a Qwen.",
        f"- Chequeos de robustez: {robustness['successful_checks']}/{len(robustness['checks'])} pasan; se excluyeron del throughput normal.",
        f"- Muestra GenAI separada: estado `{genai_sample.get('status')}`, éxito {genai_rate_text}, {genai_latency_text}; no se mezcla con latencia batch.",
        "- Esto mide eficiencia operacional del sistema en una laptop/API local. No demuestra productividad humana, ahorro laboral, escalabilidad productiva ni comportamiento bajo concurrencia.",
        "",
        "## Variabilidad y percentiles",
        "",
        "El JSON contiene media, mediana, p50, p90, p95, mínimo, máximo, desviación estándar, tasa de éxito/error, throughput y overhead cliente-servidor por modo y N.",
        "",
        "## Gráficos",
        "",
    ])
    lines.extend(f"- `{path}`" for path in figures)
    lines.extend(["", "## Robustez", "", "`reports/efficiency/robustness_checks.json` documenta input incompleto, cobertura bloqueada, categoría inválida, true_progress fuera de rango, error controlado por fila CSV y timeouts observados. Estos casos no forman parte de las repeticiones de throughput.", ""])
    return "\n".join(lines)


def write_outputs(output_dir: Path, cases: pd.DataFrame, raw_records: list[dict[str, Any]], summary: dict[str, Any], robustness: dict[str, Any], genai_sample: dict[str, Any]) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases.to_csv(output_dir / "benchmark_cases.csv", index=False)
    pd.DataFrame(raw_records).reindex(columns=RAW_FIELDS).to_csv(output_dir / "operational_benchmark_raw.csv", index=False)
    (output_dir / "operational_benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "robustness_checks.json").write_text(json.dumps(robustness, indent=2, ensure_ascii=False), encoding="utf-8")
    figures = render_figures(summary, output_dir)
    (output_dir / "operational_benchmark.md").write_text(render_markdown(summary, robustness, genai_sample, figures), encoding="utf-8")
    return figures


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = (ROOT / args.output_dir).resolve()
    artifact_dir = (ROOT / args.artifact).resolve()
    input_path = (ROOT / args.input).resolve()
    manifest_path = artifact_dir / "feature_manifest.json"
    split_path = artifact_dir / "split_manifest.json"
    if not (artifact_dir / "health.joblib").exists() or not manifest_path.exists() or not split_path.exists():
        return write_unavailable(output_dir, "unavailable_academic_artifact", f"Falta health.joblib, feature_manifest.json o split_manifest.json en {artifact_dir}.")
    if not input_path.exists():
        return write_unavailable(output_dir, "unavailable_academic_artifact", f"Falta el dataset preparado {input_path}.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_source") != "Mendeley Data 2p5sz57wh2 version 2" or set(manifest.get("numeric_features", [])) | set(manifest.get("categorical_features", [])) != set(ACADEMIC_FEATURES):
        return write_unavailable(output_dir, "unavailable_academic_artifact", "El manifest no corresponde al artifact académico Mendeley v2 de siete features.")

    session = requests.Session()
    api_url = args.api_url.rstrip("/")
    api_health, api_metadata, preflight_error = api_preflight(
        session, api_url, "0.9.0-academic", args.connect_timeout
    )
    if preflight_error:
        if api_metadata is None:
            return write_unavailable(output_dir, "unavailable_api", preflight_error)
        if api_metadata.get("artifact_version") != "0.9.0-academic" or api_metadata.get("dataset_source") != manifest.get("dataset_source"):
            status = "unavailable_academic_artifact"
        elif api_metadata.get("genai_enabled") is not False:
            status = "unavailable_genai_enabled"
        else:
            status = "unavailable_api_contract"
        return write_unavailable(output_dir, status, preflight_error, {"api": api_metadata})

    split = json.loads(split_path.read_text(encoding="utf-8"))
    source = pd.read_csv(input_path, low_memory=False)
    try:
        cases = sample_test_cases(source, set(map(str, split["test"])), limit=max(BATCH_SIZES), seed=args.seed)
    except ValueError as exc:
        return write_unavailable(output_dir, "unavailable_test_cases", str(exc), {"api": api_metadata})

    cases_by_size = {size: cases.head(size).copy() for size in BATCH_SIZES}
    case_ids_by_size = {size: frame["project_id"].tolist() for size, frame in cases_by_size.items()}
    env = environment_metadata(api_metadata, "0.9.0-academic")
    environment_json = json.dumps(env, ensure_ascii=False, sort_keys=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases.to_csv(output_dir / "benchmark_cases.csv", index=False)

    try:
        warmups = run_warmup(session, api_url, cases.iloc[0], args.request_timeout, count=3)
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        return write_unavailable(output_dir, "warmup_failed", f"El API no superó tres inferencias warm-up: {type(exc).__name__}: {exc}", {"api": api_metadata, **env})
    raw_records: list[dict[str, Any]] = []
    for size in BATCH_SIZES:
        frame = cases_by_size[size]
        for repetition in range(1, REPETITIONS_BY_SIZE[size] + 1):
            raw_records.append(_individual_run(session, api_url, frame, batch_size=size, repetition=repetition, timeout=args.request_timeout, environment_json=environment_json))
            raw_records.append(_batch_run(session, api_url, frame, batch_size=size, repetition=repetition, timeout=args.request_timeout, environment_json=environment_json))
    summary = build_summary(raw_records, case_ids_by_size=case_ids_by_size, environment=env)
    summary["warmup_runs"] = len(warmups)
    summary["warmup_observations"] = warmups
    summary["sampling"] = {
        "seed": args.seed,
        "source": str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path),
        "split": str(split_path.relative_to(ROOT)) if split_path.is_relative_to(ROOT) else str(split_path),
        "split_name": "test",
        "selection": "most recent snapshot_index per TEST project, sorted project_id then sampled once with fixed seed; each smaller N is a prefix of the same 100-project draw",
        "features_only": ACADEMIC_FEATURES,
        "targets_included": False,
        "unique_test_projects": cases.project_id.nunique(),
    }
    summary["measurement"] = {
        "individual_endpoint": "POST /api/predict?include_recommendations=false",
        "batch_endpoint": "POST /api/predict-csv",
        "individual_requests_sequential": True,
        "batch_rows_processed_sequentially_by_current_api": True,
        "primary_task": "same seven-feature ML plus local drivers, without recommendation/GenAI",
        "client_total_ms_includes_http_upload_download_and_serialization": True,
        "server_total_ms_is_sum_of_per-inference timing.total_ms": True,
    }
    robustness = run_robustness_checks(session, api_url, cases.iloc[0].to_dict(), args.request_timeout)
    if robustness["failed_checks"]:
        summary["limitations"].append("One or more controlled robustness checks did not match the expected error contract; see robustness_checks.json.")

    genai_output = output_dir / "genai_operational_sample.json"
    if args.genai_api_url:
        genai_sample = run_optional_genai_sample(session, args.genai_api_url, cases, ROOT / args.genai_report, genai_output, args.request_timeout)
    else:
        genai_sample = run_optional_genai_sample(session, None, cases, ROOT / args.genai_report, genai_output, args.request_timeout)
    figures = write_outputs(output_dir, cases, raw_records, summary, robustness, genai_sample)
    summary["figures"] = figures
    (output_dir / "operational_benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "operational_benchmark.md").write_text(render_markdown(summary, robustness, genai_sample, figures), encoding="utf-8")
    return summary


def write_unavailable(output_dir: Path, status: str, detail: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"status": status, "detail": detail, "environment": extra or {}, "batch_sizes": BATCH_SIZES, "warmup_runs": 0, "individual": {}, "batch": {}, "comparison": {}, "scaling": [], "limitations": ["No latencies or throughput were generated because academic/API preconditions were not met."]}
    (output_dir / "operational_benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "operational_benchmark.md").write_text(f"# Benchmark operacional\n\nEstado: `{status}`.\n\n{detail}\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local, reproducible de eficiencia operacional API individual vs batch.")
    parser.add_argument("--api-url", default=os.getenv("PRUNIN_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--artifact", default="artifacts/0.9.0-academic")
    parser.add_argument("--input", default="data/processed/mendeley_core.csv")
    parser.add_argument("--output-dir", default="reports/efficiency")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--connect-timeout", type=float, default=5)
    parser.add_argument("--request-timeout", type=float, default=120)
    parser.add_argument("--genai-api-url", default=None, help="Optional separate API with GenAI enabled for a five-case sample")
    parser.add_argument("--genai-report", default="reports/genai/qwen3-8b-evaluation.json")
    args = parser.parse_args()
    summary = run_benchmark(args)
    print(json.dumps({key: summary.get(key) for key in ("status", "environment", "batch_sizes", "repetitions", "comparison", "limitations")}, indent=2, ensure_ascii=False))
    return 0 if summary.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())