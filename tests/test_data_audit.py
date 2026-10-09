import pandas as pd

from prunin_ai.data.audit import audit_dataframe


def test_audit_reports_outliers_and_normalization_policy():
    df = pd.DataFrame({
        "project_id": ["a", "b", "c", "d", "e"],
        "planned_budget": [100, 110, 105, 115, 10000],
        "true_progress": [0.1, 0.2, 0.3, 0.4, 0.5],
        "data_source": ["test"] * 5,
        "is_synthetic": [True] * 5,
    })
    report = audit_dataframe(df)
    assert report["outlier_detection"]["method"].startswith("IQR")
    assert report["outlier_detection"]["features"]["planned_budget"]["outlier_count"] == 1
    assert report["normalization_policy"]["applied"] is False
    assert "LightGBM" in report["normalization_policy"]["reason"]
