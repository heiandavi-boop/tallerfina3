from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests


ACTION_CATALOG = {
    "spi": "Revisar las actividades atrasadas y acordar un plan de recuperación del cronograma.",
    "cpi": "Revisar consumo de presupuesto, estimación a la conclusión y fuentes de sobrecosto.",
    "team_utilization": "Redistribuir carga y proteger capacidad del equipo antes de aumentar compromisos.",
    "team_capacity_ratio": "Ajustar demanda, prioridades o capacidad para recuperar un ratio sostenible.",
    "average_productivity": "Identificar bloqueos operativos y concentrar el equipo en trabajo de mayor valor.",
    "defect_rate": "Priorizar causas raíz de defectos y fortalecer controles de calidad tempranos.",
    "rework_ratio": "Reducir retrabajo mediante criterios de aceptación y revisiones antes del cierre de tareas.",
    "scope_growth_ratio": "Controlar cambios de alcance y exigir trazabilidad de impacto antes de aprobarlos.",
    "dependency_delay_days": "Escalar dependencias críticas con responsable y fecha de resolución verificable.",
    "normalized_risk_exposure": "Priorizar mitigaciones de los riesgos de mayor exposición y revisar contingencias.",
    "governance_health_score": "Cerrar decisiones pendientes y reforzar cadencia de gobierno y seguimiento.",
}


def _allowed_features(drivers: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("feature"))
        for item in drivers
        if item.get("feature") and item.get("direction") == "increases_risk"
    }


def validate_generated_payload(payload: Any, allowed_features: set[str]) -> dict[str, Any]:
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else None
    schema_valid = isinstance(recommendations, list) and 0 < len(recommendations) <= 4
    referenced: list[str] = []
    narratives: list[str] = []
    if schema_valid:
        for item in recommendations:
            if not isinstance(item, dict):
                schema_valid = False
                break
            feature = item.get("evidence_feature")
            reason = item.get("reason")
            action = item.get("action")
            if not isinstance(feature, str) or not isinstance(reason, str) or not reason.strip() or not isinstance(action, str) or not action.strip():
                schema_valid = False
                break
            referenced.append(feature)
            narratives.extend([reason, action])
    summary = payload.get("summary", "") if isinstance(payload, dict) else ""
    if summary is not None and not isinstance(summary, str):
        schema_valid = False
    if isinstance(summary, str):
        narratives.append(summary)
    evidence_features_valid = bool(referenced) and set(referenced) <= allowed_features
    unsupported_numeric_claim = any(re.search(r"\d", text) for text in narratives)
    actionability = schema_valid and all(
        isinstance(item.get("action"), str) and len(item["action"].strip()) >= 8
        for item in recommendations or []
    )
    grounded = schema_valid and evidence_features_valid and not unsupported_numeric_claim
    return {
        "schema_valid": schema_valid,
        "evidence_features_valid": evidence_features_valid,
        "referenced_evidence_features": sorted(set(referenced)),
        "allowed_evidence_features": sorted(allowed_features),
        "unsupported_numeric_claim": unsupported_numeric_claim,
        "actionability": actionability,
        "grounded": grounded,
    }


