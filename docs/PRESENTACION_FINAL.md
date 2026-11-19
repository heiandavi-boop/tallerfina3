# Presentación académica — PRUNIN AI Core

**Proyecto Aplicado III · Versión académica 0.9.0-academic**

Esta presentación organiza los resultados y el recorrido demostrable. Los tiempos de intervención, comentarios personales y material de ensayo se gestionan aparte. Adaptar la duración y el formato a las instrucciones de la institución.

## Diapositiva 1 — Problema
**¿Podemos anticipar riesgos de retraso y sobrecosto antes del cierre de un proyecto?**

- La dirección de proyectos necesita interpretar señales de avance, cronograma y costos antes de intervenir.
- PRUNIN organiza datos, estima riesgos y ofrece acciones sujetas a revisión profesional.
- Alcance: prototipo académico reproducible, no sistema validado en operación empresarial.

**Evidencia:** [Informe final](INFORME_FINAL.md).

## Diapositiva 2 — Pregunta de investigación y objetivo
- Pregunta: ¿en qué medida la combinación de modelos predictivos e IA generativa permite detectar temprano condiciones de riesgo y traducir evidencias en recomendaciones?
- Meta original: detectar al menos el 75 % de proyectos **At Risk o Critical** antes de su cierre.
- KPI explícito: `Risk Alert` agrupa At Risk + Critical; mantiene separada la clasificación exacta Critical.

**Evidencia:** [Validación de la promesa](../reports/promise_validation/promise_validation_report.md).

## Diapositiva 3 — Arquitectura híbrida
- React/Vite captura información estructurada; FastAPI valida solicitudes.
- Tres modelos LightGBM predicen Health, Delay y Cost.
- Drivers locales y señales operativas generan evidencia etiquetada.
- La generación de recomendaciones puede utilizar **Ollama/Qwen3 8B** u **OpenAI API**, a elección del usuario.
- Validador de evidencia y fallback determinístico antes de presentar acciones.
- Team Health es heurístico; Final Status deriva de Health.

**Evidencia:** [Arquitectura](architecture.md), [proveedores](ai_providers.md).

## Diapositiva 4 — Datos y procedencia
- Fuente del entrenamiento académico: **Mendeley Data v2**, DOI `10.17632/2p5sz57wh2.2`.
- Datos simulados externos: 4.000 proyectos y 72.549 snapshots.
- Separación disjunta por proyecto: 2.800 TRAIN / 600 VALIDATION / 600 TEST.
- Itemlet, Collaboration y SQuaD fueron explorados; **no entrenaron los tres LightGBM de la versión académica**.
- Los experimentos históricos de PRUNIN se documentan por separado del artefacto evaluado.

**Evidencia:** [Datos](datasets.md), [evolución](project_evolution.md).

## Diapositiva 5 — Modelos y variables
- Health: clasificación multiclase (healthy / at_risk / critical).
- Delay: estimación de días de retraso.
- Cost: estimación relativa de desviación presupuestal.
- Variables supervisadas: duración y presupuesto previstos, avance real, SPI, CPI, tipo y metodología.
- Los datos de equipo ayudan a la evaluación heurística, pero no se inyectan de forma oculta al modelo supervisado.

**Evidencia:** [Ficha de modelo](model_card.md), [entrenamiento](training.md).

## Diapositiva 6 — Evaluación del aprendizaje
- Health Macro F1 = **0,627576**.
- Delay MAE = **27,710468 días**, frente a baseline de **27,850313**; mejora marginal.
- Cost: R² = **0,991816** en el entorno simulado; requiere cautela por la estructura CPI/EVM.
- Las métricas son de la versión congelada y no se recalculan por cambiar de proveedor generativo.

**Evidencia:** [Métricas académicas](../reports/0.9.0-academic/metrics.json).

