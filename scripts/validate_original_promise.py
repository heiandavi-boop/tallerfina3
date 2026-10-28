#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACADEMIC = ROOT / "reports" / "0.9.0-academic"
OUT = ROOT / "reports" / "promise_validation"
RISK = {"at_risk", "critical"}
TARGET = 0.75


def risk_alert_metrics(confusion_matrix, labels):
    index = {label: i for i, label in enumerate(labels)}
    required = {"healthy", "at_risk", "critical"}
    if not required.issubset(index):
        raise ValueError(f"Missing Health labels: {sorted(required - set(index))}")

    tp = fn = fp = tn = 0
    for actual in labels:
        for predicted in labels:
            value = int(confusion_matrix[index[actual]][index[predicted]])
            actual_risk = actual in RISK
            predicted_risk = predicted in RISK
            if actual_risk and predicted_risk:
                tp += value
            elif actual_risk:
                fn += value
            elif predicted_risk:
                fp += value
            else:
                tn += value

    recall = tp / (tp + fn)
    precision = tp / (tp + fp)
    f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "specificity": tn / (tn + fp),
        "false_negative_rate": fn / (tp + fn),
        "false_positive_rate": fp / (fp + tn),
        "accuracy": (tp + tn) / (tp + tn + fp + fn),
    }


def build_result():
    metrics = json.loads((ACADEMIC / "metrics.json").read_text(encoding="utf-8"))
    temporal = json.loads((ACADEMIC / "temporal_evaluation.json").read_text(encoding="utf-8"))
    final_health = metrics["health"]["project_level_metrics"]["test"]
    final = risk_alert_metrics(final_health["confusion_matrix"], final_health["labels"])
    final_risk_total = final["tp"] + final["fn"]

    rows = []
    for cutoff in temporal["cutoffs"]:
        current = risk_alert_metrics(cutoff["health"]["confusion_matrix"], cutoff["health"]["labels"])
        current.update({
            "cutoff_percent": int(round(float(cutoff["cutoff"]) * 100)),
            "eligible_projects": int(cutoff["test_project_count"]),
            "total_test_projects": int(cutoff["total_test_project_count"]),
            "project_coverage": float(cutoff["test_project_coverage_percent"]) / 100,
            "eligible_risk_projects": current["tp"] + current["fn"],
            "eligible_risk_coverage": (current["tp"] + current["fn"]) / final_risk_total,
            "full_cohort_detection_rate": current["tp"] / final_risk_total,
            "health_macro_f1": float(cutoff["health"]["macro_f1"]),
            "critical_recall": float(cutoff["health"]["per_class"]["critical"]["recall"]),
        })
        rows.append(current)

    final_row = dict(final)
    final_row.update({
        "cutoff_percent": 100,
        "cutoff_label": "Final",
        "eligible_projects": 600,
        "total_test_projects": 600,
        "project_coverage": 1.0,
        "eligible_risk_projects": final_risk_total,
        "eligible_risk_coverage": 1.0,
        "full_cohort_detection_rate": final["recall"],
        "health_macro_f1": float(final_health["macro_f1"]),
        "critical_recall": float(final_health["per_class"]["critical"]["recall"]),
    })
    rows.append(final_row)

    first = next(
        (row for row in rows if row["cutoff_percent"] < 100 and row["full_cohort_detection_rate"] >= TARGET),
        None,
    )

    return {
        "schema_version": "1.0",
        "source": {
            "model_version": "0.9.0-academic",
            "metrics": "reports/0.9.0-academic/metrics.json",
            "temporal_evaluation": "reports/0.9.0-academic/temporal_evaluation.json",
            "evaluation_split": "TEST",
            "test_projects": 600,
        },
        "promise": {
            "statement": "Detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo.",
            "risk_alert_definition": "At Risk OR Critical => Risk Alert; Healthy => No Risk Alert",
            "target_full_cohort_detection_rate": TARGET,
            "model_changed": False,
            "threshold_changed": False,
        },
        "final": {
            "final_risk_projects": final_risk_total,
            "confusion_binary": {key: final[key] for key in ("tp", "fn", "fp", "tn")},
            "risk_alert_recall": final["recall"],
            "risk_alert_precision": final["precision"],
            "risk_alert_f1": final["f1"],
            "specificity": final["specificity"],
            "false_negative_rate": final["false_negative_rate"],
            "false_positive_rate": final["false_positive_rate"],
            "binary_accuracy": final["accuracy"],
            "exact_critical_recall": float(final_health["per_class"]["critical"]["recall"]),
            "health_macro_f1": float(final_health["macro_f1"]),
        },
        "temporal": rows,
        "first_precompletion_cutoff_reaching_target": None if first is None else {
            "cutoff_percent": first["cutoff_percent"],
            "full_cohort_detection_rate": first["full_cohort_detection_rate"],
            "project_coverage": first["project_coverage"],
            "eligible_projects": first["eligible_projects"],
            "eligible_risk_projects": first["eligible_risk_projects"],
            "eligible_risk_coverage": first["eligible_risk_coverage"],
            "risk_alert_recall_among_eligible": first["recall"],
            "risk_alert_precision": first["precision"],
        },
        "verdict": (
            "PROMESA PRINCIPAL DEMOSTRADA EN EL ENTORNO EXPERIMENTAL"
            if first
            else "PROMESA PARCIALMENTE DEMOSTRADA"
        ),
        "caveats": [
            "La evidencia corresponde a un dataset sintético externo; no acredita generalización empresarial.",
            "La tasa de detección de cohorte completa cuenta como no detectados los proyectos sin snapshot elegible en cada corte.",
            "El recall exacto de la clase Critical permanece separado y es menor que el KPI binario de alerta.",
            "Delay mantiene mejora marginal frente a baseline; Cost requiere interpretar el caveat estructural EVM/CPI.",
            "No se modificaron modelos, labels, features, thresholds ni TEST para obtener este KPI.",
        ],
    }


