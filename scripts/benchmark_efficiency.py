#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--genai-report", default="reports/genai/qwen3-8b-evaluation.json")
    parser.add_argument("--manual-seconds-per-case", type=float, default=None)
    parser.add_argument("--output", default="reports/genai/efficiency.json")
    args = parser.parse_args()

    report = json.loads(Path(args.genai_report).read_text(encoding="utf-8"))
    if report.get("status") != "complete":
        raise SystemExit("GenAI benchmark must be complete before efficiency can be measured.")
    metrics = report["metrics"]
    automated_seconds = metrics["latency_ms_median"] / 1000.0
    result = {
        "automated_median_seconds_per_case": automated_seconds,
        "automated_cases_per_hour": 3600.0 / automated_seconds if automated_seconds > 0 else None,
        "manual_baseline_seconds_per_case": args.manual_seconds_per_case,
        "manual_baseline_status": "measured_input" if args.manual_seconds_per_case is not None else "not_measured",
        "time_saved_percent": None,
        "throughput_gain_x": None,
        "note": "A manual baseline is never invented. Provide an observed manual time with --manual-seconds-per-case to quantify efficiency.",
    }
    if args.manual_seconds_per_case is not None and args.manual_seconds_per_case > 0:
        result["time_saved_percent"] = (1.0 - automated_seconds / args.manual_seconds_per_case) * 100.0
        result["throughput_gain_x"] = args.manual_seconds_per_case / automated_seconds if automated_seconds > 0 else None
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
