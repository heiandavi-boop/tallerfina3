from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from ..constants import STATIC_NUMERIC_FEATURES, CATEGORICAL_FEATURES, CORE_TEMPORAL_FEATURES, TARGETS


def audit_dataframe(df: pd.DataFrame) -> dict:
    cols = STATIC_NUMERIC_FEATURES + CATEGORICAL_FEATURES + CORE_TEMPORAL_FEATURES + ["team_health_index"]
    coverage = {}
    for c in cols:
        coverage[c] = float(df[c].notna().mean()) if c in df.columns else 0.0
    targets = {}
    for c in TARGETS:
        targets[c] = float(df[c].notna().mean()) if c in df.columns else 0.0
    sources = df.get("data_source", pd.Series(["unknown"] * len(df))).value_counts(dropna=False).to_dict()
    synth = float(pd.to_numeric(df.get("is_synthetic", False), errors="coerce").fillna(0).astype(bool).mean()) if len(df) else 0.0
    return {
        "rows": int(len(df)),
        "projects": int(df["project_id"].nunique()) if "project_id" in df.columns else None,
        "feature_coverage": coverage,
        "target_coverage": targets,
        "sources": {str(k): int(v) for k, v in sources.items()},
        "synthetic_row_fraction": synth,
    }


def save_audit(report: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
