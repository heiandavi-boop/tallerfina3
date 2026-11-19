# Comparación experimental OpenAI vs. Ollama — PRUNIN AI Core

Ejecución: 2026-11-19T00:26:38+00:00 → 2026-11-19T00:38:44+00:00 · commit `4ed4e7b28ae683e691938678e439acdbceb1d3d5` · artefacto `0.9.0-academic`.

Criterio académico: **R6.1-Cr2** (selección del modelo generativo) y **R6.1-Cr4** (interpretación de la evaluación).

## Disponibilidad real de proveedores

| Proveedor | Modelo | Disponible | Diagnóstico |
|---|---|---|---|
| openai | `gpt-4.1` | no | openai_key_missing |
| ollama | `qwen3:8b` | sí | digest `500a1f067a9f` · Q4_K_M |

Un proveedor no disponible no tiene filas en `benchmark_results.csv`: no se fabrican resultados.

## Benchmark controlado (contrato común: 4 acciones, 180 caracteres)

| Métrica | ollama |
|---|---|
| Éxito de generación | 1.0 |
| Esquema válido | 1.0 |
| Respuesta fundamentada | 1.0 |
| Accionabilidad | 1.0 |
| Cifras no soportadas | 0.0 |
| Contradicciones | 0.0 |
| Timeouts | 0.0 |
| Acciones aceptadas (media) | 1.4 |
| Latencia mediana (ms) | 8114.68 |
| Latencia p95 (ms) | 19783.22 |
| Latencia media (ms) | 10448.58 |
| Costo medio (USD) | — |
| Costo total (USD) | — |

## Benchmark operativo (OpenAI 8 acciones / Ollama 4, como en la aplicación)

| Métrica | ollama |
|---|---|
| Éxito de generación | 1.0 |
| Esquema válido | 1.0 |
| Respuesta fundamentada | 1.0 |
| Accionabilidad | 1.0 |
| Cifras no soportadas | 0.0 |
| Contradicciones | 0.0 |
| Timeouts | 0.0 |
| Acciones aceptadas (media) | 1.4 |
| Latencia mediana (ms) | 8305.3 |
| Latencia p95 (ms) | 18347.63 |
| Latencia media (ms) | 10039.66 |
| Costo medio (USD) | — |
| Costo total (USD) | — |

## Repetibilidad

```json
{
  "ollama": {
    "cases": 5,
    "runs_per_case": 3,
    "identical_response_rate": 1.0,
    "stable_schema_rate": 1.0,
    "stable_acceptance_rate": 1.0,
    "stable_feature_set_rate": 1.0,
    "action_count_range_median": 0,
    "latency_cv_median": 0.1095
  }
}
```

## Presupuesto OpenAI

Límite 5.0 USD; costo estimado registrado 0.0 USD en 0 llamadas; bloqueadas 0. Contador de costo estimado previo a cada llamada; no equivale a un límite de facturación garantizado por OpenAI.

## Matriz de decisión

| Criterio | Ollama (qwen3:8b) | OpenAI (API) |
|---|---|---|
| Privacidad | Datos permanecen en el equipo | Indicadores se transfieren al proveedor externo |
| Ejecución local / conectividad | Funciona sin Internet | Requiere conectividad y disponibilidad del servicio |
| Recursos computacionales | Requiere ~5,2 GB y CPU/GPU local | Sin carga local; depende de cuota y límites |
| Costo variable | Sin costo por token; costo de hardware/energía | Costo por token medido en este benchmark |
| Seguridad de credenciales | No requiere clave | Requiere custodia de clave y control de presupuesto |
| Mantenibilidad | Versionado por digest del modelo local | Los modelos de API tienen ciclo de vida y pueden retirarse; el modelo es configurable |
| Escalabilidad | Limitada por el hardware del servidor | Escala con límites de tasa del proveedor |
| Calidad / groundedness | Ver tablas medidas | Ver tablas medidas |
| Latencia | Ver tablas medidas | Ver tablas medidas |

## Lectura

Groundedness es un proxy determinístico (esquema, procedencia feature/fuente, cifras literales, ausencia de contradicciones, acción y seguimiento verificables); no establece verdad semántica ni utilidad humana. Ningún juez LLM ni evaluador humano participó en estas métricas.

**Comparación incompleta:** al menos un proveedor no estuvo disponible; la selección no puede apoyarse en una comparación empírica homogénea hasta ejecutar ambos.
