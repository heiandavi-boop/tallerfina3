import io
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from prunin_ai.api import app as app_module
from prunin_ai.api.app import app, runtime
from prunin_ai.api.catalog import PRESETS
from prunin_ai.api.schema import ProjectInput


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
PROJECT_TYPES = {"construction", "healthcare", "it", "manufacturing", "marketing", "r&d"}
METHODOLOGIES = {"agile", "hybrid", "kanban", "scrum", "waterfall"}
ACADEMIC_FEATURES = [
    "planned_duration_weeks",
    "planned_budget",
    "true_progress",
    "spi",
    "cpi",
    "project_type",
    "methodology",
]


def _active_runtime_has_academic_contract():
    return (
        runtime.manifest.get("numeric_features") == ACADEMIC_FEATURES[:5]
        and runtime.manifest.get("categorical_features") == ACADEMIC_FEATURES[5:]
    )


def _academic_result(row):
    return {
        "input": row,
        "prediction": {
            "input_quality": {
                "coverage": 1.0,
                "missing_count": 0,
                "missing_trained_features": [],
            }
        },
    }


@pytest.mark.parametrize("project_type", sorted(PROJECT_TYPES))
def test_project_input_accepts_each_mendeley_project_type(project_type):
    parsed = ProjectInput.model_validate({"project_type": project_type})
    assert parsed.project_type == project_type


def test_project_input_rejects_unknown_project_type():
    with pytest.raises(ValidationError):
        ProjectInput.model_validate({"project_type": "software"})


@pytest.mark.parametrize("methodology", sorted(METHODOLOGIES))
def test_project_input_accepts_each_mendeley_methodology(methodology):
    parsed = ProjectInput.model_validate({"methodology": methodology})
    assert parsed.methodology == methodology


def test_project_input_rejects_unknown_methodology():
    with pytest.raises(ValidationError):
        ProjectInput.model_validate({"methodology": "stage_gate"})


def test_schema_options_and_presets_match_the_academic_categorical_domain():
    schema = client.get("/api/schema").json()
    field_options = {field["name"]: set(field["options"]) for field in schema["fields"] if field["name"] in {"project_type", "methodology"}}
    assert field_options == {"project_type": PROJECT_TYPES, "methodology": METHODOLOGIES}
    for preset in PRESETS.values():
        assert preset["project_type"] in PROJECT_TYPES
        assert preset["methodology"] in METHODOLOGIES


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("project_type", "software"), ("methodology", "stage_gate")],
)
def test_predict_endpoint_rejects_categories_outside_mendeley_domain(field, invalid_value):
    payload = {**PRESETS["at_risk"], field: invalid_value}
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_academic_feature_manifest_keeps_the_same_seven_features():
    expected_numeric = ["planned_duration_weeks", "planned_budget", "true_progress", "spi", "cpi"]
    expected_categorical = ["project_type", "methodology"]
    manifest_paths = [
        ROOT / "reports" / "0.9.0-academic" / "feature_manifest.json",
        ROOT / "artifacts" / "0.9.0-academic" / "feature_manifest.json",
    ]
    for manifest_path in manifest_paths:
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["numeric_features"] == expected_numeric
            assert manifest["categorical_features"] == expected_categorical


@pytest.mark.parametrize(
    ("project_type", "methodology"),
    [("it", "agile"), ("r&d", "kanban")],
)
def test_csv_accepts_real_mendeley_categorical_values(project_type, methodology, monkeypatch):
    row = {
        "planned_duration_weeks": 52,
        "planned_budget": 2_500_000_000,
        "true_progress": 0.47,
        "spi": 0.82,
        "cpi": 0.91,
        "project_type": project_type,
        "methodology": methodology,
    }
    monkeypatch.setattr(app_module, "run_prediction", lambda data, **kwargs: _academic_result(data))
    csv_bytes = pd.DataFrame([row], columns=ACADEMIC_FEATURES).to_csv(index=False).encode()
    response = client.post("/api/predict-csv", files={"file": ("mendeley-input.csv", csv_bytes, "text/csv")})
    assert response.status_code == 200
    result = response.json()["rows"][0]
    assert result["error"] is None
    assert result["prediction"]["input"]["project_type"] == project_type
    assert result["prediction"]["input"]["methodology"] == methodology
    assert result["prediction"]["prediction"]["input_quality"]["coverage"] == 1.0
    assert result["prediction"]["prediction"]["input_quality"]["missing_count"] == 0
    assert result["prediction"]["prediction"]["input_quality"]["missing_trained_features"] == []


