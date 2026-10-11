# Eficiencia operacional del sistema

**Alcance de la afirmación:** PRUNIN evalúa eficiencia operacional mediante benchmarks reproducibles de latencia, throughput y procesamiento batch. No se estima ahorro de tiempo humano porque no existe un estudio controlado de usuarios.

Estas mediciones describen el comportamiento automatizado en un equipo local; no representan productividad laboral, carga productiva ni un benchmark universal.

## Método reproducible

El runner `scripts/benchmark_operational_efficiency.py` mide el API real con `artifacts/0.9.0-academic`. Lee `artifacts/0.9.0-academic/split_manifest.json`, selecciona únicamente proyectos TEST y toma el snapshot más reciente por `project_id`. Ordena los IDs, aplica seed 42 una sola vez a 100 proyectos y usa prefijos de esa misma muestra para N=1, 10, 25, 50 y 100. `reports/efficiency/benchmark_cases.csv` registra `case_order`, `project_id` y las siete features predictivas; no incluye labels, targets ni outcomes.

Antes de medir se comprueban `/api/ready`, `/api/health`, versión, dataset, las siete features y `/api/genai-status.enabled=false`. Si el artifact servido no es `0.9.0-academic`, el script termina con `unavailable_academic_artifact`; si GenAI sigue activa, no comienza la comparación. Ejecuta tres warm-ups individuales, que se excluyen de estadísticas.

Para cada N se miden 10 repeticiones en 1/10/25 y 5 en 50/100:

- **Individual:** N requests secuenciales a `POST /api/predict?include_recommendations=false`.
- **Batch:** un request `POST /api/predict-csv` con exactamente esos mismos N proyectos.

Ambos recorren la misma predicción ML y los drivers locales, sin recomendaciones, fallback ni Qwen. No hay concurrencia: el loop del CSV también procesa filas secuencialmente. La duración cliente mide HTTP, transferencia, serialización y respuesta; `server_total_ms` suma `timing.total_ms` por inferencia. La diferencia se conserva como overhead cliente aproximado, no como una medición aislada de red.

La mediana por repetición determina throughput (`N / median_ms`) y `ms_per_project`. Speedup y reducción temporal solo se reportan si coinciden hash de casos, tarea, GenAI apagada y éxito de ambas modalidades al 100 %. El término speedup compara endpoint batch con requests individuales secuenciales; no significa paralelización.

## Ejecución

Terminal 1, servicio local aislado para benchmark:

```bash
PRUNIN_ARTIFACT_DIR=artifacts/0.9.0-academic \
PRUNIN_ENABLE_OLLAMA=0 PYTHONPATH=src \
./.venv/bin/python -m uvicorn prunin_ai.api.app:app --host 127.0.0.1 --port 8002
```

Terminal 2:

```bash
PRUNIN_ENABLE_OLLAMA=0 PYTHONPATH=src \
./.venv/bin/python scripts/benchmark_operational_efficiency.py \
  --api-url http://127.0.0.1:8002
```

El benchmark pesado no forma parte de CI. La suite de tests solo verifica sus funciones puras con fixtures. El runner no entrena modelos ni modifica artifacts.

## Resultado observado

Ejecución local del 11 de octubre de 2026, API `0.9.0-academic`, Mendeley Data v2 sintético externo, macOS arm64, Python 3.12.15. Se procesaron los mismos 100 proyectos únicos TEST; 100/100 respuestas fueron válidas en individual y batch para los cinco tamaños.

| N | Repeticiones por modo | Individual mediana (ms) | Batch mediana (ms) | Batch vs. secuencial | Throughput batch (proy/s) | Batch ms/proyecto | Éxito individual/batch |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 45.84 | 46.61 | 0.983×; batch 1.68 % más lento | 21.454 | 46.61 | 100 % / 100 % |
| 10 | 10 | 454.24 | 426.40 | 1.065×; reducción 6.13 % | 23.452 | 42.64 | 100 % / 100 % |
| 25 | 10 | 1138.24 | 1065.97 | 1.068×; reducción 6.35 % | 23.453 | 42.64 | 100 % / 100 % |
| 50 | 5 | 2265.70 | 2116.37 | 1.071×; reducción 6.59 % | 23.625 | 42.33 | 100 % / 100 % |
| 100 | 5 | 4440.90 | 4215.74 | 1.053×; reducción 5.07 % | 23.721 | 42.16 | 100 % / 100 % |

En N=100, throughput batch fue 23.721 proyectos/s (1423.24 proyectos/min), calculado sobre la mediana medida de 4215.74 ms. El batch fue 1.68 % más lento para N=1; para N=10–100 la reducción observada fue 5.07–6.59 %. Los datos son compatibles con crecimiento aproximadamente lineal respecto a la referencia local N=1, con menor costo por proyecto al agrupar. No es evidencia de escalabilidad productiva ni de paralelismo.

El JSON contiene para cada N/modo media, mediana, p50, p90, p95, mínimo, máximo, desviación estándar, éxito/error, throughput, ms/proyecto y overhead cliente-servidor. Las ejecuciones crudas están en `reports/efficiency/operational_benchmark_raw.csv`.

## Robustez y GenAI

Los controles se ejecutaron fuera de las repeticiones normales: una fila con metodología faltante fue aceptada con coverage 85.71 % y esa feature registrada para imputación según training policy; una entrada con coverage 14.29 % fue bloqueada con HTTP 422; categoría inválida y `true_progress=1.2` también fueron rechazados; CSV respondió HTTP 200 con error controlado por fila para la categoría inválida. Resultado: 5/5 checks correctos, cero timeouts/HTTP failures observados; el coverage block esperado no se contó como error del benchmark normal. Detalle: `reports/efficiency/robustness_checks.json`.

Qwen se mantuvo fuera del benchmark principal. La muestra complementaria de cinco casos TEST devolvió 5/5 recomendaciones Qwen, mediana GenAI 1136.04 ms y p95 7314.038 ms. Está separada en `reports/efficiency/genai_operational_sample.json`. Como referencia independiente, el benchmark oficial versionado de 30 casos está en `reports/genai/qwen3-8b-evaluation.json`; no se sobrescribió.

Gráficos generados con los datos medidos:

- `reports/efficiency/figures/latency_vs_batch_size.png`
- `reports/efficiency/figures/throughput_vs_batch_size.png`
- `reports/efficiency/figures/ms_per_project_vs_batch_size.png`
- `reports/efficiency/figures/sequential_vs_batch.png`

## Interpretación y límites

El resultado cuantifica capacidad operacional del proceso automatizado en un equipo local y dentro del límite de lote configurado (100). Batch reduce moderadamente el tiempo total frente a N requests secuenciales para N≥10; el tamaño del efecto se limita a esta API, artifact, máquina y ejecución. No se probó concurrencia, escalado horizontal, carga sostenida ni producción. El throughput teórico derivado de la mediana no equivale a una carga sostenida medida.

No se cronometra a personas, no hay baseline humano ni estudio controlado de usuarios; por tanto, no se afirma ahorro de tiempo, productividad humana o retorno de inversión. Una medición humana futura es opcional y necesitaría protocolo pareado, varios usuarios/casos, calidad de respuesta y condiciones registradas.

**Conclusión defendible:** PRUNIN demuestra eficiencia operacional reproducible mediante latencia, throughput y procesamiento batch sobre proyectos del TEST académico. Estas mediciones caracterizan el proceso automatizado en un entorno local; no representan productividad humana ni rendimiento productivo.