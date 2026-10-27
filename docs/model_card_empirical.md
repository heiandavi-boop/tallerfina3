# PRUNIN Empirical Model Card

## Status and intended use

Version `1.0.0-empirical` is an experimental, locally trained baseline model. It is not production-ready and must not be presented as more accurate than PRUNIN Academic. It supports exploratory estimates from baseline duration and budget for projects similar to the DSLIB sample. A human must review any use; the model does not support causal conclusions or high-impact decisions.

## Data and population

Source: DSLIB / PSLIB release v3.4, an empirical collection published by Ghent University's Operations Research & Scheduling group. The raw archive contains 231 projects; 229 have baseline schedule workbooks. A target-specific, complete-case filter for the two model features and observed target yields 151 projects for Delay and 151 for Cost. The two regressions are evaluated separately, and the same project-ID split is generated per target. The publisher's repository does not specify a data license; see [dataset card](dataset_dslib.md).

## Features and adapters

| Feature | Meaning | Input adapter |
|---|---|---|
| `planned_duration_days` | Baseline planned duration in calendar days | `planned_duration_weeks * 7` |
| `planned_budget_bac` | Budget at completion from BAC | `planned_budget` copied in caller-provided currency units |

Both features must be present and positive. No categories, methodology, progress, EVM values, names, or synthetic values are inferred or imputed. The public input adapter is recorded at `/api/models/empirical/schema`.

## Targets and selection

- Delay: observed final actual duration minus planned duration, in days. Negative values represent early completion.
- Cost: `(observed final actual cost - BAC) / BAC`, only when BAC is greater than zero. Negative values represent under-budget execution.
- Health: not trained. DSLIB does not provide one consistent observed Health/final-status label with a pre-registered, defensible definition. No thresholds were selected from TEST.

Candidates: median baseline, Ridge, Random Forest, and LightGBM. The winner was selected by validation MAE after a two-stage `GroupShuffleSplit`, grouped by `project_id`, seed 42. The held-out TEST was evaluated once after selection. The median baseline won validation for both targets; therefore the deployed empirical estimates are constants learned from real TRAIN outcomes, not a more complex ML estimator.

## Evaluation

| Target | Projects | Selected candidate | TEST MAE | TEST RMSE | TEST R² | Median baseline TEST MAE |
|---|---:|---|---:|---:|---:|---:|
| Delay (days) | 151 | Median baseline | 30.7097 | 45.9453 | -0.0339 | 30.7097 |
| Cost (ratio of BAC) | 151 | Median baseline | 0.115703 | 0.277471 | -0.0317 | 0.115703 |

Test contains 31 projects per target. Bootstrap 95% intervals for TEST MAE: Delay `[19.7403, 43.2419]` days; Cost `[0.05171, 0.21098]` BAC ratio. These estimates have substantial uncertainty and do not indicate improvement over the baseline. Candidate validation scores, test predictions, residuals, split IDs, and hashes are stored in the local artifact `artifacts/1.0.0-empirical/`.

## Leakage and temporal evaluation

Final actual duration and final cost are target-only. Snapshot features are restricted to values available at the project-control tracking date, and only dates strictly before planned finish are eligible. No post-finish snapshot was found among the 14 candidate rows audited; 13 snapshots per target remain with complete target and feature data. This is too small for training or cutoff metrics. Early-prediction evaluation is `not_available`; no 20/40/60/80% curve is fabricated. Full results: `reports/empirical/leakage_audit.json`.

## Limitations and out of scope

The sample is small, heterogeneous, observational, and incomplete. The source has no consistent Health label; Team Health remains an independent operational heuristic and is not trained by this model. Empirical outputs include Delay and Cost only; Health, Final Status, fused risk, empirical drivers, and grounded recommendations are unavailable. A shared GenAI response is not enabled for this model because there is no validated Health target or model-specific grounding evaluation.

No common external test set connects DSLIB and Mendeley, so their metrics cannot establish a head-to-head winner. The model has no prospective validation, calibration claim, fairness assessment, causal interpretation, or external-generalization evidence. Predictions for a new domain should be treated as unsupported until evaluated there.

## Operational efficiency

A separate local benchmark used 31 held-out DSLIB TEST input rows, one warm-up per mode, and three repetitions. Individual sequential requests had median total latency 79.622 ms and 389.34 projects/s; CSV batch had 50.148 ms and 618.17 projects/s; success was 100% in both modes. This is a local sequential measurement, not production load, concurrency, predictive quality, or human productivity. Full provenance: `reports/efficiency/empirical_operational_benchmark.json`.