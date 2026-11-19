"""Pure logic for the Qwen3 8B vs. GPT-OSS 20B local comparison.

Everything here is deterministic and free of network calls so it can be tested
without Ollama. Inference lives in ``scripts/run_local_model_comparison.py``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

AUTHORIZED_MODELS: tuple[str, ...] = ("qwen3:8b", "gpt-oss:20b")
MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "qwen3:8b": {
        "display_name": "Qwen3 8B",
        "think": False,
        "think_rationale": "Qwen3 admite desactivar el razonamiento; es la configuración de producción de PRUNIN.",
    },
    "gpt-oss:20b": {
        "display_name": "GPT-OSS 20B",
        "think": "low",
        "think_rationale": "GPT-OSS no permite desactivar el razonamiento: con think=false Ollama devuelve contenido vacío. Se usa el nivel mínimo admitido (low).",
    },
}
EXPECTED_CASES = 30
REPEAT_CASES = 5
DEFAULT_REPEATS = 3
TEMPERATURE = 0.1
NUM_PREDICT = 1200
DECISION_WEIGHTS: dict[str, float] = {
    "grounding": 0.30,
    "actionability": 0.25,
    "json_compliance": 0.15,
    "latency": 0.10,
    "robustness": 0.10,
    "repeatability": 0.10,
}
CRITERION_LABELS = {
    "grounding": "Grounding",
    "actionability": "Accionabilidad",
    "json_compliance": "Cumplimiento JSON",
    "latency": "Latencia",
    "robustness": "Robustez",
    "repeatability": "Repetibilidad",
}
DEFENSIBLE_MARGIN = 0.03
OPERATIONAL_FAILURES = {"ollama_timeout", "ollama_unavailable", "http_error"}
PRIORITY_ORDER = {"alta": 0, "media": 1, "baja": 2}
REPEAT_SALT = "prunin-repeat-v1"


class UnauthorizedModelError(ValueError):
    """Raised when a model outside the approved comparison is requested."""


def validate_model_selection(models: Iterable[str]) -> list[str]:
    selected = list(dict.fromkeys(str(model).strip() for model in models))
    unauthorized = [model for model in selected if model not in AUTHORIZED_MODELS]
    if unauthorized:
        raise UnauthorizedModelError(
            f"Modelos no autorizados para esta comparación: {', '.join(unauthorized)}. Solo se admiten {', '.join(AUTHORIZED_MODELS)}."
        )
    if sorted(selected) != sorted(AUTHORIZED_MODELS):
        raise UnauthorizedModelError(f"La comparación exige exactamente {', '.join(AUTHORIZED_MODELS)}.")
    return [model for model in AUTHORIZED_MODELS if model in selected]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def select_repeat_cases(case_ids: list[str], count: int = REPEAT_CASES) -> list[str]:
    """Deterministic, content-independent selection: lowest salted SHA-256 of the case id."""
    if count > len(case_ids):
        raise ValueError("No hay suficientes casos para la prueba de repetibilidad.")
    return sorted(case_ids, key=lambda case_id: sha256_text(f"{REPEAT_SALT}:{case_id}"))[:count]


def check_split_isolation(case_ids: list[str], split: dict[str, Any]) -> dict[str, Any]:
    test, train = set(map(str, split.get("test", []))), set(map(str, split.get("train", [])))
    validation = set(map(str, split.get("validation", split.get("val", []))))
    cases = set(map(str, case_ids))
    result = {
        "all_cases_in_test": cases <= test,
        "train_overlap": sorted(cases & train),
        "validation_overlap": sorted(cases & validation),
        "unique_cases": len(cases) == len(case_ids),
    }
    result["ok"] = result["all_cases_in_test"] and not result["train_overlap"] and not result["validation_overlap"] and result["unique_cases"]
    return result


def priority_order_valid(payload: Any) -> bool:
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else None
    if not isinstance(recommendations, list):
        return False
    ranks = []
    for item in recommendations:
        priority = item.get("priority") if isinstance(item, dict) else None
        if priority not in PRIORITY_ORDER:
            return False
        ranks.append(PRIORITY_ORDER[priority])
    return ranks == sorted(ranks)


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    return sum(bool(row.get(key)) for row in rows) / len(rows) if rows else None


def repeatability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Consistency of repeated generations for the same case and model."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["case_id"]), []).append(row)
    if not groups:
        return {"cases": 0, "repeats_per_case": 0, "consistent_case_rate": None, "outcome_agreement_rate": None, "identical_response_rate": None}
    consistent = outcome = identical = 0
    for items in groups.values():
        signatures = {(bool(item.get("grounded")), tuple(item.get("referenced_features") or []), tuple(item.get("priorities") or [])) for item in items}
        consistent += len(signatures) == 1
        outcome += len({bool(item.get("grounded")) for item in items}) == 1
        identical += len({item.get("response_sha256") for item in items}) == 1
    total = len(groups)
    return {
        "cases": total,
        "repeats_per_case": min(len(items) for items in groups.values()),
        "consistent_case_rate": consistent / total,
        "outcome_agreement_rate": outcome / total,
        "identical_response_rate": identical / total,
    }


def summarize_model(main_rows: list[dict[str, Any]], repeat_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = main_rows
    latencies = [float(row["latency_ms"]) for row in rows]
    all_rows = main_rows + repeat_rows
    eval_tokens = sum(int(row.get("completion_tokens") or 0) for row in rows if row.get("eval_duration_ns"))
    eval_seconds = sum(int(row.get("eval_duration_ns") or 0) for row in rows) / 1e9
    operational_failures = sum(row.get("failure_code") in OPERATIONAL_FAILURES for row in all_rows)
    return {
        "requests_main": len(rows),
        "requests_repeat": len(repeat_rows),
        "accepted": sum(bool(row.get("grounded")) for row in rows),
        "accepted_rate": _rate(rows, "grounded"),
        "json_valid_rate": _rate(rows, "json_parsed"),
        "schema_valid_rate": _rate(rows, "schema_valid"),
        "grounded_rate": _rate(rows, "grounded"),
        "unsupported_numeric_claim_rate": _rate(rows, "unsupported_numeric_claim"),
        "contradiction_rate": _rate(rows, "contradictory_claim"),
        "actionability_rate": _rate(rows, "actionability"),
        "priority_valid_rate": _rate(rows, "priority_valid"),
        "follow_up_verifiable_rate": _rate(rows, "follow_up_verifiable"),
        "operational_error_rate": operational_failures / len(all_rows) if all_rows else None,
        "timeouts": sum(row.get("failure_code") == "ollama_timeout" for row in all_rows),
        "failures": sum(not row.get("grounded") for row in rows),
        "failure_codes": dict(sorted(_count(row.get("failure_code") for row in rows if row.get("failure_code")).items())),
        "latency_ms_mean": statistics.fmean(latencies) if latencies else None,
        "latency_ms_median": statistics.median(latencies) if latencies else None,
        "latency_ms_p95": percentile(latencies, 0.95),
        "latency_ms_max": max(latencies) if latencies else None,
        "tokens_per_second": eval_tokens / eval_seconds if eval_seconds else None,
        "completion_tokens_mean": statistics.fmean([int(row.get("completion_tokens") or 0) for row in rows]) if rows else None,
        "thinking_chars_mean": statistics.fmean([int(row.get("thinking_chars") or 0) for row in rows]) if rows else None,
        "repeatability": repeatability(repeat_rows),
    }


def _count(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def criterion_scores(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Normalize every criterion to [0, 1] where 1 is best.

    Quality criteria are already proportions. Latency uses ratio normalization
    (fastest median / model median) so the fastest model gets 1.0 and scores are
    not exaggerated by min-max scaling between only two models.
    """
    medians = {model: values["latency_ms_median"] for model, values in metrics.items() if values.get("latency_ms_median")}
    fastest = min(medians.values()) if medians else None
    scores: dict[str, dict[str, float]] = {}
    for model, values in metrics.items():
        median = values.get("latency_ms_median")
        scores[model] = {
            "grounding": float(values.get("grounded_rate") or 0.0),
            "actionability": statistics.fmean([
                float(values.get("actionability_rate") or 0.0),
                float(values.get("priority_valid_rate") or 0.0),
                float(values.get("follow_up_verifiable_rate") or 0.0),
            ]),
            "json_compliance": statistics.fmean([float(values.get("json_valid_rate") or 0.0), float(values.get("schema_valid_rate") or 0.0)]),
            "latency": float(fastest / median) if fastest and median else 0.0,
            "robustness": 1.0 - float(values.get("operational_error_rate") or 0.0),
            "repeatability": float((values.get("repeatability") or {}).get("consistent_case_rate") or 0.0),
        }
    return scores


