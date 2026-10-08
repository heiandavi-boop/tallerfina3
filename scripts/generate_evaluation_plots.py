#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _confusion_matrix(metrics: dict, output: Path) -> None:
    health = metrics.get("health", {}).get("test", {})
    matrix = np.asarray(health.get("confusion_matrix", []), dtype=int)
    labels = health.get("labels", [])
    if not matrix.size or not labels:
        return
    fig, axis = plt.subplots(figsize=(5.5, 4.5), constrained_layout=True)
    image = axis.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=axis, label="Projects")
    axis.set(xticks=range(len(labels)), yticks=range(len(labels)),
             xticklabels=labels, yticklabels=labels,
             xlabel="Predicted", ylabel="Actual", title="Health · Test confusion matrix")
    plt.setp(axis.get_xticklabels(), rotation=25, ha="right")
    midpoint = matrix.max() / 2 if matrix.size else 0
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center",
                      color="white" if matrix[row, column] > midpoint else "black")
    fig.savefig(output, dpi=120)
    plt.close(fig)


def _health_metrics(metrics: dict, output: Path) -> None:
    health = metrics.get("health", {}).get("test", {})
    names = ("balanced_accuracy", "macro_f1", "weighted_f1")
    values = [health.get(name) for name in names]
    if not all(value is not None for value in values):
        return
    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    bars = axis.bar(names, values, color=("#2878B5", "#55A868", "#C44E52"))
    axis.set(ylim=(0, 1), ylabel="Score", title="Health · Test classification metrics")
    axis.bar_label(bars, fmt="%.3f", padding=3)
    fig.savefig(output, dpi=120)
    plt.close(fig)


def _actual_predicted(predictions: pd.DataFrame, actual: str, predicted: str,
                      title: str, output: Path) -> None:
    if actual not in predictions or predicted not in predictions:
        return
    values = predictions[[actual, predicted]].dropna()
    if values.empty:
        return
    x = values[actual].astype(float).to_numpy()
    y = values[predicted].astype(float).to_numpy()
    low = float(min(x.min(), y.min()))
    high = float(max(x.max(), y.max()))
    fig, axis = plt.subplots(figsize=(5.5, 4.5), constrained_layout=True)
    axis.scatter(x, y, s=12, alpha=0.45, edgecolors="none")
    axis.plot([low, high], [low, high], color="#C44E52", linestyle="--", linewidth=1)
    axis.set(xlabel="Actual", ylabel="Predicted", title=title)
    fig.savefig(output, dpi=120)
    plt.close(fig)


def _temporal_plot(report: dict, target: str, metric: str, output: Path, title: str) -> None:
    cutoffs = report.get("cutoffs", [])
    values = [row.get(target, {}).get(metric) if row.get(target) else None for row in cutoffs]
    pairs = [(row["cutoff"] * 100, value) for row, value in zip(cutoffs, values, strict=True) if value is not None]
    if not pairs:
        return
    x, y = zip(*pairs, strict=True)
    fig, axis = plt.subplots(figsize=(5.5, 4), constrained_layout=True)
    axis.plot(x, y, marker="o", linewidth=2)
    axis.set(xticks=x, xlabel="Project progress cutoff (%)", ylabel=metric, title=title)
    axis.grid(axis="y", alpha=0.25)
    fig.savefig(output, dpi=120)
    plt.close(fig)


def _importance_plot(report_dir: Path, model: str, output: Path) -> None:
    csv_path = report_dir / f"feature_importance_{model}.csv"
    if not csv_path.is_file():
        return
    importance = pd.read_csv(csv_path).head(15).sort_values("gain")
    if importance.empty:
        return
    fig, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    axis.barh(importance["feature"], importance["gain"], color="#2878B5")
    axis.set(xlabel="LightGBM gain", title=f"Global feature importance · {model}")
    fig.savefig(output, dpi=120)
    plt.close(fig)


def generate_plots(artifact_dir: Path, report_dir: Path) -> list[Path]:
    figures = report_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((report_dir / "metrics.json").read_text(encoding="utf-8"))
    temporal = json.loads((report_dir / "temporal_evaluation.json").read_text(encoding="utf-8"))
    prediction_path = artifact_dir / "test_project_predictions.csv"
    predictions = pd.read_csv(prediction_path) if prediction_path.is_file() else pd.DataFrame()
    _confusion_matrix(metrics, figures / "health_confusion_matrix.png")
    _health_metrics(metrics, figures / "health_metrics.png")
    _actual_predicted(predictions, "actual_delay_days", "predicted_delay_days",
                      "Delay · One latest test snapshot per project", figures / "delay_actual_vs_predicted.png")
    _actual_predicted(predictions, "actual_cost_overrun_ratio", "predicted_cost_overrun_ratio",
                      "Cost overrun ratio · One latest test snapshot per project", figures / "cost_actual_vs_predicted.png")
    _temporal_plot(temporal, "health", "macro_f1", figures / "temporal_health_macro_f1.png",
                   "Early Health · Test macro F1")
    _temporal_plot(temporal, "delay_days", "mae", figures / "temporal_delay_mae.png",
                   "Early Delay · Test MAE")
    _temporal_plot(temporal, "cost_overrun_ratio", "mae", figures / "temporal_cost_mae.png",
                   "Early Cost Overrun · Test MAE")
    _importance_plot(report_dir, "health", figures / "feature_importance_health.png")
    _importance_plot(report_dir, "delay", figures / "feature_importance_delay.png")
    _importance_plot(report_dir, "cost", figures / "feature_importance_cost.png")
    return sorted(path for path in figures.glob("*.png") if path.is_file())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="artifacts/0.9.0-academic")
    parser.add_argument("--reports", default="reports/0.9.0-academic")
    args = parser.parse_args()
    plots = generate_plots(ROOT / args.artifacts, ROOT / args.reports)
    print(f"Generated {len(plots)} figures in {args.reports}/figures")