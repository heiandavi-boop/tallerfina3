# Presentación final — 12 diapositivas

Audiencia: profesor/mentor, jurado técnico y responsables de proyectos. Mensaje central: prototipo reproducible con evidencia y límites claros. Los bullets son contenido de slide; el speech es apoyo para ensayo, no texto para leer en pantalla. Las citas completas están en references.md y las respuestas en PREGUNTAS_DEFENSA.md.

## Versiones de 7, 10 y 12 minutos

| Slide | 7 min (s) | 10 min (s) | 12 min (s) |
|---|---:|---:|---:|
| 1 | 25 | 35 | 40 |
| 2 | 25 | 35 | 40 |
| 3 | 30 | 40 | 45 |
| 4 | 35 | 45 | 55 |
| 5 | 30 | 40 | 50 |
| 6 | 55 | 80 | 100 |
| 7 | 40 | 60 | 75 |
| 8 | 50 | 80 | 90 |
| 9 | 60 | 90 | 110 |
| 10 | 25 | 35 | 45 |
| 11 | 25 | 30 | 35 |
| 12 | 20 | 30 | 35 |
| Total | 420 | 600 | 720 |

Son tiempos **planificados**, no tiempos humanos medidos ni evidencia de eficiencia. 7 minutos: decir idea central y cifras indispensables, una interacción demo. 10 minutos: añadir comparación con baseline y cobertura temporal, más un ejemplo generativo. 12 minutos: ampliar interpretación/guardrail y CSV/What-if, sin alargar infraestructura. Los discursos base son aproximadamente 30–60 s; recortar para 7 min y usar tiempos de interacción en 10/12. Ensayar con cronómetro y ajustar a instrucciones del profesor. Preguntas del jurado se gestionan fuera de estos totales si se permite.

El problema, método y resultados ocupan el centro; infraestructura es secundaria. Presentar primero interpretación y después mostrar fuente si se solicita.

## Slide 1. Problema y contexto

**Mensaje central:** Apoyar la decisión humana con evidencia trazable.

- Director de proyecto/PMO: interpretar avance, plazo y costo
- Priorizar atención y preguntas antes del cierre
- Predicción como apoyo; decisión humana

**Visual/gráfico:** Problema → usuario → decisión.

**Evidencia:** docs/INFORME_FINAL.md §§3–5

**Speech:** El proyecto parte de una necesidad de gestión: interpretar señales de avance, cronograma y costo para decidir dónde investigar riesgo. El usuario previsto es el director de proyecto o una PMO. PRUNIN propone un apoyo trazable antes del cierre, no sustituye la decisión humana. No tenemos una medición empresarial del costo del problema ni del retorno. La contribución se evalúa como prototipo académico con alcance explícito.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** La siguiente pregunta organiza cómo evaluaremos ese apoyo.

**Error que evitar:** Inventar impacto empresarial medido.

## Slide 2. Pregunta y objetivos

**Mensaje central:** La pregunta se evalúa parcialmente; utilidad requiere personas.

- Arquitectura híbrida para detectar retraso y sobrecosto
- Generar recomendaciones útiles como finalidad a validar
- Evaluar señal predictiva, anticipación y generación
- Objetivo: prototipo reproducible y trazable

**Visual/gráfico:** Pregunta → objetivo → evaluación.

**Evidencia:** docs/INFORME_FINAL.md §§6–9

**Speech:** Nuestra pregunta de investigación es: ¿En qué medida una arquitectura híbrida de inteligencia artificial, que combine modelos predictivos e IA generativa, permite detectar tempranamente riesgos de retraso y sobrecosto en proyectos y generar recomendaciones útiles para apoyar la toma de decisiones? El objetivo es construir y evaluar un prototipo reproducible. Medimos predicción y generación estructurada; la utilidad profesional y el ahorro humano aún requieren evidencia. Esto distingue la intención del trabajo de sus resultados demostrados.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Para responderla, necesitamos separar predicción y explicación.

**Error que evitar:** Dar por demostrada utilidad empresarial o eficiencia humana.

## Slide 3. Arquitectura híbrida

**Mensaje central:** Separar ML, heurística y explicación.

- React/Vite → FastAPI → LightGBM
- Team Health y fusión: reglas heurísticas separadas
- Drivers → Qwen/Ollama → validador o fallback

**Visual/gráfico:** Diagrama de flujo con predicción y explicación separadas..

