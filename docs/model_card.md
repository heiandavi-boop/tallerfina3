# Model Card — PRUNIN AI Core V9 académico

## Propósito

Estimar Health, retraso final en días y sobrecosto relativo a partir de snapshots. Final Status se conserva como estado de negocio derivado de Health, no como un clasificador independiente.

## Entradas estáticas candidatas

- `planned_duration_weeks`
- `planned_budget`
- `baseline_scope_units`
- `sector`
- `project_type`
- `methodology`
- `complexity`
- `criticality`

## Entradas temporales del core V9

- `true_progress`
- `spi`
- `cpi`
- `team_utilization`
- `team_capacity_ratio`
- `average_productivity`
- `defect_rate`
- `rework_ratio`
- `scope_growth_ratio`
- `dependency_delay_days`
- `normalized_risk_exposure`
- `governance_health_score`

El entrenador utiliza únicamente columnas con cobertura real en el dataset recibido y registra esa selección en `feature_manifest.json`.

## Variables retiradas del contrato V8.6.3

- `reported_progress`: no existe de forma consistente en las fuentes externas.
- `critical_path_delay_days`: no se imputa; se recuperará cuando PRUNIN disponga de CPM auditable con baseline y actuals.
- `team_morale`: se reemplaza conceptualmente por `team_health_index`, que mide señales operativas, no estados psicológicos.

## Team Health Index

Es un indicador determinístico, trazable y con cobertura explícita. Usa, cuando están disponibles:

- utilización;
- capacidad;
- productividad;
- retrabajo;
- defectos;
- estabilidad del equipo;
- colaboración.

No se usa como feature supervisada del core hasta disponer de proyectos reales donde esas señales estén emparejadas con outcomes finales. Sí puede usarse como señal operativa de fusión, marcada como heurística hasta calibración.

## Split y leakage

El split 70/15/15 es por `project_id`; todos los snapshots de cada proyecto quedan en un solo conjunto y se verifican los tres pares con `isdisjoint`. Las features proceden de una whitelist y excluyen directamente targets, duración real, costo real y outcomes finales.

Se informan por separado métricas row-level y project-level. La evaluación temprana usa exclusivamente proyectos TEST, una observación no posterior por proyecto para cada cutoff de `true_progress` (20/40/60/80 %), y no reentrena con test.

## Final Status

La inspección de Mendeley v2 encontró `Schedule_Delay` y `Cost_Overrun`, entre otros outcomes de duración/costo, pero no una etiqueta independiente `Final_Status`. Health se genera con reglas sobre delay/cost ratios y Final Status se transforma determinísticamente: `healthy → successful`, `at_risk → challenged`, `critical → critical`. No se entrena un segundo clasificador redundante. FastAPI mantiene `final_status` y añade `final_status_source=derived_from_health`.

## Limitaciones

1. El dataset Mendeley usado para el core es sintético externo; no existe validación productiva con datos PRUNIN.
2. Progreso, SPI y CPI de snapshots tardíos pueden estar temporalmente cerca del outcome; la evaluación por cutoff no elimina ese riesgo en datos sintéticos.
3. High late-stage cost performance may partly reflect the structural relationship between CPI, progress, and final cost outcomes in the synthetic EVM generator; high R² is internal synthetic performance, not production evidence.
4. Proyectos con más snapshots pueden pesar más en métricas row-level; project-level se informa aparte.
5. Itemlet, SQuaD y Collaboration/Delivery son fuentes de proyectos distintos y no se mezclan con Mendeley.
6. Team Health continúa como señal operativa heurística, no como outcome clínico ni feature supervisada.
7. La activación productiva exige validación temporal y externa con proyectos reales de PRUNIN.
4. Itemlet, SQuaD y Collaboration/Delivery son fuentes de proyectos distintos y no se mezclan con Mendeley.
5. Team Health continúa como señal operativa heurística, no como outcome clínico ni feature supervisada.
6. La activación productiva exige validación temporal/externa con proyectos reales de PRUNIN.
