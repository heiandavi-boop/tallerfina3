# Prueba local de concurrencia GenAI

**No es una prueba productiva ni acredita escalabilidad.**

Estado: `complete`. Modelo: `qwen3:8b`. Casos por nivel: 30. Timeout: 30.0 s.

| Concurrencia | Solicitudes | Éxito | Fallos | Timeout | Fallback | p50 ms | p95 ms | Throughput req/s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 0.967 | 1 | 0 | 0.033 | 6256.95 | 15337.88 | 0.133 |
| 2 | 30 | 0.933 | 2 | 0 | 0.067 | 12305.81 | 23252.48 | 0.140 |
| 4 | 30 | 0.733 | 8 | 8 | 0.267 | 28567.37 | 30003.31 | 0.147 |
| 8 | 30 | 0.367 | 19 | 19 | 0.633 | 30002.81 | 30005.73 | 0.250 |

Hardware: `{"platform": "macOS-27.2-arm64-arm-64bit", "processor": "arm", "logical_cpu_count": 15, "python_version": "3.12.15"}`.

Local concurrency check only; not a production load or scalability test.
