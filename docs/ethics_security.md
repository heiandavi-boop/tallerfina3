# Ética, privacidad y seguridad

PRUNIN apoya decisiones humanas. No sustituye al director de proyecto. La matriz distingue medidas técnicas existentes de controles productivos pendientes; no afirma que todos los riesgos estén resueltos ni acredita automáticamente Nivel 4.

## Tabla 1. Matriz de riesgos y controles

La probabilidad es una valoración cualitativa de diseño (baja/media/alta), no una frecuencia medida. El riesgo residual permanece y requiere evaluación antes de uso real.

| Riesgo | Impacto | Probabilidad cualitativa | Mitigación implementada | Mitigación futura | Riesgo residual | Evidencia |
|---|---|---|---|---|---|---|
| Bias entre subgrupos | Daño o peor atención para grupos no representados | Desconocida; no hay atributos/evidencia de subgrupos | Métricas por clase y limitación explícita | Evaluar equidad con grupos legítimos y gobernanza | Alto/desconocido: no se evaluaron subgrupos | `reports/0.9.0-academic/metrics.json`; model card |
| Imbalance de labels | Falsos negativos de clases minoritarias | Alta en TEST, medida por distribución | Macro F1, balanced accuracy, recall y baseline | Obtener más outcomes representativos; definir costos con interesados | Critical Recall permanece 56.82 % | `health_confusion_matrix.csv`; metrics |
| Representatividad sintética | Generalización inválida a empresas | Alta como límite de diseño | Procedencia y disclaimer visibles | Validación prospectiva externa aprobada | No hay validación empresarial | `dataset_summary.json`; `docs/model_card.md` |
| Privacidad y transferencia externa | Exposición de datos o transmisión no autorizada a proveedores | Media/alta según datos y despliegue | Ollama opcional local; OpenAI recibe evidencia estructurada solo cuando se selecciona; clave no se versiona | Clasificación, consentimiento/autorización, minimización, políticas de retención y revisión legal antes de proyectos reales | Persisten riesgos de terceros y del navegador, sin auditoría externa | `recommendations.py`; `docs/ai_providers.md` |
| Alucinaciones | Recomendación falsa o engañosa | Media/alta; muestra pequeña | JSON schema, allow-list, grounding numérico, timeout y fallback | Evaluación semántica humana y casos adversariales | Grounding no verifica verdad semántica | `tests/test_genai_grounding.py`; reporte Qwen |
| Automation bias | Aceptación acrítica de alertas | Media, no medida | Disclaimers, explicación de severidad y revisión humana | Estudio humano y aprobación institucional | No hay mecanismo de aprobación empresarial | `docs/human_efficiency_validation.md`; frontend |
| Falsa causalidad | Intervención equivocada por driver correlacional | Media | Etiquetas de sensibilidad local y advertencia “no demuestra causalidad” | Validar cualquier intervención con diseño causal independiente | Drivers no son causas | `model_runtime.py`; frontend |
| Leakage | Métricas optimistas | Media por cercanía temporal EVM | Split por project_id, whitelist, preprocesamiento TRAIN, TEST reservado | Evaluación temporal externa con outcomes disponibles al corte | Proximidad CPI/progreso tardío persiste | `split_manifest.json`; `feature_manifest.json` |
| Drift | Degradación no detectada | Alta si población cambia; no medida | CLI offline PSI/missing-rate, esquema, hashes y reporte fechado; opción de exit code ante alerta | Agendarlo en un entorno con datos autorizados y revisar outcomes | No hay scheduler ni monitor productivo/alertas centralizadas | `scripts/check_drift.py`; `reports/technical_closure/drift_monitoring_2026/` |
| OOD | Entrada válida sintácticamente pero ajena a TRAIN | Media, no medida en usuarios | Aviso por fence IQR/categoría no vista; no cambia predicción | Calibrar límites con datos aprobados, monitorizar falsos avisos | Fence univariado no detecta toda combinación OOD | `input_profile.json`; API `input_quality` |
| Datos faltantes | Resultado basado en evidencia insuficiente | Media | Coverage gate ≥60 %, lista de faltantes e imputación declarada | Captura más completa y análisis por patrón de falta | Imputación puede sesgar la salida | `ModelRuntime`; tests API |
| Acceso no autorizado y gasto API | Uso indebido de datos, claves y presupuesto de OpenAI | Alta si el servicio se publica sin controles | Token Bearer opcional, fallo cerrado en producción si falta token, CORS sin `*` en producción, límite por IP par/minuto y cuota diaria por proceso | HTTPS en servidor, identidad por usuario y cuotas distribuidas | Autenticación sigue siendo opcional fuera de producción; detrás de proxy la IP observada puede ser la del proxy; las cuotas no se coordinan entre réplicas | `security.py`; `app.py`; `tests/test_security_controls.py` |
| Ejecución de proveedor no configurado | Consumo de recursos o transferencia no esperada | Media | La selección del cliente no puede habilitar Ollama cuando `PRUNIN_ENABLE_OLLAMA=0`; devuelve fallback determinístico | Mantener allow-list de proveedores y probarla al cambiar el contrato | La aplicación no incorpora un rate limit global para todas las solicitudes | `recommendations.py`; `tests/test_security_controls.py` |
| Prompt injection / entrada estructurada malformada | Alterar instrucciones o forzar salida no permitida | Baja/media; no hay texto libre en contrato ML | Tipos/rangos/categorías, JSON schema, prompt fijo y allow-list | Tests adversariales, límites de tamaño y defensa de runtime | Categorías y evidencias no prueban ausencia de ataque semántico | `schema.py`; `recommendations.py`; tests |
| Disponibilidad del LLM | Análisis individual demora o cae a fallback | Media | Timeout, estado, código de error y fallback; ML independiente | Prueba de carga controlada y política de capacidad | Degradación/latencia local depende del runtime | `recommendations.py`; tests |
| Team Health mal usado | Inferencia psicológica o daño a integrantes | Media | “Condición operativa”; regla determinística; no imputación; exclusión de RR. HH. | Política de uso, revisión legal y capacitación | Puede ser reinterpretado por usuario | `team_health.py`; `docs/model_card.md` |
| Trazabilidad insuficiente | No reconstruir decisión/modelo usado | Baja/media | prediction_id, versión, inputs y logs de motor/tiempos | Almacenamiento append-only, retención y auditoría | Logs son locales/en memoria, no auditoría empresarial | `app.py`; export JSON; `/metrics` |
| Desajuste de versión de modelo | Respuesta asociada al artifact equivocado | Media en operaciones manuales | Registro versionado con hashes; estados separados de demo, congelado, candidato y selección; metadata y readiness | Manifest firmado, validación de hashes al cargar y despliegue controlado | Registro local; no hay despliegue empresarial | `reports/mlops/model_registry.json`; `ModelRuntime` |
| Uso en decisiones de RR. HH. | Decisión de alto impacto sobre personas basada en heurística | Baja dentro del propósito, impacto alto | Disclaimer explícito y no uso psicológico/de individuos | Prohibición institucional y controles de acceso/caso de uso | No se puede impedir mal uso fuera del prototipo | model card; UI Team Health |
| Overconfidence | Tratar scores como certeza/probabilidad calibrada | Media | Caveats para fusión, Delay, Cost, drivers y métricas | Calibración y validación prospectiva, sin alterar este cierre | Fusión 0.85/0.15 no calibrada; incertidumbre de dominio | model card; README |
| Uso productivo prematuro | Pérdida operativa/financiera por despliegue sin validación | Media | “No listo para producción”; CI construyó y probó contenedor demo; el registro no marca demo como producción | Revisiones de seguridad, carga, datos y aprobación formal | Sin daemon Docker local, clúster ni validación empresarial | `docs/mlops_production.md`; CI de `main`; registro |
| Error de lectura Delay/Cost | Interpretar ahorro como sobrecosto o Delay como preciso | Media | Delay raw/truncado separado; Cost negativo rotulado como debajo del presupuesto | Pruebas de comprensión con usuarios | Delay predictivo débil; presentación no mejora precisión | frontend tests; informe |

