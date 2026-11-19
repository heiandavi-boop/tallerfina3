import json

import pytest

from scripts.mlops_pipeline import init_registry
from prunin_ai.config import load_config
from prunin_ai.data.demo import generate_demo
from prunin_ai.features.team_health import compute_team_health
from prunin_ai.monitoring.mlops import (
    ModelRegistry, RetrainingBlocked, regression_gate, run_retraining, sha256_file,
)
from prunin_ai.targets import add_targets
from prunin_ai.training.core import train_core


@pytest.fixture(scope="module")
def cfg():
    return load_config("configs/training.yaml")


def _dataset(tmp_path, cfg, seed, name, source="demo_synthetic_test"):
    frame = generate_demo(projects=60, snapshots=4, seed=seed)
    frame["data_source"] = source
    frame["team_health_index"] = frame.apply(lambda r: compute_team_health(r.to_dict(), cfg["team_health"]).score, axis=1)
    path = tmp_path / f"{name}.csv"
    frame.to_csv(path, index=False)
    prov = tmp_path / f"{name}.provenance.json"
    prov.write_text(json.dumps({"authorized": True, "sha256": sha256_file(path), "data_source": source}))
    return frame, path, prov


def test_registry_rejects_overwriting_frozen_version(tmp_path):
    registry = ModelRegistry(tmp_path / "r.json")
    entry = {"name": "m", "version": "0.9.0-academic", "algorithm": "x", "dataset": {}, "metrics": {}, "status": "frozen_academic"}
    registry.register(entry)
    with pytest.raises(PermissionError):
        registry.register(entry)


def test_registry_migration_does_not_claim_demo_is_production(tmp_path):
    registry_path = tmp_path / "legacy.json"
    registry_path.write_text(json.dumps({
        "schema_version": 1,
        "production": "demo-0.1.0",
        "models": [
            {"version": "0.9.0-academic", "status": "frozen_academic",
             "approval": {"approver": "comité académico PAIII"}},
            {"version": "demo-0.1.0", "status": "production"},
        ],
        "events": [],
    }))
    registry = ModelRegistry(registry_path)
    assert registry.data["schema_version"] == 2
    assert registry.data["deployments"] == {"demo": "demo-0.1.0", "test": None, "production": None}
    assert registry.data["selected_for_deployment"] is None
    assert registry.get("demo-0.1.0")["status"] == "demo_available"


def test_init_registry_uses_both_academic_metric_units_and_no_false_approval(tmp_path):
    registry = ModelRegistry(tmp_path / "registry.json")
    init_registry(registry)
    academic = registry.get("0.9.0-academic")
    assert academic["approval"] is None
    assert academic["status"] == "frozen_academic"
    assert academic["metrics"]["holdout"].startswith("TEST")
    assert academic["metrics"]["row_level_snapshot_metrics"]["health"]["macro_f1"] == pytest.approx(0.5470548202603385)
    assert academic["metrics"]["project_level_latest_snapshot_metrics"]["health"]["macro_f1"] == pytest.approx(0.6275758334320115)
    assert academic["metrics"]["project_level_latest_snapshot_metrics"]["delay_days"]["mae"] == pytest.approx(27.71046834259029)
    assert academic["metrics"]["project_level_latest_snapshot_metrics"]["cost_overrun_ratio"]["r2"] == pytest.approx(0.9918156958562626)
    assert registry.get("demo-0.1.0")["status"] == "demo_available"
    assert registry.data["deployments"]["production"] is None


def test_regression_gate_blocks_degradation():
    baseline = {"health": 0.60, "delay_days": 20.0, "cost_overrun_ratio": 0.05}
    assert regression_gate({"health": 0.61, "delay_days": 19.0, "cost_overrun_ratio": 0.05}, baseline)["passed"]
    worse = regression_gate({"health": 0.50, "delay_days": 19.0, "cost_overrun_ratio": 0.05}, baseline)
    assert not worse["passed"] and not worse["checks"]["health"]["passed"]


def test_retraining_blocked_without_authorization_or_valid_provenance(tmp_path, cfg):
    _, path, prov = _dataset(tmp_path, cfg, 7, "new")
    common = dict(dataset_path=path, baseline_dir=tmp_path, baseline_version="b", candidate_version="c",
                  candidates_root=tmp_path / "cand", registry=ModelRegistry(tmp_path / "r.json"), cfg=cfg)
    with pytest.raises(RetrainingBlocked):
        run_retraining(provenance_path=prov, **common)
    with pytest.raises(RetrainingBlocked):
        run_retraining(provenance_path=None, authorized=True, **common)
    prov.write_text(json.dumps({"authorized": True, "sha256": "0" * 64}))
    with pytest.raises(RetrainingBlocked, match="hash"):
        run_retraining(provenance_path=prov, authorized=True, **common)
    with pytest.raises(RetrainingBlocked):
        run_retraining(provenance_path=prov, authorized=True, **{**common, "candidate_version": "0.9.0-academic"})


def test_full_cycle_gate_approval_promotion_and_rollback(tmp_path, cfg):
    base_frame, _, _ = _dataset(tmp_path, cfg, 1, "base")
    train_core(add_targets(base_frame, cfg["target_rules"]), cfg, tmp_path / "baseline")
    _, path, prov = _dataset(tmp_path, cfg, 2, "new")
    registry = ModelRegistry(tmp_path / "r.json")
    registry.register({"name": "m", "version": "base", "algorithm": "x", "dataset": {}, "metrics": {}, "status": "approved"})
    registry.data["selected_for_deployment"] = "base"

    result = run_retraining(
        dataset_path=path, provenance_path=prov, baseline_dir=tmp_path / "baseline", baseline_version="base",
        candidate_version="cand-1", candidates_root=tmp_path / "cand", registry=registry, cfg=cfg,
        authorized=True, reference_frame=base_frame, tolerance=10.0,
    )
    record = result["record"]
    assert record["status"] == "candidate_passed_gate"
    assert set(record["metrics"]["candidate"]) == {"health", "delay_days", "cost_overrun_ratio"}
    assert record["metrics"]["evaluation_split"].startswith("VALIDATION")
    assert record["trigger"] is not None and "max_psi" in record["trigger"]

    with pytest.raises(RetrainingBlocked):
        registry.select_for_deployment("cand-1")
    registry.approve("cand-1", "revisor")
    registry.select_for_deployment("cand-1")
    assert registry.data["selected_for_deployment"] == "cand-1"
    assert registry.data.get("deployments", {}).get("production") is None
    assert registry.rollback_selection() == "base"
    assert registry.data["selected_for_deployment"] == "base"
    assert [e["action"] for e in registry.data["events"]][-3:] == ["approve", "select_for_deployment", "rollback_selection"]
