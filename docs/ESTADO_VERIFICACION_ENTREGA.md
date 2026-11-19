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


## Implementación complementaria de cuatro brechas (19-11-2026)

Las mejoras siguientes son **implementaciones versionadas, no pruebas de operación ejecutada**. Las cuatro filas conservan el estado PARCIAL hasta que exista evidencia aceptable para el jurado.

1. **R6.2-Cr6 — Productividad humana.** Ya existen `scripts/productivity_study.py`, la plantilla vacía `reports/human_validation/TEMPLATE_results.csv` y `docs/human_efficiency_validation.md`. Para ejecutar un estudio con consentimiento, preparar un CSV de casos con `case_id,difficulty`; después: `python scripts/productivity_study.py assign --participants 12 --cases CASOS.csv --output ASIGNACIONES.csv`. Recopilar los tiempos y puntuaciones reales según la plantilla y ejecutar `python scripts/productivity_study.py analyze --results RESULTADOS_REALES.csv --output INFORME_PRIVADO.json`. **No cargar observaciones identificables en Git. No atribuir mejoras sin participantes reales, consentimiento y revisión de calidad.** El mínimo técnico del script es 6 pares completos; 12 es el tamaño exploratorio recomendado, sin garantía de potencia.
2. **R7.2-Cr4 — Despliegue.** Se añadió `.github/workflows/staging-deployment.yml`, activable manualmente en un runner `self-hosted, linux, prunin-staging` con aprobación de ambiente `staging`. Exige artefactos `0.9.0-academic` previamente autorizados en `/opt/prunin-academic-artifacts/0.9.0-academic`, variables seguras en `/opt/prunin-staging/config.env`, Docker y puerto local disponible. Construye imagen ligada al SHA y despliega contenedor local de *staging*, con health check y fallo explícito cuando falta infraestructura. **Sin runner configurado o ejecución verde no hay prueba de despliegue.** No es CD productivo ni procedimiento de rollback.
3. **R7.2-Cr5 — Recuperación ante fallos.** `scripts/docker_two_replica_failover.sh` conserva prueba de balanceo y continuidad, y ahora además provoca una caída `SIGKILL`, comprueba el incremento de `RestartCount`, espera `/api/ready` y verifica tráfico a través de nginx. Lo ejecuta `quality` cuando el entorno Docker está disponible. **Es Docker y no Kubernetes**; la evidencia queda pendiente de un run exitoso del SHA actualizado. No valida reinicio por fallo exclusivo del health check ni autocuración de un clúster.
4. **R7.2-Cr6 — MLOps.** `scripts/mlops_retraining_gate.py` y sus pruebas exigen drift completo, batch nuevo con SHA distinto al TRAIN, etiquetas verificadas y aprobadas, cohorte mínima y aprobación humana para declarar `ELIGIBLE_FOR_CANDIDATE_TRAINING`. Nunca reentrena ni promueve automáticamente. `.github/workflows/monitored-academic-batch.yml` permite analizar manualmente un **batch nuevo** desde un runner de staging; requiere archivos autorizados en `/opt/prunin-staging/data/`. Un estado `BLOCKED` es la salida esperada cuando falta evidencia, no un error que deba ocultarse. El workflow semanal de datos demo sigue siendo exclusivamente un smoke test, no seguimiento productivo.

**Verificación final obligatoria:** ejecutar pruebas locales y CI del SHA exacto, y aportar trazas de operaciones en staging, mediciones humanas y datasets nuevos antes de modificar los estados oficiales de la rúbrica. La ausencia de cualquiera de esas evidencias deja la brecha abierta.
