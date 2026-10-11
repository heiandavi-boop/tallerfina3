# 1. PRUNIN AI Core: prototipo híbrido reproducible para apoyo a la gestión de proyectos

Proyecto Aplicado III · versión académica 0.9.0-academic · cierre del 11 de octubre de 2026. Base revisada: main `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`. Las rutas de código y reportes son relativas a raíz. Este informe usa evidencia existente; las verificaciones de cierre se distinguen del experimento original.

## 2. Resumen ejecutivo

PRUNIN AI Core integra clasificación y regresión supervisadas con explicación generativa local para apoyar la gestión de riesgos de proyectos. La versión congelada `0.9.0-academic` se evalúa sobre un dataset sintético externo publicado en Mendeley Data. Health supera el baseline en Macro F1, Delay aporta una mejora marginal y Cost presenta desempeño interno alto condicionado por el generador EVM. Qwen3 8B fue evaluado en 30 casos con 29 respuestas aceptadas. El sistema dispone de API, interfaz, CSV, What-if y trazabilidad. No está validado con proyectos empresariales reales; el baseline humano de eficiencia permanece pendiente. El alcance defendible es un prototipo académico reproducible para entrega y sustentación.

## 3. Introducción

La gestión de proyectos requiere interpretar simultáneamente avance, cronograma y costos. PRUNIN propone convertir esas señales en estimaciones y recomendaciones revisables. Esta investigación aplicada separa la evaluación predictiva del apoyo textual y de las reglas operacionales, evitando atribuir a una capa resultados de otra.

## 4. Problema

La interpretación manual de indicadores puede dificultar la priorización de proyectos y la comunicación del riesgo. Se aborda la necesidad de una herramienta trazable que produzca estimaciones consistentes y explicaciones fundamentadas. No se dispone de un estudio empresarial que cuantifique la frecuencia del problema ni su costo: se plantea como problema de diseño académico, sin inventar observaciones de producción.

## 5. Pregunta de investigación

¿En qué medida una arquitectura híbrida de LightGBM y generación local fundamentada permite estimar y comunicar riesgo de proyectos de forma reproducible sobre un benchmark sintético externo, y cuáles son sus límites para anticipación y uso empresarial?

## 6. Objetivo general

Construir y evaluar un prototipo reproducible de apoyo a la gestión que estime Health, Delay y Cost a partir de snapshots y traduzca evidencia estructurada en recomendaciones trazables bajo supervisión humana.

## 7. Objetivos específicos

Preparar una fuente con procedencia verificable y separación por proyecto; evaluar modelos frente a baselines TRAIN; caracterizar predicción temporal y cobertura; integrar y evaluar generación local con validación; documentar automatización, riesgos y operación reproducible. Medir ahorro humano es un objetivo pendiente, no un resultado logrado.

## 8. Arquitectura propuesta

React/Vite envía entradas validadas a FastAPI. `ModelRuntime` carga manifest, configuración y pipelines LightGBM. `PruninAcademicBrain` devuelve predicciones crudas y calcula reglas operativas independientes. El runtime añade la política de presentación de Delay. Los drivers se calculan mediante perturbaciones hacia referencias. Qwen3 8B, vía Ollama, recibe evidencia estructurada y explica; un validador acepta o rechaza su salida. El fallback determinístico conserva disponibilidad. `/api/ready`, `/api/monitoring` y `/metrics` aportan observabilidad local. Evidencia: `src/prunin_ai/api/`, `inference/brain.py` y `frontend/src/`.

## 9. Dataset

Mendeley v2 (DOI `10.17632/2p5sz57wh2.2`) es un dataset sintético externo publicado en Mendeley Data. El resumen preparado versionado contiene 4000 proyectos y 72549 snapshots. No son proyectos empresariales reales de PRUNIN. La referencia de Hajihoseyni (2026) documenta la simulación. Itemlet, Collaboration y SQuaD son fuentes independientes y no se unieron al entrenamiento académico. Evidencia: `dataset_summary.json` y `docs/datasets.md`.

## 10. Preparación y calidad de datos

El adaptador `data/adapters/mendeley_evm.py` estandariza columnas, unidades e identificadores. La auditoría revisa cobertura, duplicados, calidad y outliers IQR; el pipeline imputa numéricas por mediana y categóricas por moda aprendidas en TRAIN, y codifica categorías con OneHotEncoder. No se inventan variables ausentes. La normalización no es necesaria para particiones de árboles. Las siete features académicas tienen cobertura completa en el resumen versionado; el contrato API bloquea entradas con cobertura inferior a 60 %. Team Health no recibe imputación.

## 11. Prevención de leakage

