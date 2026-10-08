# Entrenamiento

## Demo

```bash
python scripts/bootstrap_demo_data.py
python scripts/train_core.py --input data/processed/demo_core.csv --version demo-0.1.0
```

## Mendeley

Mendeley v2 es la única fuente del modelo académico `artifacts/0.9.0-academic/`. Itemlet, Collaboration y SQuaD son fuentes complementarias opcionales; un fallo suyo genera `[WARN] Optional dataset unavailable` y nunca sustituye ni amplía silenciosamente el dataset principal.

En una terminal nueva:

```bash
source .venv/bin/activate
./scripts/train_all.sh
```

El orden obligatorio es: Python/dependencias, metadata y descarga, validación raw/hash/esquema, preparación Mendeley, auditoría, `artifacts/data_readiness.json`, split agrupado y chequeos `isdisjoint`, entrenamiento, evaluación estándar, evaluación temporal, verificación de importance, export de reports, figuras, inferencia, tests y `scripts/preflight_demo.sh`. `train_core.py` vuelve a validar raw y exige readiness, fingerprint procesado y split aprobados para el modelo académico.

`python scripts/download_datasets.py` usa metadata oficial para Mendeley v2, Itemlet (Parquet preferido y sus metadatos) y Collaboration. Los archivos válidos se reutilizan desde caché; `python scripts/download_datasets.py --validate-only` valida Mendeley sin red. Los originales se conservan en `data/raw/`; `python scripts/prepare_datasets.py` escribe solo en `data/processed/` y no concatena datasets.

SQuaD es opcional por su tamaño. `PRUNIN_INCLUDE_SQUAD=1 ./scripts/train_all.sh` solicita un subset acotado del record; nunca descarga el volcado masivo. Collaboration conserva el ZIP y registra CSV candidatos de colaboración/delivery, pero no los une a proyectos Mendeley. Sus señales quedan fuera del modelo académico hasta validar una unidad temporal y una definición operacional compatibles.

`train_core.py` solo admite un archivo local preparado; rechaza URLs y cualquier archivo dentro de `data/raw/`.

## Leakage y alcance

El split es por proyecto, no por snapshot: los tres conjuntos deben ser disjuntos en `project_id`, y el split validado queda en `artifacts/0.9.0-academic/split_manifest.json`. Las columnas directas de outcomes y resultados finales se excluyen del whitelist de features y se comprueba que no haya solapamiento con los targets.

La validación sigue siendo sintética y no es una evaluación prospectiva: outcomes de proyecto se repiten en snapshots mensuales, y SPI/CPI/progreso del mismo periodo pueden estar temporalmente cerca del resultado final. Filas de proyectos con más snapshots pesan más en las métricas por fila. Los resultados requieren validación temporal/proyecto real antes de una conclusión operacional.

El reporte `artifacts/data_readiness.json` registra cobertura, distribuciones, procedencia y el estado del leakage gate. Un readiness falso, falta de Mendeley o fallo de auditoría detiene el flujo antes de entrenar.

`reports/0.9.0-academic/` contiene métricas, resumen del dataset/split, readiness, feature manifest, reproducibilidad, clasificación por clase y evaluación temporal. `scripts/export_report.py` exporta solo resultados ligeros; no copia datasets ni `.joblib`. `scripts/generate_evaluation_plots.py` produce figuras analíticas de confusion matrix, predicción/actual, evolución por cutoff e importance nativa.

Health classification report incluye accuracy, balanced accuracy, macro/weighted F1, precision/recall macro y weighted, soporte/precision/recall/F1 por clase y confusion matrix en validation/test. Regresión agrega mediana y percentiles absolutos del error. MAPE se deja nulo si hay valores cero/negativos; Cost Overrun incluye MAE en puntos porcentuales.

Los experimentos comparan candidatos usando TRAIN/VALIDATION; TEST queda para evaluación después de congelar la selección y nunca decide hiperparámetros/promoción. Delay mantiene el artifact vigente salvo promoción manual documentada. El R² alto de Cost tardío puede reflejar la relación estructural entre CPI, progreso y costo final del generador EVM sintético; no es validación productiva.

Final Status no es independiente en Mendeley v2: el record no tiene target original de estado y el target del proyecto era una traducción uno-a-uno de Health. Se mantiene como estado de negocio derivado sin segundo modelo ML.

## Criterios de aceptación antes de reportar resultados

1. No hay solapamiento de `project_id` entre train/validation/test.
2. `health` contiene al menos dos clases en train y test; Final Status se deriva de Health en Mendeley v2.
3. `health`, `delay_days` y `cost_overrun_ratio` superan la cobertura mínima de readiness.
4. Se informa por separado si la fuente es sintética o real.
5. No se presenta `team_health_index` como moral, satisfacción o salud mental.
6. La fusión con Team Health se identifica como heurística hasta contar con calibración real.
