# PRUNIN AI Core

Prototipo académico reproducible para apoyar a directores de proyecto y oficinas de proyectos (PMO) en la interpretación del riesgo de retraso y sobrecosto. Predicciones y recomendaciones apoyan una decisión humana; no acreditan validación empresarial.

**Pregunta de investigación:** ¿En qué medida una arquitectura híbrida de inteligencia artificial, que combine modelos predictivos e IA generativa, permite detectar tempranamente riesgos de retraso y sobrecosto en proyectos y generar recomendaciones útiles para apoyar la toma de decisiones?

## Arquitectura

React/Vite → FastAPI → LightGBM (Health, Delay y Cost) → drivers de sensibilidad local → evidencia estructurada → proveedor seleccionable (Ollama/Qwen3 8B u OpenAI API) → validación de grounding → acciones priorizadas con justificación/seguimiento o fallback determinístico. [Diagramas y pipeline](docs/architecture.md).

La evidencia de recomendaciones distingue `model_driver`, `observed_operational_signal` y `heuristic_indicator`. Las reglas operativas [configuradas](configs/operational_signals.yaml) son heurísticas de revisión, no aprendidas por LightGBM. La ausencia de drivers positivos no descarta desviaciones de la entrada; una lista sin acciones exige ausencia de señales accionables y no equivale a ausencia de riesgo. Evidencia insuficiente y fallo generativo tienen estados separados. CSV solo genera recomendaciones al abrir una fila individual.

Final Status deriva de Health. Team Health es una **heurística operacional determinística**, no psicológica; la fusión 0.85/0.15 no está calibrada con outcomes reales. Qwen no predice Health/Delay/Cost; grounded_fallback no es GenAI. CSV y What-if no llaman al LLM.

## Historia del proyecto y fuentes

PRUNIN evolucionó mediante experimentos anteriores con datos sintéticos propios, enfoques PyTorch y entrenamiento temporal Long Horizon, según registros históricos del desarrollo. La documentación y los artefactos de esas versiones requieren recuperación para auditoría independiente; **no se presentan como entrenamiento de los LightGBM actuales**. Las fuentes externas Itemlet, Collaboration y SQuaD también se exploraron como complementarias, pero no se mezclaron con el conjunto académico. Ver [cronología, procedencia y niveles de evidencia](docs/project_evolution.md).

## Datos y features

