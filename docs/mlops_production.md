# Despliegue, escalabilidad y MLOps

## Estado implementado

La versión académica incluye:

- artefactos versionados por directorio;
- SHA256 de datos;
- split manifest;
- configuración de entrenamiento resuelta y model card;
- workflow CI en GitHub Actions; cada ejecución debe comprobarse para el SHA exacto en la pestaña Actions (véase `docs/ESTADO_VERIFICACION_ENTREGA.md`);
- `/api/health` y `/api/ready`;
- `/api/monitoring`;
- `/metrics` scrapeable en formato Prometheus;
- logs estructurados por `prediction_id`;
- Dockerfile reproducible;
- fallback ante falla GenAI;
- pipeline `train_all.sh` fail-fast.
- perfil de calidad/OOD calculado solo con proyectos TRAIN y fingerprints;
- detector offline de PSI y missing-rate con CLI y pruebas sintéticas.

## Diseño escalable reproducible

`deploy/k8s/prunin-ai-core.yaml` define:

- 3 réplicas;
- Service como balanceador interno;
- readiness y liveness probes;
- rolling updates;
- límites/requests de CPU y memoria;
- HorizontalPodAutoscaler;
- PodDisruptionBudget con al menos dos pods disponibles;
- ejecución no-root, filesystem raíz de solo lectura y `/tmp` temporal limitado;
- cierre graceful del proceso Uvicorn.
- reinicio automático administrado por Kubernetes.

El manifiesto es **evidencia de diseño y automatización**, no evidencia de que exista un clúster productivo activo. Su sintaxis/contratos se validan en tests estáticos; este cierre no usó `kubectl` ni operó un cluster. La descripción exacta es: “deployment automation/design validated statically; production cluster not operated.”

## Monitorización

Los contadores runtime permiten observar:

- predicciones exitosas;
- fallas de inferencia;
- intentos GenAI;
- respuestas GenAI aceptadas;
- fallbacks;
- p95 aproximado de latencia;
- uptime.

Son métricas en memoria por proceso; para producción deben recolectarse centralmente con Prometheus/OpenTelemetry antes de escalar horizontalmente.

## Política de actualización/retraining

No se reentrena automáticamente solo porque exista un calendario. Se debe reentrenar cuando:

1. cambia el fingerprint del dataset aprobado;
2. aparece un volumen suficiente de proyectos reales con outcomes;
3. un monitor externo confirma drift o degradación;
4. el nuevo candidato mejora en validation según criterios predefinidos.

TEST permanece reservado para evaluación final después de congelar la selección.

## Limitación actual

No existe validación productiva, almacenamiento central de métricas, alertas centralizadas, drift continuo/productivo ni retraining continuo con datos PRUNIN. Se añadió una CLI offline que genera reportes fechados con PSI, missing rate, validación de esquema y hashes, y permite devolver un código de alerta para integrarla con un scheduler autorizado. No implica monitorización central ni ejecución programada en este cierre.

## Separación entre implementación y operación pendiente

Implementado: hashes/manifests, logging con prediction_id, endpoints y métricas locales, monitor offline invocable por CLI, registro local de modelos, política y pipeline de retraining bloqueado, empaquetado Docker y CI. El CI de `main` construyó la imagen demo y ejecutó el smoke test; Docker no se pudo ejecutar en este equipo porque no había daemon. No significa que exista retraining continuo en producción.

Diseñado/pendiente: Prometheus centralizado, alertas reales, drift automático productivo, retraining continuo, infraestructura cloud y Kubernetes real. El HPA 3–10 requiere metrics-server; debe probarse carga y capacidad antes de operar. El Dockerfile requiere artefactos locales dentro del contexto; un clon solo con reportes no incluye los modelos pesados. No se construyó la imagen ni se desplegó un clúster durante este cierre.

## Interpretación frente a Nivel 4

La integración de scripts, CI, logging y métricas locales es evidencia académica. Kubernetes cubre orquestación de despliegue a nivel de diseño, no ejecución probada; no existe Airflow/Kubeflow. Escalado, balanceo y recuperación automática solo están especificados en YAML, sin prueba de fallos/carga. El fallback GenAI y timeout sí están implementados localmente.

R7.2 Cr6 no alcanza retraining continuo real: la política documentada no equivale a un servicio de reentrenamiento. Requiere outcomes suficientes/aprobados y drift/degradación o cambio de dataset revisado; comparar el candidato en VALIDATION y preservar TEST congelado. No se reentrena por mejorar una cifra ni por calendario sin causa. Ver rubric_matrix.md para gaps de cada criterio.

## Promoción y rollback manuales

Procedimiento diseñado, no ejecutado como operación productiva en esta auditoría:

