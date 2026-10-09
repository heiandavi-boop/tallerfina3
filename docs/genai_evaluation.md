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

## Eficiencia

La latencia de automatización se mide automáticamente. El ahorro de tiempo frente a un proceso humano **no se inventa**. Para cuantificarlo:

1. medir el tiempo manual de interpretar un caso y redactar una recomendación;
2. registrar la mediana observada;
3. ejecutar:

```bash
python scripts/benchmark_efficiency.py \
  --manual-seconds-per-case 120
```

El valor `120` es solo un ejemplo de uso del comando; no debe convertirse en resultado académico si no fue medido.
