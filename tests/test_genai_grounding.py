import json
import requests

from prunin_ai.api import recommendations
from prunin_ai.api.recommendations import build_grounded_prompt, grounded_fallback, validate_generated_payload


PREDICTION = {"health": "at_risk", "delay_days": 27.3, "cost_overrun_ratio": 0.04}
DRIVERS = [{"feature": "cpi", "value": 0.82, "reference": 1.0, "direction": "increases_risk"}]


def _action(feature="spi", *, priority="alta", reason="El SPI es una señal asociada con presión en el cronograma.", action="Identificar las actividades con mayor desviación frente al plan y definir un plan de recuperación para el siguiente seguimiento.", follow_up="Revisar SPI y cumplimiento del cronograma en el siguiente corte.", title="Recuperar el cronograma"):
    return {
        "priority": priority,
        "title": title,
        "evidence_feature": feature,
        "reason": reason,
        "action": action,
        "follow_up": follow_up,
    }


def test_generated_payload_accepts_only_allowlisted_evidence():
    payload = {
        "recommendations": [_action()],
        "summary": "Priorizar la revisión del cronograma.",
    }
    result = validate_generated_payload(payload, {"spi", "cpi"})
    assert result["schema_valid"] is True
    assert result["evidence_features_valid"] is True
    assert result["action_structure_valid"] is True
    assert result["follow_up_present"] is True
    assert result["unsupported_numeric_claim"] is False
    assert result["grounded"] is True


