# Cierre definitivo — PRUNIN AI Core

**Veredicto: LISTO PARA ENTREGA ACADÉMICA** como prototipo reproducible para entrega y sustentación. No implica producción ni Nivel 4 en toda la rúbrica. Fecha: 11 de octubre de 2026 (America/Bogota). Base main inicial auditada y confirmada contra remoto: `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`.

Esta versión incorpora un benchmark operacional medido sobre el artifact académico `0.9.0-academic`; sus datos registran la revisión de código usada para medir. GitHub Actions se ejecuta en cada push/PR, pero un resultado histórico no certifica un HEAD posterior: consultar únicamente el run `quality` asociado al commit final de esta entrega.

## Tabla 1. Preparación por área

Estados utilizados: LISTO, LISTO CON LIMITACIÓN, DISEÑO, PENDIENTE HUMANO y PENDIENTE PRODUCTIVO. Rutas de reportes académicos son relativas a reports/0.9.0-academic; las de cierre a reports/closure/definitive; código relativo a raíz.

| Área | Estado | Evidencia | Limitación |
|---|---|---|---|
| Dataset | LISTO CON LIMITACIÓN | dataset_summary.json: 4000/72549, DOI v2 | Sintético externo; no validación empresarial |
| Preprocessing | LISTO | audit.py, training/core.py, schema.py, readiness | Scaling estándar innecesario; no detector OOD |
| Leakage | LISTO CON LIMITACIÓN | split 2800/600/600, overlap 0; feature_manifest | Proximidad temporal CPI/EVM tardío |
| Health | LISTO CON LIMITACIÓN | baselines/metrics: Macro F1 0.627576 vs 0.277940 | Recall critical 25/44; desbalance |
| Delay | LISTO CON LIMITACIÓN | MAE 27.710468 vs 27.850313; raw/display tests | Mejora marginal; componente más débil |
| Cost | LISTO CON LIMITACIÓN | MAE 0.147158 pp; R² 0.991816 | Relación estructural CPI/progreso–outcome sintético |
| Temporal | LISTO CON LIMITACIÓN | temporal_evaluation.json; figura versionada | 20 %: 236/600, 39.333 %; cobertura desigual |
| GenAI | LISTO CON LIMITACIÓN | qwen3-8b-evaluation.json complete; preflight_genai | 30 casos condicionados; no comparativa empírica de tres LLM |
| Grounding | LISTO CON LIMITACIÓN | recommendations.py; PROJ_0840 rechazado; tests | Proxy; no verdad semántica total |
| Team Health | LISTO CON LIMITACIÓN | team_health.py; CsvAnalyzer.jsx; tests | Heurística sin imputación/psicología; fusión no calibrada |
| CSV | LISTO | Tests API/frontend y api_smoke.json 5 filas | 100 es límite configurado, no throughput bajo carga |
| What-if | LISTO | Tests API y smoke de raw negativo | Sensibilidad operacional; no intervención causal |
| API | LISTO | /api/health, /api/ready, schema y preflight | Uso local; controles productivos pendientes |
| Frontend | LISTO | 14 tests passing; build success; dist | Probar navegador/proyección/red en salón |
| Tests | LISTO | 116 backend passing; npm ci, 14 frontend; compileall/pip check; tests puros del benchmark | CI demo omite los dos tests que requieren artifact/dataset académico local |
| CI | CONFIGURADO | quality ejecuta npm ci/build/tests, artifacts demo, compileall y pytest en push/PR | Asociar resultado al HEAD exacto publicado |
| Docker | LISTO CON LIMITACIÓN | Dockerfile.playground: Node22, npm ci, API Python | Imagen no construida en cierre; requiere artefactos locales |
| Kubernetes | DISEÑO | Deployment3/Service/probes/RollingUpdate/HPA3–10 | Sin clúster; metrics-server/imagen y pruebas pendientes |
| Monitoring | LISTO CON LIMITACIÓN | monitoring.py, /api/monitoring y /metrics | Contadores en memoria por proceso; no centralización |
| MLOps | LISTO CON LIMITACIÓN | Versiones, SHA256, manifests, prediction_id, CI y política | Sin alertas/drift/retraining continuo productivo |
| Efficiency | LISTO CON LIMITACIÓN | reports/efficiency/operational_benchmark_summary.json; benchmark reproducible individual/batch, N=1–100 | Medición local secuencial; sin baseline de usuarios, carga productiva ni concurrencia |
| Ethics | LISTO CON LIMITACIÓN | Matriz de 15 riesgos, impactos y controles | Representatividad, OOD, seguridad y semántica residuales |
| Written communication | LISTO CON LIMITACIÓN | INFORME_FINAL 25 secciones, APA, tablas/figuras | Completar identidad/datos institucionales y revisión final |
| Oral communication | PENDIENTE HUMANO | 12 slides; 7/10/12 min; 23 términos; 32 respuestas | Ensayo, voz, postura y defensa no acreditados por GitHub |
| Real-world validation | PENDIENTE PRODUCTIVO | model_card y alcance de informe | Outcomes reales y evaluación prospectiva externa |

