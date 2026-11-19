#!/usr/bin/env python3
"""Fail-closed MLOps retraining decision; never starts training or promotes models.

A drift alert alone is insufficient to retrain. An approved, labeled, new
dataset and an explicit human decision are required. This tool documents
readiness without modifying frozen scientific artifacts.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def decide(drift: dict, labels: dict | None, approved: bool) -> dict:
    blockers = []
    if drift.get("status") != "complete":
        blockers.append("drift_report_not_complete")
    if not drift.get("alert"):
        blockers.append("no_confirmed_drift_alert")
    if drift.get("artifact_version") == "demo-0.1.0":
        blockers.append("demo_artifact_not_eligible")
    hashes = drift.get("input_hashes") or {}
    batch_hash = hashes.get("current_batch_sha256")
    reference_hash = hashes.get("reference_dataset_sha256")
    if not batch_hash or not reference_hash or batch_hash == reference_hash:
        blockers.append("new_independent_batch_not_verified")
    if labels is None:
        blockers.append("no_labeled_outcomes_manifest")
    else:
        if labels.get("approved") is not True:
            blockers.append("labeled_dataset_not_approved")
        if labels.get("outcomes_verified") is not True:
            blockers.append("outcomes_not_verified")
        if labels.get("batch_sha256") != batch_hash:
            blockers.append("labels_do_not_match_batch")
        if not isinstance(labels.get("project_count"), int) or labels["project_count"] < 30:
            blockers.append("insufficient_labeled_projects")
    if not approved:
        blockers.append("human_approval_missing")
    return {
        "status": "ELIGIBLE_FOR_CANDIDATE_TRAINING" if not blockers else "BLOCKED",
        "retraining_executed": False,
        "promotion_executed": False,
        "production_data_validated": False,
        "blockers": blockers,
        "model_version": drift.get("artifact_version"),
        "current_batch_sha256": batch_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drift-report", type=Path, required=True)
    parser.add_argument("--labels-manifest", type=Path)
    parser.add_argument("--approved", action="store_true", help="Explicit human decision for candidate evaluation only")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    drift = json.loads(args.drift_report.read_text(encoding="utf-8"))
    labels = json.loads(args.labels_manifest.read_text(encoding="utf-8")) if args.labels_manifest else None
    result = decide(drift, labels, args.approved)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["blockers"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
