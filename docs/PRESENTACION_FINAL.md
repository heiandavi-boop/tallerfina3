# Presentación final — guion de 12 diapositivas

Proyecto Aplicado III · 0.9.0-academic. Speech sugerido de aproximadamente 30–60 segundos por diapositiva; ensayar y ajustar al ritmo del expositor. Los resultados provienen de JSON/CSV versionados. Las referencias APA están en `docs/references.md`.

## Slide 1. PRUNIN AI Core: problema y pregunta

- Interpretar señales de avance, cronograma y costo
- Estimar riesgo y comunicar evidencia trazable
- ¿Qué permite una arquitectura híbrida en un benchmark sintético?

**Evidencia que mostrar:** `docs/INFORME_FINAL.md §§3–7`.

**Visual recomendado:** Problema → pregunta → objetivo.

**Speech:** El proyecto aborda la interpretación conjunta de señales de ejecución para apoyar la priorización del riesgo. Nuestra pregunta es qué puede aportar una arquitectura híbrida reproducible para estimar resultados y explicar evidencia. El alcance es académico: no tenemos un estudio empresarial que cuantifique el problema. La propuesta combina modelos predictivos con explicación local y supervisión humana. Durante la presentación separaré resultados comprobados, reglas operacionales y tareas pendientes.

**Error que NO cometer:** Afirmar impacto empresarial medido o validación productiva.

## Slide 2. Arquitectura híbrida

- React/Vite → FastAPI → LightGBM
- Team Health y fusión: reglas heurísticas separadas
- Drivers → Qwen/Ollama → validador o fallback

**Evidencia que mostrar:** `src/prunin_ai/api/model_runtime.py; recommendations.py; inference/brain.py`.

**Visual recomendado:** Diagrama de flujo con predicción y explicación separadas.

**Speech:** La interfaz envía variables a FastAPI, que carga los pipelines LightGBM y produce las predicciones. Team Health se calcula con reglas observables; no es un modelo entrenado. Los drivers representan sensibilidad local. Qwen recibe evidencia estructurada y redacta una explicación; su respuesta debe superar un validador. Si falla, usamos respaldo determinístico y conservamos las predicciones. Esta separación facilita trazabilidad y evita confundir texto convincente con calidad predictiva.

**Error que NO cometer:** Decir que Qwen predice riesgo o que el fallback es GenAI.

## Slide 3. Dataset y metodología

- Mendeley Data v2: sintético externo; DOI 10.17632/2p5sz57wh2.2
- 4000 proyectos; 72549 snapshots
- Split por proyecto: 2800 / 600 / 600
- Whitelist e imputación aprendida en TRAIN

**Evidencia que mostrar:** `reports/0.9.0-academic/dataset_summary.json; feature_manifest.json; split_summary.json`.

**Visual recomendado:** Tres bloques disjuntos de proyectos.

**Speech:** Utilizamos un dataset sintético externo publicado en Mendeley Data. El resumen preparado registra cuatro mil proyectos y setenta y dos mil quinientos cuarenta y nueve snapshots. La división se hace por identificador de proyecto: todos sus snapshots quedan en un único conjunto. El preprocesamiento aprende en entrenamiento y excluye outcomes finales. Esto evita contaminación directa entre splits, aunque la naturaleza sintética y la proximidad temporal de EVM siguen siendo limitaciones.

**Error que NO cometer:** Llamar a Mendeley proyectos empresariales reales o decir que no queda ningún riesgo de leakage.

## Slide 4. Modelos predictivos

- Health: clasificación supervisada LightGBM
- Delay y Cost: regresiones LightGBM
- 7 features; Final Status deriva de Health
- Team Health: heurística operacional determinística

**Evidencia que mostrar:** `reports/0.9.0-academic/feature_manifest.json; src/prunin_ai/inference/brain.py`.

**Visual recomendado:** Tabla entradas → targets y reglas.

**Speech:** Health es clasificación supervisada. Delay estima días y Cost estima un ratio de sobrecosto, ambos por regresión. Usamos cinco variables numéricas y dos categóricas, registradas en el manifest. Final Status traduce Health a un estado de negocio; no entrenamos un clasificador redundante. Team Health necesita señales operacionales observadas y suficientes. El cierre conserva modelos, etiquetas y configuración del experimento, y diferencia el Delay crudo de su presentación operacional.

