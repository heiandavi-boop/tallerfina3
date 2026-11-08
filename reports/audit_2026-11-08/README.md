# Auditoría técnica y académica local

**Nota de publicación:** este informe es una instantánea previa al commit. Las referencias a cambios sin commit/push y al CI de HEAD base describen el momento de la auditoría, no el estado actual de main. En los reportes públicos se anonimizaron rutas personales con `.` y `~`; los originales permanecen localmente bajo `reports/closure/`, ignorado por Git. No se cambiaron cifras experimentales.

Fecha: 8 de noviembre de 2026. Repositorio: `heiandavi-boop/tallerfina3`, rama `main`. HEAD inicial y final de esta tarea: `bdc6f61c44e040c3c8ef694970c7252d8ec625bf`, sin commit ni push. La propuesta del 2 de septiembre y entrega del 20 de noviembre son fechas aportadas en la solicitud; no se localizó el documento institucional original para certificarlas.

## A. Resumen ejecutivo

Se corrigió la causa de las recomendaciones vacías: se trataba la ausencia de drivers positivos como ausencia de señales de intervención. El caso bancario IT/híbrido se reprodujo con el código de HEAD y Qwen real, que aceptó `recommendations: []`. El nuevo contrato conserva la sensibilidad del modelo y añade señales operativas verificadas e indicadores heurísticos con procedencia. No se modificó el predictor. También se corrigió el resumen duplicado, se protegieron reportes históricos contra sobrescritura, se completó el protocolo humano y se reforzaron monitorización, Docker y CI.

**27/27 criterios internos revisados: 15 DEMOSTRADOS CON LIMITACIONES, 5 PARCIALES y 7 REQUIEREN EVALUACIÓN HUMANA.** No se certifica ningún máximo oficial: la rúbrica institucional no está disponible en el workspace. El objetivo interno de nivel 4 no permite reconstruir requisitos literales, pesos ni descriptores oficiales. [Revisión detallada JSON](rubric_review.json); [auditoría histórica preservada](../rubric_final/rubric_final.json).

Los diez gates finales pasaron: backend 162 passed/1 skipped, frontend 20 passed, build correcto, npm audit sin vulnerabilidades, promesa validada y preflights demo/GenAI correctos. Las 5.406 huellas protegidas, predicciones de referencia y fingerprints originales coinciden antes/después.

No se declara productividad humana, validación empresarial, comparación completa de LLM, contenedor probado, clúster activo, escalabilidad productiva ni retraining continuo. Esos límites no se cierran cambiando documentación.

### Causa, diseño y caso bancario

Evidencia completa de entrada, predicción, drivers, prompt, contexto, respuesta cruda, JSON, validación, motor y acciones: [diagnóstico inicial](recommendations-evidence-v2.json), [corrida corregida r2](recommendations-evidence-v2-r2.json) y [robustez final](robustness-evidence-v2.json).

| Capa | Procedencia | Interpretación |
|---|---|---|
| Predicción y sensibilidad | `model_driver` | LightGBM y perturbación local; no causalidad |
| Dato operacional | `observed_operational_signal` | Entrada validada + trigger heurístico versionado, no aprendido |
| Indicador determinístico | `heuristic_indicator` | Team Health con componentes/cobertura suficientes, no modelo supervisado |

Los drivers reductores se conservan como contexto y no se alteran para fabricar importancia. Cada acción debe citar una pareja feature/source autorizada y contener prioridad, título, justificación, acción concreta y seguimiento verificable. Se rechazan cifras no respaldadas, duplicados, contradicciones explícitas, formatos inválidos y procedencias falsas. El fallback usa las mismas señales y devuelve su validación independiente. No se envían nombres ni texto libre del proyecto al LLM.

Las reglas están en [operational_signals.yaml](../../configs/operational_signals.yaml). SPI/CPI <1 son desfavorables en EVM; el trigger <0.95 añade tolerancia heurística. Los demás cortes no son umbrales académicos o empresariales validados. Faltantes y valores inválidos no se imputan para generar señales. El seguimiento normal requiere Health healthy, SPI/CPI presentes y al menos cinco señales operativas evaluables; es una política conservadora de cobertura, no una prueba de ausencia de riesgo.

En la variante IT/híbrida se obtuvieron valores reales:

