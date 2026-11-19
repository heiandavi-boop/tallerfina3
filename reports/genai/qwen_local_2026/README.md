# Ejecución local de Qwen3 8B — evidencia de noviembre de 2026

Este directorio conserva únicamente los resultados **reales** de Qwen3 8B en Ollama, extraídos sin modificaciones de contenido del registro experimental previo. No es una nueva inferencia ni una comparación entre modelos.

Se registraron 30 casos en modo controlado y 30 en modo operativo local, más 15 intentos de repetibilidad. El modelo local obtuvo 30/30 respuestas aceptadas en ambos modos por el validador proxy. La latencia mediana y p95 fueron 8114.68 y 19783.22 ms (controlado), y 8305.30 y 18347.63 ms (operativo). Cinco casos repetidos tres veces mantuvieron estabilidad de respuesta. Grounding proxy no representa evaluación humana de utilidad o causalidad.

Archivos: `benchmark_cases.csv`, `qwen_results.csv`, `qwen_summary.json`, `execution_manifest.json`. El manifiesto identifica hardware, origen, hashes de entrada y fecha. Esta prueba es independiente del benchmark académico congelado, que sigue disponible en `reports/genai/qwen3-8b-evaluation.json`.

La elección de Qwen se justifica para el prototipo local; la comparación exhaustiva con alternativas locales permanece pendiente.
