from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import qrcode
import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .catalog import PRESETS
from .model_runtime import ModelRuntime, ROOT, unused_what_if_changes
from .recommendations import build_recommendations, check_ollama_status, recommendations_not_requested, warmup_ollama
from .monitoring import monitoring
from .schema import ProjectInput, WhatIfRequest

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


def run_prediction(data: dict[str, Any], *, include_recommendations: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    prediction_id = str(uuid.uuid4())
    try:
        pred = runtime.predict(data)
        drivers = runtime.local_drivers(data, pred)
        ml_and_drivers_ms = round((time.perf_counter() - started) * 1000, 2)
        recommendations = build_recommendations(data, pred, drivers) if include_recommendations else recommendations_not_requested()
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        genai_ms = recommendations.get("genai_latency_ms") if recommendations and recommendations.get("genai_attempted") else None
        model_metadata = runtime.metadata()
        monitoring.record_prediction(elapsed, recommendations or {})
        logger.info(json.dumps({
            "event": "prediction",
            "prediction_id": prediction_id,
            "model_version": runtime.version,
            "model_mode": runtime.mode,
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
                "version": runtime.version,
                "mode": runtime.mode,
                "execution": "LIVE",
                "dataset_source": model_metadata["dataset_source"],
                "dataset_type": model_metadata["dataset_type"],
                "model_type": model_metadata["model_type"],
                "final_status_mode": model_metadata["final_status_mode"],
                "fusion": model_metadata["fusion"],
                "trained_features": model_metadata["trained_features"],
            },
            "prediction": pred,
            "drivers": drivers,
            "driver_source": "local_model_sensitivity",
            "drivers_disclaimer": "La importancia o el impacto local muestra sensibilidad del modelo; no demuestra causalidad.",
            "recommendations": recommendations,
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
        monitoring.record_failure(elapsed)
        logger.exception(json.dumps({
            "event": "prediction_error",
            "prediction_id": prediction_id,
            "model_version": runtime.version,
            "inference_ms": round(elapsed, 2),
            "error_type": type(exc).__name__,
        }, ensure_ascii=False))
        raise


@app.get("/api/health")
def health():
    return {"status": "ok", **runtime.metadata()}


@app.get("/api/ready")
def ready():
    models = set(runtime.brain.models)
    required = {"health", "delay_days", "cost_overrun_ratio"}
    if not required <= models:
        raise HTTPException(503, f"Modelos requeridos no disponibles: {sorted(required - models)}")
    return {
        "status": "ready",
        "model_version": runtime.version,
        "model_mode": runtime.mode,
        "models_loaded": sorted(models),
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


@app.post("/api/predict")
def predict(payload: ProjectInput):
    try:
        return run_prediction(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/api/what-if")
def what_if(payload: WhatIfRequest):
    baseline_input = payload.baseline.model_dump()
    scenario_input = payload.scenario.model_dump()
    usage = {field["name"]: field["usage"] for field in runtime.field_usage()}
    invalid_changes = unused_what_if_changes(baseline_input, scenario_input, usage)
    if invalid_changes:
        raise HTTPException(422, f"What-if no puede modificar variables no utilizadas por este modelo: {invalid_changes}")
    try:
        baseline = run_prediction(baseline_input, include_recommendations=False)
        scenario = run_prediction(scenario_input, include_recommendations=False)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    bp, sp = baseline["prediction"], scenario["prediction"]
    return {
        "baseline": baseline,
        "scenario": scenario,
        "delta": {
            "risk_score": round(float(sp.get("fused_risk_score", 0)) - float(bp.get("fused_risk_score", 0)), 4) if sp.get("fused_risk_score") is not None and bp.get("fused_risk_score") is not None else None,
            "delay_days": round(float(sp.get("delay_days", 0)) - float(bp.get("delay_days", 0)), 2),
            "cost_overrun_ratio": round(float(sp.get("cost_overrun_ratio", 0)) - float(bp.get("cost_overrun_ratio", 0)), 4),
        },
    }


@app.post("/api/predict-csv")
async def predict_csv(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(413, "El CSV supera 5 MB.")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(400, f"No fue posible leer el CSV: {exc}")
    if len(df) > 100:
        raise HTTPException(400, "La demo pública procesa máximo 100 filas por archivo.")
    rows = []
    for i, record in enumerate(df.to_dict("records"), start=1):
        clean = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        try:
            validated = ProjectInput.model_validate(clean)
            result = run_prediction(validated.model_dump(), include_recommendations=False)
            rows.append({"row_number": i, "prediction": result, "error": None})
        except Exception as exc:
            rows.append({"row_number": i, "prediction": None, "error": str(exc)})
    return {"filename": file.filename, "rows": rows, "count": len(rows), "model": {"version": runtime.version, "mode": runtime.mode}}


@app.get("/api/qr")
def qr(url: str):
    if not url.startswith(("http://", "https://")) or len(url) > 1000:
        raise HTTPException(400, "URL inválida para QR.")
    image = qrcode.make(url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/csv-template")
def csv_template(profile: str = "academic"):
    if profile not in {"academic", "full_future"}:
        raise HTTPException(400, "profile debe ser academic o full_future.")
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
