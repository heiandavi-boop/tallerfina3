#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
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
    test = target_metrics.get("test") or {}
    labels = test.get("labels", [])
    matrix = test.get("confusion_matrix", [])
    if labels and matrix:
        pd.DataFrame(matrix, index=labels, columns=labels).rename_axis("actual").to_csv(
            report_dir / f"{target}_confusion_matrix.csv"
        )
    report_rows = []
    for split_name in ("validation", "test"):
        split = target_metrics.get(split_name) or {}
        for label, values in split.get("per_class", {}).items():
            report_rows.append({"split": split_name, "class": label, **values})
    if report_rows:
        pd.DataFrame(report_rows).to_csv(
            report_dir / f"{target}_classification_report.csv", index=False
        )


def _dataset_summary(readiness: dict, split_manifest: dict, metrics: dict) -> dict:
    feature_manifest = metrics.get("manifest", {})
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
    lines.extend(["", "## Target coverage", "", "| Target | Non-missing |", "|---|---:|"])
    lines.extend(f"| {name} | {count} |" for name, count in summary["target_coverage"].items())
    lines.extend(["", "## Features", "", "Used: " + ", ".join(summary["features_used"]),
                  "", "Missing from this dataset: " + ", ".join(summary["missing_features"]), ""])
    return "\n".join(lines)


def _experiment_markdown(metrics: dict, feature_manifest: dict, readiness: dict,
                         reproducibility: dict, temporal: dict) -> str:
    dataset = {
        "projects": readiness.get("project_count"),
        "snapshots": readiness.get("snapshot_count"),
    }
    split_counts = reproducibility.get("split_project_counts", {})
    final_mode = feature_manifest.get("final_status_mode", "independent_model")
    lines = [
        "# PRUNIN AI Core 0.9.0-academic", "", "## Dataset", "Mendeley v2",
        "", "## Tipo de datos", "Sintético externo (CC BY 4.0). No existe validación productiva todavía.",
        "", "## Proyectos", str(dataset["projects"]), "", "## Snapshots", str(dataset["snapshots"]),
        "", "## Split", f"70/15/15 por project_id: {split_counts}",
        "", "## Modelos", "LightGBM: Health, Delay y Cost Overrun.",
    ]
    if final_mode == "derived_from_health":
        lines.append("Final Status: derived business status from Health; no independent classifier was trained.")
    else:
        lines.append("Final Status: independent classifier.")
    lines.extend(["", "## Features", ", ".join(feature_manifest.get("numeric_features", []) + feature_manifest.get("categorical_features", [])),
                  "", "## Variables excluidas", ", ".join(feature_manifest.get("target_columns_excluded", [])),
                  "", "## Métricas", "", "| Target | Unit | Test summary |", "|---|---|---|"])
    for target in ("health", "final_status", "delay_days", "cost_overrun_ratio"):
        result = metrics.get(target, {})
        test = result.get("test") or {}
        if result.get("status") == "derived":
            lines.append(f"| {target} | derived | {result.get('mapping')} |")
        elif result.get("status") == "trained":
            summary = {key: test.get(key) for key in ("balanced_accuracy", "macro_f1", "mae", "mae_percentage_points", "rmse", "r2") if key in test}
            lines.append(f"| {target} | {'classification' if 'accuracy' in test else 'original target unit'} | `{json.dumps(summary, ensure_ascii=False)}` |")
        else:
            lines.append(f"| {target} | not available | {result.get('status', 'not trained')} |")
    lines.extend(["", "## Evaluación temprana", "", "| Cutoff | Test projects | Health Macro-F1 | Delay MAE (days) | Cost MAE (ratio / pp) |",
                  "|---:|---:|---:|---:|---:|"])
    for item in temporal.get("cutoffs", []):
        health = item.get("health") or {}
        delay = item.get("delay_days") or {}
        cost = item.get("cost_overrun_ratio") or {}
        cost_mae = cost.get("mae")
        cost_points = cost.get("mae_percentage_points")
        cost_text = f"{cost_mae} / {cost_points}" if cost_mae is not None else "not available"
        lines.append(f"| {item['cutoff']:.0%} | {item.get('test_project_count', 0)} | {health.get('macro_f1')} | {delay.get('mae')} | {cost_text} |")
    lines.extend(["", "## Riesgos metodológicos", *[f"- {item}" for item in readiness.get("leakage_risks", [])],
                  "- SPI/CPI/progress tardíos pueden estar cerca del outcome; evaluar prospectivamente requiere un corte temporal con datos reales.",
                  "- Los resultados por snapshot pueden dar más peso a proyectos con más observaciones; también se presentan métricas por proyecto.",
                  "", "## Limitaciones", "Mendeley es sintético. Los datasets externos no se mezclan ni se unen con Mendeley. Team Health continúa como señal operativa heurística.",
                  "", "## Reproducibilidad", f"Random seed: {reproducibility.get('random_seed')}",
                  f"Python: {reproducibility.get('python_version')}", f"Commit: {reproducibility.get('git_commit_sha')}",
                  f"Timestamp UTC: {reproducibility.get('timestamp_utc')}", "", "## Commit", str(reproducibility.get("git_commit_sha")), ""])
    return "\n".join(lines)


def export_report(artifact_dir: Path, report_dir: Path) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    metrics = _copy_json(artifact_dir, report_dir, "metrics.json")
    readiness = _copy_json(artifact_dir, report_dir, "data_readiness.json")
    feature_manifest = _copy_json(artifact_dir, report_dir, "feature_manifest.json")
    split_manifest = _read_json(artifact_dir / "split_manifest.json")
    reproducibility = _copy_json(artifact_dir, report_dir, "reproducibility.json")
    temporal = _copy_json(artifact_dir, report_dir, "temporal_evaluation.json")
    shutil.copy2(artifact_dir / "temporal_evaluation.csv", report_dir / "temporal_evaluation.csv")
    _write_json(metrics, report_dir / "metrics.json")
    training_summary = {
        "artifact_version": "0.9.0-academic",
        "targets": metrics,
        "final_status_mode": feature_manifest.get("final_status_mode"),
        "models": {name: value.get("status") for name, value in metrics.items()},
        "evaluation_split": "project-level 70/15/15; metrics expose row- and project-level results separately",
    }
    _write_json(training_summary, report_dir / "training_summary.json")
    for target in ("health", "final_status"):
        _write_classification_tables(metrics, report_dir, target)
    dataset_summary = _dataset_summary(readiness, split_manifest, metrics)
    _write_json(dataset_summary, report_dir / "dataset_summary.json")
    (report_dir / "dataset_summary.md").write_text(_dataset_markdown(dataset_summary), encoding="utf-8")
    split_summary = {
        "unit": "unique project_id",
        "project_counts": {name: len(ids) for name, ids in split_manifest.items()},
        "project_ids": {name: ids for name, ids in split_manifest.items()},
    }
    _write_json(split_summary, report_dir / "split_summary.json")
    (report_dir / "experiment_summary.md").write_text(
        _experiment_markdown(metrics, feature_manifest, readiness, reproducibility, temporal),
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