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

## 28. ¿Cómo monitorean drift?

Hay un detector académico offline de PSI/missing-rate y una advertencia OOD univariada perfilada con TRAIN. Futuro: ejecutar cohortes aprobadas periódicamente, asociar outcomes, justificar umbrales y centralizar métricas; no activar retraining automático.

**Evidencia:** `docs/drift_monitoring.md`; `src/prunin_ai/monitoring/drift.py`; `scripts/check_drift.py`.

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

## Guía de respuestas cortas: evidencia y límite

Usar este formato durante el ensayo. La plantilla prepara la defensa pero no acredita respuesta oral espontánea.

**¿Cumplieron el 75 %?**
**RESPUESTA CORTA:** Sí, en el benchmark sintético: 359/473 = 75.90 % al 60 % de avance y 96 % de cobertura.
**EVIDENCIA:** `reports/promise_validation/risk_alert_metrics.json`.
**LÍMITE:** No es validación empresarial ni Critical Recall.

**¿Por qué no usar 79.95 % al 40 %?**
**RESPUESTA CORTA:** Es recall entre elegibles; con cohorte fija el valor es 64.06 %.
**EVIDENCIA:** `reports/promise_validation/temporal_risk_alert_metrics.csv`.
**LÍMITE:** La cobertura temprana cambia por cutoff.

**¿Por qué dataset sintético?**
**RESPUESTA CORTA:** Ofrece un benchmark versionado con snapshots/outcomes disponibles; no contiene clientes PRUNIN.
**EVIDENCIA:** `dataset_summary.json`; DOI Mendeley v2.
**LÍMITE:** Representatividad externa no demostrada.

**¿Cómo evitaron leakage?**
**RESPUESTA CORTA:** Split por `project_id`, whitelist sin targets, fit TRAIN y selección en VALIDATION.
**EVIDENCIA:** `split_manifest.json`, `feature_manifest.json`, `tests/test_split_no_leakage.py`.
**LÍMITE:** CPI/progreso tardíos siguen próximos al outcome simulado.

**¿Por qué Critical Recall es 56.82 %?**
**RESPUESTA CORTA:** Detecta 25/44 Critical; 13 quedaron At Risk y 6 Healthy.
**EVIDENCIA:** `health_confusion_matrix.csv`; `metrics.json`.
**LÍMITE:** La alerta binaria no corrige la severidad multiclase.

**¿Por qué Delay es débil?**
**RESPUESTA CORTA:** MAE 27.710468 días mejora marginalmente el baseline 27.850313.
**EVIDENCIA:** `reports/0.9.0-academic/baselines.json`.
**LÍMITE:** No es una estimación precisa garantizada.

**¿Por qué conservar Delay?**
**RESPUESTA CORTA:** Es parte del experimento congelado; cambiarlo alteraría el resultado histórico.
**EVIDENCIA:** Artifact 0.9.0-academic y comparación VALIDATION del experimento Delay.
**LÍMITE:** No se afirma calidad suficiente para decisiones de plazo.

**¿Por qué Cost tiene R² tan alto?**
**RESPUESTA CORTA:** CPI/EVM y outcome mantienen relación estructural en el generador sintético.
**EVIDENCIA:** MAE 0.147158 pp; R² 0.991816; temporal MAE 3.136943 pp al 20 %.
**LÍMITE:** No demuestra desempeño con costos reales.

**¿Qwen predice?**
**RESPUESTA CORTA:** No; LightGBM predice y Qwen explica evidencia estructurada.
**EVIDENCIA:** `recommendations.py`, arquitectura y metadata API.
**LÍMITE:** La explicación puede contener errores semánticos.

**¿Qué pasa si Qwen falla?**
**RESPUESTA CORTA:** Se usa fallback determinístico y se conserva la predicción ML.
**EVIDENCIA:** `tests/test_genai_grounding.py`.
**LÍMITE:** Análisis individual espera timeout; fallback no es GenAI.

**¿Por qué Qwen?**
**RESPUESTA CORTA:** Por integración local existente y requisitos técnico-operativos.
**EVIDENCIA:** `docs/genai_model_selection.md`; benchmark comparativo parcial.
**LÍMITE:** No se demostró superioridad frente a otros modelos.

