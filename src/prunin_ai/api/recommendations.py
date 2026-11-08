from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from typing import Any

import requests

from .operational_signals import build_evidence_context


ACTION_GUIDANCE: dict[str, dict[str, str]] = {
    "team_health": {
        "priority": "media",
        "title": "Revisar la condición operativa del equipo",
        "action": "Revisar los componentes disponibles del indicador del equipo y contrastar las cargas con la capacidad antes del siguiente ciclo.",
        "follow_up": "Comparar los componentes del indicador y los acuerdos de carga en el próximo corte.",
    },
    "spi": {
        "priority": "alta",
        "title": "Recuperar el cronograma",
        "action": "Revisar las actividades con mayor desviación frente al plan y definir un plan de recuperación para el siguiente seguimiento.",
        "follow_up": "Revisar SPI y cumplimiento del cronograma en el siguiente corte.",
    },
    "cpi": {
        "priority": "alta",
        "title": "Revisar la proyección de costos",
        "action": "Analizar el consumo presupuestal y actualizar la estimación al cierre antes de asumir nuevos compromisos de gasto.",
        "follow_up": "Comparar CPI y proyección de costo en el siguiente seguimiento.",
    },
    "team_capacity_ratio": {
        "priority": "alta",
        "title": "Alinear carga y capacidad",
        "action": "Contrastar los compromisos de trabajo con la capacidad disponible y acordar una priorización para el siguiente ciclo.",
        "follow_up": "Revisar capacidad disponible y trabajo comprometido en el siguiente corte.",
    },
    "team_utilization": {
        "priority": "alta",
        "title": "Redistribuir la carga del equipo",
        "action": "Revisar la carga asignada y acordar ajustes de prioridades antes de aceptar nuevos compromisos.",
        "follow_up": "Volver a revisar utilización y capacidad del equipo en el próximo seguimiento.",
    },
    "rework_ratio": {
        "priority": "media",
        "title": "Reducir el retrabajo",
        "action": "Identificar tareas con retrabajo y aclarar los criterios de aceptación antes del próximo ciclo.",
        "follow_up": "Revisar la evolución del retrabajo en el siguiente ciclo.",
    },
    "defect_rate": {
        "priority": "media",
        "title": "Controlar defectos recurrentes",
        "action": "Revisar los defectos recurrentes y definir controles de calidad para las siguientes entregas.",
        "follow_up": "Comparar la tasa de defectos en la siguiente revisión de calidad.",
    },
    "average_productivity": {
        "priority": "media",
        "title": "Revisar bloqueos operativos",
        "action": "Identificar bloqueos del proceso con el equipo y acordar una acción para removerlos antes del siguiente ciclo.",
        "follow_up": "Revisar productividad y bloqueos pendientes en el siguiente ciclo.",
    },
    "team_stability": {
        "priority": "media",
        "title": "Revisar continuidad operativa",
        "action": "Revisar la cobertura de funciones del equipo y documentar dependencias operativas que requieran respaldo.",
        "follow_up": "Verificar continuidad de funciones en el siguiente seguimiento.",
    },
    "collaboration_level": {
        "priority": "media",
        "title": "Mejorar la coordinación",
        "action": "Acordar un espacio breve de coordinación entre las áreas involucradas y registrar dependencias pendientes.",
        "follow_up": "Revisar dependencias y acuerdos de coordinación en el siguiente corte.",
    },
    "scope_growth_ratio": {
        "priority": "media",
        "title": "Controlar cambios de alcance",
        "action": "Contrastar las solicitudes de cambio con la línea base y registrar su impacto antes de aprobarlas.",
        "follow_up": "Revisar cambios pendientes y su registro frente a la línea base.",
    },
    "dependency_delay_days": {
        "priority": "media",
        "title": "Dar seguimiento a dependencias",
        "action": "Revisar las dependencias abiertas que afectan el trabajo y acordar un próximo punto de seguimiento.",
        "follow_up": "Verificar el estado de dependencias en el siguiente corte.",
    },
    "normalized_risk_exposure": {
        "priority": "media",
        "title": "Revisar riesgos prioritarios",
        "action": "Revisar los riesgos de mayor exposición en el registro del proyecto y confirmar si requieren actualizar su tratamiento.",
        "follow_up": "Comprobar el estado de los riesgos y sus tratamientos en el próximo seguimiento.",
    },
    "governance_health_score": {
        "priority": "media",
        "title": "Cerrar decisiones de gobierno",
        "action": "Revisar decisiones abiertas y acordar la próxima instancia de seguimiento del proyecto.",
        "follow_up": "Confirmar el estado de decisiones abiertas en la siguiente revisión de gobierno.",
    },
    "planned_duration_weeks": {
        "priority": "baja",
        "title": "Contrastar la duración planificada",
        "action": "Revisar el trabajo pendiente frente a la duración planificada y documentar cualquier ajuste propuesto.",
        "follow_up": "Comparar duración y avance pendiente en el siguiente corte.",
    },
    "planned_budget": {
        "priority": "baja",
        "title": "Revisar el presupuesto disponible",
        "action": "Contrastar los compromisos vigentes y el trabajo pendiente con el presupuesto aprobado antes de asumir nuevos gastos.",
        "follow_up": "Revisar presupuesto disponible y compromisos en el próximo seguimiento.",
    },
    "true_progress": {
        "priority": "baja",
        "title": "Validar el avance reportado",
        "action": "Contrastar el avance con el trabajo completado y actualizar las tareas pendientes antes del siguiente corte.",
        "follow_up": "Revisar avance y trabajo pendiente en la siguiente actualización.",
    },
}

