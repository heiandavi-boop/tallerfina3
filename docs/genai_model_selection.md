# Selección del modelo generativo local — PRUNIN AI Core

## Decisión implementada
La versión académica utiliza **Ollama con Qwen3 8B** para convertir evidencia estructurada de proyectos en acciones trazables. Esta elección está alineada con privacidad de los indicadores, ejecución sin servicio de inferencia externo, control de versiones por digest, disponibilidad en el hardware de demostración y capacidad de respuesta estructurada en español. No representa una afirmación de superioridad universal.

La arquitectura separa los tres modelos LightGBM congelados (Health, Delay, Cost) de la capa generativa. Qwen no calcula las predicciones ni reemplaza la revisión profesional. El motor genera máximo cuatro acciones con evidencia verificable y seguimiento, y el validador puede rechazar la generación y ofrecer respaldo determinístico.

## Alternativas locales de estudio

| Candidato local | Disponibilidad documentada | Resultado de PRUNIN |
|---|---|---|
| Qwen3 8B | Instalado y evaluado en Ollama | Medido en dos pruebas independientes |
| Gemma 3 4B | No disponible en la corrida de candidatos | Sin mediciones; no se atribuye rendimiento |
| Ministral 3 8B | No disponible en la corrida de candidatos | Sin mediciones; no se atribuye rendimiento |
| gpt-oss:20b | Detectado entre modelos locales instalados durante diagnóstico | No ejecutado en el mismo benchmark; falta comparación homogénea |

Esta lista documenta alternativas posibles, no una comparación exhaustiva ejecutada. Para cerrar R6.1-Cr2 en Nivel 4 se necesita correr candidatos compatibles con el mismo conjunto de casos, formato, condiciones y validador; registrar velocidad, aceptación, contradicciones, pertinencia, consumo de recursos y repetibilidad. No mezclar mediciones con esquemas distintos.

## Evidencia existente

**Evaluación histórica académica congelada:** Qwen3 8B produjo 29/30 recomendaciones aceptadas, una cifra no soportada, mediana 3092.645 ms y p95 6634.72 ms. Se conserva en `reports/genai/qwen3-8b-evaluation.json`.

**Ejecución experimental adicional:** Qwen3 8B, digest `500a1f067a9f`, cuantización Q4_K_M, produjo 30/30 respuestas aceptadas en los 30 casos controlados y 30/30 en el modo operativo local. Latencia mediana 8114.68 ms (p95 19783.22 ms) y 8305.3 ms (p95 18347.63 ms), respectivamente; cinco casos repetidos tres veces mantuvieron la estructura y las acciones. Esta ejecución fue distinta de la evaluación histórica y no sustituye sus métricas.

**Benchmark de candidatos locales:** Qwen3 8B produjo 29/30 aceptaciones en un experimento adicional, mientras que los otros candidatos de ese experimento no estuvieron disponibles. Consultar `reports/genai/comparison/` para el detalle real de esa corrida.

## Matriz de decisión

| Criterio | Valor y limitación de Qwen3 8B |
|---|---|
| Privacidad | Inferencia de recomendaciones dentro del entorno local, si Ollama se configura en una red confiable |
| Conectividad | No necesita un servicio remoto de inferencia; sí requiere que Ollama esté operativo |
| Recursos | El modelo cuantizado requiere memoria y capacidad de cómputo; el rendimiento depende del equipo |
| Costos | No hay cargo externo por tokens, pero existen costos computacionales |
| Calidad | Se cumplen los controles proxy en las pruebas reportadas; falta evaluación humana ciega |
| Reproducibilidad | Digest de modelo y parámetros documentados; los resultados varían con el entorno |
| Riesgo operacional | Latencia y timeouts aumentan bajo concurrencia; usar fallback determinístico |

**Conclusión:** Qwen3 8B es la alternativa seleccionada y realmente implementada. La elección se justifica por las restricciones del prototipo; la comparación exhaustiva empírica con otros modelos locales y la calidad humana siguen pendientes. La rúbrica no exige un proveedor de nube.
