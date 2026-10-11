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

El benchmark Qwen está `complete`, 30 casos, éxito/grounding 29/30. Es evaluación del modelo elegido, no comparación de tres modelos ni prueba de utilidad humana. El groundedness es proxy; schema válido no basta. La elección satisface requisitos locales y reduce una dependencia obligatoria de API externa, sin afirmar que una API externa sea inferior.

Para Nivel 4 de elección, esta tabla mejora la cobertura documental, pero no acredita exhaustividad experimental ni hardware/latencia comparables. No se atribuye una victoria empírica a Qwen.

## Fuentes primarias

- Qwen. (s. f.). [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B).
- Qwen Team. (2025). [Qwen3: Think deeper, act faster](https://qwenlm.github.io/blog/qwen3/).
- Google DeepMind. (s. f.-a). [Gemma 3 4B IT model card](https://huggingface.co/google/gemma-3-4b-it).
- Google DeepMind. (s. f.-b). [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3).
- Mistral AI. (s. f.-b). [Ministral 3 8B Instruct 2512 model card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512).
- Mistral AI. (s. f.-a). [Ministral 3 8B documentation](https://docs.mistral.ai/models/ministral-3-8b-25-12).

Consulta/verificación: 11 de octubre de 2026. APA consolidada y citas del informe: `references.md`. No reejecutar ni sobrescribir la evaluación oficial al revisar la selección.
