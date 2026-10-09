import requests

from prunin_ai.api import recommendations
from prunin_ai.api.recommendations import grounded_fallback, validate_generated_payload


PREDICTION = {"health": "at_risk", "delay_days": 27.3, "cost_overrun_ratio": 0.04}
DRIVERS = [{"feature": "cpi", "value": 0.82, "reference": 1.0, "direction": "increases_risk"}]


def test_generated_payload_accepts_only_allowlisted_evidence():
    payload = {
        "recommendations": [
            {"evidence_feature": "spi", "reason": "El cronograma muestra presión.", "action": "Revisar actividades atrasadas."}
        ],
        "summary": "Se requiere seguimiento del cronograma.",
    }
    result = validate_generated_payload(payload, {"spi", "cpi"})
    assert result["schema_valid"] is True
    assert result["evidence_features_valid"] is True
    assert result["unsupported_numeric_claim"] is False
    assert result["grounded"] is True


def test_generated_payload_rejects_unknown_evidence_and_new_numbers():
    payload = {
        "recommendations": [
            {"evidence_feature": "scope_growth_ratio", "reason": "El riesgo subió 20 por ciento.", "action": "Reducir alcance."}
        ],
        "summary": "Atender el riesgo.",
    }
    result = validate_generated_payload(payload, {"spi"})
    assert result["evidence_features_valid"] is False
    assert result["unsupported_numeric_claim"] is True
    assert result["grounded"] is False
    assert result["failure_code"] == "unknown_evidence_feature"


def test_empty_recommendations_are_valid_when_no_risk_drivers_exist():
    result = validate_generated_payload(
        {"recommendations": [], "summary": "No se identificaron drivers de riesgo relevantes."},
        set(),
        prediction=PREDICTION,
        drivers=[],
    )
    assert result["schema_valid"] is True
    assert result["grounded"] is True
    assert result["actionability"] is True
    assert result["failure_code"] is None


def test_empty_recommendations_are_rejected_when_risk_drivers_exist():
    result = validate_generated_payload(
        {"recommendations": [], "summary": "No se identificaron drivers."},
        {"cpi"},
        prediction=PREDICTION,
        drivers=DRIVERS,
    )
    assert result["grounded"] is False
    assert result["failure_code"] == "empty_recommendations_with_risk_drivers"


