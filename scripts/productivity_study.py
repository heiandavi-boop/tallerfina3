"""Human productivity study for PRUNIN (R6.2-Cr6): manual vs assisted analysis.

Subcommands:
  assign   Counterbalanced AB/BA plan with difficulty-matched case pairs.
  analyze  Validates real observations and computes time/quality deltas.

Without consented real participants the analysis reports status "NO MEDIDA";
it never synthesizes observations.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "reports" / "human_validation" / "results.csv"
DEFAULT_OUTPUT = ROOT / "reports" / "human_validation" / "productivity_summary.json"
CONDITIONS = ("manual", "prunin")
QUALITY_FIELDS = (
    "quality_alert_score",
    "quality_severity_score",
    "quality_delay_cost_score",
    "quality_evidence_score",
    "quality_action_score",
)
REQUIRED_FIELDS = (
    "participant_id",
    "case_id",
    "condition",
    "order",
    "time_seconds",
    "consent",
    *QUALITY_FIELDS,
)
MIN_PARTICIPANTS = 6
# Assisted analysis must not lose more than this many quality points (0-5 scale) to count as an improvement.
QUALITY_NON_INFERIORITY_MARGIN = 0.25


def time_improvement_pct(manual_seconds: float, assisted_seconds: float) -> float:
    if manual_seconds <= 0:
        raise ValueError("manual time must be positive")
    return (manual_seconds - assisted_seconds) / manual_seconds * 100.0


def pair_cases_by_difficulty(cases: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Pairs adjacent cases after sorting by difficulty so both conditions see comparable load."""
    ordered = sorted(cases, key=lambda case: (float(case["difficulty"]), str(case["case_id"])))
    if len(ordered) < 2:
        raise ValueError("at least two cases are required")
    return [(ordered[i]["case_id"], ordered[i + 1]["case_id"]) for i in range(0, len(ordered) - 1, 2)]


