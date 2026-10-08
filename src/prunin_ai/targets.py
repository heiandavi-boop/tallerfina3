from __future__ import annotations
import numpy as np
import pandas as pd


def add_targets(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    out = df.copy()

    if "delay_days" not in out.columns:
        out["delay_days"] = np.nan
    if "cost_overrun_ratio" not in out.columns:
        out["cost_overrun_ratio"] = np.nan

    if "planned_duration_days" in out.columns:
        planned = pd.to_numeric(out["planned_duration_days"], errors="coerce")
    elif "planned_duration_weeks" in out.columns:
        planned = pd.to_numeric(out["planned_duration_weeks"], errors="coerce") * 7.0
    else:
        planned = pd.Series(np.nan, index=out.index)

    delay = pd.to_numeric(out["delay_days"], errors="coerce").clip(lower=0)
    delay_ratio = delay / planned.replace(0, np.nan)
    cost_ratio = pd.to_numeric(out["cost_overrun_ratio"], errors="coerce")

    h_delay = float(rules["healthy_max_delay_ratio"])
    h_cost = float(rules["healthy_max_cost_overrun_ratio"])
    r_delay = float(rules["at_risk_max_delay_ratio"])
    r_cost = float(rules["at_risk_max_cost_overrun_ratio"])

    complete = delay_ratio.notna() & cost_ratio.notna()
    healthy = complete & (delay_ratio <= h_delay) & (cost_ratio <= h_cost)
    at_risk = complete & ~healthy & (delay_ratio <= r_delay) & (cost_ratio <= r_cost)
    critical = complete & ~(healthy | at_risk)

    if "health" not in out.columns:
        out["health"] = pd.Series(pd.NA, index=out.index, dtype="object")
    out.loc[healthy, "health"] = "healthy"
    out.loc[at_risk, "health"] = "at_risk"
    out.loc[critical, "health"] = "critical"

    if "final_status" not in out.columns:
        out["final_status"] = "incomplete"
    out.loc[healthy, "final_status"] = "successful"
    out.loc[at_risk, "final_status"] = "challenged"
    out.loc[critical, "final_status"] = "critical"

    out["delay_ratio"] = delay_ratio
    return out
