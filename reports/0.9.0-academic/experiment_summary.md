# PRUNIN AI Core 0.9.0-academic

## Dataset
Mendeley v2

## Tipo de datos
Sintético externo (CC BY 4.0). No existe validación productiva todavía.

## Proyectos
4000

## Snapshots
72549

## Split
70/15/15 por project_id: {'train': 2800, 'validation': 600, 'test': 600}

## Modelos
LightGBM: Health, Delay y Cost Overrun.
Final Status: derived business status from Health; no independent classifier was trained.

## Features
planned_duration_weeks, planned_budget, true_progress, spi, cpi, project_type, methodology

## Variables excluidas
actual_cost, actual_duration, actual_duration_days, actual_duration_months, cost_overrun, cost_overrun_ratio, delay_days, final_status, health, schedule_delay, schedule_delay_days

## Métricas

| Target | Unit | Test summary |
|---|---|---|
| health | classification | `{"balanced_accuracy": 0.582768010376126, "macro_f1": 0.5470548202603385}` |
| final_status | derived | {'healthy': 'successful', 'at_risk': 'challenged', 'critical': 'critical'} |
| delay_days | original target unit | `{"mae": 32.17595573757554, "rmse": 43.52880713694457, "r2": 0.03305282047934266}` |
| cost_overrun_ratio | original target unit | `{"mae": 0.018027032862485026, "mae_percentage_points": 1.8027032862485026, "rmse": 0.026432533568949177, "r2": 0.8297066199911258}` |

## Evaluación temprana

| Cutoff | Test projects | Health Macro-F1 | Delay MAE (days) | Cost MAE (ratio / pp) |
|---:|---:|---:|---:|---:|
| 20% | 236 | 0.39793773109518665 | 33.146182570492925 | 0.031369433183519604 / 3.1369433183519604 |
| 40% | 463 | 0.509354768489031 | 30.40682256027908 | 0.027893733246334856 / 2.7893733246334858 |
| 60% | 576 | 0.5229588790027976 | 28.3056066326096 | 0.02143231471500083 / 2.143231471500083 |
| 80% | 599 | 0.5705878972080334 | 27.522773422256524 | 0.014067181848647381 / 1.406718184864738 |

## Riesgos metodológicos
- Project outcomes are repeated across monthly snapshots.
- Same-period SPI/CPI/progress may be temporally close to final outcomes; this is not a prospective time-cutoff evaluation.
- Direct target, actual-duration and actual-cost columns are excluded from the model feature whitelist.
- SPI/CPI/progress tardíos pueden estar cerca del outcome; evaluar prospectivamente requiere un corte temporal con datos reales.
- Los resultados por snapshot pueden dar más peso a proyectos con más observaciones; también se presentan métricas por proyecto.

## Limitaciones
Mendeley es sintético. Los datasets externos no se mezclan ni se unen con Mendeley. Team Health continúa como señal operativa heurística.

## Reproducibilidad
Random seed: 42
Python: 3.12.15
Commit: b9aead9b60f2094ae7166b1b6c6f38acd47b67dc
Timestamp UTC: 2026-10-08T22:48:25.510591+00:00

## Commit
b9aead9b60f2094ae7166b1b6c6f38acd47b67dc
