# Arquitectura del cerebro V9 académico

## Principio

No se fuerza un único dataset universal. Las fuentes públicas no describen los mismos proyectos y por ello no deben unirse por columnas como si fueran observaciones equivalentes.

```text
Mendeley Risk + EVM ──> Core Predictor ──> Health / Status / Delay / Cost
                                   │
PRUNIN operacional ──> Team Health Index ─┤
                                   │       ├─> Fusion / explicación
Itemlet ──────────────> Effort signals ────┤
GitHub Collaboration ─> Team signals ──────┤
SQuaD ────────────────> Quality signals ───┘
```

## Diferencias frente a V8.6.3

V8.6.3 tiene 15 features temporales. V9 académico elimina del core obligatorio `reported_progress`, `critical_path_delay_days` y `team_morale`.

- `reported_progress`: puede seguir mostrándose como comparación administrativa si el usuario lo captura, pero no condiciona el modelo.
- `critical_path_delay_days`: queda reservado para una futura feature calculada por CPM real, no simulada.
- `team_morale`: se sustituye por `team_health_index` operativo.

## Team Health Index

No es una etiqueta psicológica. La fórmula usa señales observables y renormaliza pesos cuando faltan componentes. Cada cálculo devuelve `score`, `level`, `weight_coverage` y `component_count`.

## Prevención de leakage

Los snapshots se dividen por `project_id`, no por fila. Un proyecto completo pertenece a train, validation o test.

## Artefactos

Cada entrenamiento guarda:

- `health.joblib`
- `final_status.joblib`
- `delay_days.joblib`
- `cost_overrun_ratio.joblib`
- `metrics.json`
- `feature_manifest.json`
- `split_manifest.json`
- `training_config_resolved.yaml`