def assign(participant_ids: list[str], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Balanced crossover: order (manual-first/prunin-first) and case-to-condition mapping both alternate."""
    pairs = pair_cases_by_difficulty(cases)
    plan = []
    for index, participant in enumerate(participant_ids):
        case_a, case_b = pairs[(index // 4) % len(pairs)]
        manual_first = index % 2 == 0
        swap_cases = (index // 2) % 2 == 1
        manual_case, assisted_case = (case_b, case_a) if swap_cases else (case_a, case_b)
        sequence = [("manual", manual_case), ("prunin", assisted_case)]
        if not manual_first:
            sequence.reverse()
        for order, (condition, case_id) in enumerate(sequence, start=1):
            plan.append({"participant_id": participant, "case_id": case_id, "condition": condition, "order": order})
    return plan


def _float(value: Any, field: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"row {row_number}: {field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"row {row_number}: {field} must be finite")
    return number


def validate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = []
    for number, row in enumerate(rows, start=2):
        missing = [field for field in REQUIRED_FIELDS if str(row.get(field, "")).strip() == ""]
        if missing:
            raise ValueError(f"row {number}: missing {', '.join(missing)}")
        if str(row["consent"]).strip().lower() not in {"yes", "si", "sí", "true", "1"}:
            raise ValueError(f"row {number}: observation without recorded consent")
        if row["condition"] not in CONDITIONS:
            raise ValueError(f"row {number}: condition must be manual or prunin")
        time_seconds = _float(row["time_seconds"], "time_seconds", number)
        if time_seconds <= 0:
            raise ValueError(f"row {number}: time_seconds must be positive")
        quality = []
        for field in QUALITY_FIELDS:
            score = _float(row[field], field, number)
            if not 0 <= score <= 5:
                raise ValueError(f"row {number}: {field} must be within 0-5")
            quality.append(score)
        clean.append({**row, "time_seconds": time_seconds, "order": int(_float(row["order"], "order", number)), "quality": statistics.fmean(quality)})
    seen = {(row["participant_id"], row["condition"]) for row in clean}
    if len(seen) != len(clean):
        raise ValueError("each participant must have at most one observation per condition")
    return clean


def _paired_test(differences: list[float]) -> dict[str, Any]:
    if len(differences) < 2 or statistics.pstdev(differences) == 0:
        return {"test": "wilcoxon_signed_rank", "p_value": None, "reason": "insufficient_variation"}
    from scipy.stats import wilcoxon

    result = wilcoxon(differences)
    return {"test": "wilcoxon_signed_rank", "statistic": float(result.statistic), "p_value": float(result.pvalue)}


def analyze(rows: list[dict[str, Any]], min_participants: int = MIN_PARTICIPANTS) -> dict[str, Any]:
    clean = validate_rows(rows)
    by_participant: dict[str, dict[str, dict[str, Any]]] = {}
    for row in clean:
        by_participant.setdefault(row["participant_id"], {})[row["condition"]] = row
    complete = {pid: data for pid, data in by_participant.items() if set(data) == set(CONDITIONS)}
    base = {
        "formula": "(T_manual - T_asistido) / T_manual * 100",
        "quality_non_inferiority_margin": QUALITY_NON_INFERIORITY_MARGIN,
        "observations": len(clean),
        "complete_participants": len(complete),
        "min_participants": min_participants,
    }
    if len(complete) < min_participants:
        return {**base, "status": "NO MEDIDA", "reason": "insufficient_real_participants"}
    manual_times = [data["manual"]["time_seconds"] for data in complete.values()]
    assisted_times = [data["prunin"]["time_seconds"] for data in complete.values()]
    per_participant = [time_improvement_pct(m, a) for m, a in zip(manual_times, assisted_times)]
    quality_delta = [data["prunin"]["quality"] - data["manual"]["quality"] for data in complete.values()]
    order_effect = {
        f"{first}_first": statistics.fmean(
            time_improvement_pct(data["manual"]["time_seconds"], data["prunin"]["time_seconds"])
            for data in complete.values()
            if data[first]["order"] == 1
        )
        for first in CONDITIONS
        if any(data[first]["order"] == 1 for data in complete.values())
    }
    median_manual = statistics.median(manual_times)
    median_assisted = statistics.median(assisted_times)
    mean_quality_delta = statistics.fmean(quality_delta)
    improvement = time_improvement_pct(median_manual, median_assisted)
    quality_ok = mean_quality_delta >= -QUALITY_NON_INFERIORITY_MARGIN
    return {
        **base,
        "status": "MEDIDA",
        "time_seconds_median": {"manual": median_manual, "prunin": median_assisted},
        "time_improvement_pct_of_medians": improvement,
        "time_improvement_pct_per_participant_median": statistics.median(per_participant),
        "time_test": _paired_test([m - a for m, a in zip(manual_times, assisted_times)]),
        "quality_mean": {
            "manual": statistics.fmean(data["manual"]["quality"] for data in complete.values()),
            "prunin": statistics.fmean(data["prunin"]["quality"] for data in complete.values()),
        },
        "quality_delta_mean": mean_quality_delta,
        "quality_test": _paired_test(quality_delta),
        "order_effect_time_improvement_pct": order_effect,
        "productivity_claim_supported": improvement > 0 and quality_ok,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("assign")
    plan.add_argument("--participants", type=int, required=True)
    plan.add_argument("--cases", type=Path, required=True, help="CSV with case_id,difficulty")
    plan.add_argument("--output", type=Path, required=True)
    report = sub.add_parser("analyze")
    report.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    report.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    report.add_argument("--min-participants", type=int, default=MIN_PARTICIPANTS)
    args = parser.parse_args(argv)

    if args.command == "assign":
        with args.cases.open(newline="", encoding="utf-8") as handle:
            cases = list(csv.DictReader(handle))
        participants = [f"P{index:03d}" for index in range(1, args.participants + 1)]
        rows = assign(participants, cases)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"plan: {len(rows)} sessions -> {args.output}")
        return 0

    rows: list[dict[str, Any]] = []
    if args.results.exists():
        with args.results.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    summary = {"results_file": str(args.results.relative_to(ROOT) if args.results.is_relative_to(ROOT) else args.results), **analyze(rows, args.min_participants)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "complete_participants": summary["complete_participants"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
