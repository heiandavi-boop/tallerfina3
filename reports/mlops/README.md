# MLOps: registro, monitorización y reentrenamiento controlado

Componentes: `src/prunin_ai/monitoring/mlops.py`, `scripts/mlops_pipeline.py`, `scripts/check_drift.py` y `tests/test_mlops_pipeline.py`.
Registro local: [`model_registry.json`](model_registry.json), esquema 2.

## Semántica del registro

- `0.9.0-academic`: `frozen_academic`; versión de investigación preservada. No representa aprobación institucional.
- `demo-0.1.0`: `demo_available`; artefacto sintético disponible para demostración.
- `demo-candidate-2026`: `rejected_regression`.
- `deployments.production` y `deployments.test`: `null`; no se verificó despliegue en esos entornos.
- `deployments.demo`: `demo-0.1.0`; referencia a la demo local/CI, no a producción.
- `selected_for_deployment`: `null`. Seleccionar una versión tras aprobación registra una decisión de registro, no despliega un servicio.

La migración del esquema anterior retiró la atribución de aprobación al “comité académico” porque no había evidencia documental. También cambió el estado `production` de la demo a `demo_available` y eliminó el puntero de producción no verificado.

## Métricas académicas y unidades

La versión académica conserva en el registro las métricas de `reports/0.9.0-academic/metrics.json` separadas por unidad, siempre sobre TEST congelado:

| Target | Snapshot rows (cada proyecto puede aportar varios snapshots) | Último snapshot por proyecto |
|---|---:|---:|
| Health | Macro-F1 0.547055 | Macro-F1 0.627576 |
| Delay | MAE 32.175956 días | MAE 27.710468 días |
| Cost | R² 0.829707 | R² 0.991816 |

La diferencia anterior del registro no era una contradicción de los resultados: se habían copiado métricas por snapshot y comparado con indicadores del informe calculados por proyecto, sin registrar esa distinción. El esquema 2 conserva ambas evaluaciones y el archivo fuente. Cost R² sigue condicionado por la estructura del generador sintético.

## Monitorización offline

`scripts/check_drift.py` construye la referencia exclusivamente con proyectos TRAIN y compara un batch sin entrenar ni promover modelos. Genera un perfil fuera del directorio de artefactos académicos, un reporte JSON fechado con hashes, PSI y missing rate. La opción `--fail-on-alert` devuelve código 2 para una tarea de automatización cuando aparece una alerta. Una alerta describe cambio de datos y **no** confirma drift conceptual ni pérdida de desempeño.

Ejecución registrada: comparación TRAIN vs. VALIDATION, 600 proyectos y 10.880 snapshots; no hubo features con alerta ni columnas faltantes. El reporte confirma `retraining_triggered: false`. Es una verificación retrospectiva reproducible, no monitorización empresarial continua.

## Ciclo de reentrenamiento controlado

1. Bloqueado sin `--authorize`.
2. Exige `*.provenance.json` con `authorized: true` y SHA-256 coincidente; rechaza Mendeley académico.
3. Genera TRAIN/VALIDATION/TEST propios por `project_id`, sin solapamiento. La decisión utiliza solo VALIDATION; no abre el TEST académico.
4. Entrena en `artifacts/candidates/<versión>`, ignorado por Git.
5. El gate compara Health macro-F1 (mayor es mejor) y MAE de Delay/Cost (menor es mejor); rechaza degradación mayor a 2 % relativo.
6. La aprobación requiere una persona responsable identificada. `select-for-deployment` solo selecciona en el registro; no despliega. `rollback-selection` revierte esa selección y no detiene/restaura un servicio.

Demostración ejecutada con datos sintéticos nuevos (seed 2026, 400 proyectos): el candidato mejora Delay 4,0 % y Cost 2,6 %, pero Health baja 13,6 %. El gate marca `rejected_regression`; ninguna promoción ni despliegue ocurrió. La alerta PSI alta de `methodology`/`project_type` se debe a vocabularios incompatibles entre dos versiones del generador demo y no debe interpretarse como drift de una población real.

## Límites

No hay nuevos datos empresariales autorizados, scheduler conectado a una fuente operativa, ground truth, aprobación humana de candidatos ni despliegue productivo. Kubernetes no tiene contexto de clúster disponible. Docker está instalado, pero no hay daemon local; el CI de `main` sí construyó y ejecutó el smoke test de contenedor en el commit `868ea86435bde7412bcee36c0ead821f289b694f`.