def csv_text(result):
    fields = [
        "cutoff_percent", "eligible_projects", "total_test_projects", "project_coverage_percent",
        "eligible_risk_projects", "eligible_risk_coverage_percent", "tp", "fn", "fp", "tn",
        "risk_alert_recall_percent", "risk_alert_precision_percent", "risk_alert_f1_percent",
        "specificity_percent", "false_negative_rate_percent", "false_positive_rate_percent",
        "full_cohort_detection_rate_percent", "health_macro_f1", "critical_recall",
    ]
    lines = [",".join(fields)]
    for row in result["temporal"]:
        values = [
            row["cutoff_percent"], row["eligible_projects"], row["total_test_projects"],
            f'{row["project_coverage"] * 100:.6f}', row["eligible_risk_projects"],
            f'{row["eligible_risk_coverage"] * 100:.6f}', row["tp"], row["fn"], row["fp"], row["tn"],
            f'{row["recall"] * 100:.6f}', f'{row["precision"] * 100:.6f}', f'{row["f1"] * 100:.6f}',
            f'{row["specificity"] * 100:.6f}', f'{row["false_negative_rate"] * 100:.6f}',
            f'{row["false_positive_rate"] * 100:.6f}', f'{row["full_cohort_detection_rate"] * 100:.6f}',
            f'{row["health_macro_f1"]:.12f}', f'{row["critical_recall"]:.12f}',
        ]
        lines.append(",".join(map(str, values)))
    return "\n".join(lines) + "\n"


def markdown_text(result):
    first = result["first_precompletion_cutoff_reaching_target"]
    final = result["final"]
    pct = lambda value: f"{value * 100:.2f}%"
    return f"""# Validación de la promesa original — PRUNIN AI Core

La promesa se operacionaliza como **detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo**. Risk Alert agrupa At Risk + Critical; Healthy queda como No Alert. No se modifica el modelo.

## Resultado

- Risk Alert Recall final: **{pct(final['risk_alert_recall'])}**
- Risk Alert Precision final: **{pct(final['risk_alert_precision'])}**
- Risk Alert F1 final: **{pct(final['risk_alert_f1'])}**
- Critical Recall exacto: **{pct(final['exact_critical_recall'])}**
- Primer corte pre-cierre que supera 75 % sobre toda la cohorte riesgosa: **{first['cutoff_percent']} %**
- Detección de toda la cohorte riesgosa en ese corte: **{pct(first['full_cohort_detection_rate'])}**
- Cobertura TEST en ese corte: **{pct(first['project_coverage'])}**

La métrica de cohorte completa usa como denominador fijo los {final['final_risk_projects']} proyectos TEST que finalmente son At Risk/Critical; un proyecto sin snapshot elegible todavía cuenta como no detectado.

**Veredicto:** {result['verdict']}.
"""


def outputs(result):
    final = result["final"]
    cm = (
        "actual,pred_no_alert,pred_risk_alert\n"
        f"healthy,{final['confusion_binary']['tn']},{final['confusion_binary']['fp']}\n"
        f"at_risk_or_critical,{final['confusion_binary']['fn']},{final['confusion_binary']['tp']}\n"
    )
    return {
        OUT / "risk_alert_metrics.json": json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        OUT / "temporal_risk_alert_metrics.csv": csv_text(result),
        OUT / "risk_alert_confusion_matrix.csv": cm,
        OUT / "promise_validation_report.md": markdown_text(result),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_result()
    generated = outputs(result)

    if args.check:
        mismatches = [
            str(path.relative_to(ROOT))
            for path, expected in generated.items()
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        if mismatches:
            raise SystemExit("Promise validation outputs are stale: " + ", ".join(mismatches))
        print("PROMISE VALIDATION: OK")
        first = result["first_precompletion_cutoff_reaching_target"]
        print(f"{first['cutoff_percent']}% full-cohort detection={first['full_cohort_detection_rate']:.6f}")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    for path, content in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print("PROMISE VALIDATION WRITTEN")
    print(json.dumps(result["first_precompletion_cutoff_reaching_target"], indent=2))


if __name__ == "__main__":
    main()