Modelo: **0.9.0-academic**. Mendeley v2, DOI [10.17632/2p5sz57wh2.2](https://doi.org/10.17632/2p5sz57wh2.2): **dataset sintético externo publicado en Mendeley Data**. Resumen procesado: 4000 proyectos, 72549 snapshots. Split por project_id: 2800 TRAIN / 600 VALIDATION / 600 TEST, disjuntos.

Numéricas: planned_duration_weeks, planned_budget, true_progress, spi, cpi. Categóricas: project_type y methodology.

- project_type: construction, healthcare, it, manufacturing, marketing, r&d.
- methodology: agile, hybrid, kanban, scrum, waterfall.

No se mezclan fuentes independientes. Imputación ML por mediana/moda TRAIN; cobertura mínima API 60 %. true_progress solo tolera ruido flotante de 1e-9 en límites. Team Health no se imputa y necesita señales suficientes. La API puede emitir una advertencia OOD basada en perfil TRAIN; no cambia la predicción. [Model card](docs/model_card.md), [preparación](docs/training.md) y [drift/OOD](docs/drift_monitoring.md).

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

Benchmark Qwen3 8B histórico congelado: 30 casos, 29/30 aceptados; esquema/features válidas 30/30, una cifra no soportada; mediana 3092.645 ms y p95 6634.72 ms. La comparación OpenAI/Ollama del 19-11-2026 reutilizó 30 casos en modo controlado y operativo: Qwen3 8B logró 30/30 aceptadas en ambos, con mediana 8114.68 ms (p95 19783.22 ms) en el modo controlado. La repetibilidad de 5 casos × 3 dio respuestas idénticas. OpenAI no pudo medirse porque `OPENAI_API_KEY` no estaba disponible en el proceso; gasto real 0 USD, por lo que la comparación empírica sigue incompleta. Decisión organizativa provisional: conservar Ollama local como opción preferida cuando privacidad, operación sin red y ausencia de costo por token sean prioritarias; mantener OpenAI configurable sujeto a autorización, acceso y evaluación real, sin afirmar superioridad. El digest de Qwen y las condiciones están en el [reporte comparativo](reports/genai/provider_comparison_2026/comparison_report.md); los resultados históricos se conservan en [evaluación](docs/genai_evaluation.md) y la recomendación en [selección](docs/genai_model_selection.md).

Concurrencia local, 30 casos por nivel: éxito 96.67/93.33/73.33/36.67 % en 1/2/4/8; timeout 0/0/26.67/63.33 %; throughput 0.1335/0.1402/0.1475/0.2499 req/s. El mayor throughput viene con una caída marcada del éxito. No es prueba productiva ni demuestra escalabilidad. [Reporte](reports/genai/concurrency/report.md).

La sección de acciones convierte señales permitidas en tarjetas con prioridad, acción, justificación y seguimiento. Evaluación previa de acciones V3: 20 casos, `action_structure_valid_rate` y `follow_up_present_rate` 100 %, sin claims numéricos no soportados, timeouts o JSON inválido; mediana 7054.585 ms, p95 17741.41 ms. No mide utilidad humana. [Reporte y ejemplos](reports/genai/action_recommendations/README.md). La evaluación oficial Qwen anterior permanece intacta.

Revisión posterior `evidence-v2`: [ocho casos diagnósticos reales](reports/audit_2026-11-08/recommendations-evidence-v2-r2.json), 8/8 aceptados con procedencia; no es una muestra held-out ni reemplaza los benchmarks anteriores. La primera corrida fallida se conserva para trazabilidad. Los scripts de evaluación rechazan destinos existentes. Gemma/Ministral siguen ausentes; el tag futuro correcto es `ministral-3:8b`. No hay comparación empírica completa ni ganador demostrado.

[Cierre de cuatro brechas](reports/recommendations_closure_2026-11-08/README.md): CSV bancario → análisis individual → Qwen real → JSON descargado y comparado en Chrome; también fallback real por conexión fallida. Grounding contextual reforzado y 174 tests backend/21 frontend aprobados. Modelos y resultados científicos intactos. La descarga del navegador integrado de VS Code conserva una limitación documentada.

## Ejecutar y demostrar

Con entorno, frontend y artefactos preparados:

```bash
./scripts/preflight_demo.sh
./scripts/run_playground.sh
```

Abrir http://localhost:8000. El preflight esperado es `RESULTADO: LISTO PARA DEMO`. [Instalación, LAN/QR y detalle de la demo](docs/playground.md); [protocolo de demo](docs/DEMO_PROTOCOL.md). `frontend/dist/` se versiona para facilitar la sustentación offline. El repositorio no incluye los `.joblib` académicos ni datasets pesados; un clon requiere copiar artefactos aprobados localmente o reproducirlos según [docs/training.md](docs/training.md). Los reportes científicos sí permanecen versionados; `reports/closure/` contiene salidas internas de proceso y no forma parte de la entrega. La selección usa PRUNIN_ARTIFACT_DIR, luego artifacts/0.9.0-academic y después demo-0.1.0, rotulado como demo sintético.

Para activar GenAI local, con Ollama y qwen3:8b instalados:

```bash
PRUNIN_ENABLE_OLLAMA=1 PRUNIN_OLLAMA_MODEL=qwen3:8b ./scripts/run_playground.sh
```

Ejecutar `./scripts/preflight_genai.sh` por separado con Ollama y API activos. Si Ollama falla, ML y fallback permanecen disponibles. `/api/genai-status` muestra estado; timeout por defecto 30 s configurable. El benchmark comparativo y la concurrencia son scripts manuales; no descargan modelos y la prueba local no se llama productiva.

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

quality CI usa Python 3.12/Node 22, npm ci, frontend build/tests, artefactos demo efímeros, compileall y pytest; no descarga Mendeley ni ejecuta Ollama/benchmark pesado. CI verde se acredita por SHA y run completado. Docker empaqueta frontend/API; Kubernetes es [diseño validado estáticamente](deploy/k8s/prunin-ai-core.yaml), tres réplicas y HPA 3–10, sin clúster operado. El daemon Docker local tampoco estuvo disponible en la última auditoría; el CI de `main` construyó y ejecutó el smoke test. [MLOps](docs/mlops_production.md) incluye registro con estados diferenciados, reporte offline de drift invocable por CLI, readiness, monitoring y `/metrics`; no hay monitorización continua central ni retraining con datos reales. El registro no declara entorno de producción.

Benchmark HTTP académico local (19-11-2026): 100/100 respuestas correctas por nivel de concurrencia 1/4/8/16. Throughput 20.14/24.14/23.42/23.35 req/s; p95 80.98/200.88/457.41/954.38 ms. Hubo recuperación después de una entrada inválida controlada; no se detuvo ninguna instancia. Es una medición de un proceso en un equipo, no prueba de alta disponibilidad. [Reporte](reports/technical_closure/http_concurrency_2026/http_concurrency_summary.json), [auditoría técnica](reports/technical_closure/technical_audit.md).

Reproducción del entrenamiento: [docs/training.md](docs/training.md) y scripts/train_all.sh (fail-fast). Ejecutarla en entorno separado; no sobrescribir modelos/resultados congelados para preparar la entrega.

## Limitaciones

Dataset sintético, severidad Critical todavía limitada, Delay débil, caveat EVM de Cost, cobertura temprana desigual, fusión no calibrada y drivers no causales. No hay baseline humano medido ni validación prospectiva empresarial. Grounding es proxy y requiere revisión humana. La eficiencia del API no demuestra productividad humana; el [protocolo humano](docs/human_efficiency_validation.md), la [presentación](docs/PRESENTACION_FINAL.md) y la [matriz de evidencias orales](docs/ORAL_EVIDENCE.md) están documentados; la medición humana no se ha ejecutado. [Ética](docs/ethics_security.md). No está listo para producción.

## Estado de evaluación

- [Informe final](docs/INFORME_FINAL.md)
- [Auditoría local actual: informe A–F, pruebas e integridad](reports/audit_2026-11-08/README.md)
- [Revisión actual de 27 criterios y limitación de rúbrica oficial](reports/audit_2026-11-08/rubric_review.json)
- [Rúbrica institucional PAIII: 27 criterios, nivel 4 y brechas](docs/RUBRICA_OFICIAL_PAIII_2026.md)
- [Estado de cumplimiento, alcance y límites](docs/rubric_matrix.md)
- [Cierre, evidencias y pendientes](docs/FINAL_READINESS.md)
- [Matriz histórica previa de 27 criterios](reports/rubric_final/rubric_final.md)
- [Resultados predictivos congelados](reports/0.9.0-academic/)
- [Resultados GenAI](reports/genai/)
- [Contenido académico de la presentación](docs/PRESENTACION_FINAL.md)
- [Protocolo demostrable](docs/DEMO_PROTOCOL.md) y [evidencia de criterios orales](docs/ORAL_EVIDENCE.md)
- [Manifiesto de entrega](docs/DELIVERY_MANIFEST.md)
- [Referencias APA 7](docs/references.md)

## Selección de IA generativa: Ollama u OpenAI

La interfaz permite seleccionar **Ollama local**, **OpenAI mediante API** o **solo predicción** antes de cada análisis individual. OpenAI admite ingresar la clave en el formulario de sesión (solo memoria de la pestaña; no localStorage ni respuesta JSON) o configurar `OPENAI_API_KEY` como variable de entorno **del servidor**, sin almacenar el secreto en Git. El backend llama a `https://api.openai.com/v1/chat/completions`. El modelo predeterminado es `gpt-4.1`, pero su identificador se puede cambiar según modelos habilitados en la cuenta. No es necesario reiniciar PRUNIN para cambiar entre motores desde la UI.

La versión OpenAI admite hasta **8 acciones basadas en evidencia** y un resumen de **1.200 caracteres**, en lugar de 4 acciones y 180 caracteres de Ollama. Estos límites corresponden al formato de recomendaciones de PRUNIN, **no a las capacidades de razonamiento, contexto o modelos disponibles en la API OpenAI**. La API no equivale a la suscripción ChatGPT; se factura por consumo. Los guardrails de procedencia, validación y fallback permanecen habilitados. No se envía texto libre del proyecto al modelo generativo; se transmiten señales estructuradas y posibles datos de proyecto que figuren en la evidencia de inferencia. Si son sensibles, verificar la política de tratamiento de datos antes de usar OpenAI.

**Seguridad:** Solo enviar la clave desde `localhost` o una instancia HTTPS; no introducirla en una aplicación PRUNIN hospedada por un tercero no confiable. La clave viaja al backend como cabecera por solicitud y no se guarda en servidor. En producción, el API falla cerrado si no está configurado `PRUNIN_API_TOKEN` y rechaza CORS `*`. El límite OpenAI es por dirección IP par/minuto y por proceso/día: no coordina cuotas entre réplicas ni sustituye un límite de facturación. La bandera del servidor `PRUNIN_ENABLE_OLLAMA=0` no se puede anular con un encabezado del cliente. Para usuarios externos siguen siendo obligatorios HTTPS e identidad adecuada antes de despliegue productivo. `GET /api/genai-status` nunca devuelve la clave ni confirma créditos. Véase [guía de proveedores](docs/ai_providers.md) y [auditoría de seguridad](docs/ethics_security.md).
