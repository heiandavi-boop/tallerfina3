from prunin_ai.api.monitoring import MonitoringRegistry


def test_monitoring_registry_tracks_prediction_and_genai():
    registry = MonitoringRegistry(max_samples=10)
    registry.record_prediction(25.0, {"genai_attempted": True, "genai_used": True})
    registry.record_prediction(50.0, {"genai_attempted": True, "genai_used": False, "failure_code": "ollama_timeout"})
    registry.record_prediction(60.0, {"genai_attempted": True, "genai_used": False, "failure_code": "unsupported_numeric_claim"})
    registry.record_prediction(65.0, {"genai_attempted": True, "genai_used": False, "failure_code": "invalid_json"})
    registry.record_failure(75.0)
    snapshot = registry.snapshot(model_version="test", model_mode="demo")
    assert snapshot["total_predictions"] == 4
    assert snapshot["prediction_failures"] == 1
    assert snapshot["genai_attempts"] == 4
    assert snapshot["genai_successes"] == 1
    assert snapshot["genai_fallbacks"] == 3
    assert snapshot["genai_timeouts"] == 1
    assert snapshot["genai_validation_failures"] == 1
    assert snapshot["genai_invalid_json"] == 1
    assert snapshot["inference_latency_ms"]["sample_count"] == 5
    assert snapshot["inference_latency_ms"]["p95"] == 75.0
    prometheus = registry.prometheus_text(model_version="test", model_mode="demo")
    assert "prunin_genai_timeouts_total 1" in prometheus
    assert "prunin_genai_validation_failures_total 1" in prometheus
    assert "prunin_genai_invalid_json_total 1" in prometheus