| Resultado | Valor |
|---|---:|
| Health | at_risk |
| Delay | 69.6617489754 días |
| Cost | ratio 0.1327694682, equivalente a 13.27694682 % estimado |
| Final Status | challenged |
| Riesgo combinado heurístico, no probabilidad calibrada | 0.5249625769 |
| Team Health heurístico | 0.48549, critical, cinco componentes |
| Driver completo | SPI=0.72, referencia 1, impacto -0.0183, reduces_risk |
| Drivers positivos | ninguno |

Se detectaron nueve señales operativas: SPI 0.72, CPI 0.81, utilización 1.12, capacidad 0.72, productividad 0.68, retrabajo 0.19, defectos 0.11, dependencias 15 días y exposición 0.49. El contexto añadió Team Health como heurística, no como décima observación aprendida. Los campos categóricos IT/híbrido son una variante explícita: la corrida separa los campos bancarios suministrados sin adivinarlos. Presupuesto/SPI están fuera de la referencia TRAIN; estas predicciones no son validación del caso bancario ni garantía de precisión empresarial.

Antes: Qwen real devolvió «No se identifican acciones correctivas prioritarias...» y lista vacía. Después: cuatro acciones validadas, tres de prioridad alta (cronograma, capacidad y carga) y una media (verificar componentes de Team Health). Ejemplo real: **Revisar las actividades con mayor desviación frente al plan y definir un plan de recuperación para el siguiente seguimiento.** Evidencia: SPI observado; seguimiento: revisar SPI y cumplimiento del cronograma en el siguiente corte. No se inventaron responsables nominales, fechas, contratos ni montos.

La primera implementación de gramática `anyOf` omitió campos comunes en Ollama; al simplificarla, 400 tokens truncaron las acciones. Se conservaron esos diagnósticos y se corrigió la gramática, validando parejas en Python y usando 1200 tokens con timeout de 30 s. La corrida r2 aceptó 8/8 payloads, con cero cifras no soportadas, JSON inválidos o timeouts; p50 8286.095 ms y p95 16866.36 ms. Un caso válido no requería acciones: no deben interpretarse como ocho recomendaciones útiles. Son casos de desarrollo, no un benchmark held-out ni una comparación de calidad contra las métricas históricas. Las ocho respuestas pasaron también el validador final reforzado.

[Control saludable real](healthy-control.json): snapshot ML de VALIDATION `mendeley::PROJ_0009` complementado explícitamente con señales operativas favorables del preset. Health healthy y Team Health 0.952333; Qwen real devolvió lista vacía y `no_priority_signals`. Conservó drivers positivos como contexto sin inventar acciones correctivas. No es una medición de exactitud ni una afirmación de verdad empresarial.

[Prueba visual](browser_smoke.json): HTTP 200, motor Qwen real, cuatro acciones y un resumen, en escritorio 1440x1000 y móvil 390x844 sin overflow horizontal. La entrada visual conserva campos adicionales del preset; no se confunde con el caso bancario exacto. CSV no llama al LLM por fila; abrir «Ver análisis completo» sí solicita recomendaciones para ese proyecto. El fallback nunca se etiqueta como GenAI utilizada.

## B. Matriz de los 27 criterios

**L** = DEMOSTRADO CON LIMITACIONES; **P** = PARCIAL; **H** = REQUIERE EVALUACIÓN HUMANA. El estado inicial es la traducción de la matriz interna anterior. Para cada fila, requisito oficial exacto y nivel máximo exigido son **NO VERIFICABLES sin la rúbrica oficial**. El JSON contiene implementación, limitación, riesgo, acción, prueba necesaria y resultado individual completos.

