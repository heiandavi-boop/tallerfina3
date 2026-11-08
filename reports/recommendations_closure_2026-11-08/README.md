# Cierre verificable de las cuatro brechas de recomendaciones

**Nota de publicación:** las menciones a cambios locales sin commit/push describen esta verificación previa a la publicación autorizada. Las rutas personales de los logs públicos se sustituyeron por `.` y `~`, conservando los originales en `reports/closure/` fuera de Git; los resultados y el JSON bancario descargado no se alteraron.

Fecha: 8 de noviembre de 2026. HEAD de referencia: `bdc6f61c44e040c3c8ef694970c7252d8ec625bf`. Cambios locales, sin commit ni push. Este reporte no sustituye métricas académicas ni evaluaciones GenAI históricas.

## 1. Diagnóstico de causa raíz

El código publicado en main solo autorizaba drivers `increases_risk`. El caso bancario IT/híbrido produce únicamente SPI como driver reductor; por tanto, el contrato antiguo obligaba al generador a responder sin acciones aunque hubiera desviaciones operativas. La ausencia de sensibilidad positiva no significa ausencia de problemas observados. Además, `RecommendationCard` renderizaba el resumen tanto antes de la lista como en la rama vacía.

Las cuatro correcciones ya estaban presentes en el árbol local al recibir esta solicitud; se verificaron y se completó el E2E CSV/descarga que faltaba. Se encontraron y reprodujeron dos debilidades adicionales del validador contextual: aceptaba SPI 0.74 cuando el dato era 0.72 por una tolerancia del 3 %, y aceptaba describir como favorable un SPI adverso. Las regresiones fallaron antes del refuerzo y pasaron después.

## 2. Arquitectura y correcciones

| Fuente | Contrato | Uso y límites |
|---|---|---|
| Sensibilidad predictiva | `model_driver` | Perturbaciones locales del modelo, sin causalidad; drivers reductores preservados como contexto |
| Señal operacional | `observed_operational_signal` | Entrada validada y trigger heurístico configurable; el valor se coteja con la entrada original |
| Indicador determinístico | `heuristic_indicator` | Team Health con componentes/cobertura suficientes, no un modelo supervisado |

Las parejas `evidence_feature`/`evidence_source` referencian los valores exactos de `evidence_context`. No se duplican valores inventados dentro de cada acción. El prompt conserva predicciones y las tres procedencias, limita la evidencia autorizada y exige prioridad, título, razón, acción concreta y seguimiento. Hay al menos una acción si existen señales accionables; se separan seguimiento normal, señales prioritarias, datos insuficientes y fallo del servicio. El fallback consume las mismas señales, elimina duplicados por feature y expone su validación independiente.

Reglas: [configuración operacional](../../configs/operational_signals.yaml). SPI/CPI <1 son desfavorables en EVM, con tolerancia heurística de revisión <0.95. Los demás cortes son criterios heurísticos no calibrados, no estándares empresariales ni probabilidades predictivas. Faltantes, no finitos y valores fuera de rango no sustentan acciones. No se usó TEST para fijar estos criterios. [Implementación operacional](../../src/prunin_ai/api/operational_signals.py).

Grounding contextual reforzado: solo admite cifras exactas o redondeadas a la precisión escrita; rechaza valores cercanos arbitrarios, porcentajes con unidades incorrectas y atribuir el valor de CPI a SPI. Comprueba también interpretaciones favorables explícitamente contradictorias con señales adversas. El contrato histórico sin contexto mantiene compatibilidad; los reportes históricos no se revalidan ni sobrescriben como si fueran una nueva corrida. [Validador](../../src/prunin_ai/api/recommendations.py).

Las comprobaciones de contradicción son patrones determinísticos, no comprensión semántica universal. Persisten revisión humana, incertidumbre del modelo y límites de datos sintéticos. Ningún guardrail garantiza verdad o utilidad profesional.

## 3. Tabla final de brechas

Estado inicial referido a main publicado, no a que se hubiera eliminado el trabajo local previo.

