"""CLI for the local model registry and the gated retraining pipeline.

Examples:
  python scripts/mlops_pipeline.py init-registry
  python scripts/mlops_pipeline.py demo-cycle            # blocked: requires --authorize
  python scripts/mlops_pipeline.py demo-cycle --authorize
  python scripts/mlops_pipeline.py approve --version demo-candidate-2026 --approver "Nombre"
  python scripts/mlops_pipeline.py select-for-deployment --version candidate-version
  python scripts/mlops_pipeline.py rollback-selection
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from prunin_ai.config import load_config  # noqa: E402
from prunin_ai.data.demo import generate_demo  # noqa: E402
from prunin_ai.features.team_health import compute_team_health  # noqa: E402
from prunin_ai.monitoring.mlops import (  # noqa: E402
    ModelRegistry, RetrainingBlocked, run_retraining, sha256_file,
)

DEFAULT_REGISTRY = ROOT / "reports/mlops/model_registry.json"


def _hashes(directory: Path) -> dict[str, str]:
    return {p.name: sha256_file(p) for p in sorted(directory.glob("*.joblib"))}


def init_registry(registry: ModelRegistry) -> None:
    academic_metrics = json.loads((ROOT / "reports/0.9.0-academic/metrics.json").read_text(encoding="utf-8"))
    row_metrics = {
        "health": academic_metrics["health"]["test"],
        "delay_days": academic_metrics["delay_days"]["test"],
        "cost_overrun_ratio": academic_metrics["cost_overrun_ratio"]["test"],
    }
    project_metrics = {
        target: academic_metrics[target]["project_level_metrics"]["test"]
        for target in ("health", "delay_days", "cost_overrun_ratio")
    }
    readiness = json.loads((ROOT / "reports/0.9.0-academic/data_readiness.json").read_text(encoding="utf-8"))
    split_path = ROOT / "artifacts/0.9.0-academic/split_manifest.json"
    config = yaml.safe_load((ROOT / "configs/training.yaml").read_text(encoding="utf-8"))
    academic_dir = ROOT / "artifacts/0.9.0-academic"
    academic_entry = {
        "name": "prunin-core",
        "version": "0.9.0-academic",
        "algorithm": "LightGBM (health classifier, delay/cost regressors)",
        "dataset": {
            "data_source": "mendeley_2p5sz57wh2_v2",
            "sha256": readiness.get("processed_sha256"),
            "path": "data/processed/mendeley_core.csv",
        },
        "configuration": {
            "random_seed": config.get("random_seed"),
            "split_manifest_sha256": sha256_file(split_path) if split_path.is_file() else None,
            "metrics_source": "reports/0.9.0-academic/metrics.json",
        },
        "metrics": {
            "holdout": "TEST (frozen; never used for candidate selection)",
            "row_level_snapshot_metrics": row_metrics,
            "project_level_latest_snapshot_metrics": project_metrics,
        },
        "artifact_hashes": _hashes(academic_dir) if academic_dir.is_dir() else {},
        "status": "frozen_academic",
        "freeze_basis": "Preserved academic baseline; registry status is not an institutional approval.",
        "approval": None,
    }
    academic = registry.get("0.9.0-academic")
    if academic is None:
        registry.register(academic_entry)
    else:
        if any(academic.get(key) != value for key, value in academic_entry.items()):
            academic.update(academic_entry)
            registry._event(
                "metadata_corrected",
                "0.9.0-academic",
                note="Separated snapshot-row and project-level TEST metrics; removed unsupported approval attribution.",
            )

    demo_dir = ROOT / "artifacts/demo-0.1.0"
    if demo_dir.is_dir():
        demo_entry = {
            "name": "prunin-core",
            "version": "demo-0.1.0",
            "algorithm": "LightGBM (health classifier, delay/cost regressors)",
            "dataset": {"data_source": "demo_synthetic_smoke_test", "generator_seed": 42},
            "metrics": {"evaluation_split": "synthetic demonstration; see artifacts/demo-0.1.0/metrics.json"},
            "artifact_hashes": _hashes(demo_dir),
            "status": "demo_available",
            "approval": None,
        }
        demo = registry.get("demo-0.1.0")
        if demo is None:
            registry.register(demo_entry)
        elif any(demo.get(key) != value for key, value in demo_entry.items()):
            demo.update(demo_entry)
            registry._event(
                "metadata_corrected",
                "demo-0.1.0",
                note="Reclassified demo artifact; no production deployment was verified.",
            )
        registry.data.setdefault("deployments", {"demo": None, "test": None, "production": None})
        registry.data["deployments"]["demo"] = "demo-0.1.0"
        registry.data["deployments"]["production"] = None
        registry.data["deployments"]["test"] = None
    registry.save()


def build_synthetic_dataset(path: Path, seed: int, projects: int, cfg: dict) -> Path:
    frame = generate_demo(projects=projects, seed=seed)
    frame["data_source"] = f"demo_synthetic_retraining_seed{seed}"
    frame["team_health_index"] = frame.apply(lambda r: compute_team_health(r.to_dict(), cfg["team_health"]).score, axis=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    provenance = {
        "authorized": True, "data_source": frame["data_source"].iloc[0], "sha256": sha256_file(path),
        "generator": "prunin_ai.data.demo.generate_demo", "seed": seed, "projects": projects,
        "note": "Datos sintéticos de demostración, separados del experimento académico Mendeley.",
    }
    provenance_path = path.with_suffix(".provenance.json")
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "command",
        choices=["init-registry", "demo-cycle", "approve", "select-for-deployment", "rollback-selection", "show"],
    )
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--authorize", action="store_true", help="Habilita explícitamente el reentrenamiento.")
    ap.add_argument("--version", default="demo-candidate-2026")
    ap.add_argument("--approver", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--projects", type=int, default=400)
    ap.add_argument("--work-dir", default=str(ROOT / "artifacts/candidates"))
    args = ap.parse_args(argv)

    registry = ModelRegistry(args.registry)
    try:
        if args.command == "init-registry":
            init_registry(registry)
        elif args.command == "demo-cycle":
            if not args.authorize:
                raise RetrainingBlocked("Reentrenamiento bloqueado por defecto: use --authorize con un dataset aprobado.")
            cfg = load_config(ROOT / "configs/training.yaml")
            work = Path(args.work_dir)
            dataset = work / f"retraining_seed{args.seed}.csv"
            provenance = build_synthetic_dataset(dataset, args.seed, args.projects, cfg)
            reference = ROOT / "data/processed/demo_core.csv"
            result = run_retraining(
                dataset_path=dataset, provenance_path=provenance,
                baseline_dir=ROOT / "artifacts/demo-0.1.0", baseline_version="demo-0.1.0",
                candidate_version=args.version, candidates_root=work, registry=registry, cfg=cfg,
                authorized=True,
                reference_frame=pd.read_csv(reference, low_memory=False) if reference.is_file() else None,
            )
            registry.save()
            print(json.dumps(result["record"]["gate"], indent=2))
            print(f"status={result['record']['status']}")
        elif args.command == "approve":
            registry.approve(args.version, args.approver, args.note)
            registry.save()
        elif args.command == "select-for-deployment":
            registry.select_for_deployment(args.version)
            registry.save()
        elif args.command == "rollback-selection":
            print(f"selected_for_deployment={registry.rollback_selection()}")
            registry.save()
        print(json.dumps({
            "deployments": registry.data.get("deployments"),
            "selected_for_deployment": registry.data.get("selected_for_deployment"),
            "models": {m["version"]: m["status"] for m in registry.data["models"]},
        }, indent=2))
    except (RetrainingBlocked, PermissionError, KeyError, ValueError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
