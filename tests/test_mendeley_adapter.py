import pandas as pd
import numpy as np
import pytest
from prunin_ai.data.adapters.mendeley_evm import prepare_mendeley
from prunin_ai.data.adapters.mendeley_evm import _read_table


def test_mendeley_adapter_preserves_unknown_features_as_nan(tmp_path):
    static = pd.DataFrame({
        "Project ID": ["P1"],
        "Planned Duration Months": [2],
        "Budget": [1000.0],
        "Project Type": ["software"],
        "Methodology": ["agile"],
        "Project Complexity": ["medium"],
        "Governance Maturity": [0.8],
        "Risk History Score": [0.2],
    })
    ts = pd.DataFrame({
        "Project ID": ["P1", "P1"],
        "Month": [1, 2],
        "PV": [300.0, 600.0],
        "EV": [250.0, 500.0],
        "AC": [270.0, 550.0],
    })
    summary = pd.DataFrame({
        "Project ID": ["P1"],
        "Delay Weeks": [2.0],
        "Cost Overrun Pct": [10.0],
    })
    sp, tp, op = tmp_path/"static.csv", tmp_path/"ts.csv", tmp_path/"out.csv"
    static.to_csv(sp, index=False); ts.to_csv(tp, index=False); summary.to_csv(op, index=False)
    out = prepare_mendeley(sp, tp, op)

    assert len(out) == 2
    assert np.isclose(out["planned_duration_weeks"].iloc[0], 2 * 4.345)
    assert np.isclose(out["delay_days"].iloc[0], 14.0)
    assert np.isclose(out["cost_overrun_ratio"].iloc[0], 0.10)
    assert np.isclose(out["true_progress"].iloc[-1], 0.50)
    assert out["team_utilization"].isna().all()
    assert out["rework_ratio"].isna().all()
    assert out["team_health_index"].isna().all()
    assert out["is_synthetic"].all()


def test_mendeley_adapter_reads_csv_rows_wrapped_in_xlsx_cells(tmp_path):
    from openpyxl import Workbook

    path = tmp_path / "simulated.csv.xlsx"
    workbook = Workbook()
    workbook.active.append(["Project_ID,Month,PV,EV,AC"])
    workbook.active.append(["P1,1,100,90,110"])
    workbook.save(path)

    result = _read_table(path)

    assert list(result.columns) == ["Project_ID", "Month", "PV", "EV", "AC"]
    assert result.iloc[0].to_dict() == {"Project_ID": "P1", "Month": "1", "PV": "100", "EV": "90", "AC": "110"}


def test_mendeley_v2_maps_published_duration_budget_and_outcomes(tmp_path):
    static = pd.DataFrame({
        "Project_ID": ["P1"], "Project_Type": ["Construction"],
        "Project_Budget_USD": [1000.0], "Estimated_Timeline_Months": [10],
        "Methodology_Used": ["Waterfall"],
    })
    timeseries = pd.DataFrame({
        "Project_ID": ["P1"], "Month": [1], "PV": [100.0], "EV": [90.0], "AC": [110.0],
        "Planned_Budget": [1000.0],
    })
    summary = pd.DataFrame({
        "Project_ID": ["P1"], "Estimated_Timeline_Months": [10],
        "Actual_Duration_Months": [12], "Planned_Budget": [1000.0],
        "Actual_Cost": [1150.0], "Schedule_Delay": [2], "Cost_Overrun": [150.0],
    })
    paths = [tmp_path / "static.csv", tmp_path / "timeseries.xlsx", tmp_path / "summary.xlsx"]
    static.to_csv(paths[0], index=False)
    timeseries.to_excel(paths[1], index=False)
    summary.to_excel(paths[2], index=False)

    result = prepare_mendeley(*paths)

    assert result.loc[0, "planned_duration_weeks"] == pytest.approx(43.45)
    assert result.loc[0, "planned_budget"] == pytest.approx(1000.0)
    assert result.loc[0, "methodology"] == "waterfall"
    assert result.loc[0, "delay_days"] == pytest.approx(60.875)
    assert result.loc[0, "cost_overrun_ratio"] == pytest.approx(0.15)
