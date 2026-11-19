# MLOps: registro de modelos y ciclo de reentrenamiento controlado

Componentes: `src/prunin_ai/monitoring/mlops.py`, `scripts/mlops_pipeline.py`, `tests/test_mlops_pipeline.py`.
Registro versionado: [`model_registry.json`](model_registry.json).

## Qué hace el pipeline

1. **Bloqueado por defecto.** Sin `--authorize` termina con `BLOCKED` y no entrena nada.
2. **Procedencia.** Exige un archivo `*.provenance.json` con `authorized: true` y el SHA-256 exacto del dataset. Rechaza el dataset académico Mendeley.
3. **Activación.** Calcula PSI y missing rate frente a la referencia (`compare_feature_distributions`) y lo registra como `trigger`. Con `require_drift` exige que exista drift.
4. **Split propio.** TRAIN/VALIDATION/TEST por `project_id`, sin fuga entre proyectos. La selección usa **solo VALIDATION**; el TEST académico congelado no se toca.
5. **Entrenamiento aislado.** Los candidatos se escriben en `artifacts/candidates/<versión>` (ignorado por git). Las versiones congeladas no pueden reutilizarse ni sobrescribirse.
6. **Gate de regresión.** Compara candidato y baseline sobre la misma VALIDATION: Health macro-F1 (mayor es mejor) y MAE de Delay y Cost (menor es mejor). Bloquea si alguna métrica empeora más de 2 % relativo.
7. **Aprobación y promoción.** Solo un candidato `candidate_passed_gate` puede aprobarse, con responsable identificado. Solo uno `approved` puede promoverse.
8. **Rollback.** `rollback` restaura la versión de producción anterior. Cada acción queda en `events`.

## Ejecución real (2026-11-19)

```bash
python scripts/mlops_pipeline.py init-registry
python scripts/mlops_pipeline.py demo-cycle              # → BLOCKED (exit 3)
python scripts/mlops_pipeline.py demo-cycle --authorize  # datos sintéticos seed 2026, 400 proyectos
```

Baseline: `demo-0.1.0`. Candidato: `demo-candidate-2026`. Evaluación sobre VALIDATION del nuevo dataset sintético.

| Modelo | Métrica | Candidato | Baseline | Cambio relativo | Gate |
|---|---|---:|---:|---:|---|
| Health | macro-F1 | 0.3292 | 0.3812 | −13.6 % | ✗ |
| Delay | MAE (días) | 31.358 | 32.659 | +4.0 % (mejora) | ✓ |
| Cost | MAE | 0.04768 | 0.04898 | +2.6 % (mejora) | ✓ |

**Resultado: `rejected_regression`.** El candidato no se promovió y producción sigue en `demo-0.1.0`.

El gate funcionó como se diseñó: el candidato mejoraba dos modelos, pero degradaba la clasificación de salud.

**Drift registrado:** `drift_alert=true` en `methodology` y `project_type`. La referencia local `data/processed/demo_core.csv` se generó con una versión anterior del generador de demostración, que usaba otro vocabulario de categorías (`stage_gate` y `software` frente a `agile` y `r&d`). El PSI máximo (≈24) está inflado por las categorías ausentes en la referencia, que se recortan a ε. Este caso ilustra un cambio de esquema categórico, no una variación gradual.

## Alcance y límites

- Es una **demostración local de ciclo completo** con datos sintéticos separados del experimento académico. No es operación continua en producción: no hay scheduler, datos reales nuevos ni ground truth posterior.
- El drift detectado es de **datos** (entradas). El drift conceptual y la pérdida de desempeño requieren outcomes reales que hoy no existen.
- La versión `0.9.0-academic` figura como `frozen_academic`, con los hashes de sus `.joblib`. El pipeline no puede modificarla.
