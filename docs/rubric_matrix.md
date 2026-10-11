# Matriz de cumplimiento — Proyecto Aplicado III

Auditoría del cierre sobre main inicial `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`, confirmado contra remoto el 11 de octubre de 2026. La matriz no sustituye la rúbrica oficial ni asigna automáticamente Nivel 4; distingue evidencia implementada, evaluación local y diseño.

| Resultado / criterio | Exigencia | Evidencia | Estado | Riesgo pendiente |
|---|---|---|---|---|
| R6.1 Cr1 Problema/contexto | Problema y objetivo contextualizados | INFORME_FINAL.md §§3–7; README.md | CUMPLIDO ACADÉMICO | Validación empresarial pendiente |
| R6.1 Cr2 Elección GenAI | Justificar alternativas y elección | genai_model_selection.md; references.md | CUMPLIDO DOCUMENTAL | Comparación técnico-documental Qwen/Gemma/Ministral; sin benchmark comparativo empírico |
| R6.1 Cr3 Integración GenAI | Integración funcional trazable | src/prunin_ai/api/recommendations.py; tests/test_genai_grounding.py | CUMPLIDO ACADÉMICO | Disponibilidad local; revisión semántica humana |
| R6.1 Cr4 Evaluación GenAI | Medir e interpretar desempeño | reports/genai/qwen3-8b-evaluation.json; genai_evaluation.md | EVALUADO: complete, 30 casos | Grounding y actionability son proxies; muestra condicionada a drivers |
| R6.2 Cr5 Automatización | Automatizar tareas pertinentes | src/prunin_ai/api/app.py; frontend/src/components/CsvAnalyzer.jsx | CUMPLIDO ACADÉMICO | CSV y What-if no llaman Qwen |
| R6.2 Cr6 Eficiencia | Comparación cuantificable con proceso manual | scripts/benchmark_efficiency.py; efficiency_evaluation.md | PENDIENTE DE EVIDENCIA HUMANA | Medir 5 casos reales; latencia GenAI sola no prueba ahorro end-to-end |
| R6.2 Cr7 Ética | Riesgos y mitigaciones | ethics_security.md; tests/test_genai_grounding.py | CUMPLIDO DOCUMENTAL/TÉCNICO | Representatividad y revisión humana en entorno real |
| R6.2 Cr8 Documentación | Entrega escrita y trazabilidad | INFORME_FINAL.md; PRESENTACION_FINAL.md; model_card.md; FINAL_READINESS.md | CUMPLIDO ACADÉMICO | Revisión final y sustentación del autor |
| R7.1 Cr1 Preprocesamiento | Calidad y prevención de leakage | src/prunin_ai/data/audit.py; training/core.py; reports/0.9.0-academic/feature_manifest.json | CUMPLIDO ACADÉMICO | Proximidad temporal CPI/EVM; sintético externo |
| R7.1 Cr2 Herramientas | Selección y uso reproducible | requirements.txt; frontend/package-lock.json; references.md | CUMPLIDO ACADÉMICO | Dependencia de artefactos locales y runtime |
| R7.1 Cr3 Pipeline | Pipeline modular reproducible | scripts/train_all.sh; reports/0.9.0-academic/reproducibility.json | CUMPLIDO ACADÉMICO | No se reentrenó en el cierre; hashes preservados |
| R7.2 Cr4 Despliegue | Automatizar empaquetado y validación | Dockerfile.playground; .github/workflows/quality.yml; scripts/preflight_demo.sh | ARTEFACTOS IMPLEMENTADOS | Docker no probado en este cierre; sin despliegue cloud real |
| R7.2 Cr5 Escalabilidad/robustez | Probes, réplica y recuperación | deploy/k8s/prunin-ai-core.yaml; recommendations.py | DISEÑO + FALLBACK IMPLEMENTADO | Sin clúster ni prueba de carga; HPA requiere metrics-server |
| R7.2 Cr6 MLOps | Versionado, observabilidad y actualización | mlops_production.md; src/prunin_ai/api/monitoring.py; reports/0.9.0-academic/reproducibility.json | ACADÉMICO IMPLEMENTADO / PRODUCTIVO PARCIAL | Prometheus central, alertas, drift y retraining continuo pendientes |

Las rutas `src/`, `reports/`, `scripts/`, `deploy/` y `README.md` son relativas a raíz; los demás documentos están en `docs/`. Resultados académicos congelados: `reports/0.9.0-academic/`. GenAI está evaluado en estado `complete`; no está pendiente de su primera ejecución. La comparación entre tres LLM sigue siendo documental.

RA1: informe coherente, metodología, resultados, conclusiones, límites y referencias en `INFORME_FINAL.md`. RA2: guion de 12 diapositivas en `PRESENTACION_FINAL.md` y demostración en `DEMO_PRESENTACION.md`. El cierre técnico no reemplaza la medición humana exigida por Cr6 ni acredita producción.
