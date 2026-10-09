# Despliegue, escalabilidad y MLOps

## Estado implementado

La versión académica incluye:

- artefactos versionados por directorio;
- SHA256 de datos;
- split manifest;
- configuración de entrenamiento resuelta;
- CI en GitHub Actions;
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
