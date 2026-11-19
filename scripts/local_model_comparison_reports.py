"""Deterministic report generation for the Qwen3 8B vs. GPT-OSS 20B comparison.

Reports are derived only from the integrity-checked JSONL checkpoint and the
execution manifest, so regenerating them from the same inputs yields identical bytes.
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

from prunin_ai.genai_comparison import (  # noqa: E402
    AUTHORIZED_MODELS,
    CRITERION_LABELS,
    DECISION_WEIGHTS,
    DEFENSIBLE_MARGIN,
    MODEL_PROFILES,
    decide,
    summarize_model,
)

RAW_FIELDS = [
    "model", "phase", "case_id", "repeat", "timestamp_utc", "health", "generation_success", "json_parsed", "schema_valid",
    "grounded", "unsupported_numeric_claim", "contradictory_claim", "actionability", "priority_valid", "follow_up_verifiable",
    "actions_generated", "referenced_features", "priorities", "failure_code", "failure_detail", "latency_ms", "prompt_tokens",
    "completion_tokens", "eval_duration_ns", "load_duration_ns", "done_reason", "thinking_chars", "evidence_sha256",
    "prompt_sha256", "response_sha256", "raw_response",
]
COMPARISON_METRICS = [
    ("Calidad", "accepted_rate", "Respuestas aceptadas", "rate"),
    ("Calidad", "json_valid_rate", "JSON válido", "rate"),
    ("Calidad", "schema_valid_rate", "Esquema válido", "rate"),
    ("Calidad", "grounded_rate", "Grounding", "rate"),
    ("Confiabilidad", "unsupported_numeric_claim_rate", "Alucinaciones numéricas", "rate"),
    ("Confiabilidad", "contradiction_rate", "Contradicciones", "rate"),
    ("Confiabilidad", "failures", "Respuestas rechazadas (de 30)", "count"),
    ("Recomendaciones", "actionability_rate", "Accionabilidad", "rate"),
    ("Recomendaciones", "priority_valid_rate", "Prioridad válida y ordenada", "rate"),
    ("Recomendaciones", "follow_up_verifiable_rate", "Seguimiento verificable", "rate"),
    ("Rendimiento", "latency_ms_mean", "Latencia media (ms)", "ms"),
    ("Rendimiento", "latency_ms_median", "Latencia mediana (ms)", "ms"),
    ("Rendimiento", "latency_ms_p95", "Latencia p95 (ms)", "ms"),
    ("Rendimiento", "tokens_per_second", "Tokens generados por segundo", "num"),
    ("Rendimiento", "completion_tokens_mean", "Tokens generados por respuesta", "num"),
    ("Rendimiento", "thinking_chars_mean", "Caracteres de razonamiento por respuesta", "num"),
    ("Estabilidad", "timeouts", "Timeouts (principal + repetición)", "count"),
    ("Estabilidad", "operational_error_rate", "Tasa de fallos operativos", "rate"),
    ("Estabilidad", "repeat_consistent", "Casos repetidos consistentes", "rate"),
    ("Estabilidad", "repeat_outcome", "Acuerdo de aceptación entre repeticiones", "rate"),
    ("Estabilidad", "repeat_identical", "Respuestas idénticas entre repeticiones", "rate"),
]
OUTPUT_FILES = [
    "benchmark_cases.csv", "benchmark_raw.csv", "benchmark_summary.json", "model_comparison.csv", "decision_matrix.csv",
    "comparison_report.md", "critical_analysis.md", "conclusions.md",
    "charts/quality_comparison.png", "charts/grounding_comparison.png", "charts/latency_comparison.png",
    "charts/reliability_comparison.png", "charts/decision_matrix.png",
]


def _name(model: str) -> str:
    return MODEL_PROFILES[model]["display_name"]


def _metric(metrics: dict[str, Any], key: str) -> Any:
    repeat = metrics.get("repeatability") or {}
    return {
        "repeat_consistent": repeat.get("consistent_case_rate"),
        "repeat_outcome": repeat.get("outcome_agreement_rate"),
        "repeat_identical": repeat.get("identical_response_rate"),
    }.get(key, metrics.get(key))


def _fmt(value: Any, kind: str) -> str:
    if value is None:
        return "n/d"
    if kind == "rate":
        return f"{100 * float(value):.1f} %"
    if kind == "ms":
        return f"{float(value):.0f}"
    if kind == "count":
        return str(int(value))
    return f"{float(value):.1f}"


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round(item) for item in value]
    return value


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in fields})


def build_summary(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = manifest["models"]
    case_order = {case_id: index for index, case_id in enumerate(manifest["case_ids"])}
    per_model: dict[str, Any] = {}
    paired: dict[str, list[bool]] = {}
    for model in models:
        main = sorted((row for row in rows if row["model"] == model and row["phase"] == "main"), key=lambda row: case_order[row["case_id"]])
        repeat = [row for row in rows if row["model"] == model and row["phase"] == "repeat"]
        paired[model] = [bool(row["grounded"]) for row in main]
        per_model[model] = {
            "display_name": _name(model),
            "think": MODEL_PROFILES[model]["think"],
            "metadata": manifest.get("model_metadata", {}).get(model),
            "metrics": summarize_model(main, repeat),
            "resources": (manifest.get("resources") or {}).get(model),
            "warmup": next((item for item in manifest.get("warmups", []) if item["model"] == model), None),
        }
    evidence_complete = bool((manifest.get("completeness") or {}).get("complete")) and not manifest.get("simulated")
    decision = decide({model: per_model[model]["metrics"] for model in models}, evidence_complete=evidence_complete, paired_grounded=paired)
    if manifest.get("simulated"):
        decision["reasons"].insert(0, "Ejecución SIMULADA para pruebas: no constituye evidencia experimental.")
    return _round({
        "experiment_id": manifest.get("experiment_id"),
        "simulated": bool(manifest.get("simulated")),
        "evaluation_type": "Indicadores automáticos del validador determinista de PRUNIN; sin evaluación semántica humana.",
        "started_utc": manifest.get("started_utc"),
        "finished_utc": manifest.get("finished_utc"),
        "ollama_version": manifest.get("ollama_version"),
        "hardware": manifest.get("hardware"),
        "cases": len(manifest["case_ids"]),
        "repeat_case_ids": manifest["repeat_case_ids"],
        "repeats": manifest["repeats"],
        "generation_parameters": manifest.get("generation_parameters"),
        "configuration_differences": manifest.get("configuration_differences"),
        "models": per_model,
        "decision": decision,
    })


def _charts(output_dir: Path, summary: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"svg.hashsalt": "prunin", "font.size": 9})
    charts = output_dir / "charts"
    charts.mkdir(exist_ok=True)
    models = list(summary["models"])
    names = [_name(model) for model in models]
    colors = ["#2563eb", "#ea580c"]
    metrics = {model: summary["models"][model]["metrics"] for model in models}

    def grouped(filename: str, title: str, keys: list[tuple[str, str]], *, percent: bool = True, ylabel: str = "%") -> None:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        width = 0.38
        for index, model in enumerate(models):
            values = [(_metric(metrics[model], key) or 0) * (100 if percent else 1) for key, _ in keys]
            positions = [position + (index - 0.5) * width for position in range(len(keys))]
            bars = ax.bar(positions, values, width, label=names[index], color=colors[index])
            ax.bar_label(bars, fmt="%.0f", fontsize=8, padding=2)
        ax.set_xticks(range(len(keys)), [label for _, label in keys], rotation=15, ha="right")
        ax.set_ylabel(ylabel)
        if percent:
            ax.set_ylim(0, 110)
        ax.set_title(title)
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(charts / filename, dpi=120, metadata={"Software": None})
        plt.close(fig)

    grouped("quality_comparison.png", "Calidad estructural sobre 30 casos TEST", [("json_valid_rate", "JSON válido"), ("schema_valid_rate", "Esquema válido"), ("accepted_rate", "Aceptadas"), ("actionability_rate", "Accionabilidad"), ("priority_valid_rate", "Prioridad"), ("follow_up_verifiable_rate", "Seguimiento")])
    grouped("grounding_comparison.png", "Grounding y repetibilidad", [("grounded_rate", "Grounding"), ("repeat_consistent", "Repetición consistente"), ("repeat_outcome", "Acuerdo de aceptación"), ("repeat_identical", "Respuesta idéntica")])
    grouped("latency_comparison.png", "Latencia por solicitud (ms)", [("latency_ms_mean", "Media"), ("latency_ms_median", "Mediana"), ("latency_ms_p95", "p95"), ("latency_ms_max", "Máxima")], percent=False, ylabel="milisegundos")
    grouped("reliability_comparison.png", "Confiabilidad (menor es mejor)", [("unsupported_numeric_claim_rate", "Cifras no soportadas"), ("contradiction_rate", "Contradicciones"), ("operational_error_rate", "Fallos operativos")])

    decision = summary["decision"]
    criteria = list(DECISION_WEIGHTS)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    left = [0.0] * len(models)
    palette = ["#1d4ed8", "#059669", "#7c3aed", "#d97706", "#64748b", "#db2777"]
    for index, criterion in enumerate(criteria):
        values = [DECISION_WEIGHTS[criterion] * decision["scores"][model][criterion] for model in models]
        ax.barh(names, values, left=left, color=palette[index], label=f"{CRITERION_LABELS[criterion]} ({DECISION_WEIGHTS[criterion]:.0%})")
        left = [a + b for a, b in zip(left, values)]
    for position, total in enumerate(left):
        ax.text(total + 0.01, position, f"{total:.3f}", va="center")
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("Puntaje ponderado (0–1)")
    ax.set_title("Matriz de decisión multicriterio")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(charts / "decision_matrix.png", dpi=120, metadata={"Software": None})
    plt.close(fig)


def _table(summary: dict[str, Any]) -> str:
    models = list(summary["models"])
    lines = ["| Categoría | Métrica | " + " | ".join(_name(model) for model in models) + " |", "|---|---|" + "---:|" * len(models)]
    for category, key, label, kind in COMPARISON_METRICS:
        lines.append(f"| {category} | {label} | " + " | ".join(_fmt(_metric(summary["models"][model]["metrics"], key), kind) for model in models) + " |")
    return "\n".join(lines)


def _decision_table(summary: dict[str, Any]) -> str:
    models = list(summary["models"])
    decision = summary["decision"]
    lines = ["| Criterio | Peso | " + " | ".join(f"{_name(model)} (normalizado / ponderado)" for model in models) + " |", "|---|---:|" + "---:|" * len(models)]
    for criterion, weight in DECISION_WEIGHTS.items():
        cells = [f"{decision['scores'][model][criterion]:.3f} / {weight * decision['scores'][model][criterion]:.3f}" for model in models]
        lines.append(f"| {CRITERION_LABELS[criterion]} | {weight:.0%} | " + " | ".join(cells) + " |")
    lines.append("| **Total** | **100 %** | " + " | ".join(f"**{decision['totals'][model]:.3f}**" for model in models) + " |")
    return "\n".join(lines)


def _sensitivity_table(summary: dict[str, Any]) -> str:
    models = list(summary["models"])
    lines = ["| Escenario | " + " | ".join(_name(model) for model in models) + " | Mejor |", "|---|" + "---:|" * len(models) + "---|"]
    for item in summary["decision"]["sensitivity"]:
        best = _name(item["winner"]) if item["winner"] else "empate"
        lines.append(f"| {item['scenario']} | " + " | ".join(f"{item['totals'][model]:.3f}" for model in models) + f" | {best} |")
    return "\n".join(lines)


def _failure_lines(summary: dict[str, Any]) -> str:
    lines = []
    for model, data in summary["models"].items():
        codes = data["metrics"].get("failure_codes") or {}
        text = ", ".join(f"`{code}` × {count}" for code, count in codes.items()) or "ninguno"
        lines.append(f"- **{_name(model)}**: {text}.")
    return "\n".join(lines)


def _metadata_table(summary: dict[str, Any]) -> str:
    lines = ["| Atributo | " + " | ".join(_name(model) for model in summary["models"]) + " |", "|---|" + "---|" * len(summary["models"])]
    fields = [("name", "Identificador Ollama"), ("digest", "Digest"), ("family", "Familia"), ("architecture", "Arquitectura (GGUF)"), ("parameter_size", "Parámetros"), ("quantization_level", "Cuantización"), ("size_bytes", "Tamaño en disco (bytes)"), ("context_length", "Contexto máximo"), ("expert_count", "Expertos (MoE)"), ("experts_used", "Expertos activos por token")]
    for key, label in fields:
        values = []
        for model in summary["models"]:
            value = (summary["models"][model].get("metadata") or {}).get(key)
            values.append(f"`{str(value)[:12]}`" if key == "digest" and value else ("n/a" if value is None else str(value)))
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines.append("| Razonamiento (`think`) | " + " | ".join(f"`{summary['models'][model]['think']}`" for model in summary["models"]) + " |")
    lines.append("| Memoria residente medida (`/api/ps`) | " + " | ".join(
        f"{(summary['models'][model].get('resources') or {}).get('resident_size_bytes', 'n/d')} bytes" for model in summary["models"]) + " |")
    return "\n".join(lines)


def _verdict(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    if decision["defensible"] and decision["winner"]:
        return f"La matriz recomienda **{_name(decision['winner'])}** con una ventaja ponderada de {decision['margin']:.3f} (umbral defendible {DEFENSIBLE_MARGIN:.2f}), estable en todos los escenarios de sensibilidad."
    return "La matriz **no declara un ganador defendible**: " + " ".join(decision["reasons"])


def _strengths(summary: dict[str, Any]) -> str:
    models = list(summary["models"])
    scores = summary["decision"]["scores"]
    lines = []
    for model in models:
        other = next(item for item in models if item != model)
        better = [CRITERION_LABELS[key] for key in DECISION_WEIGHTS if scores[model][key] > scores[other][key] + 1e-9]
        worse = [CRITERION_LABELS[key] for key in DECISION_WEIGHTS if scores[model][key] + 1e-9 < scores[other][key]]
        lines.append(f"- **{_name(model)}** — supera en: {', '.join(better) or 'ningún criterio'}; queda por debajo en: {', '.join(worse) or 'ningún criterio'}.")
    return "\n".join(lines)


def _tradeoff(summary: dict[str, Any]) -> str:
    lines = []
    for model, data in summary["models"].items():
        memory = (data.get("resources") or {}).get("resident_size_bytes")
        metrics = data["metrics"]
        lines.append(f"{_name(model)}: {memory / 1024 ** 3:.1f} GB residentes, mediana {metrics['latency_ms_median'] / 1000:.1f} s, aceptación {100 * metrics['accepted_rate']:.1f} %"
                     if memory and metrics.get("latency_ms_median") is not None and metrics.get("accepted_rate") is not None else f"{_name(model)}: recursos no medidos")
    return ("Capacidad de ejecución local (fuera de la matriz, medida con `/api/ps`): " + "; ".join(lines) + ". "
            "En un equipo de 24 GB la memoria residente condiciona la convivencia con el navegador, el backend y otros procesos.")


def _significance(summary: dict[str, Any]) -> str:
    sig = summary["decision"].get("significance")
    if not sig:
        return "No se calculó la prueba pareada."
    def cases(count: int) -> str:
        return f"{count} caso{'s' if count != 1 else ''}"

    return (f"Prueba de McNemar exacta sobre la aceptación pareada de los 30 casos: {cases(sig['only_first'])} aceptado{'s' if sig['only_first'] != 1 else ''} solo por "
            f"{_name(sig['first_model'])} y {cases(sig['only_second'])} solo por {_name(sig['second_model'])}; p = {sig['p_value']:.4f}. "
            + ("La diferencia de aceptación es estadísticamente significativa (α = 0,05)." if sig["p_value"] < 0.05 else
               "Con 30 casos la diferencia de aceptación no es estadísticamente significativa (α = 0,05); el resultado debe leerse como evidencia direccional."))


def _report(summary: dict[str, Any]) -> str:
    hardware = summary.get("hardware") or {}
    params = summary.get("generation_parameters") or {}
    simulated = "\n> **ADVERTENCIA: ejecución simulada para pruebas automatizadas. No usar como evidencia académica.**\n" if summary["simulated"] else ""
    differences = "\n".join(f"- `{item['parameter']}`: {', '.join(f'{_name(m)}={v}' for m, v in item['values'].items())}. {item['reason']}" for item in summary.get("configuration_differences") or [])
    return f"""# Comparación experimental local: Qwen3 8B vs. GPT-OSS 20B
{simulated}
Experimento `{summary['experiment_id']}` · inicio {summary['started_utc']} · fin {summary['finished_utc']} · Ollama {summary['ollama_version']}.

