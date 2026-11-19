#!/usr/bin/env python3
"""Reproducible local comparison of Qwen3 8B vs. GPT-OSS 20B on the same 30 TEST cases.

Usage:
    python scripts/run_local_model_comparison.py \
      --models qwen3:8b gpt-oss:20b --cases 30 --repeats 3 \
      --output-dir reports/genai/qwen_vs_gptoss_2026

The script never downloads models, never overwrites a completed experiment and
resumes interrupted runs from an integrity-checked JSONL checkpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from prunin_ai.genai_comparison import (  # noqa: E402
    AUTHORIZED_MODELS,
    EXPECTED_CASES,
    MODEL_PROFILES,
    NUM_PREDICT,
    REPEAT_CASES,
    TEMPERATURE,
    UnauthorizedModelError,
    canonical_json,
    check_split_isolation,
    completeness,
    priority_order_valid,
    read_jsonl,
    row_key,
    select_repeat_cases,
    sha256_file,
    sha256_text,
    validate_model_selection,
)

CHECKPOINT = "runs.jsonl"
MANIFEST = "execution_manifest.json"
EXIT_OK, EXIT_BLOCKED, EXIT_INCOMPLETE = 0, 2, 3


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ollama_base(url: str) -> str:
    return url.split("/api/", 1)[0] if "/api/" in url else url.rstrip("/")


def _sysctl(name: str) -> str | None:
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=3, check=True).stdout.strip() or None
    except Exception:
        return None


def hardware_metadata() -> dict[str, Any]:
    memory = _sysctl("hw.memsize")
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "chip": _sysctl("machdep.cpu.brand_string") or platform.processor() or None,
        "memory_gb": round(int(memory) / 1024 ** 3, 1) if memory and memory.isdigit() else None,
        "logical_cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
    }


def check_environment(url: str, models: list[str], *, timeout: float = 5.0) -> dict[str, Any]:
    """Query Ollama for version, installation and metadata of every requested model. No downloads."""
    base = ollama_base(url)
    report: dict[str, Any] = {"ollama_reachable": False, "ollama_version": None, "models": {}, "missing": [], "errors": []}
    try:
        version = requests.get(f"{base}/api/version", timeout=timeout)
        version.raise_for_status()
        report["ollama_version"] = version.json().get("version")
        tags = requests.get(f"{base}/api/tags", timeout=timeout)
        tags.raise_for_status()
        installed = {item.get("name"): item for item in tags.json().get("models", []) if isinstance(item, dict)}
        report["ollama_reachable"] = True
    except Exception as exc:
        report["errors"].append(f"Ollama no accesible en {base}: {type(exc).__name__}: {exc}")
        report["missing"] = list(models)
        return report
    for model in models:
        tag = installed.get(model) or installed.get(f"{model}:latest")
        if not tag:
            report["missing"].append(model)
            continue
        details = tag.get("details") or {}
        metadata = {
            "name": tag.get("name"),
            "digest": tag.get("digest"),
            "size_bytes": tag.get("size"),
            "modified_at": tag.get("modified_at"),
            "family": details.get("family"),
            "format": details.get("format"),
            "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"),
            "context_length": details.get("context_length"),
        }
        try:
            show = requests.post(f"{base}/api/show", json={"model": model}, timeout=timeout)
            show.raise_for_status()
            info = show.json()
            model_info = info.get("model_info") or {}
            metadata["capabilities"] = info.get("capabilities")
            metadata["architecture"] = model_info.get("general.architecture")
            metadata["parameter_count"] = model_info.get("general.parameter_count")
            metadata["context_length"] = metadata["context_length"] or next((value for key, value in model_info.items() if key.endswith(".context_length")), None)
            experts = next((value for key, value in model_info.items() if key.endswith(".expert_count")), None)
            if experts:
                metadata["expert_count"] = experts
                metadata["experts_used"] = next((value for key, value in model_info.items() if key.endswith(".expert_used_count")), None)
        except Exception as exc:
            report["errors"].append(f"/api/show falló para {model}: {exc}")
        missing_fields = [key for key in ("digest", "quantization_level", "parameter_size", "size_bytes") if not metadata.get(key)]
        if missing_fields:
            report["errors"].append(f"{model}: metadatos incompletos ({', '.join(missing_fields)}).")
        report["models"][model] = metadata
    return report


def unload_all(url: str) -> list[str]:
    """Free memory so only the model under test is resident (sequential execution)."""
    base = ollama_base(url)
    unloaded = []
    try:
        loaded = requests.get(f"{base}/api/ps", timeout=5).json().get("models", [])
        for item in loaded:
            requests.post(f"{base}/api/generate", json={"model": item["name"], "keep_alive": 0}, timeout=60)
            unloaded.append(item["name"])
    except Exception:
        pass
    return unloaded


def resident_resources(url: str, model: str) -> dict[str, Any] | None:
    try:
        loaded = requests.get(f"{ollama_base(url)}/api/ps", timeout=5).json().get("models", [])
    except Exception:
        return None
    for item in loaded:
        if item.get("name") in {model, f"{model}:latest"}:
            return {"resident_size_bytes": item.get("size"), "resident_vram_bytes": item.get("size_vram"), "context_length": item.get("context_length")}
    return None


def prepare(artifact: Path, input_path: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    from genai_benchmark_common import prepare_cases
    from prunin_ai.api.operational_signals import build_evidence_context
    from prunin_ai.api.recommendations import build_grounded_prompt

    runtime, cases = prepare_cases(artifact, input_path, EXPECTED_CASES)
    split = json.loads((artifact / "split_manifest.json").read_text(encoding="utf-8"))
    isolation = check_split_isolation([case["case_id"] for case in cases], split)
    if not isolation["ok"]:
        raise RuntimeError(f"Contaminación TRAIN/TEST detectada: {isolation}")
    for case in cases:
        context = build_evidence_context(case["input"], case["prediction"], case["drivers"])
        prompt, allowed = build_grounded_prompt(case["prediction"], case["drivers"], row=case["input"])
        case["evidence"] = context
        case["allowed_features"] = sorted(allowed)
        case["evidence_sha256"] = sha256_text(canonical_json(context))
        case["prompt_sha256"] = sha256_text(prompt)
    return runtime.version, cases, isolation


def evaluate(case: dict[str, Any], model: str, url: str, timeout: float) -> dict[str, Any]:
    from prunin_ai.api.recommendations import generate_ollama_grounded

    return generate_ollama_grounded(
        case["prediction"], case["drivers"], row=case["input"], model=model, url=url, timeout=timeout,
        think=MODEL_PROFILES[model]["think"], temperature=TEMPERATURE, num_predict=NUM_PREDICT,
    )


def to_row(case: dict[str, Any], model: str, phase: str, repeat: int, result: dict[str, Any]) -> dict[str, Any]:
    validation = result.get("validation") or {}
    payload = result.get("payload")
    usage = result.get("usage") or {}
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else None
    raw = str(result.get("raw_response") or "")
    return {
        "model": model,
        "phase": phase,
        "case_id": case["case_id"],
        "repeat": repeat,
        "timestamp_utc": now_utc(),
        "health": case.get("health"),
        "evidence_sha256": case["evidence_sha256"],
        "prompt_sha256": case["prompt_sha256"],
        "generation_success": bool(result.get("ok")),
        "json_parsed": payload is not None,
        "schema_valid": bool(validation.get("schema_valid")),
        "grounded": bool(validation.get("grounded")),
        "unsupported_numeric_claim": bool(validation.get("unsupported_numeric_claim")),
        "contradictory_claim": bool(validation.get("contradictory_claim")),
        "actionability": bool(validation.get("actionability")),
        "follow_up_verifiable": bool(validation.get("follow_up_verifiable")),
        "priority_valid": priority_order_valid(payload),
        "actions_generated": len(recommendations) if isinstance(recommendations, list) else 0,
        "referenced_features": list(validation.get("referenced_evidence_features") or []),
        "priorities": [item.get("priority") for item in recommendations if isinstance(item, dict)] if isinstance(recommendations, list) else [],
        "failure_code": result.get("failure_code"),
        "failure_detail": result.get("failure_detail"),
        "latency_ms": float(result.get("latency_ms") or 0.0),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "eval_duration_ns": usage.get("eval_duration_ns"),
        "load_duration_ns": usage.get("load_duration_ns"),
        "done_reason": usage.get("done_reason"),
        "thinking_chars": usage.get("thinking_chars") or 0,
        "response_sha256": sha256_text(raw),
        "raw_response": raw,
    }


def append_row(path: Path, row: dict[str, Any]) -> None:
    record = dict(row)
    record["row_sha256"] = sha256_text(canonical_json(row))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    temporary = output_dir / f".{MANIFEST}.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output_dir / MANIFEST)


def fingerprint(manifest: dict[str, Any]) -> str:
    keys = ("models", "case_ids", "repeat_case_ids", "repeats", "generation_parameters", "inputs")
    digests = {model: (manifest.get("model_metadata", {}).get(model) or {}).get("digest") for model in manifest.get("models", [])}
    return sha256_text(canonical_json({**{key: manifest.get(key) for key in keys}, "digests": digests}))


def run(
    args: argparse.Namespace,
    *,
    environment: Callable[[str, list[str]], dict[str, Any]] = check_environment,
    prepare_fn: Callable[[Path, Path], tuple[str, list[dict[str, Any]], dict[str, Any]]] = prepare,
    evaluate_fn: Callable[[dict[str, Any], str, str, float], dict[str, Any]] = evaluate,
    unload_fn: Callable[[str], list[str]] = unload_all,
    resources_fn: Callable[[str, str], dict[str, Any] | None] = resident_resources,
    simulated: bool = False,
) -> int:
    from local_model_comparison_reports import generate_reports

    models = validate_model_selection(args.models)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    if previous and previous.get("status") == "complete":
        raise FileExistsError(f"{output_dir} contiene un experimento completo; use un nuevo --output-dir.")
    if previous is None and any(output_dir.iterdir()):
        raise FileExistsError(f"{output_dir} no está vacío y no contiene un experimento reanudable.")

    env = environment(args.ollama_url, models)
    hardware = hardware_metadata()
    if env["missing"] or not env["ollama_reachable"]:
        blocked = {
            "experiment_id": output_dir.name,
            "status": "blocked_missing_dependency",
            "checked_utc": now_utc(),
            "models": models,
            "missing_models": env["missing"],
            "ollama_version": env["ollama_version"],
            "errors": env["errors"],
            "hardware": hardware,
            "next_step": "Instalar manualmente los modelos faltantes con `ollama pull <modelo>` y volver a ejecutar el mismo comando. Este script no descarga modelos.",
        }
        if previous and previous.get("status") in {"running", "incomplete"}:
            previous.update({"status": "incomplete", "blocked_on_resume": blocked})
            write_manifest(output_dir, previous)
        else:
            write_manifest(output_dir, blocked)
        print(json.dumps(blocked, indent=2, ensure_ascii=False))
        return EXIT_BLOCKED

    artifact_version, cases, isolation = prepare_fn(args.artifact, args.input)
    case_ids = [case["case_id"] for case in cases]
    repeat_ids = select_repeat_cases(case_ids, REPEAT_CASES)
    manifest = {
        "experiment_id": output_dir.name,
        "status": "running",
        "simulated": simulated,
        "started_utc": now_utc(),
        "finished_utc": None,
        "models": models,
        "model_metadata": env["models"],
        "ollama_version": env["ollama_version"],
        "environment_warnings": env["errors"],
        "hardware": hardware,
        "artifact_version": artifact_version,
        "inputs": {
            "artifact": str(args.artifact.relative_to(ROOT)) if args.artifact.is_absolute() and args.artifact.is_relative_to(ROOT) else str(args.artifact),
            "split_manifest_sha256": sha256_file(args.artifact / "split_manifest.json") if (args.artifact / "split_manifest.json").exists() else None,
            "dataset_sha256": sha256_file(args.input) if args.input.exists() else None,
        },
        "case_selection": "Último snapshot de cada proyecto TEST con al menos un driver que aumenta el riesgo; orden aleatorio random_state=42 (prepare_cases).",
        "split_check": isolation,
        "case_ids": case_ids,
        "repeat_case_ids": repeat_ids,
        "repeat_selection": "Los 5 casos con menor SHA-256 de 'prunin-repeat-v1:<case_id>' (independiente de los resultados).",
        "repeats": args.repeats,
        "generation_parameters": {
            "prompt_builder": "prunin_ai.api.recommendations.build_grounded_prompt",
            "validator": "prunin_ai.api.recommendations.validate_generated_payload",
            "format": "JSON schema forzado (action_response_schema)",
            "temperature": TEMPERATURE,
            "num_predict": NUM_PREDICT,
            "timeout_seconds": args.timeout,
            "stream": False,
            "execution": "secuencial; un solo modelo residente en memoria",
            "warmup": "1 llamada por modelo excluida de las métricas",
            "think": {model: MODEL_PROFILES[model]["think"] for model in models},
        },
        "configuration_differences": [
            {"parameter": "think", "values": {model: MODEL_PROFILES[model]["think"] for model in models}, "reason": MODEL_PROFILES["gpt-oss:20b"]["think_rationale"]},
            {"parameter": "num_predict", "values": {model: NUM_PREDICT for model in models}, "reason": "Mismo presupuesto; en GPT-OSS incluye los tokens de razonamiento, lo que reduce el margen de salida visible."},
            {"parameter": "tokenizer", "values": {model: "propio" for model in models}, "reason": "El mismo prompt produce distinto número de tokens de entrada; los tokens/s no son directamente equivalentes."},
            {"parameter": "prompt", "values": {model: "idéntico (incluye la directiva /no_think de Qwen)" for model in models}, "reason": "No se adapta el prompt por modelo para preservar la igualdad de condiciones."},
        ],
        "warmups": [],
        "resources": {},
        "human_evaluation": "No realizada. Todas las métricas son indicadores automáticos del validador.",
    }
    checkpoint = output_dir / CHECKPOINT
    if previous and previous.get("status") in {"running", "incomplete"}:
        if fingerprint(previous) != fingerprint(manifest):
            raise RuntimeError("La configuración, los casos o el digest de los modelos cambiaron; no se puede reanudar este experimento. Use un nuevo --output-dir.")
        manifest.update({key: previous[key] for key in ("started_utc", "warmups", "resources") if key in previous})
        manifest["resumed_utc"] = (previous.get("resumed_utc") or []) + [now_utc()]
    rows, problems = read_jsonl(checkpoint)
    if problems:
        manifest.setdefault("integrity_notes", []).extend(problems)
        rewrite = checkpoint.with_suffix(".tmp")
        rewrite.write_text("", encoding="utf-8")
        for row in rows:
            append_row(rewrite, row)
        rewrite.replace(checkpoint)
    done = {row_key(row) for row in rows}
    write_manifest(output_dir, manifest)

    by_id = {case["case_id"]: case for case in cases}
    try:
        for model in models:
            plan = [("main", case_id, 1) for case_id in case_ids]
            plan += [("repeat", case_id, repeat) for repeat in range(1, args.repeats + 1) for case_id in repeat_ids]
            pending = [item for item in plan if (model, *item) not in done]
            if not pending:
                continue
            unloaded = unload_fn(args.ollama_url)
            warmup = evaluate_fn(by_id[case_ids[0]], model, args.ollama_url, args.timeout)
            manifest["warmups"].append({"model": model, "timestamp_utc": now_utc(), "unloaded_before": unloaded, "latency_ms": warmup.get("latency_ms"), "failure_code": warmup.get("failure_code"), "load_duration_ns": (warmup.get("usage") or {}).get("load_duration_ns")})
            write_manifest(output_dir, manifest)
            for index, (phase, case_id, repeat) in enumerate(pending, start=1):
                result = evaluate_fn(by_id[case_id], model, args.ollama_url, args.timeout)
                row = to_row(by_id[case_id], model, phase, repeat, result)
                append_row(checkpoint, row)
                done.add(row_key(row))
                print(f"[{model}] {index}/{len(pending)} {phase} {case_id} r{repeat}: {'OK' if row['grounded'] else row['failure_code']} {row['latency_ms']:.0f} ms", flush=True)
            manifest["resources"][model] = resources_fn(args.ollama_url, model)
            write_manifest(output_dir, manifest)
    except BaseException:
        manifest["status"] = "incomplete"
        manifest["interrupted_utc"] = now_utc()
        write_manifest(output_dir, manifest)
        raise

    rows, _ = read_jsonl(checkpoint)
    status = completeness(rows, models, case_ids, repeat_ids, args.repeats)
    manifest["completeness"] = status
    if not status["complete"]:
        manifest["status"] = "incomplete"
        write_manifest(output_dir, manifest)
        print(json.dumps({"status": "incomplete", "completeness": status}, indent=2))
        return EXIT_INCOMPLETE
    manifest["finished_utc"] = now_utc()
    outputs = generate_reports(output_dir, manifest, cases, rows)
    manifest["output_sha256"] = {name: sha256_file(output_dir / name) for name in outputs}
    manifest["status"] = "complete"
    write_manifest(output_dir, manifest)
    print(json.dumps({"status": "complete", "output_dir": str(output_dir)}, indent=2))
    return EXIT_OK


def regenerate_reports(args: argparse.Namespace, *, prepare_fn: Callable[[Path, Path], tuple[str, list[dict[str, Any]], dict[str, Any]]] = prepare) -> int:
    """Re-derive every report from the verified checkpoint of a complete experiment. Runs no inference."""
    from local_model_comparison_reports import generate_reports

    output_dir: Path = args.output_dir
    manifest = json.loads((output_dir / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError("Solo se pueden regenerar reportes de un experimento completo.")
    rows, problems = read_jsonl(output_dir / CHECKPOINT)
    status = completeness(rows, manifest["models"], manifest["case_ids"], manifest["repeat_case_ids"], manifest["repeats"])
    if problems or not status["complete"]:
        raise RuntimeError(f"El checkpoint no está íntegro: {problems or status}")
    _, cases, _ = prepare_fn(args.artifact, args.input)
    by_id = {case["case_id"]: case for case in cases}
    if [case["case_id"] for case in cases] != manifest["case_ids"] or any(
        row["prompt_sha256"] != by_id[row["case_id"]]["prompt_sha256"] or row["evidence_sha256"] != by_id[row["case_id"]]["evidence_sha256"] for row in rows
    ):
        raise RuntimeError("Los casos reconstruidos no coinciden con los registrados; no se regeneran reportes.")
    outputs = generate_reports(output_dir, manifest, cases, rows)
    manifest["output_sha256"] = {name: sha256_file(output_dir / name) for name in outputs}
    manifest["reports_regenerated_utc"] = (manifest.get("reports_regenerated_utc") or []) + [now_utc()]
    write_manifest(output_dir, manifest)
    print(json.dumps({"status": "reports_regenerated", "files": len(outputs)}, indent=2))
    return EXIT_OK


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Comparación local reproducible Qwen3 8B vs. GPT-OSS 20B (PRUNIN AI Core).")
    parser.add_argument("--models", nargs="+", default=list(AUTHORIZED_MODELS))
    parser.add_argument("--cases", type=int, default=EXPECTED_CASES)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/0.9.0-academic")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/mendeley_core.csv")
    parser.add_argument("--ollama-url", default=os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/genai/qwen_vs_gptoss_2026")
    parser.add_argument("--regenerate-reports", action="store_true", help="Regenera los reportes de un experimento completo desde runs.jsonl, sin inferencias.")
    args = parser.parse_args(argv)
    if args.cases != EXPECTED_CASES:
        parser.error("La comparación PAIII usa exactamente 30 casos TEST.")
    if not 2 <= args.repeats <= 10:
        parser.error("--repeats debe estar entre 2 y 10.")
    try:
        args.models = validate_model_selection(args.models)
    except UnauthorizedModelError as exc:
        parser.error(str(exc))
    if not args.output_dir.is_absolute():
        args.output_dir = (Path.cwd() / args.output_dir).resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    args = parse_args(argv)
    code = regenerate_reports(args) if args.regenerate_reports else run(args)
    print(f"Duración total: {time.perf_counter() - started:.1f} s")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
