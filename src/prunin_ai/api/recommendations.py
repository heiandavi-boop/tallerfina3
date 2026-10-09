from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from typing import Any

import requests


ACTION_CATALOG = {
    "planned_duration_weeks": "Revisar si la duración planificada sigue siendo consistente con el trabajo restante.",
    "planned_budget": "Revisar la suficiencia del presupuesto frente al trabajo pendiente y las proyecciones actuales.",
    "true_progress": "Revisar trabajo pendiente y compromisos restantes frente al nivel actual de avance.",
    "project_type": "Revisar si la estrategia de ejecución es adecuada para las condiciones actuales del proyecto.",
    "methodology": "Revisar si la estrategia de ejecución es adecuada para las condiciones actuales del proyecto.",
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

DEFAULT_OLLAMA_TIMEOUT_SECONDS = 30.0
_NUMERIC_CLAIM = re.compile(r"(?<![\w.])[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)\s*(%)?")
_STATUS_LOCK = threading.Lock()
_LAST_GENAI_ERROR: dict[str, str] | None = None


def ollama_timeout_seconds(override: float | None = None) -> float:
    if override is not None:
        timeout = float(override)
    else:
        try:
            timeout = float(os.getenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_TIMEOUT_SECONDS)))
        except ValueError:
            timeout = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    if not math.isfinite(timeout) or timeout <= 0:
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS
    return timeout


def _set_last_genai_error(code: str | None, detail: str | None) -> None:
    global _LAST_GENAI_ERROR
    with _STATUS_LOCK:
        _LAST_GENAI_ERROR = {"failure_code": code, "failure_detail": detail} if code else None


def check_ollama_status(*, timeout: float = 3.0) -> dict[str, Any]:
    enabled = os.getenv("PRUNIN_ENABLE_OLLAMA", "0") == "1"
    model = os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    base_url = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    tags_url = base_url.rsplit("/api/", 1)[0] + "/api/tags" if "/api/" in base_url else base_url.rstrip("/") + "/api/tags"
    with _STATUS_LOCK:
        last_error = dict(_LAST_GENAI_ERROR) if _LAST_GENAI_ERROR else None
    result = {
        "enabled": enabled,
        "provider": "ollama",
        "model": model,
        "available": False,
        "last_error": last_error,
    }
    if not enabled:
        result["last_error"] = None
        return result
    try:
        response = requests.get(tags_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        installed = {str(item.get("name", "")) for item in payload.get("models", []) if isinstance(item, dict)}
        result["available"] = model in installed or f"{model}:latest" in installed
        if not result["available"]:
            result["last_error"] = {"failure_code": "model_not_found", "failure_detail": f"El modelo {model} no aparece en Ollama."}
            _set_last_genai_error("model_not_found", result["last_error"]["failure_detail"])
    except requests.exceptions.Timeout as exc:
        result["last_error"] = {"failure_code": "ollama_timeout", "failure_detail": str(exc)}
        _set_last_genai_error("ollama_timeout", str(exc))
    except requests.exceptions.ConnectionError as exc:
        result["last_error"] = {"failure_code": "ollama_unavailable", "failure_detail": str(exc)}
        _set_last_genai_error("ollama_unavailable", str(exc))
    except requests.exceptions.HTTPError as exc:
        result["last_error"] = {"failure_code": "http_error", "failure_detail": str(exc)}
        _set_last_genai_error("http_error", str(exc))
    except (ValueError, requests.exceptions.RequestException) as exc:
        result["last_error"] = {"failure_code": "ollama_unavailable", "failure_detail": str(exc)}
        _set_last_genai_error("ollama_unavailable", str(exc))
    return result


def warmup_ollama() -> dict[str, Any]:
    status = check_ollama_status(timeout=min(3.0, ollama_timeout_seconds()))
    if not status["enabled"] or not status["available"]:
        return {"ok": False, "status": status}
    url = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    try:
        response = requests.post(
            url,
            json={
                "model": status["model"],
                "messages": [{"role": "user", "content": "/no_think Responde OK."}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 8},
            },
            timeout=min(5.0, ollama_timeout_seconds()),
        )
        response.raise_for_status()
        _set_last_genai_error(None, None)
        return {"ok": True, "status": status}
    except requests.exceptions.Timeout as exc:
        _set_last_genai_error("ollama_timeout", str(exc))
        return {"ok": False, "status": status, "failure_code": "ollama_timeout", "failure_detail": str(exc)}
    except requests.exceptions.RequestException as exc:
        _set_last_genai_error("ollama_unavailable", str(exc))
        return {"ok": False, "status": status, "failure_code": "ollama_unavailable", "failure_detail": str(exc)}


def _allowed_features(drivers: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("feature"))
        for item in drivers
        if item.get("feature") and item.get("direction") == "increases_risk"
    }


