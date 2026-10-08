from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import yaml

from ..inference.brain import PruninAcademicBrain
from .catalog import FIELD_CATALOG, FIELD_MAP, PRESETS


ROOT = Path(__file__).resolve().parents[3]


def choose_artifact_dir() -> tuple[Path, str]:
    explicit = os.getenv("PRUNIN_ARTIFACT_DIR")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"PRUNIN_ARTIFACT_DIR no existe: {p}")
        return p, "configured"
    academic = ROOT / "artifacts" / "0.9.0-academic"
    if academic.exists() and (academic / "health.joblib").exists():
        return academic, "academic"
    demo = ROOT / "artifacts" / "demo-0.1.0"
    if demo.exists():
        return demo, "synthetic_demo"
    raise FileNotFoundError("No se encontró un directorio de artefactos utilizable.")


def load_config(artifact_dir: Path) -> dict:
    artifact_cfg = artifact_dir / "training_config_resolved.yaml"
    cfg_path = artifact_cfg if artifact_cfg.exists() else ROOT / "configs" / "training.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


class ModelRuntime:
    def __init__(self):
        self.artifact_dir, self.mode = choose_artifact_dir()
        self.config = load_config(self.artifact_dir)
        self.brain = PruninAcademicBrain(self.artifact_dir, self.config)
        self.manifest = self._load_json("feature_manifest.json", {})
        self.metrics = self._load_json("metrics.json", {})

    def _load_json(self, name: str, default: Any):
        p = self.artifact_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    @property
    def version(self) -> str:
        return self.artifact_dir.name

    def aligned_input(self, row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        data = dict(row)
        required = list(self.manifest.get("numeric_features", [])) + list(self.manifest.get("categorical_features", []))
        missing = []
        for name in required:
            if name not in data or data[name] is None or (isinstance(data[name], float) and np.isnan(data[name])):
                data[name] = np.nan
                missing.append(name)
        return data, missing

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        aligned, missing = self.aligned_input(row)
        trained_count = len(self.manifest.get("numeric_features", [])) + len(self.manifest.get("categorical_features", []))
        coverage = 1.0 - (len(missing) / max(trained_count, 1))
        minimum_coverage = float(os.getenv("PRUNIN_MIN_FEATURE_COVERAGE", "0.60"))
        if coverage < minimum_coverage:
            raise ValueError(f"Cobertura insuficiente de features: {coverage:.0%}. Se requiere al menos {minimum_coverage:.0%}.")
        result = self.brain.predict(aligned)
        result["input_quality"] = {
            "trained_feature_count": trained_count,
            "coverage": round(coverage, 4),
            "minimum_coverage": minimum_coverage,
            "imputation_policy": "numeric=training_median; categorical=training_mode",
            "missing_trained_features": missing,
            "missing_count": len(missing),
            "complete": not missing,
        }
        return result

    def health_risk_score(self, prediction: dict[str, Any]) -> float:
        if prediction.get("fused_risk_score") is not None:
            return float(prediction["fused_risk_score"])
        p = prediction.get("health_core_probabilities") or {}
        if p:
            return float(p.get("critical", 0.0) + 0.5 * p.get("at_risk", 0.0))
        label = str(prediction.get("health", "at_risk"))
        return {"healthy": 0.15, "at_risk": 0.5, "critical": 0.85}.get(label, 0.5)

    def local_drivers(self, row: dict[str, Any], baseline_prediction: dict[str, Any], limit: int = 7) -> list[dict[str, Any]]:
        baseline_risk = self.health_risk_score(baseline_prediction)
        drivers = []
        trained = set(self.manifest.get("numeric_features", []))
        for spec in FIELD_CATALOG:
            name = spec["name"]
            if name not in trained or spec.get("type") not in {"number", "range"}:
                continue
            current = row.get(name)
            reference = spec.get("reference")
            if current is None or reference is None:
                continue
            probe = dict(row)
            probe[name] = reference
            try:
                p = self.predict(probe)
                reference_risk = self.health_risk_score(p)
            except Exception:
                continue
            impact = baseline_risk - reference_risk
            if abs(impact) < 0.003:
                continue
            drivers.append({
                "feature": name,
                "label": spec["label"],
                "value": current,
                "reference": reference,
                "risk_impact": round(float(impact), 4),
                "direction": "increases_risk" if impact > 0 else "reduces_risk",
            })
        drivers.sort(key=lambda x: abs(x["risk_impact"]), reverse=True)
        return drivers[:limit]

    def metadata(self) -> dict[str, Any]:
        dataset_source = self.manifest.get("dataset_source", "synthetic_demo")
        dataset_type = self.manifest.get("dataset_type", "synthetic")
        return {
            "version": self.version,
            "mode": self.mode,
            "artifact_dir": str(self.artifact_dir.relative_to(ROOT)) if self.artifact_dir.is_relative_to(ROOT) else str(self.artifact_dir),
            "models_loaded": sorted(self.brain.models.keys()),
            "manifest": self.manifest,
            "metrics": self.metrics,
            "dataset_source": dataset_source,
            "dataset_type": dataset_type,
            "model_type": self.manifest.get("model_type", "LightGBM"),
            "trained_features": list(self.manifest.get("numeric_features", [])) + list(self.manifest.get("categorical_features", [])),
            "final_status_mode": self.manifest.get("final_status_mode", "independent_model"),
            "minimum_feature_coverage": float(os.getenv("PRUNIN_MIN_FEATURE_COVERAGE", "0.60")),
        }