def test_supported_driver_and_percentage_numbers_are_allowed():
    payload = {
        "recommendations": [{"evidence_feature": "cpi", "reason": "El CPI observado es 0.8 y el sobrecosto es 4 %.", "action": "Revisar la proyección de costos."}],
        "summary": "El retraso estimado es 27,3 días.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["unsupported_numeric_claim"] is False
    assert result["grounded"] is True


def test_numbers_not_present_in_evidence_are_rejected():
    payload = {
        "recommendations": [{"evidence_feature": "cpi", "reason": "El CPI es 0.82 y el retraso será 99 días.", "action": "Revisar la proyección de costos."}],
        "summary": "Priorizar seguimiento.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["unsupported_numeric_claim"] is True
    assert result["failure_code"] == "unsupported_numeric_claim"


def test_percentage_equivalent_is_allowed_but_unqualified_scaled_number_is_not():
    payload = {
        "recommendations": [{"evidence_feature": "cpi", "reason": "El CPI es 0.82 y el sobrecosto equivale a 4 %.", "action": "Revisar la proyección de costos."}],
        "summary": "Priorizar seguimiento.",
    }
    accepted = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert accepted["grounded"] is True
    payload["recommendations"][0]["reason"] = "El CPI es 0.82 y el sobrecosto equivale a 4."
    rejected = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert rejected["failure_code"] == "unsupported_numeric_claim"


def test_unknown_feature_is_rejected_even_with_valid_numeric_evidence():
    payload = {
        "recommendations": [{"evidence_feature": "team_turnover", "reason": "El CPI observado es 0.82.", "action": "Revisar la proyección de costos."}],
        "summary": "Priorizar seguimiento.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["evidence_features_valid"] is False
    assert result["failure_code"] == "unknown_evidence_feature"


def _ollama_response(content):
    class Response:
        text = content

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"message": {"content": content}}

    return Response()


def test_invalid_json_uses_safe_fallback_and_hides_raw_response(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: _ollama_response("not json"))
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["engine"] == "grounded_fallback"
    assert result["genai_attempted"] is True
    assert result["genai_used"] is False
    assert result["failure_code"] == "invalid_json"
    assert "raw_response" not in result


def test_http_error_uses_http_error_failure_code(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    class ErrorResponse:
        @staticmethod
        def raise_for_status():
            raise requests.exceptions.HTTPError("503 server error")
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: ErrorResponse())
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["engine"] == "grounded_fallback"
    assert result["failure_code"] == "http_error"


def test_valid_json_with_invalid_structure_uses_invalid_schema_code(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: _ollama_response('{"recommendations":[],"summary":9}'))
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["failure_code"] == "invalid_schema"
    assert result["genai_used"] is False


def test_successful_ollama_payload_is_marked_as_genai(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    content = '{"recommendations":[{"evidence_feature":"cpi","reason":"El desempeño de costos requiere atención.","action":"Revisar la proyección de costos."}],"summary":"Priorizar seguimiento de costos."}'
    def post(*args, **kwargs):
        assert kwargs["json"]["think"] is False
        assert kwargs["json"]["format"] == "json"
        assert kwargs["json"]["options"]["temperature"] == 0.1
        assert kwargs["json"]["options"]["num_predict"] == 400
        assert kwargs["timeout"] == 30
        return _ollama_response(content)
    monkeypatch.setattr(recommendations.requests, "post", post)
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["genai_used"] is True
    assert result["genai_attempted"] is True
    assert result["engine"] == "ollama:qwen3:8b"
    assert result["failure_code"] is None
    assert result["genai_latency_ms"] is not None
    assert "genai_debug" not in result


def test_genai_debug_is_returned_only_when_enabled(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("PRUNIN_GENAI_DEBUG", "1")
    content = '{"recommendations":[{"evidence_feature":"cpi","reason":"El desempeño de costos requiere atención.","action":"Revisar la proyección de costos."}],"summary":"Priorizar seguimiento de costos."}'
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: _ollama_response(content))
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["genai_debug"]["raw_response"] == content
    assert result["genai_debug"]["parsed_json"]["recommendations"][0]["evidence_feature"] == "cpi"


def test_read_timeout_uses_safe_fallback_with_structured_code(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", "30")
    def raise_timeout(*args, **kwargs):
        assert kwargs["timeout"] == 30
        raise requests.exceptions.ReadTimeout("read timeout=30")
    monkeypatch.setattr(recommendations.requests, "post", raise_timeout)
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["engine"] == "grounded_fallback"
    assert result["genai_used"] is False
    assert result["failure_code"] == "ollama_timeout"


def test_disabled_ollama_uses_fallback_without_attempt(monkeypatch):
    monkeypatch.delenv("PRUNIN_ENABLE_OLLAMA", raising=False)
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no request expected")))
    result = recommendations.build_recommendations({}, PREDICTION, DRIVERS)
    assert result["engine"] == "grounded_fallback"
    assert result["genai_attempted"] is False
    assert result["genai_used"] is False


def test_ollama_status_reports_available_model_and_disabled_state(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    class TagsResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"models": [{"name": "qwen3:8b"}]}
    monkeypatch.setattr(recommendations.requests, "get", lambda *args, **kwargs: TagsResponse())
    status = recommendations.check_ollama_status()
    assert status["enabled"] is True
    assert status["available"] is True
    assert status["model"] == "qwen3:8b"

    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "0")
    status = recommendations.check_ollama_status()
    assert status["enabled"] is False
    assert status["available"] is False


def test_ollama_timeout_uses_one_environment_default_and_supports_override(monkeypatch):
    monkeypatch.delenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", raising=False)
    assert recommendations.ollama_timeout_seconds() == 30
    monkeypatch.setenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", "18")
    assert recommendations.ollama_timeout_seconds() == 18
    assert recommendations.ollama_timeout_seconds(4) == 4


def test_fallback_is_auditable_and_not_presented_as_genai():
    drivers = [
        {"feature": "spi", "label": "SPI", "direction": "increases_risk", "risk_impact": 0.2}
    ]
    result = grounded_fallback({}, {"health": "at_risk"}, drivers)
    assert result["engine"] == "grounded_fallback"
    assert result["genai_attempted"] is False
    assert result["genai_used"] is False
    assert result["evidence_features"] == ["spi"]
    assert result["grounding"]["raw_project_text_sent_to_llm"] is False


def test_fallback_does_not_force_an_action_without_risk_drivers():
    result = grounded_fallback({}, {"health": "healthy"}, [{"feature": "spi", "direction": "reduces_risk"}])
    assert result["actions"] == []
    assert result["evidence_features"] == []
    assert "No se identificaron drivers" in result["summary"]
