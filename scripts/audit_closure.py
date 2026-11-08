from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_files() -> list[Path]:
    folders = ["data/raw", "artifacts/0.9.0-academic", "reports/0.9.0-academic", "reports/promise_validation",
               "reports/genai/comparison", "reports/genai/concurrency", "reports/genai/action_recommendations"]
    paths = {path for folder in folders for path in (ROOT / folder).rglob("*") if path.is_file() and not path.name.startswith(".")}
    paths.update(ROOT / name for name in ["data/processed/mendeley_core.csv", "configs/training.yaml",
                 "src/prunin_ai/targets.py", "src/prunin_ai/inference/brain.py", "src/prunin_ai/api/model_runtime.py",
                 "reports/genai/qwen3-8b-evaluation.json", "reports/genai/qwen3-8b-evaluation.csv"])
    return sorted(path for path in paths if path.is_file())


def environment() -> dict[str, Any]:
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "platform": platform.platform(), "cpu_count": os.cpu_count(),
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "node": subprocess.check_output(["node", "--version"], text=True).strip()}


def write_new(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def snapshot(output: Path) -> None:
    from prunin_ai.api.catalog import PRESETS
    from prunin_ai.api.model_runtime import ModelRuntime

    runtime = ModelRuntime()
    payload = {"environment": environment(), "hashes": {str(path.relative_to(ROOT)): sha256(path) for path in protected_files()},
               "predictions": {name: runtime.predict(row) for name, row in PRESETS.items()},
               "note": "Captured before any scientific artifact changes; interpretation-layer edits may already exist. No scientific files are regenerated."}
    write_new(output, payload)
    print(json.dumps({"snapshot": str(output), "files": len(payload["hashes"]), "models": len(list((runtime.artifact_dir).glob("*.joblib")))}))


def verify(baseline: Path, output: Path) -> None:
    from prunin_ai.api.catalog import PRESETS
    from prunin_ai.api.model_runtime import ModelRuntime

    before = json.loads(baseline.read_text(encoding="utf-8"))
    changes = [name for name, digest in before["hashes"].items() if not (ROOT / name).is_file() or sha256(ROOT / name) != digest]
    runtime = ModelRuntime()
    predictions_identical = before["predictions"] == {name: runtime.predict(row) for name, row in PRESETS.items()}
    split = json.loads((runtime.artifact_dir / "split_manifest.json").read_text())
    groups = {name: set(map(str, split[name])) for name in ("train", "validation", "test")}
    disjoint = not (groups["train"] & groups["validation"] or groups["train"] & groups["test"] or groups["validation"] & groups["test"])
    reproduction = json.loads((runtime.artifact_dir / "reproducibility.json").read_text())
    fingerprints = {"data/processed/mendeley_core.csv": reproduction["dataset_sha256"]["processed"],
                    **reproduction["dataset_sha256"]["raw_mendeley_files"]}
    fingerprint_results = {name: (ROOT / name).is_file() and sha256(ROOT / name) == digest for name, digest in fingerprints.items()}
    payload = {"environment": environment(), "baseline": str(baseline.relative_to(ROOT)), "files_checked": len(before["hashes"]),
               "changed_protected_files": changes, "predictions_identical": predictions_identical,
               "split_counts": {name: len(group) for name, group in groups.items()}, "split_disjoint": disjoint,
               "recorded_dataset_fingerprints_match": fingerprint_results,
               "reproducibility_manifest": reproduction}
    write_new(output, payload)
    print(json.dumps({key: value for key, value in payload.items() if key != "reproducibility_manifest"}, indent=2))
    if changes or not predictions_identical or not disjoint or not all(fingerprint_results.values()):
        raise SystemExit(1)


def run_gates(output: Path) -> None:
    commands = [
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
        [sys.executable, "-m", "pytest", "-q"],
        ["npm", "ci", "--prefix", "frontend"],
        ["npm", "test", "--prefix", "frontend", "--", "--run"],
        ["npm", "run", "build", "--prefix", "frontend", "--", "--emptyOutDir=false"],
        ["npm", "audit", "--prefix", "frontend"],
        [sys.executable, "scripts/validate_original_promise.py", "--check"],
        ["./scripts/preflight_demo.sh"],
        ["./scripts/preflight_genai.sh"],
    ]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PRUNIN_ENABLE_OLLAMA": "0"}
    results = []
    for index, command in enumerate(commands, start=1):
        started = datetime.now(timezone.utc).isoformat()
        command_env = {**env, "PRUNIN_ENABLE_OLLAMA": "1"} if command == ["./scripts/preflight_genai.sh"] else env
        completed = subprocess.run(command, cwd=ROOT, env=command_env, capture_output=True, text=True, timeout=600, check=False)
        log = output.parent / output.stem / f"gate-{index:02d}.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("x", encoding="utf-8") as handle:
            handle.write(completed.stdout + completed.stderr)
        results.append({"command": command, "started_at_utc": started, "returncode": completed.returncode,
                        "evidence": str(log.relative_to(ROOT)), "last_lines": (completed.stdout + completed.stderr).splitlines()[-8:]})
        print(" ".join(command), "returncode=" + str(completed.returncode), flush=True)
    write_new(output, {"environment": environment(), "checks": results,
                       "limitations": ["Local Node version differs from Node 22 pinned in CI.", "A local pass is not CI for an unpublished change."]})
    if any(item["returncode"] for item in results):
        raise SystemExit(1)


def inspect_environment(output: Path) -> None:
    import requests

    report: dict[str, Any] = {"environment": environment(), "commands": [], "model_distribution_metadata": []}
    commands = [["docker", "version", "--format", "{{json .}}"], ["sysctl", "-n", "hw.memsize"],
                ["df", "-h", "."], ["git", "status", "--short", "--branch"]]
    for command in commands:
        try:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
            report["commands"].append({"command": command, "returncode": completed.returncode, "output": completed.stdout + completed.stderr})
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["commands"].append({"command": command, "error": type(exc).__name__})
    base = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat").rsplit("/api/", 1)[0]
    for endpoint in ("tags", "version", "ps"):
        response = requests.get(base + "/api/" + endpoint, timeout=5)
        report["ollama_" + endpoint] = response.json() if response.ok else {"status": response.status_code}
    for name, tag in (("gemma3", "4b"), ("ministral-3", "8b"), ("ministral", "8b")):
        url = f"https://registry.ollama.ai/v2/library/{name}/manifests/{tag}"
        response = requests.get(url, timeout=20)
        payload = response.json() if response.ok else {}
        report["model_distribution_metadata"].append({"tag": f"{name}:{tag}", "url": url, "status": response.status_code,
            "layer_bytes": sum(layer.get("size", 0) for layer in payload.get("layers", [])),
            "manifest_sha256": hashlib.sha256(response.content).hexdigest() if response.ok else None,
            "note": "Only manifest metadata fetched; no model blobs downloaded. Disk size is not a certified RAM requirement."})
    response = requests.get("https://api.github.com/repos/heiandavi-boop/tallerfina3/actions/runs",
                            params={"head_sha": report["environment"]["head"], "per_page": 10}, timeout=20)
    report["remote_ci"] = [{key: run.get(key) for key in ("id", "head_sha", "name", "status", "conclusion", "html_url")}
                           for run in response.json().get("workflow_runs", [])] if response.ok else {"http_status": response.status_code}
    report["ci_limitation"] = "Remote runs refer to committed HEAD only, never to the local uncommitted diff. No push performed."
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    secret_pattern = re.compile(rb"(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
    report["limited_secret_scan"] = {"matches_files_only": [name for name in tracked if name and (ROOT / name).is_file() and secret_pattern.search((ROOT / name).read_bytes())],
                                     "limitation": "Known private-key/AWS/GitHub patterns only; not a comprehensive security audit. No secret values recorded."}
    protected_docs = ["PREGUNTAS_DEFENSA.md", "GLOSARIO_DEFENSA.md", "PRESENTACION_FINAL.md", "ENTREGA_FINAL_CHECKLIST.md", "FINAL_READINESS.md"]
    report["local_documents"] = [{"path": "docs/" + name, "exists": (ROOT / "docs" / name).is_file(), "tracked": "docs/" + name in tracked,
                                 "ignored": subprocess.run(["git", "check-ignore", "-q", "docs/" + name], cwd=ROOT, check=False).returncode == 0}
                                for name in protected_docs]
    report["official_rubric"] = {"available_in_workspace": False, "limitation": "Only the internal 27-item matrix is present; exact official wording, weights and maximum-level descriptors cannot be certified."}
    write_new(output, report)
    print(json.dumps({"evidence": str(output), "remote_ci": report["remote_ci"], "secret_matches": report["limited_secret_scan"]["matches_files_only"]}, indent=2))


def verify_robustness(output: Path) -> None:
    import requests
    from fastapi.testclient import TestClient

    from prunin_ai.api.app import app, runtime
    from prunin_ai.api.recommendations import build_recommendations, validate_generated_payload

    source = json.loads((output.parent / "recommendations-evidence-v2-r2.json").read_text())
    revalidated = []
    for case in source["cases"]:
        validation = validate_generated_payload(case["generation"]["payload"], set(case["allowed_features"]),
                                                 prediction=case["prediction"], drivers=case["drivers"], context=case["context"])
        revalidated.append({"case_id": case["case_id"], "validation": validation})
    row = source["cases"][1]["input"]
    actual_url = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat")
    os.environ["PRUNIN_ENABLE_OLLAMA"] = "1"
    os.environ["PRUNIN_OLLAMA_URL"] = "http://127.0.0.1:1/api/chat"
    with TestClient(app) as client:
        offline = client.post("/api/predict", json=row)
        offline.raise_for_status()
        offline_body = offline.json()
        os.environ["PRUNIN_OLLAMA_URL"] = actual_url
        recovered = client.post("/api/predict", json=row)
        recovered.raise_for_status()
        recovered_body = recovered.json()
        invalid_inputs = []
        for name, payload in (("coverage", {"spi": 0.72}), ("range", {**row, "spi": 0.01}),
                              ("category", {**row, "methodology": "unknown"})):
            response = client.post("/api/predict?include_recommendations=false", json=payload)
            invalid_inputs.append({"case": name, "status_code": response.status_code, "controlled_rejection": response.status_code == 422})
        def ml_request(index: int) -> dict[str, Any]:
            response = client.post("/api/predict?include_recommendations=false", json=row)
            body = response.json()
            return {"request": index, "status_code": response.status_code, "prediction": body.get("prediction"),
                    "engine": body.get("recommendations", {}).get("engine")}
        with ThreadPoolExecutor(max_workers=4) as executor:
            ml_rows = list(executor.map(ml_request, range(12)))
    prediction = runtime.predict(row)
    drivers = runtime.local_drivers(row, prediction)
    with ThreadPoolExecutor(max_workers=2) as executor:
        genai_rows = list(executor.map(lambda index: build_recommendations(row, prediction, drivers), range(2)))
    ps = requests.get(actual_url.rsplit("/api/", 1)[0] + "/api/ps", timeout=5).json()
    checks = {
        "historical_real_payloads_pass_current_validator": all(item["validation"]["grounded"] for item in revalidated),
        "offline_fallback": offline_body["recommendations"]["failure_code"] == "ollama_unavailable" and offline_body["recommendations"]["fallback_validation"]["grounded"],
        "real_recovery_used_genai": recovered_body["recommendations"]["genai_used"],
        "prediction_unchanged_after_fault": offline_body["prediction"] == recovered_body["prediction"],
        "input_rejections": all(item["controlled_rejection"] for item in invalid_inputs),
        "concurrent_ml_consistent": all(item["status_code"] == 200 and item["prediction"] == prediction and item["engine"] == "not_requested" for item in ml_rows),
        "concurrent_genai_degrades_safely": all(item["genai_used"] or item["fallback_validation"]["grounded"] for item in genai_rows),
    }
    write_new(output, {"environment": environment(), "contract_version": "evidence-v2", "checks": checks,
                       "revalidated_real_payloads": revalidated, "input": row, "offline_response": offline_body,
                       "recovered_response": recovered_body, "invalid_inputs": invalid_inputs,
                       "ml_concurrency": {"workers": 4, "requests": ml_rows},
                       "genai_concurrency": {"workers": 2, "requests": genai_rows},
                       "ollama_reported_loaded_models": ps,
                       "limitations": ["In-process TestClient API smoke, not network throughput or distributed load.",
                                       "Two real concurrent Qwen calls are a smoke check, not a production capacity estimate.",
                                       "Connection failure simulated via a closed loopback port; the user's Ollama service was not stopped.",
                                       "Ollama /api/ps reports loaded size, not independently measured peak RAM."]})
    print(json.dumps(checks, indent=2))
    print("Concurrent engines:", [item["engine"] for item in genai_rows])
    if not all(checks.values()):
        raise SystemExit(1)


def evaluate_recommendations(output: Path) -> None:
    import requests

    from prunin_ai.api.catalog import PRESETS
    from prunin_ai.api.model_runtime import ModelRuntime
    from prunin_ai.api.operational_signals import build_evidence_context
    from prunin_ai.api.recommendations import build_grounded_prompt, generate_ollama_grounded, grounded_fallback

    runtime = ModelRuntime()
    banking = {"planned_duration_weeks": 52, "planned_budget": 2500000000, "true_progress": 0.47,
               "spi": 0.72, "cpi": 0.81, "team_utilization": 1.12, "team_capacity_ratio": 0.72,
               "average_productivity": 0.68, "rework_ratio": 0.19, "defect_rate": 0.11,
               "dependency_delay_days": 15, "normalized_risk_exposure": 0.49}
    cases = {"banking_supplied_fields": banking, "banking_it_hybrid": {**banking, "project_type": "it", "methodology": "hybrid"},
             "healthy": PRESETS["healthy"], "schedule": {**PRESETS["healthy"], "spi": 0.72},
             "cost": {**PRESETS["healthy"], "cpi": 0.81},
             "overload": {**PRESETS["healthy"], "team_utilization": 1.12, "team_capacity_ratio": 0.72},
             "quality": {**PRESETS["healthy"], "rework_ratio": 0.19, "defect_rate": 0.11},
             "insufficient_operational_evidence": {key: PRESETS["healthy"][key] for key in runtime.brain.feature_names}}
    base = os.getenv("PRUNIN_OLLAMA_URL", "http://localhost:11434/api/chat").rsplit("/api/", 1)[0]
    tags_response = requests.get(base + "/api/tags", timeout=5)
    tags_response.raise_for_status()
    tags = tags_response.json()
    model = os.getenv("PRUNIN_OLLAMA_MODEL", "qwen3:8b")
    installed = {item["name"] for item in tags["models"]}
    if model not in installed:
        raise RuntimeError(f"Model {model} is not installed; no download attempted.")
    original = subprocess.check_output(["git", "show", "HEAD:src/prunin_ai/api/recommendations.py"], cwd=ROOT, text=True)
    namespace = {"__name__": "prunin_ai.api._audit_baseline", "__package__": "prunin_ai.api"}
    exec(compile(original, "HEAD:recommendations.py", "exec"), namespace)
    rows = []
    for case_id, row in cases.items():
        prediction = runtime.predict(row)
        drivers = runtime.local_drivers(row, prediction)
        prompt, allowed = build_grounded_prompt(prediction, drivers, row=row)
        generated = generate_ollama_grounded(prediction, drivers, row=row, model=model)
        fallback = grounded_fallback(row, prediction, drivers)
        before = namespace["grounded_fallback"](row, prediction, drivers)
        old_prompt, old_allowed = namespace["build_grounded_prompt"](prediction, drivers)
        old_generation = namespace["generate_ollama_grounded"](prediction, drivers, model=model) if case_id == "banking_it_hybrid" else None
        rows.append({"case_id": case_id, "input": row, "prediction": prediction, "drivers": drivers,
                     "positive_drivers": [item for item in drivers if item["direction"] == "increases_risk"],
                     "before": {"fallback": before, "allowed_features": sorted(old_allowed), "real_generation": old_generation,
                                "prompt": old_prompt if old_generation else None},
                     "context": build_evidence_context(row, prediction, drivers), "prompt": prompt,
                     "allowed_features": sorted(allowed), "generation": generated, "fallback": fallback,
                     "final_engine": f"ollama:{model}" if generated["ok"] else "grounded_fallback",
                     "final_actions": generated["payload"]["recommendations"] if generated["ok"] else fallback["recommendations"]})
        print(case_id, "ok=" + str(generated["ok"]), "drivers=" + str(len(drivers)), "allowed=" + str(len(allowed)), "failure=" + str(generated["failure_code"]), flush=True)
    latencies = sorted(item["generation"]["latency_ms"] for item in rows)
    rate = lambda key: sum(bool(item["generation"]["validation"].get(key)) for item in rows) / len(rows)
    payload = {"environment": environment(), "contract_version": "evidence-v2", "ollama_tags": tags,
               "config": {"model": model, "temperature": 0.1, "num_predict": 1200, "timeout_seconds": 30, "think": False},
               "metrics": {"cases": len(rows), "generation_success_rate": sum(item["generation"]["ok"] for item in rows) / len(rows),
                           "schema_valid_rate": rate("schema_valid"), "groundedness_proxy": rate("grounded"), "actionability_proxy": rate("actionability"),
                           "unsupported_numeric_claim_rate": rate("unsupported_numeric_claim"), "latency_p50_ms": (latencies[3] + latencies[4]) / 2,
                           "latency_p95_ms": latencies[-1], "timeouts": sum(item["generation"]["failure_code"] == "ollama_timeout" for item in rows),
                           "invalid_json": sum(item["generation"]["failure_code"] == "invalid_json" for item in rows)},
               "limitations": ["Eight diagnostic/development cases, not a held-out benchmark or utility evaluation.",
                               "Missing banking categorical inputs are not guessed in the supplied-fields case; the IT/hybrid variant is explicitly assumed.",
                               "Before/after use the same installed model sequentially; latency is not a controlled performance comparison.",
                               "Semantic correctness and human usefulness are not established by structural proxies."], "cases": rows}
    write_new(output, payload)
    print(json.dumps(payload["metrics"], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Non-destructive audit evidence; output files must be new.")
    parser.add_argument("action", choices=["snapshot", "verify", "recommendations", "gates", "inspect", "robustness"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.baseline is not None:
        args.baseline = args.baseline.resolve()
    if args.output.exists():
        parser.error("Output already exists; choose a new path. Frozen evidence is never overwritten.")
    if args.action == "snapshot":
        snapshot(args.output)
    elif args.action == "recommendations":
        evaluate_recommendations(args.output)
    elif args.action == "gates":
        run_gates(args.output)
    elif args.action == "inspect":
        inspect_environment(args.output)
    elif args.action == "robustness":
        verify_robustness(args.output)
    elif args.baseline is not None:
        verify(args.baseline, args.output)
    else:
        parser.error("verify requires --baseline")


if __name__ == "__main__":
    main()