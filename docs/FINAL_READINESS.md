# Cierre final — PRUNIN AI Core

**Veredicto técnico local: LISTO PARA ENTREGA como prototipo académico reproducible.** No acredita producción ni cumplimiento total de la rúbrica: Cr6 requiere evidencia humana. Fecha: 11 de octubre de 2026 (America/Bogota). HEAD inicial main y remoto confirmado: `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`. Cambios de cierre publicados en `codex/academic-final-closure`; main no se sobrescribe. CI de implementación confirmado: commit `2675b88399f7df29a0472f563ba35a21cadfa087`, workflow quality completado con success, [ejecución 38173611246](https://github.com/heiandavi-boop/tallerfina3/actions/runs/38173611246). Este documento registra ese resultado; comprobar también el run del HEAD final al integrar la rama.

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
| CI | SUCCESS OBSERVADO EN CIERRE | commit 2675b883; run 38173611246; quality.yml | El commit posterior documenta este run; verificar HEAD final antes de integrar |
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

## Inventario de entrega

Archivos modificados (incluye bundle reconstruido):

- `DEMO_PRESENTACION.md`
- `Dockerfile.playground`
- `README.md`
- `docs/ethics_security.md`
- `docs/genai_evaluation.md`
- `docs/genai_model_selection.md`
- `docs/mlops_production.md`
- `docs/model_card.md`
- `docs/playground.md`
- `docs/rubric_matrix.md`
- `frontend/dist/assets/index-CeTPLuFN.js → frontend/dist/assets/index-B6GKq6_o.js`
- `frontend/dist/index.html`
- `frontend/src/App.test.jsx`
- `frontend/src/components/AnalysisPanels.jsx`
- `frontend/src/components/TechnicalDrawer.jsx`
- `scripts/preflight_demo.py`
- `src/prunin_ai/api/model_runtime.py`
- `src/prunin_ai/data/demo.py`

Archivos creados:

- `docs/FINAL_READINESS.md`
- `docs/INFORME_FINAL.md`
- `docs/PRESENTACION_FINAL.md`
- `docs/efficiency_evaluation.md`
- `docs/references.md`
- `reports/closure/backend_tests.txt`
- `reports/closure/frontend_build.txt`
- `reports/closure/frontend_tests.txt`
- `reports/closure/preflight_demo.txt`
- `reports/closure/preflight_genai.txt`
- `reports/closure/validation.json`
- `reports/genai/efficiency.json`
- `tests/test_delay_presentation.py`

## Alcance del resultado CI

El workflow quality de la implementación terminó en success: npm ci, build/tests frontend, artefactos demo efímeros, compileall y pytest. No descargó Mendeley ni ejecutó Ollama o benchmark GenAI. Los tests académicos que necesitan datos/modelos locales pueden omitirse en CI demo; los 104 backend passing de esta auditoría se ejecutaron localmente con el artefacto académico. Este registro no altera los JSON históricos. Los logs archivados se normalizaron únicamente en espacios finales, preservando su contenido.
