# Datasets y uso previsto

## 1. Mendeley — Project Risk + EVM

DOI: https://doi.org/10.17632/2p5sz57wh2.2

Uso: entrenamiento base de costo, cronograma y outcomes. Es sintético externo, por lo que no reemplaza la validación real.

Archivos esperados:

- `project_risk_raw_dataset.csv`
- `simulated_project_ev_metrics_final.csv.xlsx`
- `project_delay_cost_overrun_summary_final.csv.xlsx`

## 2. Itemlet

https://zenodo.org/records/19411554

Uso: esfuerzo, ciclo de vida de issues, story points, complejidad y señales Agile. Es una fuente real independiente y no se une por `project_id` con Mendeley.

## 3. Collaboration / Delivery

https://zenodo.org/records/15681547

Uso: tamaño del equipo, expertise, contribución core, interacción y change lead time. Puede alimentar el diseño/validación de señales del Team Health Index.

## 4. SQuaD

https://zenodo.org/records/17566691

Uso: defectos, calidad y procesos. El dataset completo es muy grande; se recomienda trabajar con subconjuntos o tablas agregadas por release/proyecto.

## Política de procedencia

Toda fila estandarizada debe mantener:

- `data_source`
- `source_project_id`
- `is_synthetic`
- `snapshot_index`

Cada fuente conserva un `data_source` propio y un `source_project_id`. Los IDs internos llevan namespace (`mendeley::...`, `itemlet::...`, `collaboration::...`, `squad::...`). No se permite hacer `concat`, join por posición ni relacionar proyectos de fuentes distintas solo por similitud de atributos. Features ausentes quedan ausentes, no se rellenan con valores inventados.

El modelo `0.9.0-academic` se entrena exclusivamente con Mendeley v2, que es sintético. Itemlet, Collaboration y SQuaD se registran como fuentes complementarias independientes; sus descargas fallidas son warnings y no cambian la población del modelo principal. SQuaD se limita a subsets seleccionados porque el record puede referenciar volúmenes muy grandes.
