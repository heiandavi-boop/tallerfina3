from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .catalog import FIELD_MAP
from .schema import ProjectInput


@lru_cache(maxsize=1)
def load_operational_policy() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "configs" / "operational_signals.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evaluate_operational_signals(row: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy if policy is not None else load_operational_policy()
    signals = []
    available = []
    missing = []
    for feature, rule in policy["rules"].items():
        value = row.get(feature)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            missing.append(feature)
            continue
        try:
            ProjectInput.model_validate({feature: value})
        except ValidationError:
            missing.append(feature)
            continue
        available.append(feature)
        threshold = float(rule["threshold"])
        triggered = value < threshold if rule["operator"] == "below" else value > threshold
        if not triggered:
            continue
        relation = "inferior" if rule["operator"] == "below" else "superior"
        signals.append({
            "feature": feature,
            "source": "observed_operational_signal",
            "label": FIELD_MAP[feature]["label"],
            "value": value,
            "unit": rule["unit"],
            "priority": rule["priority"],
            "rule": {**rule, "version": policy["version"], "heuristic": True},
            "reason": f"{FIELD_MAP[feature]['label']} observado es {relation} al criterio heurístico de revisión; no es una predicción ni demuestra una causa.",
        })
    return {"policy_version": policy["version"], "signals": signals, "available": available, "missing": missing}


def build_evidence_context(row: dict[str, Any], prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any]:
    operational = evaluate_operational_signals(row)
    model_drivers = [{**driver, "source": "model_driver", "unit": FIELD_MAP.get(driver.get("feature"), {}).get("unit", "index")}
                     for driver in drivers if driver.get("feature")]
    indicators = []
    team = prediction.get("team_health") or {}
    if (isinstance(team.get("score"), (int, float)) and math.isfinite(team["score"])
            and team.get("component_count", 0) >= 3 and team.get("weight_coverage", 0) >= 0.5):
        indicators.append({
            "feature": "team_health", "source": "heuristic_indicator", "label": "Condición operativa del equipo",
            "value": team["score"], "unit": "normalized_index", "level": team.get("level"),
            "priority": "media", "actionable": team.get("level") in {"attention", "critical"},
            "reason": "El indicador heurístico del equipo requiere revisar sus componentes; no es un modelo supervisado ni mide salud psicológica.",
        })
    actionable = operational["signals"] + [driver for driver in model_drivers if driver.get("direction") == "increases_risk" and prediction.get("health") != "healthy"] + [item for item in indicators if item["actionable"]]
    status = "priority_signals" if actionable else "no_priority_signals" if prediction.get("health") == "healthy" and {"spi", "cpi"} <= set(operational["available"]) and len(operational["available"]) >= 5 else "insufficient_evidence"
    return {
        "contract_version": "evidence-v2", "status": status,
        "prediction": {key: prediction.get(key) for key in ("health", "delay_days", "cost_overrun_ratio", "health_probabilities", "fused_risk_score", "fused_health", "final_status")},
        "model_drivers": model_drivers, "operational_signals": operational["signals"], "heuristic_indicators": indicators,
        "operational_assessment": {key: value for key, value in operational.items() if key != "signals"},
        "actionable_evidence": actionable,
        "limitations": ["Sensibilidad local no causal; ausencia de drivers positivos no descarta desviaciones.",
                         "Reglas operativas heurísticas no calibradas; requieren indicadores y líneas base comparables.",
                         "La lectura operativa puede diferir de Health sin modificar la predicción ML.",
                         "Health healthy sin desviaciones no exige corrección por sensibilidad aislada; los drivers se conservan como contexto.",
                         "Los valores faltantes no se imputan para generar señales operativas."],
    }