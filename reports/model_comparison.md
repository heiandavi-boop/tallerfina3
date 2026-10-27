# PRUNIN Academic vs PRUNIN Empirical

## Scope

Academic is `0.9.0-academic`, trained on the synthetic external Mendeley dataset. Empirical is `1.0.0-empirical`, trained only on observed DSLIB project records or deterministic values derived from them. The lines retain separate artifacts and manifests. Academic remains the default; Empirical is not activated automatically.

**These metrics describe performance within each model's own dataset, target, split, and feature domain. They are not a head-to-head comparison.** A common external benchmark has not been constructed.

| Dimension | PRUNIN Academic | PRUNIN Empirical |
|---|---|---|
| Data source | Mendeley v2, synthetic external | DSLIB / PSLIB v3.4, empirical project records |
| Source projects | 4,000; 72,549 snapshots | 231 published; 151 complete cases per trained target |
| Features | 5 numeric + 2 categorical | Planned duration (days), BAC |
| Health | TEST Macro F1 0.627576; balanced accuracy 0.682422; critical recall 0.568182 | Not trained; no consistent label |
| Delay | TEST MAE 27.710468 days vs median 27.850313 | TEST MAE 30.7097 days; median baseline has the same MAE; R² -0.0339 |
| Cost | TEST MAE 0.147158 BAC ratio; R² 0.991816 | TEST MAE 0.115703 BAC ratio; median baseline has the same MAE; R² -0.0317 |
| Early prediction | Evaluated at 20/40/60/80% with uneven coverage | Not available; only 13 leakage-cleared snapshots per target |
| GenAI | Qwen3 benchmark remains attached to Academic evidence | Not enabled; no model-specific grounded evaluation |
| Operational efficiency | Academic benchmark reported separately | 31 DSLIB TEST input rows; individual median 79.622 ms (389.34 projects/s), CSV batch 50.148 ms (618.17 projects/s), 3 repeats, 100% success |

The numeric values above must not be ranked across rows as if they were measured on the same projects. Empirical uses a smaller, observational and incomplete population; its current constant baseline does not outperform a simple median baseline. Academic offers higher sample volume and the existing full workflow, while Empirical offers greater ecological realism for its source population but limited predictive evidence.

The empirical operational measurement is stored in `reports/efficiency/empirical_operational_benchmark.json`. It is a local sequential API measurement on 31 held-out TEST feature rows with one warm-up per mode and three repetitions. It is not a production load/concurrency test, prediction-quality comparison, or human productivity estimate.

## Recommendation

There is no automatic global winner. Academic remains active by default for continuity and its complete existing workflow. Empirical is available for manual exploration when baseline duration and BAC are the only compatible inputs and the user explicitly accepts its DSLIB scope and weak test results. A real project domain alone is not enough to recommend Empirical as more accurate.

## Limitations

The datasets, target generation, project populations, feature sets, and splits differ. No shared external test, prospective evaluation, or human baseline exists. Empirical Health and early EVM prediction are unavailable. Neither line is validated for production decisions.