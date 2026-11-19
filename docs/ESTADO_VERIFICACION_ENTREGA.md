# Estado verificable de la entrega — PAIII

> Este documento registra **evidencia técnica y limitaciones**, no una calificación ni una certificación de nivel 4. La exposición oral y los materiales de presentación se conservan **fuera de Git**.

## Alcance confirmado del prototipo

PRUNIN AI Core es la capa de inteligencia de PRUNIN/Proyecta360 para apoyar decisiones sobre **riesgo de retraso y sobrecosto de proyectos**. Integra React, FastAPI, predictores LightGBM (Health, Delay y Cost), drivers y evidencia estructurada, recomendaciones locales con Ollama/Qwen3 8B y fallback determinístico. GPT-OSS 20B es una **alternativa comparada experimentalmente**, no un segundo motor obligatorio ejecutado en simultáneo. Team Health es una heurística operacional; no es una medición psicológica.

La evidencia académica utiliza **Mendeley Data v2, datos sintéticos externos** (4.000 proyectos / 72.549 snapshots, split por proyecto 2.800 TRAIN, 600 VALIDATION y 600 TEST). No se declara validación con empresas reales.

## Resultados que sí se pueden citar

| Prueba | Resultado | Evidencia |
|---|---|---|
| Promesa de detección temprana Risk Alert | 359/473 = **75,90 %** de proyectos que finalmente están en riesgo detectados al corte del 60 %; cobertura TEST **96 %** | `reports/promise_validation/risk_alert_metrics.json` |
| Recall de la categoría Critical exacta | **56,82 %** al snapshot final; no confundir con Risk Alert | `reports/promise_validation/risk_alert_metrics.json` |
| Health Macro F1 | **0,627576** (evaluación por proyecto con snapshot final) | `README.md` y reportes académicos |
| Delay MAE | **27,710468 días** frente a baseline **27,850313**; ganancia marginal | `README.md` y reportes académicos |
| Cost MAE | **0,147158 puntos porcentuales**; condicionado por estructura del dataset sintético | `README.md` y reportes académicos |
| Qwen3 8B vs. GPT-OSS 20B | **30/30 vs. 29/30** aceptadas, medianas **8,6 vs. 7,0 s**, memoria residente **5,5 vs. 11,9 GB**; **empate técnico** | `reports/genai/qwen_vs_gptoss_2026/comparison_report.md` |

**Precisión conceptual:** 75,90 % **no es accuracy** del clasificador ni recall de la clase Critical exacta; es la detección de la cohorte de proyectos con riesgo final a un corte temporal específico. La evaluación del LLM utiliza validadores automáticos, sin juicio semántico humano.

## Estado de la rúbrica oficial (27 criterios)

El documento `docs/RUBRICA_OFICIAL_PAIII_2026.md` registra **16 demostrados con limitaciones, 4 parciales y 7 que requieren evaluación humana**. Los estados son una autoevaluación documental, no notas concedidas.

### Cuatro brechas abiertas

| Código | Estado y alcance observado | Evidencia necesaria para cerrar totalmente |
|---|---|---|
| R6.2-Cr6 | Parcial: benchmark de API, throughput y batch | Medición comparativa de usuarios reales para afirmar productividad humana |
| R7.2-Cr4 | Parcial: CI construye y prueba contenedores | Ejecución demostrable del ciclo de despliegue automatizado en un entorno identificado |
| R7.2-Cr5 | Parcial: balanceo y failover de dos contenedores; restauración manual | Verificación de recuperación automática y tolerancia a fallos en entorno operativo |
| R7.2-Cr6 | Parcial: versionado, logging, drift offline y workflow demo | Evidencia de monitoreo de datos cambiantes y ciclo continuo de retraining validado |

La arquitectura Kubernetes cuenta con verificación estática; **no** acredita operación en clúster. Las pruebas HTTP no acreditan escalabilidad del motor LLM ni productividad de personas.

### Siete criterios de oralidad

RA2-F1 a RA2-F7 requieren presentación y evaluación humana: estructura, claridad, lenguaje, técnicas vocales, recursos de apoyo, lenguaje no verbal y defensa argumentada. Ningún script de CI puede aprobarlos.

## Lista de cierre obligatoria

- [ ] Comprobar aprobación de `quality` en **el SHA exacto** destinado a entrega; no reutilizar la evidencia de otro commit.
- [ ] Ejecutar `./scripts/preflight_demo.sh` con los artefactos `0.9.0-academic` presentes, no solo el demo sintético.
- [ ] Probar manualmente la interfaz: predicción, Risk Alert, recomendaciones de Qwen, fallback, CSV por fila, What-if y exportación JSON.
- [ ] Verificar integridad de hashes/partición TEST y compatibilidad de los artefactos académicos.
- [ ] Contrastar de nuevo las 27 filas de rúbrica con evidencia ejecutada.
- [ ] Revisar nombre oficial del programa, formato de entrega y bibliografía exigida.
- [ ] Ensayar y evaluar independientemente la defensa de los siete criterios RA2.
- [ ] Mantener presentaciones, preguntas del jurado, apuntes y grabaciones únicamente en `material_privado/` local.

**Conclusión:** hay evidencia experimental relevante y reproducible, pero **el cumplimiento integral del máximo nivel no está certificado**. No inventar datos de productividad, resultados empresariales, recuperación automática, evaluaciones humanas ni CI pendiente.
