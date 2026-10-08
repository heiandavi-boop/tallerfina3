import json
import sys
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import download_datasets
import data_readiness
from verify_split import verify_and_save_split
from prunin_ai.data.local_input import require_local_training_input
from prunin_ai.constants import CATEGORICAL_FEATURES, CORE_TEMPORAL_FEATURES, STATIC_NUMERIC_FEATURES
from prunin_ai.training.core import _feature_sets


def test_training_input_rejects_remote_urls_and_raw_files(tmp_path):
    with pytest.raises(ValueError, match="URLs"):
        require_local_training_input("https://example.test/data.csv", tmp_path)

    raw = tmp_path / "data/raw/source.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("project_id\nP1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="data/raw"):
        require_local_training_input(str(raw), tmp_path)


def test_training_input_accepts_an_existing_processed_file(tmp_path):
    processed = tmp_path / "data/processed/model_input.csv"
    processed.parent.mkdir(parents=True)
    processed.write_text("project_id\nP1\n", encoding="utf-8")

    assert require_local_training_input("data/processed/model_input.csv", tmp_path) == processed


def test_train_core_cli_rejects_remote_input_before_training():
    version = "remote-input-rejected-test"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/train_core.py"), "--input",
         "https://example.invalid/data.csv", "--version", version],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert "solo acepta archivos locales" in result.stderr
    assert not (ROOT / "artifacts" / version).exists()


def test_local_validation_requires_download_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(download_datasets, "MANIFEST_PATH", tmp_path / "dataset_manifest.json")

    with pytest.raises(RuntimeError, match="Falta manifest"):
        download_datasets.validate_local_datasets()


def test_mendeley_file_urls_are_resolved_from_current_metadata():
    metadata = {
        "files": [{
            "filename": "project_risk_raw_dataset.csv",
            "id": "current-id",
            "content_details": {
                "download_url": "https://data.mendeley.com/public-files/current-id",
                "sha256_hash": "abc123",
                "size": 42,
            },
        }]
    }

    files = download_datasets._mendeley_downloads(metadata, {"project_risk_raw_dataset.csv"})

    assert files["project_risk_raw_dataset.csv"]["id"] == "current-id"
    assert files["project_risk_raw_dataset.csv"]["content_details"]["download_url"].endswith("current-id")


def test_valid_local_dataset_is_reused_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(download_datasets, "ROOT", tmp_path)
    local_file = tmp_path / "data/processed/cached.csv"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("project_id\nP1\n", encoding="utf-8")
    fingerprint = "source-v1"
    old_record = download_datasets._record(
        "test", "https://example.test", "doi:test", "version 1", "cached.csv",
        local_file, "https://example.test/cached.csv", "text/csv", "CC BY 4.0",
        False, fingerprint,
    )

    def unexpected_request(*args, **kwargs):
        raise AssertionError("Una caché válida no debe generar una descarga")

    monkeypatch.setattr(download_datasets.requests, "get", unexpected_request)
    records = []
    download_datasets._download_one(
        {"files": [old_record]}, records, dataset="test", landing_page="https://example.test",
        doi="doi:test", record="version 1", filename="cached.csv", path=local_file,
        url="https://example.test/cached.csv", license_name="CC BY 4.0", synthetic=False,
        fingerprint=fingerprint,
    )

    assert records == [old_record]


def test_invalid_csv_schema_is_rejected(tmp_path):
    file_path = tmp_path / "dataset.csv"
    file_path.write_text("name,value\nP1,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Esquema inválido"):
        download_datasets._valid_file(file_path, file_path.name, ("project_id|projectid",))


def test_mendeley_xlsx_csv_in_a_single_cell_passes_schema_validation(tmp_path):
    from openpyxl import Workbook

    file_path = tmp_path / "timeseries.csv.xlsx"
    workbook = Workbook()
    workbook.active.append(["Project_ID,Month,PV,EV,AC"])
    workbook.active.append(["P1,1,10,9,11"])
    workbook.save(file_path)

    download_datasets._valid_file(
        file_path, file_path.name,
        ("projectid|project_id|project", "pv|plannedvalue", "ev|earnedvalue", "ac|actualcost"),
    )


def test_parquet_schema_is_read_from_metadata_without_loading_rows(tmp_path):
    import pyarrow as arrow
    import pyarrow.parquet as parquet

    file_path = tmp_path / "itemlet_dataset.parquet"
    parquet.write_table(arrow.table({"project_id": ["P1"], "issue_type": ["bug"]}), file_path)

    download_datasets._valid_file(file_path, file_path.name)
    assert parquet.read_schema(file_path).names == ["project_id", "issue_type"]


def test_collaboration_candidate_mapping_only_marks_methodologically_valid_metrics():
    assert download_datasets._collaboration_feature_signals(
        "dataset/collaboration_metrics/teamMetrics_PT2160H_repo.csv"
    ) == ["team_size", "team_expertise", "core_contribution"]
    assert download_datasets._collaboration_feature_signals(
        "dataset/delivery_indicators/deliverySize_PT2160H_repo.csv"
    ) == ["delivery_size"]
    assert download_datasets._collaboration_feature_signals(
        "dataset/repositories/repo.json"
    ) == []


