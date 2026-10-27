from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..data.dslib import PROJECT_FEATURES, prepare_empirical_data


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = ROOT / "artifacts"
REPORT_ROOT = ROOT / "reports" / "empirical"
SEED = 42
MIN_PROJECTS_PER_TARGET = 30
TRAINING_LOCK = threading.Lock()
TARGETS = {
    "delay": {
        "column": "delay_days_raw",
        "unit": "days",
        "definition": "observed final actual duration - planned duration",
    },
    "cost": {
        "column": "cost_overrun_ratio",
        "unit": "ratio of BAC",
        "definition": "(observed final actual cost - BAC) / BAC",
    },
}


class EmpiricalTrainingError(RuntimeError):
    pass


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted, force_finite=True)) if len(actual) > 1 else 0.0,
    }


def split_project_indices(project_ids: list[str], seed: int = SEED) -> dict[str, list[int]]:
    indices = np.arange(len(project_ids))
    groups = np.asarray(project_ids)
    test_split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    train_validation, test = next(test_split.split(indices, groups=groups))
    inner_split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1)
    train_relative, validation_relative = next(
        inner_split.split(train_validation, groups=groups[train_validation])
    )
    train = train_validation[train_relative]
    validation = train_validation[validation_relative]
    split = {"train": train.tolist(), "validation": validation.tolist(), "test": test.tolist()}
    project_sets = {name: {project_ids[index] for index in values} for name, values in split.items()}
    if any(project_sets[left] & project_sets[right] for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise EmpiricalTrainingError("El split por proyecto produjo IDs compartidos.")
    return split


def _candidate_estimators() -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "median_baseline": DummyRegressor(strategy="median"),
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "random_forest": RandomForestRegressor(
            n_estimators=200,
            min_samples_leaf=2,
            random_state=SEED,
            n_jobs=1,
        ),
    }
    try:
        from lightgbm import LGBMRegressor

        candidates["lightgbm"] = LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=3,
            num_leaves=7,
            verbosity=-1,
            random_state=SEED,
            n_jobs=1,
        )
    except ImportError:
        pass
    return candidates


def _bootstrap_mae_interval(actual: np.ndarray, predicted: np.ndarray, seed: int = SEED) -> list[float] | None:
    if len(actual) < 10:
        return None
    generator = np.random.default_rng(seed)
    errors = []
    for _ in range(1000):
        indices = generator.integers(0, len(actual), len(actual))
        errors.append(float(np.mean(np.abs(actual[indices] - predicted[indices]))))
    lower, upper = np.quantile(errors, [0.025, 0.975])
    return [float(lower), float(upper)]


