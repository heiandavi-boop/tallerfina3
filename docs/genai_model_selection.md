# Selección multicriterio del modelo generativo

## Requisitos y decisión

PRUNIN busca interpretación en español, ejecución local, exposición mínima de datos, integración mantenible y salida JSON verificable para apoyar al director de proyecto. Qwen3 8B se conserva por su encaje operativo y la integración existente. No predice Health, Delay ni Cost. La comparación es técnico-documental, no un benchmark empírico donde Qwen haya ganado a Gemma y Ministral.

## Tabla 1. Alternativas frente a los requisitos PRUNIN

| Criterio | Qwen3 8B | Gemma 3 4B | Ministral 3 8B |
|---|---|---|---|
| Español/multilingüe | Multilingüe; evaluado localmente en español | Multilingüe; español no evaluado por PRUNIN | Español incluido; no evaluado por PRUNIN |
| Ejecución local | Soportada y usada con Ollama | Pesos disponibles para ejecución local | Orientado a ejecución local/edge |
| Privacidad | Datos permanecen locales si runtime/configuración lo mantienen | Posible localmente, no probado aquí | Posible localmente, no probado aquí |
| Tamaño publicado | 8.2B parámetros | Variante 4B | Nombre 8B; incluye componente visual |
| Hardware | Depende de cuantización/contexto; sin mínimo universal certificado | Menor variante; consumo exacto no medido aquí | Ficha declara caber en 12 GB VRAM en FP8; no requisito universal |
| Licencia | Apache 2.0 | Términos Gemma; no Apache 2.0 | Apache 2.0 |
| JSON estructurado | format=json + validación implementada | Requiere integración/validador; no probado | JSON anunciado por fabricante; no probado aquí |
| Compatibilidad operativa | recommendations.py y preflight reales | Adaptación y validación pendientes | Adaptación y validación pendientes |
| Latencia | Mediana 3.092645 s; p95 6.63472 s en benchmark local | Desconocida para PRUNIN | Desconocida para PRUNIN |
| Facilidad de integración | Implementada y con fallback | Coste de integración no medido | Coste de integración no medido |
| Contexto publicado | 32768 nativo; 131072 con YaRN | 128K en variante considerada | 256K publicado |
| Riesgos/trade-offs | Latencia individual, errores semánticos y dependencia del runtime | Condiciones de licencia y calidad local por verificar | Requisitos de runtime/cuantización y calidad local por verificar |

Fuente: fichas oficiales enlazadas abajo; la latencia Qwen proviene exclusivamente de `reports/genai/qwen3-8b-evaluation.json`. Los tamaños y ventanas publicados no son mediciones PRUNIN ni equivalen al contexto de Ollama configurado. La tabla permite valorar alternativas sin inferir cuál es más rápido por tamaño.

## Hardware y latencia: lo que no se midió

La memoria incluye pesos, caché KV y runtime; depende de precisión, cuantización, longitud y concurrencia. No se certificó un mínimo RAM/VRAM para Qwen o Gemma. El despliegue local Qwen es evidencia funcional del equipo usado, no garantía para cualquier portátil. Para una migración futura se necesitaría registrar hardware, cuantización, contexto efectivo y latencia con las mismas entradas; no se instalaron alternativas en el cierre.

No se asignan puntuaciones, pesos ni ranking numérico inventados. Un contexto mayor no es ventaja demostrada en la tarea PRUNIN, cuyo prompt es evidencia estructurada breve. El coste temporal de Qwen puede afectar al análisis individual, pero batch y What-if omiten LLM; no se probó escalamiento bajo carga.

## Evidencia específica disponible

### Evidencia empírica nueva

`reports/genai/comparison/benchmark_summary.json` y `benchmark_raw.csv` registran una comparación independiente con 30 casos comunes, misma evidencia, constructor de prompt, validador, temperatura 0.1, timeout de 30 s y hardware. El estado global es `partial`: `qwen3:8b` estaba instalado; `gemma3:4b` y `ministral:8b` se marcaron `not_available`, sin descarga automática.

