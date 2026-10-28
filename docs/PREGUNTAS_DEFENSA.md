# Preguntas de defensa — respuestas con evidencia

Responder primero la idea central y después mostrar la fuente si el jurado la solicita. Los valores redondeados derivan de JSON versionados; no se presentan como nuevos resultados. Las rutas son relativas a raíz. No usar código/JSON largo cuando una figura o explicación basta.

## 1. ¿Por qué este problema necesita IA?

No toda gestión necesita IA. PRUNIN explora ML para combinar patrones tabulares y GenAI para redactar evidencia; el baseline permite comprobar si el componente aprendido aporta señal. Su necesidad empresarial/retorno aún no fue medida.

**Evidencia:** `docs/INFORME_FINAL.md §§4–9; reports/0.9.0-academic/baselines.json`.

## 2. ¿Por qué combinar ML y GenAI?

ML estima outcomes; GenAI comunica la evidencia. Separarlos conserva predicciones si falla el texto y permite evaluar precisión y explicación de forma independiente.

**Evidencia:** `docs/architecture.md; src/prunin_ai/api/recommendations.py`.

## 3. ¿Por qué LightGBM?

Es adecuado para datos tabulares y se integra con el preprocesamiento scikit-learn; permite clasificación y regresión reproducibles. No afirmamos superioridad universal ni haber comparado todos los algoritmos.

**Evidencia:** `docs/references.md (Ke et al., 2017); src/prunin_ai/training/core.py`.

## 4. ¿Por qué Qwen3?

Por encaje con español, ejecución local, licencia Apache 2.0, tamaño e integración Ollama existente. La selección es multicriterio técnico-operativa, sin victoria experimental frente a Gemma/Ministral.

**Evidencia:** `docs/genai_model_selection.md`.

## 5. ¿Por qué no GPT/API externa?

La versión académica prioriza ejecución local y reducir transferencia a terceros y dependencia de servicios externos. No se hizo un benchmark que demuestre que una API externa sería inferior ni una comparación económica medida.

**Evidencia:** `docs/genai_model_selection.md; docs/ethics_security.md`.

## 6. ¿Por qué el dataset es sintético?

Su publicador declara un benchmark de proyectos y trayectorias EVM simulados. Ser externo y tener DOI no lo transforma en información empresarial real.

**Evidencia:** `docs/datasets.md; reports/0.9.0-academic/dataset_summary.json`.

## 7. ¿Qué limita usar datos sintéticos?

La simulación puede no representar distribución, errores de captura ni relaciones de empresas reales. La estructura EVM facilita Cost; los resultados no garantizan generalización y requieren validación prospectiva.

**Evidencia:** `docs/model_card.md`.

## 8. ¿Cómo evitaron leakage?

Split por project_id, exclusión de outcomes, whitelist de features, preprocesamiento TRAIN y comparación en VALIDATION. TEST permanece congelado. La proximidad de CPI/progreso tardíos al outcome sigue siendo riesgo metodológico.

**Evidencia:** `reports/0.9.0-academic/feature_manifest.json; scripts/verify_split.py`.

## 9. ¿Por qué Health no tiene accuracy más alta?

Hay errores entre clases; el benchmark no es separable perfectamente con estas features y configuración. No atribuimos una causa específica no estudiada. Accuracy 0.726667 debe leerse con Macro F1 0.627576, desbalance y recall critical, sin optimizar TEST.

**Evidencia:** `reports/0.9.0-academic/metrics.json; health_confusion_matrix.csv`.

## 10. ¿Por qué usar Macro F1?

Promedia F1 de las clases con igual peso y evita esconder fallas minoritarias detrás de la clase mayoritaria. El baseline logra accuracy 0.715 pero Macro F1 0.277940 y recall critical cero.

**Evidencia:** `reports/0.9.0-academic/baselines.json; docs/GLOSARIO_DEFENSA.md`.

## 11. ¿Por qué Critical tiene menor recall?

Se detectan 25 de 44 critical (0.568182); 13 se predicen at_risk y 6 healthy. El desbalance es relevante, pero no prueba por sí solo la causa de cada error. Requiere supervisión y estudio con datos externos, sin cambiar thresholds en cierre.

**Evidencia:** `reports/0.9.0-academic/health_confusion_matrix.csv`.

## 12. ¿Por qué Delay es débil?

MAE TEST 27.710468 frente a baseline 27.850313 días: mejora marginal. Las entradas/benchmark ofrecen señal limitada; no se encontró evidencia para prometer alta precisión. Delay es el componente predictivo más débil.

**Evidencia:** `reports/0.9.0-academic/baselines.json`.

## 13. ¿Por qué no reemplazaron Delay?

El experimento seleccionó la mediana TRAIN según VALIDATION: MAE 27.901042 frente a 28.881476 del LightGBM actual. La promoción automática estaba deshabilitada y se conservó el artefacto oficial. No sería riguroso afirmar que ningún candidato mejoró VALIDATION ni escoger por TEST.

