#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.api.recommendations import generate_ollama_grounded


def _tags_url(chat_url: str) -> str:
    return chat_url.rsplit("/api/", 1)[0] + "/api/tags" if "/api/" in chat_url else chat_url.rstrip("/") + "/api/tags"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test local para Ollama + Qwen grounded.")
    parser.add_argument("--model", default=os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--ollama-url", default=os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat"))
    parser.add_argument("--api-url", default=os.getenv("PRUNIN_API_URL", "http://localhost:8000"))
    parser.add_argument("--timeout", type=float, default=None)
    args = parser.parse_args()

    checks: list[tuple[str, bool]] = []
    started = time.perf_counter()
    tags = {}
    try:
        response = requests.get(_tags_url(args.ollama_url), timeout=3)
        response.raise_for_status()
        tags = response.json()
        checks.append(("Ollama available", True))
    except Exception as exc:
        checks.append(("Ollama available", False))
        print(f"Ollama check error: {type(exc).__name__}: {exc}", file=sys.stderr)
    installed = {str(item.get("name", "")) for item in tags.get("models", []) if isinstance(item, dict)}
    model_available = args.model in installed or f"{args.model}:latest" in installed
    checks.append((f"Model {args.model}", model_available))

    try:
        status_response = requests.get(f"{args.api_url.rstrip('/')}/api/genai-status", timeout=4)
        status_response.raise_for_status()
        api_status = status_response.json()
        checks.append(("GenAI API status", bool(api_status.get("enabled") and api_status.get("available") and api_status.get("model") == args.model)))
    except Exception as exc:
        status_ready = False
        checks.append(("GenAI API status", False))
        print(f"API status error: {type(exc).__name__}: {exc}", file=sys.stderr)

    generated = None
    if checks[0][1] and model_available:
        prediction = {"health": "at_risk", "delay_days": 27.3, "cost_overrun_ratio": 0.04}
        drivers = [{"feature": "cpi", "label": "CPI", "value": 0.82, "reference": 1.0, "direction": "increases_risk"}]
        generated = generate_ollama_grounded(prediction, drivers, model=args.model, url=args.ollama_url, timeout=args.timeout)
    response_received = bool(generated and generated.get("payload") is not None)
    validation = generated.get("validation", {}) if generated else {}
    checks.append(("Generation", response_received))
    checks.append(("JSON schema", bool(validation.get("schema_valid"))))
    checks.append(("Evidence grounding", bool(validation.get("grounded"))))

    for label, passed in checks:
        print(f"{label:.<27} {'PASS' if passed else 'FAIL'}")
    if generated:
        print(f"Latency{' ':.<18} {generated['latency_ms'] / 1000:.2f} s")
        if generated.get("failure_code"):
            print(f"Failure{' ':.<18} {generated['failure_code']}: {generated.get('failure_detail')}")
    print("RESULTADO: OLLAMA READY" if all(passed for _, passed in checks) else "RESULTADO: OLLAMA NOT READY")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())