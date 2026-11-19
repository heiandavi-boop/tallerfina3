# Auditoría técnica de cierre

## Alcance

Este cierre continúa en `feat/technical-closure` desde `main` sin descartar archivos locales. Se revisaron las correcciones de seguridad, el presupuesto OpenAI, el benchmark de proveedores, la plantilla de productividad, MLOps y monitorización. La evidencia separa resultados académicos congelados, pruebas técnicas locales y dependencias externas no disponibles.

## Hallazgos y cambios verificados

- **Seguridad:** las rutas API protegidas fallan cerrado en producción cuando falta `PRUNIN_API_TOKEN`; health, readiness y métricas siguen disponibles para probes. El cliente no puede habilitar Ollama si el servidor tiene `PRUNIN_ENABLE_OLLAMA=0`. Las cuotas OpenAI existentes son por IP par/minuto y por proceso/día, no distribuidas.
- **Registro MLOps:** el esquema 2 separa métricas por snapshot y por proyecto, elimina una aprobación sin evidencia y representa `demo-0.1.0` como `demo_available`. Los punteros `test` y `production` están vacíos. La selección/rollback del registro no se presenta como despliegue de servicio.
- **Monitorización offline:** la comparación TRAIN frente a VALIDATION cubrió 600 proyectos y 10.880 snapshots; no reportó alertas PSI/missing ni columnas ausentes. No activó entrenamiento.
- **HTTP real:** el benchmark concurrente obtuvo 100/100 respuestas válidas en cada nivel 1/4/8/16. Throughput: 20.14/24.14/23.42/23.35 req/s; p95: 80.98/200.88/457.41/954.38 ms. El aumento de latencia y throughput plano no demuestra escalabilidad horizontal. La prueba de recuperación fue después de una entrada inválida, no de detener una instancia.
- **Proveedores:** el 19-11-2026, Qwen3 8B (`500a1f067a9f`, Q4_K_M) aceptó 30/30 casos tanto en modo controlado como operativo. OpenAI no se ejecutó porque `OPENAI_API_KEY` no estaba disponible en el proceso; se registraron cero llamadas y USD 0. El presupuesto experimental estimado era USD 5; no representa un tope de facturación garantizado.
- **Productividad humana:** NO MEDIDA; no se registraron participantes ni respuestas humanas.

## Validación automatizada

| Validación | Resultado |
|---|---|
| Pruebas focalizadas de seguridad, MLOps, drift y benchmark HTTP | 19 passed |
| Suite backend completa | 216 passed, 1 skipped |
| `pip check` | Sin dependencias rotas |
| `compileall` para `src`, `scripts` y `tests` | Correcto |
| Pruebas frontend | 22 passed |
| Build frontend | Correcto |
| Validador de la promesa original | Correcto; detección de cohorte completa al 60 % = 0.758985 |
| `scripts/run_demo.sh` | Correcto; 3.200 filas / 400 proyectos sintéticos |
| Docker local | No validado: el sandbox denegó leer `~/.docker/config.json`; además, `/var/run/docker.sock` no existe |
| Kubernetes local | No operado; sin contexto/clúster disponible |
| GitHub Actions | PR [#5](https://github.com/heiandavi-boop/tallerfina3/pull/5) pasó antes del merge; `quality` también pasó en el merge commit `f77329cf9bb5973f99923cd03e54063987dd582c` ([run 44439664881](https://github.com/heiandavi-boop/tallerfina3/actions/runs/44439664881)) |

El primer recorrido de la suite completa encontró un test antiguo que esperaba que una solicitud explícita llamara a Ollama con la bandera del servidor desactivada. Se actualizó el test de no mutación del entorno para ejecutarse con Ollama habilitado; la prohibición de anular la bandera queda cubierta por pruebas de seguridad. La suite completa se repitió y pasó.

## Integridad científica

No se modificaron dataset, split, configuración académica, modelos `.joblib` ni métricas oficiales. Los SHA-256 actuales coinciden con los registrados en [`scientific_integrity.json`](scientific_integrity.json). Los nuevos reportes operacionales y de proveedor son evidencia independiente.

## Pendientes que condicionan afirmaciones de nivel superior

- Ejecutar la comparación OpenAI real tras configurar la clave en el entorno autorizado del proceso.
- Obtener revisión humana y participantes reales antes de reportar calidad semántica o productividad.
- Validar Docker local cuando el sandbox permita leer el archivo de configuración Docker y acceder a un daemon.
- Operar Kubernetes autorizado para verificar balanceo, recuperación, actualización y rollback.
- Mantener retraining bloqueado hasta disponer de datos nuevos autorizados y reglas aprobadas.

## Evidencia relacionada

- [Resumen de pruebas](test_summary.md)
- [Índice de evidencia](evidence_index.md)
- [Integridad científica](scientific_integrity.json)
- [Dependencias externas pendientes](remaining_external_dependencies.md)
- [Comparación OpenAI/Ollama](../genai/provider_comparison_2026/comparison_report.md)
- [Auditoría de rúbrica](../../docs/RUBRICA_OFICIAL_PAIII_2026.md)
