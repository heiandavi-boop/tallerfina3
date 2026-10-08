# PRUNIN AI Core Playground

## Objetivo

La demo ejecuta inferencia real contra los artefactos `.joblib`; no contiene resultados predeterminados en el frontend.

## Selección de modelo

1. Si `PRUNIN_ARTIFACT_DIR` está definido, usa ese directorio.
2. Si existe `artifacts/0.9.0-academic/health.joblib`, usa el modelo académico.
3. En caso contrario usa `artifacts/demo-0.1.0` y lo muestra explícitamente como `synthetic_demo`.

Esto permite ensayar la aplicación antes de finalizar el reentrenamiento sin presentar el modelo demo como resultado definitivo.

## Variables públicas

El formulario incluye todas las features entrenadas del esquema V9 académico:

- `planned_duration_weeks`
- `planned_budget`
- `baseline_scope_units`
- `sector`
- `project_type`
- `methodology`
- `complexity`
- `criticality`
- `true_progress`
- `spi`
- `cpi`
- `team_utilization`
- `team_capacity_ratio`
- `average_productivity`
- `defect_rate`
- `rework_ratio`
- `scope_growth_ratio`
- `dependency_delay_days`
- `normalized_risk_exposure`
- `governance_health_score`

Además acepta `team_stability` y `collaboration_level` para el `team_health_index`. Estas dos señales no se introducen silenciosamente en el modelo supervisado.

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

La demo nunca depende de un LLM para funcionar. Por defecto usa recomendaciones determinísticas fundamentadas en drivers observados. Si se desea habilitar generación local con Ollama:

```bash
export PRUNIN_ENABLE_OLLAMA=1
export PRUNIN_OLLAMA_MODEL=qwen3:8b
./scripts/run_playground.sh
```

Si Ollama no responde, se usa automáticamente el fallback fundamentado.

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
