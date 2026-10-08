#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGETS = ("health", "final_status", "delay_days", "cost_overrun_ratio")

parser = argparse.ArgumentParser(description="Valida las métricas de evaluación del entrenamiento.")
parser.add_argument("--artifact", required=True)
args = parser.parse_args()
artifact_dir = Path(args.artifact)
metrics_path = artifact_dir / "metrics.json"
if not metrics_path.is_file():
    raise SystemExit(f"Falta evaluación: {metrics_path}")
metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
failures = []
for target in TARGETS:
    result = metrics.get(target, {})
    if result.get("status") != "trained" or not result.get("test"):
        failures.append(target)
if failures:
    raise SystemExit("Evaluación incompleta; targets sin modelo/test: " + ", ".join(failures))
evaluation = {"targets": {name: metrics[name] for name in TARGETS}, "status": "passed"}
(artifact_dir / "evaluation.json").write_text(
    json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8"
)
for target in TARGETS:
    print(f"[OK] {target}: test={metrics[target]['test']}")