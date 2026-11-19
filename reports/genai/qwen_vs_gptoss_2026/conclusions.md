# Conclusiones

1. Se ejecutaron los mismos 30 casos TEST con Qwen3 8B y GPT-OSS 20B en Apple M5 Pro, con entrada, prompt, esquema, validador, temperatura y presupuesto idénticos, más 3 repeticiones de 5 casos por modelo.
2. Puntajes ponderados: Qwen3 8B 0.981, GPT-OSS 20B 0.987. La matriz **no declara un ganador defendible**: La diferencia ponderada (0.006) es menor que el margen defendible (0.03). El ganador cambia en el análisis de sensibilidad: sin_latencia, latency_-50%.
3. Prueba de McNemar exacta sobre la aceptación pareada de los 30 casos: 1 caso aceptado solo por Qwen3 8B y 0 casos solo por GPT-OSS 20B; p = 1.0000. Con 30 casos la diferencia de aceptación no es estadísticamente significativa (α = 0,05); el resultado debe leerse como evidencia direccional.
4. Capacidad de ejecución local (fuera de la matriz, medida con `/api/ps`): Qwen3 8B: 5.5 GB residentes, mediana 8.6 s, aceptación 100.0 %; GPT-OSS 20B: 11.9 GB residentes, mediana 7.0 s, aceptación 96.7 %. En un equipo de 24 GB la memoria residente condiciona la convivencia con el navegador, el backend y otros procesos.
5. La evaluación es exclusivamente automática; no existe evaluación semántica humana de las recomendaciones.
6. El modelo predeterminado de PRUNIN sigue siendo Qwen3 8B; cualquier cambio requiere decisión explícita.

## Frente a la rúbrica

- **R6.1-Cr2 (elección de IA generativa)**: la elección queda sustentada en una comparación experimental reproducible entre dos arquitecturas distintas (densa vs. MoE), con criterios ponderados explícitos, sensibilidad y prueba pareada. La amplitud de alternativas se limita a dos modelos locales (sin servicios externos por diseño), lo cual debe declararse como limitación ante el descriptor de Nivel 4.
- **R6.1-Cr4 (interpretación crítica)**: se interpretan los indicadores con sus límites (validador conservador, no determinismo, potencia estadística, ausencia de evaluación humana) y se separan explícitamente métricas automáticas de juicio humano.
