from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..constants import STATIC_NUMERIC_FEATURES, CATEGORICAL_FEATURES, CORE_TEMPORAL_FEATURES, TARGETS


def _outlier_profile(df: pd.DataFrame, columns: list[str]) -> dict:
    profile = {}
    for column in columns:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        profile[column] = {
            "method": "IQR_1.5",
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower,
            "upper_bound": upper,
            "outlier_count": int(mask.sum()),
            "outlier_fraction": float(mask.mean()),
        }
    return profile


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
    numeric_candidates = STATIC_NUMERIC_FEATURES + CORE_TEMPORAL_FEATURES
    return {
        "rows": int(len(df)),
        "projects": int(df["project_id"].nunique()) if "project_id" in df.columns else None,
        "feature_coverage": coverage,
        "target_coverage": targets,
        "sources": {str(k): int(v) for k, v in sources.items()},
        "synthetic_row_fraction": synth,
        "outlier_detection": {
            "status": "reported_not_silently_removed",
            "method": "IQR 1.5x on available numeric candidate features",
            "features": _outlier_profile(df, numeric_candidates),
        },
        "normalization_policy": {
            "applied": False,
            "reason": "The supervised core uses tree-based LightGBM models; numeric scaling is not required for split-based trees. Raw scale is retained and categorical variables are explicitly encoded.",
        },
    }


def save_audit(report: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
