# PRUNIN AI Core Playground

## Objetivo

La demo ejecuta inferencia real contra los artefactos `.joblib`; no contiene resultados predeterminados en el frontend.

## Selección de modelo

1. Si `PRUNIN_ARTIFACT_DIR` está definido, usa ese directorio.
2. Si existe `artifacts/0.9.0-academic/health.joblib`, usa el modelo académico.
3. En caso contrario usa `artifacts/demo-0.1.0` y lo muestra explícitamente como `synthetic_demo`.

El fallback permite smoke tests cuando faltan artefactos oficiales. En la entrega congelada no se reentrena y se exige 0.9.0-academic para mostrar sus métricas.

## Uso dinámico de variables

`/api/schema` clasifica cada campo desde `feature_manifest.json` y la configuración Team Health. La superficie principal muestra solo `ml_feature` y separa `team_health`; `not_used` queda en una sección futura deshabilitada. React no mantiene una lista académica fija.

En el artifact académico `0.9.0-academic` actualmente versionado en los reportes, las features ML son:

- `planned_duration_weeks`
- `planned_budget`
- `true_progress`
- `spi`
- `cpi`
- `project_type`
- `methodology`

La lista no se fija en React: `/api/schema` la obtiene de `feature_manifest.json`. Si un artifact futuro cambia de features, la interfaz se adapta dinámicamente.

Las categorías de `project_type` y `methodology` expuestas por el API corresponden al dominio categórico presente en el dataset Mendeley v2 utilizado para entrenar el modelo académico. React consume las opciones de `/api/schema`, que es la fuente para los selects. `true_progress` normaliza solo ruido de punto flotante de hasta `1e-9` en los límites 0 y 1; valores realmente fuera de rango se rechazan.

Las señales Team Health se derivan dinámicamente de los pesos configurados. Actualmente incluyen utilización, capacidad, productividad, retrabajo, defectos, estabilidad y colaboración; se muestran como heurística y no como inputs aprendidos por el clasificador académico.

What-if solo permite cambiar features ML y señales Team Health; las agrupa por efecto. La plantilla CSV académica incluye features ML obligatorias y Team Health opcional, nunca `not_used`. `?profile=full_future` ofrece un esquema completo para integraciones futuras.

Se excluyen deliberadamente las variables de V8.6.3 sin soporte suficiente para esta versión:

- `reported_progress`
- `critical_path_delay_days`
- `team_morale`

## Modos de prueba

- formulario manual;
- presets saludable / en riesgo / crítico;
- simulación what-if;
- carga CSV hasta 100 filas;
- descarga de plantilla CSV;
- detalle JSON de la inferencia;
- identificación de versión y modo del modelo;
- drivers por sensibilidad local;
- recomendaciones fundamentadas.

## IA generativa

LightGBM se encarga de la predicción; Qwen3 convierte evidencia estructurada en acciones priorizadas, justificadas y con seguimiento; Ollama es el runtime local y `grounded_fallback` el respaldo determinístico. La demo nunca depende de un LLM para ejecutar ML.

Si se desea habilitar generación local con Ollama:

```bash
export PRUNIN_ENABLE_OLLAMA=1
export PRUNIN_OLLAMA_MODEL=qwen3:8b
export PRUNIN_OLLAMA_TIMEOUT_SECONDS=30
./scripts/run_playground.sh
```

`GET /api/genai-status` consulta `/api/tags` con timeout corto y confirma que el modelo esté instalado. El timeout es configurable y compartido por API y benchmark mediante `PRUNIN_OLLAMA_TIMEOUT_SECONDS` (default 30 s). `PRUNIN_OLLAMA_WARMUP=1` habilita warm-up acotado al iniciar; está apagado por defecto y no se activa en CI. `PRUNIN_GENAI_DEBUG=1` agrega raw response, JSON parseado y validación al campo técnico; no se devuelve por defecto.

Cada acción aceptada presenta prioridad, título, señal permitida, procedencia, qué hacer, por qué y qué revisar después. `evidence-v2` separa sensibilidad predictiva, señales operativas observadas e indicadores heurísticos. `configs/operational_signals.yaml` define triggers de revisión no calibrados: SPI/CPI <0.95, utilización >1.05, capacidad <0.90, productividad <0.85, retrabajo >0.10, defectos >0.08, alcance >0.10, dependencias >7 días, exposición >0.30 y gobierno <0.60. SPI/CPI <1 son desfavorables según EVM; 0.95 y los demás cortes son tolerancias heurísticas, no umbrales entrenados ni evidencia empresarial. No se evaluaron contra TEST para optimizar métricas.

