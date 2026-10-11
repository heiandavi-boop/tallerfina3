import pandas as pd
import pytest

from scripts.operational_efficiency import (
    ACADEMIC_FEATURES,
    build_summary,
    percentile,
    project_case_hash,
    sample_test_cases,
    summarize_mode,
)
from scripts.benchmark_operational_efficiency import environment_metadata
from scripts.benchmark_operational_efficiency import api_preflight
from scripts.benchmark_operational_efficiency import render_markdown


def _case_frame(project_count=120):
    rows = []
    for project_index in range(project_count):
        project_id = f"mendeley::P{project_index:04d}"
        for snapshot_index, progress in ((1, 0.5), (2, 0.75)):
            rows.append({
                "project_id": project_id,
                "snapshot_index": snapshot_index,
                "planned_duration_weeks": 30 + project_index,
                "planned_budget": 1_000_000 + project_index,
                "true_progress": progress,
                "spi": 0.9,
                "cpi": 0.95,
                "project_type": "it" if project_index % 2 else "r&d",
                "methodology": "agile" if project_index % 2 else "kanban",
                "health": "critical",
                "delay_days": 12.0,
            })
    return pd.DataFrame(rows)


def _run(mode, size, repetition, total_ms, case_ids):
    return {
        "mode": mode,
        "batch_size": size,
        "repetition": repetition,
        "total_ms": total_ms,
        "server_total_ms": total_ms * 0.8,
        "client_overhead_ms": total_ms * 0.2,
        "success_count": size,
        "error_count": 0,
        "case_ids_sha256": project_case_hash(case_ids),
        "task": "ml_and_drivers_without_recommendations",
    }


def test_percentiles_use_interpolated_observations():
    values = [10, 20, 30, 40, 50]
    assert percentile(values, 0.50) == 30
    assert percentile(values, 0.90) == 46
    assert percentile(values, 0.95) == 48


def test_test_case_sampling_is_seeded_latest_per_project_and_excludes_targets():
    frame = _case_frame()
    test_ids = {f"mendeley::P{index:04d}" for index in range(100)}
    first = sample_test_cases(frame, test_ids, limit=100, seed=42)
    second = sample_test_cases(frame, test_ids, limit=100, seed=42)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 100
    assert first.project_id.nunique() == 100
    assert set(first.columns) == {"case_order", "project_id", *ACADEMIC_FEATURES}
    assert set(first.true_progress) == {0.75}
    assert set(first.project_id) <= test_ids


def test_test_sampling_rejects_fewer_than_requested_valid_projects():
    with pytest.raises(ValueError, match="valid latest TEST projects"):
        sample_test_cases(_case_frame(3), {"mendeley::P0000", "mendeley::P0001"}, limit=5)


def test_mode_statistics_calculate_throughput_and_cost_per_project():
    rows = [_run("batch", 10, 1, 2000, [f"p{i}" for i in range(10)]), _run("batch", 10, 2, 3000, [f"p{i}" for i in range(10)])]
    summary = summarize_mode(rows, mode="batch", batch_size=10)
    assert summary["repetitions"] == 2
    assert summary["mean_ms"] == 2500
    assert summary["median_ms"] == 2500
    assert summary["p50_ms"] == 2500
    assert summary["p95_ms"] == 2950
    assert summary["throughput_projects_per_second"] == 4
    assert summary["throughput_projects_per_minute"] == 240
    assert summary["ms_per_project"] == 250
    assert summary["success_rate"] == 1
    assert summary["error_rate"] == 0
    assert summary["timeout_count"] == 0


def test_comparison_computes_speedup_only_for_matched_successful_genai_off_runs():
    ids_1 = ["p1"]
    ids_2 = ["p1", "p2"]
    records = [
        _run("individual", 1, 1, 1000, ids_1), _run("batch", 1, 1, 500, ids_1),
        _run("individual", 2, 1, 2000, ids_2), _run("batch", 2, 1, 800, ids_2),
    ]
    result = build_summary(
        records,
        case_ids_by_size={1: ids_1, 2: ids_2},
        repetitions_by_size={1: 1, 2: 1},
        environment={"genai_enabled": False},
    )
    assert result["status"] == "complete"
    assert result["comparison"]["1"]["speedup_batch_vs_sequential"] == 2
    assert result["comparison"]["1"]["time_reduction_percent"] == 50
    assert result["comparison"]["2"]["speedup_batch_vs_sequential"] == 2.5
    assert result["comparison"]["2"]["time_reduction_percent"] == 60
    assert result["comparison"]["2"]["sequential_median_total_ms"] == 2000
    assert result["comparison"]["2"]["batch_median_total_ms"] == 800


