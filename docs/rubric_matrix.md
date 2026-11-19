# Matriz de evaluación PAIII 2026 — fuente institucional

**Fuente verificada:** hoja `Rubrica` del archivo institucional `Rubrica_PAIII_2026(2).xlsx`, suministrado para la revisión del 18 de noviembre de 2026. El archivo fuente se conserva fuera de Git; sus **27 criterios** y el texto original del descriptor **Nivel 4: Outstanding** están transcritos con sus evidencias en [RUBRICA_OFICIAL_PAIII_2026.md](RUBRICA_OFICIAL_PAIII_2026.md).

El archivo institucional recibido **no incluye una evaluación individual del proyecto** en las columnas de notas del invitado y mentor. Por ello este contraste no concede nivel 4 ni asigna calificación.

| Estado interno de la evidencia | Criterios | Alcance de la afirmación |
|---|---:|---|
| Demostrado con limitaciones | 15 | El repositorio aporta evidencia técnica o escrita; el máximo nivel aún debe ser evaluado |
| Parcial | 5 | Se requieren pruebas adicionales: elección de modelo, productividad, despliegue, robustez o MLOps |
| Requiere evaluación oral | 7 | La calidad real de voz, estructura, recursos y defensa solo se observa en sustentación |

Las brechas son los códigos `R6.1-Cr2`, `R6.2-Cr6`, `R7.2-Cr4`, `R7.2-Cr5` y `R7.2-Cr6`. En el criterio `R7.2-Cr5`, el descriptor institucional exige **diseñar** mecanismos de tolerancia a fallos, balanceo y recuperación; el manifiesto aporta evidencia de diseño, pero no ejecución productiva. En `R7.2-Cr4` y `R7.2-Cr6` se exigen automatización y prácticas aplicadas, por lo que un diagrama no sustituye la prueba de operación.

Avance del 19-11-2026:

- La comparación controlada y operativa de 30 casos midió Qwen3 8B en ambos modos: 30/30 aceptadas; OpenAI no se ejecutó porque faltaba la clave en el entorno del proceso. No se asigna ventaja comparativa ni se presenta costo OpenAI observado.
- El benchmark HTTP real obtuvo 100/100 respuestas válidas por nivel de concurrencia (1/4/8/16), con p95 de 80.98 a 954.38 ms y throughput estable cerca de 23–24 req/s desde cuatro workers; productividad humana sigue NO MEDIDA.
- También se ejecutaron el instrumento de productividad sin participantes, controles de seguridad del API, monitor offline TRAIN/VALIDATION y actualización del registro MLOps con estados y unidades de métricas explícitos.
- Los cinco criterios siguen en PARCIAL porque faltan OpenAI real, participantes humanos, despliegue operado y retraining continuo.

El resto de los criterios, incluso cuando existen elementos documentados, tienen límites de validación que deben declararse. [Criterios de sustentación](ORAL_EVIDENCE.md) y [manifiesto de entrega](DELIVERY_MANIFEST.md). Las referencias y rúbricas internas históricas de `reports/` son registros de evaluaciones anteriores; no se reinterpretan como calificación del instrumento oficial.