def _ready_fixture(tmp_path):
    project_count = 100
    rows = project_count * 5
    df = pd.DataFrame({
        "project_id": [f"mendeley::P{i // 5:04d}" for i in range(rows)],
        "source_project_id": [f"P{i // 5:04d}" for i in range(rows)],
        "data_source": ["mendeley_2p5sz57wh2_v2"] * rows,
        "is_synthetic": [True] * rows,
        "health": ["healthy", "at_risk", "critical", "healthy", "at_risk"] * project_count,
        "final_status": ["successful", "challenged", "critical", "successful", "challenged"] * project_count,
        "delay_days": [1.0] * rows,
        "cost_overrun_ratio": [0.01] * rows,
    })
    input_path = tmp_path / "mendeley_core.csv"
    df.to_csv(input_path, index=False)
    manifest = {"files": [
        {"dataset": "mendeley_evm", "local_path": path, "doi": data_readiness.MAIN_DOI,
         "record/version": "version 2", "synthetic": True, "validation_status": "valid"}
        for path in data_readiness.MAIN_FILES
    ]}
    audit = {
        "rows": rows, "projects": project_count,
        "feature_coverage": {name: 1.0 for name in
                             STATIC_NUMERIC_FEATURES + CATEGORICAL_FEATURES + CORE_TEMPORAL_FEATURES},
        "target_coverage": {name: 1.0 for name in data_readiness.TARGET_COLUMNS},
    }
    return df, input_path, manifest, audit


def test_readiness_keeps_mendeley_primary_and_optional_sources_as_warnings(tmp_path):
    df, input_path, manifest, audit = _ready_fixture(tmp_path)

    readiness = data_readiness.build_readiness(df, audit, manifest, input_path)

    assert readiness["main_dataset_valid"] is True
    assert readiness["blocking_errors"] == []
    assert readiness["ready_for_training"] is True
    assert readiness["leakage_check"]["status"] == "pending"
    assert {"itemlet", "collaboration", "squad"} <= set(readiness["datasets_missing"])
    assert len(readiness["warnings"]) == 3
    assert readiness["synthetic_sources"] == ["mendeley_evm"]
    assert readiness["real_sources"] == []


def test_readiness_blocks_when_a_required_mendeley_file_is_missing(tmp_path):
    df, input_path, manifest, audit = _ready_fixture(tmp_path)
    manifest["files"].pop()

    readiness = data_readiness.build_readiness(df, audit, manifest, input_path)

    assert readiness["main_dataset_valid"] is False
    assert readiness["blocking_errors"]
    assert readiness["ready_for_training"] is False


def test_optional_download_failure_warns_without_raising(capsys):
    statuses = {}
    warnings = []

    def fail_optional_source():
        raise RuntimeError("service unavailable")

    download_datasets._optional_download(
        "itemlet", fail_optional_source, [], statuses, warnings
    )

    assert statuses["itemlet"] == "unavailable"
    assert warnings == ["itemlet: service unavailable"]
    assert "[WARN] Optional dataset unavailable" in capsys.readouterr().out


def test_feature_whitelist_excludes_direct_target_columns():
    df = pd.DataFrame({
        "project_id": ["mendeley::P1"], "planned_duration_weeks": [10.0],
        "spi": [0.9], "cpi": [0.95], "health": ["at_risk"],
        "final_status": ["challenged"], "delay_days": [30.0],
        "cost_overrun_ratio": [0.1],
    })

    numeric, categorical = _feature_sets(df)

    assert not ({"health", "final_status", "delay_days", "cost_overrun_ratio"} & set(numeric + categorical))


def test_verified_split_updates_readiness_before_training(tmp_path):
    _, input_path, manifest, audit = _ready_fixture(tmp_path)
    df = pd.read_csv(input_path)
    readiness = data_readiness.build_readiness(df, audit, manifest, input_path)
    readiness_path = tmp_path / "artifacts/data_readiness.json"
    data_readiness.write_readiness(readiness, readiness_path)

    split = verify_and_save_split(input_path, tmp_path / "model-artifacts", readiness_path)
    updated = json.loads(readiness_path.read_text(encoding="utf-8"))

    assert set(split) == {"train", "validation", "test"}
    assert set(split["train"]).isdisjoint(split["validation"])
    assert set(split["train"]).isdisjoint(split["test"])
    assert set(split["validation"]).isdisjoint(split["test"])
    assert updated["leakage_check"]["status"] == "passed"
    assert updated["ready_for_training"] is True


def test_academic_cli_blocks_without_readiness_and_split(tmp_path):
    input_path = tmp_path / "mendeley_core.csv"
    input_path.write_text("project_id\nmendeley::P1\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/train_core.py"), "--input",
         str(input_path), "--version", "0.9.0-academic"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert "TRAINING BLOCKED" in result.stderr