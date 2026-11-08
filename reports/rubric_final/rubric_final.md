# Matriz final PAIII 2026

Estados limitados a `DEMONSTRATED`, `DEMONSTRATED_WITH_LIMITATION`, `PREPARED_HUMAN` y `DESIGN_ONLY`. El objetivo de esta tabla es auditar evidencia y gaps, no asignar calificación oficial. Ver [rubric_final.json](rubric_final.json) para claims seguros/no seguros y rutas de evidencia por criterio.

| Código | Criterio | Estado | Evidencia automatizada | Gap restante |
|---|---|---|---|---|
| R6.1-Cr1 | Problema y contexto | DEMONSTRATED_WITH_LIMITATION | Informe, README, KPI original | Sin validación empresarial |
| R6.1-Cr2 | Elección de GenAI | DEMONSTRATED_WITH_LIMITATION | Comparación parcial, 30 casos comunes | Gemma/Ministral no disponibles |
| R6.1-Cr3 | Integración GenAI | DEMONSTRATED_WITH_LIMITATION | API, guardrails, timeout/fallback | Escalabilidad/utilidad semántica no probadas |
| R6.1-Cr4 | Evaluación GenAI | DEMONSTRATED_WITH_LIMITATION | Evaluación oficial y comparación separada | Muestra pequeña; utilidad humana no medida |
| R6.2-Cr5 | Tareas automatizables | DEMONSTRATED_WITH_LIMITATION | API, batch, What-if, recomendación | Impacto de decisiones no probado |
| R6.2-Cr6 | Eficiencia, escala y productividad | DEMONSTRATED_WITH_LIMITATION | Benchmarks operacional y concurrencia local | No demuestra productividad ni producción |
| R6.2-Cr7 | Ética y mitigación | DEMONSTRATED_WITH_LIMITATION | Matriz ética y controles testeados | Riesgos residuales permanecen |
| R6.2-Cr8 | Documentación | DEMONSTRATED_WITH_LIMITATION | README, informe, matriz, evidencias | Revisión institucional/autor pendiente |
| RA1-F1 | Estructura escrita | DEMONSTRATED_WITH_LIMITATION | Informe académico | Portada/formato institucional |
| RA1-F2 | Intención escrita | DEMONSTRATED_WITH_LIMITATION | Audiencia, objetivos, límites | Comprensión externa no evaluada |
| RA1-F3 | Canales y medios | DEMONSTRATED_WITH_LIMITATION | Demo, figuras, CSV/JSON, slides | Uso real/proyección pendiente |
| RA1-F4 | Conclusiones | DEMONSTRATED_WITH_LIMITATION | Resultados congelados y KPI | Solo benchmark sintético |
| RA1-F5 | Gramática, tablas y figuras | DEMONSTRATED_WITH_LIMITATION | Documentación y figuras versionadas | Render final debe revisarse |
| RA1-Referencias | Referencias | DEMONSTRATED_WITH_LIMITATION | DOI/fuentes oficiales | Verificación institucional final |
| RA2-F1 | Estructura oral | PREPARED_HUMAN | Guion y plantilla de ensayo | Actuación no observada |
| RA2-F2 | Intención oral | PREPARED_HUMAN | Versiones de 7/10/12 min | Ensayo cronometrado pendiente |
| RA2-F3 | Lenguaje profesional | PREPARED_HUMAN | Glosario y preguntas | Fluidez oral no observada |
| RA2-F4 | Técnicas vocales | PREPARED_HUMAN | Checklist de voz | Práctica/observación humana |
| RA2-F5 | Recursos de apoyo | PREPARED_HUMAN | Slides, Playground, figuras | Uso en vivo no observado |
| RA2-F6 | Lenguaje no verbal | PREPARED_HUMAN | Checklist postural | Solo se evalúa en sustentación |
| RA2-F7 | Defensa/argumentación | PREPARED_HUMAN | Banco de respuestas con evidencia | Respuesta espontánea no observada |
| R7.1-Cr1 | Preprocesamiento | DEMONSTRATED_WITH_LIMITATION | Pipeline TRAIN, gate y OOD | OOD es univariado y no productivo |
| R7.1-Cr2 | Herramientas y dominio | DEMONSTRATED_WITH_LIMITATION | Código y documentación de roles | Dominio oral pendiente |
| R7.1-Cr3 | Pipeline | DEMONSTRATED_WITH_LIMITATION | `train_all.sh`, pruebas de datos | Entrenamiento oficial no repetido |
| R7.2-Cr4 | Automatización despliegue | DEMONSTRATED_WITH_LIMITATION | CI y manifiesto probado estáticamente | deployment automation/design validated statically; production cluster not operated |
| R7.2-Cr5 | Escalabilidad y robustez | DEMONSTRATED_WITH_LIMITATION | Guardrails, pruebas locales | No hay carga/clúster productivo |
| R7.2-Cr6 | MLOps | DEMONSTRATED_WITH_LIMITATION | Versionado, logs, métricas, drift offline | Sin monitor/retraining productivo |

Los siete criterios RA2 se mantienen `PREPARED_HUMAN`; obtener Nivel 4 depende de ejecutar y observar la sustentación real. No se afirma “100 % cumplido”, operación productiva ni validación empresarial.