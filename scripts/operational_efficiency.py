from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from typing import Any

import pandas as pd
from prunin_ai.api.schema import ProjectInput


ACADEMIC_FEATURES = [
    "planned_duration_weeks",
    "planned_budget",
    "true_progress",
    "spi",
    "cpi",
    "project_type",
    "methodology",
]
PROJECT_TYPES = {"construction", "healthcare", "it", "manufacturing", "marketing", "r&d"}
METHODOLOGIES = {"agile", "hybrid", "kanban", "scrum", "waterfall"}
BATCH_SIZES = [1, 10, 25, 50, 100]
REPETITIONS_BY_SIZE = {1: 10, 10: 10, 25: 10, 50: 5, 100: 5}


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def sample_test_cases(
    frame: pd.DataFrame,
    test_project_ids: set[str],
    *,
    limit: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    required = {"project_id", *ACADEMIC_FEATURES}
    missing_columns = required - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")
    if limit <= 0:
        raise ValueError("limit must be positive")

    test = frame[frame["project_id"].astype(str).isin(test_project_ids)].copy()
    if test.empty:
        raise ValueError("No rows belong to the academic TEST split")
    order_column = "snapshot_index" if "snapshot_index" in test.columns else "true_progress"
    latest = (
        test.sort_values(["project_id", order_column], kind="stable")
        .groupby("project_id", as_index=False, sort=False)
        .tail(1)
        .sort_values("project_id", kind="stable")
    )
    latest = latest.dropna(subset=ACADEMIC_FEATURES)
    latest = latest[latest["project_type"].astype(str).isin(PROJECT_TYPES)]
    latest = latest[latest["methodology"].astype(str).isin(METHODOLOGIES)]
    numeric_features = ACADEMIC_FEATURES[:5]
    for feature in numeric_features:
        latest = latest[pd.to_numeric(latest[feature], errors="coerce").map(math.isfinite)]
    valid_indexes = []
    for index, row in latest.iterrows():
        payload = {feature: row[feature] for feature in ACADEMIC_FEATURES}
        try:
            ProjectInput.model_validate(payload)
        except Exception:
            continue
        valid_indexes.append(index)
    latest = latest.loc[valid_indexes]
    if len(latest) < limit:
        raise ValueError(f"Only {len(latest)} valid latest TEST projects; {limit} required")

    sampled = latest.sample(n=limit, random_state=seed).reset_index(drop=True)
    cases = sampled.loc[:, ["project_id", *ACADEMIC_FEATURES]].copy()
    for feature in numeric_features:
        cases[feature] = pd.to_numeric(cases[feature], errors="raise").astype(float)
    cases["project_id"] = cases["project_id"].astype(str)
    cases.insert(0, "case_order", range(1, len(cases) + 1))
    return cases


def project_case_hash(project_ids: list[str]) -> str:
    payload = json.dumps(project_ids, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def summarize_mode(records: list[dict[str, Any]], *, mode: str, batch_size: int) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    selected = [record for record in records if record.get("mode") == mode and record.get("batch_size") == batch_size]
    if not selected:
        raise ValueError(f"No runs recorded for mode={mode}, batch_size={batch_size}")
    durations = [float(record["total_ms"]) for record in selected]
    if any(not math.isfinite(value) or value < 0 for value in durations):
        raise ValueError("total_ms values must be finite and non-negative")
    total_projects = batch_size * len(selected)
    successful = sum(int(record.get("success_count", 0)) for record in selected)
    failed = sum(int(record.get("error_count", 0)) for record in selected)
    median_ms = statistics.median(durations)
    throughput = batch_size / (median_ms / 1000.0) if median_ms > 0 else None
    return {
        "mode": mode,
        "batch_size": batch_size,
        "repetitions": len(selected),
        "mean_ms": statistics.fmean(durations),
        "median_ms": median_ms,
        "p50_ms": percentile(durations, 0.50),
        "p90_ms": percentile(durations, 0.90),
        "p95_ms": percentile(durations, 0.95),
        "min_ms": min(durations),
        "max_ms": max(durations),
        "std_ms": statistics.stdev(durations) if len(durations) > 1 else 0.0,
        "successful_rows": successful,
        "failed_rows": failed,
        "success_rate": successful / total_projects,
        "error_rate": failed / total_projects,
        "throughput_projects_per_second": throughput,
        "throughput_projects_per_minute": throughput * 60 if throughput is not None else None,
        "ms_per_project": median_ms / batch_size,
        "server_total_ms_median": statistics.median(
            float(record["server_total_ms"]) for record in selected if record.get("server_total_ms") is not None
        ) if any(record.get("server_total_ms") is not None for record in selected) else None,
        "client_overhead_ms_median": statistics.median(
            float(record["client_overhead_ms"]) for record in selected if record.get("client_overhead_ms") is not None
        ) if any(record.get("client_overhead_ms") is not None for record in selected) else None,
    }


def build_summary(
    records: list[dict[str, Any]],
    *,
    case_ids_by_size: dict[int, list[str]],
    repetitions_by_size: dict[int, int] | None = None,
    environment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repetitions = repetitions_by_size or REPETITIONS_BY_SIZE
    sizes = list(repetitions)
    counts: dict[tuple[str, int], int] = defaultdict(int)
    for record in records:
        counts[(str(record.get("mode")), int(record.get("batch_size", 0)))] += 1
    missing_runs = [
        {"mode": mode, "batch_size": size, "expected": repetitions[size], "actual": counts[(mode, size)]}
        for size in sizes
        for mode in ("individual", "batch")
        if counts[(mode, size)] != repetitions[size]
    ]
    result: dict[str, Any] = {
        "status": "incomplete" if missing_runs else "complete",
        "environment": environment or {},
        "warmup_runs": 3,
        "repetitions": {str(size): repetitions[size] for size in sizes},
        "batch_sizes": sizes,
        "case_count": len(case_ids_by_size.get(max(sizes, default=0), [])),
        "case_ids_by_size": {str(size): case_ids_by_size.get(size, []) for size in sizes},
        "missing_runs": missing_runs,
        "individual": {},
        "batch": {},
        "comparison": {},
        "scaling": [],
        "limitations": [
            "Mediciones de un equipo local y una API local; no representan rendimiento productivo ni hardware universal.",
            "El modo individual es secuencial y el batch procesa filas secuencialmente; no se afirma paralelización.",
            "La reducción batch refleja overhead observado de petición/serialización junto con el endpoint; no productividad humana.",
            "El benchmark principal desactiva GenAI; la latencia Qwen se informa por separado.",
            "Los casos son snapshots TEST más recientes; no se usan labels/targets como inputs.",
        ],
    }
    if missing_runs:
        return result

    for size in sizes:
        result["individual"][str(size)] = summarize_mode(records, mode="individual", batch_size=size)
        result["batch"][str(size)] = summarize_mode(records, mode="batch", batch_size=size)
        individual = result["individual"][str(size)]
        batch = result["batch"][str(size)]
        hashes = {
            record.get("case_ids_sha256")
            for record in records
            if record.get("batch_size") == size and record.get("mode") in {"individual", "batch"}
        }
        same_task = all(record.get("task") == "ml_and_drivers_without_recommendations" for record in records if record.get("batch_size") == size)
        genai_disabled = (environment or {}).get("genai_enabled") is False
        all_successful = individual["success_rate"] == 1.0 and batch["success_rate"] == 1.0
        comparable = len(hashes) == 1 and same_task and genai_disabled and all_successful
        speedup = individual["median_ms"] / batch["median_ms"] if comparable and batch["median_ms"] > 0 else None
        reduction = (1.0 - batch["median_ms"] / individual["median_ms"]) * 100.0 if comparable and individual["median_ms"] > 0 else None
        result["comparison"][str(size)] = {
            "same_case_set": len(hashes) == 1,
            "same_task": same_task,
            "genai_disabled": genai_disabled,
            "both_modes_successful": all_successful,
            "speedup_batch_vs_sequential": speedup,
            "time_reduction_percent": reduction,
            "interpretation": "Reducción de overhead mediante el endpoint batch; no es paralelización." if comparable else "No comparable: revise mismo caso/tarea, GenAI apagado y éxito total.",
        }
        expected_linear_ms = result["batch"]["1"]["median_ms"] * size if "1" in result["batch"] else None
        measured_ratio = batch["median_ms"] / expected_linear_ms if expected_linear_ms and expected_linear_ms > 0 else None
        if measured_ratio is None:
            trend = "no disponible"
        elif measured_ratio < 0.9:
            trend = "sublineal respecto a la referencia local N=1"
        elif measured_ratio > 1.1:
            trend = "supralineal respecto a la referencia local N=1"
        else:
            trend = "aproximadamente lineal respecto a la referencia local N=1"
        result["scaling"].append({
            "batch_size": size,
            "measured_total_ms": batch["median_ms"],
            "ms_per_project": batch["ms_per_project"],
            "throughput_projects_per_second": batch["throughput_projects_per_second"],
            "success_rate": batch["success_rate"],
            "relative_to_local_n1_linear_reference": measured_ratio,
            "observed_pattern": trend,
        })
    return result