## Verificaciones ejecutadas

pip check: sin dependencias rotas. compileall: success. Backend académico: 116 passed. npm ci: success desde lockfile. Frontend: 14 passed. Build: success. Preflight con 0.9.0-academic: RESULTADO: LISTO PARA DEMO. Preflight GenAI separado: RESULTADO: OLLAMA READY. El benchmark operacional está `complete`, con 100 casos únicos TEST, 80 runs individuales/batch, GenAI apagada y 100 % de éxito normal. Sus reports/figures están en `reports/efficiency/`; el reporte identifica HEAD medido `e0beff1`. El throughput y speedup son locales, no productivos ni humanos.

Benchmark operacional local: `reports/efficiency/operational_benchmark_summary.json`, `operational_benchmark_raw.csv`, casos TEST, robustness y cuatro figuras. 100 proyectos únicos, N=1/10/25/50/100, 10/10/10/5/5 repeticiones por modo, tres warm-ups; GenAI apagada. N=100: batch 4215.74 ms vs individual secuencial 4440.90 ms, throughput mediano 23.721 proy/s, ambos con 100 % de éxito. No equivale a productividad humana ni a carga productiva. Muestra Qwen separada: `reports/efficiency/genai_operational_sample.json`.

Se ejecutó un smoke funcional sobre cinco casos cuyos IDs provienen del benchmark Qwen: API/CSV sin LLM, cobertura ML completa y ausencia de Team Health inventado; What-if conserva raw=-0.3 usando un stub temporal en memoria. Ese stub es una prueba de política, no una predicción académica ni un cambio de modelo. Tiempos observados se guardan con alcance local, sin llamarlos ahorro humano/throughput productivo. No se reejecutó el benchmark oficial ni entrenamiento.

Logs, comandos y hashes: reports/closure/definitive/. Los logs pueden normalizar espacios finales sin cambiar resultados. La reproducción desde un clon necesita modelos/datasets locales; CI usa fixtures efímeros y puede omitir pruebas académicas dependientes de datos.

## Integridad preservada

Los .joblib existentes, artefactos, configuración, pesos, thresholds, definición de targets, seed, dataset académico, split, mapping Final Status, fusión 0.85/0.15 y arquitectura LightGBM/Qwen permanecen intactos. Los reportes académicos y benchmark Qwen históricos no se reescribieron. Hashes inicial/final se comprueban en validation.json. No se entrenó el modelo académico; los tests pueden ajustar fixtures temporales y CI genera únicamente artefactos demo de prueba.

Delay operacional=max(0, raw) aplica en API/UI/CSV/What-if; raw queda en detalle técnico y métricas crudas históricas permanecen. Cost negativo conserva ahorro. Team Health del batch se oculta si ningún score es calculable y aparece si alguno lo es; no se imputa. Se añadieron scripts/reportes de benchmark operacional, sin dependencia nueva, RAG, cloud, base de datos ni infraestructura real. No se modificaron modelos ni artefactos.

