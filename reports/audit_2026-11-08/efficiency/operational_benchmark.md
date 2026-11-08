# Benchmark de eficiencia operacional

Estado: **complete**. Artifact: `0.9.0-academic`. Dataset: Mendeley Data 2p5sz57wh2 version 2.
HEAD medido: `bdc6f61c44e040c3c8ef694970c7252d8ec625bf`. Fecha UTC: 2026-11-08T15:31:38.423937+00:00.
Entorno observado: macOS-27.2-arm64-arm-64bit, Python 3.12.15, arquitectura arm64; API mode `academic`, workers no determinados por API.

Medición local end-to-end sobre TEST académico. `individual` son llamadas secuenciales sin recomendaciones; `batch` es una llamada CSV secuencial. No es prueba productiva ni productividad humana.

## Resultados

| N | Rep. | Individual mediana (ms) | Batch mediana (ms) | Speedup | Reducción | Throughput batch (proy/s; proy/min) | Batch ms/proyecto | Éxito individual/batch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 31.17 | 31.84 | 0.979× | -2.1% | 31.409; 1884.5 | 31.84 | 100.0% / 100.0% |
| 10 | 10 | 313.71 | 290.04 | 1.082× | 7.5% | 34.478; 2068.7 | 29.00 | 100.0% / 100.0% |
| 25 | 10 | 786.83 | 710.00 | 1.108× | 9.8% | 35.211; 2112.7 | 28.40 | 100.0% / 100.0% |
| 50 | 5 | 1556.96 | 1414.91 | 1.100× | 9.1% | 35.338; 2120.3 | 28.30 | 100.0% / 100.0% |
| 100 | 5 | 3029.48 | 2863.88 | 1.058× | 5.5% | 34.918; 2095.1 | 28.64 | 100.0% / 100.0% |

## Interpretación

- El batch alcanzó su mayor throughput medido en N=50 dentro de los tamaños probados; no se extrapola más allá de 100.
- Patrón de escalamiento local relativo a la referencia batch N=1: N=1: aproximadamente lineal respecto a la referencia local N=1; N=10: aproximadamente lineal respecto a la referencia local N=1; N=25: sublineal respecto a la referencia local N=1; N=50: sublineal respecto a la referencia local N=1; N=100: sublineal respecto a la referencia local N=1.
- Si el speedup es >1, se interpreta como menor overhead por agrupar proyectos en un endpoint secuencial, no como paralelización.
- GenAI estuvo apagada durante ambos modos. La latencia de ML+drivers en respuestas API se conserva separada del total; no se atribuye a Qwen.
- Chequeos de robustez: 5/5 pasan; se excluyeron del throughput normal.
- Muestra GenAI separada: estado `official_report_only`, éxito 96.7%, mediana 3092.64 ms, p95 6634.72 ms; no se mezcla con latencia batch.
- Esto mide eficiencia operacional del sistema en una laptop/API local. No demuestra productividad humana, ahorro laboral, escalabilidad productiva ni comportamiento bajo concurrencia.

## Variabilidad y percentiles

El JSON contiene media, mediana, p50, p90, p95, mínimo, máximo, desviación estándar, tasa de éxito/error, throughput y overhead cliente-servidor por modo y N.

## Gráficos

- `reports/audit_2026-11-08/efficiency/figures/latency_vs_batch_size.png`
- `reports/audit_2026-11-08/efficiency/figures/throughput_vs_batch_size.png`
- `reports/audit_2026-11-08/efficiency/figures/ms_per_project_vs_batch_size.png`
- `reports/audit_2026-11-08/efficiency/figures/sequential_vs_batch.png`

## Robustez

`reports/efficiency/robustness_checks.json` documenta input incompleto, cobertura bloqueada, categoría inválida, true_progress fuera de rango, error controlado por fila CSV y timeouts observados. Estos casos no forman parte de las repeticiones de throughput.