| Código | Requisito interno | Inicial | Acción ejecutada/revisión | Evidencia | Final | Brecha pendiente |
|---|---|---|---|---|---|---|
| R6.1-Cr1 | Problema/contexto | L | Contraste objetivo, KPI y alcance | [Informe](../../docs/INFORME_FINAL.md) | L | Impacto empresarial no estudiado |
| R6.1-Cr2 | Selección GenAI | L | Tags/tamaños reales y salidas seguras | [Entorno](environment.json) | P | Dos candidatos ausentes; comparación pendiente |
| R6.1-Cr3 | Integración GenAI | L | Evidencia tipada, fallback y UI corregidos | [Qwen real](recommendations-evidence-v2-r2.json) | L | Semántica/utilidad humana no acreditadas |
| R6.1-Cr4 | Evaluación GenAI | L | Corridas separadas y fallos preservados | [Evaluación](../../docs/genai_evaluation.md) | L | Muestras pequeñas; proxies |
| R6.2-Cr5 | Tareas automatizables | L | CSV sin LLM; generación individual probada | [Pruebas UI](../../frontend/src/App.test.jsx) | L | Impacto en decisiones no medido |
| R6.2-Cr6 | Eficiencia/productividad | L | 80 runs nuevos y protocolo humano completo | [Benchmark](efficiency/operational_benchmark_summary.json) | P | Productividad humana NO MEDIDA |
| R6.2-Cr7 | Ética/riesgos | L | Procedencia, no falsos positivos y revisión limitada de secretos | [Ética](../../docs/ethics_security.md) | L | Seguridad, sesgos y error semántico residual |
| R6.2-Cr8 | Documentación | L | Arquitectura, métodos y auditoría actualizados | [Matriz](rubric_review.json) | L | Fuente oficial, portada y render del autor |
| RA1-F1 | Estructura escrita | L | Revisión de método/resultados/límites | [Informe](../../docs/INFORME_FINAL.md) | L | Formato institucional |
| RA1-F2 | Intención escrita | L | Separación de objetivo y resultados observados | [README](../../README.md) | L | Comprensión externa no evaluada |
| RA1-F3 | Canales/medios | L | Demo y recursos revisados; smoke visual | [Navegador](browser_smoke.json) | L | Proyección y red reales |
| RA1-F4 | Conclusiones | L | KPI, Critical, Delay y Cost diferenciados | [Promesa](../promise_validation/risk_alert_metrics.json) | L | Generalización empresarial |
| RA1-F5 | Gramática/tablas/figuras | L | Fuentes/unidades y figuras preservadas | [Figuras](../0.9.0-academic/figures/) | L | Revisión final PDF/slides |
| RA1-Referencias | Referencias | L | Fuentes y manifiestos documentados sin DOI inventados | [Referencias](../../docs/references.md) | L | Revisión APA/institucional y enlaces externos |
| RA2-F1 | Estructura oral | H | Guion existente preservado | [Ensayo](../../docs/ENSAYO_SUSTENTACION.md) | H | Exposición observada |
| RA2-F2 | Intención oral | H | Planes 7/10/12 min revisados | [Presentación](../../docs/PRESENTACION_FINAL.md) | H | Tiempo oficial y cronometraje real |
| RA2-F3 | Lenguaje profesional | H | Glosario/preguntas preservados | [Glosario](../../docs/GLOSARIO_DEFENSA.md) | H | Fluidez oral |
| RA2-F4 | Voz | H | Plantilla sin datos fabricados | [Ensayo](../../docs/ENSAYO_SUSTENTACION.md) | H | Volumen, pausas, ritmo observados |
| RA2-F5 | Recursos de apoyo | H | Demo, respaldo y evidencia preparados | [Demo](../../DEMO_PRESENTACION.md) | H | Uso efectivo en sustentación |
| RA2-F6 | Lenguaje no verbal | H | Checklist preservado | [Ensayo](../../docs/ENSAYO_SUSTENTACION.md) | H | Postura/contacto visual observados |
| RA2-F7 | Defensa | H | Evidencias y límites para preguntas difíciles | [Preguntas](../../docs/PREGUNTAS_DEFENSA.md) | H | Argumentación espontánea |
| R7.1-Cr1 | Preprocesamiento | L | Fingerprints, splits y tests revisados | [Integridad](integrity_after.json) | L | OOD univariado y datos sintéticos |
| R7.1-Cr2 | Herramientas/dominio | L | Roles, dependencias y runtimes verificados | [Gates](gates-r2.json) | L | Defensa humana; Node local distinto |
| R7.1-Cr3 | Pipeline | L | Fail-fast y fixtures CI verificados | [Entrenamiento](../../docs/training.md) | L | Entrenamiento oficial no repetido |
| R7.2-Cr4 | Despliegue automático | L | No-root, healthcheck, contexto y probes | [Dockerfile](../../Dockerfile.playground) | P | Daemon ausente; sin build/smoke de contenedor |
| R7.2-Cr5 | Escala/robustez | L | Recuperación y concurrencia acotada reales | [Robustez](robustness-evidence-v2.json) | P | Sin carga sostenida/distribuida ni clúster |
| R7.2-Cr6 | MLOps | L | Huellas, métricas y promoción/rollback documentados | [MLOps](../../docs/mlops_production.md) | P | Sin operación central/retraining continuo |

