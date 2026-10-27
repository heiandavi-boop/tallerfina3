from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

import joblib
import pandas as pd
from ..features.team_health import compute_team_health


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = ROOT / "artifacts"
REGISTRY_PATH = ARTIFACT_ROOT / "model_registry.json"
ACTIVE_MODEL_PATH = ARTIFACT_ROOT / "active_model.json"
_LOCK = RLock()
_EMPIRICAL_CACHE: tuple[str, dict[str, Any], dict[str, Any]] | None = None


class ModelUnavailableError(ValueError):
    pass


def _read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"schema_version": 1, "default_model": "academic", "active_model": "academic", "models": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _record_for(model_id: str) -> dict[str, Any] | None:
    return next((model for model in _read_registry().get("models", []) if model.get("id") == model_id), None)


def _artifact_dir(record: dict[str, Any]) -> Path:
    candidate = (ROOT / str(record.get("artifact_path", ""))).resolve()
    if not candidate.is_relative_to(ARTIFACT_ROOT.resolve()):
        raise ModelUnavailableError("La ruta del artifact está fuera del directorio permitido.")
    return candidate


def _validate_artifact(record: dict[str, Any]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    artifact_dir = _artifact_dir(record)
    if not artifact_dir.is_dir():
        raise ModelUnavailableError("El artifact empírico no está disponible en este entorno.")
    required = ("checksums.json", "training_manifest.json", "metrics.json", "schema.json")
    if any(not (artifact_dir / name).is_file() for name in required):
        raise ModelUnavailableError("El artifact empírico está incompleto.")
    checksums_path = artifact_dir / "checksums.json"
    artifact_hash = record.get("artifact_hash")
    if artifact_hash and hashlib.sha256(checksums_path.read_bytes()).hexdigest() != artifact_hash:
        raise ModelUnavailableError("El checksum global del artifact no coincide.")
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    for filename, expected in checksums.items():
        path = (artifact_dir / filename).resolve()
        if not path.is_relative_to(artifact_dir.resolve()) or not path.is_file():
            raise ModelUnavailableError("El artifact contiene una ruta de checksum inválida.")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ModelUnavailableError(f"El checksum de {filename} no coincide.")
    manifest = json.loads((artifact_dir / "training_manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
    schema = json.loads((artifact_dir / "schema.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "completed" or not metrics or not schema.get("features"):
        raise ModelUnavailableError("El artifact no supera las validaciones de completitud.")
    return artifact_dir, metrics, schema


def _load_empirical(record: dict[str, Any]) -> dict[str, Any]:
    global _EMPIRICAL_CACHE
    artifact_dir, metrics, schema = _validate_artifact(record)
    cache_key = f"{record.get('version')}:{artifact_dir}"
    with _LOCK:
        if _EMPIRICAL_CACHE and _EMPIRICAL_CACHE[0] == cache_key:
            return _EMPIRICAL_CACHE[1]
        expected_targets = record.get("targets", [])
        models = {}
        for target in expected_targets:
            artifact = artifact_dir / f"{target}.joblib"
            if not artifact.is_file():
                raise ModelUnavailableError(f"Falta el modelo {target} en el artifact empírico.")
            models[target] = joblib.load(artifact)
        if not models:
            raise ModelUnavailableError("El artifact no contiene modelos cargables.")
        runtime = {"artifact_dir": artifact_dir, "metrics": metrics, "schema": schema, "models": models}
        _EMPIRICAL_CACHE = (cache_key, runtime, record)
        return runtime


def model_records(academic_runtime: Any) -> list[dict[str, Any]]:
    registry = _read_registry()
    stored = {item.get("id"): item for item in registry.get("models", [])}
    academic_metrics = academic_runtime.metrics
    official_metrics_path = ROOT / "reports" / "0.9.0-academic" / "metrics.json"
    if official_metrics_path.exists():
        academic_metrics = json.loads(official_metrics_path.read_text(encoding="utf-8"))
    academic = {
        "id": "academic",
        "name": "PRUNIN Academic",
        "version": academic_runtime.version,
        "source_type": "synthetic",
        "dataset_source": academic_runtime.metadata().get("dataset_source", "Mendeley Data synthetic"),
        "dataset_type": "synthetic_external",
        "status": "ready",
        "artifact_path": academic_runtime.metadata().get("artifact_dir"),
        "project_count": 4000,
        "snapshot_count": 72549,
        "features": academic_runtime.metadata().get("trained_features", []),
        "metrics": academic_metrics,
        "metric_level": "project-level",
        "targets": ["health", "delay_days", "cost_overrun_ratio"],
        "limitations": ["Synthetic external data; not a prospective business validation."],
    }
    empirical = stored.get("empirical") or {
        "id": "empirical",
        "name": "PRUNIN Empirical",
        "version": "1.0.0-empirical",
        "source_type": "real",
        "dataset_source": "DSLIB / PSLIB",
        "status": "not_trained",
        "artifact_path": "artifacts/1.0.0-empirical",
        "targets": [],
        "metrics": {},
    }
    empirical = {**empirical, "name": "PRUNIN Empirical"}
    if empirical.get("status") == "ready":
        try:
            artifact_dir, metrics, schema = _validate_artifact(empirical)
            empirical.update({"artifact_path": str(artifact_dir.relative_to(ROOT)), "metrics": metrics, "features": [item["name"] for item in schema["features"]], "targets": list(metrics)})
        except Exception as exc:
            empirical.update({"status": "unavailable", "availability_warning": str(exc)})
    empirical.setdefault("project_count", max((item.get("projects", 0) for item in empirical.get("metrics", {}).values()), default=0))
    empirical.setdefault("snapshot_count", max((item.get("snapshots", 0) for item in empirical.get("metrics", {}).values()), default=0))
    empirical.setdefault("limitations", ["Small observational sample; no Health label; snapshot EVM sample too sparse for training."])
    temporal_counts_path = ROOT / "reports" / "empirical" / "temporal_sample_counts.json"
    if temporal_counts_path.exists():
        temporal_counts = json.loads(temporal_counts_path.read_text(encoding="utf-8"))
        empirical["early_prediction"] = {
            "status": "not_available",
            "delay_candidate_projects": temporal_counts.get("delay", {}).get("projects", 0),
            "delay_candidate_snapshots": temporal_counts.get("delay", {}).get("snapshots", 0),
            "cost_candidate_projects": temporal_counts.get("cost", {}).get("projects", 0),
            "cost_candidate_snapshots": temporal_counts.get("cost", {}).get("snapshots", 0),
        }
    return [academic, empirical]


def get_active_model_id(academic_runtime: Any) -> tuple[str, str | None]:
    requested = os.getenv("PRUNIN_ACTIVE_MODEL")
    if requested is None and ACTIVE_MODEL_PATH.exists():
        try:
            requested = json.loads(ACTIVE_MODEL_PATH.read_text(encoding="utf-8")).get("model_id")
        except (OSError, json.JSONDecodeError):
            requested = None
    model_id = requested or "academic"
    if model_id == "academic":
        return "academic", None
    records = {record["id"]: record for record in model_records(academic_runtime)}
    record = records.get(model_id)
    if record and record.get("status") == "ready":
        try:
            _load_empirical(_record_for("empirical") or record)
            return model_id, None
        except Exception as exc:
            return "academic", f"Empirical model unavailable; Academic model remains active. {exc}"
    return "academic", "Empirical model unavailable; Academic model remains active."


def select_model(model_id: str, academic_runtime: Any) -> dict[str, Any]:
    records = {record["id"]: record for record in model_records(academic_runtime)}
    record = records.get(model_id)
    if record is None:
        raise ModelUnavailableError(f"Modelo desconocido: {model_id}.")
    if record.get("status") != "ready":
        raise ModelUnavailableError(f"El modelo {model_id} no está disponible para inferencia.")
    if model_id == "empirical":
        _load_empirical(_record_for("empirical") or record)
        environment_override = os.getenv("PRUNIN_ACTIVE_MODEL")
        if environment_override and environment_override != model_id:
            raise ModelUnavailableError(f"PRUNIN_ACTIVE_MODEL={environment_override} tiene prioridad sobre la selección manual.")
    ACTIVE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = ACTIVE_MODEL_PATH.with_suffix(".json.part")
    temporary_path.write_text(json.dumps({"model_id": model_id}, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(ACTIVE_MODEL_PATH)
    return {"active_model": model_id, "version": record["version"]}


def model_schema(model_id: str, academic_runtime: Any) -> dict[str, Any]:
    if model_id == "academic":
        return {
            "model_id": "academic",
            "version": academic_runtime.version,
            "features": academic_runtime.metadata().get("trained_features", []),
            "feature_manifest": academic_runtime.manifest,
            "targets": ["health", "delay_days", "cost_overrun_ratio"],
        }
    record = _record_for(model_id)
    if not record or record.get("status") != "ready":
        raise ModelUnavailableError(f"El esquema de {model_id} no está disponible.")
    return _validate_artifact(record)[2]


def predict_empirical(row: dict[str, Any], academic_runtime: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    record = _record_for("empirical")
    if not record or record.get("status") != "ready":
        raise ModelUnavailableError("El modelo empírico no está entrenado.")
    runtime = _load_empirical(record)
    duration_weeks = row.get("planned_duration_weeks")
    duration_days = row.get("planned_duration_days")
    if duration_days is None and duration_weeks is not None:
        duration_days = float(duration_weeks) * 7.0
    budget = row.get("planned_budget_bac")
    if budget is None:
        budget = row.get("planned_budget")
    if duration_days is None or budget is None:
        raise ValueError("El modelo empírico requiere planned_duration_weeks y planned_budget; no se imputan variables.")
    if float(duration_days) <= 0 or float(budget) <= 0:
        raise ValueError("La duración y el BAC deben ser mayores que cero para el modelo empírico.")
    features = pd.DataFrame([{"planned_duration_days": float(duration_days), "planned_budget_bac": float(budget)}])
    output: dict[str, Any] = {"health": None, "final_status": None, "health_status": "not_available_no_label"}
    if "delay" in runtime["models"]:
        raw_delay = float(runtime["models"]["delay"].predict(features)[0])
        output.update({"delay_days_raw": raw_delay, "delay_days": max(0.0, raw_delay)})
    if "cost" in runtime["models"]:
        output["cost_overrun_ratio"] = float(runtime["models"]["cost"].predict(features)[0])
    output["input_quality"] = {
        "trained_feature_count": len(runtime["schema"].get("features", [])),
        "coverage": 1.0,
        "minimum_coverage": 1.0,
        "missing_trained_features": [],
        "missing_count": 0,
        "complete": True,
    }
    output["team_health"] = compute_team_health(row, academic_runtime.config["team_health"]).to_dict()
    metadata = {
        "id": "empirical",
        "version": record["version"],
        "mode": "empirical_real_data",
        "execution": "LIVE",
        "dataset_source": record.get("dataset_source", "DSLIB / PSLIB"),
        "dataset_type": "empirical_real",
        "artifact_path": record["artifact_path"],
        "model_type": "validation-selected baseline/regressor",
        "trained_features": runtime["schema"].get("features", []),
        "health_available": False,
        "feature_adapter": {
            "planned_duration_weeks": "planned_duration_days = weeks * 7 calendar days",
            "planned_budget": "planned_budget_bac = BAC; same currency units supplied by caller",
        },
    }
    return output, metadata