**Evidencia:** `reports/experiments/delay/comparison.json; comparison.csv; README.md`.

## 14. ¿Por qué Cost tiene R² tan alto?

CPI/progreso y el outcome tienen relación estructural en el generador EVM sintético. R² 0.991816 es desempeño interno tardío, no evidencia empresarial. Al 20 % Cost MAE es 3.136943 pp, mucho mayor al resultado tardío.

**Evidencia:** `reports/0.9.0-academic/baselines.json; temporal_evaluation.json`.

## 15. ¿Qwen hace las predicciones?

No. LightGBM predice Health, Delay y Cost; Qwen interpreta evidencia y redacta recomendaciones. Final Status deriva de Health.

**Evidencia:** `src/prunin_ai/inference/brain.py; docs/architecture.md`.

## 16. ¿Qué pasa si Qwen alucina?

El validador rechaza schema/features/cifras no admitidas y activa fallback, con código de fallo. PROJ_0840 falló por cifra no soportada. Errores semánticos sin cifras nuevas pueden pasar; revisión humana sigue necesaria.

**Evidencia:** `reports/genai/qwen3-8b-evaluation.json; tests/test_genai_grounding.py`.

## 17. ¿Qué pasa si Ollama falla?

Timeout/fallo quedan registrados y se usa respaldo determinístico conservando ML. El análisis individual puede esperar el timeout configurado; batch y What-if no dependen del LLM.

**Evidencia:** `src/prunin_ai/api/recommendations.py; app.py`.

## 18. ¿Qué es grounding?

En PRUNIN es apoyar la generación en evidencia permitida y verificar esquema, features y cifras. Es un proxy de ingeniería, no prueba de verdad semántica ni causalidad.

**Evidencia:** `docs/genai_evaluation.md`.

## 19. ¿Team Health es IA?

Aquí es una heurística operacional determinística de señales observadas. No es modelo supervisado ni indicador de moral/salud mental.

**Evidencia:** `src/prunin_ai/features/team_health.py; docs/model_card.md`.

## 20. ¿Por qué Team Health no aparece en algunos CSV?

Necesita mínimo tres componentes y cobertura ponderada 0.5. No inventamos/imputamos señales. La columna se oculta si ninguna fila tiene score calculable y aparece si al menos una lo tiene.

**Evidencia:** `frontend/src/components/CsvAnalyzer.jsx; frontend/src/App.test.jsx`.

## 21. ¿Por qué la fusión es 85/15?

Es una regla operacional provisional para dar mayor peso al core; los pesos están fijados en configuración. No se estimaron con outcomes reales ni garantizan optimalidad. No se cambia en el cierre.

**Evidencia:** `configs/training.yaml; docs/model_card.md`.

## 22. ¿Los drivers son causales?

No. Miden cambio local cuando una variable se sustituye por referencia manteniendo otras. No son experimentos de intervención ni garantizan qué pasaría al actuar en el mundo.

**Evidencia:** `src/prunin_ai/api/model_runtime.py; drivers_disclaimer en app.py`.

## 23. ¿Qué significa detección temprana?

Evaluar una observación cuya true_progress no supera un cutoff 20/40/60/80 %, antes de disponer del snapshot final. Es definición por avance, no una fecha fija ni garantía prospectiva.

**Evidencia:** `reports/0.9.0-academic/temporal_evaluation.json`.

## 24. ¿Qué ocurre al 20 % de avance?

236 de 600 proyectos tienen snapshot elegible: cobertura 39.333 %. Health Macro F1 0.397938 y critical recall 0.111111 en ese subconjunto. No afirmamos que se evaluaron los 600 ni eficacia temprana universal.

**Evidencia:** `reports/0.9.0-academic/temporal_evaluation.json`.

### 24A. ¿Cumplieron la meta original del 75 %?

Sí, **dentro del entorno experimental**. La meta original se refería a proyectos Critical **o** At Risk. Usando como denominador fijo los 473 proyectos TEST que finalmente pertenecen a esas dos clases, PRUNIN ya ha detectado 359 al 60 % de avance: **75.90 %**, con 576/600 proyectos TEST cubiertos (96 %). Al final detecta 390/473 = **82.45 %**.

**Evidencia:** `reports/promise_validation/risk_alert_metrics.json`; `temporal_risk_alert_metrics.csv`.

### 24B. ¿Por qué agrupan At Risk y Critical? ¿No están cambiando el objetivo?

No. La propuesta inicial formuló explícitamente la meta como detectar proyectos **críticos o en alto riesgo**. La agregación Risk Alert únicamente traduce esas dos clases a un KPI binario de atención. El modelo Health sigue siendo multiclase y sus métricas originales permanecen visibles.

**Evidencia:** `reports/0.9.0-academic/health_confusion_matrix.csv`; `scripts/validate_original_promise.py`.

### 24C. ¿Por qué no dicen que cumplen al 40 % si el recall entre elegibles ya es 79.95 %?