## C. Pruebas y condiciones

Registro autoritativo: [gates-r2.json](gates-r2.json), fecha/entorno por corrida y timestamp por comando. Entorno: macOS 27.2 arm64, Python 3.12.15 en `.venv`, Node 26.7.0 local, npm 11.19.0; CI declara Python 3.12 y Node 22. Tests ordinarios con Ollama desactivado; generación real solo en integración/preflight explícitos. El primer registro [gates.json](gates.json) se conserva, pero r2 separa correctamente tests y servicio externo. El archivo raíz gate-01.txt conserva el primer pip check antes de corregir una ruta relativa del registrador.

| Comando | Resultado | Archivo de evidencia |
|---|---|---|
| `python -m pip check` | Sin requisitos rotos | [gate 01](gates-r2/gate-01.txt) |
| `python -m compileall -q src scripts tests` | Código 0 | [gate 02](gates-r2/gate-02.txt) |
| `PYTHONPATH=src python -m pytest -q` | 162 passed, 1 skipped; 10.70 s | [gate 03](gates-r2/gate-03.txt) |
| `npm ci --prefix frontend` | Instalación desde lockfile correcta | [gate 04](gates-r2/gate-04.txt) |
| `npm test --prefix frontend -- --run` | 20 passed | [gate 05](gates-r2/gate-05.txt) |
| `npm run build --prefix frontend` | Build correcto | [gate 06](gates-r2/gate-06.txt) |
| `npm audit --prefix frontend` | 0 vulnerabilidades | [gate 07](gates-r2/gate-07.txt) |
| `python scripts/validate_original_promise.py --check` | OK, 0.758985 | [gate 08](gates-r2/gate-08.txt) |
| `./scripts/preflight_demo.sh` | LISTO PARA DEMO | [gate 09](gates-r2/gate-09.txt) |
| `./scripts/preflight_genai.sh` | OLLAMA READY, respuesta real validada | [gate 10](gates-r2/gate-10.txt) |

El skip corresponde a `kubectl` opcional. npm ci advirtió sobre la política local allowScripts de fsevents; no hubo fallo ni vulnerabilidad reportada. No se instalaron dependencias nuevas. El editor no reportó errores en los módulos nuevos/modificados revisados; el análisis completo también mostraba avisos informativos de símbolos no usados, que no se eliminaron como limpieza ajena.

La cobertura incluye Health/Delay/Cost/Final Status, Team Health, What-if, CSV, API, frontend, recomendaciones y fallback. Los casos adversos sin drivers, sanos, insuficientes, cifras inventadas, procedencia falsa, errores de servicio, seguimiento y resumen único tienen pruebas. No se confunden mocks con las corridas reales enlazadas.

**Eficiencia computacional:** [corrida independiente](efficiency/operational_benchmark.md), 80 runs normales en N=1/10/25/50/100, mismos proyectos por modo, warm-up excluido y GenAI apagada. Para N=100: 3029.484 ms individual frente a 2863.875 ms batch, reducción 5.4666%. N=1 fue ligeramente más lento en batch. No hay paralelización ni ahorro humano inferido.

**Robustez operacional:** [5/5 checks de entrada](efficiency/robustness_checks.json). [Siete comprobaciones adicionales](robustness-evidence-v2.json) pasaron: respuestas reales revalidadas, fallback offline, recuperación real, predicción idéntica antes/después del fallo, rechazos de entrada, 12 solicitudes ML concurrentes consistentes y degradación GenAI segura. En dos llamadas Qwen concurrentes, una aceptó a 16685.81 ms y otra usó fallback por timeout a 30002.52 ms. Es una prueba acotada, no estimación de capacidad. `/api/ps` registra tamaño cargado reportado por Ollama, no pico RAM medido independientemente.

**Productividad humana: NO MEDIDA.** [Protocolo](../../docs/human_efficiency_validation.md) con consentimiento, contrabalanceo, rúbrica 0–10 ciega y análisis pareado por participante. La [plantilla](../human_validation/TEMPLATE_results.csv) mantiene solo encabezados. No hay participantes, encuestas ni datos laborales inventados.