VALID_PRIORITIES = {"alta", "media", "baja"}
PRIORITY_ORDER = {"alta": 0, "media": 1, "baja": 2}
ACTION_VERBS = {
    "acordar", "actualizar", "alinear", "analizar", "comparar", "confirmar", "contrastar",
    "controlar", "definir", "documentar", "establecer", "evaluar", "identificar", "organizar",
    "priorizar", "redistribuir", "registrar", "revisar", "verificar",
    "acuerda", "actualiza", "alinea", "analiza", "compara", "confirma", "contrasta",
    "controla", "define", "documenta", "establece", "evalua", "identifica", "organiza",
    "prioriza", "redistribuye", "registra", "revisa", "verifica",
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


def _has_unsupported_number(text: str, allowed_values: list[float], allowed_percentages: list[float], *, exact_rounding: bool = False) -> bool:
    for match in _NUMERIC_CLAIM.finditer(text):
        literal = match.group(0).replace("%", "").replace(",", ".").strip()
        try:
            number = float(literal)
        except ValueError:
            return True
        if not math.isfinite(number):
            return True
        scale = 100 if match.group(1) else 1
        if match.group(1):
            number /= 100
            candidates = allowed_percentages
        else:
            candidates = allowed_values
        if exact_rounding:
            decimals = len(literal.split(".", 1)[1]) if "." in literal else 0
            supported = any(
                (number != 0 or allowed == 0)
                and math.isclose(number, round(allowed * scale, decimals) / scale, rel_tol=1e-9, abs_tol=1e-12)
                for allowed in candidates
            )
        else:
            supported = any(math.isclose(number, allowed, rel_tol=0.03, abs_tol=0.005) for allowed in candidates)
        if not supported:
            return True
    return False


def _observed_claim_checks(text: str, context: dict[str, Any]) -> tuple[bool, bool]:
    unsupported_value = False
    contrary_interpretation = False
    for signal in context["operational_signals"]:
        subject = "(?:" + "|".join(re.escape(name) for name in (signal["feature"], signal["label"])) + ")"
        prefix = rf"\b{subject}(?:\s+observad[oa])?"
        for claim in re.finditer(prefix + r"\s*(?:(?:es|de|=|:)\s*)?([+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)\s*%?)", text, re.IGNORECASE):
            values, percentages = _evidence_numeric_values(None, [signal])
            unsupported_value |= _has_unsupported_number(claim.group(1), values, percentages, exact_rounding=True)
        contrary_interpretation |= bool(re.search(
            prefix + r"\s+(?:es|resulta|muestra un desempeño|presenta un desempeño)\s+(?:un desempeño\s+)?favorable\b",
            text, re.IGNORECASE,
        ))
    return unsupported_value, contrary_interpretation


def _recommendation_sort_key(recommendation: dict[str, Any]) -> int:
    return PRIORITY_ORDER.get(str(recommendation.get("priority", "baja")), len(PRIORITY_ORDER))


def _is_concrete_action(action: str) -> bool:
    words = action.strip().lower().split()
    if not words or len(action.strip()) < 36:
        return False
    verb = words[0].strip("¿¡.,:;()")
    return verb in ACTION_VERBS


def action_response_schema(allowed_features: set[str], context: dict[str, Any] | None = None) -> dict[str, Any]:
    has_risk_drivers = bool(allowed_features)
    recommendation_schema = {
        "type": "object",
        "properties": {
            "priority": {"type": "string", "enum": ["alta", "media", "baja"]},
            "title": {"type": "string", "minLength": 4, "maxLength": 80},
            "evidence_feature": {"type": "string", "enum": sorted(allowed_features)},
            "reason": {"type": "string", "minLength": 12},
            "action": {"type": "string", "minLength": 36},
            "follow_up": {"type": "string", "minLength": 12},
        },
        "required": ["priority", "title", "evidence_feature", "reason", "action", "follow_up"],
        "additionalProperties": False,
    }
    if context is not None:
        recommendation_schema["properties"]["evidence_source"] = {
            "type": "string", "enum": ["model_driver", "observed_operational_signal", "heuristic_indicator"],
        }
        recommendation_schema["required"].append("evidence_source")
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 180},
            "recommendations": {
                "type": "array",
                "minItems": 1 if has_risk_drivers else 0,
                "maxItems": 4 if has_risk_drivers else 0,
                "items": recommendation_schema,
            },
        },
        "required": ["summary", "recommendations"],
        "additionalProperties": False,
    }


