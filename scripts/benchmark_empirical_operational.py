from __future__ import annotations

import argparse
import io
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    return float(pd.Series(values).quantile(quantile))


def summarize(samples: list[dict[str, Any]], key: str, project_count: int) -> dict[str, Any]:
    durations = [item[key] for item in samples]
    median_seconds = statistics.median(durations)
    return {
        "runs": len(durations),
        "median_total_ms": round(median_seconds * 1000, 3),
        "p95_total_ms": round(percentile(durations, 0.95) * 1000, 3),
        "median_projects_per_second": round(project_count / median_seconds, 4) if median_seconds else None,
        "success_rate_percent": round(sum(item["success"] for item in samples) * 100 / len(samples), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local PRUNIN Empirical inference using DSLIB TEST inputs.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least one")

    registry_path = ROOT / "artifacts" / "model_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    empirical = next(item for item in registry["models"] if item.get("id") == "empirical")
    artifact_dir = ROOT / empirical["artifact_path"]
    split = json.loads((artifact_dir / "split_manifest.json").read_text(encoding="utf-8"))
    test_ids = set(split["targets"]["delay"]["test"])
    frame = pd.read_csv(ROOT / "data" / "processed" / "dslib" / "model_samples.csv")
    rows = frame[frame["project_id"].isin(test_ids)][["project_id", "planned_duration_days", "planned_budget_bac"]].dropna()
    if len(rows) != len(test_ids):
        raise RuntimeError("Processed DSLIB data do not contain all empirical TEST feature rows.")
    inputs = [
        {
            "planned_duration_weeks": float(row.planned_duration_days) / 7.0,
            "planned_budget": float(row.planned_budget_bac),
        }
        for row in rows.itertuples(index=False)
    ]
    csv_bytes = pd.DataFrame(inputs).to_csv(index=False).encode("utf-8")
    base_url = args.api_url.rstrip("/")
    individual_url = f"{base_url}/api/predict?model_id=empirical&include_recommendations=false"
    batch_url = f"{base_url}/api/predict-csv?model_id=empirical"
    session = requests.Session()

    for item in inputs[:1]:
        warmup = session.post(individual_url, json=item, timeout=30)
        warmup.raise_for_status()
    warmup_batch = session.post(batch_url, files={"file": ("empirical-warmup.csv", csv_bytes, "text/csv")}, timeout=30)
    warmup_batch.raise_for_status()

    individual_samples = []
    batch_samples = []
    for _ in range(args.repeats):
        started = time.perf_counter()
        individual_success = 0
        for item in inputs:
            response = session.post(individual_url, json=item, timeout=30)
            if response.ok and response.json().get("model", {}).get("id") == "empirical":
                individual_success += 1
        individual_samples.append({"seconds": time.perf_counter() - started, "success": individual_success == len(inputs)})

        started = time.perf_counter()
        response = session.post(batch_url, files={"file": ("empirical-test.csv", csv_bytes, "text/csv")}, timeout=30)
        batch_success = False
        if response.ok:
            body = response.json()
            batch_success = body.get("count") == len(inputs) and all(row.get("prediction") for row in body.get("rows", []))
        batch_samples.append({"seconds": time.perf_counter() - started, "success": batch_success})

    individual = summarize(individual_samples, "seconds", len(inputs))
    batch = summarize(batch_samples, "seconds", len(inputs))
    dataset_manifest = json.loads((ROOT / "data" / "raw" / "dslib" / "dataset_manifest.json").read_text(encoding="utf-8"))
    report = {
        "status": "complete" if individual["success_rate_percent"] == 100 and batch["success_rate_percent"] == 100 else "incomplete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_id": "empirical",
        "model_version": empirical["version"],
        "dataset": "DSLIB / PSLIB v3.4",
        "dataset_hash": dataset_manifest["files"][0]["sha256"],
        "evaluation_split": "TEST",
        "project_count": len(inputs),
        "repeats": args.repeats,
        "warmups": {"individual": 1, "batch": 1},
        "environment": {"os": platform.platform(), "python": platform.python_version(), "api_url": args.api_url},
        "individual_sequential": individual,
        "csv_batch_sequential": batch,
        "batch_over_individual_speedup": round(individual["median_total_ms"] / batch["median_total_ms"], 4) if batch["median_total_ms"] else None,
        "interpretation": "Local sequential operational measurement only. Not a production load test, concurrency result, human productivity estimate, or predictive-accuracy comparison.",
    }
    output_dir = ROOT / "reports" / "efficiency"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "empirical_operational_benchmark.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "projects": len(inputs), "individual": individual, "batch": batch, "report": str(output_path.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()