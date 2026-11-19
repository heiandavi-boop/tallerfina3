#!/usr/bin/env python3
"""Read-only gate for scientific evidence and contradictory PAIII delivery claims.

This checks files already versioned in the repository. It does NOT execute Ollama,
enroll participants, assess oral delivery or award a rubric grade.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root: Path) -> list[str]:
    issues: list[str] = []
    comparison = root / "reports/genai/qwen_vs_gptoss_2026"
    summary_path = comparison / "benchmark_summary.json"
    manifest_path = comparison / "execution_manifest.json"
    productivity_path = root / "reports/human_validation/productivity_summary.json"
    rubric_path = root / "docs/RUBRICA_OFICIAL_PAIII_2026.md"
    report_path = root / "docs/INFORME_FINAL.md"
    for path in (summary_path, manifest_path, productivity_path, rubric_path, report_path):
        if not path.is_file():
            issues.append(f"Missing evidence: {path.relative_to(root)}")
    if issues:
        return issues
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        productivity = json.loads(productivity_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        return [f"Invalid evidence document: {exc}"]
    expected = {"qwen3:8b", "gpt-oss:20b"}
    if set(manifest.get("models", [])) != expected:
        issues.append("Comparison must contain exactly the two designated local models")
    if manifest.get("status") != "complete" or manifest.get("simulated") is not False:
        issues.append("Comparison must explicitly be complete and non-simulated")
    comp = manifest.get("completeness", {})
    if not (comp.get("complete") is True and comp.get("present") == comp.get("expected") == 90 and comp.get("missing") == 0 and comp.get("duplicates") == 0):
        issues.append("Comparison must contain 90 non-duplicated observed runs")
    split = manifest.get("split_check", {})
    if not (split.get("ok") is True and split.get("all_cases_in_test") is True and not split.get("train_overlap") and not split.get("validation_overlap")):
        issues.append("TEST cohort isolation is not established")
    if summary.get("decision", {}).get("evidence_complete") is not True:
        issues.append("Decision evidence is incomplete")
    if set(summary.get("models", {})) != expected:
        issues.append("Benchmark summary model list is incomplete or unexpected")
    rubric = rubric_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    cr2 = next((line for line in rubric.splitlines() if line.startswith("| R6.1-Cr2 |")), "")
    if "qwen_vs_gptoss_2026" not in cr2 or "DEMOSTRADO CON LIMITACIONES" not in cr2:
        issues.append("Rubric R6.1-Cr2 must cite the measured comparison and retain its limitations")
    for code in ("R6.2-Cr6", "R7.2-Cr4", "R7.2-Cr5", "R7.2-Cr6"):
        if not any(line.startswith(f"| {code} |") and "| PARCIAL |" in line for line in rubric.splitlines()):
            issues.append(f"Rubric must not assert unverified full completion: {code}")
    if productivity.get("complete_participants", 0) < productivity.get("min_participants", 6):
        if productivity.get("status") != "NO MEDIDA":
            issues.append("Human productivity cannot be reported measured without sufficient participants")
        if "Productividad humana: NO MEDIDA" not in report and "Productividad humana NO MEDIDA" not in report:
            issues.append("Public academic report must disclose that human productivity has not been measured")
    selection = root / "docs/genai_model_selection.md"
    if not selection.is_file() or "Qwen3 8B vs. GPT-OSS 20B" not in selection.read_text(encoding="utf-8"):
        issues.append("Public model selection must disclose the actual paired model comparison")
    # Delivery consistency: count rubric outcomes, verify KPI semantics, and avoid
    # references to presentation notes intentionally removed from the public tree.
    rubric_rows = [line.split("|") for line in rubric.splitlines()
                   if line.startswith("| R6.") or line.startswith("| R7.")
                   or line.startswith("| RA1-") or line.startswith("| RA2-")]
    rubric_counts = {"DEMOSTRADO CON LIMITACIONES": 0,
                     "PARCIAL": 0, "REQUIERE EVALUACIÓN HUMANA": 0}
    for cells in rubric_rows:
        if len(cells) < 7:
            issues.append("Malformed rubric criterion row")
            continue
        status = cells[5].strip()
        if status not in rubric_counts:
            issues.append(f"Unexpected rubric status: {status}")
        else:
            rubric_counts[status] += 1
    if len(rubric_rows) != 27 or rubric_counts != {
        "DEMOSTRADO CON LIMITACIONES": 16,
        "PARCIAL": 4, "REQUIERE EVALUACIÓN HUMANA": 7
    }:
        issues.append(f"Rubric counts changed; review evidence: {rubric_counts}")

    promise_path = root / "reports/promise_validation/risk_alert_metrics.json"
    if not promise_path.is_file():
        issues.append("Missing risk-alert KPI report")
    else:
        try:
            promise = json.loads(promise_path.read_text(encoding="utf-8"))
            final_risk = promise["final"]["final_risk_projects"]
            cutoff = next(row for row in promise["temporal"]
                          if row.get("cutoff_percent") == 60)
            if final_risk != 473 or cutoff.get("tp") != 359:
                issues.append("Risk-alert numerator or denominator changed; revalidate slides")
            if abs(cutoff.get("full_cohort_detection_rate", 0) -
                   359 / 473) > 1e-10:
                issues.append("Incorrect 60% Risk Alert detection metric")
            if abs(promise["final"].get("exact_critical_recall", 0) -
                   0.5681818181818182) > 1e-10:
                issues.append("Critical exact recall changed; revalidate limitations")
        except (KeyError, ValueError, StopIteration, TypeError, json.JSONDecodeError) as exc:
            issues.append(f"Cannot verify risk-alert report: {exc}")

    readme_path = root / "README.md"
    mlops_path = root / "docs/mlops_production.md"
    for path in (readme_path, report_path, mlops_path):
        if path.is_file() and "FINAL_READINESS.md" in path.read_text(encoding="utf-8"):
            issues.append(f"Stale public link to private notes: {path.relative_to(root)}")
    delivery_status = root / "docs/ESTADO_VERIFICACION_ENTREGA.md"
    if not delivery_status.is_file():
        issues.append("Missing current delivery verification checklist")
    if "Autor: completar" in report or "HEAD final exacto y CI se consignan" in report:
        issues.append("Final academic report still contains outdated cover or CI placeholders")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    issues = check(args.root.resolve())
    print(json.dumps({"status": "PASS" if not issues else "FAIL", "checks": "PAIII scientific evidence and claim consistency", "issues": issues}, indent=2, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
