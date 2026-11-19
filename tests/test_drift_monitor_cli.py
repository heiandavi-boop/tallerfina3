import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_drift.py"
SPEC = importlib.util.spec_from_file_location("check_drift_cli", SCRIPT)
CHECK_DRIFT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_DRIFT)


def _fixture(tmp_path):
    artifact = tmp_path / "academic-test"
    artifact.mkdir()
    (artifact / "feature_manifest.json").write_text(json.dumps({
        "numeric_features": ["spi"],
        "categorical_features": ["project_type"],
    }))
    (artifact / "split_manifest.json").write_text(json.dumps({
        "train": ["train-1", "train-2"],
        "validation": ["validation-1"],
        "test": ["test-1"],
    }))
    source = tmp_path / "reference.csv"
    pd.DataFrame({
        "project_id": ["train-1", "train-2", "validation-1", "test-1"],
        "spi": [0.9, 1.1, 2.0, 3.0],
        "project_type": ["it", "build", "it", "build"],
    }).to_csv(source, index=False)
    batch = tmp_path / "batch.csv"
    pd.DataFrame({
        "project_id": ["new-1", "new-2"],
        "spi": [10.0, 11.0],
        "project_type": ["unknown", "unknown"],
    }).to_csv(batch, index=False)
    return artifact, source, batch


def test_monitor_writes_timestamped_alert_without_modifying_academic_artifact(tmp_path, capsys):
    artifact, source, batch = _fixture(tmp_path)
    output = tmp_path / "monitor-output"

    code = CHECK_DRIFT.main([
        "--artifact", str(artifact),
        "--input", str(source),
        "--batch", str(batch),
        "--output-dir", str(output),
        "--fail-on-alert",
    ])

    report = json.loads(capsys.readouterr().out)
    assert code == 2
    assert report["alert"] is True
    assert report["retraining_triggered"] is False
    assert report["generated_at_utc"]
    assert report["input_hashes"]["current_batch_sha256"]
    assert set(report["alert_features"]) == {"project_type", "spi"}
    assert Path(report["report_path"]).is_file()
    assert not (artifact / "input_profile.json").exists()


def test_monitor_flags_missing_feature_column(tmp_path, capsys):
    artifact, source, batch = _fixture(tmp_path)
    pd.DataFrame({"project_id": ["new-1"], "spi": [1.0]}).to_csv(batch, index=False)

    code = CHECK_DRIFT.main([
        "--artifact", str(artifact),
        "--input", str(source),
        "--batch", str(batch),
        "--output-dir", str(tmp_path / "monitor-output"),
    ])

    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["alert"] is True
    assert report["data_quality"]["missing_feature_columns"] == ["project_type"]
    assert report["data_quality"]["missing_schema_alert"] is True
