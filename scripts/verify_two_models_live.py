#!/usr/bin/env python3
"""Live smoke test for PRUNIN's two authorized local Ollama models.

Run only with a working API, official local artifacts and both Ollama models
installed; does not install models, retrain or modify frozen reports.

Example:
  python scripts/verify_two_models_live.py --csv ~/Downloads/PRUNIN_Proyecto_Bancario_Escenario_Base.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import requests

MODELS = ("qwen3:8b", "gpt-oss:20b")
NUMERIC = {
    "planned_duration_weeks", "planned_budget", "baseline_scope_units",
    "true_progress", "spi", "cpi", "team_utilization", "team_capacity_ratio",
    "average_productivity", "defect_rate", "rework_ratio", "scope_growth_ratio",
    "dependency_delay_days", "normalized_risk_exposure", "governance_health_score",
    "team_stability", "collaboration_level",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True, help="Single-row PRUNIN input CSV")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--token", default=None, help="API token if configured; do not publish")
    args = parser.parse_args()
    with args.csv.expanduser().open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if len(rows) != 1:
        raise SystemExit("ERROR: El CSV debe contener exactamente un proyecto.")
    row = {key: float(value) if key in NUMERIC else value
           for key, value in rows[0].items() if value is not None and value != ""}
    base = args.api.rstrip("/")
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    try:
        response = requests.get(base + "/api/genai-models", headers=headers, timeout=15)
        response.raise_for_status()
        catalog = response.json()
        installed = {item["id"] for item in catalog.get("models", []) if item.get("installed")}
        print("Modelos Ollama instalados:", ", ".join(sorted(installed)) or "(ninguno)")
        missing = set(MODELS) - installed
        if missing:
            print("BLOQUEADO: Instala primero estos modelos:", ", ".join(sorted(missing)))
            return 2
        responses = {}
        for model in MODELS:
            print(f"Probando {model}...")
            response = requests.post(
                base + "/api/predict",
                json=row,
                headers={**headers, "X-PRUNIN-Provider": "ollama", "X-PRUNIN-Model": model},
                timeout=args.timeout,
            )
            response.raise_for_status()
            result = response.json()
            genai = result.get("recommendations", {})
            print(json.dumps({
                "model": model,
                "engine": genai.get("engine"),
                "genai_attempted": genai.get("genai_attempted"),
                "genai_used": genai.get("genai_used"),
                "grounded": genai.get("grounding", {}).get("grounded"),
                "failure_code": genai.get("failure_code"),
                "latency_ms": genai.get("genai_latency_ms"),
                "health": result.get("prediction", {}).get("health"),
            }, ensure_ascii=False))
            responses[model] = result
        a, b = (responses[name] for name in MODELS)
        ml_keys = ("health", "health_probabilities", "delay_days_raw", "cost_overrun_ratio")
        stable = all(a["prediction"].get(k) == b["prediction"].get(k) for k in ml_keys)
        good = all(
            responses[model]["recommendations"].get("engine") == f"ollama:{model}"
            and responses[model]["recommendations"].get("genai_used") is True
            and responses[model]["recommendations"].get("grounding", {}).get("grounded") is True
            for model in MODELS
        )
        print("Predicciones ML idénticas:", stable)
        print("Ambos modelos generan recomendaciones validadas:", good)
        if not (stable and good):
            print("FALLO: revisar el mensaje de error del modelo y el contrato de recomendaciones.")
            return 1
        print("OK: selector de los dos modelos verificado por API.")
        return 0
    except (OSError, ValueError, requests.RequestException) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
