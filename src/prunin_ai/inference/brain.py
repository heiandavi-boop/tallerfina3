from __future__ import annotations
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd
from ..features.team_health import compute_team_health


class PruninAcademicBrain:
    def __init__(self, artifact_dir: str | Path, config: dict):
        self.artifact_dir = Path(artifact_dir)
        self.config = config
        self.models = {}
        for name in ["health", "final_status", "delay_days", "cost_overrun_ratio"]:
            p = self.artifact_dir / f"{name}.joblib"
            if p.exists():
                self.models[name] = joblib.load(p)
        manifest_path = self.artifact_dir / "feature_manifest.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        self.feature_names = list(self.manifest.get("numeric_features", [])) + list(self.manifest.get("categorical_features", []))

    def _frame(self, row: dict) -> pd.DataFrame:
        safe = dict(row)
        for name in self.feature_names:
            safe.setdefault(name, np.nan)
        return pd.DataFrame([{name: safe.get(name, np.nan) for name in self.feature_names}])

    @staticmethod
    def _predict_one(model, x):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"X does not have valid feature names.*", category=UserWarning)
            pred = model.predict(x)[0]
        return pred.item() if hasattr(pred, "item") else pred

    @staticmethod
    def _probabilities(model, x):
        if not hasattr(model, "predict_proba"):
            return None
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"X does not have valid feature names.*", category=UserWarning)
            probs = model.predict_proba(x)[0]
        return {str(label): float(value) for label, value in zip(model.classes_, probs)}

    def predict(self, row: dict) -> dict:
        x = self._frame(row)
        result = {}
        for name, model in self.models.items():
            result[name] = self._predict_one(model, x)
            p = self._probabilities(model, x)
            if p is not None:
                result[f"{name}_probabilities"] = p
                result[f"{name}_confidence"] = max(p.values()) if p else None

        team = compute_team_health(row, self.config["team_health"])
        result["team_health"] = team.to_dict()

        p = result.get("health_probabilities") or {}
        if p and team.score is not None:
            core_risk = p.get("critical", 0.0) + 0.5 * p.get("at_risk", 0.0)
            fusion = self.config["inference_fusion"]
            combined = float(fusion["core_weight"]) * core_risk + float(fusion["team_health_weight"]) * (1.0 - team.score)
            result["health_core_probabilities"] = p
            result["fused_risk_score"] = float(combined)
            result["fused_health"] = "critical" if combined >= 0.66 else ("at_risk" if combined >= 0.33 else "healthy")
        else:
            result["fused_health"] = result.get("health")
        return result