**¿Por qué no compararon los LLM?**
**RESPUESTA CORTA:** La comparación ahora se implementó; solo Qwen estaba disponible en esta máquina.
**EVIDENCIA:** `reports/genai/comparison/benchmark_summary.json`.
**LÍMITE:** Gemma y Ministral quedan `not_available`; la comparación es parcial.

**¿Team Health es IA?**
**RESPUESTA CORTA:** Es una heurística operacional determinística, no un modelo supervisado.
**EVIDENCIA:** `src/prunin_ai/features/team_health.py`.
**LÍMITE:** No usar como salud mental, moral o evaluación individual de RR. HH.

**¿Los drivers son causales?**
**RESPUESTA CORTA:** No; son sensibilidad local al sustituir una feature por referencia.
**EVIDENCIA:** `model_runtime.py` y disclaimers UI/API.
**LÍMITE:** No estiman efectos de intervención.

**¿Cómo detectan OOD?**
**RESPUESTA CORTA:** Perfil TRAIN, fence univariado de 1.5 IQR y categoría no vista; API solo advierte.
**EVIDENCIA:** `input_profile.json`, `monitoring/drift.py`, tests de drift.
**LÍMITE:** No detecta todos los cambios multivariados y no altera predicción.

**¿Kubernetes está desplegado?**
**RESPUESTA CORTA:** No; el manifiesto se valida estáticamente.
**EVIDENCIA:** `tests/test_deployment_manifests.py`; “deployment automation/design validated statically; production cluster not operated.”
**LÍMITE:** No se operó ni validó un clúster.

**¿Es escalable?**
**RESPUESTA CORTA:** Hay prueba local de concurrencia, no validación productiva de escalabilidad.
**EVIDENCIA:** `reports/genai/concurrency/summary.json`; HPA del manifiesto.
**LÍMITE:** Sin carga sostenida ni clúster real.

**¿Hay retraining automático?**
**RESPUESTA CORTA:** No; requiere datos/outcomes aprobados y comparación en VALIDATION.
**EVIDENCIA:** `docs/mlops_production.md`; `docs/drift_monitoring.md`.
**LÍMITE:** TEST debe permanecer congelado; no hay servicio activo.

**¿Está listo para producción?**
**RESPUESTA CORTA:** No; es un prototipo académico.
**EVIDENCIA:** Model card, ética, readiness y diseño Kubernetes.
**LÍMITE:** Faltan validación prospectiva, accesos, monitorización central y pruebas de operación.

**¿Qué falta para producción?**
**RESPUESTA CORTA:** Datos reales aprobados, evaluación externa, seguridad operacional, observabilidad y capacidad probada.
**EVIDENCIA:** `docs/mlops_production.md`; `docs/ethics_security.md`.
**LÍMITE:** Esta lista no significa que el despliegue esté iniciado.

**¿Se validó con empresas?**
**RESPUESTA CORTA:** No.
**EVIDENCIA:** Dataset Mendeley sintético; no hay estudio empresarial versionado.
**LÍMITE:** No afirmar ROI, utilidad o generalización empresarial.

**¿Cómo justifican eficiencia?**
**RESPUESTA CORTA:** Con mediciones automatizadas de latencia, percentiles, throughput, éxito y batch.
**EVIDENCIA:** `reports/efficiency/`; prueba de concurrencia local.
**LÍMITE:** No mide ahorro ni productividad humana.

**¿Qué significa Macro F1?**
**RESPUESTA CORTA:** Media no ponderada del F1 de las clases.
**EVIDENCIA:** Health Macro F1 0.627576; baseline 0.277940.
**LÍMITE:** No equivale a porcentaje de acierto ni calibración.

**¿Qué pasa con falsos negativos?**
**RESPUESTA CORTA:** Puede no activarse una alerta; por eso hay que revisar casos y mantener decisión humana.
**EVIDENCIA:** Matriz de confusión y recall por clase.
**LÍMITE:** El daño operativo no se midió con usuarios.

**¿Qué pasa con Critical clasificado At Risk?**
**RESPUESTA CORTA:** Es error de severidad, pero sí activa Risk Alert.
**EVIDENCIA:** Matriz Health y métricas Risk Alert separadas.
**LÍMITE:** La alerta no sustituye el diagnóstico de severidad.

**Cierre de respuesta:** si la pregunta pide evidencia ausente, reconocer el límite y señalar el protocolo/pendiente; no improvisar una cifra.
