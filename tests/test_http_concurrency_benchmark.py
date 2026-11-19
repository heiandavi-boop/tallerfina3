from scripts.benchmark_http_concurrency import _valid_prediction


def test_http_benchmark_requires_predictive_fields():
    assert _valid_prediction({"prediction": {
        "health": "at_risk",
        "delay_days": 10,
        "cost_overrun_ratio": 0.1,
    }})
    assert not _valid_prediction({"prediction": {"health": "at_risk", "delay_days": 10}})
    assert not _valid_prediction({"prediction": None})
