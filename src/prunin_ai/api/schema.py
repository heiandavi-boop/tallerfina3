from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planned_duration_weeks: float | None = Field(None, ge=1, le=520)
    planned_budget: float | None = Field(None, ge=1)
    baseline_scope_units: float | None = Field(None, ge=1)

    sector: Literal["banking", "healthcare", "manufacturing", "research", "technology", "telecom"] | None = None
    project_type: Literal["data_ai", "infrastructure", "process", "research", "software", "transformation"] | None = None
    methodology: Literal["hybrid", "kanban", "scrum", "stage_gate", "waterfall"] | None = None
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


class WhatIfRequest(BaseModel):
    baseline: ProjectInput
    scenario: ProjectInput


class CsvRowResponse(BaseModel):
    row_number: int
    input: dict[str, Any]
    prediction: dict[str, Any] | None = None
    error: str | None = None
