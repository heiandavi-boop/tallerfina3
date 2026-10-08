from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Mapping, Any


@dataclass(frozen=True)
class TeamHealthResult:
    score: float | None
    level: str
    weight_coverage: float
    component_count: int
    components: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


def _number(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def utilization_score(v: float) -> float:
    # Rango sostenible: hasta 85 %. La sobreasignación se penaliza progresivamente.
    if v <= 0.85:
        return 1.0
    if v <= 1.0:
        return 1.0 - ((v - 0.85) / 0.15) * 0.5
    return _clip01(0.5 - (v - 1.0) * 1.25)


def capacity_score(v: float) -> float:
    # ratio = capacidad disponible / demanda. 1 o superior cubre la demanda.
    return _clip01(v)


def productivity_score(v: float) -> float:
    # 1.0 representa productividad de referencia.
    return _clip01(v)


def rework_score(v: float) -> float:
    return 1.0 - _clip01(v / 0.25)


def defect_score(v: float) -> float:
    return 1.0 - _clip01(v / 0.15)


def direct_score(v: float) -> float:
    return _clip01(v)


SCORERS = {
    "team_utilization": utilization_score,
    "team_capacity_ratio": capacity_score,
    "average_productivity": productivity_score,
    "rework_ratio": rework_score,
    "defect_rate": defect_score,
    "team_stability": direct_score,
    "collaboration_level": direct_score,
}


def compute_team_health(values: Mapping[str, Any], config: Mapping[str, Any]) -> TeamHealthResult:
    weights = dict(config["weights"])
    thresholds = config["thresholds"]
    minimum_components = int(config.get("minimum_components", 3))
    minimum_coverage = float(config.get("minimum_weight_coverage", 0.5))

    component_scores: dict[str, float] = {}
    used_weight = 0.0
    weighted_sum = 0.0

    for name, weight in weights.items():
        raw = _number(values.get(name))
        if raw is None:
            continue
        score = SCORERS[name](raw)
        component_scores[name] = score
        weighted_sum += score * float(weight)
        used_weight += float(weight)

    coverage = used_weight / max(sum(float(x) for x in weights.values()), 1e-12)
    count = len(component_scores)

    if count < minimum_components or coverage < minimum_coverage or used_weight <= 0:
        return TeamHealthResult(None, "insufficient_data", coverage, count, component_scores)

    score = weighted_sum / used_weight
    if score >= float(thresholds["healthy"]):
        level = "healthy"
    elif score >= float(thresholds["attention"]):
        level = "attention"
    else:
        level = "critical"

    return TeamHealthResult(round(score, 6), level, coverage, count, component_scores)
