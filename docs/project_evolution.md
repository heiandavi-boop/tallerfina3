# Evolución histórica, datasets y trazabilidad de PRUNIN

**Alcance:** distinguir el proyecto PRUNIN a lo largo de su desarrollo de los tres modelos desplegados en el artefacto académico `0.9.0-academic`. Este documento es una reconstrucción documental; no constituye una ejecución de entrenamiento nueva.

## Resumen ejecutivo

PRUNIN ha tenido distintas etapas de modelado. En conversaciones y registros históricos de desarrollo se describieron experimentos con **datasets sintéticos propios y modelos PyTorch**, incluida una línea Long Horizon con observaciones temporales. Posteriormente se desarrolló un **pipeline académico independiente con tres modelos LightGBM**, cuya fuente de entrenamiento identificada y reproducible es **Mendeley Data v2**. La capa de recomendaciones de **Qwen3 8B** utiliza un modelo generativo preentrenado e información estructurada de inferencia; no fue entrenada con Mendeley en este repositorio.

**Regla de comunicación:** decir «PRUNIN ha trabajado con diversas fuentes y experimentos» no equivale a «los tres LightGBM actuales se entrenaron con todas las fuentes». La evidencia más sólida sobre los artefactos vigentes está en los manifiestos, `docs/model_card.md`, `docs/training.md` y `reports/0.9.0-academic/`.

## Cronología y grado de comprobación

| Etapa | Datos/modelos descritos | Uso | Verificación |
|---|---|---|---|
| Exploración y versiones V8.6.2 | Simulaciones propias de proyectos; modelos previos | Desarrollo y evaluación de condiciones de proyecto | **Antecedente de conversaciones del proyecto**; no hay aquí un manifiesto versionado de entrenamiento de esta versión. |
| V8.6.2-RC1 / SIM500 | SIM500, 500 proyectos; además se describieron 200 escenarios de frontera | **Evaluación**, no prueba de entrenamiento con SIM500 | **Antecedente histórico**; recuperar reportes originales antes de citar métricas como auditadas. |
| Long Horizon / `0.7.4-health` | `long_horizon_dataset_10000_health_v2`, 10.000 proyectos propios, con cortes 20/40/60/80 % | **Entrenamiento histórico** referido en registros previos | **Antecedente histórico pendiente de adjuntar**: artefactos, configuración, split, hashes y logs no están acreditados en este repositorio. |
| V8.6.3 | `health_anchor_v863.pt`, descrito como componente PyTorch entrenado con escenarios balanceados | Entrenamiento/experimentación histórica del módulo Health | **Antecedente histórico pendiente de adjuntar**; no confundir con Health LightGBM actual. |
| `0.9.0-academic` | Mendeley Data v2; 4.000 proyectos, 72.549 snapshots | **Entrenamiento de Health, Delay y Cost con LightGBM** | **Confirmado por el repositorio:** código de preparación, manifiestos, hashes y reportes académicos. |
| Integración de Qwen3 8B | Modelo generativo existente servido por Ollama | Recomendaciones fundamentadas en evidencia; no es un cuarto LightGBM | Confirmado por la implementación API y evaluaciones GenAI. |

**Precisión sobre antecedentes:** los nombres, cantidades y entrenamientos previos indicados arriba provienen de registros y conversaciones históricas del proyecto, no de una validación independiente de los artefactos antiguos dentro de este `main`. No se atribuyen métricas oficiales ni porcentajes de eficacia a esos entrenamientos sin sus reportes originales.

## Fuentes de datos externas y su utilización

| Fuente | Procedencia | Papel en el repositorio actual |
|---|---|---|
| **Mendeley Data v2** | Publicación externa, DOI [10.17632/2p5sz57wh2.2](https://doi.org/10.17632/2p5sz57wh2.2) | **Única fuente de entrenamiento del artefacto académico `0.9.0-academic`**. |
| **Itemlet** | Registro externo consultado por el descargador a través de Zenodo | Fuente complementaria opcional; no se concatena para entrenar LightGBM académico. |
| **Collaboration** | Registro externo en Zenodo con indicadores de colaboración/delivery | Fuente complementaria opcional; sus CSV se inspeccionan pero no se unen a Mendeley. |
| **SQuaD** | Registro externo en Zenodo, con repositorios e indicadores de desarrollo | Fuente opcional; descarga parcial condicionada por `PRUNIN_INCLUDE_SQUAD`; no entrena los tres artefactos académicos. |

La implementación de descarga de fuentes opcionales **no acredita por sí sola** que todas fueran descargadas exitosamente en la misma ejecución. Comprobar el manifiesto local de adquisición antes de afirmarlo. El entrenamiento académico solo utiliza `data/processed/mendeley_core.csv`, como documenta `scripts/prepare_datasets.py`.

## Detalle técnico del modelo académico vigente

- **Fuente y versión:** Mendeley Data v2, DOI 10.17632/2p5sz57wh2.2.
- **Volumen:** 4.000 proyectos y 72.549 observaciones de seguimiento (*snapshots*).
- **Partición disjunta por proyecto:** TRAIN 2.800; VALIDATION 600; TEST 600. No se divide por fila para evitar mezclar observaciones de un mismo proyecto.
- **Variables entrenadas:** `planned_duration_weeks`, `planned_budget`, `true_progress`, `spi`, `cpi`, `project_type`, `methodology`.
- **Tres modelos:** Health = clasificación; Delay = regresión de días; Cost = regresión de desviación relativa del presupuesto.
- **Final Status:** resultado derivado de Health; **Team Health:** cálculo heurístico externo al entrenamiento supervisado.
- **Control de calidad:** hashes de fuentes y dataset, verificación del split, preprocesamiento aprendido sobre TRAIN, auditoría y resultados reproducibles.
- **Promesa original:** en TEST, Risk Alert (At Risk o Critical) detecta 359/473 proyectos finalmente en riesgo al 60 % de avance = **75,90 %**, con 96 % de cobertura de la población TEST. No confundir con **56,82 %** de recall para la clase Critical exacta.
- **Generación:** Qwen3 8B en Ollama transforma evidencias autorizadas en acciones con procedencia, justificación y seguimiento. No cambia las salidas LightGBM.

## Evidencias y límites de la documentación

1. [Preparación y entrenamiento académico](training.md).
2. [Ficha del artefacto académico](model_card.md).
3. [Arquitectura actual](architecture.md).
4. [Métricas y reportes académicos](../reports/0.9.0-academic/).
5. [Validación del KPI inicial](../reports/promise_validation/promise_validation_report.md).
6. [Descargador de fuentes externas](../scripts/download_datasets.py).
7. [Preparación del archivo académico](../scripts/prepare_datasets.py).

Para certificar los entrenamientos históricos V8/Long Horizon dentro de este repositorio aún se requieren los enlaces a sus informes originales, fingerprints, artefactos o commits. **No reescribir reportes actuales, no mezclar datasets ni reentrenar el artefacto congelado para completar esta cronología.**

## Forma recomendada de contarlo durante la presentación

> «PRUNIN nació como una línea de investigación aplicada en la que probamos simulaciones propias y modelos anteriores, incluidos enfoques temporales. Para la entrega académica consolidamos tres modelos especializados LightGBM y un pipeline reproducible usando Mendeley Data v2. Paralelamente exploramos Itemlet, Collaboration y SQuaD como fuentes potenciales de ampliación, pero las mantuvimos separadas por rigor metodológico. Hoy demostramos esa versión académica conectada con reglas operativas y Qwen3 8B, sin presentar los experimentos previos como si fueran el entrenamiento de estos artefactos».
