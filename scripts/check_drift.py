#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.monitoring.drift import build_reference_profile, compare_feature_distributions


def build_train_reference(artifact: Path, input_path: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((artifact / "feature_manifest.json").read_text(encoding="utf-8"))
    split = json.loads((artifact / "split_manifest.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(input_path, low_memory=False)
    if "project_id" not in frame:
        raise ValueError("El dataset de referencia debe contener project_id.")
    frame["project_id"] = frame["project_id"].astype(str)
    train_ids = set(map(str, split["train"]))
    reference = frame[frame["project_id"].isin(train_ids)].copy()
    if reference.empty:
        raise ValueError("El dataset no contiene proyectos TRAIN del split manifest.")
    profile = build_reference_profile(
        reference,
        manifest.get("numeric_features", []),
        manifest.get("categorical_features", []),
    )
    profile.update({
        "artifact_version": artifact.name,
        "reference_project_count": len(train_ids),
        "reference_snapshot_count": len(reference),
        "dataset_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "split_sha256": hashlib.sha256((artifact / "split_manifest.json").read_bytes()).hexdigest(),
    })
    return reference, profile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Perfil TRAIN y compara un batch para alertas académicas de drift.")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/0.9.0-academic")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/mendeley_core.csv")
    parser.add_argument("--batch", type=Path, help="CSV nuevo a comparar; sin esto solo escribe el perfil TRAIN.")
    parser.add_argument(
        "--profile-output",
        type=Path,
        help="Ruta del perfil; el valor predeterminado queda en reports/ y no modifica los artefactos académicos.",
    )
    parser.add_argument("--report-output", type=Path, help="Ruta opcional para guardar el reporte de drift.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/monitoring/drift")
    parser.add_argument("--fail-on-alert", action="store_true", help="Termina con código 2 cuando haya alerta.")
    parser.add_argument("--psi-threshold", type=float, default=0.2)
    parser.add_argument("--missing-rate-shift-threshold", type=float, default=0.1)
    args = parser.parse_args(argv)
    artifact = args.artifact.resolve()
    input_path = args.input.resolve()
    default_profile = ROOT / "reports/monitoring/profiles" / f"{artifact.name}-train-profile.json"
    profile_output = (args.profile_output or default_profile).resolve()
    reference, profile = build_train_reference(artifact, input_path)
    profile["thresholds"] = {
        "psi": args.psi_threshold,
        "missing_rate_shift": args.missing_rate_shift_threshold,
    }
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    profile_output.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    result = {
        "status": "profile_created",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "profile_path": str(profile_output),
        "reference_split": "TRAIN",
        "reference_dataset_sha256": profile["dataset_sha256"],
        "split_manifest_sha256": profile["split_sha256"],
        "retraining_triggered": False,
    }
    if args.batch:
        batch_path = args.batch.resolve()
        current = pd.read_csv(batch_path, low_memory=False)
        report = compare_feature_distributions(
            reference,
            current,
            profile,
            psi_threshold=args.psi_threshold,
            missing_rate_shift_threshold=args.missing_rate_shift_threshold,
        )
        expected_features = list(profile["numeric"]) + list(profile["categorical"])
        missing_columns = sorted(set(expected_features) - set(current.columns))
        report["generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        report["artifact_version"] = artifact.name
        report["profile_path"] = str(profile_output)
        report["retraining_triggered"] = False
        report["input_hashes"] = {
            "reference_dataset_sha256": profile["dataset_sha256"],
            "split_manifest_sha256": profile["split_sha256"],
            "current_batch_sha256": sha256_file(batch_path),
        }
        report["data_quality"] = {
            "expected_feature_count": len(expected_features),
            "missing_feature_columns": missing_columns,
            "current_missing_rate_by_feature": {
                feature: float(current[feature].isna().mean()) if feature in current else 1.0
                for feature in expected_features
            },
            "missing_schema_alert": bool(missing_columns),
        }
        report["alert"] = bool(report["alert"] or missing_columns)
        result = report
        report_path = (
            args.report_output.resolve()
            if args.report_output
            else args.output_dir.resolve()
            / f"drift-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{report['input_hashes']['current_batch_sha256'][:8]}.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report["report_path"] = str(report_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if args.batch and args.fail_on_alert and result["alert"] else 0


if __name__ == "__main__":
    raise SystemExit(main())