**Evidencia:** src/prunin_ai/api/model_runtime.py; recommendations.py; inference/brain.py`.

**Speech:** La interfaz envía variables a FastAPI, que carga los pipelines LightGBM y produce las predicciones. Team Health se calcula con reglas observables; no es un modelo entrenado. Los drivers representan sensibilidad local. Qwen recibe evidencia estructurada y redacta una explicación; su respuesta debe superar un validador. Si falla, usamos respaldo determinístico y conservamos las predicciones. Esta separación facilita trazabilidad y evita confundir texto convincente con calidad predictiva.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Ese flujo depende de datos cuya procedencia debemos entender.

**Error que evitar:** Decir que Qwen predice riesgo o que el fallback es GenAI.

## Slide 4. Dataset y metodología

**Mensaje central:** Datos sintéticos y split disjunto delimitan la validez.

- Mendeley Data v2: sintético externo; DOI 10.17632/2p5sz57wh2.2
- 4000 proyectos; 72549 snapshots
- Split por proyecto: 2800 / 600 / 600
- Whitelist e imputación aprendida en TRAIN

**Visual/gráfico:** Tres bloques disjuntos de proyectos..

**Evidencia:** reports/0.9.0-academic/dataset_summary.json; feature_manifest.json; split_summary.json`.

**Speech:** Utilizamos un dataset sintético externo publicado en Mendeley Data. El resumen preparado registra cuatro mil proyectos y setenta y dos mil quinientos cuarenta y nueve snapshots. La división se hace por identificador de proyecto: todos sus snapshots quedan en un único conjunto. El preprocesamiento aprende en entrenamiento y excluye outcomes finales. Esto evita contaminación directa entre splits, aunque la naturaleza sintética y la proximidad temporal de EVM siguen siendo limitaciones.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Con esos datos definimos qué aprende cada modelo.

**Error que evitar:** Llamar a Mendeley proyectos empresariales reales o decir que no queda ningún riesgo de leakage.

## Slide 5. Modelos y reglas operacionales

**Mensaje central:** Tres modelos; Final Status y Team Health son reglas.

- Health: clasificación supervisada LightGBM
- Delay y Cost: regresiones LightGBM
- 7 features; Final Status deriva de Health
- Team Health: heurística operacional determinística

**Visual/gráfico:** Tabla entradas → targets y reglas..

**Evidencia:** reports/0.9.0-academic/feature_manifest.json; src/prunin_ai/inference/brain.py`.

**Speech:** Health es clasificación supervisada. Delay estima días y Cost estima un ratio de sobrecosto, ambos por regresión. Usamos cinco variables numéricas y dos categóricas, registradas en el manifest. Final Status traduce Health a un estado de negocio; no entrenamos un clasificador redundante. Team Health necesita señales operacionales observadas y suficientes. El cierre conserva modelos, etiquetas y configuración del experimento, y diferencia el Delay crudo de su presentación operacional.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Veamos los resultados y su comparación con referencias simples.

**Error que evitar:** Presentar Final Status o Team Health como modelos supervisados independientes.

## Slide 6. Resultados ML

**Mensaje central:** Health aporta señal; Delay y Cost requieren interpretación crítica.

- Health Macro F1: 0.627576 vs baseline 0.277940
- Health balanced accuracy: 0.682422; critical recall: 0.568182
- Delay MAE: 27.710468 vs 27.850313 días
- Cost MAE: 0.147158 pp; R²: 0.991816 (caveat EVM)

**Visual/gráfico:** Tabla project-level TEST con unidades explícitas..

**Evidencia:** reports/0.9.0-academic/baselines.json; figures/baseline_comparison.png`.

**Speech:** Estas son métricas oficiales de seiscientos proyectos TEST usando el snapshot más reciente. Health mejora sobre el baseline cuando se considera Macro F1; accuracy sola ocultaría el desbalance. La detección crítica sigue incompleta. Delay es el resultado más débil: su mejora en MAE es marginal. Cost tiene desempeño interno muy alto, pero está relacionado en parte con la estructura CPI/EVM del generador sintético. Ninguno de estos valores acredita resultados en empresas reales.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** El resultado tardío no basta: ahora revisaremos anticipación.

**Error que evitar:** Confundir ratio con puntos porcentuales o ocultar la debilidad de Delay.

## Slide 7. Evaluación temprana

**Mensaje central:** Mejora con avance, con cobertura desigual.

- Macro F1: 0.397938 / 0.509355 / 0.522959 / 0.570588
- Proyectos elegibles: 236 / 463 / 576 / 599
- Cobertura al 20 %: 39.333 %
- Una observación por proyecto no posterior a cada cutoff

**Visual/gráfico:** Curva F1 con cobertura visible debajo..

