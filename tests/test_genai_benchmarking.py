import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from genai_benchmark_common import model_is_installed, percentile, summarize_rows

def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_availability_does_not_match_other_tags():
    assert model_is_installed("qwen3:8b", {"qwen3:8b"})
    assert model_is_installed("qwen3:8b", {"qwen3:14b"}) is False
    assert model_is_installed("qwen3:8b", {"qwen3:8b:latest"})


def test_benchmark_metrics_are_calculated_from_raw_rows():
    rows = [
        {"generation_success": True, "schema_valid": True, "grounded": True, "unsupported_numeric_claim": False, "actionability": True, "latency_ms": 100, "failure_code": None},
        {"generation_success": False, "schema_valid": False, "grounded": False, "unsupported_numeric_claim": True, "actionability": False, "latency_ms": 300, "failure_code": "ollama_timeout"},
    ]

    metrics = summarize_rows(rows)

    assert metrics["requests_total"] == 2
    assert metrics["generation_success_rate"] == 0.5
    assert metrics["unsupported_numeric_claim_rate"] == 0.5
    assert metrics["timeout_rate"] == 0.5
    assert metrics["latency_ms_median"] == 200
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5


def test_unavailable_concurrency_writes_outputs_without_calls(tmp_path, monkeypatch):
    module = _load_script("benchmark_genai_concurrency")
    monkeypatch.setattr(module, "ollama_models", lambda url: (None, "ConnectionError"))
    monkeypatch.setattr(module, "prepare_cases", lambda *args: (_ for _ in ()).throw(AssertionError("cases must not run")))
    monkeypatch.setattr("sys.argv", ["benchmark_genai_concurrency.py", "--output-dir", str(tmp_path)])

    assert module.main() == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["status"] == "not_executed"
    assert summary["availability"] == "not_available"
    assert (tmp_path / "raw.csv").exists()
    assert (tmp_path / "report.md").exists()


def test_candidate_benchmark_marks_uninstalled_model_not_available(tmp_path, monkeypatch):
    module = _load_script("benchmark_genai_candidates")
    monkeypatch.setattr(module, "ollama_models", lambda url: ({"qwen3:8b"}, None))
    cases = [{"case_id": f"case-{index}", "risk_drivers": [{"feature": "spi"}], "prediction": {}, "health": "at_risk"} for index in range(30)]
    monkeypatch.setattr(module, "prepare_cases", lambda *args: (SimpleNamespace(version="0.9.0-academic"), cases))
    monkeypatch.setattr(module, "evaluate_case", lambda case, model, url, timeout: {
        "case_id": case["case_id"], "model": model, "generation_success": True, "schema_valid": True,
        "grounded": True, "unsupported_numeric_claim": False, "actionability": True,
        "latency_ms": 10.0, "failure_code": None, "health": "at_risk", "driver_count": 1,
    })
    monkeypatch.setattr("sys.argv", ["benchmark_genai_candidates.py", "--models", "qwen3:8b", "gemma3:4b", "--output-dir", str(tmp_path)])

    assert module.main() == 0
    summary = json.loads((tmp_path / "benchmark_summary.json").read_text())
    assert summary["status"] == "partial"
    assert summary["models"]["qwen3:8b"]["status"] == "complete"
    assert summary["models"]["gemma3:4b"]["status"] == "not_available"
    assert summary["models"]["gemma3:4b"]["metrics"] is None
    assert len(summary["case_ids"]) == 30