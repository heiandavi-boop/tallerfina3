# Matriz de cumplimiento — Proyecto Aplicado III

Esta matriz enlaza cada criterio de la rúbrica con evidencia verificable del repositorio. No sustituye la rúbrica oficial.

| Resultado / criterio | Evidencia actual | Estado | Evidencia principal |
|---|---|---|---|
| R6.1 Cr1 Problema/contexto | PRUNIN estima riesgo temprano de Health, Delay y Cost y genera apoyo accionable para gestión de proyectos | Cumplido | README, docs/model_card.md, reports/0.9.0-academic/experiment_summary.md |
| R6.1 Cr2 Elección GenAI | Comparación Qwen3 8B vs Gemma 3 4B vs Ministral 3 8B y decisión alineada a privacidad/local/español | Cumplido documentalmente; benchmark específico pendiente de ejecutar | docs/genai_model_selection.md |
| R6.1 Cr3 Integración GenAI | Ollama recibe exclusivamente predicción + drivers estructurados; validación de grounding + fallback | Cumplido | src/prunin_ai/api/recommendations.py |
| R6.1 Cr4 Evaluación GenAI | Benchmark reproducible de schema, grounding, actionability, cifras no soportadas y latencia | Implementado; resultados dependen de ejecutar Ollama local | scripts/evaluate_genai.py, docs/genai_evaluation.md |
| R6.2 Cr5 Tareas automatizables | Automatiza interpretación/resumen/recomendación sin delegar la decisión final | Cumplido | recommendations.py, docs/genai_evaluation.md |
| R6.2 Cr6 Eficiencia | Latencia automática y script para comparar contra tiempo humano medido | Parcial hasta medir baseline humano real | scripts/benchmark_efficiency.py |
| R6.2 Cr7 Ética | Matriz de alucinación, privacidad, sesgo, leakage, causalidad, disponibilidad, drift y mitigaciones | Cumplido documental/técnico | docs/ethics_security.md |
| R6.2 Cr8 Documentación | README + arquitectura + dataset + entrenamiento + model card + GenAI + MLOps + reports | Cumplido | docs/ y reports/ |
| R7.1 Cr1 Preprocesamiento | validación, imputación, encoding, coverage, hash y ahora detección IQR de outliers; normalización justificada como no necesaria para LightGBM | Cumplido | src/prunin_ai/data/audit.py, training/core.py |
| R7.1 Cr2 Herramientas | pandas/sklearn/LightGBM/FastAPI/React/Docker/GitHub Actions/Ollama | Cumplido | requirements.txt, README |
| R7.1 Cr3 Pipeline | pipeline modular, fail-fast y reproducible de descarga a preflight | Cumplido | scripts/train_all.sh |
| R7.2 Cr4 Automatización despliegue | Docker, CI, health/readiness, monitoring, metrics y manifiesto K8s | Cumplido como artefacto desplegable; no afirmar clúster productivo activo | Dockerfile.playground, deploy/k8s/, .github/workflows/quality.yml |
| R7.2 Cr5 Escalabilidad/robustez | 3 replicas, Service, probes, rolling update, HPA; fallback GenAI | Cumplido a nivel de diseño reproducible | deploy/k8s/prunin-ai-core.yaml |
| R7.2 Cr6 MLOps | versionado, SHA, manifests, logging, monitoring, CI y política de actualización/retraining | Cumplido salvo retraining continuo real con PRUNIN, que requiere datos productivos | docs/mlops_production.md |

## Comunicación escrita

Para RA1 la entrega debe mantener:

1. problema y contexto;
2. metodología;
3. resultados diferenciando datos sintéticos de validación real;
4. conclusiones ligadas a los resultados;
5. limitaciones;
6. referencias bibliográficas pertinentes.

Las fuentes públicas principales están registradas en `docs/datasets.md` y `docs/genai_model_selection.md`.

## Comunicación oral

Para RA2 usar la secuencia de `DEMO_PRESENTACION.md` y no improvisar métricas. Las respuestas deben apoyarse en `reports/0.9.0-academic/`.

## Dos evidencias que todavía requieren ejecución humana/local

### Benchmark GenAI

```bash
PRUNIN_ENABLE_OLLAMA=1 PRUNIN_OLLAMA_MODEL=qwen3:8b \
python scripts/evaluate_genai.py --cases 30
```

No declarar porcentajes de grounding/calidad si este reporte no está en estado `complete`.

### Eficiencia frente a proceso humano

Medir una muestra real de tiempo manual para interpretar un proyecto y redactar una recomendación. Luego:

```bash
python scripts/benchmark_efficiency.py --manual-seconds-per-case <SEGUNDOS_MEDIDOS>
```

No inventar el baseline humano.
