# PRUNIN AI Core 0.9.0-academic

## Problema
Early risk estimation for project Health, Delay and Cost Overrun.

## Dataset
Mendeley v2 — DOI 10.17632/2p5sz57wh2.2

## Tipo de datos
Synthetic external dataset (CC BY 4.0). No production validation exists.

## Proyectos
4000

## Snapshots
72549

## Split
70/15/15 grouped by project_id: {'train': 2800, 'validation': 600, 'test': 600}

## Leakage prevention
Direct targets/outcomes are excluded from the feature whitelist; projects are disjoint across train/validation/test.

## Modelos
LightGBM: Health, Delay and Cost Overrun.
Final Status: derived business status from Health; no independent classifier was trained.

## Features utilizadas
planned_duration_weeks, planned_budget, true_progress, spi, cpi, project_type, methodology

## Variables excluidas
actual_cost, actual_duration, actual_duration_days, actual_duration_months, cost_overrun, cost_overrun_ratio, delay_days, final_status, health, schedule_delay, schedule_delay_days

## Project-level evaluation
One latest available snapshot per project within each split.

| Target | Test project metrics |
|---|---|
| health | `{"accuracy": 0.7266666666666667, "balanced_accuracy": 0.6824223458081726, "macro_f1": 0.6275758334320115, "weighted_f1": 0.7405357252418434, "critical_recall": 0.5681818181818182, "critical_support": 44, "per_class_recall": {"at_risk": 0.7389277389277389, "critical": 0.5681818181818182, "healthy": 0.7401574803149606}}` |
| delay_days | `{"mae": 27.71046834259029, "rmse": 37.238021288469284, "r2": 0.07530489938405993}` |
| cost_overrun_ratio | `{"mae": 0.0014715785054456153, "mae_percentage_points": 0.14715785054456154, "rmse": 0.00598016858871776, "r2": 0.9918156958562626}` |
| final_status | Derived business status from Health; no separate ML metric. |

## Snapshot-level evaluation
Each available snapshot is one row; projects with more snapshots can carry more weight.

| Target | Test snapshot metrics |
|---|---|
| health | `{"accuracy": 0.6783518399559512, "balanced_accuracy": 0.582768010376126, "macro_f1": 0.5470548202603385, "weighted_f1": 0.6942235187775262, "critical_recall": 0.4544287548138639, "critical_support": 779}` |
| delay_days | `{"mae": 32.17595573757554, "rmse": 43.52880713694457, "r2": 0.03305282047934266}` |
| cost_overrun_ratio | `{"mae": 0.018027032862485026, "mae_percentage_points": 1.8027032862485026, "rmse": 0.026432533568949177, "r2": 0.8297066199911258}` |

## Baselines
Train-only majority-class/median baselines; TEST is descriptive and not used for model selection.

| Target | Baseline | Project-level TEST comparison |
|---|---|---|
| health | majority_class_from_train_projects: at_risk | macro_f1 improvement=0.3496360861045091 |
| delay_days | median_from_train_projects: 30.4375 | mae improvement=0.139844157409712 |
| cost_overrun_ratio | median_from_train_projects: 0.05623971460336885 | mae improvement=0.04950285882252536 |

## Evaluación temporal
TEST only; one snapshot per project with maximum true_progress <= cutoff.

| Cutoff | Available / TEST projects | Coverage | Max selected progress | Health Macro-F1 | Critical recall | Delay MAE | Delay RMSE | Delay R² | Cost MAE ratio | Cost MAE pp | Cost R² |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20% | 236 / 600 | 39.3% | 0.1999660477055671 | 0.39793773109518665 | 0.1111111111111111 | 33.146182570492925 | 44.85608441156631 | 0.08602426000403374 | 0.031369433183519604 | 3.1369433183519604 | 0.4223254523787896 |
| 40% | 463 / 600 | 77.2% | 0.3999743726235977 | 0.509354768489031 | 0.44 | 30.40682256027908 | 40.96282138769324 | 0.019973592640045168 | 0.027893733246334856 | 2.7893733246334858 | 0.659699584613774 |
| 60% | 576 / 600 | 96.0% | 0.5998440113584965 | 0.5229588790027976 | 0.4473684210526316 | 28.3056066326096 | 38.45500934069916 | 0.03820864306092553 | 0.02143231471500083 | 2.143231471500083 | 0.8250949890776234 |
| 80% | 599 / 600 | 99.8% | 0.7999771784515177 | 0.5705878972080334 | 0.5454545454545454 | 27.522773422256524 | 37.49074480506258 | 0.06299140797036062 | 0.014067181848647381 | 1.406718184864738 | 0.9261744521913563 |

## Delay experiment

Selection uses TRAIN fit and VALIDATION metrics; TEST is only evaluated after freezing the selection.
- Selection: candidate selected on validation only; automatic promotion disabled
- Selected candidate: median_train_project_baseline
- TEST after freeze: MAE 27.8503125, RMSE 38.99882017780046, R² -0.014210966177522932.
- Promoted automatically: False

## Feature importance
LightGBM native gain/split; this is predictive sensitivity, not causality.

## Riesgos metodológicos
- Project outcomes are repeated across monthly snapshots.
- Same-period SPI/CPI/progress may be temporally close to final outcomes; this is not a prospective time-cutoff evaluation.
- Direct target, actual-duration and actual-cost columns are excluded from the model feature whitelist.
- CPI has a structural relation with final cost in synthetic EVM generation; high late-stage Cost R² is internal synthetic performance, not production evidence.
- Critical class has limited project-level support and lower recall/F1 than the majority class.

## Limitaciones
No real PRUNIN validation exists. External projects are not joined to Mendeley. Team Health remains an observable operational heuristic; fusion weights are not empirically calibrated.

## Reproducibilidad
Python: 3.12.15
Random seed: 42
Dataset SHA256: 32b7586db9dda0b3994573a3985c114dafe65dee93c948254b69f00d194c0ac3
Timestamp UTC: 2026-10-08T23:36:23.654734+00:00
Commit: dd890b529083b5efc8e27914a596bae30b0bc4b0

## Qué no se puede concluir
These synthetic results do not establish causal effects, operational validity, or expected performance on live PRUNIN projects.

## Qué falta para producción
Prospective evaluation and calibration on real PRUNIN projects, plus external validation of temporal cutoffs and operational fusion.
