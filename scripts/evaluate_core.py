#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

MODEL_TARGETS = ("health", "delay_days", "cost_overrun_ratio")

parser = argparse.ArgumentParser(description="Valida las métricas de evaluación del entrenamiento.")
parser.add_argument("--artifact", required=True)
args = parser.parse_args()
artifact_dir = Path(args.artifact)
metrics_path = artifact_dir / "metrics.json"
if not metrics_path.is_file():
    raise SystemExit(f"Falta evaluación: {metrics_path}")
metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
failures = []
for target in MODEL_TARGETS:
    result = metrics.get(target, {})
    if result.get("status") != "trained" or not result.get("test"):
        failures.append(target)
status = metrics.get("final_status", {})
if status.get("status") not in {"trained", "derived"}:
    failures.append("final_status")
if failures:
    raise SystemExit("Evaluación incompleta; targets sin modelo/test: " + ", ".join(failures))
targets = {name: metrics[name] for name in MODEL_TARGETS + ("final_status",)}
evaluation = {"targets": targets, "status": "passed"}
(artifact_dir / "evaluation.json").write_text(
    json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8"
)
for target in MODEL_TARGETS:
    print(f"[OK] {target}: test={metrics[target]['test']}")
if status["status"] == "derived":
    print("[OK] final_status: derived from Health; no independent model evaluated")
else:
    print(f"[OK] final_status: test={status['test']}")