## Auditoría Nivel 4 y acciones humanas

La matriz rubric_matrix.md cubre 27 ítems con exigencia, Nivel 4, evidencia/ruta, estado, gap, corrección y demostración; incluye auditoría final con banderas repo/acción humana. Evidencias compatibles documentales/técnicas no son calificación oficial.

R6.2 Cr6 tiene evidencia cuantitativa de eficiencia operacional local y comparación individual/batch; no demuestra productividad humana ni rendimiento productivo, por lo que la valoración final del nivel corresponde al evaluador. Siguen sin acreditarse una comparación empírica completa de tres LLM, mitigación ética total, escalabilidad/orquestación operada ni MLOps con retraining continuo. RA2 está preparado, no se observó actuación: F4 voz y F6 lenguaje no verbal requieren ensayo humano explícito.

Pendientes: completar autor/institución de portada; revisar/ensayar guion de 7/10/12 min; practicar voz/postura y respuestas; comprobar legibilidad/proyección y LAN; antes de uso real obtener datos/outcomes aprobados, validación externa y controles operacionales. Un estudio humano controlado de tiempos/calidad queda como trabajo futuro opcional; no es necesario para afirmar la eficiencia operacional automatizada medida. Son pendientes visibles, no pruebas fabricadas.

La prueba manual adicional de 99 proyectos balanceados comunicada por el autor no tiene resultado estructurado versionado identificado. Se mantiene como validación funcional manual, sin metricar números recordados; el test de 99 filas del repo verifica contrato/cobertura y no garantiza balance. Lo oficial continúa en TEST de 600 proyectos.

## Evidencias para la sustentación

INFORME_FINAL.md desarrolla contexto → problema → método → resultados → significado → límites → conclusiones. PRESENTACION_FINAL.md prepara 12 slides con mensajes, speech, transiciones y tiempos planificados. GLOSARIO_DEFENSA.md define 23 términos. PREGUNTAS_DEFENSA.md contiene 32 respuestas con fuente. DEMO_PRESENTACION.md describe flujo de demo sin código/terminal prolongados. architecture.md contiene arquitectura, pipeline y flujo GenAI Mermaid; figuras predictivas existentes fueron inspeccionadas y no alteradas.

PRUNIN AI Core está listo como prototipo académico reproducible para entrega y sustentación. Combina modelos predictivos supervisados con una capa generativa local y grounded para apoyar la interpretación del riesgo de proyectos. Sus resultados se validaron sobre un dataset sintético externo, por lo que aún requiere validación prospectiva con datos empresariales reales antes de un uso productivo.

## Inventario exacto contra main inicial

La entrega incluye la integración del cierre anterior y la ampliación actual. El manifest machine-readable está en reports/closure/definitive/changed_files.json. Archivos por estado:

