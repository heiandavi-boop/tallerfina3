from __future__ import annotations

import os
from typing import Any
import requests


def grounded_fallback(row: dict[str, Any], prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any]:
    actions: list[str] = []
    reasons: list[str] = []
    for d in drivers[:5]:
        if d["direction"] != "increases_risk":
            continue
        name = d["feature"]
        reasons.append(f"{d['label']} muestra una señal asociada con mayor riesgo en esta inferencia.")
        mapping = {
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
        if name in mapping:
            actions.append(mapping[name])
    if not actions:
        actions = ["Mantener seguimiento de las señales principales y volver a ejecutar el análisis cuando cambien las condiciones."]
    return {
        "engine": "grounded_fallback",
        "reasons": reasons[:5],
        "actions": list(dict.fromkeys(actions))[:5],
        "disclaimer": "Recomendaciones generadas únicamente a partir de señales observadas y sensibilidad local del modelo; no reemplazan el criterio del director del proyecto.",
    }


def ollama_recommendations(row: dict[str, Any], prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if os.getenv("PRUNIN_ENABLE_OLLAMA", "0") != "1":
        return None
    url = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    model = os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    compact = {
        "prediction": {k: prediction.get(k) for k in ["health", "fused_health", "delay_days", "cost_overrun_ratio", "final_status", "team_health"]},
        "drivers": drivers[:6],
    }
    prompt = (
        "Eres la capa explicativa de PRUNIN. Usa EXCLUSIVAMENTE el JSON adjunto. "
        "No inventes causas, probabilidades ni datos. Devuelve JSON válido con claves reasons y actions, "
        "cada una con máximo 4 textos cortos en español.\nDATOS:\n" + str(compact)
    )
    try:
        r = requests.post(url, json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "format": "json"}, timeout=12)
        r.raise_for_status()
        payload = r.json()
        import json
        content = payload.get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        return {
            "engine": f"ollama:{model}",
            "reasons": list(parsed.get("reasons", []))[:4],
            "actions": list(parsed.get("actions", []))[:4],
            "disclaimer": "Texto generado por IA sobre evidencia estructurada del modelo; validar antes de tomar decisiones.",
        }
    except Exception:
        return None


def build_recommendations(row: dict[str, Any], prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any]:
    return ollama_recommendations(row, prediction, drivers) or grounded_fallback(row, prediction, drivers)
