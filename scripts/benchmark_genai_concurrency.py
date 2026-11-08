#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    percentile,
    prepare_cases,
    summarize_rows,
)


CONCURRENCY_LEVELS = (1, 2, 4, 8)


def run_level(cases: list[dict], model: str, url: str, timeout: float, concurrency: int) -> tuple[list[dict], float]:
    started = time.perf_counter()
    rows = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(evaluate_case, case, model, url, timeout): case for case in cases}
        for future in as_completed(futures):
            case = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    "case_id": case["case_id"], "model": model, "generation_success": False,
                    "schema_valid": False, "grounded": False, "unsupported_numeric_claim": False,
                    "actionability": False, "latency_ms": 0.0,
                    "failure_code": f"benchmark_error:{type(exc).__name__}",
                    "health": case.get("health"), "driver_count": len(case["risk_drivers"]),
                }
            row["concurrency"] = concurrency
            rows.append(row)
    return rows, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba local de concurrencia Ollama; no representa prueba productiva.")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/0.9.0-academic")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/mendeley_core.csv")
    parser.add_argument("--model", default=os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=float(os.getenv("PRUNIN_OLLAMA_TIMEOUT_SECONDS", "30")))
    parser.add_argument("--ollama-url", default=os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/genai/concurrency")
    args = parser.parse_args()
    if args.cases != 30:
        parser.error("La prueba PAIII usa exactamente 30 casos; --cases se conserva en 30.")
    installed, error = ollama_models(args.ollama_url)
    summary = {
        "status": "not_executed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "cases_requested": 30,
        "concurrency_levels": list(CONCURRENCY_LEVELS),
        "timeout_seconds": args.timeout,
        "temperature": TEMPERATURE,
        "hardware": hardware_metadata(),
        "ollama_error": error,
        "levels": [],
        "claim_limit": "Local concurrency check only; not a production load or scalability test.",
    }
    raw: list[dict] = []
    if installed is None or not model_is_installed(args.model, installed):
        summary["availability"] = "not_available"
        summary["reason"] = error or "Model tag is not installed; no download was attempted."
    else:
        runtime, cases = prepare_cases(args.artifact, args.input, 30)
        summary.update({"status": "complete", "availability": "available", "artifact_version": runtime.version, "case_ids": [case["case_id"] for case in cases]})
        for concurrency in CONCURRENCY_LEVELS:
            warmup = evaluate_case(cases[0], args.model, args.ollama_url, args.timeout)
            rows, wall_seconds = run_level(cases, args.model, args.ollama_url, args.timeout, concurrency)
            raw.extend(rows)
            metrics = summarize_rows(rows)
            metrics.update({
                "failures": sum(not row["generation_success"] for row in rows),
                "timeouts": sum(row["failure_code"] == "ollama_timeout" for row in rows),
                "fallback_rate": sum(not row["generation_success"] for row in rows) / len(rows) if rows else None,
                "wall_time_seconds": wall_seconds,
                "throughput_requests_per_second": len(rows) / wall_seconds if wall_seconds > 0 else None,
            })
            summary["levels"].append({
                "concurrency": concurrency,
                "warmup_excluded": True,
                "warmup_failure_code": warmup["failure_code"],
                "metrics": metrics,
            })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["case_id", "model", "concurrency", "generation_success", "schema_valid", "grounded", "unsupported_numeric_claim", "actionability", "latency_ms", "failure_code", "health", "driver_count"]
    with (args.output_dir / "raw.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw)
    report_lines = ["# Prueba local de concurrencia GenAI", "", "**No es una prueba productiva ni acredita escalabilidad.**", "", f"Estado: `{summary['status']}`. Modelo: `{args.model}`. Casos por nivel: 30. Timeout: {args.timeout} s.", "", "| Concurrencia | Solicitudes | Éxito | Fallos | Timeout | Fallback | p50 ms | p95 ms | Throughput req/s |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for level in summary["levels"]:
        metrics = level["metrics"]
        report_lines.append(
            f"| {level['concurrency']} | {metrics['requests_total']} | {metrics['generation_success_rate']:.3f} | {metrics['failures']} | {metrics['timeouts']} | {metrics['fallback_rate']:.3f} | {metrics['latency_ms_median']:.2f} | {metrics['latency_ms_p95']:.2f} | {metrics['throughput_requests_per_second']:.3f} |"
        )
    if summary["status"] == "not_executed":
        report_lines.extend(["", f"Benchmark no ejecutado: {summary['reason']}"])
    report_lines.extend(["", "Hardware: `" + json.dumps(summary["hardware"], ensure_ascii=False) + "`.", "", summary["claim_limit"]])
    (args.output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "availability": summary.get("availability"), "levels": summary["levels"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())