def _evidence_numeric_values(
    prediction: dict[str, Any] | None,
    drivers: list[dict[str, Any]] | None,
) -> tuple[list[float], list[float]]:
    values: set[float] = set()
    percentage_values: set[float] = set()
    if prediction:
        for key in ("delay_days", "cost_overrun_ratio", "fused_risk_score"):
            value = prediction.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.add(float(value))
                if key in {"cost_overrun_ratio", "fused_risk_score"}:
                    percentage_values.add(float(value))
        probabilities = prediction.get("health_probabilities")
        if isinstance(probabilities, dict):
            for value in probabilities.values():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    values.add(float(value))
                    percentage_values.add(float(value))
        team_health = prediction.get("team_health")
        if isinstance(team_health, dict) and isinstance(team_health.get("score"), (int, float)):
            values.add(float(team_health["score"]))
            percentage_values.add(float(team_health["score"]))
    percent_features = {"true_progress", "team_utilization", "average_productivity", "defect_rate", "rework_ratio", "scope_growth_ratio", "normalized_risk_exposure", "governance_health_score"}
    for driver in drivers or []:
        feature = str(driver.get("feature", ""))
        for key in ("value", "reference"):
            value = driver.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric = float(value)
                values.add(numeric)
                if feature in percent_features or feature.endswith(("_ratio", "_rate")):
                    percentage_values.add(numeric)
    return sorted(values), sorted(percentage_values)


def _has_unsupported_number(text: str, allowed_values: list[float], allowed_percentages: list[float]) -> bool:
    for match in _NUMERIC_CLAIM.finditer(text):
        try:
            number = float(match.group(0).replace("%", "").replace(",", ".").strip())
        except ValueError:
            return True
        if match.group(1):
            number /= 100
            candidates = allowed_percentages
        else:
            candidates = allowed_values
        if not any(math.isclose(number, allowed, rel_tol=0.03, abs_tol=0.005) for allowed in candidates):
            return True
    return False


def validate_generated_payload(
    payload: Any,
    allowed_features: set[str],
    *,
    prediction: dict[str, Any] | None = None,
    drivers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else None
    summary = payload.get("summary") if isinstance(payload, dict) else None
    schema_valid = isinstance(recommendations, list) and len(recommendations) <= 4 and isinstance(summary, str)
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
            if not isinstance(feature, str) or not isinstance(reason, str) or not reason.strip() or not isinstance(action, str) or len(action.strip()) < 8:
                schema_valid = False
                break
            referenced.append(feature)
            narratives.extend([reason, action])
    if isinstance(summary, str):
        narratives.append(summary)
    risk_drivers_exist = bool(allowed_features)
    empty_with_risk = schema_valid and risk_drivers_exist and not recommendations
    evidence_features_valid = empty_with_risk or (not allowed_features and not referenced) or (bool(referenced) and set(referenced) <= allowed_features)
    allowed_numbers, allowed_percentages = _evidence_numeric_values(prediction, drivers)
    unsupported_numeric_claim = any(_has_unsupported_number(text, allowed_numbers, allowed_percentages) for text in narratives)
    actionability = schema_valid and all(len(item["action"].strip()) >= 8 for item in recommendations or [])
    grounded = schema_valid and evidence_features_valid and not unsupported_numeric_claim and not empty_with_risk
    if not schema_valid:
        failure_code = "invalid_schema"
        failure_detail = "Se esperaba summary textual y hasta cuatro recomendaciones con evidencia, razón y acción válidas."
    elif empty_with_risk:
        failure_code = "empty_recommendations_with_risk_drivers"
        failure_detail = "Hay drivers que aumentan riesgo, pero la respuesta no propuso recomendaciones."
    elif not evidence_features_valid:
        failure_code = "unknown_evidence_feature"
        failure_detail = "Una recomendación citó evidencia fuera de la lista permitida."
    elif unsupported_numeric_claim:
        failure_code = "unsupported_numeric_claim"
        failure_detail = "La respuesta incluyó cifras que no aparecen en la evidencia estructurada."
    elif not actionability:
        failure_code = "grounding_validation_failed"
        failure_detail = "La respuesta no contiene acciones concretas suficientemente claras."
    else:
        failure_code = None
        failure_detail = None
    return {
        "schema_valid": schema_valid,
        "evidence_features_valid": evidence_features_valid,
        "referenced_evidence_features": sorted(set(referenced)),
        "allowed_evidence_features": sorted(allowed_features),
        "allowed_numeric_values": allowed_numbers,
        "allowed_numeric_percentages": allowed_percentages,
        "unsupported_numeric_claim": unsupported_numeric_claim,
        "actionability": actionability,
        "grounded": grounded,
        "failure_code": failure_code,
        "failure_detail": failure_detail,
    }


def build_grounded_prompt(prediction: dict[str, Any], drivers: list[dict[str, Any]]) -> tuple[str, set[str]]:
    relevant_drivers = [item for item in drivers if item.get("direction") == "increases_risk"][:6]
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
        "Eres la capa de explicación de PRUNIN AI Core. Tu única fuente es EVIDENCIA. "
        "No inventes hechos, causas, variables, cifras, personas ni eventos. No escribas cifras ni porcentajes en reason, action o summary; describe cualitativamente. "
        "Solo puedes citar evidence_feature incluida en allowed_evidence_features. "
        "Evita cifras nuevas; si mencionas una, debe provenir literalmente de EVIDENCIA. "
        "Devuelve exclusivamente JSON válido, sin markdown ni texto adicional, con esta estructura: "
        '{"recommendations":[{"evidence_feature":"cpi","reason":"explicación breve",'
        '"action":"acción concreta"}],"summary":"resumen breve"}. '
        "Máximo cuatro recomendaciones y una evidencia por recomendación. "
        "Si allowed_evidence_features está vacío, recommendations debe ser [].\n"
        "EVIDENCIA:\n" + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )
    return prompt, allowed_features


