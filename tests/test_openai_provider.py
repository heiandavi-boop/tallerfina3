"""Dual-provider tests do not require an OpenAI key or a running Ollama server."""
import json

from prunin_ai.api import recommendations as ai

ROW = {
    "spi": 0.72,
    "cpi": 0.81,
    "team_utilization": 1.12,
    "team_capacity_ratio": 0.72,
}
PREDICTION = {"health": "at_risk", "delay_days": 27.0, "cost_overrun_ratio": 0.08}
DRIVERS = []


def _valid_response():
    fallback = ai.grounded_fallback(ROW, PREDICTION, DRIVERS)
    return {"summary": fallback["summary"], "recommendations": fallback["recommendations"]}


def test_openai_uses_server_transport_and_does_not_return_key(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps(_valid_response(), ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 300, "completion_tokens": 200},
            }

    def mock_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(ai.requests, "post", mock_post)
    result = ai.generate_openai_grounded(
        PREDICTION, DRIVERS, row=ROW, api_key="sk-example-secret", model="gpt-4.1"
    )

    assert result["ok"], result.get("validation")
    assert calls[0][0] == "https://api.openai.com/v1/chat/completions"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer sk-example-secret"
    assert calls[0][1]["json"]["model"] == "gpt-4.1"
    assert calls[0][1]["json"]["response_format"] == {"type": "json_object"}
    assert "/no_think" not in calls[0][1]["json"]["messages"][1]["content"]
    assert "sk-example-secret" not in str(result)
    assert result["usage"]["prompt_tokens"] == 300


def test_missing_key_uses_grounded_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = ai.build_recommendations(ROW, PREDICTION, DRIVERS, provider="openai")
    assert not result["genai_used"]
    assert result["selected_provider"] == "openai"
    assert result["failure_code"] == "openai_key_missing"
    assert result["recommendations"]


def test_explicit_ollama_selection_does_not_mutate_process_env(monkeypatch):
    monkeypatch.setenv("PRUNIN_ENABLE_OLLAMA", "0")
    called = []

    def stub(prediction, drivers, *, row=None):
        called.append(True)
        return {"ok": False, "model": "qwen3:8b", "error": "ollama_unavailable",
                "failure_code": "ollama_unavailable", "failure_detail": "offline",
                "latency_ms": 1, "validation": None, "payload": None}

    monkeypatch.setattr(ai, "generate_ollama_grounded", stub)
    result = ai.build_recommendations(ROW, PREDICTION, DRIVERS, provider="ollama")
    assert called
    assert result["selected_provider"] == "ollama"
    assert result["genai_attempted"]
    assert ai.os.environ["PRUNIN_ENABLE_OLLAMA"] == "0"


def test_openai_extended_validation_keeps_grounding_rules():
    data = _valid_response()
    data["summary"] = "Revisar señales y contrastar decisiones con el director del proyecto. " * 4
    features = {item["evidence_feature"] for item in data["recommendations"]}
    context = ai.build_evidence_context(ROW, PREDICTION, DRIVERS)
    result = ai.validate_generated_payload(
        data, features, prediction=PREDICTION, drivers=DRIVERS,
        context=context, max_actions=8, max_summary_chars=1200
    )
    assert result["grounded"], result
    default = ai.validate_generated_payload(
        data, features, prediction=PREDICTION, drivers=DRIVERS, context=context
    )
    assert not default["schema_valid"]
