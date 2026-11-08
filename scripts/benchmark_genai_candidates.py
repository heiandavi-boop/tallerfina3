#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from genai_benchmark_common import (
    TEMPERATURE,
    evaluate_case,
    hardware_metadata,
    model_is_installed,
    ollama_models,
    prepare_cases,
    require_new_outputs,
    summarize_rows,
)


def write_outputs(output_dir: Path, summary: dict, rows: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [
        "case_id", "model", "generation_success", "schema_valid", "grounded",
        "unsupported_numeric_claim", "actionability", "latency_ms", "failure_code",
        "health", "driver_count",
    ]
    with (output_dir / "benchmark_raw.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Benchmark comparativo de candidatos GenAI",
        "",
        f"Estado: `{summary['status']}`. Casos por modelo: {summary['cases_requested']}; temperatura: {TEMPERATURE}; timeout: {summary['timeout_seconds']} s.",
        "",
        "Todas las llamadas usan los mismos snapshots TEST, evidencia, prompt, esquema JSON, validador y hardware dentro de esta ejecución. No se descargan modelos. El benchmark compara salidas explicativas, no predictores ni utilidad humana.",
        "",
        "| Modelo | Estado | N | Éxito | Esquema | Grounded | Cifra no soportada | Acción | Timeout | JSON inválido | Mediana ms | p95 ms |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, result in summary["models"].items():
        metrics = result.get("metrics") or {}
        values = [
            f"{metrics.get(key):.3f}" if isinstance(metrics.get(key), (int, float)) else "—"
            for key in (
                "generation_success_rate", "schema_valid_rate", "grounded_rate",
                "unsupported_numeric_claim_rate", "actionability_rate", "timeout_rate", "invalid_json_rate",
            )
        ]
        lines.append(
            f"| {model} | {result['status']} | {metrics.get('requests_total', 0)} | "
            + " | ".join(values[:5])
            + f" | {values[5]} | {values[6]} | {metrics.get('latency_ms_median') or '—'} | {metrics.get('latency_ms_p95') or '—'} |"
        )
    lines.extend(["", "Hardware registrado: `" + json.dumps(summary["hardware"], ensure_ascii=False) + "`.", "", "No interpretar resultados de una sola máquina como ranking universal. Un modelo no disponible se marca `not_available`; la comparación se considera parcial."])
    (output_dir / "benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparación local reproducible de modelos Ollama ya instalados.")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/0.9.0-academic")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/mendeley_core.csv")
    parser.add_argument("--models", nargs="+", default=["qwen3:8b", "gemma3:4b", "ministral-3:8b"])
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=float(os.getenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", "30")))
    parser.add_argument("--ollama-url", default=os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/genai/evidence-v2/comparison")
    args = parser.parse_args()
    if args.cases != 30:
        parser.error("La comparación PAIII usa exactamente 30 casos; --cases se conserva en 30.")
    require_new_outputs(args.output_dir, ["benchmark_summary.json", "benchmark_raw.csv", "benchmark_report.md"])
    models = list(dict.fromkeys(args.models))
    installed, error = ollama_models(args.ollama_url)
    summary = {
        "status": "not_available",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "cases_requested": 30,
        "timeout_seconds": args.timeout,
        "temperature": TEMPERATURE,
        "format": "json",
        "contract_version": "evidence-v2",
        "num_predict": 1200,
        "prompt_builder": "build_grounded_prompt",
        "validator": "validate_generated_payload",
        "hardware": hardware_metadata(),
        "ollama_available": installed is not None,
        "ollama_error": error,
        "models": {},
        "notes": ["No automatic model downloads are performed.", "All available candidates share the same 30 prepared TEST cases and evidence payloads."],
    }
    rows: list[dict] = []
    if installed is None:
        for model in models:
            summary["models"][model] = {"status": "not_available", "reason": error, "metrics": None}
        write_outputs(args.output_dir, summary, rows)
        print(json.dumps({"status": summary["status"], "models": summary["models"]}, indent=2))
        return 0

    available = [model for model in models if model_is_installed(model, installed)]
    for model in models:
        if model not in available:
            summary["models"][model] = {"status": "not_available", "reason": "Model tag is not installed; no download was attempted.", "metrics": None}
    if available:
        runtime, cases = prepare_cases(args.artifact, args.input, 30)
        summary.update({"status": "complete" if len(available) == len(models) else "partial", "artifact_version": runtime.version, "case_ids": [case["case_id"] for case in cases], "evaluation_unit": "latest TEST project snapshot with at least one increasing-risk local driver"})
        for model in available:
            warmup = evaluate_case(cases[0], model, args.ollama_url, args.timeout)
            model_rows = [evaluate_case(case, model, args.ollama_url, args.timeout) for case in cases]
            rows.extend(model_rows)
            summary["models"][model] = {
                "status": "complete",
                "warmup_excluded": True,
                "warmup_failure_code": warmup["failure_code"],
                "metrics": summarize_rows(model_rows),
            }
        if len(available) == 1:
            summary["status"] = "partial" if len(models) > 1 else "complete"
    write_outputs(args.output_dir, summary, rows)
    print(json.dumps({"status": summary["status"], "models": summary["models"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())