**Despliegue:** Docker cliente instalado, daemon inaccesible; build y smoke de contenedor NO EJECUTADOS. Kubernetes solo tiene YAML y pruebas estáticas; no se operó clúster. Con Docker autorizado y disponible: construir `docker build -f Dockerfile.playground -t prunin-ai-core:0.9.0-academic .`, iniciar localmente con `PRUNIN_ENABLE_OLLAMA=0`, mapear un puerto libre y comprobar `/api/ready`, `/api/health`, `/`, `/assets` y predicción con fallback. El dominio example y los recursos de Kubernetes requieren configuración/aprobación reales; no aplicar a infraestructura externa automáticamente.

**Comparación LLM:** Qwen Q4_K_M disponible; Gemma y Ministral ausentes. Manifiestos públicos sin blobs descargados: Gemma 3 4B 3,350,272,259 bytes; Ministral 3 8B 6,022,236,102 bytes. Equipo: 24 GiB RAM, aproximadamente 519 GiB libres. Eso permite planear almacenamiento, no certificar memoria efectiva de inferencia. Tag corregido: `ministral-3:8b`; el antiguo `ministral:8b` respondió 404. La comparación completa requiere autorización de descarga y la misma cohorte/configuración para todos, incluido Qwen de nuevo con evidence-v2. No existe ganador empírico.

## D. Integridad científica

[Antes](integrity_before.json) y [después](integrity_after.json): 5.406 archivos protegidos comprobados, ninguno cambiado; tres predicciones de presets idénticas. Coinciden los SHA256 originales del CSV procesado y los tres raw Mendeley registrados en reproducibility. TRAIN/VALIDATION/TEST disjuntos: 2800/600/600. Los tres `.joblib`, targets, inferencia ML, `local_drivers`, configuración/seed/umbrales científicos y reportes oficiales permanecen intactos. Se comprobó además cero diff Git en métricas, promesa, eficiencia histórica y benchmarks GenAI oficiales/históricos.

| Evidencia oficial conservada | Resultado |
|---|---|
| Dataset | 4.000 proyectos, 72.549 snapshots sintéticos externos |
| Risk Alert al 60 % | 359/473 = 75.90 %, cobertura 576/600 = 96 % |
| Critical Recall exacto | 25/44 = 56.82 % |
| Health Macro F1 | 0.627576 |
| Delay MAE / baseline | 27.710468 / 27.850313 días; mejora marginal |
| Cost MAE / R² | 0.147158 puntos porcentuales / 0.991816; caveat estructural EVM |
| Qwen oficial | 30 casos, 29 aceptadas, una cifra no soportada |

No se utilizó TEST para seleccionar modelos, hiperparámetros ni estos triggers operacionales. El benchmark técnico usa snapshots TEST congelados sin targets como inputs; los casos de desarrollo no sustituyen métricas oficiales. No se reentrenó LightGBM ni se activó reentrenamiento automático. El cambio está en interpretación, evidencia, recomendaciones, presentación y controles operativos/documentales.

### Riesgos introducidos o residuales

- Reglas operativas no calibradas: pueden requerir adaptación a líneas base y denominadores reales; su procedencia y tolerancias son explícitas.
- Contexto y 1200 tokens aumentan latencia y presión bajo concurrencia; el timeout/fallback permanece y la degradación se observó.
- Suprimir correcciones por sensibilidad aislada en Health healthy no garantiza ausencia de riesgo ni sustituye revisión humana.
- Los patrones de contradicción y groundedness no detectan todo error semántico ni prueban utilidad profesional.
- Docker no-root/healthcheck solo se validaron estáticamente; necesitan build y smoke antes de operar.

## E. Intervención humana y externa pendiente

1. Obtener la rúbrica oficial y contrastar literalidad, pesos y máximo exigido de las 27 filas; confirmar formato, autor, portada y fechas institucionales.
2. Autorizar, instalar y comparar Gemma/Ministral si se desea cerrar selección empírica; no se descargaron automáticamente.
3. Aprobar ética/consentimiento, reclutar participantes reales y ejecutar el protocolo antes de declarar productividad o utilidad.
4. Obtener datos empresariales aprobados y outcomes para validación prospectiva; los resultados actuales son sintéticos.
5. Habilitar Docker local y ejecutar build/smoke; cluster/cloud, carga sostenida y observabilidad central requieren autorización y recursos.
6. Ejecutar sustentación/ensayo real. Las versiones locales 7/10/12 min suman 420/600/720 s planificados; no se midieron en voz alta ni se asume duración oficial. Probar proyector, red, fallback y copia offline. Explicar objetivo/KPI, arquitectura, resultados, límites y conclusión; abrir primero informe/gráficas y después demo/evidencia técnica si se solicita. Preparación no acredita voz, lenguaje no verbal o defensa espontánea.
7. Revisar renders, referencias externas y materiales personales antes de entregar; su evidencia V3 histórica no debe presentarse como evaluación del contrato v2 actual.

