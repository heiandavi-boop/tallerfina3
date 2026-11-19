"""Provider comparison harness tests: no network, no real keys, no fabricated rows."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from prunin_ai.api import recommendations as ai

ROOT = Path(__file__).resolve().parents[1]
ROW = {"spi": 0.72, "cpi": 0.81, "team_utilization": 1.12, "team_capacity_ratio": 0.72}
PREDICTION = {"health": "at_risk", "delay_days": 27.0, "cost_overrun_ratio": 0.08}
CASE = {"case_id": "P-1", "input": ROW, "prediction": PREDICTION, "drivers": []}


def _load():
    spec = importlib.util.spec_from_file_location("benchmark_provider_comparison", ROOT / "scripts" / "benchmark_provider_comparison.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload():
    fallback = ai.grounded_fallback(ROW, PREDICTION, [])
    return {"summary": fallback["summary"], "recommendations": fallback["recommendations"]}


def test_budget_guard_blocks_before_exceeding_estimated_limit():
    bench = _load()
    guard = bench.BudgetGuard(0.05, 2.0, 8.0, margin=1.5, reserved_output_tokens=1000)
    reservation = guard.reserve("x" * 3000)
    assert reservation == pytest.approx((1000 * 2 + 1000 * 8) / 1e6 * 1.5)
    assert guard.settle({"prompt_tokens": 1000, "completion_tokens": 500}, reservation) == pytest.approx(0.006)
    guard.settle(None, 0.04)  # missing usage keeps the conservative reservation
    assert guard.unmetered_calls == 1
    with pytest.raises(bench.BudgetExceeded):
        guard.reserve("x" * 3000)
    assert guard.blocked_calls == 1


def test_openai_diagnosis_without_key_makes_no_request(monkeypatch):
    bench = _load()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = bench.diagnose_openai("gpt-4.1", get=lambda *a, **k: pytest.fail("no request expected"))
    assert report["available"] is False and report["failure_code"] == "openai_key_missing"


def test_openai_diagnosis_maps_401_without_leaking_key(monkeypatch):
    bench = _load()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")

    class Response:
        status_code = 401

    report = bench.diagnose_openai("gpt-4.1", get=lambda url, **kwargs: Response())
    assert report["failure_code"] == "openai_auth_error"
    assert "sk-secret-value" not in json.dumps(report)


def test_ollama_diagnosis_records_digest_and_quantization():
    bench = _load()

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self.data

    def get(url, **kwargs):
        if url.endswith("/api/version"):
            return Response({"version": "0.33.2"})
        return Response({"models": [{"name": "qwen3:8b", "digest": "abc", "details": {"quantization_level": "Q4_K_M", "parameter_size": "8.2B"}}]})

    report = bench.diagnose_ollama("qwen3:8b", "http://localhost:11434/api/chat", get=get)
    assert report["available"] and report["digest"] == "abc" and report["quantization"] == "Q4_K_M"
    assert report["ollama_version"] == "0.33.2"


def test_run_skips_unavailable_provider_and_stops_on_budget(monkeypatch):
    bench = _load()
    monkeypatch.setattr(bench, "build_case_evidence", lambda case, **config: {"prompt": "p" * 300, "evidence_json": "[]", "allowed_features": [], "evidence_status": "ok"})
    calls = []

    def caller(provider, case, config, settings):
        calls.append((provider, config["max_actions"]))
        payload = _payload()
        return {"ok": True, "model": "m", "latency_ms": 100.0, "payload": payload, "raw_response": json.dumps(payload),
                "validation": {"grounded": True, "schema_valid": True, "actionability": True, "evidence_features_valid": True},
                "usage": {"prompt_tokens": 100, "completion_tokens": 100}}

    providers = {"openai": {"available": True, "model": "gpt-4.1"}, "ollama": {"available": False, "failure_code": "ollama_unavailable"}}
    guard = bench.BudgetGuard(0.0035, 2.0, 8.0, margin=1.0, reserved_output_tokens=100)
    rows, stops = bench.run([CASE, {**CASE, "case_id": "P-2"}], providers, {}, repeat_cases=1, repeats=2, budget=guard, caller=caller, log=lambda _: None)
    assert all(provider == "openai" for provider, _ in calls)
    assert calls[0][1] == 4 and rows[0]["mode"] == "controlled"
    assert stops and guard.spent_usd <= guard.limit_usd
    summary = bench.summarize(rows, providers, stops, guard)
    assert summary["comparison_status"] == "incomplete_provider_unavailable"
    assert "controlled" not in summary["providers"]["ollama"]


def test_aggregate_reports_percentiles_acceptance_and_variability():
    bench = _load()
    base = {"generation_success": True, "schema_valid": True, "grounded": True, "evidence_supported": True, "unsupported_numeric_claim": False,
            "contradiction": False, "actionability": True, "follow_up_verifiable": True, "timeout": False, "actions_generated": 2,
            "actions_accepted": 2, "completion_tokens": 50, "cost_usd": 0.01, "project_id": "A", "provider": "ollama", "response": "x", "referenced_features": "spi"}
    rows = [{**base, "latency_ms": value} for value in (100.0, 200.0, 300.0, 400.0, 10_000.0)]
    rows[-1].update(grounded=False, actions_accepted=0, timeout=True, response="y")
    stats = bench.aggregate(rows)
    assert stats["grounded_response_rate"] == 0.8 and stats["timeout_rate"] == 0.2
    assert stats["latency_ms_median"] == 300.0 and stats["latency_ms_p95"] > 2000
    assert stats["cost_usd_total"] == pytest.approx(0.05)
    repeat = bench.repeatability(rows)["ollama"]
    assert repeat["identical_response_rate"] == 0.0 and repeat["stable_acceptance_rate"] == 0.0


def test_ollama_contract_parameters_reach_schema_and_usage_is_returned(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": json.dumps(_payload(), ensure_ascii=False)}, "prompt_eval_count": 900, "eval_count": 210}

    def post(url, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(ai.requests, "post", post)
    result = ai.generate_ollama_grounded(PREDICTION, [], row=ROW, max_actions=3, max_summary_chars=150)
    assert captured["format"]["properties"]["recommendations"]["maxItems"] == 3
    assert captured["format"]["properties"]["summary"]["maxLength"] == 150
    assert result["usage"] == {"prompt_tokens": 900, "completion_tokens": 210}
    default = ai.action_response_schema({"spi"})
    assert default["properties"]["recommendations"]["maxItems"] == 4


def test_openai_controlled_contract_limits_actions_in_prompt_and_validation(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(_payload(), ensure_ascii=False)}}], "usage": {}}

    def post(url, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(ai.requests, "post", post)
    ai.generate_openai_grounded(PREDICTION, [], row=ROW, api_key="sk-x", max_actions=4, max_summary_chars=180)
    assert "no excedas 4 acciones" in captured["messages"][1]["content"]
