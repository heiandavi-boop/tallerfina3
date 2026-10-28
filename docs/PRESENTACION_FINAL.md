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

## Slide 2. Pregunta, promesa y criterio de éxito

**Mensaje central:** La defensa se evalúa contra la promesa original.

- Anticipar riesgos de retraso y sobrecosto antes del cierre
- Apoyar la toma de decisiones del director/PMO
- Meta original: detectar ≥75 % de proyectos **Critical o At Risk**
- Separar alerta de riesgo de clasificación exacta de severidad

**Visual/gráfico:** Promesa → KPI → evidencia temporal.

**Evidencia:** docs/INFORME_FINAL.md §§6–8 y reports/promise_validation/

**Speech:** La promesa original no era clasificar exactamente el 75 % de los Critical. Era detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo. Por eso formalizamos un KPI operacional sin cambiar el modelo: Healthy es No Alert y At Risk o Critical es Risk Alert. Conservamos las métricas multiclase, incluido el Critical Recall, como evidencia complementaria.

**Transición:** Ahora mostramos cómo la arquitectura produce esa alerta sin cambiar sus modelos.

**Error que evitar:** Presentar Risk Alert como un modelo nuevo o esconder Critical Recall.

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

## Slide 6. Resultados ML y KPI de riesgo

**Mensaje central:** PRUNIN detecta proyectos que requieren atención, pero la severidad exacta sigue siendo más difícil.

- TEST project-level: 600 proyectos
- Risk Alert Recall final: **82.45 %**
- Risk Alert Precision final: **92.20 %**
- Risk Alert F1 final: **87.05 %**
- Critical Recall exacto: **56.82 %**
- Health Macro F1: 0.627576 vs baseline 0.277940
- Delay MAE: 27.71 vs 27.85 días → mejora marginal
- Cost MAE: 0.147 pp; R² 0.992 → interpretar con caveat EVM

**Visual/gráfico:** Matriz binaria Risk Alert y una nota con Critical Recall.

**Evidencia:** reports/promise_validation/; reports/0.9.0-academic/

**Speech:** La promesa de negocio se responde con Risk Alert: de 473 proyectos que realmente terminan At Risk o Critical, PRUNIN detecta 390, equivalente a 82.45 %. Cuando exigimos distinguir específicamente la severidad Critical, el recall baja a 56.82 %. Son preguntas diferentes y mostramos ambas. Delay es débil; Cost es fuerte internamente pero está condicionado por la estructura sintética.

**Error que evitar:** Decir que 82.45 % es recall de Critical.

## Slide 7. ¿Cuándo alcanzamos la meta del 75 %?

**Mensaje central:** La meta se supera al 60 % de avance bajo una métrica estricta de cohorte completa.

| Avance | Cobertura TEST | Riesgos finales ya detectados |
|---:|---:|---:|
| 20 % | 39.33 % | 28.54 % |
| 40 % | 77.17 % | 64.06 % |
| 60 % | **96.00 %** | **75.90 %** |
| 80 % | 99.83 % | 79.92 % |
| Final | 100 % | 82.45 % |

**Visual/gráfico:** reports/promise_validation/figures/risk_alert_detection_vs_progress.svg con línea objetivo 75 %.

**Evidencia:** scripts/validate_original_promise.py; reports/promise_validation/

**Speech:** Para no favorecer el resultado por cobertura, usamos como denominador fijo los 473 proyectos que finalmente son At Risk o Critical. Si un proyecto todavía no tiene snapshot elegible, cuenta como no detectado. Con esta regla PRUNIN cruza la meta en el 60 % de avance: 359 de 473 proyectos finales en riesgo ya están detectados, con 96 % de cobertura del TEST. Es una demostración experimental de anticipación antes del cierre, no una validación empresarial.

**Error que evitar:** Decir que al 40 % ya cumplimos 75 % usando solo el recall del subconjunto elegible.

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

## Slide 9. Demo: de la señal a la decisión

**Mensaje central:** La demo muestra una alerta operacional y después explica la evidencia.

- Ingresar snapshot del proyecto
- Mostrar **Risk Alert: requiere atención / sin alerta**
- Mantener Health ML: Healthy / At Risk / Critical
- Mostrar Delay y Cost como estimaciones complementarias
- Explicar drivers y recomendación Qwen/fallback
- Ejecutar What-if y CSV sin confundirlos con causalidad

**Visual/gráfico:** Playground en vivo.

**Evidencia:** frontend/src/components/AnalysisPanels.jsx; DEMO_PRESENTACION.md

**Speech:** La alerta no sustituye Health ni añade un cuarto modelo. Es una traducción operacional de la predicción existente: At Risk o Critical requiere atención. Después mostramos la severidad, las estimaciones y la explicación. Esto conecta directamente el sistema con la promesa original sin alterar el modelo.

**Error que evitar:** Presentar el banner de Risk Alert como probabilidad calibrada o modelo nuevo.

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

## Slide 11. Qué demostramos y qué no

**Mensaje central:** Cumplimiento experimental no equivale a validación empresarial.

- Meta ≥75 %: demostrada en benchmark sintético al 60 % de avance
- Critical Recall exacto: 56.82 %
- Delay: mejora marginal frente a baseline
- Cost: caveat estructural CPI/EVM
- Dataset sintético; sin validación prospectiva empresarial
- Utilidad humana de recomendaciones aún no medida

**Visual/gráfico:** Dos columnas: demostrado / pendiente.

**Speech:** El resultado principal es defendible únicamente dentro del entorno experimental. No afirmamos producción, generalización empresarial ni que la clasificación exacta Critical tenga el mismo desempeño que Risk Alert. La principal etapa futura es validar la misma metodología con datos reales y outcomes observados.

**Error que evitar:** Convertir “cumple experimentalmente” en “funciona en cualquier empresa”.

## Slide 12. Conclusión

**Mensaje central:** PRUNIN cumple la promesa principal dentro del experimento y deja visibles sus límites.

- 473 proyectos TEST terminan At Risk/Critical
- 359 ya están detectados al 60 % → **75.90 %**
- Cobertura TEST en ese punto → **96 %**
- Detección final → **82.45 %**
- Critical Recall exacto → **56.82 %**
- Siguiente etapa: validación prospectiva con proyectos reales

**Visual/gráfico:** 75.90 % al 60 % + línea de meta.

**Evidencia:** reports/promise_validation/; docs/INFORME_FINAL.md

**Speech:** Partimos con una meta concreta: detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo. En el entorno experimental, PRUNIN alcanza 75.90 % de detección de toda la cohorte final de riesgo al 60 % de avance, con 96 % de cobertura, y termina en 82.45 %. La severidad Critical exacta sigue siendo una limitación y Delay continúa débil. Por eso concluimos que la promesa principal está demostrada experimentalmente, mientras la generalización empresarial queda como siguiente etapa.

**Transición:** Abrimos preguntas y respondemos siempre distinguiendo KPI de alerta, severidad y alcance.

**Error que evitar:** Decir “75.90 % de Critical” o “validado en producción”.

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
