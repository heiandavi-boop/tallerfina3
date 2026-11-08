from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd


def build_reference_profile(
    reference: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
    *,
    iqr_multiplier: float = 1.5,
) -> dict[str, Any]:
    if reference.empty:
        raise ValueError("La referencia TRAIN no puede estar vacía.")
    if iqr_multiplier <= 0:
        raise ValueError("iqr_multiplier debe ser positivo.")

    numeric: dict[str, dict[str, float]] = {}
    for feature in numeric_features:
        source = reference.get(feature, pd.Series(index=reference.index, dtype="float64"))
        values = pd.to_numeric(source, errors="coerce")
        observed = values.dropna()
        if observed.empty:
            continue
        q1, median, q3 = (float(observed.quantile(q)) for q in (0.25, 0.5, 0.75))
        iqr = q3 - q1
        numeric[feature] = {
            "q1": q1,
            "median": median,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": q1 - iqr_multiplier * iqr,
            "upper_bound": q3 + iqr_multiplier * iqr,
            "missing_rate": float(values.isna().mean()),
        }

    categorical: dict[str, dict[str, Any]] = {}
    for feature in categorical_features:
        values = reference.get(feature, pd.Series(index=reference.index, dtype="object"))
        counts = values.fillna("__MISSING__").astype(str).value_counts(normalize=True)
        categorical[feature] = {
            "categories": sorted(str(value) for value in values.dropna().unique()),
            "distribution": {str(key): float(value) for key, value in counts.items()},
            "missing_rate": float(values.isna().mean()),
        }
    return {
        "profile_version": 1,
        "reference_split": "TRAIN",
        "numeric": numeric,
        "categorical": categorical,
        "thresholds": {"psi": 0.2, "missing_rate_shift": 0.1},
    }


def assess_input_ood(row: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    flagged: list[str] = []
    details: dict[str, dict[str, Any]] = {}
    for feature, stats in profile.get("numeric", {}).items():
        value = row.get(feature)
        if value is None or isinstance(value, bool):
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(numeric_value):
            continue
        if numeric_value < stats["lower_bound"] or numeric_value > stats["upper_bound"]:
            flagged.append(feature)
            details[feature] = {
                "kind": "outside_training_iqr_fence",
                "value": numeric_value,
                "lower_bound": stats["lower_bound"],
                "upper_bound": stats["upper_bound"],
            }
    for feature, stats in profile.get("categorical", {}).items():
        value = row.get(feature)
        if value is not None and str(value) not in set(stats.get("categories", [])):
            flagged.append(feature)
            details[feature] = {"kind": "category_not_observed_in_training", "value": str(value)}
    return {"ood_warning": bool(flagged), "ood_features": sorted(flagged), "ood_details": details}


def _psi(expected: list[float], actual: list[float], epsilon: float = 1e-6) -> float:
    expected_array = np.asarray(expected, dtype=float)
    actual_array = np.asarray(actual, dtype=float)
    expected_share = expected_array / max(expected_array.sum(), 1.0)
    actual_share = actual_array / max(actual_array.sum(), 1.0)
    expected_share = np.clip(expected_share, epsilon, None)
    actual_share = np.clip(actual_share, epsilon, None)
    return float(np.sum((actual_share - expected_share) * np.log(actual_share / expected_share)))


def compare_feature_distributions(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    profile: dict[str, Any],
    *,
    psi_threshold: float | None = None,
    missing_rate_shift_threshold: float | None = None,
) -> dict[str, Any]:
    if reference.empty or current.empty:
        raise ValueError("Las cohortes de referencia y actual deben contener filas.")
    thresholds = profile.get("thresholds", {})
    psi_limit = float(psi_threshold if psi_threshold is not None else thresholds.get("psi", 0.2))
    missing_limit = float(
        missing_rate_shift_threshold
        if missing_rate_shift_threshold is not None
        else thresholds.get("missing_rate_shift", 0.1)
    )
    features: dict[str, dict[str, Any]] = {}
    alerts: list[str] = []

    for feature, stats in profile.get("numeric", {}).items():
        reference_values = pd.to_numeric(reference.get(feature, pd.Series(index=reference.index, dtype="float64")), errors="coerce")
        current_values = pd.to_numeric(current.get(feature, pd.Series(index=current.index, dtype="float64")), errors="coerce")
        edges = sorted({
            float("-inf"), stats["q1"], stats["median"], stats["q3"], float("inf")
        })
        reference_counts = np.histogram(reference_values.dropna(), bins=edges)[0].tolist()
        current_counts = np.histogram(current_values.dropna(), bins=edges)[0].tolist()
        psi = _psi(reference_counts, current_counts)
        missing_shift = abs(float(current_values.isna().mean()) - float(reference_values.isna().mean()))
        feature_alerts = []
        if psi >= psi_limit:
            feature_alerts.append("psi")
        if missing_shift >= missing_limit:
            feature_alerts.append("missing_rate_shift")
        features[feature] = {
            "kind": "numeric",
            "psi": psi,
            "reference_missing_rate": float(reference_values.isna().mean()),
            "current_missing_rate": float(current_values.isna().mean()),
            "missing_rate_shift": missing_shift,
            "alerts": feature_alerts,
        }
        if feature_alerts:
            alerts.append(feature)

    for feature, stats in profile.get("categorical", {}).items():
        reference_values = reference.get(feature, pd.Series(index=reference.index, dtype="object"))
        current_values = current.get(feature, pd.Series(index=current.index, dtype="object"))
        categories = sorted(set(stats.get("categories", [])) | set(reference_values.dropna().astype(str)) | set(current_values.dropna().astype(str)) | {"__MISSING__"})
        reference_counts = Counter(reference_values.fillna("__MISSING__").astype(str))
        current_counts = Counter(current_values.fillna("__MISSING__").astype(str))
        psi = _psi([reference_counts[key] for key in categories], [current_counts[key] for key in categories])
        missing_shift = abs(float(current_values.isna().mean()) - float(reference_values.isna().mean()))
        feature_alerts = []
        if psi >= psi_limit:
            feature_alerts.append("category_distribution_shift")
        if missing_shift >= missing_limit:
            feature_alerts.append("missing_rate_shift")
        features[feature] = {
            "kind": "categorical",
            "psi": psi,
            "reference_missing_rate": float(reference_values.isna().mean()),
            "current_missing_rate": float(current_values.isna().mean()),
            "missing_rate_shift": missing_shift,
            "alerts": feature_alerts,
        }
        if feature_alerts:
            alerts.append(feature)

    return {
        "status": "complete",
        "reference_split": profile.get("reference_split", "unknown"),
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "thresholds": {"psi": psi_limit, "missing_rate_shift": missing_limit},
        "alert": bool(alerts),
        "alert_features": sorted(set(alerts)),
        "features": features,
        "interpretation": "Input-distribution warning only; it does not change model predictions or trigger retraining.",
    }