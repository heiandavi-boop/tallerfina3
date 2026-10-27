from __future__ import annotations

import importlib
import json

from fastapi.testclient import TestClient

from prunin_ai.api.app import app
from prunin_ai.training.empirical_training_service import split_project_indices


app_module = importlib.import_module("prunin_ai.api.app")
client = TestClient(app)


def model_records():
    return [
        {"id": "academic", "version": "0.9.0-academic", "status": "ready", "source_type": "synthetic", "metrics": {}},
        {"id": "empirical", "version": "1.0.0-empirical", "status": "ready", "source_type": "real", "metrics": {}},
    ]


def empirical_prediction(data, runtime):
    return (
        {
            "health": None,
            "final_status": None,
            "delay_days_raw": 3.0,
            "delay_days": 3.0,
            "cost_overrun_ratio": -0.02,
            "input_quality": {"complete": True, "coverage": 1.0, "missing_count": 0},
        },
        {
            "version": "1.0.0-empirical",
            "mode": "empirical_real_data",
            "dataset_source": "DSLIB / PSLIB v3.4",
            "dataset_type": "empirical_real",
            "model_type": "median baseline",
            "trained_features": ["planned_duration_days", "planned_budget_bac"],
            "health_available": False,
        },
    )


def test_project_group_split_is_reproducible_and_disjoint():
    project_ids = [f"project-{index}" for index in range(120)]
    first = split_project_indices(project_ids, seed=42)
    second = split_project_indices(project_ids, seed=42)
    assert first == second
    partitions = {key: {project_ids[index] for index in indexes} for key, indexes in first.items()}
    assert not partitions["train"] & partitions["validation"]
    assert not partitions["train"] & partitions["test"]
    assert not partitions["validation"] & partitions["test"]


def test_empirical_prediction_keeps_health_unavailable(monkeypatch):
    monkeypatch.setattr(app_module, "predict_empirical", empirical_prediction)
    payload = client.get("/api/schema").json()["presets"]["at_risk"]

    response = client.post("/api/predict?model_id=empirical", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["model"]["id"] == "empirical"
    assert body["prediction"]["health"] is None
    assert body["prediction"]["delay_days_raw"] == 3.0
    assert body["prediction"]["cost_overrun_ratio"] == -0.02
    assert body["recommendations"]["engine"] == "not_available_for_empirical_targets"


def test_side_by_side_prediction_reports_domain_caveat(monkeypatch):
    monkeypatch.setattr(app_module, "predict_empirical", empirical_prediction)
    payload = client.get("/api/schema").json()["presets"]["at_risk"]

    response = client.post("/api/compare-models", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["academic"]["model"]["id"] == "academic"
    assert body["empirical"]["model"]["id"] == "empirical"
    assert body["comparison"]["head_to_head"] is False
    assert body["comparison"]["health_comparison"] == "not_available"
    assert "no indican cuál" in body["comparison"]["note"]


def test_manual_selection_returns_registry_response(monkeypatch):
    monkeypatch.setattr(app_module, "select_model", lambda model_id, runtime: {"active_model": model_id, "version": "1.0.0-empirical"})

    response = client.post("/api/models/select", json={"model_id": "empirical"})

    assert response.status_code == 200
    assert response.json()["active_model"] == "empirical"


def test_empirical_csv_requires_canonical_features(monkeypatch):
    monkeypatch.setattr(app_module, "model_records", lambda runtime: model_records())
    payload = b"planned_duration_weeks\n12\n"

    response = client.post("/api/predict-csv?model_id=empirical", files={"file": ("input.csv", payload, "text/csv")})

    assert response.status_code == 422
    assert "planned_budget" in response.json()["detail"]


def test_empirical_csv_uses_selected_model_for_valid_rows(monkeypatch):
    monkeypatch.setattr(app_module, "model_records", lambda runtime: model_records())
    calls = []

    def fake_prediction(data, *, include_recommendations=True, model_id=None):
        calls.append((data, model_id))
        return {"prediction": {"delay_days_raw": 3.0}, "model": {"id": model_id, "version": "1.0.1-empirical"}}

    monkeypatch.setattr(app_module, "run_prediction", fake_prediction)
    csv = b"planned_duration_weeks,planned_budget\n52,2500000000\n"

    response = client.post("/api/predict-csv?model_id=empirical", files={"file": ("input.csv", csv, "text/csv")})

    assert response.status_code == 200
    assert response.json()["model"]["id"] == "empirical"
    assert response.json()["rows"][0]["prediction"]["model"]["id"] == "empirical"
    assert calls[0][1] == "empirical"


def test_training_endpoint_is_gated_and_rejects_duplicate_jobs(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_TRAINING_UI", "0")
    assert client.post("/api/training/empirical").status_code == 403

    monkeypatch.setenv("PRUNIN_ENABLE_TRAINING_UI", "1")
    submitted = []
    monkeypatch.setattr(app_module.training_executor, "submit", lambda function, job_id: submitted.append(job_id))
    with app_module.training_jobs_lock:
        app_module.training_jobs.clear()
    try:
        first = client.post("/api/training/empirical")
        second = client.post("/api/training/empirical")
        assert first.status_code == 200
        assert first.json()["status"] == "queued"
        assert second.status_code == 409
        assert submitted == [first.json()["job_id"]]
        status = client.get(f"/api/training/{first.json()['job_id']}")
        logs = client.get(f"/api/training/{first.json()['job_id']}/logs")
        assert status.json()["status"] == "queued"
        assert logs.json()["events"][0]["status"] == "queued"
    finally:
        with app_module.training_jobs_lock:
            app_module.training_jobs.clear()