| Brecha | Estado inicial | Corrección aplicada | Prueba | Estado final |
|---|---|---|---|---|
| Evaluación operacional | Abierta: dependía de drivers positivos | Evaluador independiente, configuración y procedencia; faltantes/rangos/tolerancias explícitos | SPI/CPI, utilización/capacidad por separado, calidad, mezcla y ausencia de drivers; CSV real | Corregida y verificada localmente |
| Contexto para Qwen | Abierta: descartaba evidencia operacional | Predicciones, drivers completos, señales e indicadores tipados, allow-list por caso | Qwen real desde fila CSV sin drivers positivos; evidencia guardada | Corregida y verificada localmente |
| Validador de evidencia | Abierta: solo drivers, sin procedencia operacional | Parejas autorizadas, seguimiento, deduplicación, redondeo exacto y contradicciones explícitas; fallback con mismas fuentes | Valores/cifras inventados, evidencia inexistente, procedencia falsa, timeout/error, casos mixtos y unidades | Corregida y reforzada; límites semánticos explícitos |
| Duplicación React | Abierta: resumen dos veces si lista vacía | Una sola rama de resumen; prioridades y procedencias; motor real diferenciado | Vitest de resumen único, CSV/descarga; E2E Chrome Qwen y fallback | Corregida y verificada localmente |

## 4. Caso bancario de extremo a extremo

CSV reproducible: [banking_recommendations.csv](../../tests/fixtures/banking_recommendations.csv). Los doce valores principales son exactamente los suministrados. Campos restantes compatibles: banking, IT, hybrid, complejidad/criticidad high, alcance base 1500, estabilidad 0.76, colaboración 0.68, crecimiento de alcance 0.09 y gobierno 0.56; provienen del escenario existente, sin presentarlos como observaciones empresariales reales.

Secuencia ejecutada en Chrome independiente, sin mock del LLM:

1. Cargar el CSV y pulsar Analizar archivo. HTTP 200; una fila válida, siete features ML completas, recomendaciones `not_requested`, `genai_attempted=false`, `genai_ms=null` y cero requests individuales.
2. Abrir Ver análisis completo. Un solo POST individual, exactamente la misma entrada y predicciones que el lote.
3. Evaluar señales independientes y construir contexto, incluso con cero drivers positivos.
4. Ejecutar Qwen3 8B vía Ollama, validar respuesta y renderizar cuatro acciones con prioridad/procedencia y resumen único.
5. Abrir evidencia técnica y Descargar resultados. Evento de descarga real y archivo JSON guardado, idéntico campo por campo a la respuesta individual.

Evidencia real completa: [reporte E2E](browser-e2e/browser-report.json), [respuesta CSV](browser-e2e/batch-response.json), [respuesta individual](browser-e2e/individual-response.json), [JSON descargado](browser-e2e/technical-download.json), [captura desktop](browser-e2e/desktop.png) y [captura móvil](browser-e2e/mobile.png). Las capturas de elemento largo pueden incluir la cabecera sticky durante el stitching; no son una auditoría de usabilidad. El test mide además ausencia de overflow horizontal y por tarjeta en 390 px.

| Resultado real | Valor |
|---|---:|
| Prediction ID | 5dc4c7f2-de51-4bee-a1a8-b346565f3d5f |
| Health | at_risk |
| Delay | 69.6617489754 días |
| Cost | ratio 0.1327694682, equivalente a 13.27694682 % estimado |
| Final Status | challenged |
| Team Health heurístico | 0.522667, attention, siete componentes |
| Riesgo combinado heurístico, no probabilidad calibrada | 0.5193860269 |
| Driver calculado | SPI=0.72, referencia 1, impacto -0.0183, reduces_risk |
| Drivers positivos | 0 |
| Motor | ollama:qwen3:8b |
| Latencia GenAI | 12820.21 ms |
| Validación | schema, evidencia, procedencia, acción y seguimiento válidos; sin cifras no soportadas |

Se detectaron diez señales operativas: SPI 0.72; CPI 0.81; utilización 1.12; capacidad 0.72; productividad 0.68; retrabajo 0.19; defectos 0.11; dependencias 15 días; exposición 0.49; gobierno 0.56. Alcance 0.09 no activó el trigger. Team Health se mantuvo como indicador heurístico separado. Los valores bancarios OOD de presupuesto y SPI emiten advertencia; no se alteran las predicciones para adecuarlas a la expectativa.

### Recomendaciones reales producidas

