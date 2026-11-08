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
- **actionability_rate**: cada acción comienza con un verbo permitido y describe una tarea ejecutable con detalle mínimo.
- **action_structure_valid_rate**: prioridad enum válida, título, evidencia allow-listed, razón, acción concreta y follow-up completos, hasta cuatro elementos.
- **follow_up_present_rate**: todas las acciones incluyen qué señal revisar después.
- **unsupported_numeric_claim_rate**: frecuencia de cifras nuevas en texto generado.
- **timeout_rate**: frecuencia de solicitudes que exceden el timeout configurado.
- **invalid_json_rate**: frecuencia de respuestas vacías o que no pueden parsearse estrictamente como JSON.
- **latency_ms_median / p95**: costo temporal local.

La evaluación Qwen oficial congelada definió `actionability_rate` como una acción no vacía. La evaluación nueva de acciones usa una definición más estricta: la acción empieza con verbo permitido, expresa una tarea concreta y cada recomendación tiene un `follow_up`; por eso las dos tasas no deben compararse como una única métrica homogénea.

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

Son 29 respuestas aceptadas y una rechazada por cifra no soportada. Schema/features válidas y acción no vacía no prueban calidad semántica ni utilidad real. Muestra condicionada y equipo local; este reporte oficial no es un benchmark comparativo completo de tres modelos. No se reejecutó ni sobrescribió el benchmark oficial en este cierre.

## Benchmark comparativo y concurrencia local

`scripts/benchmark_genai_candidates.py` ejecuta 30 casos TEST comunes para cada tag Ollama instalado, usando el mismo `build_grounded_prompt`, `generate_ollama_grounded`/validador, JSON, temperatura 0.1, timeout y hardware de la corrida. No descarga modelos. El reporte comparativo generado en este cierre está en `reports/genai/comparison/`; su estado `partial` indica Qwen disponible y Gemma/Ministral `not_available`. Sus métricas pertenecen a una nueva corrida y no reemplazan el resultado oficial descrito arriba.

`scripts/benchmark_genai_concurrency.py` ejecutó 30 casos por nivel en esta máquina. Resultado: éxito 96.67/93.33/73.33/36.67 %, timeout 0/0/26.67/63.33 %, p50 6256.955/12305.81/28567.37/30002.805 ms, p95 15337.88/23252.48/30003.31/30005.73 ms y throughput 0.1335/0.1402/0.1475/0.2499 req/s para concurrencia 1/2/4/8. Se observa throughput más alto junto con caída del éxito; no se infiere capacidad productiva. Tabla, hardware y datos crudos: `reports/genai/concurrency/`. Es una prueba local exploratoria, no una prueba productiva ni evidencia de escalabilidad. Si Ollama/modelo no están disponibles, los scripts registran el benchmark no ejecutado y terminan sin descargar nada.

## Eficiencia humana pendiente

El benchmark API en `efficiency_evaluation.md` mide eficiencia operacional automatizada, no tiempo o productividad de una persona. Para investigar este resultado distinto, usar el protocolo `human_efficiency_validation.md` y la plantilla vacía de `reports/human_validation/`. No completar datos retrospectivamente ni convertir latencia LLM en ahorro humano. El script histórico `benchmark_efficiency.py` requiere un baseline manual observado; no pasar valores supuestos:

```bash
python scripts/benchmark_efficiency.py \
  --manual-seconds-per-case <MEDIANA_REAL>
```

## Evaluación nueva de acciones

La evaluación de acciones usa el validador nuevo y se guarda en una ruta independiente; no sobrescribe `reports/genai/qwen3-8b-evaluation.json`:

```bash
PRUNIN_ENABLE_OLLAMA=1 PRUNIN_OLLAMA_MODEL=qwen3:8b \
PYTHONPATH=src python scripts/evaluate_genai.py --cases 20 \
  --output reports/genai/action_recommendations/qwen3-8b-actions-v3.json
```

Reporte V3 ejecutado: 20/20 casos; `generation_success_rate`, `schema_valid_rate`, `evidence_feature_valid_rate`, `grounded_response_rate`, `action_structure_valid_rate`, `follow_up_present_rate` y `actionability_rate` = 1.0; claims numéricos no soportados, timeout y JSON inválido = 0. Mediana 7054.585 ms, p95 17741.41 ms. El JSON y CSV están en `reports/genai/action_recommendations/`; V1/V2 se conservan para trazabilidad de la iteración.

Estas son métricas estructurales de una muestra sintética condicionada a drivers TEST; no equivalen a utilidad humana, calidad profesional o causalidad. Ejemplo Qwen y fallback determinístico se documentan en `reports/genai/action_recommendations/README.md`.

La latencia GenAI no es tiempo completo de la tarea ni evidencia de ahorro humano. Sin medición, Cr6 permanece pendiente.

## Interpretación del rechazo y valor estratégico

El caso `mendeley::PROJ_0840` (critical) conservó esquema y evidence_features válidos pero falló por `unsupported_numeric_claim`. El validador impidió aceptar una respuesta con cifras no soportadas. Ese rechazo es evidencia útil del guardrail, no prueba de ausencia de otros errores semánticos. Medir actionability como acción no vacía no demuestra que la acción sea pertinente, viable o efectiva. El apoyo a síntesis/interpretación está implementado; su valor profesional y productividad requieren revisión humana y el protocolo de eficiencia.

No se selecciona un modelo predictivo ni se modifica TEST utilizando este benchmark de explicaciones. No se reejecutó ni sobrescribió el reporte en el cierre.
