# Cierre final — PRUNIN AI Core

**Veredicto técnico local: LISTO PARA ENTREGA como prototipo académico reproducible.** No acredita producción ni cumplimiento total de la rúbrica: Cr6 requiere evidencia humana. Fecha: 11 de octubre de 2026 (America/Bogota). HEAD inicial main y remoto confirmado: `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`. Cambios de cierre se preparan en rama separada; main no se sobrescribe. Estado remoto de la rama se registra al completar CI.

| Elemento | Estado | Evidencia | Pendiente |
|---|---|---|---|
| Dataset | LISTO ACADÉMICO | reports/0.9.0-academic/dataset_summary.json | Validación empresarial; sintético externo |
| Split | LISTO | 2800/600/600; overlap 0/0/0; reports/closure/validation.json | Ninguno en cierre |
| Health | LISTO CON LIMITACIÓN | metrics.json; baselines.json | Recall crítico limitado; clases desbalanceadas |
| Delay | LISTO CON LIMITACIÓN | MAE 27.710468 vs 27.850313; runtime; tests/test_delay_presentation.py | Mejora marginal; no sustitución de modelo |
| Cost | LISTO CON CAVEAT | MAE 0.147158 pp; R² 0.991816 | Dependencia estructural CPI/EVM sintético |
| Final Status | LISTO DERIVADO | inference/brain.py; preflight | Sin target independiente |
| Temporal | LISTO CON COBERTURA EXPLÍCITA | temporal_evaluation.csv | Al 20 % solo 236/600 (39.333 %) |
| GenAI | LISTO EVALUADO LOCALMENTE | qwen3-8b-evaluation.json: complete, 30 casos; closure/preflight_genai.txt | Revisión humana semántica; no comparación empírica de tres LLM |
| Team Health | LISTO COMO HEURÍSTICA | features/team_health.py; App.test.jsx | Sin calibración/outcomes reales; no imputación |
| CSV | LISTO | Tests API; frontend; hasta 100 filas | No usar prueba manual 99 como métrica oficial |
| What-if | LISTO | tests/test_playground_api.py; preflight | Sensibilidad, no causalidad |
| Backend | PASSING | 104 passed; closure/backend_tests.txt | Ningún test fallido |
| Frontend | PASSING | 14 passed; closure/frontend_tests.txt | Ningún test fallido |
| Build frontend | SUCCESS | closure/frontend_build.txt; frontend/dist | Assets reconstruidos |
| pip check / compileall | PASSING | closure/validation.json | Ninguno |
| Preflight demo | LISTO PARA DEMO | closure/preflight_demo.txt; artefacto académico | TestClient local; comprobar navegador/red del salón |
| Preflight GenAI | OLLAMA READY | closure/preflight_genai.txt | Requiere API con GenAI activado y Ollama en la demo |
| CI | MAIN INICIAL SUCCESS / CIERRE POR VERIFICAR | run 38170532271; quality.yml | Verificar ejecución del commit de cierre; no inferir verde de main anterior |
| Docker | EMPAQUETADO IMPLEMENTADO | Dockerfile.playground: Node 22 + npm ci | Imagen no construida en este cierre; artefactos locales requeridos |
| Kubernetes | DISEÑO | YAML revisado, 3 réplicas, HPA 3–10 | Sin clúster; requiere metrics-server e imagen/entorno |
| MLOps | ACADÉMICO IMPLEMENTADO / PRODUCTIVO PARCIAL | mlops_production.md; /metrics; prediction_id | Centralización, alertas, drift y retraining continuo |
| Eficiencia humana | PENDIENTE | efficiency_evaluation.md; efficiency.json: not_measured | Cronometrar cinco casos y conservar respuestas |
| Validación real | PENDIENTE | model_card.md; INFORME_FINAL.md | Proyectos empresariales con outcomes |
| Informe y sustentación | LISTO | INFORME_FINAL.md; PRESENTACION_FINAL.md; DEMO_PRESENTACION.md | Revisión/ensayo del autor |

## Integridad y alcance de los cambios

La regresión cruda de Delay permanece en `delay_days_raw`; el campo operacional `delay_days` aplica max(0, raw). Los reportes académicos siguen usando la predicción original. Cost negativo no se trunca. Se conservaron pesos, fusión, thresholds, labels, features, arquitectura Qwen/Ollama, dataset y split. No se ejecutó entrenamiento académico ni se modificaron los .joblib existentes; hashes antes/después en `reports/closure/validation.json`. Los tests pueden entrenar fixtures temporales; CI genera únicamente modelos demo efímeros y no modifica los oficiales.

Se alineó el generador de futuros smoke tests con las categorías API, sin regenerar el dataset académico ni artefactos locales existentes. Se preservaron tests que rechazan categorías antiguas y sector research (campo no usado por ML académico). Se actualizaron únicamente documentos contradictorios y empaquetado necesario; no hubo refactor grande.

La evaluación oficial de Qwen no se reescribió. El preflight GenAI es un smoke test separado ejecutado realmente. `reports/genai/efficiency.json` deriva latencia del benchmark y deja baseline/ahorro/ganancia null; el throughput es cálculo teórico, no prueba de carga.

## Pendientes humanos y riesgos para la defensa

Medir cinco casos humanos para Cr6; revisar pertinencia semántica de recomendaciones; ensayar presentación y comprobar LAN/navegador antes de sustentar. La medición humana no puede reemplazarse por cifras de ejemplo. La prueba manual balanceada de 99 proyectos reportada por el autor carece de resultados estructurados versionados identificados; no se fabricó una métrica. El test local de 99 filas verifica contrato y cobertura, sin garantizar 33/33/33.

La reproducción desde un clon necesita obtener/preparar datos y artefactos locales (los modelos pesados no están en Git). Con los artefactos académicos presentes, tests y preflight pasan. Dataset sintético, debilidad Delay, dependencia EVM de Cost, cobertura temprana y fusión no calibrada delimitan uso; no constituyen fallos ocultos.

PRUNIN AI Core está listo como prototipo académico reproducible para entrega y sustentación. No está validado para producción. La matriz no asigna automáticamente Nivel 4; ver `rubric_matrix.md` para el estado de cada criterio.
