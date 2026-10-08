from __future__ import annotations

import io
import json
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

from .catalog import FIELD_CATALOG, PRESETS
from .model_runtime import ModelRuntime, ROOT
from .recommendations import build_recommendations
from .schema import ProjectInput, WhatIfRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        runtime.brain.predict(PRESETS["at_risk"])
    except Exception:
        pass
    yield


app = FastAPI(title="PRUNIN AI Core Playground", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
runtime = ModelRuntime()


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


def run_prediction(data: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    pred = runtime.predict(data)
    drivers = runtime.local_drivers(data, pred)
    recommendations = build_recommendations(data, pred, drivers)
    elapsed = (time.perf_counter() - started) * 1000
    model_metadata = runtime.metadata()
    return serialize({
        "prediction_id": str(uuid.uuid4()),
        "model": {
            "version": runtime.version,
            "mode": runtime.mode,
            "execution": "LIVE",
            "dataset_source": model_metadata["dataset_source"],
            "dataset_type": model_metadata["dataset_type"],
            "model_type": model_metadata["model_type"],
        },
        "prediction": pred,
        "drivers": drivers,
        "recommendations": recommendations,
        "inference_ms": round(elapsed, 2),
        "input": data,
    })


@app.get("/api/health")
def health():
    return {"status": "ok", **runtime.metadata()}


@app.get("/api/schema")
def schema():
    return {
        "fields": FIELD_CATALOG,
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
    try:
        baseline = run_prediction(payload.baseline.model_dump())
        scenario = run_prediction(payload.scenario.model_dump())
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
            result = run_prediction(validated.model_dump())
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
def csv_template():
    row = PRESETS["at_risk"]
    path = ROOT / "artifacts" / "playground_input_template.csv"
    pd.DataFrame([row]).to_csv(path, index=False)
    return FileResponse(path, media_type="text/csv", filename="prunin_playground_template.csv")


DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
