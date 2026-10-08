from __future__ import annotations
import numpy as np
import pandas as pd

SECTORS = ["banking", "healthcare", "manufacturing", "research", "technology", "telecom"]
PROJECT_TYPES = ["data_ai", "infrastructure", "process", "research", "software", "transformation"]
METHODOLOGIES = ["hybrid", "kanban", "scrum", "stage_gate", "waterfall"]
COMPLEXITIES = ["low", "medium", "high", "very_high"]
CRITICALITIES = ["low", "medium", "high", "mission_critical"]


def generate_demo(projects: int = 400, snapshots: int = 8, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(projects):
        pid = f"DEMO-{p:05d}"
        duration_w = float(rng.integers(12, 160))
        budget = float(np.exp(rng.normal(16.0, 1.0)))
        scope = float(rng.integers(100, 2500))
        sector = rng.choice(SECTORS)
        project_type = rng.choice(PROJECT_TYPES)
        methodology = rng.choice(METHODOLOGIES)
        complexity = rng.choice(COMPLEXITIES, p=[0.2, 0.4, 0.3, 0.1])
        criticality = rng.choice(CRITICALITIES, p=[0.2, 0.4, 0.3, 0.1])
        latent = rng.normal(0, 0.7) + {"low":-0.4,"medium":0,"high":0.45,"very_high":0.8}[complexity]
        final_delay_ratio = max(0.0, rng.normal(0.06 + 0.07*latent, 0.06))
        final_cost = max(-0.08, rng.normal(0.04 + 0.05*latent, 0.05))
        delay_days = final_delay_ratio * duration_w * 7.0
        for s in range(1, snapshots + 1):
            cutoff = s / snapshots
            stress = latent * cutoff + rng.normal(0, 0.12)
            true_progress = np.clip(cutoff - 0.06*max(stress, 0) + rng.normal(0,0.02), 0, 1)
            spi = np.clip(1.0 - 0.10*stress + rng.normal(0,0.03), 0.45, 1.25)
            cpi = np.clip(1.0 - 0.09*stress + rng.normal(0,0.03), 0.45, 1.25)
            util = np.clip(0.82 + 0.10*stress + rng.normal(0,0.04), 0.45, 1.35)
            cap = np.clip(1.0 - 0.08*stress + rng.normal(0,0.04), 0.45, 1.2)
            prod = np.clip(0.95 - 0.10*stress + rng.normal(0,0.04), 0.35, 1.2)
            defects = np.clip(0.03 + 0.025*max(stress,0) + rng.normal(0,0.008), 0, .2)
            rework = np.clip(0.04 + 0.04*max(stress,0) + rng.normal(0,0.01), 0, .3)
            scope_growth = np.clip(0.01 + 0.02*max(stress,0) + rng.normal(0,0.005), 0, .15)
            dep_delay = max(0, rng.normal(1.2 + 2.5*max(stress,0), 1.4))
            risk = np.clip(0.10 + 0.08*max(stress,0) + rng.normal(0,0.02), 0, 1)
            governance = np.clip(0.75 - 0.12*max(stress,0) + rng.normal(0,0.04), 0, 1)
            rows.append({
                "project_id": pid,
                "source_project_id": pid,
                "snapshot_index": s,
                "cutoff_ratio": cutoff,
                "planned_duration_weeks": duration_w,
                "planned_duration_days": duration_w*7,
                "planned_budget": budget,
                "baseline_scope_units": scope,
                "sector": sector,
                "project_type": project_type,
                "methodology": methodology,
                "complexity": complexity,
                "criticality": criticality,
                "true_progress": true_progress,
                "spi": spi,
                "cpi": cpi,
                "team_utilization": util,
                "team_capacity_ratio": cap,
                "average_productivity": prod,
                "defect_rate": defects,
                "rework_ratio": rework,
                "scope_growth_ratio": scope_growth,
                "dependency_delay_days": dep_delay,
                "normalized_risk_exposure": risk,
                "governance_health_score": governance,
                "delay_days": delay_days,
                "cost_overrun_ratio": final_cost,
                "data_source": "demo_synthetic_smoke_test",
                "is_synthetic": True,
            })
    return pd.DataFrame(rows)