En esta corrida nueva de Qwen: generación/schema/grounding proxy/actionability 29/30 (0.9667), cifras no soportadas 0/30, timeout 0/30, JSON inválido 1/30, mediana 6336.35 ms y p95 13340.74 ms. La muestra y latencia difieren de la evaluación oficial congelada de 30 casos, que permanece en `reports/genai/qwen3-8b-evaluation.json` (29/30, una cifra no soportada, mediana 3092.645 ms, p95 6634.72 ms). Son corridas distintas, no una sustitución ni una mejora comparativa de Qwen.

### Evidencia documental y disponibilidad

Las comparaciones de licencia, contexto, capacidad publicada e integración provienen de fichas oficiales enlazadas abajo. Los claims de tamaño/contexto no son mediciones PRUNIN. Gemma y Ministral no produjeron resultados empíricos en esta máquina. Por ello, la selección de Qwen sigue siendo técnico-operativa; no existe ranking empírico entre los tres.

El groundedness es proxy; schema válido no basta para semántica. Esta corrida tampoco mide utilidad humana ni productividad. Los artefactos oficiales Qwen anteriores no se modificaron.

Para Nivel 4 de elección, esta tabla mejora la cobertura documental, pero no acredita exhaustividad experimental ni hardware/latencia comparables. No se atribuye una victoria empírica a Qwen.

## Verificación local adicional: 8 de noviembre de 2026

[environment.json](../reports/audit_2026-11-08/environment.json) registra Ollama, digest, cuantización y tamaño de los modelos instalados, memoria física y espacio libre. Qwen3 8B Q4_K_M está disponible; Gemma y Ministral no. El tag futuro correcto es `ministral-3:8b`: su manifiesto público respondió 200, mientras `ministral:8b` respondió 404. Esto corrige el comando futuro, no los reportes históricos.

Los manifiestos públicos, consultados sin descargar blobs, sumaron 3,350,272,259 bytes para Gemma 3 4B y 6,022,236,102 para Ministral 3 8B. Son necesidades de almacenamiento de esas distribuciones, no mínimos RAM/VRAM certificados. El equipo tiene 24 GiB de memoria unificada y aproximadamente 519 GiB libres; pesos, caché KV, contexto, procesos y concurrencia requieren margen adicional. La memoria libre efectiva y el pico de inferencia de candidatos ausentes no se midieron. No se autorizaron ni realizaron descargas.

Para completar la comparación, obtener autorización, fijar los digests/cuantizaciones, contexto, seed si aplica y presupuesto de tokens, registrar hardware/estado de procesos y ejecutar `benchmark_genai_candidates.py --output-dir <DIRECTORIO_NUEVO>` con los mismos 30 casos para todos los candidatos. El contrato nuevo usa evidence-v2 y 1200 tokens: debe repetirse Qwen en esa misma corrida, no combinar sus métricas con el contrato histórico. Medir memoria con un instrumento validado o conservarla como no medida. Evaluar semántica y utilidad humana por separado con revisión ciega. Sin esa comparación, R6.1-Cr2 permanece PARCIAL y no existe ganador empírico.

## Fuentes primarias

- Qwen. (s. f.). [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B).
- Qwen Team. (2025). [Qwen3: Think deeper, act faster](https://qwenlm.github.io/blog/qwen3/).
- Google DeepMind. (s. f.-a). [Gemma 3 4B IT model card](https://huggingface.co/google/gemma-3-4b-it).
- Google DeepMind. (s. f.-b). [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3).
- Mistral AI. (s. f.-b). [Ministral 3 8B Instruct 2512 model card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512).
- Mistral AI. (s. f.-a). [Ministral 3 8B documentation](https://docs.mistral.ai/models/ministral-3-8b-25-12).

Consulta/verificación documental: 8 de noviembre de 2026. APA consolidada y citas del informe: `references.md`. La evaluación oficial permanece intacta; la corrida comparativa nueva se conserva en `reports/genai/comparison/`.