Todas las cifras provienen de `benchmark_raw.csv` (inferencias reales registradas en `runs.jsonl` con huella SHA-256 por fila). Son **indicadores automáticos** del validador determinista de PRUNIN; **no** hubo evaluación semántica humana.

## 1. Por qué Qwen3 8B y GPT-OSS 20B

Son los dos modelos generativos abiertos instalados localmente que cumplen las restricciones de PRUNIN: ejecución sin servicios externos (privacidad de datos de proyecto), licencia Apache 2.0, salida JSON restringida por esquema en Ollama y tamaño compatible con un portátil de 24 GB. Representan dos diseños distintos —denso de 8B frente a mezcla de expertos de 21B— lo que amplía la búsqueda más allá de variantes del mismo modelo. Gemma y servicios en la nube quedaron fuera de alcance por decisión del proyecto.

## 2. Arquitectura y diferencias relevantes

- **Qwen3 8B**: transformer denso (~8,2 B parámetros, todos activos por token) con modo de razonamiento híbrido que puede desactivarse. Es el modelo de producción de PRUNIN.
- **GPT-OSS 20B**: transformer de mezcla de expertos (~21 B parámetros totales, ~3,6 B activos por token según la ficha pública de OpenAI), pesos MXFP4 y razonamiento obligatorio con niveles `low/medium/high`.