- M: `DEMO_PRESENTACION.md`
- M: `Dockerfile.playground`
- M: `README.md`
- A: `docs/FINAL_READINESS.md`
- A: `docs/GLOSARIO_DEFENSA.md`
- A: `docs/INFORME_FINAL.md`
- A: `docs/PREGUNTAS_DEFENSA.md`
- A: `docs/PRESENTACION_FINAL.md`
- M: `docs/architecture.md`
- A: `docs/efficiency_evaluation.md`
- M: `docs/ethics_security.md`
- M: `docs/genai_evaluation.md`
- M: `docs/genai_model_selection.md`
- M: `docs/mlops_production.md`
- M: `docs/model_card.md`
- M: `docs/playground.md`
- A: `docs/references.md`
- M: `docs/rubric_matrix.md`
- M: `docs/training.md`
- R087: `frontend/dist/assets/index-CeTPLuFN.js` → `frontend/dist/assets/index-B6GKq6_o.js`
- M: `frontend/dist/index.html`
- M: `frontend/src/App.test.jsx`
- M: `frontend/src/components/AnalysisPanels.jsx`
- M: `frontend/src/components/TechnicalDrawer.jsx`
- A: `reports/closure/backend_tests.txt`
- A: `reports/closure/definitive/api_smoke.json`
- A: `reports/closure/definitive/backend_tests.txt`
- A: `reports/closure/definitive/changed_files.json`
- A: `reports/closure/definitive/frontend_build.txt`
- A: `reports/closure/definitive/frontend_tests.txt`
- A: `reports/closure/definitive/npm_ci.txt`
- A: `reports/closure/definitive/preflight_demo.txt`
- A: `reports/closure/definitive/preflight_genai.txt`
- A: `reports/closure/definitive/validation.json`
- A: `reports/closure/frontend_build.txt`
- A: `reports/closure/frontend_tests.txt`
- A: `reports/closure/preflight_demo.txt`
- A: `reports/closure/preflight_genai.txt`
- A: `reports/closure/validation.json`
- A: `reports/genai/efficiency.json`
- M: `scripts/preflight_demo.py`
- M: `src/prunin_ai/api/model_runtime.py`
- M: `src/prunin_ai/data/demo.py`
- A: `tests/test_delay_presentation.py`

## Evidencia GitHub Actions de main

El run 38177951135 terminó completed/success sobre d3b0a9fdc5023841d7411102998c03bf1211b6ba: npm ci, build/tests frontend, fixtures demo, compileall y pytest. Sin descarga Mendeley ni ejecución Ollama/benchmark pesado. Este documento registra el resultado ya observado y no lo atribuye a otro SHA. La verificación del HEAD final se informa en el reporte de entrega después de verlo completado; no se requiere reentrenar ni repetir benchmarks.

## Addendum Empirical — 27 de octubre de 2026

**Veredicto: EMPIRICAL MODEL READY WITH LIMITATIONS.** La línea académica `0.9.0-academic` conserva su runtime, artefactos, métricas y benchmark; Academic sigue como default. DSLIB v3.4 fue descargado localmente, auditado y procesado sin mezclar Mendeley ni modificar el ZIP bruto. El publicador no declara una licencia en el repositorio, por lo que el ZIP y los datos derivados permanecen fuera de Git.

La cobertura real es 231 proyectos publicados, 229 con baseline y 151 proyectos completos por target tras exigir features y outcomes. El artifact `1.0.0-empirical` entrena Delay y Cost, no Health. GroupShuffleSplit usa seed 42 y separa por project_id; test contiene 31 proyectos por target. La mediana ganó validación; TEST Delay MAE 30.7097 días/R² -0.0339 y Cost MAE 0.115703/R² -0.0317, iguales en MAE al baseline mediano. Solo 13 snapshots temporales completos por target: evaluación 20/40/60/80 no disponible. El modelo no se activa automáticamente.

La interfaz Models permite consultar ambos registros, métricas, comparar predicciones, seleccionar manualmente el modelo, declarar el dominio para una recomendación contextual de baja confianza, revisar historial y descargar el reporte. El entrenamiento es asíncrono y requiere `PRUNIN_ENABLE_TRAINING_UI=1`; por defecto está deshabilitado. Cada job crea una versión nueva y deja Academic activo. Evidencia: `docs/dataset_dslib.md`, `docs/model_card_empirical.md`, `docs/empirical_health_definition.md`, `reports/empirical/` y `reports/model_comparison.md`. Las métricas entre datasets no son head-to-head y no acreditan producción.

Benchmark operacional Empirical local completado sobre 31 features TEST: individual 79.622 ms / 389.34 proy/s y CSV batch 50.148 ms / 618.17 proy/s, 3 repeticiones, 100 % éxito. No es carga/concurrencia productiva ni evaluación de exactitud. Reporte: `reports/efficiency/empirical_operational_benchmark.json`.
