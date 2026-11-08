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

from prunin_ai.monitoring.drift import build_reference_profile, compare_feature_distributions


def build_train_reference(artifact: Path, input_path: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((artifact / "feature_manifest.json").read_text(encoding="utf-8"))
    split = json.loads((artifact / "split_manifest.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(input_path, low_memory=False)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Perfil TRAIN y compara un batch para alertas académicas de drift.")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/0.9.0-academic")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/mendeley_core.csv")
    parser.add_argument("--batch", type=Path, help="CSV nuevo a comparar; sin esto solo escribe el perfil TRAIN.")
    parser.add_argument("--profile-output", type=Path, help="Ruta del perfil; por defecto <artifact>/input_profile.json.")
    parser.add_argument("--report-output", type=Path, help="Ruta opcional para guardar el reporte de drift.")
    parser.add_argument("--psi-threshold", type=float, default=0.2)
    parser.add_argument("--missing-rate-shift-threshold", type=float, default=0.1)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    input_path = args.input.resolve()
    profile_output = (args.profile_output or artifact / "input_profile.json").resolve()
    reference, profile = build_train_reference(artifact, input_path)
    profile["thresholds"] = {
        "psi": args.psi_threshold,
        "missing_rate_shift": args.missing_rate_shift_threshold,
    }
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    profile_output.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    result = {"status": "profile_created", "profile_path": str(profile_output), "reference_split": "TRAIN"}
    if args.batch:
        current = pd.read_csv(args.batch.resolve(), low_memory=False)
        report = compare_feature_distributions(
            reference,
            current,
            profile,
            psi_threshold=args.psi_threshold,
            missing_rate_shift_threshold=args.missing_rate_shift_threshold,
        )
        report["profile_path"] = str(profile_output)
        result = report
        if args.report_output:
            report_path = args.report_output.resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())