{_metadata_table(summary)}

## 3. Metodología experimental

- **Casos**: los mismos 30 proyectos TEST (último snapshot con al menos un driver de riesgo; `random_state=42`), verificados contra `split_manifest.json` sin solape con TRAIN ni VALIDATION.
- **Entrada idéntica**: misma predicción LightGBM congelada, drivers, contexto de evidencia, prompt (`build_grounded_prompt`), esquema JSON forzado y validador (`validate_generated_payload`). Las huellas `evidence_sha256` y `prompt_sha256` de cada caso son iguales para ambos modelos.
- **Parámetros**: temperatura {params.get('temperature')}, `num_predict` {params.get('num_predict')}, timeout {params.get('timeout_seconds')} s, `stream=false`.
- **Ejecución**: secuencial; antes de cada modelo se descargan los modelos residentes y se realiza un warm-up excluido de las métricas.
- **Repetibilidad**: casos {', '.join(f'`{case}`' for case in summary['repeat_case_ids'])} (selección determinística por SHA-256), {summary['repeats']} repeticiones por modelo.
- **Diferencias de configuración registradas**:
{differences}

## 4. Condiciones de hardware

{hardware.get('chip') or 'n/d'} · {hardware.get('memory_gb') or 'n/d'} GB de memoria unificada · {hardware.get('platform')} · Python {hardware.get('python_version')}. La memoria residente se midió con `/api/ps` de Ollama; no se midió CPU/GPU del sistema operativo.

