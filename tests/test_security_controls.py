"""Security and adversarial-output checks for local-only PRUNIN."""
import json

import pytest
from fastapi.testclient import TestClient

from prunin_ai.api import app as app_module
from prunin_ai.api import recommendations as ai
from prunin_ai.api.catalog import PRESETS
from prunin_ai.api.operational_signals import build_evidence_context
from prunin_ai.api.security import requires_token, resolve_cors_origins, token_matches

client = TestClient(app_module.app)
ROW = {"spi": 0.72, "cpi": 0.81, "team_utilization": 1.12, "team_capacity_ratio": 0.72}
PREDICTION = {"health": "at_risk", "delay_days": 27.0, "cost_overrun_ratio": 0.08}


def test_token_is_optional_by_default(monkeypatch):
    monkeypatch.delenv("PRUNIN_API_TOKEN", raising=False)
    assert client.get("/api/schema").status_code == 200


def test_token_protects_api_but_keeps_probes_open(monkeypatch):
    monkeypatch.setenv("PRUNIN_API_TOKEN", "secret-token")
    assert client.get("/api/ready").status_code == 200
    assert client.get("/metrics").status_code == 200
    denied = client.post("/api/predict?include_recommendations=false", json=PRESETS["at_risk"])
    assert denied.status_code == 401 and "secret-token" not in denied.text
    assert client.get("/api/schema", headers={"Authorization": "Bearer wrong"}).status_code == 401
    allowed = client.post("/api/predict?include_recommendations=false", json=PRESETS["at_risk"], headers={"Authorization": "Bearer secret-token"})
    assert allowed.status_code == 200
    assert requires_token("/api/predict") and not requires_token("/assets/app.js")
    assert not token_matches("secret-token", "secret-token")


def test_production_fails_closed_when_api_token_is_not_configured(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENV", "production")
    monkeypatch.delenv("PRUNIN_API_TOKEN", raising=False)
    denied = client.get("/api/schema")
    assert denied.status_code == 503
    assert denied.json()["code"] == "api_auth_not_configured"
    assert client.get("/api/ready").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_disabled_ollama_cannot_be_enabled_by_client(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "0")
    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: pytest.fail("Disabled transport must not be called"))
    response = client.post("/api/predict", json=PRESETS["at_risk"], headers={"X-PRUNIN-Provider": "ollama"})
    assert response.status_code == 200
    result = response.json()["recommendations"]
    assert result["selected_provider"] == "ollama"
    assert result["genai_attempted"] is False
    assert result["failure_code"] == "provider_disabled"


def test_unknown_provider_fails_closed_without_network(monkeypatch):
    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: pytest.fail("Unknown transport must not be called"))
    response = client.post("/api/predict", json=PRESETS["at_risk"], headers={"X-PRUNIN-Provider": "remote"})
    assert response.status_code == 422


def test_cors_policy_rejects_wildcard_in_production():
    assert resolve_cors_origins("local", None) == ["*"]
    assert resolve_cors_origins("production", None) == []
    assert resolve_cors_origins("production", "https://prunin.example") == ["https://prunin.example"]
    with pytest.raises(RuntimeError):
        resolve_cors_origins("production", "*")


def _validated_payload(action_text: str):
    from prunin_ai.api.operational_signals import build_evidence_context
    context = build_evidence_context(ROW, PREDICTION, [])
    fallback = ai.grounded_fallback(ROW, PREDICTION, [])
    payload = {
        "summary": fallback["summary"],
        "recommendations": [
            {
                **item,
                "evidence_source": "observed_operational_signal",
                "action": action_text,
            }
            for item in fallback["recommendations"]
        ],
    }
    validation = ai.validate_generated_payload(
        payload,
        {item["feature"] for item in context["actionable_evidence"]},
        prediction=PREDICTION, drivers=[], context=context,
    )
    return payload, validation


def test_adversarial_unsubstantiated_numbers_are_rejected():
    payload, validation = _validated_payload("Revisar el SPI real de 0.15 y recuperar 999 días.")
    assert validation["grounded"] is False
    assert validation["unsupported_numeric_claim"] is True
    assert validation["failure_code"] == "unsupported_numeric_claim"


def test_adversarial_unexpected_payload_fields_are_rejected():
    payload, validation = _validated_payload("Revisar el costo real y acordar un seguimiento.")
    payload["recommendations"][0]["unverified_sensitive_field"] = "inventado"
    context = build_evidence_context(ROW, PREDICTION, [])
    validation = ai.validate_generated_payload(
        payload, {item["feature"] for item in context["actionable_evidence"]},
        prediction=PREDICTION, drivers=[], context=context,
    )
    assert validation["grounded"] is False
    assert validation["failure_code"] == "invalid_schema"
