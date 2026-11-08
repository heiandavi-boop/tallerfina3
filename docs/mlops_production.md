# Despliegue, escalabilidad y MLOps

## Estado implementado

La versión académica incluye:

- artefactos versionados por directorio;
- SHA256 de datos;
- split manifest;
- configuración de entrenamiento resuelta y model card;
- workflow CI en GitHub Actions (resultado por commit en FINAL_READINESS.md);
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

No existe todavía validación productiva, almacenamiento central de métricas, alertas reales, drift continuo/productivo ni retraining continuo con datos PRUNIN. Hay un detector académico offline y un aviso de entrada OOD basado en TRAIN; no es una monitorización central. Por integridad académica, no se presenta como operación ya desplegada.

## Separación entre implementación y operación pendiente

Implementado: hashes/manifests, logging con prediction_id, endpoints y métricas locales, política documentada de retraining, empaquetado Docker y CI. No significa que exista retraining continuo en producción.

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

El Dockerfile ahora declara usuario 10001 y healthcheck HTTP de readiness; `.dockerignore` excluye `.git`, documentos y reportes del contexto. Las pruebas estáticas pasaron, pero el daemon Docker no estuvo disponible: estos cambios aún requieren build y smoke reales. Kubernetes permanece sin operar.
