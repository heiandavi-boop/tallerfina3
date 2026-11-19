# Benchmark técnico en proceso (ASGI)

Generado: 2026-11-19T00:13:13.292659+00:00 · commit `4ed4e7b28ae683e691938678e439acdbceb1d3d5` · modelo `0.9.0-academic` · macOS-27.2.1-arm64-arm-64bit

Mide la aplicación FastAPI y los modelos sin red ni servidor HTTP; no mide productividad humana ni escalabilidad de clúster.

| Escenario | Solicitudes | Éxitos | Fallos | p50 ms | p95 ms | Throughput |
|---|---:|---:|---:|---:|---:|---:|
| individual_1 | 1 | 1 | 0 | 41.313 | 41.313 | 24.2 req/s |
| individual_10 | 10 | 10 | 0 | 39.936 | 40.59 | 25.0 req/s |
| individual_50 | 50 | 50 | 0 | 40.275 | 43.966 | 24.38 req/s |
| individual_100 | 100 | 100 | 0 | 40.065 | 43.073 | 24.53 req/s |
| deterministic_recommendations_50 | 50 | 50 | 0 | 40.195 | 41.993 | 24.75 req/s |
| csv_10 | 3 | 3 | 0 | 395.851 | 423.902 | 25.26 filas/s |
| csv_50 | 3 | 3 | 0 | 1887.359 | 1900.15 | 26.49 filas/s |
| csv_100 | 3 | 3 | 0 | 3765.882 | 4000.616 | 26.55 filas/s |
| concurrency_1 | 100 | 100 | 0 | 43.713 | 49.266 | 22.78 req/s |
| concurrency_4 | 100 | 100 | 0 | 163.59 | 215.426 | 23.41 req/s |
| concurrency_8 | 100 | 100 | 0 | 318.572 | 388.665 | 24.6 req/s |
| concurrency_16 | 100 | 100 | 0 | 624.812 | 814.364 | 24.23 req/s |
| invalid_inputs | 3 | 2 | 1 | — | — | — |
| genai_timeout_fault_injection | 10 | 10 | 0 | 40.753 | 41.563 | — |

CSV de 100 filas frente a 100 solicitudes individuales: 3765.882 ms frente a 4077.417 ms (7.6 % menos tiempo de máquina).

Degradación por concurrencia (relativa a 1 worker): concurrency_1: p95×1.0, throughput×1.0; concurrency_4: p95×4.37, throughput×1.03; concurrency_8: p95×7.89, throughput×1.08; concurrency_16: p95×16.53, throughput×1.06

IA generativa en vivo: NO MEDIDA en esta ejecución: proveedores generativos no accesibles desde el entorno; ver reports/genai/provider_comparison_2026/.

Limitaciones: un solo proceso y una sola máquina; TestClient serializa parte del trabajo en el event loop; los valores no son extrapolables a un clúster.