**Evidencia:** reports/0.9.0-academic/temporal_evaluation.csv; figures/temporal_health_macro_f1.png`.

**Speech:** Para examinar anticipación usamos observaciones que no superan cada nivel de avance. Health mejora al aumentar la información disponible. Sin embargo, al veinte por ciento solo doscientos treinta y seis proyectos tienen un snapshot elegible, aproximadamente treinta y nueve por ciento del TEST. La cobertura aumenta en los siguientes cortes. Por eso no presentamos la curva como evaluación de los mismos seiscientos proyectos completos ni como garantía de predicción temprana generalizable.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Además de predecir, necesitamos comunicar evidencia sin inventarla.

**Error que evitar:** Decir que todos los 600 proyectos fueron evaluados al 20 %.

## Slide 8. Qwen3 y evaluación GenAI

**Mensaje central:** Generación medida y guardrails, sin verdad semántica garantizada.

- Qwen3 8B/Ollama: explica; no predice outcomes
- Elección técnico-operativa, sin benchmark de tres modelos
- 30 casos: 29/30 aceptados/grounded; una cifra no soportada
- Mediana 3092.645 ms; p95 6634.72 ms; proxies

**Visual/gráfico:** Flujo GenAI y tarjeta con aceptadas/rechazada.

**Evidencia:** reports/genai/qwen3-8b-evaluation.json; docs/genai_evaluation.md

**Speech:** Qwen interpreta evidencia y redacta recomendaciones, mientras LightGBM mantiene la predicción. Se eligió por requisitos locales; no afirmamos que venció a Gemma o Ministral. En treinta casos, veintinueve respuestas fueron aceptadas y una fue rechazada por cifra no soportada. El rechazo muestra el guardrail funcionando. Schema y acciones no vacías no prueban verdad semántica ni utilidad profesional. La latencia es local y la revisión humana sigue siendo necesaria.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Veamos cómo esa separación aparece en la aplicación.

**Error que evitar:** Confundir grounding con verdad total, o fallback con generación.

## Slide 9. Demo y automatización

**Mensaje central:** Mostrar comportamiento real sin inventar ahorro humano.

- Analizar preset: prediction_id y artefacto real
- What-if modifica variables usadas
- CSV: hasta 100 filas; Team Health según cobertura
- 100 proyectos TEST: batch mediana 4.22 s vs 4.44 s individual secuencial
- Delay operacional ≥ 0; valor crudo en detalle técnico

**Visual/gráfico:** Demostración en vivo con drawer y CSV..

**Evidencia:** scripts/preflight_demo.sh; frontend; /api/schema y /api/predict`.

**Speech:** La demo ejecuta el artefacto cargado y registra una identificación de predicción. Mostraremos un análisis, un cambio de SPI o CPI y el procesamiento de un CSV. Si no hay señales de equipo suficientes, se oculta la columna Team Health del batch. Delay se presenta con mínimo cero y su valor crudo permanece en el detalle técnico; Cost negativo conserva ahorro. CSV y What-if no llaman al LLM. En una prueba local reproducible de cien proyectos TEST, la mediana batch fue 4.22 segundos frente a 4.44 segundos con requests individuales secuenciales. Esto mide eficiencia operacional de esta configuración, no ahorro ni productividad humana ni rendimiento productivo.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** La demostración requiere trazabilidad y revisión responsable.

**Error que evitar:** Cambiar una variable not_used y atribuirle efecto ML, o inventar ahorro de tiempo.

## Slide 10. Ética y MLOps

**Mensaje central:** Observabilidad académica y diseño no equivalen a producción.

- Human-in-the-loop, privacidad y límites sintéticos
- Hashes, manifests, CI y prediction_id
- /api/ready, /api/monitoring, /metrics
- Docker implementado; Kubernetes es diseño

**Visual/gráfico:** Dos columnas: implementado / diseñado y pendiente..

**Evidencia:** docs/ethics_security.md; mlops_production.md; deploy/k8s/prunin-ai-core.yaml; CI por commit`.

**Speech:** La trazabilidad combina versión, manifest, hashes y logs de predicción. Hay checks de CI y endpoints de observabilidad, con contadores locales por proceso. Docker empaqueta la aplicación y Kubernetes describe réplicas y HPA, pero no hay un clúster activo probado. La supervisión humana responde a errores predictivos y generativos, sesgos y representatividad. Las capacidades productivas pendientes incluyen métricas centralizadas, alertas, drift y validación con proyectos reales.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Antes de concluir, delimitemos lo que la evidencia no demuestra.

**Error que evitar:** Mostrar un workflow anterior como prueba del commit nuevo o afirmar Kubernetes desplegado.

## Slide 11. Limitaciones

**Mensaje central:** Reconocer límites es parte del rigor.

- Datos sintéticos y cobertura temporal desigual
- Delay débil; Cost condicionado por estructura EVM
- Fusión no calibrada; drivers no causales
- Throughput local medido; sin carga productiva ni baseline humano

**Visual/gráfico:** Tabla límite → evidencia → próximo paso..

**Evidencia:** docs/model_card.md; efficiency_evaluation.md; reports/experiments/delay/`.

