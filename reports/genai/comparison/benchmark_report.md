# Benchmark comparativo de candidatos GenAI

Estado: `partial`. Casos por modelo: 30; temperatura: 0.1; timeout: 30.0 s.

Todas las llamadas usan los mismos snapshots TEST, evidencia, prompt, esquema JSON, validador y hardware dentro de esta ejecución. No se descargan modelos. El benchmark compara salidas explicativas, no predictores ni utilidad humana.

| Modelo | Estado | N | Éxito | Esquema | Grounded | Cifra no soportada | Acción | Timeout | JSON inválido | Mediana ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gemma3:4b | not_available | 0 | — | — | — | — | — | — | — | — | — |
| ministral:8b | not_available | 0 | — | — | — | — | — | — | — | — | — |
| qwen3:8b | complete | 30 | 0.967 | 0.967 | 0.967 | 0.000 | 0.967 | 0.000 | 0.033 | 6336.35 | 13340.74 |

Hardware registrado: `{"platform": "macOS-27.2-arm64-arm-64bit", "processor": "arm", "logical_cpu_count": 15, "python_version": "3.12.15"}`.

No interpretar resultados de una sola máquina como ranking universal. Un modelo no disponible se marca `not_available`; la comparación se considera parcial.