## 5. Resultados individuales y comparativos

{_table(summary)}

Motivos de rechazo en la corrida principal:

{_failure_lines(summary)}

{_significance(summary)}

![Calidad](charts/quality_comparison.png)
![Grounding](charts/grounding_comparison.png)
![Latencia](charts/latency_comparison.png)
![Confiabilidad](charts/reliability_comparison.png)

## 6. Matriz de decisión

{_decision_table(summary)}

Normalización: {' '.join(f'**{CRITERION_LABELS[key]}**: {text}' for key, text in summary['decision']['normalization'].items())}

### Análisis de sensibilidad

{_sensitivity_table(summary)}

![Matriz](charts/decision_matrix.png)

## 7. Fortalezas, limitaciones y justificación para PRUNIN

{_strengths(summary)}

{_verdict(summary)}

{_tradeoff(summary)}

El modelo configurado en la aplicación **no se cambia automáticamente**; Qwen3 8B permanece como predeterminado hasta una decisión explícita del equipo.

Ver `critical_analysis.md` (riesgos y amenazas a la validez) y `conclusions.md` (conclusiones frente a R6.1-Cr2 y R6.1-Cr4).
"""


def _ratio(metrics: dict[str, Any]) -> str:
    median, p95 = metrics.get("latency_ms_median"), metrics.get("latency_ms_p95")
    return f"{p95 / median:.2f}" if median and p95 else "n/d"


def _critical(summary: dict[str, Any]) -> str:
    models = summary["models"]
    gpt = models.get("gpt-oss:20b", {}).get("metrics", {})
    qwen = models.get("qwen3:8b", {}).get("metrics", {})
    return f"""# Análisis crítico de la comparación generativa