El split por `project_id` mantiene 2800 proyectos TRAIN, 600 VALIDATION y 600 TEST. Los snapshots de un proyecto permanecen juntos; `scripts/verify_split.py` comprueba conjuntos disjuntos. La whitelist excluye targets, costo y duración reales y outcomes finales. El ajuste del preprocesador usa TRAIN; la comparación de candidatos usa VALIDATION. TEST es evaluación descriptiva del candidato congelado. Esta separación evita leakage directo, pero no elimina la proximidad entre CPI/EVM tardío y outcome sintético. Evidencia: `split_summary.json`, manifest y reproducibility.

## 12. Ingeniería de características

Las numéricas son `planned_duration_weeks`, `planned_budget`, `true_progress`, `spi`, `cpi`; las categóricas, `project_type` y `methodology`. Tipos: construction, healthcare, it, manufacturing, marketing, r&d. Metodologías: agile, hybrid, kanban, scrum, waterfall. Las variables futuras del catálogo no se presentan como features entrenadas. Los drivers son sensibilidad local ante sustitución por una referencia, no efectos causales.

## 13. Modelos predictivos

Health es clasificación supervisada LightGBM; Delay y Cost son regresiones LightGBM. Se mantienen los artefactos y reglas de generación de etiquetas del experimento. Final Status deriva de Health: healthy → successful, at_risk → challenged, critical → critical; no es un cuarto modelo académico. Los baselines se ajustan sobre TRAIN: clase mayoritaria para Health y mediana por proyecto para regresión. Evidencia: `training/core.py`, `targets.py`, `baselines.json` y `feature_manifest.json`.

## 14. Evaluación de Health

| Evaluación TEST project-level (600 proyectos) | Modelo | Baseline TRAIN |
|---|---:|---:|
| Health accuracy | 0.7266666667 | 0.7150000000 |
| Health balanced accuracy | 0.6824223458 | 0.3333333333 |
| Health Macro F1 | 0.6275758334 | 0.2779397473 |
| Health critical recall | 0.5681818182 | 0 |
| Delay MAE (días) | 27.7104683426 | 27.8503125000 |
| Cost MAE (puntos porcentuales) | 0.1471578505 | 5.0974437328 |
| Cost R² | 0.9918156959 | -0.0080230304 |

Fuente: `reports/0.9.0-academic/baselines.json`, coherente con `metrics.json`. Health TEST tiene 429 at_risk, 44 critical y 127 healthy. La accuracy del baseline 0.715 resulta del desbalance: siempre predice at_risk. Macro F1 promedia F1 de las tres clases con igual peso y permite ver esa limitación. Critical recall 0.568182 implica errores relevantes de detección; el prototipo requiere criterio humano. Las métricas project-level usan el snapshot más reciente de cada proyecto, no demuestran por sí solas predicción temprana.

## 15. Evaluación de Delay

Delay es el modelo predictivo más débil: MAE TEST 27.710468 días frente a 27.850313 del baseline, mejora marginal de 0.139844 días. Su R² es 0.075305. El experimento versionado eligió la mediana según VALIDATION y deshabilitó promoción automática; no sustituyó el artefacto LightGBM. No se usó TEST para elegir ni se reentrenó durante el cierre.

La predicción de regresión cruda puede ser ligeramente negativa. La interfaz aplica una restricción operacional de cero días para presentación, conservando el valor crudo en la trazabilidad técnica.

El API conserva `delay_days` numérico como `max(0, delay_days_raw)` y añade `delay_days_raw`. CSV y What-if comparten el runtime; sus diferencias operacionales usan el campo mostrado. Los reportes académicos conservan regresión cruda y no fueron reescritos. No se trunca Cost negativo, que puede representar ahorro.

## 16. Evaluación de Cost

Cost alcanza MAE project-level TEST 0.147158 puntos porcentuales (ratio 0.001471579) y R² 0.991816. El desempeño muy alto está relacionado en parte con la relación estructural entre CPI/EVM y el outcome de costo en el generador sintético. No demuestra precisión empresarial ni ausencia de errores fuera de esa distribución. El desempeño temprano es menor; deben leerse ambos resultados conjuntamente.

## 17. Evaluación temporal

| Avance máximo | Proyectos TEST | Cobertura | Health Macro F1 | Delay MAE días | Cost MAE pp |
|---|---:|---:|---:|---:|---:|
| 20 % | 236/600 | 39.333 % | 0.397938 | 33.146183 | 3.136943 |
| 40 % | 463/600 | 77.167 % | 0.509355 | 30.406823 | 2.789373 |
| 60 % | 576/600 | 96.000 % | 0.522959 | 28.305607 | 2.143231 |
| 80 % | 599/600 | 99.833 % | 0.570588 | 27.522773 | 1.406718 |