def validate_generated_payload(
    payload: Any,
    allowed_features: set[str],
    *,
    prediction: dict[str, Any] | None = None,
    drivers: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else None
    summary = payload.get("summary") if isinstance(payload, dict) else None
    schema_valid = (
        isinstance(recommendations, list)
        and len(recommendations) <= 4
        and isinstance(summary, str)
        and bool(summary.strip())
        and len(summary.strip()) <= 180
        and "\n" not in summary
    )
    referenced: list[str] = []
    provenance_valid = True
    allowed_pairs = {(item["feature"], item["source"]) for item in context["actionable_evidence"]} if context else set()
    narratives: list[str] = [summary] if isinstance(summary, str) else []
    if isinstance(recommendations, list):
        for item in recommendations:
            if not isinstance(item, dict):
                schema_valid = False
                continue
            priority = item.get("priority")
            title = item.get("title")
            feature = item.get("evidence_feature")
            reason = item.get("reason")
            action = item.get("action")
            follow_up = item.get("follow_up")
            narratives.extend(
                value for value in (title, reason, action, follow_up)
                if isinstance(value, str)
            )
            if (
                not isinstance(priority, str)
                or priority not in VALID_PRIORITIES
                or not isinstance(title, str)
                or not 4 <= len(title.strip()) <= 80
                or not isinstance(feature, str)
                or not isinstance(reason, str)
                or len(reason.strip()) < 12
                or not isinstance(action, str)
                or not isinstance(follow_up, str)
                or len(follow_up.strip()) < 12
            ):
                schema_valid = False
            if isinstance(feature, str):
                referenced.append(feature)
            if context is not None:
                source = item.get("evidence_source")
                if not isinstance(source, str) or not isinstance(feature, str) or (feature, source) not in allowed_pairs:
                    provenance_valid = False
                if set(item) != {"priority", "title", "evidence_feature", "evidence_source", "reason", "action", "follow_up"}:
                    schema_valid = False
    if context is not None and isinstance(payload, dict) and set(payload) != {"summary", "recommendations"}:
        schema_valid = False
    risk_drivers_exist = bool(allowed_features)
    empty_with_risk = schema_valid and risk_drivers_exist and not recommendations
    evidence_features_valid = empty_with_risk or (not allowed_features and not referenced) or (bool(referenced) and set(referenced) <= allowed_features)
    numeric_evidence = context["actionable_evidence"] if context is not None else drivers
    allowed_numbers, allowed_percentages = _evidence_numeric_values(prediction, numeric_evidence)
    unsupported_numeric_claim = any(_has_unsupported_number(text, allowed_numbers, allowed_percentages, exact_rounding=context is not None) for text in narratives)
    if context is not None and isinstance(recommendations, list):
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            matched = [signal for signal in context["actionable_evidence"] if signal["feature"] == item.get("evidence_feature") and signal["source"] == item.get("evidence_source")]
            item_numbers, item_percentages = _evidence_numeric_values(prediction if item.get("evidence_source") == "model_driver" else None, matched)
            unsupported_numeric_claim |= any(_has_unsupported_number(item[key], item_numbers, item_percentages, exact_rounding=True) for key in ("title", "reason", "action", "follow_up") if isinstance(item.get(key), str))
        provenance_valid &= len(referenced) == len(set(referenced))
    contradiction = False
    if context is not None:
        text = " ".join(narratives).lower()
        misattributed_value, contrary_observation = _observed_claim_checks(text, context)
        unsupported_numeric_claim |= misattributed_value
        contradiction = bool(
            (prediction and prediction.get("health") in {"at_risk", "critical"} and re.search(r"(?:modelo clasifica|predicción indica|prediccion indica).{0,30}(?:saludable|sin riesgo)", text))
            or (allowed_features and re.search(r"(?:no (?:hay|existen|se identifican) (?:señales|desviaciones|acciones)|sin señales prioritarias)", text))
            or re.search(r"(?:garantiza|garantizar|causado por|es la causa de)", text)
            or (context["status"] == "insufficient_evidence" and isinstance(summary, str) and not re.search(r"insuficien|completar|faltan|limitad", summary.lower()))
            or contrary_observation
        )
    actionability = schema_valid and all(_is_concrete_action(item["action"]) for item in recommendations or [])
    action_structure_valid = schema_valid and actionability
    follow_up_present = schema_valid and all(bool(item["follow_up"].strip()) for item in recommendations or [])
    follow_up_verifiable = follow_up_present and all(item["follow_up"].strip().lower().split()[0] in ACTION_VERBS | {"comprobar", "volver"} for item in recommendations or [])
    grounded = schema_valid and evidence_features_valid and provenance_valid and not contradiction and not unsupported_numeric_claim and not empty_with_risk and actionability and follow_up_verifiable
    if not schema_valid:
        failure_code = "invalid_schema"
        failure_detail = "Se esperaba summary textual y hasta cuatro recomendaciones con evidencia, razón y acción válidas."
    elif empty_with_risk:
        failure_code = "empty_recommendations_with_risk_drivers"
        failure_detail = "Hay drivers que aumentan riesgo, pero la respuesta no propuso recomendaciones."
    elif not evidence_features_valid:
        failure_code = "unknown_evidence_feature"
        failure_detail = "Una recomendación citó evidencia fuera de la lista permitida."
    elif not provenance_valid:
        failure_code = "invalid_evidence_provenance"
        failure_detail = "La procedencia no corresponde a la señal verificada o la evidencia está duplicada."
    elif contradiction:
        failure_code = "contradictory_claim"
        failure_detail = "La respuesta contradice la evidencia o afirma causalidad o garantías no demostradas."
    elif unsupported_numeric_claim:
        failure_code = "unsupported_numeric_claim"
        failure_detail = "La respuesta incluyó cifras que no aparecen en la evidencia estructurada."
    elif not actionability:
        failure_code = "non_actionable_recommendation"
        failure_detail = "Cada acción debe comenzar con un verbo y describir una tarea ejecutable y concreta."
    elif not follow_up_verifiable:
        failure_code = "non_verifiable_follow_up"
        failure_detail = "El seguimiento debe indicar una comprobación ejecutable, no solo una intención genérica."
    else:
        failure_code = None
        failure_detail = None
    return {
        "schema_valid": schema_valid,
        "evidence_features_valid": evidence_features_valid,
        "evidence_provenance_valid": provenance_valid,
        "contradictory_claim": contradiction,
        "referenced_evidence_features": sorted(set(referenced)),
        "allowed_evidence_features": sorted(allowed_features),
        "allowed_numeric_values": allowed_numbers,
        "allowed_numeric_percentages": allowed_percentages,
        "unsupported_numeric_claim": unsupported_numeric_claim,
        "actionability": actionability,
        "action_structure_valid": action_structure_valid,
        "follow_up_present": follow_up_present,
        "follow_up_verifiable": follow_up_verifiable,
        "grounded": grounded,
        "failure_code": failure_code,
        "failure_detail": failure_detail,
    }


def build_grounded_prompt(prediction: dict[str, Any], drivers: list[dict[str, Any]], *, row: dict[str, Any] | None = None) -> tuple[str, set[str]]:
    context = build_evidence_context(row or {}, prediction, drivers)
    allowed_features = {str(item["feature"]) for item in context["actionable_evidence"]}
    action_guidance = {
        feature: ACTION_GUIDANCE[feature]
        for feature in sorted(allowed_features)
        if feature in ACTION_GUIDANCE
    }
    compact = {
        **context,
        "risk_drivers": [item for item in context["model_drivers"] if item.get("direction") == "increases_risk"],
        "allowed_evidence_features": sorted(allowed_features),
        "action_guidance": action_guidance,
    }
    if allowed_features:
        example_signal = context["actionable_evidence"][0]
        example_feature = str(example_signal["feature"])
        example_guidance = ACTION_GUIDANCE.get(example_feature)
        if example_guidance:
            example_recommendations = [{
                **example_guidance,
                "evidence_feature": example_feature,
                "evidence_source": example_signal["source"],
                "reason": example_signal.get("reason") or f"{example_feature} aparece entre los drivers predictivos de riesgo; no demuestra causalidad.",
            }]
            example_summary = "Priorizar la revisión de la señal disponible."
        else:
            example_recommendations = []
            example_summary = "Priorizar la revisión de la señal disponible."
        response_example = {"summary": example_summary, "recommendations": example_recommendations}
        conditional_rule = (
            "La evidencia incluye señales verificadas de intervención. Es obligatorio devolver al menos una acción y está prohibido devolver recommendations vacías. "
            "Usa una o más de las señales exactas de allowed_evidence_features y no excedas cuatro acciones."
        )
    else:
        response_example = {
            "summary": "La evidencia es insuficiente; completar indicadores y líneas base." if context["status"] == "insufficient_evidence" else "No se identifican acciones correctivas prioritarias con la evidencia disponible; mantener seguimiento periódico.",
            "recommendations": [],
        }
        conditional_rule = "No hay señales verificadas de intervención; devuelve recommendations vacías. Si status es insufficient_evidence, informa insuficiencia, no ausencia de riesgo."
    prompt = (
        "/no_think\n"
        "Eres la capa de acciones de gestión de PRUNIN AI Core. Tu tarea NO es resumir el diagnóstico: convierte las señales permitidas en pasos concretos para el responsable del proyecto. "
        "No repitas nivel de riesgo, retraso o costo salvo que sea imprescindible para justificar una acción. Prioriza qué debería hacer ahora el responsable. "
        "No inventes causas, actividades observadas, hitos, ruta crítica, fechas, montos, porcentajes, personas, responsables nominales, contratos ni stakeholders. No afirmes causalidad. "
        "Cada acción empieza con un verbo, es ejecutable, se vincula a una señal, explica por qué y especifica qué revisar después. Usa action_guidance como referencia operativa, no como hechos adicionales. "
        "Solo puedes usar evidence_feature incluida en allowed_evidence_features. Evita números; si alguno fuera imprescindible, debe aparecer literalmente en EVIDENCIA. "
        "Conserva la pareja feature/source de actionable_evidence como evidence_feature/evidence_source. No confundas model_driver (sensibilidad local), observed_operational_signal (dato observado con regla heurística) ni heuristic_indicator (cálculo determinístico). "
        "Los drivers reduces_risk son contexto predictivo, no invalidan desviaciones operativas. Las acciones operativas no reclasifican Health ni afirman que el modelo utiliza esas variables. No dupliques una feature. "
        "Prioridad permitida: alta, media o baja; ordena alta, media, baja y prioriza SPI/CPI/capacidad cuando estén entre las señales más relevantes, sin inventar umbrales. "
        "Devuelve exclusivamente JSON válido, sin markdown ni texto adicional, con el mismo schema y nivel de concreción de este ejemplo: "
        + json.dumps(response_example, ensure_ascii=False, separators=(",", ":"))
        + ". " + conditional_rule + "\n"
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
    row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = model or os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    url = url or os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    timeout = ollama_timeout_seconds(timeout)
    context = build_evidence_context(row or {}, prediction, drivers)
    prompt, allowed_features = build_grounded_prompt(prediction, drivers, row=row)
    started = time.perf_counter()
    raw_response = ""
    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": action_response_schema(allowed_features, context),
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 1200},
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
        validation = validate_generated_payload(parsed, allowed_features, prediction=prediction, drivers=drivers, context=context)
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
        "action_structure_valid": False,
        "follow_up_present": False,
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
    context = build_evidence_context(row, prediction, drivers)
    risk_drivers = context["actionable_evidence"]
    recommendations: list[dict[str, str]] = []
    for driver in risk_drivers:
        name = str(driver.get("feature"))
        guidance = ACTION_GUIDANCE.get(name)
        if guidance is None:
            continue
        if any(item["evidence_feature"] == name for item in recommendations):
            continue
        recommendations.append({
            **guidance,
            "priority": driver.get("priority", guidance["priority"]),
            "evidence_feature": name,
            "evidence_source": driver["source"],
            "reason": driver.get("reason") or f"{driver.get('label', name)} aparece entre las señales que incrementan el riesgo en esta inferencia; esto muestra asociación, no causalidad.",
        })
    recommendations = sorted(recommendations, key=_recommendation_sort_key)[:4]
    actions = [item["action"] for item in recommendations]
    reasons = [item["reason"] for item in recommendations]
    evidence_features = [item["evidence_feature"] for item in recommendations]
    allowed_features = sorted({str(item["feature"]) for item in risk_drivers})
    if not risk_drivers:
        summary = "La evidencia disponible es insuficiente para descartar desviaciones; completar los indicadores y sus líneas base." if context["status"] == "insufficient_evidence" else "No se identifican acciones correctivas prioritarias con la evidencia disponible; mantener seguimiento periódico."
    elif not recommendations:
        summary = "No hay una acción de respaldo catalogada para estas señales; validar la evidencia con el equipo del proyecto."
    else:
        summary = "Estas acciones responden a las señales de mayor riesgo detectadas."
    result = {
        "engine": "grounded_fallback",
        "evidence_context": context,
        "evidence_status": context["status"],
        "genai_attempted": genai_attempted,
        "genai_used": False,
        "genai_failure_reason": genai_failure_reason or failure_detail or failure_code,
        "failure_code": failure_code,
        "failure_detail": failure_detail or genai_failure_reason,
        "genai_latency_ms": genai_latency_ms,
        "evidence_features": list(dict.fromkeys(evidence_features))[:5],
        "allowed_evidence_features": validation.get("allowed_evidence_features", allowed_features) if validation else allowed_features,
        "referenced_evidence_features": validation.get("referenced_evidence_features", []) if validation else [],
        "recommendations": recommendations,
        "fallback_validation": validate_generated_payload({"summary": summary, "recommendations": recommendations}, set(allowed_features), prediction=prediction, drivers=drivers, context=context),
        "reasons": reasons[:5],
        "actions": list(dict.fromkeys(actions))[:4],
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
    context = build_evidence_context(row, prediction, drivers)
    generated = generate_ollama_grounded(prediction, drivers, row=row)
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
    recs = sorted(generated["payload"]["recommendations"], key=_recommendation_sort_key)
    recommendation = {
        "engine": f"ollama:{generated['model']}",
        "evidence_context": context,
        "evidence_status": context["status"],
        "genai_attempted": True,
        "genai_used": True,
        "genai_failure_reason": None,
        "failure_code": None,
        "failure_detail": None,
        "genai_latency_ms": generated["latency_ms"],
        "evidence_features": generated["validation"]["referenced_evidence_features"],
        "allowed_evidence_features": generated["validation"]["allowed_evidence_features"],
        "referenced_evidence_features": generated["validation"]["referenced_evidence_features"],
        "recommendations": recs,
        "reasons": [item["reason"] for item in recs],
        "actions": [item["action"] for item in recs],
        "summary": generated["payload"].get("summary", ""),
        "latency_ms": generated["latency_ms"],
        "grounding": generated["validation"],
        "disclaimer": "Texto generado por IA sobre predicciones, datos observados y heurísticas identificados por su procedencia; validar antes de tomar decisiones.",
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
        "recommendations": [],
        "reasons": [],
        "actions": [],
        "summary": "No se solicitó una recomendación para esta inferencia.",
    }
