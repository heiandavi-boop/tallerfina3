from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


TRUE_PROGRESS_BOUNDARY_EPSILON = 1e-9


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planned_duration_weeks: float | None = Field(None, ge=1, le=520)
    planned_budget: float | None = Field(None, ge=1)
    baseline_scope_units: float | None = Field(None, ge=1)

    sector: Literal["banking", "healthcare", "manufacturing", "research", "technology", "telecom"] | None = None
    project_type: Literal["construction", "healthcare", "it", "manufacturing", "marketing", "r&d"] | None = None
    methodology: Literal["agile", "hybrid", "kanban", "scrum", "waterfall"] | None = None
    complexity: Literal["low", "medium", "high", "very_high"] | None = None
    criticality: Literal["low", "medium", "high", "mission_critical"] | None = None

    true_progress: float | None = Field(None, ge=0, le=1)
    spi: float | None = Field(None, ge=0.1, le=2.0)
    cpi: float | None = Field(None, ge=0.1, le=2.0)
    team_utilization: float | None = Field(None, ge=0, le=1.5)
    team_capacity_ratio: float | None = Field(None, ge=0, le=2.0)
    average_productivity: float | None = Field(None, ge=0, le=1.5)
    defect_rate: float | None = Field(None, ge=0, le=0.5)
    rework_ratio: float | None = Field(None, ge=0, le=0.5)
    scope_growth_ratio: float | None = Field(None, ge=0, le=1.0)
    dependency_delay_days: float | None = Field(None, ge=0, le=365)
    normalized_risk_exposure: float | None = Field(None, ge=0, le=1)
    governance_health_score: float | None = Field(None, ge=0, le=1)

    # Operational signals used only by Team Health. They are intentionally not
    # forced into the predictive model until paired historical outcomes exist.
    team_stability: float | None = Field(None, ge=0, le=1)
    collaboration_level: float | None = Field(None, ge=0, le=1)

    @field_validator("true_progress", mode="before")
    @classmethod
    def normalize_true_progress_float_noise(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return value
        numeric = float(value)
        if -TRUE_PROGRESS_BOUNDARY_EPSILON <= numeric < 0:
            return 0.0
        if 1 < numeric <= 1 + TRUE_PROGRESS_BOUNDARY_EPSILON:
            return 1.0
        return value


class WhatIfRequest(BaseModel):
    baseline: ProjectInput
    scenario: ProjectInput


class CsvRowResponse(BaseModel):
    row_number: int
    input: dict[str, Any]
    prediction: dict[str, Any] | None = None
    error: str | None = None
