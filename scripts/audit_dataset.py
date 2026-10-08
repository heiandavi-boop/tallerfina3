from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from prunin_ai.data.audit import audit_dataframe, save_audit

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", default=None)
ap.add_argument("--min-rows", type=int, default=0)
ap.add_argument("--min-projects", type=int, default=0)
ap.add_argument("--min-target-coverage", type=float, default=0.0)
args = ap.parse_args()
df = pd.read_csv(args.input, low_memory=False)
report = audit_dataframe(df)
print(json.dumps(report, indent=2, ensure_ascii=False))
if args.output:
    save_audit(report, args.output)
weak_targets = {
    name: coverage for name, coverage in report["target_coverage"].items()
    if coverage < args.min_target_coverage
}
if report["rows"] < args.min_rows or (report["projects"] or 0) < args.min_projects or weak_targets:
    raise SystemExit(
        f"Calidad insuficiente: rows={report['rows']} (min {args.min_rows}), "
        f"projects={report['projects']} (min {args.min_projects}), "
        f"target_coverage={weak_targets} (min {args.min_target_coverage})"
    )
