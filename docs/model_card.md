# Model Card — 0.9.0-academic

## Propósito y uso recomendado

Prototipo académico de apoyo a decisiones de gestión de proyectos. Uso: demostración reproducible, evaluación interna sobre el benchmark sintético y exploración supervisada de escenarios. No usar autónomamente para compromisos de costo/plazo, evaluación de personas ni decisiones empresariales de alto impacto. Requiere human oversight y validación externa antes de uso empresarial.

## Dataset y procedencia

Mendeley Data v2, DOI `10.17632/2p5sz57wh2.2`: dataset sintético externo publicado en Mendeley Data. 4000 proyectos, 72549 snapshots; no existe validación con proyectos empresariales reales. Itemlet/Collaboration/SQuaD no se mezclan con esta población.

## Features y targets

Numéricas: planned_duration_weeks, planned_budget, true_progress, spi, cpi. Categóricas: project_type (construction, healthcare, it, manufacturing, marketing, r&d), methodology (agile, hybrid, kanban, scrum, waterfall). El resto del catálogo no es feature académica supervisada. Mediana/moda TRAIN y OneHotEncoder forman el pipeline.

Health: clasificación supervisada LightGBM con etiquetas derivadas según reglas congeladas. Delay: regresión en días. Cost: regresión de ratio, donde un resultado negativo puede representar ahorro. Final Status: healthy → successful, at_risk → challenged, critical → critical; derivado de Health, sin modelo independiente.

## Split, baselines y resultados

Split por project_id: 2800 TRAIN / 600 VALIDATION / 600 TEST, sin overlap; whitelist excluye outcomes. Baselines ajustados solo en TRAIN. TEST no selecciona candidatos. Evaluación project-level usa snapshot más reciente; snapshot-level se informa aparte en los JSON.

| Evaluación TEST project-level (600 proyectos) | Modelo | Baseline TRAIN |
|---|---:|---:|
| Health accuracy | 0.7266666667 | 0.7150000000 |
| Health balanced accuracy | 0.6824223458 | 0.3333333333 |
| Health Macro F1 | 0.6275758334 | 0.2779397473 |
| Health critical recall | 0.5681818182 | 0 |
| Delay MAE (días) | 27.7104683426 | 27.8503125000 |
| Cost MAE (puntos porcentuales) | 0.1471578505 | 5.0974437328 |
| Cost R² | 0.9918156959 | -0.0080230304 |

TEST Health: 429 at_risk / 44 critical / 127 healthy. Accuracy alta del baseline no significa utilidad multiclase: Macro F1 refleja el desbalance. Critical recall es limitado.

## Evaluación temporal

| Avance máximo | Proyectos TEST | Cobertura | Health Macro F1 | Delay MAE días | Cost MAE pp |
|---|---:|---:|---:|---:|---:|
| 20 % | 236/600 | 39.333 % | 0.397938 | 33.146183 | 3.136943 |
| 40 % | 463/600 | 77.167 % | 0.509355 | 30.406823 | 2.789373 |
| 60 % | 576/600 | 96.000 % | 0.522959 | 28.305607 | 2.143231 |
| 80 % | 599/600 | 99.833 % | 0.570588 | 27.522773 | 1.406718 |

Una observación elegible por proyecto y cutoff. Al 20 % no se evaluaron todos los 600; las poblaciones de cobertura varían.

### KPI operacional de la promesa original

Además de la clasificación multiclase, se reporta una vista binaria de evaluación que no modifica el modelo: `At Risk OR Critical => Risk Alert`; `Healthy => No Alert`. Sobre TEST final, Risk Alert Recall es **82.45 %** (390/473), Precision **92.20 %** y F1 **87.05 %**. El recall exacto de Critical sigue siendo **56.82 %**.

Para la promesa temporal se usa una medida estricta de **detección de cohorte completa**: TP dividido por los 473 proyectos TEST que finalmente son At Risk/Critical, contando como no detectados los que todavía no tienen snapshot elegible. El primer corte pre-cierre que supera 75 % es **60 % de avance**, con **75.90 %** (359/473) y **96.00 %** de cobertura TEST. Esta evidencia es interna al benchmark sintético y no acredita generalización empresarial.

Fuente: `reports/promise_validation/`.

## Heurísticas operacionales y explicación

Team Health es heurística operacional determinística no psicológica, sin imputación, con mínimo tres componentes y cobertura ponderada 0.5. Fusión 0.85/0.15 no calibrada con outcomes reales. Drivers son sensibilidad local, no causalidad. Qwen explica/recomienda; no genera predicciones ML. Fallback determinístico no es GenAI.

## Política de presentación de Delay

La predicción de regresión cruda puede ser ligeramente negativa. La interfaz aplica una restricción operacional de cero días para presentación, conservando el valor crudo en la trazabilidad técnica.

API: delay_days=max(0, delay_days_raw). Reportes académicos: predicciones crudas intactas. Cost negativo no se trunca.

## Limitaciones y usos no recomendados

Delay es el modelo predictivo más débil y su mejora es marginal. Cost tiene rendimiento muy alto relacionado en parte con la relación estructural CPI/EVM–outcome del generador sintético; su R² no prueba rendimiento empresarial. La separación por proyecto no elimina proximidad temporal de variables tardías. No hay calibración con outcomes PRUNIN ni validación productiva. No interpretar fusión como probabilidad calibrada, drivers como causas o Team Health como modelo supervisado. No automatizar decisiones sin revisión humana.

Fuentes: reports/0.9.0-academic/; docs/references.md; docs/INFORME_FINAL.md. Artefactos, configuración y reglas permanecen congelados durante el cierre.

## Alcance de validación y comunicación de cierre

La revisión final distingue métricas congeladas de smoke tests de API/GenAI. Datos faltantes reciben solo la imputación ML declarada; inputs de rangos válidos pueden seguir fuera de distribución. No hay detector OOD/drift automático productivo. La muestra Qwen está condicionada a drivers y no acredita utilidad profesional; no sustituye human oversight. No usar baseline accuracy ni R² como prueba de validez empresarial.

La pregunta de investigación, medios de comunicación y conclusiones están en INFORME_FINAL.md; la matriz PAIII incluye RA1/RA2. Las técnicas vocales y lenguaje no verbal requieren ensayo, el ahorro humano sigue pendiente y MLOps no incluye retraining continuo real. Propósito y usos recomendados/no recomendados permanecen sin cambios de modelos ni targets.
