# Guion técnico para la demo de PRUNIN AI Core

Cierre definitivo aplicado sobre main inicial `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a`, actualizado desde remoto y con el cierre anterior integrado sin duplicaciones. El HEAD final y CI se verifican por commit, no por un workflow histórico; ver docs/FINAL_READINESS.md.

Preparación oral: docs/PRESENTACION_FINAL.md (7/10/12 min, voz y postura pendientes), docs/GLOSARIO_DEFENSA.md y docs/PREGUNTAS_DEFENSA.md (32 respuestas con evidencia).

## Preparación

```bash
./scripts/preflight_demo.sh
./scripts/run_playground.sh
```

Exigir `RESULTADO: LISTO PARA DEMO` y comprobar que el artefacto sea `0.9.0-academic`. El fallback demo está rotulado y no acredita métricas académicas. El preflight usa TestClient local; la apertura del servidor en navegador es comprobación adicional del expositor. No reentrenar durante la preparación final.

GenAI tiene preflight separado: `./scripts/preflight_genai.sh`. Ollama ausente no invalida ML ni el benchmark Qwen versionado completo. Si se usa LAN/QR comprobar red del salón. El frontend debe estar construido; no asumir que el clon incluye dist o modelos pesados.

## Secuencia de demo para sustentación

1. Problema: apoyar al director/PMO al interpretar riesgo, sin reemplazar su decisión.
2. Arquitectura: separar LightGBM, heurísticas y explicación; usar diagrama, no código largo.
3. Dataset: Mendeley v2, dataset sintético externo publicado en Mendeley Data; split por proyecto.
4. Predicción individual: analizar preset y señalar versión/LIVE. El nombre del preset no garantiza su clase predicha.
5. Health probabilities: leer probabilidades y clase; no confundir con fusión calibrada.
6. Delay/Cost: Delay operacional ≥0 y raw técnico; Cost negativo válido; limitaciones oficiales explícitas.
7. Drivers: sensibilidad local; no decir que son causas.
8. Qwen: mostrar explicación individual y flags genai_used/engine. Si fallback, llamarlo determinístico. Benchmark oficial complete: 30 casos, 29/30 aceptados/grounded, mediana 3092.645 ms, p95 6634.72 ms; schema/features/acción no vacía 1.0 como proxies.
9. What-if: modificar SPI/CPI y distinguir señales de equipo; no prometer intervenciones causales. No llama al LLM.
10. CSV: plantilla hasta 100 filas; ML completa sin imputación, Team Health opcional sin inventar señales. Columna oculta si ningún score calculable; visible si alguno. No llama Qwen. Tipos: construction, healthcare, it, manufacturing, marketing, r&d; metodologías: agile, hybrid, kanban, scrum, waterfall.
11. Trazabilidad: prediction_id, versión, timing y raw; mostrar solo el fragmento JSON necesario o descargar evidencia.
12. CI/MLOps: run exacto del commit completed/success; manifests/hashes; readiness/monitoring brevemente. Kubernetes es diseño, sin clúster activo.
13. Limitaciones: Health Macro F1 0.627576 frente a 0.277940; Delay MAE 27.710468 frente a 27.850313 días; Cost MAE 0.147158 pp y R² 0.991816 con caveat EVM. Al 20 % solo 236/600 (39.333 %). Medición humana y validación empresarial pendientes.

La demo no es un benchmark de eficiencia humana. Priorizar problema y resultados sobre terminales/infraestructura. Para 7 min elegir una interacción; para 10/12 min ampliar según plan de diapositivas.

## Contingencias y límites

Sin Internet la inferencia local puede funcionar si frontend y artefactos están presentes. Sin Ollama funciona el fallback determinístico. Cobertura ML menor al 60 % bloquea inferencia; mostrar error por fila. Team Health exige señales observadas sin imputación. Drivers no son causales, fusión 0.85/0.15 no calibrada. No afirmar mejora humana hasta medirla. La demo no prueba validación empresarial ni escalabilidad productiva.

La prueba manual adicional de 99 proyectos balanceados comunicada por el autor no tiene un resultado estructurado versionado identificado; no se convierte en métrica oficial. El test reproducible local de 99 filas es una verificación distinta de contrato/cobertura. TEST oficial sigue siendo 600 proyectos.

## Preguntas difíciles

