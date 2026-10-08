STATIC_NUMERIC_FEATURES = [
    "planned_duration_weeks",
    "planned_budget",
    "baseline_scope_units",
]

CATEGORICAL_FEATURES = [
    "sector",
    "project_type",
    "methodology",
    "complexity",
    "criticality",
]

# V9 académico: no reported_progress, critical_path_delay_days ni team_morale.
CORE_TEMPORAL_FEATURES = [
    "true_progress",
    "spi",
    "cpi",
    "team_utilization",
    "team_capacity_ratio",
    "average_productivity",
    "defect_rate",
    "rework_ratio",
    "scope_growth_ratio",
    "dependency_delay_days",
    "normalized_risk_exposure",
    "governance_health_score",
]

DERIVED_OPERATIONAL_FEATURES = ["team_health_index"]

ALL_MODEL_CANDIDATES = STATIC_NUMERIC_FEATURES + CORE_TEMPORAL_FEATURES

TARGETS = {
    "health": "classification",
    "final_status": "classification",
    "delay_days": "regression",
    "cost_overrun_ratio": "regression",
}

HEALTH_LABELS = ["healthy", "at_risk", "critical"]
STATUS_LABELS = ["successful", "challenged", "critical", "incomplete"]