Todas tuvieron prioridad alta y `observed_operational_signal`:

| Evidencia | Acción real | Seguimiento real |
|---|---|---|
| CPI 0.81 | Analizar el consumo presupuestal y actualizar la estimación al cierre antes de asumir nuevos compromisos de gasto | Comparar CPI y proyección de costo en el siguiente seguimiento |
| SPI 0.72 | Revisar las actividades con mayor desviación frente al plan y definir un plan de recuperación para el siguiente seguimiento | Revisar SPI y cumplimiento del cronograma en el siguiente corte |
| Capacidad/demanda 0.72 | Contrastar los compromisos de trabajo con la capacidad disponible y acordar una priorización para el siguiente ciclo | Revisar capacidad disponible y trabajo comprometido en el siguiente corte |
| Utilización 1.12 | Revisar la carga asignada y acordar ajustes de prioridades antes de aceptar nuevos compromisos | Volver a revisar utilización y capacidad del equipo en el próximo seguimiento |

No se predefinió una respuesta como ejecución real. Las razones y la salida cruda se conservan en el JSON descargado porque se habilitó debug temporal solo para este caso ficticio. Los servidores habituales volvieron a debug=0 al terminar.

### Fallo de servicio y navegador integrado

Se ejecutó el mismo CSV contra una API temporal con Ollama apuntando a un puerto local cerrado. No se detuvo el servicio Ollama del usuario. [Reporte fallback real](browser-fallback/browser-report.json) y [su JSON descargado](browser-fallback/technical-download.json): `grounded_fallback`, `ollama_unavailable`, GenAI intentada pero no usada, cuatro acciones con procedencia válida y `fallback_validation.grounded=true`. Entrada y predicciones idénticas a la ejecución con Qwen. La instancia temporal se detuvo al terminar.

El navegador integrado de VS Code no notificó el evento download ni produjo un archivo reciente detectable. Se probaron reversiblemente revocación diferida y enlace adjunto, sin resolver esa limitación. No se modificó el componente por una causa no confirmada. La descarga sí se demostró en Chrome independiente con su gestor real y comparación del archivo recibido; no se afirma que la descarga funcione en el navegador integrado de VS Code. Para descargar desde la demo, abrir la URL en Chrome externo.

## 5. Pruebas ejecutadas

Registro con comandos, timestamps, entorno, códigos y logs: [gates.json](gates.json). Entorno local Python 3.12.15, macOS arm64, Node 26.7.0. Chrome 157.0.8103.38 y playwright-core 1.65.0 para E2E; no se descargó navegador. playwright-core se instaló temporalmente fuera del repositorio, sin modificar package.json ni lockfile.

| Comando | Resultado | Evidencia |
|---|---|---|
| `python -m pip check` | Sin requisitos rotos | [log 01](gates/gate-01.txt) |
| `python -m compileall -q src scripts tests` | Código 0 | [log 02](gates/gate-02.txt) |
| `PYTHONPATH=src python -m pytest -q` | 174 passed, 1 skipped; 10.82 s | [log 03](gates/gate-03.txt) |
| `npm ci --prefix frontend` | Instalación reproducible correcta | [log 04](gates/gate-04.txt) |
| `npm test --prefix frontend -- --run` | 21 passed | [log 05](gates/gate-05.txt) |
| `npm run build --prefix frontend -- --emptyOutDir=false` | Build correcto; bundles anteriores conservados | [log 06](gates/gate-06.txt) |
| `npm audit --prefix frontend` | 0 vulnerabilidades | [log 07](gates/gate-07.txt) |
| `python scripts/validate_original_promise.py --check` | OK, 0.758985 | [log 08](gates/gate-08.txt) |
| `./scripts/preflight_demo.sh` | LISTO PARA DEMO | [log 09](gates/gate-09.txt) |
| `./scripts/preflight_genai.sh` | OLLAMA READY; respuesta real validada | [log 10](gates/gate-10.txt) |
| `test_banking_browser.mjs` con Qwen | Siete comprobaciones E2E pasaron, JSON descargado real | [Chrome/Qwen](browser-e2e/browser-report.json) |
| `test_banking_browser.mjs` con conexión fallida | Siete comprobaciones E2E pasaron, fallback y descarga reales | [Chrome/fallback](browser-fallback/browser-report.json) |

