# PRUNIN AI Core Playground

## Objetivo

La demo ejecuta inferencia real contra los artefactos `.joblib`; no contiene resultados predeterminados en el frontend.

## Selección de modelo

1. Si `PRUNIN_ARTIFACT_DIR` está definido, usa ese directorio.
2. Si existe `artifacts/0.9.0-academic/health.joblib`, usa el modelo académico.
3. En caso contrario usa `artifacts/demo-0.1.0` y lo muestra explícitamente como `synthetic_demo`.

Esto permite ensayar la aplicación antes de finalizar el reentrenamiento sin presentar el modelo demo como resultado definitivo.

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

LightGBM se encarga de la predicción, Qwen3 de la explicación/recomendación, Ollama del runtime local y `grounded_fallback` del respaldo determinístico. La demo nunca depende de un LLM para ejecutar ML.

Si se desea habilitar generación local con Ollama:

```bash
export PRUNIN_ENABLE_OLLAMA=1
export PRUNIN_OLLAMA_MODEL=qwen3:8b
export PRUNIN_OLLAMA_TIMEOUT_SECONDS=30
./scripts/run_playground.sh
```

`GET /api/genai-status` consulta `/api/tags` con timeout corto y confirma que el modelo esté instalado. El timeout es configurable y compartido por API y benchmark mediante `PRUNIN_OLLAMA_TIMEOUT_SECONDS` (default 30 s). `PRUNIN_OLLAMA_WARMUP=1` habilita warm-up acotado al iniciar; está apagado por defecto y no se activa en CI. `PRUNIN_GENAI_DEBUG=1` agrega raw response, JSON parseado y validación al campo técnico; no se devuelve por defecto.

Las recomendaciones aceptadas citan solo features allow-listed de drivers que aumentan riesgo. Las cifras se cotejan con evidencia estructurada, admitiendo equivalencia decimal/porcentual. Sin drivers de riesgo, lista vacía y resumen prudente son válidos; con drivers, debe existir al menos una recomendación. JSON inválido, timeout, HTTP error, feature desconocida o cifra no soportada activan `grounded_fallback` con código y detalle trazables. El fallback nunca se presenta como GenAI.

`POST /api/what-if` omite recomendaciones para ambas inferencias y `/api/predict-csv` las omite por fila; las predicciones y drivers siguen ejecutándose. Usa `/api/predict` para recomendación individual. Para integración local: `./scripts/preflight_genai.sh`; para benchmark TEST: `python scripts/evaluate_genai.py --cases 30`.

## Arranque

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
