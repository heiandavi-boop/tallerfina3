from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_reproducibility(
    repository_root: str | Path,
    artifact_version: str,
    config: dict,
    readiness: dict,
    split_manifest: dict,
) -> dict:
    root = Path(repository_root)
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    try:
        manifest = json.loads((root / "data/raw/dataset_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {"files": []}
    raw_hashes = {
        row["local_path"]: row["sha256"]
        for row in manifest.get("files", [])
        if row.get("dataset") == "mendeley_evm" and row.get("sha256")
    }
    packages = {
        name: importlib.metadata.version(distribution)
        for name, distribution in {
            "pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn",
            "lightgbm": "lightgbm",
        }.items()
    }
    return {
        "python_version": platform.python_version(),
        "packages": packages,
        "git_commit_sha": commit,
        "random_seed": int(config.get("random_seed", 42)),
        "dataset_sha256": {
            "processed": readiness.get("processed_sha256"),
            "raw_mendeley_files": raw_hashes,
        },
        "training_config": config,
        "artifact_version": artifact_version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "split_project_counts": {name: len(projects) for name, projects in split_manifest.items()},
    }