Fuente: `temporal_evaluation.csv/json`. Para cada cutoff se toma como máximo una observación por proyecto TEST, no posterior al avance indicado. En 20 % solamente 236 proyectos tienen observación elegible; la cobertura 39.333 % impide afirmar evaluación de los 600 en ese corte. Health mejora conforme avanza el proyecto, pero sigue limitado en anticipación. Los grupos de cobertura cambian: no es una trayectoria pareada completa de los mismos 600.

## 18. Team Health

Es una heurística operacional determinística, no un modelo supervisado ni indicador psicológico. Usa utilización, capacidad, productividad, retrabajo, defectos, estabilidad y colaboración disponibles. Requiere al menos tres componentes válidos y cobertura ponderada ≥ 0.5 según configuración existente. No imputa faltantes. En batch se oculta toda la columna si ninguna fila tiene score calculable; si alguna lo tiene, la columna aparece y las filas sin score siguen sin valor. La fusión 0.85 ML / 0.15 Team Health es heurística no calibrada con outcomes reales y se distingue del Health supervisado.

## 19. IA generativa

Qwen3 8B corre localmente mediante Ollama y convierte predicciones y drivers en explicación y recomendaciones. No predice Health, Delay ni Cost. CSV y What-if ejecutan ML sin generación; la generación opcional pertenece al análisis individual. El fallback `grounded_fallback` es determinístico y no se etiqueta como IA generativa.

## 20. Selección de Qwen3 8B

Se conservó Qwen por ejecución local, soporte de español, tamaño y compatibilidad operativa con Ollama (Qwen Team, 2025). Gemma 3 4B y Ministral 3 8B se consideraron mediante documentación técnica oficial. No se ejecutó un benchmark comparativo PRUNIN entre los tres ni se afirma superioridad empírica de Qwen. El benchmark existente verifica únicamente Qwen en la configuración local usada.

## 21. Grounding y seguridad

El prompt restringe la respuesta a evidencia estructurada; el validador exige esquema JSON, features permitidas y ausencia de cifras nuevas no soportadas. Timeout, JSON inválido o evidencia no admitida activan fallback sin retirar la predicción ML. La trazabilidad distingue intento y uso GenAI, motor, error y tiempos. Groundedness es un proxy determinístico de ingeniería, no prueba de verdad semántica; una frase aceptada todavía puede ser incorrecta o poco útil. Se requiere revisión humana.

## 22. Resultados de evaluación GenAI

El reporte `reports/genai/qwen3-8b-evaluation.json` está `complete`, modelo `qwen3:8b`, artefacto `0.9.0-academic`, 30 casos evaluados. La unidad es el snapshot TEST más reciente con al menos un driver local de incremento de riesgo: una muestra condicionada, no todos los proyectos ni entradas arbitrarias.

| Indicador | Valor observado |
|---|---:|
| generation_success_rate | 0.9666666667 |
| schema_valid_rate | 1.0000000000 |
| evidence_feature_valid_rate | 1.0000000000 |
| grounded_response_rate | 0.9666666667 |
| actionability_rate | 1.0000000000 |
| unsupported_numeric_claim_rate | 0.0333333333 |
| timeout_rate | 0.0000000000 |
| invalid_json_rate | 0.0000000000 |
| latency_ms_median | 3092.6450000000 |
| latency_ms_p95 | 6634.7200000000 |

29 de 30 respuestas fueron aceptadas y una introdujo una afirmación numérica no soportada. Schema y features válidas no garantizan aceptación: grounding aplica restricciones adicionales. Actionability comprueba acciones no vacías, no eficacia profesional. Mediana y p95 corresponden a este equipo y corrida, sin extrapolación a producción. El benchmark no se repitió ni se alteró durante este cierre.

## 23. Automatización

El API valida y analiza proyectos, devuelve prediction_id, probabilidades y evidencia. CSV procesa hasta 100 filas con errores por fila; What-if compara escenarios y señala variables sin efecto ML. La interfaz separa features entrenadas, señales heurísticas y variables futuras. La automatización está demostrada funcionalmente por tests y preflight; no sustituye decisiones del director del proyecto.

## 24. Eficiencia

Existe latencia automática medida, pero no baseline humano real versionado. `docs/efficiency_evaluation.md` define cinco casos, cronometraje, tabla pendiente y cálculo de mediana. `scripts/benchmark_efficiency.py` acepta una mediana observada; sin ella ahorro y throughput gain quedan null. La mediana GenAI no incluye toda la tarea humana ni todo el API. Cr6 sigue pendiente de evidencia humana y no se declara mejora porcentual de productividad.

