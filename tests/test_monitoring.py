from prunin_ai.api.monitoring import MonitoringRegistry


def test_monitoring_registry_tracks_prediction_and_genai():
    registry = MonitoringRegistry(max_samples=10)
    registry.record_prediction(25.0, {"genai_attempted": True, "genai_used": True})
    registry.record_prediction(50.0, {"genai_attempted": True, "genai_used": False})
    registry.record_failure(75.0)
    snapshot = registry.snapshot(model_version="test", model_mode="demo")
    assert snapshot["total_predictions"] == 2
    assert snapshot["prediction_failures"] == 1
    assert snapshot["genai_attempts"] == 2
    assert snapshot["genai_successes"] == 1
    assert snapshot["genai_fallbacks"] == 1
    assert snapshot["inference_latency_ms"]["sample_count"] == 3
    assert snapshot["inference_latency_ms"]["p95"] == 75.0