La falta de drivers positivos no descarta desviaciones. Se exige al menos una acción si hay evidencia accionable; solo se permite seguimiento normal si la evaluación es suficiente y no hay señales prioritarias. Sin evidencia suficiente, se informa la limitación sin inventar riesgos. Los valores ausentes no se imputan en esta capa. Cifras inventadas, procedencia falsa, contradicciones explícitas, seguimiento no verificable, formato inválido o fallo del servicio activan fallback sobre señales verificadas. El respaldo devuelve la misma estructura y nunca se etiqueta como GenAI. El resumen se muestra una sola vez. Las reglas no cambian Health, Delay, Cost, Final Status, Team Health ni el cálculo de drivers.

`POST /api/what-if` omite recomendaciones para ambas inferencias y `/api/predict-csv` las omite por fila; las predicciones y drivers siguen ejecutándose. «Ver análisis completo» solicita una nueva inferencia individual con recomendaciones para la fila seleccionada, sin llamar al LLM para todo el CSV. Para integración local: `./scripts/preflight_genai.sh`. La evaluación nueva exige un destino independiente y se niega a sobrescribir reportes existentes.

## Arranque

### Regresión bancaria y descarga

El [CSV bancario de regresión](../tests/fixtures/banking_recommendations.csv) conserva SPI 0.72, CPI 0.81, utilización 1.12 y las demás desviaciones del caso ficticio. Cargarlo por CSV y abrir «Ver análisis completo» ejecuta generación individual con la misma entrada, sin LLM masivo. La [evidencia E2E](../reports/recommendations_closure_2026-11-08/README.md) registra Qwen real, fallback por conexión fallida y JSON descargado idéntico a la respuesta individual. Para descarga, usar Chrome externo: el navegador integrado de VS Code no notificó el evento en esta prueba. El test reproducible es `scripts/test_banking_browser.mjs`, con herramienta temporal externa según el reporte; no cambia dependencias del proyecto.

```bash
./scripts/setup_playground.sh
./scripts/run_playground.sh
```

Abrir `http://localhost:8000`.

## Despliegue público

La aplicación se empaqueta en `Dockerfile.playground`. El contenedor construye React/Vite y sirve el resultado desde FastAPI, por lo que solo se expone un puerto.

## QR y evidencia descargable

El panel técnico genera un QR con la URL actual mediante `/api/qr`. Cuando la aplicación esté desplegada en una URL pública, el mismo QR permitirá a los asistentes abrirla desde su celular. El resultado individual también se puede descargar como JSON con `prediction_id`, versión, modo, inputs, predicciones, drivers y recomendaciones.

La vista de resultados distingue `Health ML` de `Riesgo combinado`. Team Health y la fusión 0.85/0.15 son heurísticas operativas no calibradas con outcomes reales. Los drivers muestran sensibilidad local, no causalidad. Para Mendeley v2, Final Status se devuelve como estado de negocio derivado, sin probabilidades propias.

La calidad de entrada expone cobertura y señales faltantes. Si el perfil TRAIN está disponible, `ood_warning` y `ood_features` advierten sobre valores numéricos fuera de fences IQR o categorías no observadas en TRAIN. OOD es una advertencia y no cambia la predicción. Ver `docs/drift_monitoring.md` para límites y comparación batch; no se afirma monitorización productiva.

## Cierre: presentación operacional

La predicción de regresión cruda puede ser ligeramente negativa. La interfaz aplica una restricción operacional de cero días para presentación, conservando el valor crudo en la trazabilidad técnica.

`delay_days_raw` conserva la regresión; `delay_days` aplica max(0, raw) en API/CSV/What-if. Cost negativo no se trunca. La columna Team Health del batch se oculta si ninguna fila tiene score calculable; aparece si al menos una lo tiene.

## Preparación y medios de demostración

Para instalar el entorno usar ./scripts/setup_playground.sh y verificar después preflight. No ejecutar entrenamientos sobre artefactos oficiales durante el cierre. Un clon no incluye modelos/datasets pesados; copiar los artefactos aprobados o reproducir en un entorno separado según training.md. La demo de fixtures no acredita resultados académicos.

La URL local es http://localhost:8000; run_playground.sh muestra LAN cuando disponible. PRUNIN_PUBLIC_URL configura QR para URL publicada si existe, sin afirmar hosting real. Verificar red del salón. Guion ejecutivo: PRESENTACION_FINAL.md; secuencia en vivo: ../DEMO_PRESENTACION.md; preguntas y glosario en PREGUNTAS_DEFENSA.md y GLOSARIO_DEFENSA.md. Mostrar resultados/gráficos antes de código y no leer JSON completo sin propósito.

El valor ml_inference_ms incluye ML y drivers, igual a timing.ml_and_drivers_ms; no etiquetarlo como tiempo puro del predictor. Timing.total_ms incluye la generación cuando se intenta. El límite CSV de 100 filas no es throughput bajo carga. La matriz completa distingue evidencia técnica, comunicación escrita y desempeño oral pendiente.