## Qué miden y qué no miden los indicadores

Los indicadores son verificaciones automáticas del validador de PRUNIN: forma JSON, citas de evidencia permitidas y con procedencia correcta, ausencia de cifras no presentes en la evidencia, ausencia de contradicciones detectables por reglas, acciones que empiezan con verbo ejecutable y seguimiento verificable. Detectan errores verificables, pero **no** juzgan utilidad gerencial, priorización correcta ni calidad de redacción. Esa evaluación requiere expertos humanos y **no se realizó**.

## Riesgos técnicos

- **Razonamiento obligatorio de GPT-OSS**: con `think=false` Ollama devuelve contenido vacío; se usó `think=low`. GPT-OSS generó en promedio {_fmt(gpt.get('thinking_chars_mean'), 'num')} caracteres de razonamiento (Qwen: {_fmt(qwen.get('thinking_chars_mean'), 'num')}). Este razonamiento consume el mismo presupuesto `num_predict`.
- **Cifras no soportadas**: tasa de {_fmt(gpt.get('unsupported_numeric_claim_rate'), 'rate')} en GPT-OSS y {_fmt(qwen.get('unsupported_numeric_claim_rate'), 'rate')} en Qwen. Una cifra inventada en una recomendación de proyecto puede inducir decisiones erróneas; por eso el validador bloquea la respuesta y PRUNIN cae a la recomendación determinista.
- **Memoria**: GPT-OSS ocupa más memoria residente; en 24 GB compite con el navegador y el backend, lo que puede aumentar la latencia en uso real.
- **Cola de latencia**: la relación p95/mediana es {_ratio(qwen)} en Qwen y {_ratio(gpt)} en GPT-OSS; la cola larga, no la mediana, determina la espera percibida en la demostración.
- **No determinismo**: con temperatura 0,1 el texto varía entre ejecuciones: respuestas idénticas en {_fmt((qwen.get('repeatability') or {}).get('identical_response_rate'), 'rate')} de los casos repetidos con Qwen y {_fmt((gpt.get('repeatability') or {}).get('identical_response_rate'), 'rate')} con GPT-OSS, aunque la aceptación, las señales citadas y las prioridades se mantuvieron en {_fmt((qwen.get('repeatability') or {}).get('consistent_case_rate'), 'rate')} y {_fmt((gpt.get('repeatability') or {}).get('consistent_case_rate'), 'rate')} de los casos, respectivamente.

