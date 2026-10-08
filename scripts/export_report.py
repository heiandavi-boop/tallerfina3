#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_json(artifact_dir: Path, report_dir: Path, name: str) -> dict:
    value = _read_json(artifact_dir / name)
    _write_json(value, report_dir / name)
    return value


def _write_classification_tables(metrics: dict, report_dir: Path, target: str) -> None:
    target_metrics = metrics.get(target, {})
    if target_metrics.get("status") != "trained":
        return
    project = target_metrics.get("project_level_metrics", {})
    project_test = project.get("test") or {}
    labels = project_test.get("labels", [])
    matrix = project_test.get("confusion_matrix", [])
    if labels and matrix:
        pd.DataFrame(matrix, index=labels, columns=labels).rename_axis("actual").to_csv(
            report_dir / f"{target}_confusion_matrix.csv"
        )
    snapshot_test = target_metrics.get("test") or {}
    snapshot_labels = snapshot_test.get("labels", [])
    snapshot_matrix = snapshot_test.get("confusion_matrix", [])
    if snapshot_labels and snapshot_matrix:
        pd.DataFrame(snapshot_matrix, index=snapshot_labels, columns=snapshot_labels).rename_axis("actual").to_csv(
            report_dir / f"{target}_snapshot_confusion_matrix.csv"
        )
    report_rows = []
    for unit, splits in (
        ("project_level", project),
        ("snapshot_level", target_metrics.get("row_level_metrics", {})),
    ):
        for split_name in ("validation", "test"):
            split = splits.get(split_name) or {}
            for label, values in split.get("per_class", {}).items():
                report_rows.append({"evaluation_unit": unit, "split": split_name, "class": label, **values})
    if report_rows:
        pd.DataFrame(report_rows).to_csv(report_dir / f"{target}_classification_report.csv", index=False)


def _dataset_summary(readiness: dict, split_manifest: dict, metrics: dict, feature_manifest: dict) -> dict:
    split_project_counts = {name: len(ids) for name, ids in split_manifest.items()}
    split_snapshot_counts = {
        name: metrics.get("health", {}).get(f"{name}_rows")
        for name in ("train", "validation", "test")
    }
    target_coverage = {}
    for name in ("health", "final_status", "delay_days", "cost_overrun_ratio"):
        target = readiness.get("target_distribution", {}).get(name, {})
        if "count" in target:
            count = target["count"]
        else:
            count = sum(value for value in target.values() if isinstance(value, (int, float)))
        target_coverage[name] = count / max(int(readiness.get("snapshot_count") or 0), 1)
    return {
        "dataset": "Simulated project risk and earned-value dataset",
        "source": "Mendeley Data",
        "doi": "10.17632/2p5sz57wh2.2",
        "version": 2,
        "synthetic": True,
        "project_count": readiness.get("project_count"),
        "snapshot_count": readiness.get("snapshot_count"),
        "train_projects": split_project_counts.get("train"),
        "validation_projects": split_project_counts.get("validation"),
        "test_projects": split_project_counts.get("test"),
        "train_snapshots": split_snapshot_counts.get("train"),
        "validation_snapshots": split_snapshot_counts.get("validation"),
        "test_snapshots": split_snapshot_counts.get("test"),
        "health_distribution": readiness.get("health_distribution", {}),
        "final_status_distribution": readiness.get("final_status_distribution", {}),
        "target_coverage": target_coverage,
        "feature_coverage": readiness.get("feature_coverage", {}),
        "missing_features": readiness.get("missing_features", []),
        "features_used": feature_manifest.get("numeric_features", []) + feature_manifest.get("categorical_features", []),
        "data_sources_not_joined": readiness.get("real_sources", []),
    }


