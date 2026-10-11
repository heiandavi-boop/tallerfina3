# Guion técnico para la demo de PRUNIN AI Core

Base main revisada y confirmada remotamente: `b2d0ca32f0599fc6c2227f2a5eb3e6dea6ff812a` (11 de octubre de 2026). Para estado final de cambios/CI consultar `docs/FINAL_READINESS.md`; no presentar un HEAD anterior como validación de cambios nuevos.

## Preparación

```bash
./scripts/preflight_demo.sh
./scripts/run_playground.sh
```

Exigir `RESULTADO: LISTO PARA DEMO` y comprobar que el artefacto sea `0.9.0-academic`. El fallback demo está rotulado y no acredita métricas académicas. El preflight usa TestClient local; la apertura del servidor en navegador es comprobación adicional del expositor. No reentrenar durante la preparación final.

GenAI tiene preflight separado: `./scripts/preflight_genai.sh`. Ollama ausente no invalida ML ni el benchmark Qwen versionado completo. Si se usa LAN/QR comprobar red del salón. El frontend debe estar construido; no asumir que el clon incluye dist o modelos pesados.

## Secuencia de demo

1. Presentar problema y dataset sintético externo, sin afirmar producción.
2. Abrir detalles técnicos: versión, dataset, features, LIVE, prediction_id, probabilidades y tiempos.
3. Analizar el preset En riesgo. El nombre del preset es un escenario de entrada, no garantía de la clase predicha. Mostrar Health ML, Final Status derivado, Delay operacional y raw, Cost, Team Health si calculable y sensibilidad local.
4. What-if: modificar SPI/CPI (ML) y señales de equipo (heurística). No modificar variables not_used para prometer efectos ML. Mostrar diferencias, no causalidad.
5. Descargar plantilla y subir CSV hasta 100 filas. Categorías: construction, healthcare, it, manufacturing, marketing, r&d; metodología agile, hybrid, kanban, scrum, waterfall. Siete features completas evitan imputación ML. Sin señales suficientes de equipo no se inventa score; la columna se oculta si ninguna fila tiene valor válido.
6. Mostrar recomendaciones individuales: distinguir ollama:qwen3:8b de grounded_fallback. CSV/What-if no llaman Qwen. JSON descargable conserva delay_days_raw; delay_days=max(0, raw). Cost negativo puede indicar ahorro y no se trunca.
7. Mostrar reportes oficiales: Health Macro F1 0.627576 / baseline 0.277940; Delay MAE 27.710468 / 27.850313 días; Cost MAE 0.147158 pp y R² 0.991816 con caveat EVM. Después evaluación temporal con cobertura.
8. Mostrar JSON GenAI `complete`: 30 casos, 29/30 aceptados/grounded, schema/features 1.0, actionability 1.0 (proxy), una cifra no soportada, mediana 3092.645 ms y p95 6634.72 ms. No son métricas de eficacia empresarial.
9. Cerrar con ética, manifests/hashes, readiness/metrics y diseño Docker/Kubernetes. Solo mostrar CI verde correspondiente al commit comprobado.

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
