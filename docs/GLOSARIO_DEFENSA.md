# Glosario para la defensa

Usar la definición breve antes de citar cifras. EVM significa gestión del valor ganado; EV es valor ganado, PV valor planificado y AC costo real. Las definiciones SPI/CPI son conceptuales, no nuevas features ni una nueva metodología implementada.

| Término | Definición disciplinar | Cómo explicarlo a alguien no técnico |
|---|---|---|
| Health | Clasificación supervisada del riesgo global según etiquetas del experimento: healthy, at_risk, critical. | Un semáforo aprendido con ejemplos; no una decisión definitiva. |
| SPI | Índice EVM de desempeño del cronograma: EV/PV, valor ganado sobre valor planificado. | Compara trabajo logrado con el previsto a esa fecha; menor que 1 indica rezago según EVM. |
| CPI | Índice EVM de desempeño del costo: EV/AC, valor ganado sobre costo real. | Compara valor de trabajo logrado con lo gastado; menor que 1 indica menor eficiencia de costo. |
| MAE | Media del valor absoluto de errores de regresión; conserva unidad del target. | Cuánto se equivoca en promedio, sin cancelar errores positivos y negativos. |
| RMSE | Raíz de la media de errores cuadrados; penaliza más errores grandes. | Resume error dando más peso a equivocaciones grandes. |
| R² | 1 − suma de errores cuadrados / variación del target alrededor de su media; puede ser negativo. | Cuánto explica respecto a predecir la media; no es porcentaje de aciertos. |
| Accuracy | Fracción total de clasificaciones correctas. | Qué parte de las respuestas acierta; puede engañar cuando domina una clase. |
| Balanced Accuracy | Media del recall por clase en clasificación multiclase. | Da igual peso a detectar cada clase, aunque tengan tamaños diferentes. |
| Macro F1 | Media no ponderada del F1 por clase; F1 combina precisión y recall mediante media armónica. | Equilibra calidad de las tres clases sin favorecer la más frecuente. |
| Recall | Fracción de casos reales de una clase detectados correctamente. | De los proyectos realmente críticos, cuántos logramos encontrar. |
| Baseline | Referencia simple ajustada solo en TRAIN: mayoría o mediana por proyecto. | Una regla sencilla que el modelo debe comparar antes de afirmar valor. |
| Leakage | Información no disponible legítimamente contamina entrenamiento/evaluación. | Dar al modelo pistas del futuro o duplicar el mismo proyecto entre conjuntos. |
| LightGBM | Biblioteca de gradient boosting de árboles usada para clasificación y regresión tabulares. | Muchos árboles que corrigen sucesivamente errores para aprender patrones. |
| GenAI | IA generativa que produce texto aquí, separada del predictor supervisado. | Redacta una explicación a partir de evidencia; no calcula el semáforo de PRUNIN. |
| Grounding | Restricción/validación de generación contra evidencia permitida; aquí proxy determinístico. | Pedir que se apoye en datos concretos y rechazar cifras nuevas; aún puede equivocarse en significado. |
| Fallback | Respaldo determinístico cuando generación está apagada, no disponible o rechazada. | Una respuesta de reglas que mantiene el servicio; no es IA generativa. |
| Inference / inferencia | Aplicar un modelo entrenado a nuevas entradas sin reajustar parámetros. | Usar lo aprendido para estimar un proyecto ahora. |
| MLOps | Prácticas de versionado, reproducibilidad, despliegue y observabilidad de modelos. | Saber qué modelo opera, revisar errores y actualizarlo con control. |
| Drift | Cambio de distribución o relación entradas–outcome a lo largo del tiempo. | Los proyectos nuevos empiezan a diferir de los que el modelo conocía. |
| HPA | HorizontalPodAutoscaler; ajusta réplicas Kubernetes según métricas configuradas. | Un mecanismo diseñado para aumentar o reducir copias; aquí no existe clúster activo. |
| Team Health | Heurística operacional determinística de señales observadas de equipo; sin imputación/psicología. | Indicador del funcionamiento operativo del equipo, no su salud mental. |
| Sensitivity / sensibilidad local | Cambio de salida al sustituir una variable por referencia manteniendo las otras. | Qué tanto cambia la estimación en esa prueba; no prueba la causa. |
| Causalidad | Relación de causa/efecto cuya identificación exige diseño/evidencia adicional. | Afirmar que intervenir en una variable producirá un cambio; PRUNIN no lo demuestra. |

Evitar «99 % de precisión», «Qwen predice riesgo», «drivers causales» o «Team Health supervisado». Final Status es traducción de Health: healthy→successful, at_risk→challenged, critical→critical. Diferenciar ratio de Cost y puntos porcentuales (ratio×100); nunca llamar R² accuracy.

Evidencia de uso: model_card.md; src/prunin_ai/training/core.py; src/prunin_ai/api/recommendations.py; reports/0.9.0-academic/; deploy/k8s/. Las referencias primarias están en references.md. Pronunciación, ejemplos y fluidez deben ensayarse; el archivo no acredita desempeño oral.