1. Abrir una revisión con causa verificable: datos/outcomes nuevos aprobados, drift investigado o degradación medida. Confirmar consentimiento, licencia, unidades y ausencia de leakage.
2. Crear versión y carpeta nuevas; nunca reutilizar `0.9.0-academic`, su dataset o TEST. Registrar fingerprint, manifiesto de split, código, dependencias, seed y configuración antes de entrenar.
3. Ajustar candidatos solo en TRAIN y seleccionar con VALIDATION según métricas y tolerancias definidas antes. Evaluar sesgos, OOD, rendimiento, seguridad y regresión del contrato. No inspeccionar TEST para elegir hiperparámetros o reglas.
4. Congelar el candidato y evaluar una sola vez en el holdout aprobado para ese estudio. Si falla, no ajustar repetidamente sobre ese holdout: revisar el diseño y obtener nueva evaluación independiente. Conservar también resultados desfavorables.
5. Una persona responsable aprueba explícitamente la promoción y sus límites. Desplegar primero en entorno aislado con fixtures, `/api/ready`, `/api/health`, predicción, CSV, What-if y fallback sin Ollama. Identificar imagen por digest y artefacto por hash, no solo por tag mutable.
6. Cambiar `PRUNIN_ARTIFACT_DIR` a la versión aprobada mediante configuración revisada; no sobrescribir modelos. Registrar aprobación, hashes, configuración y fecha. Antes de tráfico real, disponer de métricas centralizadas y criterios de rollback.
7. Ante fallo, restaurar la referencia de configuración a la versión previa aprobada, verificar readiness y smoke tests, registrar incidente y conservar ambos artefactos. No eliminar datos ni resultados para hacer rollback.

Los logs actuales registran identificador, versión, tiempos, motor y código de fallo, no el texto libre del proyecto. Los contadores son por proceso; no hay trazabilidad persistente empresarial ni coordinación multiworker. El escaneo de patrones de secretos es limitado y no sustituye revisión de seguridad. Las nuevas causas de rechazo de procedencia, contradicción y seguimiento se contabilizan como validación fallida, no como éxito GenAI.

El Dockerfile ahora declara usuario 10001 y healthcheck HTTP de readiness; `.dockerignore` excluye `.git`, documentos y reportes del contexto. El CI de `main` construyó y ejecutó el smoke test del contenedor con artefactos demo sintéticos. En esta auditoría el CLI Docker está instalado, pero no hay daemon local (`/var/run/docker.sock` ausente); Kubernetes permanece sin contexto configurado ni operación real.


## Verificación adicional del empaquetado para el nivel 4 de PAIII

El workflow `quality` contiene el paso `bash scripts/container_smoke.sh`, ejecutado sobre artefactos **demo sintéticos** producidos por `scripts/run_demo.sh`. El script construye la imagen a partir del Dockerfile, inicia un contenedor temporal sin credenciales de inferencia externa, comprueba `/api/ready`, `/api/genai-providers` y `/metrics` y elimina el contenedor.

El resultado constituye evidencia reproducible de **construcción y arranque de Docker**, solo cuando el job del commit relevante termine en `success`. No es una prueba de balanceo Kubernetes, HPA ni actualización de modelos. La evaluación de nivel 4 para R7.2-Cr4/Cr6 sigue sujeta a ejecución y monitorización completas en un entorno autorizado. No usar expresiones como “clúster operado” ni “retraining continuo” sin evidencias.

## Auditoría del registro local (noviembre de 2026)

La auditoría identificó y corrigió dos ambigüedades en el esquema inicial:

1. Los valores anteriormente registrados para Health, Delay y Cost eran métricas por snapshot, mientras que los indicadores destacados en el informe eran métricas por último snapshot del proyecto. El esquema 2 registra ambas unidades y su fuente (`reports/0.9.0-academic/metrics.json`): row-level Macro-F1 0.547055, Delay MAE 32.175956 días y Cost R² 0.829707; project-level Macro-F1 0.627576, Delay MAE 27.710468 días y Cost R² 0.991816. No se modificó ningún resultado académico.
2. Se eliminó una atribución de aprobación al “comité académico PAIII” sin evidencia documental. `frozen_academic` describe preservación técnica, no una aprobación institucional. `demo-0.1.0` cambió de `production` a `demo_available`; los punteros `test` y `production` están vacíos. `select-for-deployment` cambia una selección del registro, no despliega ni verifica un servicio. `rollback-selection` tampoco equivale a rollback de un despliegue.

El monitor se ejecutó sobre los 600 proyectos y 10.880 snapshots de VALIDATION frente a la referencia TRAIN: sin alerta PSI/missing ni columnas faltantes. La ejecución quedó en `reports/technical_closure/drift_monitoring_2026/`; no activó reentrenamiento. Es una comparación retrospectiva entre particiones, no observabilidad continua.

## Registro de modelos y ciclo de reentrenamiento controlado (noviembre de 2026)

Implementado en `src/prunin_ai/monitoring/mlops.py` y `scripts/mlops_pipeline.py`, con pruebas en `tests/test_mlops_pipeline.py`:

- **Registro versionado** ([model_registry.json](../reports/mlops/model_registry.json)). Por versión guarda dataset y hash, configuración, métricas, estado, aprobación, versión padre, hashes de artefactos y un log de eventos. `0.9.0-academic` está en estado `frozen_academic` y no puede sobrescribirse.
- **Reentrenamiento bloqueado por defecto.** Requiere `--authorize` y un archivo de procedencia con `authorized: true` y SHA-256 coincidente, y rechaza el dataset académico Mendeley.
- **Ejecución del candidato.** Registra un trigger de drift (PSI y missing rate), entrena en `artifacts/candidates/` (ignorado por git) y compara candidato y baseline solo sobre VALIDATION.
- **Gate de regresión (2 % relativo), aprobación humana, selección de release y rollback de selección**, cada uno registrado como evento. Son transiciones del registro, no despliegue ni rollback de un servicio.

**Ejecución real:** con datos sintéticos de seed 2026, el candidato `demo-candidate-2026` quedó en `rejected_regression`, porque el macro-F1 de Health bajó un 13,6 %, aunque Delay y Cost mejoraron. El registro actual mantiene vacíos los punteros `test` y `production`; `demo-0.1.0` está etiquetada `demo_available`, no como despliegue. Detalle en [reports/mlops/README.md](../reports/mlops/README.md).

**Límite:** es una demostración local del ciclo, no un reentrenamiento continuo programado. El drift conceptual y la pérdida de desempeño requieren ground truth real, que hoy no existe.

## Validación de despliegue en este cierre

- Docker CLI está instalada, pero no había daemon local disponible. La construcción y el smoke test del contenedor se verificaron en el job `quality` de GitHub Actions para el commit correspondiente.
- No existe un clúster Kubernetes local (no hay kind, minikube ni contexto de kubectl). El manifiesto se valida estáticamente con `tests/test_deployment_manifests.py`; la prueba con `kubectl` se omite si no hay clúster.
- No se probaron balanceo, caída de pods ni rollback en un clúster.

## Comprobación de drift recurrente en CI (demostración sintética)

El workflow [scheduled-demo-drift.yml](../.github/workflows/scheduled-demo-drift.yml) programa una comprobación semanal y permite ejecutarla manualmente. Genera la demo mediante `scripts/run_demo.sh`, crea un perfil con `scripts/check_drift.py`, calcula la comparación del lote de demostración y archiva los resultados como artefacto GitHub Actions de duración limitada. Se ejecuta con permisos de lectura sobre el repositorio y **no** llama al pipeline de reentrenamiento.

**Límite científico:** al comparar el dataset demo contra sí mismo, esta comprobación valida la *automatización del instrumento y el registro de evidencia*, no la detección de drift en producción, ni la llegada de datos nuevos, ni el retraining continuo real. Es necesario incorporar una fuente de lotes nuevos autorizados, historial persistente de alertas y revisión humana del gate antes de afirmar operación continua. La primera ejecución programada solo se acredita cuando exista una corrida del workflow con resultado satisfactorio.

## Prueba de balanceo y continuidad con dos contenedores Docker

El script [docker_two_replica_failover.sh](../scripts/docker_two_replica_failover.sh) monta dos instancias de demostración de FastAPI detrás de nginx sobre una red temporal Docker. Solicita cuarenta respuestas para comprobar tráfico en ambos backends, detiene uno, verifica veinte solicitudes a través del balanceador y posteriormente restaura manualmente el contenedor. La prueba está incorporada en el workflow `quality` después del smoke test de imagen, de modo que su resultado puede auditarse en las ejecuciones de CI.

**Ámbito preciso:** es una prueba de balanceo y tolerancia básica a la caída de una instancia en Docker, **no Kubernetes**, no autoescalado, no recuperación automática y no disponibilidad productiva. Su resultado solo podrá declararse exitoso cuando GitHub Actions lo haya ejecutado y registrado. Se mantienen pendientes las pruebas de HPA, actualización y recuperación automática en un clúster autorizado.

## Evidencia operativa adicional posterior al cierre inicial

La demostración de dos instancias de FastAPI con balanceador nginx se ejecuta con `scripts/docker_two_replica_failover.sh` dentro de [quality](../.github/workflows/quality.yml). La ejecución de [main dfdae707](https://github.com/heiandavi-boop/tallerfina3/actions/runs/44454392965) validó reparto de tráfico 20/20, continuidad al detener una réplica y restauración **manual** de la réplica detenida. No se activó un clúster Kubernetes y no se demostró autorrecuperación del orquestador. Esta evidencia mejora el diseño de robustez R7.2-Cr5, pero no convierte la solución en producción resiliente.

El workflow [scheduled-demo-drift.yml](../.github/workflows/scheduled-demo-drift.yml) tiene una programación semanal y ejecución manual para crear datos demo, perfilar y comparar el conjunto sintético, y archivar el resultado. El CI [quality](../.github/workflows/quality.yml) verificó el diagnóstico de datos demo. **No hay prueba de funcionamiento sostenido del calendario semanal sobre datos cambiantes**, ni ingestión de outcomes, drift productivo o actualización periódica de LightGBM. El reentrenamiento sigue sujeto a gate y aprobación humana, no a automatismos que puedan modificar el artefacto académico congelado.

Las secciones anteriores describen las limitaciones del cierre técnico original. Esta adenda consigna verificaciones posteriores sin reescribir la historia experimental.
