# Protocolo de evaluación de eficiencia

## Estado actual

**Pendiente de evidencia humana.** No existe un baseline humano medido versionado. La evaluación Qwen completa registra mediana de generación de 3.092645 s y p95 de 6.63472 s. Son tiempos del benchmark GenAI, no tiempo total de análisis ni ahorro de trabajo humano. CSV y What-if automatizan ML sin LLM.

## Medición mínima reproducible

Seleccionar y congelar cinco casos del benchmark `reports/genai/qwen3-8b-evaluation.json`, registrando sus `project_id`, siete features y evidencia disponible. Usar los mismos casos y tarea para la comparación automática. Anotar fecha, perfil del participante, equipo, instrucciones y si hay entrenamiento previo; evitar mostrarle la recomendación generada antes de cronometrar.

Para cada caso presentar los datos, iniciar el cronómetro y pedir: interpretar señales, identificar el riesgo y redactar una recomendación con evidencia. Detenerlo al entregar el texto. Registrar segundos reales y conservar la respuesta para revisar utilidad con los mismos criterios. Una tabla vacía no es resultado.

| Caso (registrar project_id) | Tiempo humano (segundos) | Observaciones |
|---|---|---|
| 1 — pendiente | PENDIENTE | |
| 2 — pendiente | PENDIENTE | |
| 3 — pendiente | PENDIENTE | |
| 4 — pendiente | PENDIENTE | |
| 5 — pendiente | PENDIENTE | |

Calcular `mediana_humana = median(tiempos_reales)` y ejecutar solamente después de obtenerla:

```bash
python scripts/benchmark_efficiency.py \
  --manual-seconds-per-case <MEDIANA_REAL>
```

El script calcula `(1 - mediana_automática / mediana_humana) * 100` y `mediana_humana / mediana_automática`. Su latencia automática procede del benchmark Qwen de 30 casos: compararla con cinco casos manuales es exploratorio, con tamaños y condiciones diferentes. Para una afirmación end-to-end sólida, medir también ML, drivers, generación y revisión humana sobre los mismos cinco casos (`timing.total_ms` del API), reportando fallbacks y calidad. No confundir capacidad teórica por hora con throughput observado bajo carga.

Se puede ejecutar sin baseline para registrar únicamente la evidencia automática; `manual_baseline_status=not_measured`, ahorro y ganancia quedan null. No introducir valores de ejemplo en la tabla ni invocar el script con segundos ficticios. Cr6 permanece pendiente hasta adjuntar mediciones, respuestas y condiciones experimentales. Cinco casos constituyen evidencia exploratoria, no una generalización de eficiencia empresarial.
