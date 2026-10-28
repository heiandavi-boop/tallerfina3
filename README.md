# PRUNIN AI Core

Prototipo académico reproducible para apoyar a directores de proyecto y oficinas de proyectos (PMO) en la interpretación del riesgo de retraso y sobrecosto. Predicciones y recomendaciones apoyan una decisión humana; no acreditan validación empresarial.

**Pregunta de investigación:** ¿En qué medida una arquitectura híbrida de inteligencia artificial, que combine modelos predictivos e IA generativa, permite detectar tempranamente riesgos de retraso y sobrecosto en proyectos y generar recomendaciones útiles para apoyar la toma de decisiones?

## Arquitectura

React/Vite → FastAPI → LightGBM (Health, Delay y Cost) → drivers de sensibilidad local → evidencia estructurada → Qwen3 8B/Ollama opcional → validación de grounding → explicación/recomendación o fallback determinístico. [Diagramas y pipeline](docs/architecture.md).

Final Status deriva de Health. Team Health es una **heurística operacional determinística**, no psicológica; la fusión 0.85/0.15 no está calibrada con outcomes reales. Qwen no predice Health/Delay/Cost; grounded_fallback no es GenAI. CSV y What-if no llaman al LLM.

## Datos y features

Modelo: **0.9.0-academic**. Mendeley v2, DOI [10.17632/2p5sz57wh2.2](https://doi.org/10.17632/2p5sz57wh2.2): **dataset sintético externo publicado en Mendeley Data**. Resumen procesado: 4000 proyectos, 72549 snapshots. Split por project_id: 2800 TRAIN / 600 VALIDATION / 600 TEST, disjuntos.

Numéricas: planned_duration_weeks, planned_budget, true_progress, spi, cpi. Categóricas: project_type y methodology.

- project_type: construction, healthcare, it, manufacturing, marketing, r&d.
- methodology: agile, hybrid, kanban, scrum, waterfall.

No se mezclan fuentes independientes. Imputación ML por mediana/moda TRAIN; cobertura mínima API 60 %. true_progress solo tolera ruido flotante de 1e-9 en límites. Team Health no se imputa y necesita señales suficientes. [Model card](docs/model_card.md) y [preparación](docs/training.md).

## Resultados clave

TEST por proyecto, 600 proyectos usando el snapshot más reciente: Health accuracy 0.726667, balanced accuracy 0.682422, Macro F1 0.627576 y critical recall 0.568182; baseline Macro F1 0.277940. Accuracy sola oculta desbalance.

### KPI de la promesa original — Risk Alert

La meta inicial se evalúa como **detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo**. Sin cambiar el modelo, la vista operacional agrupa `At Risk + Critical` como **Risk Alert** y conserva `Healthy` como **No Alert**.

| Corte | Cobertura TEST | Recall entre riesgos elegibles | Proyectos finales en riesgo ya detectados |
|---:|---:|---:|---:|
| 20 % | 39.33 % | 71.05 % | 28.54 % |
| 40 % | 77.17 % | 79.95 % | 64.06 % |
| 60 % | 96.00 % | 78.73 % | **75.90 %** |
| 80 % | 99.83 % | 79.92 % | 79.92 % |
| Final | 100 % | 82.45 % | 82.45 % |

El denominador estricto de la última columna son los **473 proyectos TEST que finalmente son At Risk o Critical**; los proyectos sin snapshot elegible en un corte cuentan como todavía no detectados. El primer corte pre-cierre que supera la meta es **60 % de avance: 359/473 = 75.90 %**, con 576/600 proyectos cubiertos. El recall exacto de la clase Critical permanece separado en 56.82 %.

Evidencia reproducible: [reporte](reports/promise_validation/promise_validation_report.md), [JSON](reports/promise_validation/risk_alert_metrics.json), [CSV temporal](reports/promise_validation/temporal_risk_alert_metrics.csv) y [figura](reports/promise_validation/figures/risk_alert_detection_vs_progress.svg).

Delay MAE 27.710468 frente a 27.850313 días: mejora marginal y componente predictivo más débil. Cost MAE 0.147158 puntos porcentuales y R² 0.991816, relacionado en parte con la estructura CPI/progreso–outcome del generador EVM sintético. Al 20 % de avance la cobertura TEST es solo 236/600 (39.333 %). [Resultados e interpretación](docs/INFORME_FINAL.md).

## GenAI

Benchmark Qwen3 8B versionado: complete, 30 casos, éxito/grounding 29/30, esquema/features válidas 30/30, acciones no vacías 30/30, una cifra no soportada; timeout/JSON inválido cero. Mediana 3092.645 ms y p95 6634.72 ms. Son proxies locales y muestra condicionada a drivers, no utilidad empresarial demostrada. Selección de Qwen frente a Gemma/Ministral técnico-operativa; sin benchmark empírico comparativo. [Selección](docs/genai_model_selection.md), [evaluación](docs/genai_evaluation.md) y [eficiencia pendiente](docs/efficiency_evaluation.md).

## Ejecutar y demostrar

Con entorno, frontend y artefactos preparados:

```bash
./scripts/preflight_demo.sh
./scripts/run_playground.sh
```

Abrir http://localhost:8000. El preflight esperado es `RESULTADO: LISTO PARA DEMO`. [Instalación, LAN/QR y detalle de la demo](docs/playground.md); [guion](DEMO_PRESENTACION.md). Un clon no incluye modelos pesados ni datasets; verificar los artefactos oficiales locales para sustentar. La selección usa PRUNIN_ARTIFACT_DIR, luego artifacts/0.9.0-academic y después demo-0.1.0, rotulado como demo sintético.

Para activar GenAI local, con Ollama y qwen3:8b instalados:

```bash
PRUNIN_ENABLE_OLLAMA=1 PRUNIN_OLLAMA_MODEL=qwen3:8b ./scripts/run_playground.sh
```

Ejecutar `./scripts/preflight_genai.sh` por separado con el API activo. Si Ollama falla, ML y fallback permanecen disponibles. `/api/genai-status` muestra estado; timeout por defecto 30 s configurable. No reejecutar el benchmark oficial durante el cierre.

Demo: análisis individual, probabilidades, drivers, What-if, CSV hasta 100 filas, JSON descargable con prediction_id y versión. Delay presenta `max(0, delay_days_raw)` y conserva raw en detalle técnico; métricas históricas no cambian. Cost negativo puede representar ahorro. Team Health del CSV se oculta si ninguna fila tiene score, aparece si alguna lo tiene.

## Validación y operación

```bash
source .venv/bin/activate
python -m pip check
python -m compileall -q src scripts tests
PYTHONPATH=src python -m pytest -q
npm ci --prefix frontend
npm test --prefix frontend -- --run
npm run build --prefix frontend
./scripts/preflight_demo.sh
```

quality CI usa Python 3.12/Node 22, npm ci, frontend build/tests, artefactos demo efímeros, compileall y pytest; no descarga Mendeley ni ejecuta Ollama/benchmark pesado. CI verde se acredita por SHA y run completado. Docker empaqueta frontend/API; Kubernetes es [diseño](deploy/k8s/prunin-ai-core.yaml), tres réplicas y HPA 3–10, sin clúster productivo probado. [MLOps](docs/mlops_production.md) expone readiness, monitoring y /metrics; centralización, drift y retraining continuo siguen pendientes.

Reproducción del entrenamiento: [docs/training.md](docs/training.md) y scripts/train_all.sh (fail-fast). Ejecutarla en entorno separado; no sobrescribir modelos/resultados congelados para preparar la entrega.

## Limitaciones

Dataset sintético, severidad Critical todavía limitada, Delay débil, caveat EVM de Cost, cobertura temprana desigual, fusión no calibrada y drivers no causales. No hay baseline humano medido ni validación prospectiva empresarial. Grounding es proxy y requiere revisión humana. [Ética](docs/ethics_security.md). No está listo para producción.

## Estado de evaluación

- [Informe final](docs/INFORME_FINAL.md)
- [Matriz completa PAIII: técnica, RA1 y RA2](docs/rubric_matrix.md)
- [Cierre, evidencias y pendientes](docs/FINAL_READINESS.md)
- [Resultados predictivos congelados](reports/0.9.0-academic/)
- [Resultados GenAI](reports/genai/)
- [Presentación de 7/10/12 minutos](docs/PRESENTACION_FINAL.md)
- [Preguntas de defensa](docs/PREGUNTAS_DEFENSA.md) y [glosario](docs/GLOSARIO_DEFENSA.md)
- [Referencias APA 7](docs/references.md)