## Diapositiva 7 — Detección temprana
- `Risk Alert`: 359/473 proyectos finalmente en riesgo detectados al 60 % de avance.
- Recall **75,90 %**, con **96 %** de cobertura del conjunto TEST en ese corte.
- Recall del nivel Critical exacto: **56,82 %**, distinto de Risk Alert.
- La cobertura a etapas muy tempranas es menor; no ocultar limitaciones del indicador.

**Evidencia:** [Reporte temporal](../reports/promise_validation/promise_validation_report.md).

## Diapositiva 8 — Recomendaciones fundamentadas
- La generación utiliza evidencia estructurada, procedencia de cada señal, prioridad y seguimiento.
- **Ollama/Qwen3 8B**: evaluación histórica oficial de 30 casos con 29 respuestas aceptadas; no es una evaluación de OpenAI.
- **Benchmark 2026** (mismos 30 casos, controlado y operativo): Qwen3 8B 30/30 aceptadas, mediana 8,1 s. **OpenAI no medido**: la clave no estaba accesible para el proceso; gasto 0 USD.
- El usuario puede alternar proveedores sin cambiar las predicciones.
- Una respuesta inválida activa acciones de respaldo determinístico.

**Evidencia:** [Evaluación GenAI](genai_evaluation.md), [proveedores](ai_providers.md), [comparación 2026](../reports/genai/provider_comparison_2026/comparison_report.md).

## Diapositiva 9 — Demostración funcional
1. Elegir un caso de prueba y ejecutar la predicción.
2. Examinar nivel de riesgo, probabilidades, retraso, costo y señales.
3. Seleccionar Ollama u OpenAI, si el proveedor está disponible.
4. Revisar recomendaciones y referencias de evidencia.
5. Simular un escenario What-if y probar una fila de CSV.
6. Consultar versión, resultado JSON y trazabilidad de los controles.

**Evidencia:** [Protocolo de demo](DEMO_PROTOCOL.md).

## Diapositiva 10 — Ética, privacidad y control operativo
- No usar datos empresariales sensibles sin autorización.
- En modo OpenAI se transmiten al proveedor externo las señales estructuradas.
- Claves solamente en memoria de sesión o entorno del servidor; nunca en repositorio.
- En producción, el API falla cerrado si falta el token; el límite OpenAI vigente es por IP par/minuto y por proceso/día, no una cuota distribuida.
- El cliente no puede habilitar Ollama cuando el servidor lo desactiva; un despliegue público aún requiere HTTPS e identidad multiusuario.
- Los indicadores del modelo no prueban causalidad ni reemplazan decisiones profesionales.

**Evidencia:** [Ética y seguridad](ethics_security.md).

## Diapositiva 11 — Limitaciones y trabajo futuro
- Fuente principal sintética externa; falta validación prospectiva con proyectos reales.
- Delay ofrece mejora limitada frente al baseline.
- Algunas señales son heurísticas y no provienen de variables supervisadas.
- Productividad humana NO MEDIDA: el instrumento está listo, pero no hay participantes. La comparación con OpenAI está pendiente de la clave.
- MLOps: registro, gate de regresión y rollback demostrados con datos sintéticos (candidato rechazado). Docker se valida en CI; no hay clúster Kubernetes.

**Evidencia:** [Matriz interna](rubric_matrix.md), [cierre](FINAL_READINESS.md).

## Diapositiva 12 — Conclusiones
- PRUNIN permite obtener predicciones replicables e información accionable documentada.
- La meta operacional de detección temprana se cumple en el corte y denominador especificados, no en cualquier punto del proyecto.
- Separar predicción, heurísticas, IA generativa y revisión humana mejora la trazabilidad.
- Los proveedores generativos son intercambiables; los resultados científicos congelados permanecen intactos.

**Fuentes:** [Referencias](references.md).

---

## Material gráfico y soporte
Usar figuras de `reports/0.9.0-academic/figures/`, la gráfica de `reports/promise_validation/figures/` y capturas actuales verificadas del Playground. La sustentación oral y el uso real de los recursos requieren comprobación humana, tal como se especifica en [criterios orales](ORAL_EVIDENCE.md).