**Speech:** Las limitaciones son parte del resultado. Delay apenas supera la mediana; el experimento seleccionó la mediana en VALIDATION sin promoción automática y conservamos el modelo congelado. Cost necesita validación externa. La fusión de equipo no está calibrada y los drivers no son causas. Tampoco hay evidencia de ahorro humano. Una prueba manual adicional de noventa y nueve filas no reemplaza métricas oficiales sin resultados estructurados versionados. Estas restricciones delimitan lo que podemos defender.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Con esos límites, podemos formular la conclusión defendible.

**Error que evitar:** Presentar la prueba manual 99 como benchmark oficial o disimular pendientes.

## Slide 12. Conclusión

**Mensaje central:** Prototipo académico reproducible; validación real pendiente.

- Prototipo híbrido reproducible y trazable
- Health supera baseline; GenAI local fue evaluado
- Limitaciones y pendientes documentados
- Cierre académico; validación real como siguiente etapa

**Visual/gráfico:** Tres resultados y dos pendientes principales..

**Evidencia:** docs/FINAL_READINESS.md; rubric_matrix.md; INFORME_FINAL.md`.

**Speech:** Concluimos que PRUNIN integra predicción y explicación en un prototipo verificable. Health mejora la evaluación multiclase frente al baseline y la generación local fue medida con controles explícitos. La eficiencia operacional local también se midió con requests individuales y batch; no hicimos un estudio controlado de productividad humana ni una prueba productiva. Persisten limitaciones en Delay y en la dependencia sintética del costo. El aporte es una base académica reproducible y una defensa honesta de su alcance. La etapa siguiente requiere proyectos reales y evidencia de utilidad, antes de considerar operación empresarial.

**Detalle secundario:** rutas de código, parámetros y JSON solo si el jurado los pide.

**Transición:** Abrimos preguntas y respondemos con evidencia, sin improvisar métricas.

**Error que evitar:** Cerrar diciendo listo para producción o cumplimiento total automático de la rúbrica.

## Recursos de apoyo y demostración

Mostrar diagramas de architecture.md; matriz de confusión y temporal en reports/0.9.0-academic/figures; Playground con resultado individual, probabilities y drawer; Qwen o fallback rotulado; CSV/What-if; run CI del commit de entrega completado success. Mostrar /metrics o monitoring brevemente, sin convertir contadores locales en operación distribuida.

Las figuras existentes provienen de reportes reales; enseñar cobertura junto a la curva temporal. Feature importance puede quedar en reserva si preguntan: es importancia del modelo, no causalidad. Si Mermaid no se renderiza en el medio elegido, comprobar/exportar el diagrama durante preparación sin cambiar el flujo. Evitar terminales prolongadas, código largo y JSON sin una pregunta concreta.

## RA2 F4. Checklist de técnicas vocales — requiere práctica humana

- [ ] Ensayar velocidad comprensible y pausas entre ideas.
- [ ] Volumen audible; probar micrófono si corresponde.
- [ ] Evitar muletillas y leer la pantalla.
- [ ] Enfatizar Macro F1, limitación Delay y cobertura 20 %.
- [ ] Respirar antes de cambios de sección.
- [ ] Medir tiempo por slide y total con cronómetro.

## RA2 F6. Checklist de lenguaje no verbal — pendiente de ensayo humano

- [ ] Mantener contacto visual con el jurado.
- [ ] Postura estable y gestos al servicio del argumento.
- [ ] Movimientos moderados; no dar la espalda al explicar.
- [ ] No leer el informe ni la pantalla continuamente.
- [ ] Usar puntero solo para una cifra o relación concreta.
- [ ] Ensayar la interacción con computador sin perder contacto visual.

## Registro humano pendiente

| Ensayo | Duración real | Observaciones de voz/postura/argumentación |
|---|---|---|
| 7 minutos | PENDIENTE | |
| 10 minutos | PENDIENTE | |
| 12 minutos | PENDIENTE | |

La documentación prepara RA2 F1/F2/F3/F5/F7; no acredita su ejecución oral. Voz y lenguaje no verbal no pueden demostrarse mediante CI. Completar identidad institucional de la portada, verificar legibilidad/proyección y hacer ensayo con preguntas difíciles antes de entregar/sustentar.