Fuente: `schema.py`, `app.py`, `model_runtime.py`, `recommendations.py`, `monitoring.py`, `team_health.py`, tests y reportes académicos. Los avisos human-in-the-loop son controles de comunicación, no evidencia de supervisión institucional desplegada.

## Límites y uso responsable

Mendeley v2 es un dataset sintético externo publicado en Mendeley Data. Se necesita validación real antes de uso empresarial. Team Health no representa salud mental, moral o satisfacción psicológica; no debe utilizarse para evaluar individuos. Fusión 0.85/0.15 no calibrada. Drivers son sensibilidad local, no causalidad. Grounded_fallback es determinístico, no GenAI. Cost negativo puede indicar ahorro; Delay raw permanece disponible.

La validación de cifras y allow-list no demuestra ausencia de errores de significado. El caso PROJ_0840 rechazado por cifra no soportada muestra el guardrail actuando, no mitigación total de alucinaciones. Una persona debe revisar relevancia, viabilidad y contexto antes de decidir.

## Uso futuro de datos empresariales

Antes de incorporar proyectos reales o activar OpenAI en una instancia multiusuario: autenticación y autorización en FastAPI, HTTPS con control en servidor, límites de gasto y registros sin secretos, clasificación de datos y evaluación de contrato/tratamiento con proveedor. Después, acordar propósito/base de tratamiento; minimizar y clasificar datos; establecer acceso, retención/borrado y registro de auditoría; seudonimizar identificadores; validar moneda/magnitudes, categorías y distribución; obtener outcomes con revisión humana; evaluar temporalmente y por subgrupos. Estas acciones son pendientes productivos, sin añadir login, cloud ni nuevas funcionalidades en este cierre.

