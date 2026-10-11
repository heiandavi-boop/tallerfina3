# Ética, privacidad y seguridad

PRUNIN apoya decisiones humanas. No sustituye al director de proyecto. La matriz distingue medidas técnicas existentes de controles productivos pendientes; no afirma que todos los riesgos estén resueltos ni acredita automáticamente Nivel 4.

## Tabla 1. Riesgos, impactos y controles

| Riesgo | Impacto | Mitigación implementada | Limitación restante |
|---|---|---|---|
| Sesgo/desbalance | Desatender clases minoritarias | Macro F1, balanced accuracy y recall por clase; baseline explícito | Recall crítico incompleto; no validación de subgrupos empresariales |
| Dataset sintético / representatividad | Generalizar simulación a empresas | Procedencia sintética y limitaciones en README/model card | Validación externa/prospectiva real pendiente |
| Privacidad | Transferencia de información de proyectos | Ollama local; prompt con evidencia estructurada, no texto libre del proyecto | Local no reemplaza control de acceso, minimización/retención |
| Seguridad y exposición de información | Acceso no autorizado o exposición técnica | Validación Pydantic, límites CSV y CORS configurable; debug GenAI apagado por defecto | Sin autenticación/rate limiting productivo; JSON/debug puede incluir entradas |
| Alucinación / output no grounded | Texto convincente con cifras o features no soportadas | Prompt grounded, esquema, allow-list y validador de cifras; rechazo y fallback | No verifica verdad semántica total; exige revisión humana |
| Automation bias / decisiones humanas | Aceptar recomendación como decisión | Avisos y separación entre ML, heurísticas y explicación | No hay ensayo humano de sesgo ni mecanismo de aprobación empresarial |
| Falsa causalidad | Tratar perturbaciones/importance como causas | Drivers rotulados sensibilidad local; advertencia explícita | Correlaciones/perturbaciones no prueban intervenciones |
| Leakage | Métricas optimistas por información futura | Split por project_id, whitelist outcomes excluidos, preprocesamiento TRAIN | CPI/progreso tardíos próximos al outcome sintético |
| Drift | Degradación con nueva población/tiempo | Versionado, hashes, métricas runtime y política de actualización | No detector de drift productivo ni alertas centralizadas |
| Datos faltantes | Inferencia con información insuficiente | Missing_trained_features/cobertura; gate ≥60 %; imputación TRAIN visible | Imputación puede debilitar resultado; cobertura no es calidad total |
| Inputs fuera de distribución (OOD) | Rangos válidos pero combinación inédita | Validación de rangos/categorías y aviso de límite sintético | No detector estadístico OOD; magnitudes/moneda deben validarse antes de uso real |
| Disponibilidad LLM | Fallo/timeout bloquea interpretación | Timeout acotado y fallback; ML independiente; batch/What-if sin Qwen | Análisis individual espera timeout; concurrencia no validada |
| Team Health | Inferir psicología o perjudicar individuos | Heurística operacional; mínimo componentes/cobertura; sin imputación | Sin calibración empresarial; no usar en decisiones individuales de RR. HH. |
| Trazabilidad | No identificar modelo, input o fallo | Prediction_id, versión, JSON de resultado, logs de motor/tiempos/errores | Logs no constituyen almacenamiento central persistente ni auditoría empresarial |
| Presentación Delay/Cost | Ocultar negativos o alterar métricas | Delay operacional ≥0 con raw preservado; Cost negativo intacto | Clamp no mejora precisión académica ni elimina debilidad Delay |

Fuente: `schema.py`, `app.py`, `model_runtime.py`, `recommendations.py`, `monitoring.py`, `team_health.py`, tests y reportes académicos. Los avisos de human-in-the-loop son controles de comunicación, no evidencia de supervisión institucional ya desplegada.

## Límites y uso responsable

Mendeley v2 es un dataset sintético externo publicado en Mendeley Data. Se necesita validación real antes de uso empresarial. Team Health no representa salud mental, moral o satisfacción psicológica; no debe utilizarse para evaluar individuos. Fusión 0.85/0.15 no calibrada. Drivers son sensibilidad local, no causalidad. Grounded_fallback es determinístico, no GenAI. Cost negativo puede indicar ahorro; Delay raw permanece disponible.

La validación de cifras y allow-list no demuestra ausencia de errores de significado. El caso PROJ_0840 rechazado por cifra no soportada muestra el guardrail actuando, no mitigación total de alucinaciones. Una persona debe revisar relevancia, viabilidad y contexto antes de decidir.

## Uso futuro de datos empresariales

Antes de incorporar proyectos reales: acordar propósito/base de tratamiento; minimizar y clasificar datos; establecer acceso, retención/borrado y registro de auditoría; seudonimizar identificadores; validar moneda/magnitudes, categorías y distribución; obtener outcomes con revisión humana; evaluar temporalmente y por subgrupos. Estas acciones son pendientes productivos, sin añadir login, cloud ni nuevas funcionalidades en este cierre.

La ausencia de datos reales impide fijar umbrales de drift, certificar representatividad o cuantificar daño residual. Se propone revisar métricas cuando existan outcomes aprobados, sin escoger modelos usando TEST congelado. Ver `mlops_production.md` y `model_card.md`.
