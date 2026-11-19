#!/usr/bin/env python3
"""Controlled and operational OpenAI vs Ollama comparison for PRUNIN (R6.1-Cr2).

Credentials are read only from the process environment and never written to outputs.
A provider that is unavailable is recorded with its real failure; no rows are fabricated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

OUTPUT_NAMES = [
    "benchmark_cases.csv", "benchmark_results.csv", "benchmark_summary.json", "comparison_report.md",
    "execution_manifest.json", "latency_comparison.png", "grounding_comparison.png",
    "actionability_comparison.png", "cost_comparison.png",
]

# USD per 1M tokens, verified 2026-11-18 at https://developers.openai.com/api/docs/models/gpt-4.1
OPENAI_PRICING = {"gpt-4.1": {"input": 2.0, "output": 8.0, "source": "https://developers.openai.com/api/docs/models/gpt-4.1", "verified": "2026-11-18"}}

# Controlled: identical task contract for both providers. Operational: as PRUNIN ships.
MODES = {
    "controlled": {"openai": {"max_actions": 4, "max_summary_chars": 180}, "ollama": {"max_actions": 4, "max_summary_chars": 180}},
    "operational": {"openai": {"max_actions": 8, "max_summary_chars": 1200}, "ollama": {"max_actions": 4, "max_summary_chars": 180}},
}


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetGuard:
    """Estimated-cost guard. It is not a billing limit enforced by OpenAI."""

    limit_usd: float
    input_per_million: float
    output_per_million: float
    margin: float = 1.5
    reserved_output_tokens: int = 4000
    spent_usd: float = 0.0
    calls: int = 0
    blocked_calls: int = 0
    unmetered_calls: int = 0
    history: list[float] = field(default_factory=list)

    def cost(self, prompt_tokens: float, completion_tokens: float) -> float:
        return (prompt_tokens * self.input_per_million + completion_tokens * self.output_per_million) / 1_000_000

    def reserve(self, prompt_text: str) -> float:
        # ~3 characters per token over-estimates Spanish JSON prompts conservatively.
        reservation = self.cost(math.ceil(len(prompt_text) / 3), self.reserved_output_tokens) * self.margin
        if self.spent_usd + reservation > self.limit_usd:
            self.blocked_calls += 1
            raise BudgetExceeded(f"Presupuesto estimado agotado: gastado {self.spent_usd:.4f} USD, reserva {reservation:.4f} USD, límite {self.limit_usd:.2f} USD.")
        return reservation

    def settle(self, usage: dict[str, Any] | None, reservation: float) -> float:
        prompt_tokens = (usage or {}).get("prompt_tokens")
        completion_tokens = (usage or {}).get("completion_tokens")
        if isinstance(prompt_tokens, (int, float)) and isinstance(completion_tokens, (int, float)):
            actual = self.cost(prompt_tokens, completion_tokens)
        else:
            # Without usage the request may still be billed; keep the conservative reservation.
            actual = reservation
            self.unmetered_calls += 1
        self.spent_usd += actual
        self.calls += 1
        self.history.append(actual)
        return actual

    def snapshot(self) -> dict[str, Any]:
        return {
            "limit_usd": self.limit_usd, "estimated_spent_usd": round(self.spent_usd, 6), "calls": self.calls,
            "blocked_calls": self.blocked_calls, "calls_without_usage": self.unmetered_calls, "margin": self.margin,
            "reserved_output_tokens_per_call": self.reserved_output_tokens,
            "note": "Contador de costo estimado previo a cada llamada; no equivale a un límite de facturación garantizado por OpenAI.",
        }


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def diagnose_openai(model: str, *, get: Callable[..., Any] = requests.get) -> dict[str, Any]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    report: dict[str, Any] = {"provider": "openai", "model": model, "key_present_in_process_env": bool(key), "pricing": OPENAI_PRICING.get(model)}
    if not key:
        report.update(available=False, failure_code="openai_key_missing", detail="OPENAI_API_KEY no existe en el entorno del proceso que ejecuta el benchmark.")
        return report
    try:
        response = get(f"https://api.openai.com/v1/models/{model}", headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except requests.exceptions.RequestException as exc:
        report.update(available=False, failure_code="openai_unavailable", detail=type(exc).__name__)
        return report
    report["http_status"] = response.status_code
    codes = {401: "openai_auth_error", 403: "openai_permission_error", 404: "openai_model_unavailable", 429: "openai_rate_limit"}
    if response.status_code >= 400:
        report.update(available=False, failure_code=codes.get(response.status_code, "openai_http_error"), detail=f"HTTP {response.status_code}")
        return report
    report.update(available=True, model_owner=(response.json() or {}).get("owned_by"))
    if model not in OPENAI_PRICING:
        report.update(available=False, failure_code="pricing_unverified", detail="No hay tarifa verificada para controlar el presupuesto de este modelo.")
    return report


def diagnose_ollama(model: str, url: str, *, get: Callable[..., Any] = requests.get, post: Callable[..., Any] = requests.post) -> dict[str, Any]:
    base = url.rsplit("/api/", 1)[0]
    report: dict[str, Any] = {"provider": "ollama", "model": model, "url": url}
    try:
        tags = get(f"{base}/api/tags", timeout=5)
        tags.raise_for_status()
        models = {item.get("name"): item for item in tags.json().get("models", []) if isinstance(item, dict)}
        version = get(f"{base}/api/version", timeout=5).json().get("version")
    except (requests.exceptions.RequestException, ValueError) as exc:
        report.update(available=False, failure_code="ollama_unavailable", detail=type(exc).__name__)
        return report
    report["installed_models"] = sorted(name for name in models if name)
    report["ollama_version"] = version
    entry = models.get(model) or models.get(f"{model}:latest")
    if not entry:
        report.update(available=False, failure_code="ollama_model_missing", detail=f"{model} no está instalado.")
        return report
    details = entry.get("details") or {}
    report.update(
        available=True, digest=entry.get("digest"), size_bytes=entry.get("size"),
        parameter_size=details.get("parameter_size"), quantization=details.get("quantization_level"), family=details.get("family"),
    )
    return report


def build_case_evidence(case: dict[str, Any], *, max_actions: int, max_summary_chars: int) -> dict[str, Any]:
    from prunin_ai.api.operational_signals import build_evidence_context
    from prunin_ai.api.recommendations import build_grounded_prompt

    prompt, allowed = build_grounded_prompt(case["prediction"], case["drivers"], row=case["input"], max_actions=max_actions, max_summary_chars=max_summary_chars)
    context = build_evidence_context(case["input"], case["prediction"], case["drivers"])
    evidence = json.dumps(context["actionable_evidence"], ensure_ascii=False, sort_keys=True, default=str)
    return {"prompt": prompt, "allowed_features": sorted(allowed), "evidence_json": evidence, "evidence_status": context.get("status")}


def call_provider(provider: str, case: dict[str, Any], config: dict[str, int], settings: dict[str, Any]) -> dict[str, Any]:
    from prunin_ai.api.recommendations import generate_ollama_grounded, generate_openai_grounded

    kwargs = {"row": case["input"], **config}
    if provider == "openai":
        return generate_openai_grounded(case["prediction"], case["drivers"], model=settings["openai_model"], **kwargs)
    return generate_ollama_grounded(case["prediction"], case["drivers"], model=settings["ollama_model"], url=settings["ollama_url"], timeout=settings["ollama_timeout"], **kwargs)


def result_row(case: dict[str, Any], provider: str, mode: str, repeat: int, result: dict[str, Any], evidence: dict[str, Any], *, model_version: str | None, cost_usd: float | None) -> dict[str, Any]:
    validation = result.get("validation") or {}
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
    actions = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else []
    usage = result.get("usage") or {}
    failure = result.get("failure_code")
    grounded = bool(validation.get("grounded"))
    return {
        "project_id": case["case_id"], "provider": provider, "mode": mode, "repeat": repeat,
        "model": result.get("model"), "model_version": model_version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "health": case["prediction"].get("health"), "evidence_sha256": sha256_text(evidence["evidence_json"]),
        "prompt_sha256": sha256_text(evidence["prompt"]),
        "response": result.get("raw_response") or "",
        "generation_success": result.get("payload") is not None,
        "schema_valid": bool(validation.get("schema_valid")),
        "grounded": grounded,
        "evidence_supported": bool(validation.get("evidence_features_valid")) and bool(validation.get("evidence_provenance_valid", validation.get("evidence_features_valid"))),
        "unsupported_numeric_claim": bool(validation.get("unsupported_numeric_claim")),
        "contradiction": bool(validation.get("contradictory_claim")),
        "actionability": bool(validation.get("actionability")),
        "follow_up_verifiable": bool(validation.get("follow_up_verifiable")),
        "actions_generated": len(actions),
        # PRUNIN accepts the whole payload only when it is grounded; otherwise it uses the fallback.
        "actions_accepted": len(actions) if grounded else 0,
        "referenced_features": ";".join(validation.get("referenced_evidence_features") or []),
        "failure_code": failure or "",
        "timeout": failure in {"ollama_timeout", "openai_timeout"},
        "latency_ms": float(result.get("latency_ms") or 0.0),
        "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
        "cost_usd": cost_usd,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"requests_total": 0}
    count = len(rows)
    rate = lambda key: round(sum(bool(row[key]) for row in rows) / count, 4)
    latencies = [row["latency_ms"] for row in rows]
    costs = [row["cost_usd"] for row in rows if isinstance(row.get("cost_usd"), (int, float))]
    by_case: dict[str, list[float]] = {}
    for row in rows:
        by_case.setdefault(row["project_id"], []).append(row["latency_ms"])
    tokens_out = [row["completion_tokens"] for row in rows if isinstance(row.get("completion_tokens"), (int, float))]
    return {
        "requests_total": count,
        "success_rate": rate("generation_success"),
        "failure_rate": round(1 - sum(bool(row["generation_success"]) for row in rows) / count, 4),
        "timeout_rate": rate("timeout"),
        "schema_valid_rate": rate("schema_valid"),
        "grounded_response_rate": rate("grounded"),
        "evidence_supported_rate": rate("evidence_supported"),
        "unsupported_numeric_claim_rate": rate("unsupported_numeric_claim"),
        "contradiction_rate": rate("contradiction"),
        "actionability_rate": rate("actionability"),
        "follow_up_verifiable_rate": rate("follow_up_verifiable"),
        "actions_generated_mean": round(statistics.mean(row["actions_generated"] for row in rows), 3),
        "actions_accepted_mean": round(statistics.mean(row["actions_accepted"] for row in rows), 3),
        "latency_ms_mean": round(statistics.mean(latencies), 2),
        "latency_ms_median": round(statistics.median(latencies), 2),
        "latency_ms_p95": round(percentile(latencies, 0.95) or 0.0, 2),
        "latency_ms_min": round(min(latencies), 2), "latency_ms_max": round(max(latencies), 2),
        "latency_ms_stdev": round(statistics.pstdev(latencies), 2),
        "completion_tokens_median": statistics.median(tokens_out) if tokens_out else None,
        "cost_usd_total": round(sum(costs), 6) if costs else None,
        "cost_usd_mean": round(statistics.mean(costs), 6) if costs else None,
        "per_case_latency_cv_median": round(statistics.median(
            statistics.pstdev(values) / statistics.mean(values) for values in by_case.values() if len(values) > 1 and statistics.mean(values) > 0
        ), 4) if any(len(values) > 1 for values in by_case.values()) else None,
    }


def repeatability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["provider"], row["project_id"]), []).append(row)
    summary: dict[str, Any] = {}
    for provider in sorted({key[0] for key in groups}):
        cases = [items for (name, _), items in groups.items() if name == provider and len(items) > 1]
        if not cases:
            continue
        summary[provider] = {
            "cases": len(cases), "runs_per_case": min(len(items) for items in cases),
            "identical_response_rate": round(sum(len({item["response"] for item in items}) == 1 for items in cases) / len(cases), 4),
            "stable_schema_rate": round(sum(len({item["schema_valid"] for item in items}) == 1 for items in cases) / len(cases), 4),
            "stable_acceptance_rate": round(sum(len({item["grounded"] for item in items}) == 1 for items in cases) / len(cases), 4),
            "stable_feature_set_rate": round(sum(len({item["referenced_features"] for item in items}) == 1 for items in cases) / len(cases), 4),
            "action_count_range_median": statistics.median(max(i["actions_generated"] for i in items) - min(i["actions_generated"] for i in items) for items in cases),
            "latency_cv_median": round(statistics.median(
                (statistics.pstdev([i["latency_ms"] for i in items]) / statistics.mean([i["latency_ms"] for i in items])) if statistics.mean([i["latency_ms"] for i in items]) else 0.0 for items in cases
            ), 4),
        }
    return summary


def run(
    cases: list[dict[str, Any]], providers: dict[str, dict[str, Any]], settings: dict[str, Any], *,
    repeat_cases: int, repeats: int, budget: BudgetGuard | None, caller: Callable[..., dict[str, Any]] = call_provider,
    log: Callable[[str], None] = print,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    stops: list[dict[str, Any]] = []
    plan = [(mode, case, 1) for mode in MODES for case in cases]
    plan += [("repeatability", case, run_index) for case in cases[:repeat_cases] for run_index in range(1, repeats + 1)]
    for provider, diagnosis in providers.items():
        if not diagnosis.get("available"):
            continue
        version = diagnosis.get("digest") or diagnosis.get("model")
        for mode, case, repeat in plan:
            config = MODES["controlled" if mode == "repeatability" else mode][provider]
            evidence = build_case_evidence(case, **config)
            reservation = 0.0
            if provider == "openai" and budget is not None:
                try:
                    reservation = budget.reserve(evidence["prompt"])
                except BudgetExceeded as exc:
                    stops.append({"provider": provider, "mode": mode, "project_id": case["case_id"], "reason": str(exc)})
                    log(f"[budget] {exc}")
                    break
            result = caller(provider, case, config, settings)
            cost = budget.settle(result.get("usage"), reservation) if provider == "openai" and budget is not None else None
            rows.append(result_row(case, provider, mode, repeat, result, evidence, model_version=version, cost_usd=cost))
            log(f"[{provider}/{mode}] {case['case_id']} r{repeat}: grounded={rows[-1]['grounded']} {rows[-1]['latency_ms']:.0f} ms {rows[-1]['failure_code']}")
    return rows, stops


def summarize(rows: list[dict[str, Any]], providers: dict[str, dict[str, Any]], stops: list[dict[str, Any]], budget: BudgetGuard | None) -> dict[str, Any]:
    summary: dict[str, Any] = {"providers": {}, "budget": budget.snapshot() if budget else None, "budget_stops": stops}
    for provider, diagnosis in providers.items():
        entry: dict[str, Any] = {"available": bool(diagnosis.get("available")), "diagnosis": diagnosis}
        if diagnosis.get("available"):
            for mode in (*MODES, "repeatability"):
                entry[mode] = aggregate([row for row in rows if row["provider"] == provider and row["mode"] == mode])
        summary["providers"][provider] = entry
    summary["repeatability"] = repeatability([row for row in rows if row["mode"] == "repeatability"])
    summary["comparison_status"] = "complete" if all(p.get("available") for p in providers.values()) else "incomplete_provider_unavailable"
    return summary


def plot(rows: list[dict[str, Any]], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = sorted({(row["provider"], row["mode"]) for row in rows if row["mode"] != "repeatability"})
    names = [f"{p}\n{m}" for p, m in labels]
    groups = [[row for row in rows if (row["provider"], row["mode"]) == key] for key in labels]

    def bar(filename: str, title: str, values: list[float], ylabel: str) -> None:
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.bar(names, values, color="#3b6ea5")
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        for index, value in enumerate(values):
            axis.annotate(f"{value:.2f}", (index, value), ha="center", va="bottom")
        fig.tight_layout()
        fig.savefig(output / filename, dpi=140)
        plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 4))
    if groups:
        axis.boxplot([[row["latency_ms"] / 1000 for row in group] for group in groups], tick_labels=names)
    axis.set_title("Latencia por proveedor y modo (s)")
    axis.set_ylabel("segundos")
    fig.tight_layout()
    fig.savefig(output / "latency_comparison.png", dpi=140)
    plt.close(fig)
    bar("grounding_comparison.png", "Tasa de respuestas fundamentadas", [sum(r["grounded"] for r in g) / len(g) for g in groups], "proporción")
    bar("actionability_comparison.png", "Acciones aceptadas por caso (media)", [statistics.mean(r["actions_accepted"] for r in g) for g in groups], "acciones")
    bar("cost_comparison.png", "Costo total estimado (USD)", [sum(r["cost_usd"] or 0.0 for r in g) for g in groups], "USD")


DECISION_CRITERIA = [
    ("Privacidad", "Datos permanecen en el equipo", "Indicadores se transfieren al proveedor externo"),
    ("Ejecución local / conectividad", "Funciona sin Internet", "Requiere conectividad y disponibilidad del servicio"),
    ("Recursos computacionales", "Requiere ~5,2 GB y CPU/GPU local", "Sin carga local; depende de cuota y límites"),
    ("Costo variable", "Sin costo por token; costo de hardware/energía", "Costo por token medido en este benchmark"),
    ("Seguridad de credenciales", "No requiere clave", "Requiere custodia de clave y control de presupuesto"),
    ("Mantenibilidad", "Versionado por digest del modelo local", "Los modelos de API tienen ciclo de vida y pueden retirarse; el modelo es configurable"),
    ("Escalabilidad", "Limitada por el hardware del servidor", "Escala con límites de tasa del proveedor"),
]


def render_report(summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "# Comparación experimental OpenAI vs. Ollama — PRUNIN AI Core",
        "",
        f"Ejecución: {manifest['started_utc']} → {manifest['finished_utc']} · commit `{manifest['git_commit']}` · artefacto `{manifest['artifact_version']}`.",
        "",
        "Criterio académico: **R6.1-Cr2** (selección del modelo generativo) y **R6.1-Cr4** (interpretación de la evaluación).",
        "",
        "## Disponibilidad real de proveedores",
        "",
        "| Proveedor | Modelo | Disponible | Diagnóstico |",
        "|---|---|---|---|",
    ]
    for name, entry in summary["providers"].items():
        diag = entry["diagnosis"]
        detail = diag.get("failure_code") or f"digest `{str(diag.get('digest', ''))[:12]}` · {diag.get('quantization') or diag.get('model_owner') or ''}"
        lines.append(f"| {name} | `{diag.get('model')}` | {'sí' if entry['available'] else 'no'} | {detail} |")
    lines += ["", "Un proveedor no disponible no tiene filas en `benchmark_results.csv`: no se fabrican resultados.", ""]
    metrics = [
        ("success_rate", "Éxito de generación"), ("schema_valid_rate", "Esquema válido"), ("grounded_response_rate", "Respuesta fundamentada"),
        ("actionability_rate", "Accionabilidad"), ("unsupported_numeric_claim_rate", "Cifras no soportadas"), ("contradiction_rate", "Contradicciones"),
        ("timeout_rate", "Timeouts"), ("actions_accepted_mean", "Acciones aceptadas (media)"), ("latency_ms_median", "Latencia mediana (ms)"),
        ("latency_ms_p95", "Latencia p95 (ms)"), ("latency_ms_mean", "Latencia media (ms)"), ("cost_usd_mean", "Costo medio (USD)"), ("cost_usd_total", "Costo total (USD)"),
    ]
    for mode, title in (("controlled", "Benchmark controlado (contrato común: 4 acciones, 180 caracteres)"), ("operational", "Benchmark operativo (OpenAI 8 acciones / Ollama 4, como en la aplicación)")):
        available = [(name, entry[mode]) for name, entry in summary["providers"].items() if entry["available"]]
        lines += [f"## {title}", ""]
        if not available:
            lines += ["Sin proveedores disponibles para este modo.", ""]
            continue
        lines += ["| Métrica | " + " | ".join(name for name, _ in available) + " |", "|---|" + "---|" * len(available)]
        for key, label in metrics:
            lines.append(f"| {label} | " + " | ".join("—" if stats.get(key) is None else str(stats.get(key)) for _, stats in available) + " |")
        lines.append("")
    lines += ["## Repetibilidad", "", "```json", json.dumps(summary["repeatability"], indent=2, ensure_ascii=False), "```", ""]
    budget = summary.get("budget")
    if budget:
        lines += ["## Presupuesto OpenAI", "", f"Límite {budget['limit_usd']} USD; costo estimado registrado {budget['estimated_spent_usd']} USD en {budget['calls']} llamadas; bloqueadas {budget['blocked_calls']}. {budget['note']}", ""]
    lines += ["## Matriz de decisión", "", "| Criterio | Ollama (qwen3:8b) | OpenAI (API) |", "|---|---|---|"]
    lines += [f"| {criterion} | {local} | {remote} |" for criterion, local, remote in DECISION_CRITERIA]
    lines += [
        "| Calidad / groundedness | Ver tablas medidas | Ver tablas medidas |",
        "| Latencia | Ver tablas medidas | Ver tablas medidas |",
        "",
        "## Lectura",
        "",
        "Groundedness es un proxy determinístico (esquema, procedencia feature/fuente, cifras literales, ausencia de contradicciones, acción y seguimiento verificables); no establece verdad semántica ni utilidad humana. "
        "Ningún juez LLM ni evaluador humano participó en estas métricas.",
    ]
    if summary["comparison_status"] != "complete":
        lines += ["", "**Comparación incompleta:** al menos un proveedor no estuvo disponible; la selección no puede apoyarse en una comparación empírica homogénea hasta ejecutar ambos."]
    return "\n".join(lines) + "\n"


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    from genai_benchmark_common import hardware_metadata, prepare_cases, require_new_outputs

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default="artifacts/0.9.0-academic")
    parser.add_argument("--input", default="data/processed/mendeley_core.csv")
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--repeat-cases", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--providers", default="openai,ollama")
    parser.add_argument("--openai-model", default=os.getenv("PRUNIN_OPENAI_MODEL", "gpt-4.1"))
    parser.add_argument("--ollama-model", default=os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--ollama-url", default=os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat"))
    parser.add_argument("--ollama-timeout", type=float, default=120.0)
    parser.add_argument("--budget-usd", type=float, default=5.0)
    parser.add_argument("--output-dir", default="reports/genai/provider_comparison_2026")
    args = parser.parse_args(argv)

    output = ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    require_new_outputs(output, OUTPUT_NAMES)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    selected = [name.strip() for name in args.providers.split(",") if name.strip()]
    providers: dict[str, dict[str, Any]] = {}
    if "openai" in selected:
        providers["openai"] = diagnose_openai(args.openai_model)
    if "ollama" in selected:
        providers["ollama"] = diagnose_ollama(args.ollama_model, args.ollama_url)
    pricing = OPENAI_PRICING.get(args.openai_model)
    budget = BudgetGuard(args.budget_usd, pricing["input"], pricing["output"]) if pricing else None

    runtime, cases = prepare_cases(ROOT / args.artifact, ROOT / args.input, args.cases)
    case_rows = []
    for case in cases:
        evidence = build_case_evidence(case, **MODES["controlled"]["ollama"])
        case_rows.append({
            "project_id": case["case_id"], "health": case["prediction"].get("health"),
            "delay_days": case["prediction"].get("delay_days"), "cost_overrun_ratio": case["prediction"].get("cost_overrun_ratio"),
            "evidence_status": evidence["evidence_status"], "allowed_features": ";".join(evidence["allowed_features"]),
            "evidence_sha256": sha256_text(evidence["evidence_json"]), "evidence_json": evidence["evidence_json"],
        })
    write_csv(output / "benchmark_cases.csv", case_rows)

    settings = {"openai_model": args.openai_model, "ollama_model": args.ollama_model, "ollama_url": args.ollama_url, "ollama_timeout": args.ollama_timeout}
    rows, stops = run(cases, providers, settings, repeat_cases=args.repeat_cases, repeats=args.repeats, budget=budget)
    write_csv(output / "benchmark_results.csv", rows)
    summary = summarize(rows, providers, stops, budget)
    manifest = {
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(), "artifact_version": runtime.version, "command": "python scripts/benchmark_provider_comparison.py " + " ".join(argv or sys.argv[1:]),
        "inputs": {"artifact": args.artifact, "split_manifest_sha256": sha256_file(ROOT / args.artifact / "split_manifest.json"), "dataset_sha256": sha256_file(ROOT / args.input)},
        "case_selection": "Últimos snapshots TEST con al menos un driver que aumenta el riesgo; orden aleatorio con random_state=42 (mismo criterio que la evaluación histórica Qwen).",
        "cases": len(cases), "repeat_cases": args.repeat_cases, "repeats": args.repeats, "modes": MODES,
        "generation_parameters": {
            "ollama": {"temperature": 0.1, "num_predict": 1200, "think": False, "format": "JSON schema forzado", "timeout_seconds": args.ollama_timeout},
            "openai": {"endpoint": "/v1/chat/completions", "response_format": "json_object", "temperature": "predeterminada del proveedor", "max_completion_tokens": "sin límite explícito", "timeout_seconds": float(os.getenv("PRUNIN_OPENAI_TIMEOUT_SECONDS", "120"))},
            "timeout_policy_note": "Ollama local usa 120 s para no penalizar la carga en frío; OpenAI usa PRUNIN_OPENAI_TIMEOUT_SECONDS.",
        },
        "providers": providers, "hardware": hardware_metadata(), "budget": budget.snapshot() if budget else None,
        "secrets": "Ningún valor de credencial se escribe en estos archivos.",
    }
    (output / "benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (output / "execution_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    plot(rows, output)
    (output / "comparison_report.md").write_text(render_report(summary, manifest), encoding="utf-8")
    print(json.dumps({name: entry.get("controlled", entry["diagnosis"].get("failure_code")) for name, entry in summary["providers"].items()}, indent=2, ensure_ascii=False, default=str))
    return 0 if summary["comparison_status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