def test_generated_payload_rejects_unknown_evidence_and_new_numbers():
    payload = {
        "recommendations": [_action(
            "scope_growth_ratio",
            reason="El riesgo subió 20 por ciento por esta señal.",
            action="Reducir el alcance mediante una revisión detallada de las solicitudes antes de acordar nuevos compromisos.",
        )],
        "summary": "Priorizar la revisión del alcance.",
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
        "recommendations": [_action(
            "cpi",
            title="Revisar costos",
            reason="El CPI observado es 0.8 y el sobrecosto es 4 % según la evidencia disponible.",
            action="Revisar la proyección y analizar el consumo presupuestal antes de aprobar nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el próximo seguimiento.",
        )],
        "summary": "El retraso estimado es 27,3 días.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["unsupported_numeric_claim"] is False
    assert result["grounded"] is True


def test_numbers_not_present_in_evidence_are_rejected():
    payload = {
        "recommendations": [_action(
            "cpi",
            title="Revisar costos",
            reason="El CPI es 0.82 y el retraso será 99 días según el plan.",
            action="Revisar la proyección y analizar el consumo presupuestal antes de aprobar nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el próximo seguimiento.",
        )],
        "summary": "Priorizar seguimiento de costos.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["unsupported_numeric_claim"] is True
    assert result["failure_code"] == "unsupported_numeric_claim"


def test_unsupported_numbers_are_counted_even_when_action_schema_is_invalid():
    result = validate_generated_payload(
        {"recommendations": [{"priority": "urgent", "action": "El retraso estimado será 99 días."}], "summary": "Revisar el proyecto."},
        {"cpi"},
        prediction=PREDICTION,
        drivers=DRIVERS,
    )

    assert result["schema_valid"] is False
    assert result["unsupported_numeric_claim"] is True


def test_percentage_equivalent_is_allowed_but_unqualified_scaled_number_is_not():
    payload = {
        "recommendations": [_action(
            "cpi",
            title="Revisar costos",
            reason="El CPI es 0.82 y el sobrecosto equivale a 4 %.",
            action="Revisar la proyección y analizar el consumo presupuestal antes de aprobar nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el próximo seguimiento.",
        )],
        "summary": "Priorizar seguimiento de costos.",
    }
    accepted = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert accepted["grounded"] is True
    payload["recommendations"][0]["reason"] = "El CPI es 0.82 y el sobrecosto equivale a 4."
    rejected = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert rejected["failure_code"] == "unsupported_numeric_claim"


def test_unknown_feature_is_rejected_even_with_valid_numeric_evidence():
    payload = {
        "recommendations": [_action(
            "team_turnover",
            title="Revisar costos",
            reason="El CPI observado es 0.82.",
            action="Revisar la proyección y analizar el consumo presupuestal antes de aprobar nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el próximo seguimiento.",
        )],
        "summary": "Priorizar seguimiento de costos.",
    }
    result = validate_generated_payload(payload, {"cpi"}, prediction=PREDICTION, drivers=DRIVERS)
    assert result["evidence_features_valid"] is False
    assert result["failure_code"] == "unknown_evidence_feature"


def test_invalid_priority_and_empty_follow_up_are_rejected():
    invalid_priority = validate_generated_payload(
        {"recommendations": [_action(priority="urgente")], "summary": "Priorizar acciones de gestión."},
        {"spi"},
    )
    malformed_priority = validate_generated_payload(
        {"recommendations": [_action(priority=[])], "summary": "Priorizar acciones de gestión."},
        {"spi"},
    )
    missing_follow_up = validate_generated_payload(
        {"recommendations": [_action(follow_up="")], "summary": "Priorizar acciones de gestión."},
        {"spi"},
    )
    assert invalid_priority["schema_valid"] is False
    assert malformed_priority["schema_valid"] is False
    assert missing_follow_up["schema_valid"] is False
    assert missing_follow_up["follow_up_present"] is False


def test_non_concrete_action_and_more_than_four_recommendations_are_rejected():
    weak_action = validate_generated_payload(
        {"recommendations": [_action(action="Revisar el proyecto.")], "summary": "Priorizar acciones de gestión."},
        {"spi"},
    )
    too_many = validate_generated_payload(
        {"recommendations": [_action() for _ in range(5)], "summary": "Priorizar acciones de gestión."},
        {"spi"},
    )
    assert weak_action["actionability"] is False
    assert weak_action["grounded"] is False
    assert too_many["schema_valid"] is False


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
    assert result["recommendations"][0]["follow_up"]


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


def test_ollama_unavailable_keeps_structured_fallback(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setattr(
        recommendations.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.exceptions.ConnectionError("offline")),
    )

    result = recommendations.build_recommendations({}, PREDICTION, DRIVERS)

    assert result["engine"] == "grounded_fallback"
    assert result["genai_attempted"] is True
    assert result["genai_used"] is False
    assert result["failure_code"] == "ollama_unavailable"
    assert result["recommendations"][0]["evidence_feature"] == "cpi"
    assert result["recommendations"][0]["follow_up"]


def test_valid_json_with_invalid_structure_uses_invalid_schema_code(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setattr(recommendations.requests, "post", lambda *args, **kwargs: _ollama_response('{"recommendations":[],"summary":9}'))
    result = recommendations.ollama_recommendations({}, PREDICTION, DRIVERS)
    assert result["failure_code"] == "invalid_schema"
    assert result["genai_used"] is False


def test_successful_ollama_payload_is_marked_as_genai(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    content = json.dumps({
        "recommendations": [_action(
            "cpi",
            priority="alta",
            title="Revisar costos",
            reason="El CPI aparece entre las señales asociadas con mayor riesgo.",
            action="Analizar el consumo presupuestal y actualizar la estimación al cierre antes de asumir nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el siguiente seguimiento.",
        )],
        "summary": "Priorizar la revisión de costos.",
    }, ensure_ascii=False)
    def post(*args, **kwargs):
        assert kwargs["json"]["think"] is False
        response_schema = kwargs["json"]["format"]
        action_schema = response_schema["properties"]["recommendations"]
        assert action_schema["minItems"] == 1
        assert action_schema["maxItems"] == 4
        item_properties = action_schema["items"]["properties"]
        assert item_properties["priority"]["enum"] == ["alta", "media", "baja"]
        assert item_properties["evidence_feature"]["enum"] == ["cpi"]
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
    content = json.dumps({
        "recommendations": [_action(
            "cpi",
            priority="alta",
            title="Revisar costos",
            reason="El CPI aparece entre las señales asociadas con mayor riesgo.",
            action="Analizar el consumo presupuestal y actualizar la estimación al cierre antes de asumir nuevos compromisos.",
            follow_up="Comparar CPI y proyección de costo en el siguiente seguimiento.",
        )],
        "summary": "Priorizar la revisión de costos.",
    }, ensure_ascii=False)
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
    assert result["recommendations"][0]["priority"] == "alta"
    assert result["recommendations"][0]["follow_up"]


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


def test_ollama_unavailable_is_reported_without_claiming_model_available(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "1")
    monkeypatch.setattr(
        recommendations.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.exceptions.ConnectionError("offline")),
    )

    status = recommendations.check_ollama_status()

    assert status["enabled"] is True
    assert status["available"] is False
    assert status["last_error"]["failure_code"] == "ollama_unavailable"


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
    assert result["recommendations"][0]["priority"] == "alta"
    assert result["recommendations"][0]["evidence_feature"] == "spi"
    assert result["recommendations"][0]["follow_up"]
    assert result["grounding"]["raw_project_text_sent_to_llm"] is False


def test_fallback_does_not_force_an_action_without_risk_drivers():
    result = grounded_fallback({}, {"health": "healthy"}, [{"feature": "spi", "direction": "reduces_risk"}])
    assert result["actions"] == []
    assert result["recommendations"] == []
    assert result["evidence_features"] == []
    assert "No se identifican acciones correctivas prioritarias" in result["summary"]


def test_grounded_prompt_requests_actions_follow_up_and_non_causal_language():
    prompt, allowed = build_grounded_prompt(PREDICTION, DRIVERS)

    assert allowed == {"cpi"}
    assert "Tu tarea NO es resumir el diagnóstico" in prompt
    assert '"follow_up"' in prompt
    assert "No afirmes causalidad" in prompt
    assert "Prioriza qué debería hacer ahora el responsable" in prompt
    assert "está prohibido devolver recommendations vacías" in prompt
    assert '"evidence_feature":"cpi"' in prompt
    assert '"evidence_feature":"spi"' not in prompt


def test_grounded_prompt_allows_empty_actions_only_without_risk_drivers():
    prompt, allowed = build_grounded_prompt(PREDICTION, [])

    assert allowed == set()
    assert "No hay drivers que incrementen riesgo" in prompt
    assert '"recommendations":[]' in prompt


def test_fallback_returns_a_complete_action_structure_in_priority_order():
    drivers = [
        {"feature": "rework_ratio", "label": "Retrabajo", "direction": "increases_risk"},
        {"feature": "spi", "label": "SPI", "direction": "increases_risk"},
        {"feature": "cpi", "label": "CPI", "direction": "increases_risk"},
    ]

    result = grounded_fallback({}, PREDICTION, drivers)

    assert [item["priority"] for item in result["recommendations"]] == ["alta", "alta", "media"]
    assert all({"priority", "title", "evidence_feature", "reason", "action", "follow_up"} <= set(item) for item in result["recommendations"])
    assert all(item["action"].split()[0].lower() in recommendations.ACTION_VERBS for item in result["recommendations"])