def weighted_totals(scores: dict[str, dict[str, float]], weights: dict[str, float]) -> dict[str, float]:
    total_weight = sum(weights.values())
    if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        raise ValueError(f"Los pesos deben sumar 1.0; suman {total_weight}.")
    return {model: sum(weights[key] * values[key] for key in weights) for model, values in scores.items()}


def _normalized(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _winner(totals: dict[str, float], tolerance: float = 1e-9) -> str | None:
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if len(ranked) < 2 or ranked[0][1] - ranked[1][1] <= tolerance:
        return None
    return ranked[0][0]


def sensitivity_scenarios(base: dict[str, float] = DECISION_WEIGHTS) -> dict[str, dict[str, float]]:
    scenarios = {
        "base": dict(base),
        "pesos_iguales": _normalized({key: 1.0 for key in base}),
        "sin_latencia": _normalized({**base, "latency": 0.0}),
        "latencia_x2": _normalized({**base, "latency": base["latency"] * 2}),
    }
    for key in base:
        scenarios[f"{key}_+50%"] = _normalized({**base, key: base[key] * 1.5})
        scenarios[f"{key}_-50%"] = _normalized({**base, key: base[key] * 0.5})
    return scenarios


def mcnemar_exact(first: list[bool], second: list[bool]) -> dict[str, Any]:
    if len(first) != len(second):
        raise ValueError("McNemar requiere resultados pareados.")
    only_first = sum(a and not b for a, b in zip(first, second))
    only_second = sum(b and not a for a, b in zip(first, second))
    discordant = only_first + only_second
    if discordant == 0:
        return {"only_first": 0, "only_second": 0, "p_value": 1.0}
    tail = sum(math.comb(discordant, index) for index in range(min(only_first, only_second) + 1)) / 2 ** discordant
    return {"only_first": only_first, "only_second": only_second, "p_value": min(1.0, 2 * tail)}


def decide(metrics: dict[str, dict[str, Any]], *, evidence_complete: bool, paired_grounded: dict[str, list[bool]] | None = None) -> dict[str, Any]:
    scores = criterion_scores(metrics)
    totals = weighted_totals(scores, DECISION_WEIGHTS)
    scenarios = []
    for name, weights in sensitivity_scenarios().items():
        scenario_totals = weighted_totals(scores, weights)
        scenarios.append({"scenario": name, "weights": weights, "totals": scenario_totals, "winner": _winner(scenario_totals)})
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 0.0
    base_winner = _winner(totals)
    stable = base_winner is not None and all(item["winner"] == base_winner for item in scenarios)
    significance = None
    if paired_grounded and len(paired_grounded) == 2:
        first, second = (paired_grounded[model] for model in AUTHORIZED_MODELS)
        significance = {"test": "McNemar exacto sobre aceptación pareada (30 casos)", "first_model": AUTHORIZED_MODELS[0], "second_model": AUTHORIZED_MODELS[1], **mcnemar_exact(first, second)}
    reasons = []
    if not evidence_complete:
        reasons.append("La evidencia está incompleta; no se declara ganador.")
    if base_winner is None:
        reasons.append("Los puntajes ponderados están empatados.")
    elif margin < DEFENSIBLE_MARGIN:
        reasons.append(f"La diferencia ponderada ({margin:.3f}) es menor que el margen defendible ({DEFENSIBLE_MARGIN:.2f}).")
    if base_winner is not None and not stable:
        changed = [item["scenario"] for item in scenarios if item["winner"] != base_winner]
        reasons.append("El ganador cambia en el análisis de sensibilidad: " + ", ".join(changed) + ".")
    defensible = evidence_complete and base_winner is not None and margin >= DEFENSIBLE_MARGIN and stable
    return {
        "weights": dict(DECISION_WEIGHTS),
        "weights_sum": sum(DECISION_WEIGHTS.values()),
        "normalization": {
            "grounding": "Tasa de respuestas aceptadas por el validador (grounded_rate).",
            "actionability": "Media de actionability_rate, priority_valid_rate y follow_up_verifiable_rate.",
            "json_compliance": "Media de json_valid_rate y schema_valid_rate.",
            "latency": "Mediana más rápida / mediana del modelo (1.0 = más rápido).",
            "robustness": "1 − tasa de fallos operativos (timeout, indisponibilidad, HTTP) en corridas principal y de repetición.",
            "repeatability": "Proporción de casos repetidos con igual aceptación, señales citadas y prioridades en todas las repeticiones.",
        },
        "scores": scores,
        "totals": totals,
        "ranking": [model for model, _ in ranked],
        "margin": margin,
        "defensible_margin": DEFENSIBLE_MARGIN,
        "sensitivity": scenarios,
        "stable_under_sensitivity": stable,
        "significance": significance,
        "evidence_complete": evidence_complete,
        "winner": base_winner if defensible else None,
        "defensible": defensible,
        "reasons": reasons or [f"{base_winner} supera por {margin:.3f} puntos ponderados y se mantiene en todos los escenarios de sensibilidad."],
    }


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read checkpoint rows verifying the per-row digest. A truncated final line is tolerated."""
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    if not path.exists():
        return rows, problems
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                problems.append("truncated_last_line_ignored")
                continue
            raise ValueError(f"Línea {index + 1} de {path.name} corrupta; no se puede reanudar con integridad.")
        digest = record.pop("row_sha256", None)
        if digest != sha256_text(canonical_json(record)):
            raise ValueError(f"La línea {index + 1} de {path.name} no coincide con su huella SHA-256.")
        rows.append(record)
    return rows, problems


def row_key(row: dict[str, Any]) -> tuple[str, str, str, int]:
    return (str(row["model"]), str(row["phase"]), str(row["case_id"]), int(row.get("repeat") or 0))


def expected_keys(models: list[str], case_ids: list[str], repeat_case_ids: list[str], repeats: int) -> list[tuple[str, str, str, int]]:
    keys = []
    for model in models:
        keys.extend((model, "main", case_id, 1) for case_id in case_ids)
        keys.extend((model, "repeat", case_id, repeat) for repeat in range(1, repeats + 1) for case_id in repeat_case_ids)
    return keys


def completeness(rows: list[dict[str, Any]], models: list[str], case_ids: list[str], repeat_case_ids: list[str], repeats: int) -> dict[str, Any]:
    present = [row_key(row) for row in rows if row.get("phase") in {"main", "repeat"}]
    expected = expected_keys(models, case_ids, repeat_case_ids, repeats)
    duplicates = len(present) - len(set(present))
    missing = sorted(set(expected) - set(present))
    unexpected = sorted(set(present) - set(expected))
    return {
        "expected": len(expected),
        "present": len(set(present)),
        "missing": len(missing),
        "duplicates": duplicates,
        "unexpected": len(unexpected),
        "complete": not missing and not duplicates and not unexpected,
    }


def validate_comparison_dir(directory: Path) -> dict[str, Any]:
    """Verify a finished comparison before anything is shown or cited."""
    errors: list[str] = []
    manifest_path, summary_path = directory / "execution_manifest.json", directory / "benchmark_summary.json"
    if not manifest_path.exists() or not summary_path.exists():
        return {"valid": False, "status": "not_available", "errors": ["No existe una comparación generada."]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status != "complete":
        errors.append(f"Estado del experimento: {status}.")
    if manifest.get("models") != list(AUTHORIZED_MODELS):
        errors.append("Los modelos del manifiesto no coinciden con la comparación autorizada.")
    case_ids = manifest.get("case_ids") or []
    if len(case_ids) != EXPECTED_CASES or len(set(case_ids)) != EXPECTED_CASES:
        errors.append("El manifiesto no registra exactamente 30 casos TEST únicos.")
    for name, digest in (manifest.get("output_sha256") or {}).items():
        path = directory / name
        if not path.exists() or sha256_file(path) != digest:
            errors.append(f"La huella de {name} no coincide con el manifiesto.")
    if status == "complete" and not manifest.get("output_sha256"):
        errors.append("El manifiesto completo no registra huellas de salida.")
    raw = directory / "benchmark_raw.csv"
    if raw.exists() and status == "complete":
        with raw.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for model in AUTHORIZED_MODELS:
            main = [row["case_id"] for row in rows if row["model"] == model and row["phase"] == "main"]
            if sorted(main) != sorted(case_ids):
                errors.append(f"{model}: los casos principales no coinciden con los 30 casos del manifiesto.")
            repeat = [row for row in rows if row["model"] == model and row["phase"] == "repeat"]
            if len(repeat) != len(manifest.get("repeat_case_ids") or []) * int(manifest.get("repeats") or 0):
                errors.append(f"{model}: la prueba de repetibilidad está incompleta.")
    return {"valid": not errors, "status": status, "errors": errors}


def load_public_comparison(directory: Path) -> dict[str, Any]:
    """Sanitized, read-only view for the API. Never exposes filesystem paths."""
    check = validate_comparison_dir(directory)
    if check["status"] == "not_available":
        return {"status": "not_available", "valid": False, "errors": check["errors"]}
    summary = json.loads((directory / "benchmark_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "execution_manifest.json").read_text(encoding="utf-8"))
    decision = summary.get("decision") or {}
    return {
        "status": check["status"],
        "valid": check["valid"],
        "errors": check["errors"],
        "experiment_id": manifest.get("experiment_id"),
        "finished_utc": manifest.get("finished_utc"),
        "cases": len(manifest.get("case_ids") or []),
        "repeat_cases": len(manifest.get("repeat_case_ids") or []),
        "repeats": manifest.get("repeats"),
        "hardware": {key: manifest.get("hardware", {}).get(key) for key in ("chip", "memory_gb", "platform")},
        "ollama_version": manifest.get("ollama_version"),
        "models": {
            model: {
                "display_name": MODEL_PROFILES[model]["display_name"],
                "metadata": {key: (manifest.get("model_metadata", {}).get(model) or {}).get(key) for key in ("digest", "parameter_size", "quantization_level", "family", "context_length", "size_bytes")},
                "metrics": {key: value for key, value in (summary.get("models", {}).get(model, {}).get("metrics") or {}).items() if key != "failure_codes"},
                "resources": summary.get("models", {}).get(model, {}).get("resources"),
                "think": MODEL_PROFILES[model]["think"],
            }
            for model in AUTHORIZED_MODELS
        },
        "decision": {
            "weights": decision.get("weights"),
            "scores": decision.get("scores"),
            "totals": decision.get("totals"),
            "margin": decision.get("margin"),
            "stable_under_sensitivity": decision.get("stable_under_sensitivity"),
            "significance": decision.get("significance"),
            "winner": decision.get("winner") if check["valid"] else None,
            "defensible": bool(decision.get("defensible")) and check["valid"],
            "reasons": decision.get("reasons"),
        },
        "configuration_differences": manifest.get("configuration_differences"),
        "human_evaluation": "No realizada: todas las métricas son automáticas.",
    }
