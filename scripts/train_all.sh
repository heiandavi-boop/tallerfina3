#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
VERSION="0.9.0-academic"
INPUT="data/processed/mendeley_core.csv"
ARTIFACT="artifacts/$VERSION"
READINESS="artifacts/data_readiness.json"

block_training() {
  local reason="$1"
  "$PY" scripts/data_readiness.py --blocking-error "$reason" || true
  echo "TRAINING BLOCKED: dataset did not pass readiness checks" >&2
  exit 1
}

echo "# PRUNIN AI Core Academic Pipeline"
echo "Python ....................."
"$PY" -c 'import sys; print(sys.version.split()[0]); sys.exit("Se requiere Python >=3.10") if sys.version_info < (3, 10) else None'
echo "Python ..................... OK"

echo "Dependencies ..............."
"$PY" -m pip check
"$PY" -c 'import importlib.util,sys; modules=("pandas","numpy","sklearn","lightgbm","yaml","openpyxl","requests","pyarrow","matplotlib"); missing=[name for name in modules if importlib.util.find_spec(name) is None]; print("Faltan dependencias: " + ", ".join(missing), file=sys.stderr) if missing else None; raise SystemExit(bool(missing))'
echo "Dependencies ............... OK"

echo "Mendeley metadata .........."
if [[ "${PRUNIN_INCLUDE_SQUAD:-0}" == "1" ]]; then
  if ! "$PY" scripts/download_datasets.py --include-squad; then
    block_training "Mendeley metadata/download/raw validation failed."
  fi
else
  if ! "$PY" scripts/download_datasets.py; then
    block_training "Mendeley metadata/download/raw validation failed."
  fi
fi
echo "Mendeley metadata .......... OK"
echo "Mendeley download .......... OK"
echo "Itemlet .................... optional; see downloader status"
echo "Collaboration .............. optional; see downloader status"
echo "SQuaD ...................... optional; see downloader status"

echo "Raw validation ............."
if ! "$PY" scripts/download_datasets.py --validate-only; then
  block_training "Mendeley raw files failed local validation."
fi
echo "Raw validation ............. OK"

echo "Dataset preparation ........"
if ! "$PY" scripts/prepare_datasets.py; then
  block_training "Mendeley preparation failed."
fi
if [[ ! -s "$INPUT" ]]; then
  block_training "Prepared Mendeley dataset is missing or empty."
fi
echo "Dataset preparation ........ OK"

echo "Data audit ................."
if ! "$PY" scripts/audit_dataset.py --input "$INPUT" \
  --output "artifacts/${VERSION}-audit.json"; then
  block_training "Mendeley data audit failed."
fi
echo "Data audit ................. OK"

echo "Data readiness ............."
if ! "$PY" scripts/data_readiness.py --input "$INPUT" \
  --audit "artifacts/${VERSION}-audit.json" --output "$READINESS"; then
  echo "TRAINING BLOCKED: dataset did not pass readiness checks" >&2
  exit 1
fi
if [[ ! -s "$READINESS" ]]; then
  block_training "Data readiness report is missing."
fi
echo "Data readiness ............. PASS"

echo "Leakage verification ......."
if ! "$PY" scripts/verify_split.py; then
  block_training "Project-level leakage verification failed."
fi
echo "Leakage verification ....... PASS"

"$PY" -c 'import json,sys; r=json.load(open(sys.argv[1],encoding="utf-8")); assert r.get("ready_for_training") is True and not r.get("blocking_errors") and r.get("leakage_check",{}).get("status")=="passed", "TRAINING BLOCKED: readiness is not PASS"' "$READINESS"

echo "Health training ............"
if ! "$PY" scripts/train_core.py --input "$INPUT" --version "$VERSION"; then
  block_training "Academic training failed."
fi
"$PY" -c 'import json,sys; m=json.load(open(sys.argv[1],encoding="utf-8")); r=json.load(open(sys.argv[2],encoding="utf-8")); targets=("health","delay_days","cost_overrun_ratio"); failed=[name for name in targets if m.get(name,{}).get("status")!="trained"]; final=m.get("final_status",{}); expected="derived" if r.get("final_status_mode")=="derived_from_health" else "trained"; failed += ["final_status"] if final.get("status")!=expected else []; print("Invalid model targets: " + ", ".join(failed),file=sys.stderr) if failed else None; raise SystemExit(bool(failed))' "$ARTIFACT/metrics.json" "$READINESS"
echo "Health training ............ OK"
if "$PY" -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))["final_status"]["status"]=="derived" else 1)' "$ARTIFACT/metrics.json"; then
  echo "Final Status ............... derived from Health"
else
  echo "Final Status training ...... OK"
fi
echo "Delay training ............. OK"
echo "Cost training .............. OK"

echo "Evaluation ................."
"$PY" scripts/evaluate_core.py --artifact "$ARTIFACT"
echo "Evaluation ................. OK"

echo "Temporal evaluation ........"
"$PY" scripts/evaluate_temporal.py
test -s "$ARTIFACT/temporal_evaluation.json"
test -s "$ARTIFACT/temporal_evaluation.csv"
echo "Temporal evaluation ........ OK"

echo "Feature importance ........."
for report in feature_importance_health.csv feature_importance_delay.csv feature_importance_cost.csv; do
  test -s "$ARTIFACT/$report"
done
if [[ "$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["final_status_mode"])' "$ARTIFACT/feature_manifest.json")" == "independent_model" ]]; then
  test -s "$ARTIFACT/feature_importance_final_status.csv"
fi
echo "Feature importance ......... OK"

echo "Report export .............."
"$PY" scripts/export_report.py --artifacts "$ARTIFACT" --output "reports/$VERSION"
for report in metrics.json data_readiness.json feature_manifest.json training_summary.json \
  experiment_summary.md health_confusion_matrix.csv health_classification_report.csv \
  temporal_evaluation.json temporal_evaluation.csv dataset_summary.json dataset_summary.md \
  split_summary.json reproducibility.json; do
  test -s "reports/$VERSION/$report"
done
echo "Report export .............. OK"

echo "Evaluation figures ........."
"$PY" scripts/generate_evaluation_plots.py --artifacts "$ARTIFACT" --reports "reports/$VERSION"
for figure in health_confusion_matrix.png health_metrics.png delay_actual_vs_predicted.png \
  cost_actual_vs_predicted.png temporal_health_macro_f1.png temporal_delay_mae.png \
  temporal_cost_mae.png feature_importance_health.png feature_importance_delay.png \
  feature_importance_cost.png; do
  test -s "reports/$VERSION/figures/$figure"
done
echo "Evaluation figures ......... OK"

echo "Artifacts .................."
for model in health delay_days cost_overrun_ratio; do
  test -s "$ARTIFACT/$model.joblib"
done
test -s "$ARTIFACT/metrics.json"
test -s "$ARTIFACT/feature_manifest.json"
test -s "$ARTIFACT/split_manifest.json"
test -s "$ARTIFACT/data_readiness.json"
echo "Artifacts .................. OK"

echo "Inference .................."
"$PY" scripts/predict_example.py --artifact "$ARTIFACT" --input "$INPUT"
echo "Inference .................. OK"

echo "Tests ......................"
PYTHONPATH=src "$PY" -m pytest -q
echo "Tests ...................... PASS"

echo "Playground ................."
PRUNIN_ARTIFACT_DIR="$ARTIFACT" ./scripts/preflight_demo.sh
echo "Playground ................. READY"
echo "PRUNIN AI CORE ACADEMIC READY"
echo "Model: $VERSION"
echo "Reports: reports/$VERSION/"
echo "Playground: READY"