La ausencia de datos reales impide fijar umbrales de drift, certificar representatividad o cuantificar daño residual. Se propone revisar métricas cuando existan outcomes aprobados, sin escoger modelos usando TEST congelado. Ver `mlops_production.md` y `model_card.md`.

## Evidencia de controles técnicos (cierre local)

La aplicación devuelve HTTP 503 para rutas API protegidas si `PRUNIN_ENV=production` y no existe `PRUNIN_API_TOKEN`; health, readiness y métricas siguen accesibles para probes. El límite OpenAI predeterminado es 20 solicitudes por minuto por dirección IP par observada por ASGI y 500 llamadas por día por proceso. Ambos contadores son memoria local y se reinician al reiniciar el proceso; **no son cuotas globales** ni límites de facturación.

Durante la revisión se comprobó que un encabezado `X-PRUNIN-Provider: ollama` podía forzar una inferencia aunque la bandera del servidor indicara proveedor deshabilitado. Se eliminó esa excepción: la bandera configurada en el servidor ahora tiene precedencia y la API usa fallback determinístico. Las pruebas verifican que esa ruta no llama al transporte Ollama. Esto no sustituye un límite general de solicitudes ni la autenticación obligatoria en un despliegue multiusuario.

## Controles del API implementados (noviembre de 2026)

| Riesgo | Control | Evidencia |
|---|---|---|
| Uso no autorizado del API | Token Bearer opcional en backend (`PRUNIN_API_TOKEN`); health, ready y metrics quedan públicos | `src/prunin_ai/api/security.py`, `tests/test_security_controls.py` |
| Orígenes no confiables | `PRUNIN_ENV=production` rechaza `CORS *`; los orígenes son explícitos | ídem |
| Costos y abuso de OpenAI | Límite por cliente por minuto y cuota diaria; respuesta 429 con `Retry-After` y código de fallo | ídem |
| Gasto experimental | Presupuesto estimado (USD 5, margen 1,5×) que bloquea antes de cada llamada | `scripts/benchmark_provider_comparison.py` |
| Fuga de claves | La clave se toma solo del entorno o de la sesión; los reportes registran presencia/ausencia, nunca el valor | `execution_manifest.json` |

**Pendiente:** gestión de identidades multiusuario, HTTPS terminado en un despliegue real, persistencia distribuida de cuotas (hoy en memoria por proceso) y revisión humana externa de las recomendaciones.