## Riesgos éticos

- Las recomendaciones automáticas pueden percibirse como juicio sobre personas o equipos; PRUNIN las presenta como apoyo y siempre con la evidencia citada.
- La aceptación por el validador no garantiza ausencia de sesgo ni corrección causal; el responsable del proyecto conserva la decisión.
- Ambos modelos se ejecutan localmente: ningún dato de proyecto sale del equipo.

## Amenazas a la validez

- **Interna**: el prompt incluye la directiva `/no_think` pensada para Qwen; el nivel de razonamiento difiere por limitación de GPT-OSS; los tokenizadores difieren, por lo que los tokens/s no son estrictamente comparables. El orden de ejecución (primero Qwen, luego GPT-OSS) puede introducir efectos térmicos del equipo.
- **Del constructo**: el validador es conservador (por ejemplo, rechaza un umbral numérico razonable no presente en la evidencia); mide adherencia al contrato de PRUNIN, no calidad general del modelo.
- **Externa**: 30 casos de un único dataset (Mendeley) y un solo equipo; los resultados no se generalizan a otros dominios ni hardware.
- **Estadística**: con 30 casos pareados la potencia es limitada. {_significance(summary)}
- **Repetibilidad**: 5 casos × {summary['repeats']} repeticiones es una muestra pequeña de la variabilidad.
"""


def _conclusions(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    totals = ", ".join(f"{_name(model)} {value:.3f}" for model, value in decision["totals"].items())
    return f"""# Conclusiones

