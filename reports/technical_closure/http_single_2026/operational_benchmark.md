# Benchmark de eficiencia operacional

Estado: **complete**. Artifact: `0.9.0-academic`. Dataset: Mendeley Data 2p5sz57wh2 version 2.
HEAD medido: `868ea86435bde7412bcee36c0ead821f289b694f`. Fecha UTC: 2026-11-19T01:29:48.928789+00:00.
Entorno observado: macOS-27.2.1-arm64-arm-64bit, Python 3.12.15, arquitectura arm64; API mode `configured`, workers no determinados por API.

Medición local end-to-end sobre TEST académico. `individual` son llamadas secuenciales sin recomendaciones; `batch` es una llamada CSV secuencial. No es prueba productiva ni productividad humana.

## Resultados

| N | Rep. | Individual mediana (ms) | Batch mediana (ms) | Speedup | Reducción | Throughput batch (proy/s; proy/min) | Batch ms/proyecto | Éxito individual/batch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 43.52 | 44.55 | 0.977× | -2.4% | 22.446; 1346.7 | 44.55 | 100.0% / 100.0% |
| 10 | 10 | 424.29 | 401.06 | 1.058× | 5.5% | 24.934; 1496.1 | 40.11 | 100.0% / 100.0% |
| 25 | 10 | 1052.62 | 994.87 | 1.058× | 5.5% | 25.129; 1507.7 | 39.79 | 100.0% / 100.0% |
| 50 | 5 | 2106.24 | 1980.56 | 1.063× | 6.0% | 25.245; 1514.7 | 39.61 | 100.0% / 100.0% |
| 100 | 5 | 4238.28 | 3979.90 | 1.065× | 6.1% | 25.126; 1507.6 | 39.80 | 100.0% / 100.0% |

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

- `reports/technical_closure/http_single_2026/figures/latency_vs_batch_size.png`
- `reports/technical_closure/http_single_2026/figures/throughput_vs_batch_size.png`
- `reports/technical_closure/http_single_2026/figures/ms_per_project_vs_batch_size.png`
- `reports/technical_closure/http_single_2026/figures/sequential_vs_batch.png`

## Robustez

`reports/efficiency/robustness_checks.json` documenta input incompleto, cobertura bloqueada, categoría inválida, true_progress fuera de rango, error controlado por fila CSV y timeouts observados. Estos casos no forman parte de las repeticiones de throughput.
