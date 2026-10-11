# Evaluación de IA generativa

## Qué se evalúa

La rúbrica exige interpretar el desempeño de la capa generativa en función del objetivo empresarial. PRUNIN utiliza un benchmark reproducible sobre proyectos del conjunto TEST, sin usar esos resultados para modificar los modelos predictivos.

El script es:

```bash
python scripts/evaluate_genai.py \
  --artifact artifacts/0.9.0-academic \
  --input data/processed/mendeley_core.csv \
  --model qwen3:8b \
  --cases 30
```

Requiere Ollama y el modelo solicitado disponibles. El timeout viene de `PRUNIN_OLLAMA_TIMEOUT_SECONDS` (default 30 s), o puede reemplazarse con `--timeout`. Si Ollama no está activo, el script genera `status=unavailable` y termina sin inventar métricas. Una evaluación completa escribe JSON y CSV bajo `reports/genai/`.

Comprobación local de integración, incluido API status y una generación grounded:

```bash
export PRUNIN_ENABLE_OLLAMA=1
export PRUNIN_OLLAMA_MODEL=qwen3:8b
export PRUNIN_OLLAMA_TIMEOUT_SECONDS=30
./scripts/preflight_genai.sh
```

`PRUNIN_OLLAMA_WARMUP=1` habilita warm-up acotado al iniciar el API; está apagado por defecto y fuera de CI. `PRUNIN_GENAI_DEBUG=1` habilita raw response/JSON parseado únicamente en evidencia técnica.

## Métricas

- **generation_success_rate**: respuestas aceptadas por el validador.
- **schema_valid_rate**: salida con el contrato JSON requerido.
- **evidence_feature_valid_rate**: todas las variables citadas pertenecen a los drivers permitidos.
- **grounded_response_rate**: proxy determinístico que exige esquema válido, evidencia allow-listed y ausencia de nuevas afirmaciones numéricas.
- **actionability_rate**: cada recomendación contiene una acción no vacía.
- **unsupported_numeric_claim_rate**: frecuencia de cifras nuevas en texto generado.
- **timeout_rate**: frecuencia de solicitudes que exceden el timeout configurado.
- **invalid_json_rate**: frecuencia de respuestas vacías o que no pueden parsearse estrictamente como JSON.
- **latency_ms_median / p95**: costo temporal local.

### Límite metodológico

El indicador de groundedness es un **proxy de ingeniería**, no una prueba de verdad semántica ni causalidad. Las cifras se comparan contra valores de drivers, referencias, outcomes, probabilidades y porcentajes equivalentes de la evidencia estructurada; las cifras nuevas se rechazan. Para una validación productiva debe agregarse revisión humana ciega sobre pertinencia, utilidad y daño potencial.

## Seguridad por diseño

Si la salida generativa no cumple el contrato, PRUNIN la descarta y activa `grounded_fallback`. Códigos como `ollama_timeout`, `invalid_json`, `unknown_evidence_feature` y `unsupported_numeric_claim` quedan en trazabilidad; la raw response no se expone salvo debug. Sin drivers de riesgo, `recommendations: []` con resumen prudente es válido; con drivers, una lista vacía falla validación. La predicción ML permanece disponible aunque Ollama esté apagado o falle.

What-if y CSV no llaman al LLM. `inference_ms` se conserva como total y `timing.ml_and_drivers_ms`, `timing.genai_ms`, `timing.total_ms` separan sus componentes en `/api/predict`.

## Resultados versionados

Reporte: `reports/genai/qwen3-8b-evaluation.json`, status=complete, 30 casos con snapshot TEST más reciente y al menos un driver de incremento de riesgo.

| Indicador | Valor observado |
|---|---:|
| generation_success_rate | 0.9666666667 |
| schema_valid_rate | 1.0000000000 |
| evidence_feature_valid_rate | 1.0000000000 |
| grounded_response_rate | 0.9666666667 |
| actionability_rate | 1.0000000000 |
| unsupported_numeric_claim_rate | 0.0333333333 |
| timeout_rate | 0.0000000000 |
| invalid_json_rate | 0.0000000000 |
| latency_ms_median | 3092.6450000000 |
| latency_ms_p95 | 6634.7200000000 |

Son 29 respuestas aceptadas y una rechazada por cifra no soportada. Schema/features válidas y acción no vacía no prueban calidad semántica ni utilidad real. Muestra condicionada y equipo local; no benchmark comparativo de tres modelos. No se reejecutó el benchmark en este cierre.

## Eficiencia

Ver `efficiency_evaluation.md`: baseline humano pendiente. Medir cinco casos, conservar tiempos y respuestas, calcular mediana real y solo entonces ejecutar:

```bash
python scripts/benchmark_efficiency.py \
  --manual-seconds-per-case <MEDIANA_REAL>
```

La latencia GenAI no es tiempo completo de la tarea ni evidencia de ahorro humano. Sin medición, Cr6 permanece pendiente.

## Interpretación del rechazo y valor estratégico

El caso `mendeley::PROJ_0840` (critical) conservó esquema y evidence_features válidos pero falló por `unsupported_numeric_claim`. El validador impidió aceptar una respuesta con cifras no soportadas. Ese rechazo es evidencia útil del guardrail, no prueba de ausencia de otros errores semánticos. Medir actionability como acción no vacía no demuestra que la acción sea pertinente, viable o efectiva. El apoyo a síntesis/interpretación está implementado; su valor profesional y productividad requieren revisión humana y el protocolo de eficiencia.

No se selecciona un modelo predictivo ni se modifica TEST utilizando este benchmark de explicaciones. No se reejecutó ni sobrescribió el reporte en el cierre.
