# Detector académico de drift y OOD

## Alcance

`src/prunin_ai/monitoring/drift.py` implementa perfil de referencia TRAIN, evaluación univariada de OOD y comparación de cohortes. Es un detector transparente de investigación/operación manual, no un monitor productivo. Sus avisos no modifican features, thresholds, artefactos `.joblib` ni predicciones, y no activan retraining.

El perfil `artifacts/0.9.0-academic/input_profile.json` se genera desde las filas cuyos `project_id` están en `split_manifest.json["train"]`. Conserva fingerprint SHA256 del CSV procesado y del split, nombre del artifact, conteos y límites. No usa VALIDATION/TEST para construir referencia. Si el perfil no existe, la API reporta `ood_available=false` y no inventa advertencias.

## OOD de una entrada API

`input_quality` informa `coverage`, `missing_features`, `ood_warning` y `ood_features`. Numéricas fuera de fence TRAIN de 1.5 IQR y categorías ausentes de TRAIN generan aviso; una feature faltante sigue cubierta por la política de imputación/gate y no se confunde automáticamente con OOD. El frontend muestra el aviso solo cuando el backend lo produce. El fence univariado no detecta combinaciones inéditas, shift semántico, magnitudes/moneda incorrectas ni falsos positivos; es solo una advertencia.

## Comparación batch

Construir/actualizar el perfil con TRAIN y comparar un CSV nuevo:

```bash
source .venv/bin/activate
PYTHONPATH=src python scripts/check_drift.py
PYTHONPATH=src python scripts/check_drift.py --batch path/to/new_batch.csv --report-output reports/drift/example.json
```

Por defecto, `--psi-threshold 0.2` y `--missing-rate-shift-threshold 0.1`; ambos se configuran por CLI. Variables numéricas y categóricas se comparan por PSI y por cambio absoluto de missing-rate. Las categorías desconocidas se incluyen como bins; una cohorte vacía se rechaza. Los umbrales son iniciales y no están calibrados con outcomes reales.

El reporte registra tamaños, features, scores, límites y alertas. Revisar una alerta con expertos y outcomes aprobados; no seleccionar modelos con TEST. La política de retraining requiere datos aprobados, outcomes observados, comparación en VALIDATION y TEST final congelado. No hay retraining automático ni drift continuo productivo.