def generate_ollama_grounded(
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
    *,
    model: str | None = None,
    url: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    model = model or os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    url = url or os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    timeout = ollama_timeout_seconds(timeout)
    prompt, allowed_features = build_grounded_prompt(prediction, drivers)
    started = time.perf_counter()
    raw_response = ""
    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 400},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        response_payload = response.json()
        message = response_payload.get("message") if isinstance(response_payload, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raw_response = str(getattr(response, "text", ""))
            return _generation_failure(
                model, allowed_features, started, "invalid_json", "Ollama devolvió contenido vacío o sin campo message.content.", raw_response=raw_response
            )
        raw_response = content
        parsed = json.loads(content)
        validation = validate_generated_payload(parsed, allowed_features, prediction=prediction, drivers=drivers)
        latency_ms = (time.perf_counter() - started) * 1000
        failure_code = validation.get("failure_code")
        failure_detail = validation.get("failure_detail")
        _set_last_genai_error(failure_code, failure_detail)
        return {
            "ok": bool(validation["grounded"]),
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "payload": parsed,
            "validation": validation,
            "failure_code": failure_code,
            "failure_detail": failure_detail,
            "error": failure_code,
            "raw_response": raw_response,
        }
    except requests.exceptions.Timeout as exc:
        return _generation_failure(model, allowed_features, started, "ollama_timeout", str(exc), raw_response=raw_response)
    except requests.exceptions.ConnectionError as exc:
        return _generation_failure(model, allowed_features, started, "ollama_unavailable", str(exc), raw_response=raw_response)
    except requests.exceptions.HTTPError as exc:
        return _generation_failure(model, allowed_features, started, "http_error", str(exc), raw_response=raw_response)
    except (json.JSONDecodeError, ValueError) as exc:
        return _generation_failure(model, allowed_features, started, "invalid_json", str(exc), raw_response=raw_response)
    except requests.exceptions.RequestException as exc:
        return _generation_failure(model, allowed_features, started, "http_error", str(exc), raw_response=raw_response)
    except Exception as exc:
        return _generation_failure(model, allowed_features, started, "http_error", f"Fallo inesperado de Ollama: {exc}", raw_response=raw_response)


def _generation_failure(
    model: str,
    allowed_features: set[str],
    started: float,
    failure_code: str,
    failure_detail: str,
    *,
    raw_response: str = "",
) -> dict[str, Any]:
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    _set_last_genai_error(failure_code, failure_detail)
    validation = {
        "schema_valid": False,
        "evidence_features_valid": False,
        "referenced_evidence_features": [],
        "allowed_evidence_features": sorted(allowed_features),
        "allowed_numeric_values": [],
        "allowed_numeric_percentages": [],
        "unsupported_numeric_claim": False,
        "actionability": False,
        "grounded": False,
        "failure_code": failure_code,
        "failure_detail": failure_detail,
    }
    return {
        "ok": False,
        "model": model,
        "latency_ms": latency_ms,
        "payload": None,
        "validation": validation,
        "failure_code": failure_code,
        "failure_detail": failure_detail,
        "error": failure_code,
        "raw_response": raw_response,
    }


def grounded_fallback(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
    *,
    genai_attempted: bool = False,
    genai_failure_reason: str | None = None,
    failure_code: str | None = None,
    failure_detail: str | None = None,
    genai_latency_ms: float | None = None,
    validation: dict[str, Any] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions: list[str] = []
    reasons: list[str] = []
    evidence_features: list[str] = []
    risk_drivers = [driver for driver in drivers if driver.get("direction") == "increases_risk"]
    for driver in risk_drivers[:5]:
        name = str(driver.get("feature"))
        evidence_features.append(name)
        reasons.append(f"{driver.get('label', name)} muestra una señal asociada con mayor riesgo en esta inferencia.")
        if name in ACTION_CATALOG:
            actions.append(ACTION_CATALOG[name])
    allowed_features = sorted(_allowed_features(drivers))
    if not risk_drivers:
        summary = "No se identificaron drivers locales que aumenten riesgo y requieran una acción específica."
        actions = []
    elif not actions:
        summary = "Se observan señales de riesgo sin una acción de respaldo catalogada; revisar la evidencia con el equipo del proyecto."
    else:
        summary = "Recomendaciones de respaldo asociadas con señales observadas del modelo."
    result = {
        "engine": "grounded_fallback",
        "genai_attempted": genai_attempted,
        "genai_used": False,
        "genai_failure_reason": genai_failure_reason or failure_detail or failure_code,
        "failure_code": failure_code,
        "failure_detail": failure_detail or genai_failure_reason,
        "genai_latency_ms": genai_latency_ms,
        "evidence_features": list(dict.fromkeys(evidence_features))[:5],
        "allowed_evidence_features": validation.get("allowed_evidence_features", allowed_features) if validation else allowed_features,
        "referenced_evidence_features": validation.get("referenced_evidence_features", []) if validation else [],
        "reasons": reasons[:5],
        "actions": list(dict.fromkeys(actions))[:5],
        "summary": summary,
        "grounding": validation or {
            "source": "local_model_sensitivity",
            "structured_evidence_only": True,
            "raw_project_text_sent_to_llm": False,
            "schema_valid": False,
            "grounded": False,
            "actionability": bool(actions),
        },
        "disclaimer": "Recomendaciones generadas únicamente a partir de señales observadas y sensibilidad local del modelo; no reemplazan el criterio del director del proyecto.",
    }
    if os.getenv("PRUNIN_GENAI_DEBUG", "0") == "1" and debug:
        result["genai_debug"] = debug
    return result


def ollama_recommendations(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if os.getenv("PRUNIN_ENABLE_OLLAMA", "0") != "1":
        return None
    generated = generate_ollama_grounded(prediction, drivers)
    if not generated["ok"]:
        return grounded_fallback(
            row,
            prediction,
            drivers,
            genai_attempted=True,
            genai_failure_reason=generated.get("error"),
            failure_code=generated.get("failure_code"),
            failure_detail=generated.get("failure_detail"),
            genai_latency_ms=generated.get("latency_ms"),
            validation=generated.get("validation"),
            debug={"raw_response": generated.get("raw_response"), "parsed_json": generated.get("payload"), "validation": generated.get("validation")},
        )
    recs = generated["payload"]["recommendations"]
    recommendation = {
        "engine": f"ollama:{generated['model']}",
        "genai_attempted": True,
        "genai_used": True,
        "genai_failure_reason": None,
        "failure_code": None,
        "failure_detail": None,
        "genai_latency_ms": generated["latency_ms"],
        "evidence_features": generated["validation"]["referenced_evidence_features"],
        "allowed_evidence_features": generated["validation"]["allowed_evidence_features"],
        "referenced_evidence_features": generated["validation"]["referenced_evidence_features"],
        "reasons": [item["reason"] for item in recs],
        "actions": [item["action"] for item in recs],
        "summary": generated["payload"].get("summary", ""),
        "latency_ms": generated["latency_ms"],
        "grounding": generated["validation"],
        "disclaimer": "Texto generado por IA sobre evidencia estructurada del modelo; validar antes de tomar decisiones.",
    }
    if os.getenv("PRUNIN_GENAI_DEBUG", "0") == "1":
        recommendation["genai_debug"] = {"raw_response": generated.get("raw_response"), "parsed_json": generated.get("payload"), "validation": generated.get("validation")}
    return recommendation


def build_recommendations(
    row: dict[str, Any],
    prediction: dict[str, Any],
    drivers: list[dict[str, Any]],
) -> dict[str, Any]:
    generated = ollama_recommendations(row, prediction, drivers)
    if generated is not None:
        return generated
    return grounded_fallback(row, prediction, drivers)


def recommendations_not_requested() -> dict[str, Any]:
    return {
        "engine": "not_requested",
        "genai_attempted": False,
        "genai_used": False,
        "failure_code": None,
        "failure_detail": None,
        "genai_latency_ms": None,
        "evidence_features": [],
        "allowed_evidence_features": [],
        "referenced_evidence_features": [],
        "reasons": [],
        "actions": [],
        "summary": "No se solicitó una recomendación para esta inferencia.",
    }
