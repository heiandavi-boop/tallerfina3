from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from fastapi.testclient import TestClient
from prunin_ai.api.app import app, runtime
checks = []


def check(name, ok, detail=''):
    checks.append((name, bool(ok), detail))


metadata = runtime.metadata()
model_features = set(metadata.get('trained_features', []))
team_health_features = set(runtime.config.get('team_health', {}).get('weights', {})) - model_features
expected_usage = {
    field['name']: 'ml_feature' if field['name'] in model_features
    else 'team_health' if field['name'] in team_health_features else 'not_used'
    for field in runtime.field_usage()
}

check('Frontend precompilado', (ROOT/'frontend/dist/index.html').exists())
check('Artefactos seleccionados', runtime.artifact_dir.exists(), str(runtime.artifact_dir))
for model in ['health', 'final_status', 'delay_days', 'cost_overrun_ratio']:
    derived = model == 'final_status' and runtime.manifest.get('final_status_mode') == 'derived_from_health'
    present = (runtime.artifact_dir / f'{model}.joblib').exists()
    check(f'Modelo {model}', present or derived, 'derivado de Health' if derived else '')
check('Metadata del modelo', all(metadata.get(key) for key in ['dataset_source', 'dataset_type', 'model_type']))
check('Fusion operativa heurística', metadata.get('fusion', {}).get('type') == 'operational_heuristic'
      and metadata.get('fusion', {}).get('calibrated') is False)

client = TestClient(app)
schema = client.get('/api/schema')
check('GET /api/schema', schema.status_code == 200, str(schema.status_code))
if schema.status_code == 200:
    body = schema.json()
    fields = body['fields']
    usage = {field['name']: field['usage'] for field in fields}
    check('Usage fields dinámico', usage == expected_usage)
    check('Features ML visibles', set(body['ml_features']) == model_features and model_features <= set(usage))
    check('Team Health separado', set(body['team_health_features']) == team_health_features)
    check('Features ML sin clase not_used', all(usage[name] == 'ml_feature' for name in model_features))
    sample = body['presets']['at_risk']
    prediction = client.post('/api/predict', json=sample)
    check('POST /api/predict', prediction.status_code == 200, str(prediction.status_code))
    if prediction.status_code == 200:
        response = prediction.json()
        result = response['prediction']
        check('Health ML output', result.get('health') in {'healthy', 'at_risk', 'critical'}, str(result.get('health')))
        check('Delay output', isinstance(result.get('delay_days'), (int, float)), str(result.get('delay_days')))
        check('Cost output', isinstance(result.get('cost_overrun_ratio'), (int, float)), str(result.get('cost_overrun_ratio')))
        check('Team Health auditable', isinstance(result.get('team_health'), dict) and
              all(key in result['team_health'] for key in ['score', 'level', 'weight_coverage', 'component_count', 'components']))
        check('Final Status derivation', result.get('final_status_source') == metadata.get('final_status_mode') and
              (metadata.get('final_status_mode') != 'derived_from_health' or
               result.get('final_status') == {'healthy': 'successful', 'at_risk': 'challenged', 'critical': 'critical'}.get(result.get('health'))))
        check('Driver source', response.get('driver_source') == 'local_model_sensitivity')
        check('Inference trace', bool(response.get('prediction_id')) and isinstance(response.get('inference_ms'), (int, float)))
        check('What-if', client.post('/api/what-if', json={'baseline': sample, 'scenario': sample}).status_code == 200)
    template = client.get('/api/csv-template')
    if template.status_code == 200:
        import csv
        import io

        columns = set(next(csv.reader(io.StringIO(template.text))))
        check('Plantilla CSV ML + Team Health', columns == set(body['academic_template_fields']))
        check('ML features en plantilla', model_features <= columns)
        check('Team Health opcional en plantilla', set(body['team_health_features']) <= columns)
        check('Plantilla CSV sin not_used', not (columns & set(body['not_used_features'])))

print('\nPRUNIN AI Core · Preflight')
print('='*54)
for name, ok, detail in checks:
    print(f"{'OK ' if ok else 'FAIL'}  {name:28} {detail}")
failed = [x for x in checks if not x[1]]
print('='*54)
print(f"Modelo: {runtime.version} ({runtime.mode})")
if failed:
    print(f"RESULTADO: {len(failed)} falla(s)")
    raise SystemExit(1)
print('RESULTADO: LISTO PARA DEMO')
