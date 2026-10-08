# Esquema normalizado para entrenamiento

## Identidad y procedencia

| Columna | Requerida | Descripción |
|---|---:|---|
| `project_id` | Sí | Identidad usada para split por proyecto. |
| `source_project_id` | Recomendada | Identidad original en la fuente. |
| `data_source` | Recomendada | Fuente de procedencia. |
| `is_synthetic` | Recomendada | Marca de datos sintéticos. |
| `snapshot_index` | Recomendada | Orden temporal del snapshot. |

## Features

Las columnas de features están documentadas en `docs/model_card.md`. No todas son obligatorias: el entrenador excluye automáticamente una feature completamente ausente, pero nunca inventa valores para incorporarla.

## Targets

Se requiere `delay_days` y `cost_overrun_ratio` para derivar las etiquetas del core cuando `health` / `final_status` no vienen de una fuente auditada.

- `delay_days`: días de retraso final >= 0.
- `cost_overrun_ratio`: `(costo_final - presupuesto_base) / presupuesto_base`; por ejemplo 0.10 = 10 %.

## Convención temporal

Toda feature de un snapshot debe poder conocerse en su fecha de corte. No se permiten features calculadas usando información posterior al snapshot.