**Error que NO cometer:** Presentar Final Status o Team Health como modelos supervisados independientes.

## Slide 5. Resultados Health / Delay / Cost

- Health Macro F1: 0.627576 vs baseline 0.277940
- Health balanced accuracy: 0.682422; critical recall: 0.568182
- Delay MAE: 27.710468 vs 27.850313 días
- Cost MAE: 0.147158 pp; R²: 0.991816 (caveat EVM)

**Evidencia que mostrar:** `reports/0.9.0-academic/baselines.json; figures/baseline_comparison.png`.

**Visual recomendado:** Tabla project-level TEST con unidades explícitas.

**Speech:** Estas son métricas oficiales de seiscientos proyectos TEST usando el snapshot más reciente. Health mejora sobre el baseline cuando se considera Macro F1; accuracy sola ocultaría el desbalance. La detección crítica sigue incompleta. Delay es el resultado más débil: su mejora en MAE es marginal. Cost tiene desempeño interno muy alto, pero está relacionado en parte con la estructura CPI/EVM del generador sintético. Ninguno de estos valores acredita resultados en empresas reales.

**Error que NO cometer:** Confundir ratio con puntos porcentuales o ocultar la debilidad de Delay.

## Slide 6. Predicción temprana 20/40/60/80 %

- Macro F1: 0.397938 / 0.509355 / 0.522959 / 0.570588
- Proyectos elegibles: 236 / 463 / 576 / 599
- Cobertura al 20 %: 39.333 %
- Una observación por proyecto no posterior a cada cutoff

**Evidencia que mostrar:** `reports/0.9.0-academic/temporal_evaluation.csv; figures/temporal_health_macro_f1.png`.

**Visual recomendado:** Curva F1 con cobertura visible debajo.

**Speech:** Para examinar anticipación usamos observaciones que no superan cada nivel de avance. Health mejora al aumentar la información disponible. Sin embargo, al veinte por ciento solo doscientos treinta y seis proyectos tienen un snapshot elegible, aproximadamente treinta y nueve por ciento del TEST. La cobertura aumenta en los siguientes cortes. Por eso no presentamos la curva como evaluación de los mismos seiscientos proyectos completos ni como garantía de predicción temprana generalizable.

**Error que NO cometer:** Decir que todos los 600 proyectos fueron evaluados al 20 %.

## Slide 7. IA generativa Qwen3

- Qwen3 8B local vía Ollama
- Explica y recomienda sobre evidencia estructurada
- Selección técnico-documental frente a Gemma/Ministral
- Fallback determinístico cuando falla validación

**Evidencia que mostrar:** `docs/genai_model_selection.md; src/prunin_ai/api/recommendations.py`.

**Visual recomendado:** Evidencia → texto → controles.

**Speech:** Elegimos Qwen por encaje operativo con ejecución local, español, tamaño y Ollama. La elección frente a Gemma y Ministral se fundamentó documentalmente: no hicimos un benchmark comparativo de los tres. Qwen interpreta predicciones y drivers; no modifica Health, Delay ni Cost. La privacidad local es una ventaja operativa, aunque aún requiere controles de acceso en una implementación empresarial. El fallback permite mantener servicio sin afirmar generación cuando no la hubo.

**Error que NO cometer:** Afirmar superioridad empírica de Qwen frente a alternativas no evaluadas.

## Slide 8. Evaluación GenAI

- 30 casos; status=complete; 29/30 aceptados y grounded
- Schema/features/actionability: 1.0 (proxies)
- Cifra no soportada: 1/30; timeout/JSON inválido: 0
- Latencia mediana 3092.645 ms; p95 6634.72 ms

**Evidencia que mostrar:** `reports/genai/qwen3-8b-evaluation.json y CSV`.

**Visual recomendado:** Tarjetas de métricas y ejemplo de rechazo.

**Speech:** El benchmark real de Qwen está completado y versionado. Evaluó treinta snapshots TEST con al menos un driver de incremento del riesgo. Veintinueve respuestas fueron aceptadas y una introdujo una cifra no soportada. La validación estructural fue completa, pero eso no significa verdad semántica. Actionability exige texto de acción, no demuestra utilidad profesional. Los tiempos corresponden a la corrida local. Falta revisión humana ciega y no extrapolamos estos resultados a producción.