## 25. Ética y riesgos

Se documentan privacidad, alucinaciones, sesgo de automatización, representatividad sintética, leakage, drift y falsa causalidad. Ollama local reduce transferencia a terceros, pero no reemplaza controles de acceso y retención. La supervisión humana es obligatoria para decisiones de impacto. Team Health no debe usarse para evaluar salud mental ni individuos. La validación real es necesaria antes de recomendaciones empresariales de alto impacto. Evidencia: `docs/ethics_security.md`.

## 26. MLOps

La infraestructura académica incluye versionado, hashes SHA256, manifests, configuración resuelta, model card, CI, logs con prediction_id y endpoints de readiness/monitoring/métricas. Los contadores son en memoria por proceso. La política de actualización requiere datos aprobados, revisión de degradación y selección en VALIDATION. Prometheus centralizado, alertas reales, drift automático y retraining productivo continuo no están implementados como operación real.

## 27. Despliegue y escalabilidad

Dockerfile empaqueta frontend y API usando lockfile. El manifiesto Kubernetes define Deployment con tres réplicas, RollingUpdate, probes, requests/limits, Service y HPA mínimo 3/máximo 10. Es diseño desplegable; no un clúster activo ni una prueba de producción. Requiere imagen con artefactos, dominio y recursos adecuados, metrics-server para HPA y observabilidad central antes de operar. No se montó infraestructura ni se afirmó throughput bajo carga.

## 28. Limitaciones

Los datos son sintéticos, el desbalance afecta Health, la detección crítica es incompleta, Delay apenas mejora la mediana y Cost depende del generador EVM. La evaluación temprana tiene cobertura desigual. La fusión no está calibrada; drivers no son causales. El benchmark GenAI es pequeño y condicionado; sus validadores son proxies. No hay baseline humano, validación empresarial ni clúster productivo. La prueba manual balanceada de 99 filas comunicada por el autor no tiene resultados estructurados versionados identificados: no se incorpora como métrica oficial. Existe un test local de 99 filas que verifica contrato y cobertura, sin balance 33/33/33 garantizado.

## 29. Trabajo futuro

Medir los cinco casos humanos y revisar recomendaciones; obtener proyectos reales con outcomes bajo acuerdos de datos; validar temporalmente y externamente; calibrar fusión; estudiar Delay usando TRAIN/VALIDATION sin escoger por TEST; desplegar observabilidad central y probar carga antes de escalar. Son tareas futuras, sin experimentos ni funcionalidades nuevas durante este cierre.

## 30. Conclusiones

La evidencia respalda un prototipo académico reproducible de arquitectura híbrida, con Health superior al baseline en Macro F1 y explicación generativa local evaluada. No todas las salidas tienen igual solidez: Delay conserva una limitación explícita y Cost requiere la advertencia del generador sintético. La separación de ML, reglas operativas y GenAI permite una defensa trazable. El cierre conserva resultados, artefactos y split; el ahorro humano y la validez empresarial permanecen pendientes. El estado técnico de entrega y sus verificaciones se registra en `docs/FINAL_READINESS.md`.

## 31. Referencias

Hajihoseyni, R. (2026). *Simulated project risk and earned-value dataset: Project features, monthly PV/EV/AC time series and delay/cost outcomes* (Versión 2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/2p5sz57wh2.2

Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems, 30*. https://papers.nips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html

Qwen Team. (2025, 29 de abril). *Qwen3: Think deeper, act faster*. https://qwenlm.github.io/blog/qwen3/

Google DeepMind. (s. f.). *Gemma 3 model card*. Google AI for Developers. Recuperado el 11 de octubre de 2026, de https://ai.google.dev/gemma/docs/core/model_card_3

Mistral AI. (s. f.). *Ministral 3 8B*. Mistral Docs. Recuperado el 11 de octubre de 2026, de https://docs.mistral.ai/models/ministral-3-8b-25-12

Scikit-learn developers. (s. f.). *About us*. Recuperado el 11 de octubre de 2026, de https://scikit-learn.org/stable/about.html

The Kubernetes Authors. (s. f.). *Deployments*. Recuperado el 11 de octubre de 2026, de https://kubernetes.io/docs/concepts/workloads/controllers/deployment/

Verificación y alcance bibliográfico: `docs/references.md`. Evidencia experimental propia: `reports/0.9.0-academic/{dataset_summary,feature_manifest,metrics,baselines,temporal_evaluation,reproducibility}.json`, `reports/experiments/delay/comparison.json` y `reports/genai/qwen3-8b-evaluation.json`.
