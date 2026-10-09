#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.api.catalog import FIELD_MAP
from prunin_ai.api.model_runtime import ModelRuntime
from prunin_ai.api.recommendations import generate_ollama_grounded


def _latest_per_project(frame: pd.DataFrame) -> pd.DataFrame:
    order = ["project_id"]
    if "snapshot_index" in frame.columns:
        order.append("snapshot_index")
    elif "true_progress" in frame.columns:
        order.append("true_progress")
    return frame.sort_values(order).groupby("project_id", as_index=False).tail(1)


def _ollama_available(url: str) -> tuple[bool, str | None]:
    tags_url = url.rsplit("/api/", 1)[0] + "/api/tags" if "/api/" in url else url.rstrip("/") + "/api/tags"
    try:
        response = requests.get(tags_url, timeout=3)
        response.raise_for_status()
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def evaluate(artifact: Path, input_path: Path, model: str, cases: int, output: Path) -> dict:
    os.environ["PRUNIN_ARTIFACT_DIR"] = str(artifact)
    runtime = ModelRuntime()
    split = json.loads((artifact / "split_manifest.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(input_path, low_memory=False)
    frame["project_id"] = frame["project_id"].astype(str)
    test = frame[frame["project_id"].isin(set(map(str, split["test"])))].copy()
    latest = _latest_per_project(test).sample(frac=1.0, random_state=42)

    url = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    available, error = _ollama_available(url)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not available:
        report = {
            "status": "unavailable",
            "model": model,
            "ollama_url": url,
            "reason": error,
            "note": "No generative-model performance claim is valid until this benchmark is executed with Ollama available.",
        }
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report

    rows = []
    for _, source in latest.iterrows():
        if len(rows) >= cases:
            break
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
        result = generate_ollama_grounded(prediction, risk_drivers, model=model, url=url, timeout=30)
        validation = result["validation"]
        rows.append({
            "project_id": str(source["project_id"]),
            "health": prediction.get("health"),
            "driver_count": len(risk_drivers),
            "generation_ok": bool(result["ok"]),
            "schema_valid": bool(validation["schema_valid"]),
            "evidence_features_valid": bool(validation["evidence_features_valid"]),
            "grounded": bool(validation["grounded"]),
            "actionability": bool(validation["actionability"]),
            "unsupported_numeric_claim": bool(validation["unsupported_numeric_claim"]),
            "latency_ms": float(result["latency_ms"]),
            "error": result.get("error"),
            "referenced_evidence_features": validation.get("referenced_evidence_features", []),
            "allowed_evidence_features": validation.get("allowed_evidence_features", []),
            "payload": result.get("payload"),
        })

    if not rows:
        raise RuntimeError("No evaluable cases with increasing-risk drivers were found.")

    def rate(key: str) -> float:
        return sum(bool(row[key]) for row in rows) / len(rows)

    latencies = [row["latency_ms"] for row in rows]
    summary = {
        "status": "complete",
        "model": model,
        "artifact_version": runtime.version,
        "dataset_source": runtime.manifest.get("dataset_source"),
        "evaluation_unit": "latest TEST project snapshot with at least one increasing-risk local driver",
        "cases_requested": cases,
        "cases_evaluated": len(rows),
        "metrics": {
            "generation_success_rate": rate("generation_ok"),
            "schema_valid_rate": rate("schema_valid"),
            "evidence_feature_valid_rate": rate("evidence_features_valid"),
            "grounded_response_rate": rate("grounded"),
            "actionability_rate": rate("actionability"),
            "unsupported_numeric_claim_rate": rate("unsupported_numeric_claim"),
            "latency_ms_median": float(statistics.median(latencies)),
            "latency_ms_p95": float(sorted(latencies)[min(len(latencies) - 1, round((len(latencies) - 1) * 0.95))]),
        },
        "metric_definition_note": "Groundedness is a deterministic proxy: valid JSON schema, all cited evidence features are allow-listed drivers, and no new numeric claims appear. It does not prove semantic causality.",
        "cases": rows,
    }
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = output.with_suffix(".csv")
    pd.DataFrame([{k: v for k, v in row.items() if k not in {"payload", "referenced_evidence_features", "allowed_evidence_features"}} for row in rows]).to_csv(csv_path, index=False)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="artifacts/0.9.0-academic")
    parser.add_argument("--input", default="data/processed/mendeley_core.csv")
    parser.add_argument("--model", default=os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--output", default="reports/genai/qwen3-8b-evaluation.json")
    args = parser.parse_args()
    report = evaluate(ROOT / args.artifact, ROOT / args.input, args.model, args.cases, ROOT / args.output)
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2, ensure_ascii=False))
    if report.get("status") != "complete":
        raise SystemExit(2)
