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

Requiere Ollama disponible. Si Ollama no está activo, el script genera un reporte `status=unavailable` y termina sin inventar métricas.

## Métricas

- **generation_success_rate**: respuestas aceptadas por el validador.
- **schema_valid_rate**: salida con el contrato JSON requerido.
- **evidence_feature_valid_rate**: todas las variables citadas pertenecen a los drivers permitidos.
- **grounded_response_rate**: proxy determinístico que exige esquema válido, evidencia allow-listed y ausencia de nuevas afirmaciones numéricas.
- **actionability_rate**: cada recomendación contiene una acción no vacía.
- **unsupported_numeric_claim_rate**: frecuencia de cifras nuevas en texto generado.
- **latency_ms_median / p95**: costo temporal local.

### Límite metodológico

El indicador de groundedness es un **proxy de ingeniería**, no una prueba de verdad semántica ni causalidad. Para una validación productiva debe agregarse revisión humana ciega sobre pertinencia, utilidad y daño potencial.

## Seguridad por diseño

Si la salida generativa no cumple el contrato de grounding, PRUNIN la descarta y activa `grounded_fallback`. La predicción ML permanece disponible aunque Ollama esté apagado o falle.

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
