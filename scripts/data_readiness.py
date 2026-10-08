#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.constants import CATEGORICAL_FEATURES, CORE_TEMPORAL_FEATURES, STATIC_NUMERIC_FEATURES

MAIN_DATASET = "mendeley_evm"
MAIN_DOI = "10.17632/2p5sz57wh2.2"
MAIN_FILES = {
    "data/raw/mendeley/project_risk_raw_dataset.csv",
    "data/raw/mendeley/simulated_project_ev_metrics_final.csv.xlsx",
    "data/raw/mendeley/project_delay_cost_overrun_summary_final.csv.xlsx",
}
TARGET_COLUMNS = ("health", "final_status", "delay_days", "cost_overrun_ratio")
MIN_ROWS = 500
MIN_PROJECTS = 100
MIN_TARGET_COVERAGE = 0.80


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).items()}


def build_readiness(
    df: pd.DataFrame | None,
    audit: dict | None,
    manifest: dict | None,
    processed_path: Path | None,
    blocking_errors: list[str] | None = None,
) -> dict:
    errors = list(blocking_errors or [])
    warnings = list((manifest or {}).get("warnings", []))
    file_rows = (manifest or {}).get("files", [])
    valid_main_files = {
        row.get("local_path") for row in file_rows
        if row.get("dataset") == MAIN_DATASET
        and row.get("doi") == MAIN_DOI
        and row.get("record/version") == "version 2"
        and row.get("synthetic") is True
        and row.get("validation_status") == "valid"
    }
    main_valid = MAIN_FILES <= valid_main_files
    if not main_valid:
        errors.append("Mendeley v2 is missing one or more required, validated source files.")

    available = sorted({row.get("dataset") for row in file_rows if row.get("dataset")})
    expected = {MAIN_DATASET, "itemlet", "collaboration", "squad"}
    missing = sorted(expected - set(available))
    for name in missing:
        if name != MAIN_DATASET:
            warnings.append(f"[WARN] Optional dataset unavailable: {name}")

    snapshot_count = int(len(df)) if df is not None else 0
    project_count = int(df["project_id"].nunique()) if df is not None and "project_id" in df else 0
    feature_names = STATIC_NUMERIC_FEATURES + CATEGORICAL_FEATURES + CORE_TEMPORAL_FEATURES
    feature_coverage = {
        name: float((audit or {}).get("feature_coverage", {}).get(name, 0.0))
        for name in feature_names
    }
    missing_features = [name for name, coverage in feature_coverage.items() if coverage <= 0]
    target_coverage = (audit or {}).get("target_coverage", {})
    target_distribution = {}
    health_distribution = {}
    final_status_distribution = {}
    if df is not None:
        for target in TARGET_COLUMNS:
            if target not in df:
                continue
            if target in {"health", "final_status"}:
                distribution = _counts(df[target])
                target_distribution[target] = distribution
                if target == "health":
                    health_distribution = distribution
                else:
                    final_status_distribution = distribution
            else:
                values = pd.to_numeric(df[target], errors="coerce").dropna()
                target_distribution[target] = {
                    "count": int(values.size),
                    "min": float(values.min()) if values.size else None,
                    "median": float(values.median()) if values.size else None,
                    "max": float(values.max()) if values.size else None,
                }

    if df is None:
        errors.append("Prepared Mendeley dataset is unavailable.")
    else:
        if snapshot_count < MIN_ROWS:
            errors.append(f"Snapshot count {snapshot_count} is below minimum {MIN_ROWS}.")
        if project_count < MIN_PROJECTS:
            errors.append(f"Project count {project_count} is below minimum {MIN_PROJECTS}.")
        for target in TARGET_COLUMNS:
            coverage = float(target_coverage.get(target, 0.0))
            if coverage < MIN_TARGET_COVERAGE:
                errors.append(f"Target coverage for {target} is {coverage:.3f}, below {MIN_TARGET_COVERAGE:.2f}.")
        if "data_source" not in df or set(df["data_source"].dropna().astype(str)) != {"mendeley_2p5sz57wh2_v2"}:
            errors.append("Academic input must contain only the Mendeley v2 source.")
        if "source_project_id" not in df or df["source_project_id"].isna().any():
            errors.append("Mendeley source_project_id is missing or incomplete.")
        if "project_id" not in df or not df["project_id"].astype(str).str.startswith("mendeley::").all():
            errors.append("Mendeley project_id values must retain the mendeley:: namespace.")
        elif "source_project_id" in df and not (
            df["project_id"].astype(str) == "mendeley::" + df["source_project_id"].astype(str)
        ).all():
            errors.append("project_id does not match its source_project_id namespace mapping.")

    synthetic_sources = sorted({
        row.get("dataset") for row in file_rows if row.get("synthetic") is True and row.get("dataset")
    })
    real_sources = sorted({
        row.get("dataset") for row in file_rows if row.get("synthetic") is False and row.get("dataset")
    })
    readiness = {
        "ready_for_training": False,
        "blocking_errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "datasets_available": available,
        "datasets_missing": missing,
        "main_dataset_valid": main_valid,
        "project_count": project_count,
        "snapshot_count": snapshot_count,
        "feature_coverage": feature_coverage,
        "target_distribution": target_distribution,
        "health_distribution": health_distribution,
        "final_status_distribution": final_status_distribution,
        "missing_features": missing_features,
        "leakage_check": {"status": "pending", "checked_before_training": False},
        "synthetic_sources": synthetic_sources,
        "real_sources": real_sources,
        "processed_sha256": file_sha256(processed_path) if processed_path and processed_path.is_file() else None,
        "leakage_risks": [
            "Project outcomes are repeated across monthly snapshots.",
            "Same-period SPI/CPI/progress may be temporally close to final outcomes; this is not a prospective time-cutoff evaluation.",
            "Direct target, actual-duration and actual-cost columns are excluded from the model feature whitelist.",
        ],
    }
    readiness["ready_for_training"] = not readiness["blocking_errors"]
    return readiness


def write_readiness(readiness: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/mendeley_core.csv")
    parser.add_argument("--audit", default="artifacts/0.9.0-academic-audit.json")
    parser.add_argument("--manifest", default="data/raw/dataset_manifest.json")
    parser.add_argument("--output", default="artifacts/data_readiness.json")
    parser.add_argument("--blocking-error", action="append", default=[])
    args = parser.parse_args()
    input_path = ROOT / args.input
    audit_path = ROOT / args.audit
    manifest_path = ROOT / args.manifest
    df = pd.read_csv(input_path, low_memory=False) if input_path.is_file() else None
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    readiness = build_readiness(
        df, audit, manifest, input_path if input_path.is_file() else None, args.blocking_error
    )
    output = ROOT / args.output
    write_readiness(readiness, output)
    print(json.dumps(readiness, indent=2, ensure_ascii=False))
    if readiness["blocking_errors"]:
        print("TRAINING BLOCKED: dataset did not pass readiness checks", file=sys.stderr)
        return 1
    print("DATA READINESS: dataset checks passed; project leakage is pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())