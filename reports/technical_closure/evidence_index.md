# Índice de evidencia del cierre técnico

| Área | Evidencia | Interpretación |
|---|---|---|
| Evaluación del motor local | [Selección](../../docs/genai_model_selection.md), [respuestas Qwen](../genai/qwen_local_2026/README.md) | 30 casos en dos modos y 15 repeticiones; comparación exhaustiva local pendiente |
| HTTP individual/CSV | [`operational_benchmark.md`](http_single_2026/operational_benchmark.md), `operational_benchmark_summary.json`, `operational_benchmark_raw.csv` | Medición local de una instancia; no es productividad humana |
| HTTP concurrente | [`http_concurrency_summary.json`](http_concurrency_2026/http_concurrency_summary.json), `http_concurrency_raw.csv` | 100/100 respuestas por nivel; p95 aumenta y throughput se estabiliza |
| Robustez de entrada | [`robustness_checks.json`](http_single_2026/robustness_checks.json) | Errores de entrada controlados; no prueba de falla de instancia |
| Perfil de referencia | [`0.9.0-academic-train-profile.json`](../monitoring/profiles/0.9.0-academic-train-profile.json) | Estadísticos agregados de TRAIN; no contiene filas del dataset |
| Drift offline | [`drift-20261119T013516Z-8001fdc1.json`](drift_monitoring_2026/drift-20261119T013516Z-8001fdc1.json) | Comparación retrospectiva TRAIN/VALIDATION; no activa retraining |
| MLOps | [`model_registry.json`](../mlops/model_registry.json), [`README.md`](../mlops/README.md) | Esquema 2; demo separada; sin puntero productivo |
| Seguridad | [`test_summary.md`](test_summary.md), tests `tests/test_security_controls.py` | Fallo cerrado y bandera de proveedor cubiertos por pruebas |
| Integridad académica | [`scientific_integrity.json`](scientific_integrity.json) | SHA-256 del dataset, split, configuración, modelos y métricas |
| Cierre técnico | [`technical_audit.md`](technical_audit.md), [`technical_audit.json`](technical_audit.json) | Resumen verificable de resultados, límites y dependencias |

La evaluación local conserva exclusivamente respuestas reales del motor Qwen, separadas del experimento histórico congelado y de las pruebas HTTP. 