def _dataset_markdown(summary: dict) -> str:
    distribution = summary["health_distribution"]
    lines = [
        "# Academic dataset summary", "", "- Source: Mendeley Data v2",
        "- DOI: 10.17632/2p5sz57wh2.2", "- Type: synthetic external dataset",
        f"- Projects: {summary['project_count']}", f"- Snapshots: {summary['snapshot_count']}",
        f"- Split projects: train {summary['train_projects']}, validation {summary['validation_projects']}, test {summary['test_projects']}",
        f"- Split snapshots: train {summary['train_snapshots']}, validation {summary['validation_snapshots']}, test {summary['test_snapshots']}",
        "", "## Health distribution", "", "| Class | Snapshots |", "|---|---:|",
    ]
    lines.extend(f"| {name} | {count} |" for name, count in distribution.items())
    lines.extend(["", "## Target coverage", "", "| Target | Coverage |", "|---|---:|"])
    lines.extend(f"| {name} | {value:.1%} |" for name, value in summary["target_coverage"].items())
    lines.extend(["", "## Features", "", "Used: " + ", ".join(summary["features_used"]),
                  "", "Missing from this dataset: " + ", ".join(summary["missing_features"]), ""])
    return "\n".join(lines)


def _experiment_markdown(metrics: dict, feature_manifest: dict, readiness: dict,
                         reproducibility: dict, temporal: dict, baselines: dict,
                         delay_experiment: dict | None) -> str:
    split_counts = reproducibility.get("split_project_counts", {})
    final_mode = feature_manifest.get("final_status_mode", "independent_model")
    features = feature_manifest.get("numeric_features", []) + feature_manifest.get("categorical_features", [])
    lines = [
        "# PRUNIN AI Core 0.9.0-academic", "",
        "## Problema", "Early risk estimation for project Health, Delay and Cost Overrun.",
        "", "## Dataset", "Mendeley v2 — DOI 10.17632/2p5sz57wh2.2",
        "", "## Tipo de datos", "Synthetic external dataset (CC BY 4.0). No production validation exists.",
        "", "## Proyectos", str(readiness.get("project_count")),
        "", "## Snapshots", str(readiness.get("snapshot_count")),
        "", "## Split", f"70/15/15 grouped by project_id: {split_counts}",
        "", "## Leakage prevention", "Direct targets/outcomes are excluded from the feature whitelist; projects are disjoint across train/validation/test.",
        "", "## Modelos", "LightGBM: Health, Delay and Cost Overrun.",
    ]
    if final_mode == "derived_from_health":
        lines.append("Final Status: derived business status from Health; no independent classifier was trained.")
    else:
        lines.append("Final Status: independently trained classifier.")
    lines.extend([
        "", "## Features utilizadas", ", ".join(features),
        "", "## Variables excluidas", ", ".join(feature_manifest.get("target_columns_excluded", [])),
        "", "## Project-level evaluation", "One latest available snapshot per project within each split.",
        "", "| Target | Test project metrics |", "|---|---|"])
    for target in ("health", "delay_days", "cost_overrun_ratio"):
        project_test = metrics.get(target, {}).get("project_level_metrics", {}).get("test") or {}
        keys = ("accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "mae", "mae_percentage_points", "rmse", "r2")
        summary = {key: project_test[key] for key in keys if key in project_test}
        if target == "health":
            per_class = project_test.get("per_class", {})
            summary["critical_recall"] = per_class.get("critical", {}).get("recall")
            summary["critical_support"] = per_class.get("critical", {}).get("support")
            summary["per_class_recall"] = {name: values.get("recall") for name, values in per_class.items()}
        lines.append(f"| {target} | `{json.dumps(summary, ensure_ascii=False)}` |")
    lines.append("| final_status | Derived business status from Health; no separate ML metric. |")
    lines.extend(["", "## Snapshot-level evaluation", "Each available snapshot is one row; projects with more snapshots can carry more weight.",
                  "", "| Target | Test snapshot metrics |", "|---|---|"])
    for target in ("health", "delay_days", "cost_overrun_ratio"):
        snapshot_test = metrics.get(target, {}).get("row_level_metrics", {}).get("test") or {}
        keys = ("accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "mae", "mae_percentage_points", "rmse", "r2")
        summary = {key: snapshot_test[key] for key in keys if key in snapshot_test}
        if target == "health":
            per_class = snapshot_test.get("per_class", {})
            summary["critical_recall"] = per_class.get("critical", {}).get("recall")
            summary["critical_support"] = per_class.get("critical", {}).get("support")
        lines.append(f"| {target} | `{json.dumps(summary, ensure_ascii=False)}` |")
    lines.extend(["", "## Baselines", "Train-only majority-class/median baselines; TEST is descriptive and not used for model selection.",
                  "", "| Target | Baseline | Project-level TEST comparison |", "|---|---|---|"])
    for target, baseline in baselines.items():
        comparison = baseline.get("project_level_test_improvement", {})
        lines.append(f"| {target} | {baseline.get('method')}: {baseline.get('train_statistic')} | {comparison.get('metric')} improvement={comparison.get('model_minus_baseline')} |")
    lines.extend(["", "## Evaluación temporal", "TEST only; one snapshot per project with maximum true_progress <= cutoff.",
                  "", "| Cutoff | Available / TEST projects | Coverage | Max selected progress | Health Macro-F1 | Critical recall | Delay MAE | Delay RMSE | Delay R² | Cost MAE ratio | Cost MAE pp | Cost R² |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for item in temporal.get("cutoffs", []):
        health = item.get("health") or {}
        delay = item.get("delay_days") or {}
        cost = item.get("cost_overrun_ratio") or {}
        critical_recall = health.get("per_class", {}).get("critical", {}).get("recall")
        coverage = item.get("test_project_coverage_percent")
        coverage_text = f"{coverage:.1f}%" if coverage is not None else "N/A"
        lines.append(
            f"| {item['cutoff']:.0%} | {item.get('test_project_count', 0)} / {item.get('total_test_project_count', 0)} | "
            f"{coverage_text} | {item.get('max_selected_progress')} | {health.get('macro_f1')} | {critical_recall} | "
            f"{delay.get('mae')} | {delay.get('rmse')} | {delay.get('r2')} | {cost.get('mae')} | "
            f"{cost.get('mae_percentage_points')} | {cost.get('r2')} |"
        )
    lines.extend(["", "## Delay experiment", "", "Selection uses TRAIN fit and VALIDATION metrics; TEST is only evaluated after freezing the selection."])
    if delay_experiment:
        decision = delay_experiment.get("decision", {})
        test_eval = delay_experiment.get("test_evaluation_after_freeze", {})
        selected_metrics = test_eval.get("metrics", {})
        lines.extend([
            f"- Selection: {decision.get('selection_status')}",
            f"- Selected candidate: {decision.get('selected_candidate')}",
            f"- TEST after freeze: MAE {selected_metrics.get('mae')}, RMSE {selected_metrics.get('rmse')}, R² {selected_metrics.get('r2')}.",
            f"- Candidate vs incumbent TEST (descriptive only): {test_eval.get('candidate_vs_incumbent_test')}.",
            f"- Promoted automatically: {delay_experiment.get('promoted_to_delay_days_joblib', False)}",
        ])
    else:
        lines.append("- Experiment report not present.")
    lines.extend([
        "", "## Feature importance", "LightGBM native gain/split; this is predictive sensitivity, not causality.",
        "", "## Riesgos metodológicos", *[f"- {item}" for item in readiness.get("leakage_risks", [])],
        "- CPI has a structural relation with final cost in synthetic EVM generation; high late-stage Cost R² is internal synthetic performance, not production evidence.",
        "- Critical class has limited project-level support and lower recall/F1 than the majority class.",
        "", "## Limitaciones", "No real PRUNIN validation exists. External projects are not joined to Mendeley. Team Health remains an observable operational heuristic; fusion weights are not empirically calibrated.",
        "", "## Reproducibilidad", f"Python: {reproducibility.get('python_version')}",
        f"Random seed: {reproducibility.get('random_seed')}", f"Dataset SHA256: {reproducibility.get('dataset_sha256', {}).get('processed')}",
        f"Timestamp UTC: {reproducibility.get('timestamp_utc')}", f"Commit: {reproducibility.get('git_commit_sha')}",
        "", "## Qué no se puede concluir", "These synthetic results do not establish causal effects, operational validity, or expected performance on live PRUNIN projects.",
        "", "## Qué falta para producción", "Prospective evaluation and calibration on real PRUNIN projects, plus external validation of temporal cutoffs and operational fusion.", "",
    ])
    return "\n".join(lines)


def export_report(artifact_dir: Path, report_dir: Path) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    metrics = _copy_json(artifact_dir, report_dir, "metrics.json")
    readiness = _copy_json(artifact_dir, report_dir, "data_readiness.json")
    feature_manifest = _copy_json(artifact_dir, report_dir, "feature_manifest.json")
    split_manifest = _read_json(artifact_dir / "split_manifest.json")
    reproducibility = _copy_json(artifact_dir, report_dir, "reproducibility.json")
    temporal = _copy_json(artifact_dir, report_dir, "temporal_evaluation.json")
    baselines = _copy_json(artifact_dir, report_dir, "baselines.json")
    shutil.copy2(artifact_dir / "temporal_evaluation.csv", report_dir / "temporal_evaluation.csv")
    shutil.copy2(artifact_dir / "baseline_comparison.csv", report_dir / "baseline_comparison.csv")
    _write_json(metrics, report_dir / "metrics.json")
    training_summary = {
        "artifact_version": "0.9.0-academic",
        "targets": metrics,
        "final_status_mode": feature_manifest.get("final_status_mode"),
        "models": {name: value.get("status") for name, value in metrics.items()},
        "evaluation_split": "project-level 70/15/15; metrics expose row- and project-level results separately",
        "baselines": baselines,
    }
    _write_json(training_summary, report_dir / "training_summary.json")
    for target in ("health", "final_status"):
        _write_classification_tables(metrics, report_dir, target)
    dataset_summary = _dataset_summary(readiness, split_manifest, metrics, feature_manifest)
    _write_json(dataset_summary, report_dir / "dataset_summary.json")
    (report_dir / "dataset_summary.md").write_text(_dataset_markdown(dataset_summary), encoding="utf-8")
    split_summary = {
        "unit": "unique project_id",
        "project_counts": {name: len(ids) for name, ids in split_manifest.items()},
        "project_ids": {name: ids for name, ids in split_manifest.items()},
    }
    _write_json(split_summary, report_dir / "split_summary.json")
    delay_experiment_path = ROOT / "reports/experiments/delay/comparison.json"
    delay_experiment = _read_json(delay_experiment_path) if delay_experiment_path.is_file() else None
    if delay_experiment_path.is_file():
        delay_report_dir = report_dir.parent / "experiments/delay"
        delay_report_dir.mkdir(parents=True, exist_ok=True)
        for name in ("comparison.json", "comparison.csv", "README.md"):
            source = delay_experiment_path.parent / name
            destination = delay_report_dir / name
            if source.is_file() and source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
    (report_dir / "experiment_summary.md").write_text(
        _experiment_markdown(metrics, feature_manifest, readiness, reproducibility, temporal, baselines, delay_experiment),
        encoding="utf-8",
    )
    for importance_name in (
        "feature_importance_health.csv", "feature_importance_delay.csv",
        "feature_importance_cost.csv", "feature_importance_final_status.csv",
    ):
        source = artifact_dir / importance_name
        if source.is_file():
            shutil.copy2(source, report_dir / importance_name)
    return sorted(path for path in report_dir.rglob("*") if path.is_file())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="artifacts/0.9.0-academic")
    parser.add_argument("--output", default="reports/0.9.0-academic")
    args = parser.parse_args()
    try:
        generated = export_report(ROOT / args.artifacts, ROOT / args.output)
        print(f"Exported {len(generated)} report files to {args.output}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Report export failed: {error}", file=sys.stderr)
        raise SystemExit(1)