**Error que NO cometer:** Confundir grounding automático con ausencia total de alucinaciones.

## Slide 9. Demo y automatización

- Analizar preset: prediction_id y artefacto real
- What-if modifica variables usadas
- CSV: hasta 100 filas; Team Health según cobertura
- Delay operacional ≥ 0; valor crudo en detalle técnico

**Evidencia que mostrar:** `scripts/preflight_demo.sh; frontend; /api/schema y /api/predict`.

**Visual recomendado:** Demostración en vivo con drawer y CSV.

**Speech:** La demo ejecuta el artefacto cargado y registra una identificación de predicción. Mostraremos un análisis, un cambio de SPI o CPI y el procesamiento de un CSV. Si no hay señales de equipo suficientes, se oculta la columna Team Health del batch. Delay se presenta con mínimo cero y su valor crudo permanece en el detalle técnico; Cost negativo conserva ahorro. CSV y What-if no llaman al LLM. La automatización existe, pero el ahorro humano aún necesita cronometraje real.

**Error que NO cometer:** Cambiar una variable not_used y atribuirle efecto ML, o inventar ahorro de tiempo.

## Slide 10. Ética y MLOps

- Human-in-the-loop, privacidad y límites sintéticos
- Hashes, manifests, CI y prediction_id
- /api/ready, /api/monitoring, /metrics
- Docker implementado; Kubernetes es diseño

**Evidencia que mostrar:** `docs/ethics_security.md; mlops_production.md; deploy/k8s/prunin-ai-core.yaml; CI por commit`.

**Visual recomendado:** Dos columnas: implementado / diseñado y pendiente.

**Speech:** La trazabilidad combina versión, manifest, hashes y logs de predicción. Hay checks de CI y endpoints de observabilidad, con contadores locales por proceso. Docker empaqueta la aplicación y Kubernetes describe réplicas y HPA, pero no hay un clúster activo probado. La supervisión humana responde a errores predictivos y generativos, sesgos y representatividad. Las capacidades productivas pendientes incluyen métricas centralizadas, alertas, drift y validación con proyectos reales.

**Error que NO cometer:** Mostrar un workflow anterior como prueba del commit nuevo o afirmar Kubernetes desplegado.

## Slide 11. Limitaciones

- Datos sintéticos y cobertura temporal desigual
- Delay débil; Cost condicionado por estructura EVM
- Fusión no calibrada; drivers no causales
- Baseline humano y validación empresarial pendientes

**Evidencia que mostrar:** `docs/model_card.md; efficiency_evaluation.md; reports/experiments/delay/`.

**Visual recomendado:** Tabla límite → evidencia → próximo paso.

**Speech:** Las limitaciones son parte del resultado. Delay apenas supera la mediana; el experimento seleccionó la mediana en VALIDATION sin promoción automática y conservamos el modelo congelado. Cost necesita validación externa. La fusión de equipo no está calibrada y los drivers no son causas. Tampoco hay evidencia de ahorro humano. Una prueba manual adicional de noventa y nueve filas no reemplaza métricas oficiales sin resultados estructurados versionados. Estas restricciones delimitan lo que podemos defender.

**Error que NO cometer:** Presentar la prueba manual 99 como benchmark oficial o disimular pendientes.

## Slide 12. Conclusiones

- Prototipo híbrido reproducible y trazable
- Health supera baseline; GenAI local fue evaluado
- Limitaciones y pendientes documentados
- Cierre académico; validación real como siguiente etapa

**Evidencia que mostrar:** `docs/FINAL_READINESS.md; rubric_matrix.md; INFORME_FINAL.md`.

**Visual recomendado:** Tres resultados y dos pendientes principales.

**Speech:** Concluimos que PRUNIN integra predicción y explicación en un prototipo verificable. Health mejora la evaluación multiclase frente al baseline y la generación local fue medida con controles explícitos. También quedan limitaciones importantes: Delay, dependencia sintética del costo y ausencia de medición humana. El aporte es una base académica reproducible y una defensa honesta de su alcance. La etapa siguiente requiere proyectos reales y evidencia de utilidad, antes de considerar operación empresarial.

**Error que NO cometer:** Cerrar diciendo listo para producción o cumplimiento total automático de la rúbrica.
