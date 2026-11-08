from __future__ import annotations

import json
import os
import platform
import statistics
from pathlib import Path
from typing import Any

import pandas as pd
import requests


TEMPERATURE = 0.1


def require_new_outputs(directory: Path, names: list[str]) -> None:
    if any((directory / name).exists() for name in names):
        raise FileExistsError("Evaluation outputs already exist; select a new versioned directory.")


def ollama_models(url: str, *, timeout: float = 3.0) -> tuple[set[str] | None, str | None]:
    tags_url = url.rsplit("/api/", 1)[0] + "/api/tags" if "/api/" in url else url.rstrip("/") + "/api/tags"
    try:
        response = requests.get(tags_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return {
            str(item.get("name", ""))
            for item in payload.get("models", [])
            if isinstance(item, dict) and item.get("name")
        }, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def model_is_installed(model: str, installed: set[str]) -> bool:
    return model in installed or f"{model}:latest" in installed


def prepare_cases(artifact: Path, input_path: Path, cases: int) -> tuple[Any, list[dict[str, Any]]]:
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from prunin_ai.api.catalog import FIELD_MAP
    from prunin_ai.api.model_runtime import ModelRuntime

    os.environ["PRUNIN_ARTIFACT_DIR"] = str(artifact.resolve())
    runtime = ModelRuntime()
    split = json.loads((artifact / "split_manifest.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(input_path, low_memory=False)
    frame["project_id"] = frame["project_id"].astype(str)
    test = frame[frame["project_id"].isin(set(map(str, split["test"])))].copy()
    order = ["project_id"]
    if "snapshot_index" in test.columns:
        order.append("snapshot_index")
    elif "true_progress" in test.columns:
        order.append("true_progress")
    latest = test.sort_values(order).groupby("project_id", as_index=False).tail(1)
    latest = latest.sample(frac=1.0, random_state=42)
    prepared = []
    for _, source in latest.iterrows():
        row = {
            name: (None if pd.isna(source.get(name)) else source.get(name))
            for name in FIELD_MAP
            if name in source.index
        }
        try:
            prediction = runtime.predict(row)
            drivers = runtime.local_drivers(row, prediction)
        except Exception:
            continue
        risk_drivers = [item for item in drivers if item.get("direction") == "increases_risk"]
        if not risk_drivers:
            continue
        prepared.append({
            "case_id": str(source["project_id"]),
            "input": row,
            "drivers": drivers,
            "prediction": prediction,
            "risk_drivers": risk_drivers,
            "health": prediction.get("health"),
        })
        if len(prepared) == cases:
            break
    if len(prepared) != cases:
        raise RuntimeError(f"Se solicitaron {cases} casos y solo se pudieron preparar {len(prepared)}.")
    return runtime, prepared


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    if not rows:
        return {
            "requests_total": 0,
            "generation_success_rate": None,
            "schema_valid_rate": None,
            "grounded_rate": None,
            "unsupported_numeric_claim_rate": None,
            "actionability_rate": None,
            "timeout_rate": None,
            "invalid_json_rate": None,
            "latency_ms_median": None,
            "latency_ms_p95": None,
        }
    count = len(rows)
    rate = lambda key: sum(bool(row[key]) for row in rows) / count
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "requests_total": count,
        "generation_success_rate": rate("generation_success"),
        "schema_valid_rate": rate("schema_valid"),
        "grounded_rate": rate("grounded"),
        "unsupported_numeric_claim_rate": rate("unsupported_numeric_claim"),
        "actionability_rate": rate("actionability"),
        "timeout_rate": sum(row.get("failure_code") == "ollama_timeout" for row in rows) / count,
        "invalid_json_rate": sum(row.get("failure_code") == "invalid_json" for row in rows) / count,
        "latency_ms_median": float(statistics.median(latencies)),
        "latency_ms_p95": float(percentile(latencies, 0.95)),
    }


def evaluate_case(case: dict[str, Any], model: str, url: str, timeout: float) -> dict[str, Any]:
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from prunin_ai.api.recommendations import generate_ollama_grounded

    result = generate_ollama_grounded(
        case["prediction"], case.get("drivers", case["risk_drivers"]), row=case.get("input"), model=model, url=url, timeout=timeout
    )
    validation = result["validation"]
    return {
        "case_id": case["case_id"],
        "model": model,
        "generation_success": bool(result["ok"]),
        "schema_valid": bool(validation["schema_valid"]),
        "grounded": bool(validation["grounded"]),
        "unsupported_numeric_claim": bool(validation["unsupported_numeric_claim"]),
        "actionability": bool(validation["actionability"]),
        "latency_ms": float(result["latency_ms"]),
        "failure_code": result.get("failure_code"),
        "health": case.get("health"),
        "driver_count": len(case["risk_drivers"]),
    }


def hardware_metadata() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
    }