**¿Por qué el dataset es sintético?**

La fuente declara trayectorias y outcomes simulados. Su procedencia externa y publicación no lo convierten en proyectos empresariales reales.

**¿Por qué usar datos sintéticos?**

Permiten desarrollar y reproducir el pipeline con snapshots/outcomes disponibles sin exponer datos empresariales. No reemplazan representatividad ni validación externa.

**¿Qué falta para producción?**

Proyectos reales con outcomes, validación externa/prospectiva, controles de acceso y datos, observabilidad central, alertas/drift, calibración y pruebas operacionales/carga.

**¿Por qué Delay es débil?**

Su MAE TEST 27.710468 apenas mejora 27.850313 del baseline. Las siete features y el benchmark sintético ofrecen señal limitada; no atribuimos una causa empírica no estudiada.

**¿Por qué no reemplazaron Delay?**

El experimento seleccionó la mediana TRAIN según MAE VALIDATION (27.901042 vs 28.881476 del LightGBM), con promoción automática deshabilitada. El artefacto académico permaneció congelado; este cierre no cambia modelos ni utiliza TEST para seleccionarlos.

**¿Por qué Cost tiene R² tan alto?**

Existe una relación estructural CPI/EVM–outcome en el generador sintético. R² 0.991816 es desempeño interno tardío, no precisión productiva; la evaluación temporal es menos favorable.

**¿Por qué Qwen?**

Ejecución local, español, tamaño e integración Ollama. Selección técnico-documental frente a Gemma/Ministral; se evaluó Qwen, sin comparar empíricamente los tres.

**¿Qwen predice los resultados?**

No. LightGBM predice Health, Delay y Cost. Qwen explica evidencia y genera recomendaciones; Final Status deriva de Health.

**¿Qué pasa si Ollama falla?**

ML permanece disponible y se activa grounded_fallback determinístico. El resultado indica motor, intento, uso y error; no se presenta fallback como GenAI.

**¿Team Health es IA?**

En este proyecto es una heurística operacional determinística, no ML supervisado ni evaluación psicológica.

**¿Por qué Team Health no aparece siempre?**

Necesita al menos tres señales válidas y cobertura de peso 0.5. No imputamos señales ausentes; si ninguna fila CSV tiene score, la columna se oculta por completo.

**¿Los drivers son causales?**

No. Son sensibilidad local al sustituir una feature por su referencia manteniendo las demás; no representan intervenciones causales.

**¿Cómo evitaron leakage?**

Split por project_id, conjuntos disjuntos, whitelist sin outcomes, preprocesamiento TRAIN y selección VALIDATION. Persiste riesgo de proximidad temporal con CPI/EVM tardío en simulación.

**¿Por qué el baseline Health puede tener accuracy alta?**

La clase mayoritaria at_risk representa 429/600 TEST. Predecir siempre esa clase da accuracy 0.715 pero Macro F1 0.277940 y recall critical cero.

**¿Qué significa Macro F1?**

F1 combina precisión y recall; Macro F1 promedia por igual el F1 de las clases, sin ponderar por su frecuencia. Hace visibles fallas en clases minoritarias.

**¿El modelo funciona temprano?**

Hay evaluación por avance: Macro F1 0.397938 al 20 % y 0.570588 al 80 %. La cobertura al 20 % es 236/600 (39.333 %); anticipación limitada, sin garantía empresarial.

**¿Está desplegado en Kubernetes?**

No hay evidencia de clúster activo. El YAML diseña tres réplicas, probes, Service, RollingUpdate y HPA 3–10. No se desplegó ni probó en producción.

**¿Qué demuestra la prueba de 99 filas?**

El autor comunicó una prueba manual balanceada que produjo las tres clases. No identificamos resultados estructurados versionados de esa corrida, por lo que no calculamos métricas recordadas. El test local existente valida contrato/cobertura de 99 filas, sin asegurar balance; lo oficial sigue siendo TEST de 600 proyectos.

**¿Demostraron ahorro humano?**

No todavía: mediana GenAI 3.092645 s no es baseline humano ni tiempo end-to-end. El protocolo de cinco casos está pendiente en docs/efficiency_evaluation.md.

Guion de diapositivas: `docs/PRESENTACION_FINAL.md`. Informe: `docs/INFORME_FINAL.md`. Referencias: `docs/references.md`.
