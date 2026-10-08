#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from download_datasets import validate_local_datasets
from prunin_ai.config import load_config
from prunin_ai.data.adapters.mendeley_evm import prepare_mendeley
from prunin_ai.targets import add_targets


def prepare() -> Path:
    validate_local_datasets()
    raw = ROOT / "data/raw/mendeley"
    paths = {
        "static": raw / "project_risk_raw_dataset.csv",
        "timeseries": raw / "simulated_project_ev_metrics_final.csv.xlsx",
        "summary": raw / "project_delay_cost_overrun_summary_final.csv.xlsx",
    }
    df = prepare_mendeley(paths["static"], paths["timeseries"], paths["summary"])
    config = load_config(ROOT / "configs/training.yaml")
    df = add_targets(df, config["target_rules"])
    output = ROOT / "data/processed/mendeley_core.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(
        f"[OK] Prepared Mendeley only: {output.relative_to(ROOT)} | "
        f"snapshots={len(df)} | projects={df.project_id.nunique()}"
    )
    return output


if __name__ == "__main__":
    prepare()