Porque al 40 % solo 463/600 proyectos tienen snapshot elegible. Para una afirmación más estricta usamos toda la cohorte de 473 proyectos que finalmente son At Risk/Critical y contamos como no detectados los que todavía no tienen observación. Con ese denominador, al 40 % se ha detectado 64.06 %; la meta de 75 % se cruza por primera vez al 60 %.

**Evidencia:** `reports/promise_validation/temporal_risk_alert_metrics.csv`.

### 24D. Entonces, ¿por qué Critical Recall sigue en 56.82 %?

Porque “detectar que un proyecto necesita atención” y “clasificar exactamente la severidad Critical” son problemas distintos. Risk Alert considera correcta una predicción At Risk para un proyecto Critical porque la alerta de intervención sí fue activada; la métrica multiclase considera esa misma predicción un error de severidad. Por transparencia reportamos ambas.

**Evidencia:** `reports/0.9.0-academic/metrics.json`; `reports/promise_validation/risk_alert_metrics.json`.

## 25. ¿Está PRUNIN listo para producción?

No. Está listo como prototipo académico reproducible, con limitaciones visibles y necesidad de validación real, controles productivos y pruebas operacionales.

**Evidencia:** `docs/FINAL_READINESS.md; docs/model_card.md`.

## 26. ¿Kubernetes está realmente desplegado?

No hay evidencia de clúster activo. El YAML conserva tres réplicas, Service, RollingUpdate, probes, recursos y HPA 3–10 como diseño.

**Evidencia:** `deploy/k8s/prunin-ai-core.yaml`.

## 27. ¿Qué falta para producción?

Validación externa/prospectiva, outcomes reales, gobierno/controles de datos, revisión humana, calibración, observabilidad central, alertas, drift y carga/recuperación reales. No se añadió cloud ni infraestructura en este cierre.

**Evidencia:** `docs/mlops_production.md; docs/ethics_security.md`.

## 28. ¿Cómo monitorearían drift?

Hoy hay contadores/latencias locales, no drift estadístico automático. Futuro: comparar distribución de inputs y desempeño con outcomes respecto a una referencia aprobada, centralizar métricas, revisar alertas y subgrupos; umbrales deben justificarse con datos reales.

**Evidencia:** `docs/mlops_production.md; src/prunin_ai/api/monitoring.py`.

## 29. ¿Cuándo reentrenarían?

Con datos aprobados suficientes y cambios de dataset o degradación/drift revisados; candidato evaluado en VALIDATION y TEST final congelado. No basta un calendario ni se ejecuta retraining continuo actualmente.

**Evidencia:** `docs/mlops_production.md`.

## 30. ¿Qué aporta GenAI si existe fallback?

GenAI redacta/organiza evidencia; fallback mantiene una respuesta determinística disponible. La mejora de utilidad sobre fallback no fue medida con personas, así que no afirmamos superioridad cuantificada.

**Evidencia:** `docs/genai_evaluation.md; src/prunin_ai/api/recommendations.py`.

## 31. ¿Qué evidencia de eficiencia tienen?

Medimos eficiencia operacional de manera reproducible mediante latencia, throughput y comparación entre inferencias individuales y el endpoint batch sobre los mismos proyectos TEST. En esta máquina, para N=100, batch tuvo mediana de 4.22 s frente a 4.44 s secuencial y throughput mediano de 23.721 proyectos/s; el éxito fue 100 % en ambos modos. El batch actual sigue procesando filas secuencialmente, por lo que la diferencia observada es overhead de endpoint/serialización, no paralelismo ni producción.

**¿Esto demuestra productividad humana?** No. Demuestra capacidad y eficiencia del proceso automatizado. La productividad humana requiere un estudio controlado con usuarios, que no realizamos; tampoco inferimos ahorro de tiempo laboral.

**Evidencia:** `reports/efficiency/operational_benchmark.md`, `operational_benchmark_summary.json` y `operational_benchmark_raw.csv`.

## 32. ¿Cómo se usaría con datos empresariales reales?

Mediante captura/pseudonimización acordada, correspondencia semántica y de unidades con features, validación temporal externa sin unir proyectos arbitrarios y revisión de outcomes. No basta mapear columnas y asumir que el benchmark sintético generaliza.

**Evidencia:** `docs/datasets.md; docs/ethics_security.md; docs/model_card.md`.

## Dos precisiones adicionales

**Delay negativo:** raw=-0.3 conserva delay_days_raw=-0.3; delay_days presenta 0. El ajuste es operacional, no una mejora del modelo ni de métricas. Cost negativo no se trunca.

**Prueba 99:** el autor comunicó una validación funcional manual balanceada; no hay resultados estructurados versionados identificados de esa corrida. El test local de 99 filas es una prueba de contrato/cobertura distinta; los resultados oficiales son 600 proyectos TEST. No citar una accuracy recordada.

**Cierre de respuesta:** si la pregunta pide evidencia ausente, reconocer el límite y señalar el protocolo/pendiente; no improvisar una cifra.