## F. Repositorio y revisión local

No se realizó commit, push, cambio de rama ni reescritura de historial. `main` conserva HEAD `bdc6f61c44e040c3c8ef694970c7252d8ec625bf`; los cambios son locales. El [CI 42492682508](https://github.com/heiandavi-boop/tallerfina3/actions/runs/42492682508) está completed/success para ese HEAD base exacto. **No acredita este diff sin commit/publicación.** La configuración actual se validó estáticamente y los gates locales pasaron; Node 22 del CI no se ejecutó localmente.

El staging anterior se preservó: modificación de `.gitignore`, edición previa de README y retirada del checklist del índice. Las modificaciones nuevas de README coexisten sin sustituir el staged previo. No se stagearon automáticamente los cambios nuevos ni se reintrodujeron archivos ignorados.

| Grupo | Archivos modificados |
|---|---|
| Backend | `src/prunin_ai/api/recommendations.py`, `src/prunin_ai/api/monitoring.py` |
| Frontend | `frontend/src/components/AnalysisPanels.jsx`, `frontend/src/Experience.jsx`, `frontend/src/App.test.jsx`, `frontend/dist/index.html` |
| Benchmarks | `scripts/evaluate_genai.py`, `scripts/genai_benchmark_common.py`, `scripts/benchmark_genai_candidates.py`, `scripts/benchmark_genai_concurrency.py` |
| Tests | `tests/test_genai_grounding.py`, `tests/test_genai_benchmarking.py`, `tests/test_deployment_manifests.py`, `tests/test_evaluation_reporting.py` |
| Despliegue/CI | `Dockerfile.playground`, `.dockerignore`, `.github/workflows/quality.yml` |
| Documentación | `README.md`, `docs/INFORME_FINAL.md`, `docs/architecture.md`, `docs/playground.md`, `docs/genai_evaluation.md`, `docs/genai_model_selection.md`, `docs/human_efficiency_validation.md`, `docs/mlops_production.md`, `docs/rubric_matrix.md` |

Nuevos: `src/prunin_ai/api/operational_signals.py`, `configs/operational_signals.yaml`, `scripts/audit_closure.py`, este directorio de evidencia y `frontend/dist/assets/index-BEZ9mCx3.js`. El bundle anterior `index-BMutMG7X.js` se conserva físicamente y sin cambios; Vite lo retiró al construir y se restauró solo ese archivo generado. No se eliminan documentos locales.

**Exclusiones reales:** `docs/ENTREGA_FINAL_CHECKLIST.md` existe localmente, está ignorado y no rastreado en el índice. Preguntas, glosario, presentación y FINAL_READINESS ya estaban rastreados al comenzar; tienen dependencias documentales y se preservaron sin editar ni cambiar su seguimiento. No se afirma que estén ignorados. La discrepancia frente a la solicitud se informó; cualquier cambio posterior de seguimiento necesita revisión explícita. Dataset pesado, modelos, `.env`, caches y logs excluidos siguen fuera de la incorporación automática. El escaneo de secretos fue limitado y no sustituye revisión de privacidad de los logs locales antes de publicar.

Para revisar sin publicar:

```bash
git status --short --branch
git diff --stat
git diff
git diff --cached
git diff --check
git diff --cached --check
```

Después de revisión humana, stagear solo rutas aprobadas (`git add -- <RUTAS_REVISADAS>`), nunca `git add .` indiscriminado. No se proporciona ni ejecuta push automático. La publicación y CI de un commit nuevo quedan pendientes de autorización.

La versión corregida queda disponible en **http://127.0.0.1:8001/** con Qwen habilitado; la instancia del usuario en el puerto 8000 no se detuvo. La API temporal sin LLM del benchmark en 8002 se detuvo al terminar.

**Conclusión:** motor de recomendaciones corregido y verificado localmente; evidencia científica preservada; 27 criterios internos auditados con límites explícitos. No hay fundamento para fabricar un 100 %, una calificación oficial ni capacidades productivas/humanas aún no demostradas.