def build_grounded_prompt(prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> tuple[str, set[str]]:
    relevant_drivers = [item for item in drivers[:6] if item.get("direction") == "increases_risk"]
    allowed_features = _allowed_features(relevant_drivers)
    compact = {
        "prediction": {
            key: prediction.get(key)
            for key in ["health", "fused_health", "delay_days", "cost_overrun_ratio", "final_status", "team_health"]
        },
        "risk_drivers": relevant_drivers,
        "allowed_evidence_features": sorted(allowed_features),
    }
    prompt = (
        "/no_think\n"
        "Eres la capa explicativa de PRUNIN para gestión de proyectos. "
        "Usa EXCLUSIVAMENTE el JSON EVIDENCIA. No inventes causas, hechos, cifras ni variables. "
        "No uses números en tus textos. Cada recomendación debe citar exactamente una evidence_feature "
        "de allowed_evidence_features. Devuelve SOLO JSON válido con esta estructura: "
        '{"recommendations":[{"evidence_feature":"spi","reason":"texto corto","action":"acción concreta"}],'
        '"summary":"resumen corto"}. Máximo cuatro recomendaciones. '
        "Si no hay drivers de riesgo, devuelve recommendations vacío y un summary prudente.\n"
        "EVIDENCIA:\n" + json.dumps(compact, ensure_ascii=False)
    )
    return prompt, allowed_features


def generate_ollama_grounded(
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
    *,
    model: str | None = None,
    url: str | None = None,
    timeout: float = 12,
) -> dict[str, Any]:
    model = model or os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    url = url or os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    prompt, allowed_features = build_grounded_prompt(prediction, drivers)
    started = time.perf_counter()
    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        validation = validate_generated_payload(parsed, allowed_features)
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "ok": bool(validation["grounded"]),
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "payload": parsed,
            "validation": validation,
            "error": None if validation["grounded"] else "grounding_validation_failed",
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "ok": False,
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "payload": None,
            "validation": {
                "schema_valid": False,
                "evidence_features_valid": False,
                "referenced_evidence_features": [],
                "allowed_evidence_features": sorted(allowed_features),
                "unsupported_numeric_claim": False,
                "actionability": False,
                "grounded": False,
            },
            "error": f"{type(exc).__name__}: {exc}",
        }


def grounded_fallback(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
    *,
    genai_attempted: bool = False,
    genai_failure_reason: str | None = None,
) -> dict[str, Any]:
    actions: list[str] = []
    reasons: list[str] = []
    evidence_features: list[str] = []
    for driver in drivers[:5]:
        if driver.get("direction") != "increases_risk":
            continue
        name = str(driver.get("feature"))
        evidence_features.append(name)
        reasons.append(f"{driver.get('label', name)} muestra una señal asociada con mayor riesgo en esta inferencia.")
        if name in ACTION_CATALOG:
            actions.append(ACTION_CATALOG[name])
    if not actions:
        actions = ["Mantener seguimiento de las señales principales y volver a ejecutar el análisis cuando cambien las condiciones."]
    return {
        "engine": "grounded_fallback",
        "genai_attempted": genai_attempted,
        "genai_used": False,
        "genai_failure_reason": genai_failure_reason,
        "evidence_features": list(dict.fromkeys(evidence_features))[:5],
        "reasons": reasons[:5],
        "actions": list(dict.fromkeys(actions))[:5],
        "grounding": {
            "source": "local_model_sensitivity",
            "structured_evidence_only": True,
            "raw_project_text_sent_to_llm": False,
        },
        "disclaimer": "Recomendaciones generadas únicamente a partir de señales observadas y sensibilidad local del modelo; no reemplazan el criterio del director del proyecto.",
    }


def ollama_recommendations(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if os.getenv("PRUNIN_ENABLE_OLLAMA", "0") != "1":
        return None
    result = generate_ollama_grounded(prediction, drivers)
    if not result["ok"]:
        return grounded_fallback(
            row,
            prediction,
            drivers,
            genai_attempted=True,
            genai_failure_reason=result.get("error"),
        )
    recs = result["payload"]["recommendations"]
    return {
        "engine": f"ollama:{result['model']}",
        "genai_attempted": True,
        "genai_used": True,
        "genai_failure_reason": None,
        "evidence_features": result["validation"]["referenced_evidence_features"],
        "reasons": [item["reason"] for item in recs],
        "actions": [item["action"] for item in recs],
        "summary": result["payload"].get("summary", ""),
        "latency_ms": result["latency_ms"],
        "grounding": result["validation"],
        "disclaimer": "Texto generado por IA sobre evidencia estructurada del modelo; validar antes de tomar decisiones.",
    }


def build_recommendations(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
) -> dict[str, Any]:
    generated = ollama_recommendations(row, prediction, drivers)
    if generated is not None:
        return generated
    return grounded_fallback(row, prediction, drivers)
