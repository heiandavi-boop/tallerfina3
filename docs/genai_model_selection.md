# Selección del modelo generativo

## Objetivo empresarial

La capa generativa de PRUNIN no reemplaza los modelos predictivos. Su función es convertir predicciones estructuradas y drivers locales en explicaciones y acciones breves para un director de proyecto, manteniendo trazabilidad y evitando afirmar causalidad.

Los requisitos del caso son:

1. ejecución local para proteger información de proyectos;
2. buen soporte de español;
3. capacidad de seguir instrucciones y producir JSON estructurado;
4. tamaño razonable para equipos de desarrollo locales;
5. licencia abierta y despliegue sin dependencia obligatoria de un proveedor externo;
6. integración sencilla con Ollama;
7. fallback determinístico cuando la generación falle.

## Alternativas consideradas

| Alternativa | Evidencia técnica | Ventajas para PRUNIN | Trade-off |
|---|---|---|---|
| Qwen3 8B | 8B, contexto de 128K, 119 idiomas/dialectos, Apache 2.0 y soporte recomendado para Ollama/LM Studio/llama.cpp | Español, ejecución local, tamaño compatible con laptop, modo no-thinking para respuestas cortas, buen encaje con JSON/instrucciones | Requiere benchmark específico del caso antes de declarar calidad |
| Gemma 3 4B | modelo abierto ligero, 128K, más de 140 idiomas y diseñado también para laptops/desktop | Menor tamaño y buena portabilidad local | La comparación de calidad para este caso debe medirse; no se asume superioridad |
| Ministral 3 8B | modelo open-weight orientado a edge/local, contexto de 256K y structured outputs | Muy buen candidato para despliegue local y salida estructurada | Integración del proyecto actual está implementada sobre Ollama/Qwen; cambiar exige benchmark y compatibilidad operativa |

Fuentes oficiales consultadas:

- Qwen Team. (2025). *Qwen3: Think Deeper, Act Faster*. https://qwenlm.github.io/blog/qwen3/
- Qwen. *Qwen3-8B model card*. https://huggingface.co/Qwen/Qwen3-8B
- Google DeepMind. *Gemma 3 model card*. https://ai.google.dev/gemma/docs/core/model_card_3
- Mistral AI. *Ministral 3 8B*. https://docs.mistral.ai/models/ministral-3-8b-25-12

## Decisión

Qwen3 8B se mantiene como modelo generativo principal de la versión académica porque satisface los requisitos operativos de privacidad local, español, tamaño y ejecución vía Ollama. Esta decisión es **técnica y operativa**, no una afirmación de que Qwen3 sea universalmente mejor.

La selección final de calidad debe validarse con el benchmark de PRUNIN:

```bash
PRUNIN_ENABLE_OLLAMA=1 \
PRUNIN_OLLAMA_MODEL=qwen3:8b \
python scripts/evaluate_genai.py --cases 30
```

Los resultados se guardan en `reports/genai/`. Si el benchmark no ha sido ejecutado, la documentación no debe presentar porcentajes de calidad, grounding o latencia como hechos.

## Criterio estratégico

El modelo generativo recibe únicamente evidencia estructurada: predicciones, Team Health resumido y drivers locales. No decide el Health ni crea probabilidades. Su valor es reducir la carga de interpretación y producir recomendaciones trazables sin exponer información a una API externa por defecto.
