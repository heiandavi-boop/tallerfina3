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

## Diseño escalable reproducible

`deploy/k8s/prunin-ai-core.yaml` define:

- 3 réplicas;
- Service como balanceador interno;
- readiness y liveness probes;
- rolling updates;
- límites/requests de CPU y memoria;
- HorizontalPodAutoscaler;
- reinicio automático administrado por Kubernetes.

El manifiesto es **evidencia de diseño y automatización**, no evidencia de que exista un clúster productivo activo.

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

No existe todavía validación productiva, almacenamiento central de métricas, alertas reales ni retraining continuo con datos PRUNIN. Por integridad académica, esas capacidades se presentan como siguiente paso y no como operación ya desplegada.

## Separación entre implementación y operación pendiente

Implementado: hashes/manifests, logging con prediction_id, endpoints y métricas locales, política documentada de retraining, empaquetado Docker y CI. No significa que exista retraining continuo en producción.

Diseñado/pendiente: Prometheus centralizado, alertas reales, drift automático productivo, retraining continuo, infraestructura cloud y Kubernetes real. El HPA 3–10 requiere metrics-server; debe probarse carga y capacidad antes de operar. El Dockerfile requiere artefactos locales dentro del contexto; un clon solo con reportes no incluye los modelos pesados. No se construyó la imagen ni se desplegó un clúster durante este cierre.
