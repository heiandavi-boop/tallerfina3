"""Tests for the Qwen3 8B vs. GPT-OSS 20B comparison harness.

Every Ollama response in this file is SIMULATED (no network). Simulated runs are
flagged ``simulated=True`` and can never produce a defensible winner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_local_model_comparison as runner  # noqa: E402
from local_model_comparison_reports import OUTPUT_FILES, generate_reports  # noqa: E402
from prunin_ai.api import recommendations  # noqa: E402
from prunin_ai.genai_comparison import (  # noqa: E402
    AUTHORIZED_MODELS,
    DECISION_WEIGHTS,
    UnauthorizedModelError,
    check_split_isolation,
    completeness,
    decide,
    percentile,
    read_jsonl,
    select_repeat_cases,
    sensitivity_scenarios,
    summarize_model,
    validate_comparison_dir,
    validate_model_selection,
    weighted_totals,
)

ARTIFACT = ROOT / "artifacts/0.9.0-academic"
CASE_IDS = [f"T{index:03d}" for index in range(30)]


def simulated_environment(url, models):
    return {
        "ollama_reachable": True, "ollama_version": "SIMULATED", "missing": [], "errors": [],
        "models": {model: {"name": model, "digest": f"sim-{model}", "parameter_size": "x", "quantization_level": "q", "size_bytes": 1} for model in models},
    }


def simulated_cases():
    return [{
        "case_id": case_id, "health": "at_risk", "input": {}, "prediction": {"health": "at_risk"}, "drivers": [], "risk_drivers": [{}],
        "allowed_features": ["cpi"], "evidence_sha256": "e" * 64, "prompt_sha256": "p" * 64,
    } for case_id in CASE_IDS]


def simulated_prepare(artifact, input_path):
    return "SIMULATED", simulated_cases(), {"ok": True, "cases": 30, "train_overlap": [], "validation_overlap": [], "outside_test": []}


def simulated_result(case, model, url, timeout):
    accepted = model == "qwen3:8b" or int(case["case_id"][1:]) % 3 != 0
    payload = {"summary": "s", "recommendations": [{"priority": "alta", "evidence": "cpi", "action": "Revisar", "follow_up": "Verificar"}]}
    return {
        "ok": accepted, "latency_ms": 1000.0 if model == "qwen3:8b" else 900.0, "payload": payload,
        "validation": {"schema_valid": True, "grounded": accepted, "unsupported_numeric_claim": not accepted, "actionability": True,
                       "follow_up_verifiable": True, "contradictory_claim": False, "referenced_evidence_features": ["cpi"]},
        "failure_code": None if accepted else "unsupported_numeric_claim", "raw_response": json.dumps(payload),
        "usage": {"prompt_tokens": 10, "completion_tokens": 100, "eval_duration_ns": 2_000_000_000, "thinking_chars": 0},
    }


def make_args(tmp_path: Path, name: str = "exp") -> argparse.Namespace:
    return argparse.Namespace(models=list(AUTHORIZED_MODELS), cases=30, repeats=3, timeout=5.0, artifact=ARTIFACT,
                              input=ROOT / "data/processed/mendeley_core.csv", ollama_url="http://simulated/api/chat", output_dir=tmp_path / name)


def simulated_run(args, evaluate_fn=simulated_result):
    return runner.run(args, environment=simulated_environment, prepare_fn=simulated_prepare, evaluate_fn=evaluate_fn,
                      unload_fn=lambda url: [], resources_fn=lambda url, model: {"resident_size_bytes": 1}, simulated=True)


def test_only_the_two_authorized_models_are_accepted():
    assert validate_model_selection(["gpt-oss:20b", "qwen3:8b"]) == ["qwen3:8b", "gpt-oss:20b"]
    for models in (["qwen3:8b", "gemma3:12b"], ["qwen3:8b"], ["qwen3:8b", "gpt-oss:20b", "llama3"], ["qwen3:8b", "qwen3:8b"]):
        with pytest.raises(UnauthorizedModelError):
            validate_model_selection(models)
    with pytest.raises(SystemExit):
        runner.parse_args(["--models", "qwen3:8b", "gemma3:12b"])
    with pytest.raises(SystemExit):
        runner.parse_args(["--cases", "10"])


def test_repeat_selection_is_deterministic_and_independent_of_order():
    first = select_repeat_cases(CASE_IDS)
    assert len(first) == 5 and set(first) <= set(CASE_IDS)
    assert select_repeat_cases(list(reversed(CASE_IDS))) == first


def test_split_isolation_detects_train_contamination():
    split = {"train": ["A"], "validation": ["B"], "test": ["C", "D"]}
    assert check_split_isolation(["C", "D"], split)["ok"]
    contaminated = check_split_isolation(["C", "A"], split)
    assert not contaminated["ok"] and contaminated["train_overlap"] == ["A"]


def test_real_test_cases_are_identical_and_isolated():
    version_a, cases_a, isolation = runner.prepare(ARTIFACT, ROOT / "data/processed/mendeley_core.csv")
    _, cases_b, _ = runner.prepare(ARTIFACT, ROOT / "data/processed/mendeley_core.csv")
    assert isolation["ok"] and len(cases_a) == 30
    assert [(case["case_id"], case["prompt_sha256"], case["evidence_sha256"]) for case in cases_a] == [(case["case_id"], case["prompt_sha256"], case["evidence_sha256"]) for case in cases_b]
    split = json.loads((ARTIFACT / "split_manifest.json").read_text(encoding="utf-8"))
    assert {case["case_id"] for case in cases_a} <= set(map(str, split["test"]))


def test_timeout_and_empty_content_are_classified(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("simulated timeout")

    monkeypatch.setattr(recommendations.requests, "post", timeout)
    result = recommendations.generate_ollama_grounded({"health": "at_risk"}, [], model="gpt-oss:20b", think="low")
    assert result["failure_code"] == "ollama_timeout" and result["payload"] is None

    class Empty:
        text = '{"message": {"content": "", "thinking": "abc"}}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "", "thinking": "abc"}, "eval_count": 7, "done_reason": "stop"}

    sent = {}

    def empty(url, json, timeout):
        sent.update(json)
        return Empty()

    monkeypatch.setattr(recommendations.requests, "post", empty)
    result = recommendations.generate_ollama_grounded({"health": "at_risk"}, [], model="gpt-oss:20b", think="low", temperature=0.1, num_predict=1200)
    assert result["failure_code"] == "invalid_json" and result["usage"]["thinking_chars"] == 3
    assert sent["think"] == "low" and sent["options"] == {"temperature": 0.1, "num_predict": 1200} and "format" in sent


def test_json_contract_row_records_validator_outcome():
    case = simulated_cases()[0]
    failed = runner.to_row(case, "gpt-oss:20b", "main", 1, {"ok": False, "payload": None, "validation": {}, "failure_code": "invalid_json", "latency_ms": 5})
    assert not failed["json_parsed"] and not failed["schema_valid"] and not failed["grounded"] and failed["failure_code"] == "invalid_json"
    ok = runner.to_row(case, "qwen3:8b", "main", 1, simulated_result(case, "qwen3:8b", "", 1))
    assert ok["json_parsed"] and ok["schema_valid"] and ok["grounded"] and ok["priority_valid"] and ok["priorities"] == ["alta"]


def test_metrics_are_computed_correctly():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    rows = [
        {"case_id": "a", "grounded": True, "json_parsed": True, "schema_valid": True, "latency_ms": 100, "completion_tokens": 10, "eval_duration_ns": 1_000_000_000},
        {"case_id": "b", "grounded": False, "json_parsed": True, "schema_valid": False, "latency_ms": 300, "failure_code": "ollama_timeout", "completion_tokens": 30, "eval_duration_ns": 1_000_000_000},
    ]
    repeat = [{"case_id": "a", "grounded": True, "response_sha256": "x"}, {"case_id": "a", "grounded": True, "response_sha256": "y"}]
    metrics = summarize_model(rows, repeat)
    assert metrics["accepted_rate"] == 0.5 and metrics["schema_valid_rate"] == 0.5 and metrics["latency_ms_median"] == 200
    assert metrics["tokens_per_second"] == 20 and metrics["timeouts"] == 1 and metrics["operational_error_rate"] == 0.25
    assert metrics["repeatability"]["consistent_case_rate"] == 1.0 and metrics["repeatability"]["identical_response_rate"] == 0.0


def _metrics(grounded: float, latency: float) -> dict:
    return {"grounded_rate": grounded, "actionability_rate": grounded, "priority_valid_rate": 1, "follow_up_verifiable_rate": grounded,
            "json_valid_rate": 1, "schema_valid_rate": 1, "latency_ms_median": latency, "operational_error_rate": 0,
            "repeatability": {"consistent_case_rate": 1}}


def test_decision_weights_sum_to_one_and_winner_requires_evidence():
    assert sum(DECISION_WEIGHTS.values()) == pytest.approx(1.0)
    for weights in sensitivity_scenarios().values():
        assert sum(weights.values()) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        weighted_totals({"m": {key: 1 for key in DECISION_WEIGHTS}}, {**DECISION_WEIGHTS, "grounding": 0.5})
    clear = {"qwen3:8b": _metrics(0.9, 1000), "gpt-oss:20b": _metrics(0.5, 1000)}
    assert decide(clear, evidence_complete=True)["winner"] == "qwen3:8b"
    assert decide(clear, evidence_complete=False)["winner"] is None
    close = {"qwen3:8b": _metrics(0.80, 1000), "gpt-oss:20b": _metrics(0.79, 1000)}
    result = decide(close, evidence_complete=True)
    assert result["winner"] is None and not result["defensible"]


def test_simulated_run_completes_and_refuses_overwrite(tmp_path):
    args = make_args(tmp_path)
    assert simulated_run(args) == runner.EXIT_OK
    manifest = json.loads((args.output_dir / "execution_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete" and manifest["simulated"] is True
    for name in OUTPUT_FILES:
        assert (args.output_dir / name).exists(), name
    assert validate_comparison_dir(args.output_dir)["valid"]
    summary = json.loads((args.output_dir / "benchmark_summary.json").read_text(encoding="utf-8"))
    assert summary["decision"]["winner"] is None and "SIMULADA" in summary["decision"]["reasons"][0]
    with pytest.raises(FileExistsError):
        simulated_run(args)
    (args.output_dir / "decision_matrix.csv").write_text("tampered", encoding="utf-8")
    assert not validate_comparison_dir(args.output_dir)["valid"]


def test_interrupted_run_is_marked_incomplete_and_resumes_without_duplicates(tmp_path):
    args = make_args(tmp_path)
    calls = {"count": 0}

    def flaky(case, model, url, timeout):
        calls["count"] += 1
        if calls["count"] == 12:
            raise KeyboardInterrupt
        return simulated_result(case, model, url, timeout)

    with pytest.raises(KeyboardInterrupt):
        simulated_run(args, flaky)
    manifest = json.loads((args.output_dir / "execution_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "incomplete"
    assert not validate_comparison_dir(args.output_dir)["valid"]
    with (args.output_dir / "runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"truncated": ')
    assert simulated_run(args) == runner.EXIT_OK
    rows, _ = read_jsonl(args.output_dir / "runs.jsonl")
    status = completeness(rows, list(AUTHORIZED_MODELS), CASE_IDS, select_repeat_cases(CASE_IDS), 3)
    assert status["complete"] and status["duplicates"] == 0 and len(rows) == 2 * (30 + 15)


def test_missing_model_blocks_without_inference(tmp_path):
    args = make_args(tmp_path)

    def missing(url, models):
        return {"ollama_reachable": True, "ollama_version": "SIMULATED", "missing": ["gpt-oss:20b"], "errors": [], "models": {}}

    def never(*_):
        raise AssertionError("No debe ejecutar inferencias.")

    code = runner.run(args, environment=missing, prepare_fn=never, evaluate_fn=never, unload_fn=lambda url: [], simulated=True)
    manifest = json.loads((args.output_dir / "execution_manifest.json").read_text(encoding="utf-8"))
    assert code == runner.EXIT_BLOCKED and manifest["status"] == "blocked_missing_dependency" and manifest["missing_models"] == ["gpt-oss:20b"]
    assert not (args.output_dir / "runs.jsonl").exists()


def test_reports_are_reproducible(tmp_path):
    args = make_args(tmp_path)
    simulated_run(args)
    manifest = json.loads((args.output_dir / "execution_manifest.json").read_text(encoding="utf-8"))
    rows, _ = read_jsonl(args.output_dir / "runs.jsonl")
    regenerated = tmp_path / "regenerated"
    regenerated.mkdir()
    cases = simulated_cases()
    for case in cases:
        case["allowed_features"] = ["cpi"]
    generate_reports(regenerated, manifest, cases, rows)
    for name in OUTPUT_FILES:
        original = hashlib.sha256((args.output_dir / name).read_bytes()).hexdigest()
        assert hashlib.sha256((regenerated / name).read_bytes()).hexdigest() == original, name


def test_api_exposes_only_sanitized_comparison(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from prunin_ai.api import app as app_module

    monkeypatch.setattr(app_module, "GENAI_COMPARISON_DIR", tmp_path / "missing")
    client = TestClient(app_module.app)
    assert client.get("/api/genai-comparison").json()["status"] == "not_available"
    args = make_args(tmp_path)
    simulated_run(args)
    monkeypatch.setattr(app_module, "GENAI_COMPARISON_DIR", args.output_dir)
    body = client.get("/api/genai-comparison").json()
    assert body["valid"] and set(body["models"]) == set(AUTHORIZED_MODELS)
    assert str(tmp_path) not in json.dumps(body) and body["decision"]["defensible"] is False
    assert client.post("/api/genai-comparison").status_code in {404, 405}


def test_frozen_academic_artifacts_are_unchanged():
    frozen = ["artifacts/0.9.0-academic", "reports/genai/qwen_local_2026"]
    tracked = subprocess.run(["git", "ls-files", *frozen], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert tracked, "Los artefactos congelados deben estar versionados."
    changed = subprocess.run(["git", "status", "--porcelain", "--", *frozen], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert changed.strip() == ""


def test_regenerating_reports_keeps_integrity_and_never_runs_inference(tmp_path):
    args = make_args(tmp_path)
    simulated_run(args)
    before = (args.output_dir / "runs.jsonl").read_bytes()
    assert runner.regenerate_reports(args, prepare_fn=simulated_prepare) == runner.EXIT_OK
    assert (args.output_dir / "runs.jsonl").read_bytes() == before
    assert validate_comparison_dir(args.output_dir)["valid"]

    def changed_cases(artifact, input_path):
        version, cases, isolation = simulated_prepare(artifact, input_path)
        cases[0]["prompt_sha256"] = "x" * 64
        return version, cases, isolation

    with pytest.raises(RuntimeError):
        runner.regenerate_reports(args, prepare_fn=changed_cases)
