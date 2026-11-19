"""Local versioned model registry and gated retraining pipeline.

The academic version (0.9.0-academic) is registered as frozen and can never be
replaced by this pipeline. Retraining is blocked by default and only produces
candidates in an isolated directory; promotion requires explicit approval.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, mean_absolute_error

from ..targets import add_targets
from ..training.core import _split_groups, train_core
from .drift import build_reference_profile, compare_feature_distributions

FROZEN_VERSIONS = frozenset({"0.9.0-academic"})
REGISTRY_SCHEMA_VERSION = 1
GATED_TARGETS = {
    "health": ("macro_f1", "higher"),
    "delay_days": ("mae", "lower"),
    "cost_overrun_ratio": ("mae", "lower"),
}


class RetrainingBlocked(RuntimeError):
    """Raised when a retraining precondition is not satisfied."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelRegistry:
    """JSON-backed registry; every mutation is appended to an audit log."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.is_file():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"schema_version": REGISTRY_SCHEMA_VERSION, "production": None, "models": [], "events": []}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def get(self, version: str) -> dict[str, Any] | None:
        return next((m for m in self.data["models"] if m["version"] == version), None)

    def _event(self, action: str, version: str, **details: Any) -> None:
        self.data["events"].append({"timestamp": _now(), "action": action, "version": version, **details})

    def register(self, entry: dict[str, Any]) -> dict[str, Any]:
        required = {"name", "version", "algorithm", "dataset", "status", "metrics"}
        missing = required - set(entry)
        if missing:
            raise ValueError(f"Entrada de registro incompleta: {sorted(missing)}")
        existing = self.get(entry["version"])
        if existing is not None:
            if existing["version"] in FROZEN_VERSIONS:
                raise PermissionError(f"La versión {entry['version']} está congelada y no puede sobrescribirse.")
            raise ValueError(f"La versión {entry['version']} ya está registrada.")
        record = {"registered_at": _now(), "approval": None, "parent_version": None, **entry}
        self.data["models"].append(record)
        self._event("register", record["version"], status=record["status"])
        return record

    def approve(self, version: str, approver: str, note: str = "") -> dict[str, Any]:
        record = self.get(version)
        if record is None:
            raise KeyError(version)
        if record["status"] != "candidate_passed_gate":
            raise RetrainingBlocked(f"Solo se aprueban candidatos que pasaron el gate (estado actual: {record['status']}).")
        if not approver.strip():
            raise RetrainingBlocked("La aprobación requiere un responsable identificado.")
        record["approval"] = {"approver": approver, "note": note, "approved_at": _now()}
        record["status"] = "approved"
        self._event("approve", version, approver=approver)
        return record

    def promote(self, version: str) -> dict[str, Any]:
        record = self.get(version)
        if record is None:
            raise KeyError(version)
        if record["status"] != "approved":
            raise RetrainingBlocked("La promoción requiere aprobación humana previa.")
        previous = self.data.get("production")
        record["status"] = "production"
        record["previous_production"] = previous
        if previous and (prev := self.get(previous)) and prev["version"] not in FROZEN_VERSIONS:
            prev["status"] = "archived"
        self.data["production"] = version
        self._event("promote", version, previous=previous)
        return record

    def rollback(self) -> str:
        current = self.data.get("production")
        record = self.get(current) if current else None
        previous = record.get("previous_production") if record else None
        if not previous:
            raise RetrainingBlocked("No existe versión anterior para rollback.")
        record["status"] = "rolled_back"
        prev = self.get(previous)
        if prev is not None and prev["version"] not in FROZEN_VERSIONS:
            prev["status"] = "production"
        self.data["production"] = previous
        self._event("rollback", previous, from_version=current)
        return previous


def _metric(target: str, y_true: pd.Series, y_pred: np.ndarray) -> float:
    if GATED_TARGETS[target][0] == "macro_f1":
        return float(f1_score(y_true.astype(str), np.asarray(y_pred).astype(str), average="macro", zero_division=0))
    return float(mean_absolute_error(y_true, y_pred))


def evaluate_models(model_dir: str | Path, frame: pd.DataFrame) -> dict[str, float]:
    results: dict[str, float] = {}
    for target in GATED_TARGETS:
        path = Path(model_dir) / f"{target}.joblib"
        rows = frame.dropna(subset=[target])
        if not path.is_file() or rows.empty:
            continue
        pipe = joblib.load(path)
        columns = list(getattr(pipe, "feature_names_in_", rows.columns))
        results[target] = _metric(target, rows[target], pipe.predict(rows.reindex(columns=columns)))
    return results


def regression_gate(
    candidate: dict[str, float], baseline: dict[str, float], tolerance: float = 0.02
) -> dict[str, Any]:
    """Blocks promotion if any gated metric degrades more than ``tolerance`` (relative)."""
    checks = {}
    for target, (metric, direction) in GATED_TARGETS.items():
        if target not in candidate or target not in baseline:
            checks[target] = {"metric": metric, "passed": False, "reason": "métrica no disponible"}
            continue
        cand, base = candidate[target], baseline[target]
        scale = max(abs(base), 1e-9)
        delta = (cand - base) / scale if direction == "higher" else (base - cand) / scale
        checks[target] = {
            "metric": metric, "direction": direction, "candidate": cand, "baseline": base,
            "relative_improvement": delta, "passed": bool(delta >= -tolerance),
        }
    return {"tolerance": tolerance, "passed": all(c["passed"] for c in checks.values()), "checks": checks}


def check_trigger(reference: pd.DataFrame, current: pd.DataFrame, numeric: list[str], categorical: list[str]) -> dict[str, Any]:
    profile = build_reference_profile(reference, numeric, categorical)
    report = compare_feature_distributions(reference, current, profile)
    return {
        "drift_alert": report["alert"],
        "alert_features": report["alert_features"],
        "max_psi": max((f["psi"] for f in report["features"].values()), default=0.0),
    }


def run_retraining(
    *,
    dataset_path: str | Path,
    provenance_path: str | Path | None,
    baseline_dir: str | Path,
    baseline_version: str,
    candidate_version: str,
    candidates_root: str | Path,
    registry: ModelRegistry,
    cfg: dict[str, Any],
    authorized: bool = False,
    reference_frame: pd.DataFrame | None = None,
    require_drift: bool = False,
    tolerance: float = 0.02,
) -> dict[str, Any]:
    """Executes the gated cycle; never touches TEST for model selection."""
    if not authorized:
        raise RetrainingBlocked("Reentrenamiento bloqueado por defecto: use --authorize con un dataset aprobado.")
    if candidate_version in FROZEN_VERSIONS or candidate_version == baseline_version:
        raise RetrainingBlocked("La versión candidata no puede reutilizar una versión congelada o la baseline.")
    dataset_path = Path(dataset_path)
    if not dataset_path.is_file():
        raise RetrainingBlocked(f"Dataset inexistente: {dataset_path}")
    if provenance_path is None or not Path(provenance_path).is_file():
        raise RetrainingBlocked("Falta el registro de procedencia/autorización del dataset.")
    provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
    dataset_hash = sha256_file(dataset_path)
    if not provenance.get("authorized") or provenance.get("sha256") != dataset_hash:
        raise RetrainingBlocked("La procedencia no autoriza este dataset o el hash no coincide.")
    if provenance.get("data_source") == "mendeley_2p5sz57wh2_v2":
        raise RetrainingBlocked("El dataset académico congelado no puede usarse para reentrenar candidatos.")

    frame = add_targets(pd.read_csv(dataset_path, low_memory=False), cfg["target_rules"])
    seed = int(cfg.get("random_seed", 42))
    train_idx, val_idx, test_idx = _split_groups(frame, seed)
    split_manifest = {
        name: sorted(frame.iloc[idx]["project_id"].astype(str).unique())
        for name, idx in (("train", train_idx), ("validation", val_idx), ("test", test_idx))
    }
    validation = frame.iloc[val_idx]

    trigger = None
    if reference_frame is not None:
        numeric = [c for c in frame.select_dtypes("number").columns if c in reference_frame.columns and c not in GATED_TARGETS]
        categorical = [c for c in ("sector", "project_type", "methodology", "complexity", "criticality") if c in frame.columns]
        trigger = check_trigger(reference_frame, frame, numeric, categorical)
        if require_drift and not trigger["drift_alert"]:
            raise RetrainingBlocked("No hay drift que justifique reentrenar (require_drift activo).")

    out = Path(candidates_root) / candidate_version
    if out.exists():
        raise RetrainingBlocked(f"El directorio candidato ya existe: {out}")
    train_core(frame, cfg, out, split_manifest=split_manifest)

    candidate_metrics = evaluate_models(out, validation)
    baseline_metrics = evaluate_models(baseline_dir, validation)
    gate = regression_gate(candidate_metrics, baseline_metrics, tolerance)
    record = registry.register({
        "name": "prunin-core",
        "version": candidate_version,
        "algorithm": "LightGBM (health classifier, delay/cost regressors)",
        "dataset": {"path": dataset_path.name, "sha256": dataset_hash, "data_source": provenance.get("data_source"),
                    "rows": int(len(frame)), "projects": int(frame["project_id"].nunique())},
        "configuration": {"random_seed": seed, "model": cfg.get("model", {})},
        "metrics": {"evaluation_split": "VALIDATION (candidate split)", "candidate": candidate_metrics,
                    "baseline": baseline_metrics},
        "artifact_hashes": {p.name: sha256_file(p) for p in sorted(out.glob("*.joblib"))},
        "gate": gate,
        "trigger": trigger,
        "parent_version": baseline_version,
        "status": "candidate_passed_gate" if gate["passed"] else "rejected_regression",
    })
    return {"candidate_dir": str(out), "record": record}
