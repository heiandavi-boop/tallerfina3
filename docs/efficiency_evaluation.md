# Protocolo de evaluación de eficiencia

## Estado actual

**Pendiente de evidencia humana.** No existe un baseline humano medido versionado. La evaluación Qwen completa registra mediana de generación de 3.092645 s y p95 de 6.63472 s. Son tiempos del benchmark GenAI, no tiempo total de análisis ni ahorro de trabajo humano. CSV y What-if automatizan ML sin LLM.

## A. Evidencia automática disponible

| Elemento | Evidencia actual | Alcance de la afirmación |
|---|---|---|
| Inferencia ML y drivers | API timing.ml_and_drivers_ms y ml_inference_ms | Incluye drivers; no es duración del predictor puro ni promedio poblacional |
| Tiempo total del análisis | API timing.total_ms e inference_ms | Puede incluir GenAI según flags; una observación no es benchmark bajo carga |
| Latencia Qwen | Benchmark versionado: mediana 3.092645 s, p95 6.63472 s | Solo esta corrida local y muestra condicionada |
| Capacidad batch | /api/predict-csv admite máximo 100 filas | Límite configurado, no throughput medido |
| Cantidad por lote | count y filas/errores del resultado CSV | Conservar lote, errores y duración si se mide |
| Recomendación automática | generation_success_rate=29/30; schema/features válidas 30/30 | Generación aceptada, no eficacia profesional |

Fuente: `src/prunin_ai/api/app.py`, tests y `reports/genai/qwen3-8b-evaluation.json`. CSV y What-if no usan Qwen. El preflight acredita ejecución, sin inventar latencia ML promedio ni escalabilidad. El cálculo automated_cases_per_hour del script es teórico a partir de la mediana Qwen, sin concurrencia, carga ni revisión humana.

## B. Medición humana mínima reproducible

Seleccionar y congelar cinco casos del benchmark `reports/genai/qwen3-8b-evaluation.json`, registrando sus `project_id`, siete features y evidencia disponible. Usar los mismos casos y tarea para la comparación automática. Anotar fecha, perfil del participante, equipo, instrucciones y si hay entrenamiento previo; evitar mostrarle la recomendación generada antes de cronometrar.

Para cada caso presentar los datos, iniciar el cronómetro y pedir: interpretar señales, identificar el riesgo y redactar una recomendación con evidencia. Detenerlo al entregar el texto. Registrar segundos reales y conservar la respuesta para revisar utilidad con los mismos criterios. Una tabla vacía no es resultado.

| Caso (registrar project_id) | Tiempo humano (segundos) | Observaciones |
|---|---|---|
| mendeley::PROJ_0760 | PENDIENTE DE MEDICIÓN | Registrar perfil, contexto y respuesta |
| mendeley::PROJ_2717 | PENDIENTE DE MEDICIÓN | Registrar perfil, contexto y respuesta |
| mendeley::PROJ_0062 | PENDIENTE DE MEDICIÓN | Registrar perfil, contexto y respuesta |
| mendeley::PROJ_0539 | PENDIENTE DE MEDICIÓN | Registrar perfil, contexto y respuesta |
| mendeley::PROJ_2331 | PENDIENTE DE MEDICIÓN | Registrar perfil, contexto y respuesta |

Calcular `mediana_humana = median(tiempos_reales)` y ejecutar solamente después de obtenerla:

```bash
python scripts/benchmark_efficiency.py \
  --manual-seconds-per-case <MEDIANA_REAL>
```

El script calcula `(1 - mediana_automática / mediana_humana) * 100` y `mediana_humana / mediana_automática`. Su latencia automática procede del benchmark Qwen de 30 casos: compararla con cinco casos manuales es exploratorio, con tamaños y condiciones diferentes. Para una afirmación end-to-end sólida, medir también ML, drivers, generación y revisión humana sobre los mismos cinco casos (`timing.total_ms` del API), reportando fallbacks y calidad. No confundir capacidad teórica por hora con throughput observado bajo carga.

Se puede ejecutar sin baseline para registrar únicamente la evidencia automática; `manual_baseline_status=not_measured`, ahorro y ganancia quedan null. No introducir valores de ejemplo en la tabla ni invocar el script con segundos ficticios. Cr6 permanece pendiente hasta adjuntar mediciones, respuestas y condiciones experimentales. Cinco casos constituyen evidencia exploratoria, no una generalización de eficiencia empresarial.

## Datos y comparabilidad de los cinco casos

Los identificadores de la tabla proceden del JSON real, no son cinco observaciones humanas ya medidas. Recuperar sus siete entradas desde `data/processed/mendeley_core.csv`, filtrando por esos project_id y eligiendo el snapshot más reciente (snapshot_index). Registrar cuáles se usaron, verificar pertenencia a TEST y conservar las entradas presentadas sin cambiarlas. El benchmark histórico no permite inferir tiempo de lectura humana.

Cronometrar explícitamente revisión de inputs → interpretación del riesgo → identificación de señales principales → redacción de recomendación accionable. No revelar la respuesta Qwen antes de medir. Guardar texto manual, cronómetro, fecha y condiciones. Si se comparan latencias por caso del benchmark, indicar que son históricos/locales; para una comparación end-to-end pareada nueva medir ambos procesos bajo las mismas condiciones, sin sobrescribir el reporte oficial. El marcador `<MEDIANA_REAL>` no es un argumento ejecutable hasta reemplazarlo con la medición.

Estado rúbrica: **Pendiente de evidencia humana cuantitativa.** No se acredita Nivel 4 de eficiencia/escalabilidad/productividad con latencia y límite de lote por sí solos.