def test_no_division_by_zero_and_missing_runs_never_mark_complete():
    ids = ["p1"]
    zero_records = [_run(mode, 1, 1, 0, ids) for mode in ("individual", "batch")]
    zero_summary = summarize_mode(zero_records, mode="batch", batch_size=1)
    assert zero_summary["throughput_projects_per_second"] is None
    assert zero_summary["ms_per_project"] == 0

    incomplete = build_summary(
        [_run("individual", 1, 1, 5, ids)],
        case_ids_by_size={1: ids},
        repetitions_by_size={1: 2},
        environment={"genai_enabled": False},
    )
    assert incomplete["status"] == "incomplete"
    assert incomplete["comparison"] == {}
    assert incomplete["missing_runs"]


def test_speedup_is_not_reported_when_runs_failed_or_case_hashes_differ():
    ids = ["p1", "p2"]
    individual = _run("individual", 2, 1, 100, ids)
    failed_batch = _run("batch", 2, 1, 50, ids)
    failed_batch["success_count"] = 1
    failed_batch["error_count"] = 1
    result = build_summary(
        [individual, failed_batch],
        case_ids_by_size={2: ids},
        repetitions_by_size={2: 1},
        environment={"genai_enabled": False},
    )
    assert result["comparison"]["2"]["speedup_batch_vs_sequential"] is None

    different_batch = {**_run("batch", 2, 1, 50, ids), "case_ids_sha256": project_case_hash(["p1", "different"])}
    result = build_summary(
        [individual, different_batch],
        case_ids_by_size={2: ids},
        repetitions_by_size={2: 1},
        environment={"genai_enabled": False},
    )
    assert result["comparison"]["2"]["same_case_set"] is False
    assert result["comparison"]["2"]["speedup_batch_vs_sequential"] is None

    genai_enabled = build_summary(
        [_run("individual", 2, 1, 100, ids), _run("batch", 2, 1, 50, ids)],
        case_ids_by_size={2: ids},
        repetitions_by_size={2: 1},
        environment={"genai_enabled": True},
    )
    assert genai_enabled["comparison"]["2"]["speedup_batch_vs_sequential"] is None


def test_environment_metadata_preserves_academic_api_and_genai_off_state():
    api = {
        "api_url": "http://127.0.0.1:8002",
        "api_status": "ready",
        "artifact_version": "0.9.0-academic",
        "artifact_mode": "configured",
        "dataset_source": "Mendeley Data 2p5sz57wh2 version 2",
        "dataset_type": "synthetic external data",
        "model_type": "LightGBM",
        "trained_features": ACADEMIC_FEATURES,
        "genai_enabled": False,
        "genai_available": False,
    }
    environment = environment_metadata(api, "0.9.0-academic")
    assert environment["artifact_version"] == "0.9.0-academic"
    assert environment["api_mode"] == "configured"
    assert environment["dataset_source"] == "Mendeley Data 2p5sz57wh2 version 2"
    assert environment["genai_enabled"] is False


def test_api_preflight_rejects_demo_artifact_for_academic_measurement():
    class Response:
        def __init__(self, payload):
            self.payload = payload

        @staticmethod
        def raise_for_status():
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, timeout):
            if url.endswith("/api/ready"):
                return Response({"status": "ready"})
            if url.endswith("/api/health"):
                return Response({"version": "demo-0.1.0", "dataset_source": "synthetic_demo", "dataset_type": "synthetic", "model_type": "LightGBM", "trained_features": ACADEMIC_FEATURES, "mode": "synthetic_demo"})
            return Response({"enabled": False, "available": False, "model": "qwen3:8b"})

    _, metadata, error = api_preflight(Session(), "http://api.test", "0.9.0-academic", 1)
    assert metadata["artifact_version"] == "demo-0.1.0"
    assert "se requiere '0.9.0-academic'" in error


def test_markdown_summary_identifies_measured_head_and_local_limitations():
    case_ids = ["p1"]
    records = [_run(mode, 1, 1, duration, case_ids) for mode, duration in (("individual", 100), ("batch", 90))]
    summary = build_summary(
        records,
        case_ids_by_size={1: case_ids},
        repetitions_by_size={1: 1},
        environment={
            "genai_enabled": False,
            "git_sha": "abc123",
            "date_utc": "2026-10-11T00:00:00+00:00",
            "artifact_version": "0.9.0-academic",
            "dataset_source": "Mendeley Data v2",
            "os": "test-os",
            "python_version": "3.12",
            "cpu_architecture": "arm64",
            "api_mode": "academic",
            "workers": None,
        },
    )
    md = render_markdown(summary, {"successful_checks": 0, "checks": []}, {"status": "unavailable"}, [])
    assert "HEAD medido: `abc123`" in md
    assert "No demuestra productividad humana" in md