# Benchmark de eficiencia operacional

Estado: **complete**. Artifact: `0.9.0-academic`. Dataset: Mendeley Data 2p5sz57wh2 version 2.
HEAD medido: `e0beff14db7eab98f19c20ea90a3b3f7e4deea6b`. Fecha UTC: 2026-10-11T22:43:47.255385+00:00.
Entorno observado: macOS-27.0.1-arm64-arm-64bit, Python 3.12.15, arquitectura arm64; API mode `configured`, workers no determinados por API.

Medición local end-to-end sobre TEST académico. `individual` son llamadas secuenciales sin recomendaciones; `batch` es una llamada CSV secuencial. No es prueba productiva ni productividad humana.

## Resultados

| N | Rep. | Individual mediana (ms) | Batch mediana (ms) | Speedup | Reducción | Throughput batch (proy/s; proy/min) | Batch ms/proyecto | Éxito individual/batch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 45.84 | 46.61 | 0.983× | -1.7% | 21.454; 1287.2 | 46.61 | 100.0% / 100.0% |
| 10 | 10 | 454.24 | 426.40 | 1.065× | 6.1% | 23.452; 1407.1 | 42.64 | 100.0% / 100.0% |
| 25 | 10 | 1138.24 | 1065.97 | 1.068× | 6.3% | 23.453; 1407.2 | 42.64 | 100.0% / 100.0% |
| 50 | 5 | 2265.70 | 2116.37 | 1.071× | 6.6% | 23.625; 1417.5 | 42.33 | 100.0% / 100.0% |
| 100 | 5 | 4440.90 | 4215.74 | 1.053× | 5.1% | 23.721; 1423.2 | 42.16 | 100.0% / 100.0% |

## Interpretación

- El batch alcanzó su mayor throughput medido en N=100 dentro de los tamaños probados; no se extrapola más allá de 100.
- Patrón de escalamiento local relativo a la referencia batch N=1: N=1: aproximadamente lineal respecto a la referencia local N=1; N=10: aproximadamente lineal respecto a la referencia local N=1; N=25: aproximadamente lineal respecto a la referencia local N=1; N=50: aproximadamente lineal respecto a la referencia local N=1; N=100: aproximadamente lineal respecto a la referencia local N=1.
- Si el speedup es >1, se interpreta como menor overhead por agrupar proyectos en un endpoint secuencial, no como paralelización.
- GenAI estuvo apagada durante ambos modos. La latencia de ML+drivers en respuestas API se conserva separada del total; no se atribuye a Qwen.
- Chequeos de robustez: 5/5 pasan; se excluyeron del throughput normal.
- Muestra GenAI separada: estado `complete`, éxito 100.0%, mediana 1136.04 ms, p95 7314.04 ms; no se mezcla con latencia batch.
- Esto mide eficiencia operacional del sistema en una laptop/API local. No demuestra productividad humana, ahorro laboral, escalabilidad productiva ni comportamiento bajo concurrencia.

## Variabilidad y percentiles

El JSON contiene media, mediana, p50, p90, p95, mínimo, máximo, desviación estándar, tasa de éxito/error, throughput y overhead cliente-servidor por modo y N.

## Gráficos

- `reports/efficiency/figures/latency_vs_batch_size.png`
- `reports/efficiency/figures/ms_per_project_vs_batch_size.png`
- `reports/efficiency/figures/sequential_vs_batch.png`
- `reports/efficiency/figures/throughput_vs_batch_size.png`

## Robustez

`reports/efficiency/robustness_checks.json` documenta input incompleto, cobertura bloqueada, categoría inválida, true_progress fuera de rango, error controlado por fila CSV y timeouts observados. Estos casos no forman parte de las repeticiones de throughput.