def _evaluate_target(frame: pd.DataFrame, target: str) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    rows = frame.dropna(subset=[*PROJECT_FEATURES, target]).copy()
    rows = rows[np.isfinite(rows[PROJECT_FEATURES + [target]]).all(axis=1)]
    if rows["project_id"].nunique() < MIN_PROJECTS_PER_TARGET:
        raise EmpiricalTrainingError(
            f"Solo {rows['project_id'].nunique()} proyectos tienen features baseline y target {target}; "
            f"se requieren al menos {MIN_PROJECTS_PER_TARGET} para train/validation/test agrupados."
        )

    rows = rows.sort_values("project_id").reset_index(drop=True)
    split = split_project_indices(rows["project_id"].astype(str).tolist())
    train_indices = np.asarray(split["train"], dtype=int)
    validation_indices = np.asarray(split["validation"], dtype=int)
    test_indices = np.asarray(split["test"], dtype=int)
    features = rows[PROJECT_FEATURES]
    actual = rows[target].to_numpy(dtype=float)
    candidates = _candidate_estimators()
    validation_results = []
    fitted_candidates: dict[str, Any] = {}
    for name, estimator in candidates.items():
        try:
            estimator.fit(features.iloc[train_indices], actual[train_indices])
            validation_prediction = estimator.predict(features.iloc[validation_indices])
            validation_results.append({"model": name, **regression_metrics(actual[validation_indices], validation_prediction)})
            fitted_candidates[name] = estimator
        except Exception as exc:
            validation_results.append({"model": name, "status": "failed", "error_type": type(exc).__name__})
    eligible = [item for item in validation_results if "mae" in item]
    if not eligible:
        raise EmpiricalTrainingError(f"Ningún candidato pudo entrenarse para {target}.")
    winner = min(eligible, key=lambda item: (item["mae"], item["model"]))["model"]

    final_model = _candidate_estimators()[winner]
    train_validation_indices = np.concatenate((train_indices, validation_indices))
    final_model.fit(features.iloc[train_validation_indices], actual[train_validation_indices])
    test_prediction = final_model.predict(features.iloc[test_indices])
    test_actual = actual[test_indices]
    baseline = DummyRegressor(strategy="median")
    baseline.fit(features.iloc[train_validation_indices], actual[train_validation_indices])
    baseline_metrics = regression_metrics(test_actual, baseline.predict(features.iloc[test_indices]))
    model_metrics = regression_metrics(test_actual, test_prediction)
    result = {
        "target": target,
        "unit": TARGETS["delay" if target == "delay_days_raw" else "cost"]["unit"],
        "definition": TARGETS["delay" if target == "delay_days_raw" else "cost"]["definition"],
        "projects": int(rows["project_id"].nunique()),
        "snapshots": 0,
        "selection_metric": "mae",
        "validation_candidates": validation_results,
        "selected_model": winner,
        "test": {
            **model_metrics,
            "baseline": baseline_metrics,
            "mae_bootstrap_95pct_interval": _bootstrap_mae_interval(test_actual, test_prediction),
            "test_projects": int(len(test_indices)),
        },
    }
    split_manifest = {
        name: rows.iloc[indices]["project_id"].astype(str).tolist()
        for name, indices in split.items()
    }
    prediction_rows = [
        {
            "project_id": rows.iloc[index]["project_id"],
            "target": target,
            "actual": float(actual[index]),
            "predicted": float(prediction),
            "residual": float(actual[index] - prediction),
            "split": "test",
        }
        for index, prediction in zip(test_indices, test_prediction)
    ]
    return final_model, {"metrics": result, "split": split_manifest}, prediction_rows


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_worktree_dirty() -> bool | None:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _training_code_hash() -> str:
    paths = [
        ROOT / "src" / "prunin_ai" / "training" / "empirical_training_service.py",
        ROOT / "src" / "prunin_ai" / "data" / "dslib.py",
        ROOT / "scripts" / "audit_dslib.py",
        ROOT / "scripts" / "audit_empirical_leakage.py",
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_data_audits() -> None:
    environment = os.environ.copy()
    project_paths = [str(ROOT / "src"), str(ROOT / "scripts")]
    if environment.get("PYTHONPATH"):
        project_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(project_paths)
    for script in ("audit_dslib.py", "audit_empirical_leakage.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise EmpiricalTrainingError(f"Falló la auditoría requerida {script}; entrenamiento bloqueado.")


def _next_artifact_version() -> str:
    versions = []
    for path in ARTIFACT_ROOT.glob("*-empirical"):
        match = __import__("re").fullmatch(r"(\d+)\.(\d+)\.(\d+)-empirical", path.name)
        if match:
            versions.append(tuple(map(int, match.groups())))
    next_version = (1, 0, 0) if not versions else (*max(versions)[:2], max(versions)[2] + 1)
    return f"{next_version[0]}.{next_version[1]}.{next_version[2]}-empirical"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_registry(version: str, artifact_path: Path, metrics: dict[str, Any], dataset_hash: str | None,
                    artifact_hash: str) -> None:
    registry_path = ARTIFACT_ROOT / "model_registry.json"
    academic = {
        "id": "academic",
        "version": "0.9.0-academic",
        "source_type": "synthetic",
        "dataset_source": "Mendeley Data 2p5sz57wh2 v2",
        "status": "ready",
        "artifact_path": "artifacts/0.9.0-academic",
        "targets": ["health", "delay_days", "cost_overrun_ratio"],
    }
    previous_versions = []
    if registry_path.exists():
        existing = json.loads(registry_path.read_text(encoding="utf-8"))
        for item in existing.get("models", []):
            if item.get("id") == "academic":
                academic = item
            elif item.get("id") == "empirical" and item.get("version") != version:
                previous_versions.append({**item, "id": f"empirical@{item.get('version')}", "status": "archived"})
            elif item.get("id") not in {"academic", "empirical"}:
                previous_versions.append(item)
    empirical = {
        "id": "empirical",
        "version": version,
        "source_type": "real",
        "dataset_source": "DSLIB / PSLIB v3.4",
        "dataset_hash": dataset_hash,
        "artifact_hash": artifact_hash,
        "status": "ready",
        "artifact_path": str(artifact_path.relative_to(ROOT)),
        "targets": sorted(metrics),
        "project_count": max((item.get("projects", 0) for item in metrics.values()), default=0),
        "snapshot_count": 0,
        "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    registry = {
        "schema_version": 1,
        "default_model": "academic",
        "active_model": "academic",
        "models": [academic, *previous_versions, empirical],
        "note": "Academic remains the default; empirical is not promoted automatically.",
    }
    _write_json(registry_path, registry)


def run_empirical_training(progress: Callable[[str, str], None] | None = None) -> dict[str, Any]:
    def update(stage: str, message: str) -> None:
        if progress:
            progress(stage, message)

    if not TRAINING_LOCK.acquire(blocking=False):
        raise EmpiricalTrainingError("Ya hay un entrenamiento empírico activo en este proceso.")
    lock_path = ARTIFACT_ROOT / ".empirical_training.lock"
    lock_fd: int | None = None
    staging: Path | None = None
    try:
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise EmpiricalTrainingError("Ya hay un entrenamiento empírico activo.") from exc

        update("preparing_data", "Preparando datos reales DSLIB v3.4.")
        prepared = prepare_empirical_data()
        update("auditing_data", "Verificando auditoría de cobertura y leakage.")
        _run_data_audits()
        leakage = json.loads((REPORT_ROOT / "leakage_audit.json").read_text(encoding="utf-8")) if (REPORT_ROOT / "leakage_audit.json").exists() else None
        if leakage is None or leakage.get("status") != "clear_after_filter":
            raise EmpiricalTrainingError("La auditoría de leakage no está disponible o no está aprobada; entrenamiento bloqueado.")
        dataset_audit = json.loads((REPORT_ROOT / "dslib_audit.json").read_text(encoding="utf-8"))
        temporal_sample_counts = json.loads((REPORT_ROOT / "temporal_sample_counts.json").read_text(encoding="utf-8"))
        update("feature_engineering", "Features limitadas a duración planificada y BAC observados.")

        samples_path = ROOT / "data" / "processed" / "dslib" / "model_samples.csv"
        frame = pd.read_csv(samples_path)
        for column in ("project_id", *PROJECT_FEATURES):
            if column not in frame:
                raise EmpiricalTrainingError(f"Falta la columna requerida {column} en el dataset procesado.")
        if frame["project_id"].duplicated().any():
            raise EmpiricalTrainingError("El dataset de entrenamiento contiene más de una fila por proyecto.")

        update("splitting", "Separando proyectos completos en train, validation y test.")
        update("training_health", "Health omitido: DSLIB no proporciona una etiqueta observada consistente.")
        trained: dict[str, Any] = {}
        results: dict[str, Any] = {}
        splits: dict[str, Any] = {}
        predictions: list[dict[str, Any]] = []
        for target_key, stage in (("delay", "training_delay"), ("cost", "training_cost")):
            target = TARGETS[target_key]["column"]
            update(stage, f"Evaluando candidatos para {target} con validación agrupada por proyecto.")
            model, target_result, target_predictions = _evaluate_target(frame, target)
            trained[target_key] = model
            results[target_key] = target_result["metrics"]
            splits[target_key] = target_result["split"]
            predictions.extend(target_predictions)

        update("evaluating", "Evaluación final única sobre el test congelado.")
        version = _next_artifact_version()
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        staging = ARTIFACT_ROOT / f".empirical-stage-{run_id}"
        staging.mkdir(parents=True, exist_ok=False)
        update("building_artifact", f"Construyendo artifact versionado {version}.")
        for target, model in trained.items():
            joblib.dump(model, staging / f"{target}.joblib")
        dataset_manifest_path = RAW_DIR / "dataset_manifest.json"
        dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
        schema = {
            "model_id": "empirical",
            "version": version,
            "features": [
                {"name": "planned_duration_days", "type": "number", "unit": "days", "required": True},
                {"name": "planned_budget_bac", "type": "number", "unit": "source currency units", "required": True},
            ],
            "targets": results,
            "health_available": False,
            "early_prediction": {"status": "not_available", "reason": "Only 13 leakage-cleared EVM snapshots per target."},
        }
        split_manifest = {
            "strategy": "two-stage GroupShuffleSplit",
            "group": "project_id",
            "seed": SEED,
            "targets": splits,
        }
        training_manifest = {
            "run_id": run_id,
            "artifact_version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "git_worktree_dirty": _git_worktree_dirty(),
            "training_code_sha256": _training_code_hash(),
            "dataset_hash": dataset_manifest.get("files", [{}])[0].get("sha256"),
            "dataset_version": dataset_manifest.get("version"),
            "seed": SEED,
            "config": {"features": PROJECT_FEATURES, "minimum_projects_per_target": MIN_PROJECTS_PER_TARGET},
            "status": "completed",
            "health_training": "not_available_no_consistent_observed_label",
            "prepared_project_count": prepared["project_count"],
            "split_project_counts": {target: {name: len(project_ids) for name, project_ids in split.items()} for target, split in splits.items()},
            "early_prediction": {"status": "not_available", "reason": "Only 13 leakage-cleared EVM snapshots per target."},
        }
        _write_json(staging / "schema.json", schema)
        _write_json(staging / "feature_manifest.json", {"features": PROJECT_FEATURES, "targets": list(TARGETS), "dataset_type": "empirical_real"})
        _write_json(staging / "dataset_manifest.json", dataset_manifest)
        _write_json(staging / "split_manifest.json", split_manifest)
        _write_json(staging / "training_manifest.json", training_manifest)
        _write_json(staging / "metrics.json", results)
        sample_counts = {
            "health": {"projects": 0, "snapshots": 0, "status": "not_available_no_consistent_label"},
            "delay": {
                "projects": results["delay"]["projects"],
                "snapshots": 0,
                "temporal_candidate_projects": temporal_sample_counts["delay"]["projects"],
                "temporal_candidate_snapshots": temporal_sample_counts["delay"]["snapshots"],
            },
            "cost": {
                "projects": results["cost"]["projects"],
                "snapshots": 0,
                "temporal_candidate_projects": temporal_sample_counts["cost"]["projects"],
                "temporal_candidate_snapshots": temporal_sample_counts["cost"]["snapshots"],
            },
        }
        _write_json(staging / "model_sample_counts.json", sample_counts)
        _write_json(REPORT_ROOT / "model_sample_counts.json", sample_counts)
        pd.DataFrame(predictions).to_csv(staging / "test_predictions.csv", index=False)
        pd.DataFrame(predictions).assign(residual=lambda data: data["actual"] - data["predicted"]).to_csv(staging / "test_residuals.csv", index=False)

        report_lines = [
            "# Empirical Training Report",
            "",
            f"- Version: **{version}**",
            f"- Run: `{run_id}`",
            f"- Dataset: DSLIB / PSLIB v3.4 ({prepared['project_count']} projects with baseline workbooks)",
            f"- Dataset SHA-256: `{training_manifest['dataset_hash']}`",
            f"- Seed: {SEED}; split by project_id; test reserved before model selection.",
            f"- Split sizes by target: {training_manifest['split_project_counts']}.",
            "- Health: not trained; no consistent observed Health label is available.",
            "- Features: planned duration (days), BAC; no synthetic features or inferred categories.",
            "",
            "## Dataset Audit Coverage",
            "",
            "| Variable | Projects available | Coverage |",
            "|---|---:|---:|",
            *[f"| {item['variable']} | {item['projects_available']} | {item['coverage_percent']:.2f}% |" for item in dataset_audit["coverage"]],
            "",
            f"Early prediction: **not_available**. Leakage-cleared EVM candidates: {temporal_sample_counts['delay']['projects']} projects / {temporal_sample_counts['delay']['snapshots']} snapshots per target, insufficient for reliable cutoff evaluation.",
            "",
            "## Results",
            "",
        ]
        for key, result in results.items():
            report_lines.extend([
                f"### {key.title()}",
                "",
                f"- Projects: {result['projects']}; target: {result['definition']}; unit: {result['unit']}",
                f"- Selected on validation MAE: {result['selected_model']}",
                "- Validation candidates (MAE / RMSE / R²):",
                *[f"  - {candidate['model']}: {candidate.get('mae', 'failed')} / {candidate.get('rmse', '—')} / {candidate.get('r2', '—')}" for candidate in result["validation_candidates"]],
                f"- Test: MAE {result['test']['mae']:.6g}, RMSE {result['test']['rmse']:.6g}, R² {result['test']['r2']:.6g}",
                f"- Median baseline test MAE: {result['test']['baseline']['mae']:.6g}",
                f"- Test MAE bootstrap interval: {result['test']['mae_bootstrap_95pct_interval']}",
                "",
            ])
        report_lines.extend([
            "## Limitations",
            "",
            "- Small, heterogeneous observational sample; no causal claims or external generalization established.",
            "- Only project-baseline features were used; temporal EVM snapshots are too sparse for training in this release.",
            "- The selected median estimator has no feature importance or local sensitivity drivers.",
            "- Delay and cost metrics describe DSLIB's own target/split and cannot be ranked head-to-head against the academic dataset.",
        ])
        (staging / "training_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        checksums = {}
        for path in sorted(staging.iterdir()):
            if path.is_file():
                checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        _write_json(staging / "checksums.json", checksums)
        final_path = ARTIFACT_ROOT / version
        if final_path.exists():
            raise EmpiricalTrainingError(f"El artifact destino ya existe y no se sobrescribirá: {version}.")
        staging.replace(final_path)
        staging = None
        artifact_hash = hashlib.sha256((final_path / "checksums.json").read_bytes()).hexdigest()
        _write_registry(version, final_path, results, training_manifest["dataset_hash"], artifact_hash)

        run_dir = REPORT_ROOT / "training_runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_json(run_dir / f"{run_id}.json", {**training_manifest, "metrics": results, "status": "completed"})
        report_path = REPORT_ROOT / "training_report.md"
        report_path.write_text((final_path / "training_report.md").read_text(encoding="utf-8"), encoding="utf-8")
        update("completed", f"Entrenamiento completado. {version} quedó listo, sin promoción automática.")
        return {
            "run_id": run_id,
            "version": version,
            "status": "completed",
            "artifact_path": str(final_path.relative_to(ROOT)),
            "metrics": results,
            "health_available": False,
            "active_model": "academic",
        }
    except Exception:
        if staging and staging.exists():
            import shutil

            shutil.rmtree(staging)
        raise
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            lock_path.unlink(missing_ok=True)
        TRAINING_LOCK.release()


def RAW_DIR_PATH() -> Path:
    return ROOT / "data" / "raw" / "dslib"


RAW_DIR = RAW_DIR_PATH()