1. Se ejecutaron los mismos 30 casos TEST con {' y '.join(_name(model) for model in summary['models'])} en {(summary.get('hardware') or {}).get('chip') or 'el equipo local'}, con entrada, prompt, esquema, validador, temperatura y presupuesto idénticos, más {summary['repeats']} repeticiones de 5 casos por modelo.
2. Puntajes ponderados: {totals}. {_verdict(summary)}
3. {_significance(summary)}
4. {_tradeoff(summary)}
5. La evaluación es exclusivamente automática; no existe evaluación semántica humana de las recomendaciones.
6. El modelo predeterminado de PRUNIN sigue siendo Qwen3 8B; cualquier cambio requiere decisión explícita.

## Frente a la rúbrica

- **R6.1-Cr2 (elección de IA generativa)**: la elección queda sustentada en una comparación experimental reproducible entre dos arquitecturas distintas (densa vs. MoE), con criterios ponderados explícitos, sensibilidad y prueba pareada. La amplitud de alternativas se limita a dos modelos locales (sin servicios externos por diseño), lo cual debe declararse como limitación ante el descriptor de Nivel 4.
- **R6.1-Cr4 (interpretación crítica)**: se interpretan los indicadores con sus límites (validador conservador, no determinismo, potencia estadística, ausencia de evaluación humana) y se separan explícitamente métricas automáticas de juicio humano.
"""


def generate_reports(output_dir: Path, manifest: dict[str, Any], cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[str]:
    """Write every deliverable and return the relative file names (for the manifest hashes)."""
    summary = build_summary(manifest, rows)
    repeat_ids = set(manifest["repeat_case_ids"])
    case_rows = [{
        "case_id": case["case_id"],
        "order": index + 1,
        "split": "test",
        "health": case.get("health"),
        "risk_drivers": len(case.get("risk_drivers") or []),
        "allowed_features": case.get("allowed_features"),
        "repeat_case": case["case_id"] in repeat_ids,
        "evidence_sha256": case.get("evidence_sha256"),
        "prompt_sha256": case.get("prompt_sha256"),
    } for index, case in enumerate(cases)]
    _write_csv(output_dir / "benchmark_cases.csv", list(case_rows[0]), case_rows)
    model_rank = {model: index for index, model in enumerate(AUTHORIZED_MODELS)}
    ordered = sorted(rows, key=lambda row: (model_rank.get(row["model"], 9), row["phase"] != "main", int(row["repeat"]), manifest["case_ids"].index(row["case_id"])))
    _write_csv(output_dir / "benchmark_raw.csv", RAW_FIELDS, ordered)
    (output_dir / "benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    comparison = []
    for category, key, label, kind in COMPARISON_METRICS:
        record = {"category": category, "metric": key, "label": label}
        for model in summary["models"]:
            value = _metric(summary["models"][model]["metrics"], key)
            record[model] = round(value, 6) if isinstance(value, float) else value
        comparison.append(record)
    _write_csv(output_dir / "model_comparison.csv", ["category", "metric", "label", *summary["models"]], comparison)
    decision = summary["decision"]
    matrix = []
    for criterion, weight in DECISION_WEIGHTS.items():
        record = {"criterion": criterion, "label": CRITERION_LABELS[criterion], "weight": weight}
        for model in summary["models"]:
            record[f"{model}_score"] = round(decision["scores"][model][criterion], 6)
            record[f"{model}_weighted"] = round(weight * decision["scores"][model][criterion], 6)
        matrix.append(record)
    total = {"criterion": "total", "label": "Total", "weight": round(sum(DECISION_WEIGHTS.values()), 6)}
    for model in summary["models"]:
        total[f"{model}_score"] = ""
        total[f"{model}_weighted"] = round(decision["totals"][model], 6)
    matrix.append(total)
    _write_csv(output_dir / "decision_matrix.csv", list(matrix[0]), matrix)
    (output_dir / "comparison_report.md").write_text(_report(summary), encoding="utf-8")
    (output_dir / "critical_analysis.md").write_text(_critical(summary), encoding="utf-8")
    (output_dir / "conclusions.md").write_text(_conclusions(summary), encoding="utf-8")
    _charts(output_dir, summary)
    return list(OUTPUT_FILES)
