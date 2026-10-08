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

check('Frontend precompilado', (ROOT/'frontend/dist/index.html').exists())
check('Artefactos seleccionados', runtime.artifact_dir.exists(), str(runtime.artifact_dir))
for model in ['health','final_status','delay_days','cost_overrun_ratio']:
    check(f'Modelo {model}', (runtime.artifact_dir/f'{model}.joblib').exists())

client = TestClient(app)
schema = client.get('/api/schema')
check('GET /api/schema', schema.status_code == 200, str(schema.status_code))
if schema.status_code == 200:
    sample = schema.json()['presets']['at_risk']
    pred = client.post('/api/predict', json=sample)
    check('POST /api/predict', pred.status_code == 200, str(pred.status_code))
    if pred.status_code == 200:
        p = pred.json()['prediction']
        check('Health output', p.get('health') in {'healthy','at_risk','critical'}, str(p.get('health')))
        check('Delay output', isinstance(p.get('delay_days'), (int,float)), str(p.get('delay_days')))
        check('Cost output', isinstance(p.get('cost_overrun_ratio'), (int,float)), str(p.get('cost_overrun_ratio')))
        check('Team Health', isinstance(p.get('team_health'), dict), str(p.get('team_health',{}).get('level')))

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