El skip corresponde a kubectl opcional, ajeno a las cuatro brechas. npm mantuvo un aviso local de allowScripts para fsevents, sin fallo del build. Los tests ordinarios desactivan Ollama; los mocks se distinguen de los E2E/preflight reales.

Antes de este refuerzo: 162 backend y 20 frontend aprobados en la auditoría previa. Después: 174 y 21, respectivamente. Se añadieron casos independientes de utilización/capacidad; valor cercano inventado y redondeo legítimo; contradicción favorable/desfavorable; falsa atribución CPI→SPI; redondeo porcentual; mezcla sin duplicados; cuatro entradas fuera de rango; dos flujos CSV bancarios con/sin drivers y lectura del JSON exportado. Los tests existentes cubren saludable, datos insuficientes, evidencia inexistente, prioridades, timeout, error de servicio y resumen único. La cobertura se amplió; esos conteos no son una métrica de calidad del modelo.

## 6. Archivos y reproducibilidad

Modificados en esta vuelta: [recommendations.py](../../src/prunin_ai/api/recommendations.py), [grounding tests](../../tests/test_genai_grounding.py), [API tests](../../tests/test_playground_api.py), [frontend tests](../../frontend/src/App.test.jsx), [registrador de gates](../../scripts/audit_closure.py) y documentación enlazada. Nuevos: el CSV de fixture, [test E2E](../../scripts/test_banking_browser.mjs) y este directorio. Se verificaron las implementaciones locales previas de `operational_signals.py`, su YAML, constructor de contexto, fallback y `AnalysisPanels.jsx`; no se borró ni reescribió trabajo existente.

Repetir manualmente: abrir http://localhost:8000 en Chrome, elegir Analizar varios proyectos, cargar el fixture, pulsar Analizar archivo, abrir Ver análisis completo, revisar las tarjetas y descargar resultados desde la evidencia técnica.

Repetir E2E automatizado, con Chrome ya instalado y servidor local activo:

```bash
TOOLS=$(mktemp -d /tmp/prunin-e2e.XXXXXX)
npm install --prefix "$TOOLS" --no-audit --no-fund --ignore-scripts playwright-core@1.65.0
PRUNIN_PLAYWRIGHT_MODULE="$TOOLS/node_modules/playwright-core" \
  node scripts/test_banking_browser.mjs http://127.0.0.1:8001 \
  reports/recommendations_closure_2026-11-08/browser-repeat-01
```

Elegir siempre una carpeta nueva: el test rechaza destinos existentes. `CHROME_EXECUTABLE` permite indicar un Chrome existente en otra ruta; no instala navegadores ni infraestructura. Para repetir el fallback, usar una API aislada con `PRUNIN_ENABLE_OLLAMA=1` y `PRUNIN_OLLAMA_URL=http://127.0.0.1:1/api/chat`, sin cambiar la configuración de los servidores normales ni apagar Ollama.

## 7. Integridad, estado y límites finales

[Instantánea inicial](integrity_before.json) y [comprobación final](integrity_after.json): 5.406 archivos protegidos idénticos, predicciones de referencia iguales, fingerprints originales coincidentes y split disjunto 2800/600/600. Los tres modelos `.joblib`, dataset, targets, `local_drivers`, seed, umbrales científicos, TEST, KPI 75 % y benchmarks oficiales no se modificaron ni reentrenaron. Los registros nuevos no sobrescriben resultados históricos.

Las cuatro brechas funcionales están cerradas dentro del alcance local probado. Permanece la limitación específica de descarga del navegador integrado; el procedimiento externo y la evidencia real están arriba. Persisten límites generales de heurísticas no calibradas, OOD, datos sintéticos y grounding semántico: las recomendaciones no son decisiones autónomas, causalidad ni validación empresarial. No se mide productividad humana.

Los servidores normales se dejaron disponibles en http://localhost:8000 y http://127.0.0.1:8001, con Qwen habilitado y debug desactivado; la API temporal de fallo en 8002 se detuvo. No se hizo commit, push ni cambio de historial. Se preservó el staging previo y los materiales locales excluidos. El CI remoto histórico no acredita los cambios locales sin publicar.