#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prunin_ai.config import load_config
from prunin_ai.training.core import _split_groups


def verify_and_save_split(input_path: Path, artifact_dir: Path, readiness_path: Path) -> dict:
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    if readiness.get("blocking_errors") or not readiness.get("main_dataset_valid"):
        raise RuntimeError("TRAINING BLOCKED: dataset did not pass readiness checks")
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    if digest != readiness.get("processed_sha256"):
        raise RuntimeError("Processed dataset changed after readiness checks.")
    df = pd.read_csv(input_path, usecols=["project_id"], low_memory=False)
    config = load_config(ROOT / "configs/training.yaml")
    indices = _split_groups(df, int(config.get("random_seed", 42)))
    names = ("train", "validation", "test")
    project_sets = {
        name: set(df.iloc[index]["project_id"].astype(str))
        for name, index in zip(names, indices, strict=True)
    }
    train_project_ids = project_sets["train"]
    validation_project_ids = project_sets["validation"]
    test_project_ids = project_sets["test"]
    checks = {
        "train_project_ids.isdisjoint(validation_project_ids)": train_project_ids.isdisjoint(validation_project_ids),
        "train_project_ids.isdisjoint(test_project_ids)": train_project_ids.isdisjoint(test_project_ids),
        "validation_project_ids.isdisjoint(test_project_ids)": validation_project_ids.isdisjoint(test_project_ids),
    }
    if not all(checks.values()):
        readiness["ready_for_training"] = False
        readiness["leakage_check"] = {"status": "failed", "checks": checks}
        readiness["blocking_errors"] = sorted(set(readiness["blocking_errors"] + [
            "Project ID leakage detected between train, validation, and test splits."
        ]))
        readiness_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")
        raise RuntimeError("TRAINING BLOCKED: project IDs overlap between data splits.")
    split_manifest = {name: sorted(values) for name, values in project_sets.items()}
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "split_manifest.json").write_text(
        json.dumps(split_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    readiness["leakage_check"] = {
        "status": "passed", "checked_before_training": True, "checks": checks,
        "project_counts": {name: len(values) for name, values in project_sets.items()},
    }
    readiness["ready_for_training"] = not readiness["blocking_errors"]
    readiness_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")
    if not readiness["ready_for_training"]:
        raise RuntimeError("TRAINING BLOCKED: dataset did not pass readiness checks")
    return split_manifest


if __name__ == "__main__":
    try:
        verify_and_save_split(
            ROOT / "data/processed/mendeley_core.csv",
            ROOT / "artifacts/0.9.0-academic",
            ROOT / "artifacts/data_readiness.json",
        )
        print("Leakage verification: PASS")
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)