"""Regression tests for the optional two-model Ollama selector.

These checks do not contact Ollama; real local inference remains a separate smoke test.
"""
import importlib

from fastapi.testclient import TestClient

from prunin_ai.api.catalog import PRESETS
from prunin_ai.api import recommendations


def test_model_catalog_marks_installed_models(monkeypatch):
    api = importlib.import_module("prunin_ai.api.app")
    monkeypatch.setattr(api, "check_ollama_status", lambda: {"model": "qwen3:8b", "enabled": True})
    monkeypatch.setattr(api, "installed_ollama_models", lambda: {"qwen3:8b", "gpt-oss:20b"})
    response = TestClient(api.app).get("/api/genai-models")
    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "qwen3:8b"
    assert {item["id"] for item in body["models"]} == {"qwen3:8b", "gpt-oss:20b"}
    assert all(item["installed"] for item in body["models"])


def test_predict_passes_selected_model_to_recommendations(monkeypatch):
    api = importlib.import_module("prunin_ai.api.app")
    received = {}

    def fake_build(row, pred, drivers, *, provider=None, model=None):
        received.update(provider=provider, model=model)
        return recommendations.recommendations_not_requested()

    monkeypatch.setattr(api, "build_recommendations", fake_build)
    response = TestClient(api.app).post(
        "/api/predict",
        json=PRESETS["at_risk"],
        headers={"X-PRUNIN-Provider": "ollama", "X-PRUNIN-Model": "gpt-oss:20b"},
    )
    assert response.status_code == 200
    assert received == {"provider": "ollama", "model": "gpt-oss:20b"}


def test_unknown_model_is_rejected():
    api = importlib.import_module("prunin_ai.api.app")
    response = TestClient(api.app).post(
        "/api/predict",
        json=PRESETS["at_risk"],
        headers={"X-PRUNIN-Model": "untrusted:latest"},
    )
    assert response.status_code == 422


def test_gpt_oss_uses_low_reasoning_and_qwen_disables_it(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    seen = []

    def fake_generate(pred, drivers, *, row, model, **kwargs):
        seen.append((model, kwargs.get("think")))
        return {"ok": False, "error": "invalid_json", "failure_code": "invalid_json",
                "failure_detail": "Simulated invalid output", "latency_ms": 1.0}

    monkeypatch.setattr(recommendations, "generate_ollama_grounded", fake_generate)
    for model in ("qwen3:8b", "gpt-oss:20b"):
        fallback = recommendations.ollama_recommendations(
            PRESETS["at_risk"],
            {"health": "at_risk", "delay_days": 20, "cost_overrun_ratio": 0.1},
            [],
            model=model,
        )
        assert fallback["engine"] == "grounded_fallback"
    assert seen == [("qwen3:8b", False), ("gpt-oss:20b", "low")]
