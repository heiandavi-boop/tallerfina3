# Model Card — PRUNIN AI Core V9 académico

## Propósito

Predecir cuatro resultados de gestión de proyectos: salud del proyecto, estado final, retraso final en días y sobrecosto relativo. La versión académica busca entrenabilidad y reproducibilidad con variables observables, evitando imputaciones semánticas inventadas.

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

El split es por `project_id`. Todos los snapshots de un proyecto quedan en un único conjunto: train, validation o test.

## Limitaciones

1. El dataset Mendeley usado para el core es sintético externo.
2. Itemlet, SQuaD y Collaboration/Delivery corresponden a proyectos distintos y no se unen horizontalmente con Mendeley.
3. Las métricas demo verifican software, no desempeño científico.
4. La activación productiva exige validación temporal y externa con datos reales de PRUNIN.
