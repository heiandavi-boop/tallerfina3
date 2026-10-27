from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd
import qrcode
import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .catalog import PRESETS
from .model_runtime import ModelRuntime, ROOT, unused_what_if_changes
from .recommendations import build_recommendations, check_ollama_status, recommendations_not_requested, warmup_ollama
from .monitoring import monitoring
from .schema import ProjectInput, WhatIfRequest
from .model_registry import (
    ModelUnavailableError,
    get_active_model_id,
    model_records,
    model_schema,
    predict_empirical,
    select_model,
)
from ..training.empirical_training_service import EmpiricalTrainingError, run_empirical_training

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        runtime.brain.predict(PRESETS["at_risk"])
    except Exception:
        pass
    if os.getenv("PRUNIN_OLLAMA_WARMUP", "0") == "1":
        warmup_result = warmup_ollama()
        logger.info(json.dumps({"event": "ollama_warmup", "ok": warmup_result.get("ok"), "failure_code": warmup_result.get("failure_code")}))
    yield


app = FastAPI(title="PRUNIN AI Core Playground", version="1.0.0", lifespan=lifespan)
cors_origins = [item.strip() for item in os.getenv("PRUNIN_CORS_ORIGINS", "*").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins or ["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
runtime = ModelRuntime()
logger = logging.getLogger("prunin.inference")
training_jobs: dict[str, dict[str, Any]] = {}
training_jobs_lock = Lock()
training_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prunin-empirical")
TRAINING_PROGRESS = {
    "queued": 0,
    "preparing_data": 10,
    "auditing_data": 20,
    "feature_engineering": 30,
    "splitting": 40,
    "training_health": 45,
    "training_delay": 60,
    "training_cost": 75,
    "evaluating": 88,
    "building_artifact": 96,
    "completed": 100,
    "failed": 100,
}


class ModelSelectionRequest(BaseModel):
    model_id: str


def _update_training_job(job_id: str, stage: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with training_jobs_lock:
        job = training_jobs[job_id]
        job.update({
            "status": stage,
            "progress_percent": TRAINING_PROGRESS.get(stage, job["progress_percent"]),
            "current_step": message,
            "updated_at": timestamp,
        })
        job["events"].append({"timestamp": timestamp, "status": stage, "message": message})


def _run_training_job(job_id: str) -> None:
    try:
        result = run_empirical_training(lambda stage, message: _update_training_job(job_id, stage, message))
        with training_jobs_lock:
            job = training_jobs[job_id]
            job["result"] = result
            job["status"] = "completed"
            job["progress_percent"] = 100
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        message = str(exc) if isinstance(exc, EmpiricalTrainingError) else "El entrenamiento falló; revise el reporte técnico del run."
        with training_jobs_lock:
            job = training_jobs[job_id]
            job.update({"status": "failed", "progress_percent": 100, "error": message, "updated_at": datetime.now(timezone.utc).isoformat()})
            job["events"].append({"timestamp": job["updated_at"], "status": "failed", "message": message})
        logger.exception("Empirical training job %s failed", job_id)


def serialize(value: Any):
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def run_prediction(data: dict[str, Any], *, include_recommendations: bool = True,
                   model_id: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    prediction_id = str(uuid.uuid4())
    selected_model, selection_warning = get_active_model_id(runtime) if model_id is None else (model_id, None)
    try:
        if selected_model == "empirical":
            try:
                pred, model_metadata = predict_empirical(data, runtime)
                drivers = []
                recommendations = ({
                    "engine": "not_available_for_empirical_targets",
                    "genai_attempted": False,
                    "genai_used": False,
                    "failure_code": None,
                    "actions": [],
                    "message": "Health no tiene etiqueta empírica validada; no se generan recomendaciones grounded.",
                } if include_recommendations else recommendations_not_requested())
            except ModelUnavailableError as exc:
                selected_model = "academic"
                selection_warning = f"Empirical model unavailable; Academic model remains active. {exc}"
                pred = runtime.predict(data)
                drivers = runtime.local_drivers(data, pred)
                model_metadata = runtime.metadata()
                recommendations = build_recommendations(data, pred, drivers) if include_recommendations else recommendations_not_requested()
        elif selected_model == "academic":
            pred = runtime.predict(data)
            drivers = runtime.local_drivers(data, pred)
            model_metadata = runtime.metadata()
            recommendations = build_recommendations(data, pred, drivers) if include_recommendations else recommendations_not_requested()
        else:
            raise ModelUnavailableError(f"Modelo desconocido: {selected_model}.")
        ml_and_drivers_ms = round((time.perf_counter() - started) * 1000, 2)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        genai_ms = recommendations.get("genai_latency_ms") if recommendations and recommendations.get("genai_attempted") else None
        monitoring.record_prediction(elapsed, recommendations or {}, model_id=selected_model)
        logger.info(json.dumps({
            "event": "prediction",
            "prediction_id": prediction_id,
            "model_id": selected_model,
            "model_version": model_metadata.get("version", runtime.version),
            "model_mode": model_metadata.get("mode", runtime.mode),
            "inference_ms": elapsed,
            "ml_and_drivers_ms": ml_and_drivers_ms,
            "genai_ms": genai_ms,
            "recommendation_engine": recommendations.get("engine") if recommendations else None,
            "genai_attempted": recommendations.get("genai_attempted", False) if recommendations else False,
            "genai_used": recommendations.get("genai_used", False) if recommendations else False,
            "genai_failure_code": recommendations.get("failure_code") if recommendations else None,
        }, ensure_ascii=False))
        return serialize({
            "prediction_id": prediction_id,
            "model": {
                "id": selected_model,
                "version": model_metadata.get("version", runtime.version),
                "mode": model_metadata.get("mode", runtime.mode),
                "execution": "LIVE",
                "dataset_source": model_metadata["dataset_source"],
                "dataset_type": model_metadata["dataset_type"],
                "model_type": model_metadata["model_type"],
                "final_status_mode": model_metadata.get("final_status_mode", "not_available_no_health_label"),
                "fusion": model_metadata.get("fusion"),
                "trained_features": model_metadata["trained_features"],
                "health_available": model_metadata.get("health_available", True),
                "selection_warning": selection_warning,
            },
            "prediction": pred,
            "drivers": drivers,
            "driver_source": "local_model_sensitivity" if selected_model == "academic" else "not_available_temporal_sample_too_small",
            "drivers_disclaimer": "La importancia o el impacto local muestra sensibilidad del modelo; no demuestra causalidad." if selected_model == "academic" else "El modelo empírico usa únicamente features baseline; no se estiman drivers locales.",
            "recommendations": recommendations,
            "recommendations_unavailable_reason": "No existe etiqueta Health empírica validada." if selected_model == "empirical" else None,
            "inference_ms": elapsed,
            "ml_inference_ms": ml_and_drivers_ms,
            "genai_latency_ms": genai_ms,
            "timing": {
                "ml_and_drivers_ms": ml_and_drivers_ms,
                "genai_ms": genai_ms,
                "total_ms": elapsed,
            },
            "input": data,
        })
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        monitoring.record_failure(elapsed, model_id=selected_model)
        logger.exception(json.dumps({
            "event": "prediction_error",
            "prediction_id": prediction_id,
            "model_id": selected_model,
            "model_version": runtime.version,
            "inference_ms": round(elapsed, 2),
            "error_type": type(exc).__name__,
        }, ensure_ascii=False))
        raise


@app.get("/api/health")
def health():
    active_model, warning = get_active_model_id(runtime)
    records = model_records(runtime)
    active_record = next(record for record in records if record["id"] == active_model)
    return {
        "status": "ok",
        **runtime.metadata(),
        "active_model": active_model,
        "active_version": active_record["version"],
        "available_models": records,
        "model_selection_warning": warning,
    }


@app.get("/api/models")
def models():
    active_model, warning = get_active_model_id(runtime)
    return {
        "models": model_records(runtime),
        "active_model": active_model,
        "warning": warning,
        "training_enabled": os.getenv("PRUNIN_ENABLE_TRAINING_UI", "0") == "1",
    }


@app.get("/api/models/{model_id}/schema")
def model_feature_schema(model_id: str):
    try:
        schema = model_schema(model_id, runtime)
        if model_id == "empirical":
            schema["input_adapter"] = {
                "planned_duration_weeks": {"maps_to": "planned_duration_days", "conversion": "weeks * 7 calendar days"},
                "planned_budget": {"maps_to": "planned_budget_bac", "conversion": "identity; caller currency units"},
            }
        return schema
    except ModelUnavailableError as exc:
        raise HTTPException(404, str(exc))


@app.get("/api/models/{model_id}")
def model_detail(model_id: str):
    record = next((item for item in model_records(runtime) if item["id"] == model_id), None)
    if record is None:
        raise HTTPException(404, "Modelo desconocido.")
    return record


@app.get("/api/models/{model_id}/report")
def model_report(model_id: str):
    record = next((item for item in model_records(runtime) if item["id"] == model_id), None)
    if record is None:
        raise HTTPException(404, "Modelo desconocido.")
    report_path = (ROOT / str(record.get("artifact_path", "")) / "training_report.md").resolve()
    if not report_path.is_relative_to((ROOT / "artifacts").resolve()) or not report_path.is_file():
        raise HTTPException(404, "No hay un reporte de entrenamiento para este modelo.")
    return FileResponse(report_path, media_type="text/markdown", filename=f"{model_id}-training-report.md")


@app.post("/api/models/select")
def select_active_model(payload: ModelSelectionRequest):
    try:
        return select_model(payload.model_id, runtime)
    except ModelUnavailableError as exc:
        raise HTTPException(409, str(exc))


@app.get("/api/model-comparison")
def model_comparison():
    records = {record["id"]: record for record in model_records(runtime)}
    academic = records["academic"]
    empirical = records["empirical"]
    return {
        "academic": academic,
        "empirical": empirical,
        "head_to_head": {
            "available": False,
            "reason": "Los modelos usan datasets, targets y protocolos distintos; se requiere un test externo común.",
        },
        "interpretation": "Las métricas describen desempeño dentro del dominio y split propios de cada modelo; no establecen superioridad global.",
        "recommendation": {
            "model_id": "academic",
            "automatic_winner": False,
            "reason": "Academic mantiene compatibilidad completa con la experiencia existente. Empirical solo estima Delay/Cost desde duración y BAC y no supera la baseline mediana en el TEST de DSLIB.",
        },
    }


@app.post("/api/training/empirical")
def start_empirical_training():
    if os.getenv("PRUNIN_ENABLE_TRAINING_UI", "0") != "1":
        raise HTTPException(403, "El entrenamiento desde la interfaz está deshabilitado.")
    with training_jobs_lock:
        active = next((job for job in training_jobs.values() if job["status"] not in {"completed", "failed"}), None)
        if active is not None:
            raise HTTPException(409, "Ya existe un entrenamiento empírico activo.")
        job_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        training_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress_percent": 0,
            "current_step": "Esperando el worker de entrenamiento.",
            "started_at": timestamp,
            "updated_at": timestamp,
            "error": None,
            "result": None,
            "events": [{"timestamp": timestamp, "status": "queued", "message": "Entrenamiento en cola."}],
        }
    training_executor.submit(_run_training_job, job_id)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/training/{job_id}")
def training_job(job_id: str):
    with training_jobs_lock:
        job = training_jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "No se encontró el entrenamiento.")
        return {key: value for key, value in job.items() if key != "events"}


@app.get("/api/training/{job_id}/logs")
def training_job_logs(job_id: str):
    with training_jobs_lock:
        job = training_jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "No se encontró el entrenamiento.")
        return {"job_id": job_id, "events": list(job["events"])}


@app.get("/api/ready")
def ready():
    models = set(runtime.brain.models)
    required = {"health", "delay_days", "cost_overrun_ratio"}
    if not required <= models:
        raise HTTPException(503, f"Modelos requeridos no disponibles: {sorted(required - models)}")
    active_model, warning = get_active_model_id(runtime)
    active_record = next(record for record in model_records(runtime) if record["id"] == active_model)
    return {
        "status": "ready",
        "model_version": runtime.version,
        "model_mode": runtime.mode,
        "models_loaded": sorted(models),
        "active_model": active_model,
        "active_version": active_record["version"],
        "model_selection_warning": warning,
    }


@app.get("/api/genai-status")
def genai_status():
    return check_ollama_status()


@app.get("/api/monitoring")
def monitoring_snapshot():
    return monitoring.snapshot(model_version=runtime.version, model_mode=runtime.mode)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        content=monitoring.prometheus_text(model_version=runtime.version, model_mode=runtime.mode),
        media_type="text/plain; version=0.0.4",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/schema")
def schema():
    fields = runtime.field_usage()
    ml_fields = [field for field in fields if field["usage"] == "ml_feature"]
    team_health_fields = [field for field in fields if field["usage"] == "team_health"]
    not_used_fields = [field for field in fields if field["usage"] == "not_used"]
    return {
        "fields": fields,
        "field_usage": {field["name"]: field["usage"] for field in fields},
        "ml_features": [field["name"] for field in ml_fields],
        "team_health_features": [field["name"] for field in team_health_fields],
        "not_used_features": [field["name"] for field in not_used_fields],
        "what_if_fields": [field["name"] for field in ml_fields + team_health_fields],
        "academic_template_fields": [field["name"] for field in ml_fields + team_health_fields],
        "optional_team_health_template_fields": [field["name"] for field in team_health_fields],
        "presets": PRESETS,
        "model": runtime.metadata(),
        "excluded_legacy_features": ["reported_progress", "critical_path_delay_days", "team_morale"],
        "team_health_note": "team_health_index is calculated operationally from observable signals and is not silently injected into the supervised models.",
        "public_url": os.getenv("PRUNIN_PUBLIC_URL"),
    }


@app.post("/api/compare-models")
def compare_models(payload: ProjectInput):
    data = payload.model_dump()
    results = {}
    for model_id in ("academic", "empirical"):
        try:
            results[model_id] = run_prediction(data, include_recommendations=False, model_id=model_id)
        except Exception as exc:
            results[model_id] = {"available": False, "error": str(exc) if isinstance(exc, (ValueError, ModelUnavailableError)) else "No fue posible ejecutar este modelo con el input recibido."}
    academic = results["academic"]
    empirical = results["empirical"]
    comparable = academic.get("prediction") is not None and empirical.get("prediction") is not None
    academic_prediction = academic.get("prediction", {})
    empirical_prediction = empirical.get("prediction", {})
    return {
        "academic": academic,
        "empirical": empirical,
        "comparison": {
            "compatible": comparable,
            "head_to_head": False,
            "delay_days_delta": round(float(empirical_prediction["delay_days_raw"]) - float(academic_prediction["delay_days_raw"]), 2) if comparable and empirical_prediction.get("delay_days_raw") is not None and academic_prediction.get("delay_days_raw") is not None else None,
            "cost_overrun_ratio_delta": round(float(empirical_prediction["cost_overrun_ratio"]) - float(academic_prediction["cost_overrun_ratio"]), 4) if comparable and empirical_prediction.get("cost_overrun_ratio") is not None and academic_prediction.get("cost_overrun_ratio") is not None else None,
            "health_comparison": "not_available" if not empirical_prediction.get("health") else "same" if empirical_prediction.get("health") == academic_prediction.get("health") else "different",
            "note": "Predicciones lado a lado; datasets y targets distintos, no indican cuál es correcto.",
        },
    }


@app.post("/api/predict")
def predict(payload: ProjectInput, include_recommendations: bool = True, model_id: str | None = None):
    try:
        return run_prediction(payload.model_dump(), include_recommendations=include_recommendations, model_id=model_id)
    except ModelUnavailableError as exc:
        raise HTTPException(503, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/api/what-if")
def what_if(payload: WhatIfRequest, model_id: str | None = None):
    baseline_input = payload.baseline.model_dump()
    scenario_input = payload.scenario.model_dump()
    selected_model, _ = get_active_model_id(runtime) if model_id is None else (model_id, None)
    usage = ({
        "planned_duration_weeks": "ml_feature",
        "planned_budget": "ml_feature",
        **{name: "team_health" for name in runtime.config.get("team_health", {}).get("weights", {})},
    }
             if selected_model == "empirical" else {field["name"]: field["usage"] for field in runtime.field_usage()})
    invalid_changes = unused_what_if_changes(baseline_input, scenario_input, usage)
    if invalid_changes:
        raise HTTPException(422, f"What-if no puede modificar variables no utilizadas por este modelo: {invalid_changes}")
    try:
        baseline = run_prediction(baseline_input, include_recommendations=False, model_id=selected_model)
        scenario = run_prediction(scenario_input, include_recommendations=False, model_id=selected_model)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    bp, sp = baseline["prediction"], scenario["prediction"]
    return {
        "baseline": baseline,
        "scenario": scenario,
        "delta": {
            "risk_score": round(float(sp["fused_risk_score"]) - float(bp["fused_risk_score"]), 4) if sp.get("fused_risk_score") is not None and bp.get("fused_risk_score") is not None else None,
            "delay_days": round(float(sp["delay_days_raw"]) - float(bp["delay_days_raw"]), 2) if sp.get("delay_days_raw") is not None and bp.get("delay_days_raw") is not None else None,
            "cost_overrun_ratio": round(float(sp["cost_overrun_ratio"]) - float(bp["cost_overrun_ratio"]), 4) if sp.get("cost_overrun_ratio") is not None and bp.get("cost_overrun_ratio") is not None else None,
        },
    }


@app.post("/api/predict-csv")
async def predict_csv(file: UploadFile = File(...), model_id: str | None = None):
    selected_model, warning = get_active_model_id(runtime) if model_id is None else (model_id, None)
    available = {record["id"]: record for record in model_records(runtime)}
    if selected_model not in available:
        raise HTTPException(400, "Modelo desconocido para procesamiento CSV.")
    if available[selected_model].get("status") != "ready":
        raise HTTPException(503, "El modelo seleccionado no está disponible para procesamiento CSV.")
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(413, "El CSV supera 5 MB.")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(400, f"No fue posible leer el CSV: {exc}")
    if len(df) > 100:
        raise HTTPException(400, "La demo pública procesa máximo 100 filas por archivo.")
    if selected_model == "empirical":
        missing_columns = sorted({"planned_duration_weeks", "planned_budget"} - set(df.columns))
        if missing_columns:
            raise HTTPException(422, f"Faltan columnas requeridas para Empirical: {missing_columns}")
    rows = []
    for i, record in enumerate(df.to_dict("records"), start=1):
        clean = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        try:
            validated = ProjectInput.model_validate(clean)
            result = run_prediction(validated.model_dump(), include_recommendations=False, model_id=selected_model)
            rows.append({"row_number": i, "prediction": result, "error": None})
        except Exception as exc:
            rows.append({"row_number": i, "prediction": None, "error": str(exc)})
    return {"filename": file.filename, "rows": rows, "count": len(rows), "model": {"id": selected_model, "version": available[selected_model]["version"], "mode": available[selected_model].get("source_type"), "selection_warning": warning}}


@app.get("/api/qr")
def qr(url: str):
    if not url.startswith(("http://", "https://")) or len(url) > 1000:
        raise HTTPException(400, "URL inválida para QR.")
    image = qrcode.make(url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/csv-template")
def csv_template(profile: str = "academic", model_id: str | None = None):
    if profile not in {"academic", "full_future"}:
        raise HTTPException(400, "profile debe ser academic o full_future.")
    selected_model, _ = get_active_model_id(runtime) if model_id is None else (model_id, None)
    available = {record["id"]: record for record in model_records(runtime)}
    if selected_model not in available:
        raise HTTPException(400, "Modelo desconocido para generar la plantilla.")
    if available[selected_model].get("status") != "ready":
        raise HTTPException(503, "El modelo seleccionado no está disponible para generar la plantilla.")
    if selected_model == "empirical":
        columns = ["planned_duration_weeks", "planned_budget"]
        row = {name: PRESETS["at_risk"].get(name) for name in columns}
        filename = "prunin_empirical_template.csv"
        path = ROOT / "artifacts" / filename
        pd.DataFrame([row], columns=columns).to_csv(path, index=False)
        return FileResponse(
            path, media_type="text/csv", filename=filename,
            headers={"X-Required-ML-Features": ",".join(columns), "X-Optional-Team-Health-Features": ""},
        )
    fields = runtime.field_usage()
    if profile == "academic":
        columns = [field["name"] for field in fields if field["usage"] in {"ml_feature", "team_health"}]
        filename = "prunin_academic_template.csv"
    else:
        columns = [field["name"] for field in fields]
        filename = "prunin_full_future_template.csv"
    row = {name: PRESETS["at_risk"].get(name) for name in columns}
    path = ROOT / "artifacts" / filename
    pd.DataFrame([row], columns=columns).to_csv(path, index=False)
    ml_fields = [field["name"] for field in fields if field["usage"] == "ml_feature"]
    team_fields = [field["name"] for field in fields if field["usage"] == "team_health"]
    return FileResponse(
        path, media_type="text/csv", filename=filename,
        headers={
            "X-Required-ML-Features": ",".join(ml_fields),
            "X-Optional-Team-Health-Features": ",".join(team_fields),
        },
    )


DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