def test_true_progress_microscopic_float_noise_is_normalized_before_validation():
    parsed = ProjectInput.model_validate({"true_progress": 1.0000000000000002})
    assert parsed.true_progress == 1.0
    response = client.post("/api/predict", json={**PRESETS["healthy"], "true_progress": 1.0000000000000002})
    assert response.status_code == 200
    assert response.json()["input"]["true_progress"] == 1.0

    csv_row = {**PRESETS["healthy"], "true_progress": 1.0000000000000002}
    csv_bytes = pd.DataFrame([csv_row]).to_csv(index=False).encode()
    csv_response = client.post("/api/predict-csv", files={"file": ("float-noise.csv", csv_bytes, "text/csv")})
    csv_result = csv_response.json()["rows"][0]
    assert csv_result["error"] is None
    assert csv_result["prediction"]["input"]["true_progress"] == 1.0


def test_true_progress_meaningfully_outside_range_is_rejected():
    with pytest.raises(ValidationError):
        ProjectInput.model_validate({"true_progress": 1.05})
    response = client.post("/api/predict", json={**PRESETS["healthy"], "true_progress": 1.05})
    assert response.status_code == 422


def test_predict_and_csv_share_runtime_outputs_for_seven_feature_row():
    if not _active_runtime_has_academic_contract():
        pytest.skip("Runtime demo-only uses a different feature set; academic parity requires the seven-feature artifact.")
    row = {
        "planned_duration_weeks": 52,
        "planned_budget": 2_500_000_000,
        "true_progress": 0.47,
        "spi": 0.82,
        "cpi": 0.91,
        "project_type": "it",
        "methodology": "agile",
    }
    runtime_prediction = runtime.predict(row)
    api_response = client.post("/api/predict", json=row)
    assert api_response.status_code == 200
    api_body = api_response.json()
    for key in ("health", "health_probabilities", "delay_days", "cost_overrun_ratio"):
        assert api_body["prediction"][key] == runtime_prediction[key]

    csv_bytes = pd.DataFrame([row], columns=ACADEMIC_FEATURES).to_csv(index=False).encode()
    csv_response = client.post("/api/predict-csv", files={"file": ("parity.csv", csv_bytes, "text/csv")})
    csv_prediction = csv_response.json()["rows"][0]["prediction"]["prediction"]
    for key in ("health", "health_probabilities", "delay_days", "cost_overrun_ratio"):
        assert csv_prediction[key] == runtime_prediction[key]


def test_99_real_test_projects_keep_all_seven_features_when_local_data_exists():
    data_path = ROOT / "data" / "processed" / "mendeley_core.csv"
    split_path = runtime.artifact_dir / "split_manifest.json"
    if not data_path.exists() or not split_path.exists():
        pytest.skip("Mendeley source data or active artifact split manifest is not available in this environment.")
    manifest = runtime.manifest
    if not _active_runtime_has_academic_contract():
        pytest.skip("The active artifact is demo-only and does not use the academic seven-feature contract.")

    split = json.loads(split_path.read_text(encoding="utf-8"))
    source = pd.read_csv(data_path, low_memory=False)
    test_rows = source[source["project_id"].astype(str).isin(set(map(str, split["test"])))].copy()
    latest = test_rows.sort_values(["project_id", "snapshot_index"]).groupby("project_id", as_index=False).tail(1)
    sample = latest.loc[:, ACADEMIC_FEATURES].head(99)
    assert len(sample) == 99
    csv_bytes = sample.to_csv(index=False).encode()
    response = client.post("/api/predict-csv", files={"file": ("prunin_99_test_reales_7_features.csv", csv_bytes, "text/csv")})
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 99
    assert all(row["error"] is None for row in rows)
    for row in rows:
        quality = row["prediction"]["prediction"]["input_quality"]
        assert quality["coverage"] == 1.0
        assert quality["missing_count"] == 0
        assert quality["missing_trained_features"] == []