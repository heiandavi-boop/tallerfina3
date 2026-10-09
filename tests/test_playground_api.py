import io
import importlib

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from prunin_ai.api.app import app, runtime

client = TestClient(app)
app_module = importlib.import_module('prunin_ai.api.app')


def test_schema_has_all_demo_features():
    r = client.get('/api/schema')
    assert r.status_code == 200
    body = r.json()
    names = {x['name'] for x in body['fields']}
    required = {
        'planned_duration_weeks','planned_budget','baseline_scope_units',
        'sector','project_type','methodology','complexity','criticality',
        'true_progress','spi','cpi','team_utilization','team_capacity_ratio',
        'average_productivity','defect_rate','rework_ratio','scope_growth_ratio',
        'dependency_delay_days','normalized_risk_exposure','governance_health_score',
        'team_stability','collaboration_level'
    }
    assert required <= names
    assert 'team_morale' not in names
    assert 'reported_progress' not in names
    assert 'critical_path_delay_days' not in names
    model_features = set(body['model']['trained_features'])
    assert model_features == set(body['ml_features'])
    assert all(field['usage'] == 'ml_feature' for field in body['fields'] if field['name'] in model_features)
    expected_team_health = set(client.get('/api/health').json()['manifest'].get('team_health_features', []))
    if not expected_team_health:
        from prunin_ai.api.app import runtime
        expected_team_health = set(runtime.config.get('team_health', {}).get('weights', {})) - model_features
    assert set(body['team_health_features']) == expected_team_health
    assert all(field['usage'] == 'team_health' for field in body['fields'] if field['name'] in body['team_health_features'])
    assert all(field['usage'] == 'not_used' for field in body['fields'] if field['name'] in body['not_used_features'])
    assert all(field['trained'] == (field['usage'] == 'ml_feature') for field in body['fields'])
    assert all(field['usage_label'] for field in body['fields'])
    assert all(field['affects_ml_prediction'] == (field['usage'] == 'ml_feature') for field in body['fields'])
    team_health_inputs = set(runtime.config['team_health']['weights'])
    assert all(field['affects_team_health'] == (field['name'] in team_health_inputs) for field in body['fields'])


def test_predict_live():
    schema = client.get('/api/schema').json()
    r = client.post('/api/predict', json=schema['presets']['at_risk'])
    assert r.status_code == 200
    body = r.json()
    assert body['model']['execution'] == 'LIVE'
    assert body['prediction']['health'] in {'healthy','at_risk','critical'}
    assert isinstance(body['prediction']['delay_days'], (int,float))
    assert isinstance(body['prediction']['cost_overrun_ratio'], (int,float))
    assert body['prediction_id']
    assert body['model']['dataset_source']
    assert body['model']['dataset_type']
    assert body['model']['model_type']
    assert body['model']['fusion']['type'] == 'operational_heuristic'
    assert body['model']['fusion']['calibrated'] is False
    assert body['model']['fusion']['core_weight'] == 0.85
    assert body['model']['fusion']['team_health_weight'] == 0.15
    assert isinstance(body['inference_ms'], (int,float))
    assert body['timing']['total_ms'] == body['inference_ms']
    assert isinstance(body['timing']['ml_and_drivers_ms'], (int,float))
    assert body['timing']['genai_ms'] is None or isinstance(body['timing']['genai_ms'], (int,float))
    assert body['prediction']['final_status_source'] in {'derived_from_health','independent_model'}
    expected_status_source = (
        'derived_from_health'
        if schema['model']['final_status_mode'] == 'derived_from_health'
        else 'independent_model'
    )
    assert body['prediction']['final_status_source'] == expected_status_source
    assert body['driver_source'] == 'local_model_sensitivity'
    assert {driver['feature'] for driver in body['drivers']} <= set(body['model']['trained_features'])
    assert 'no demuestra causalidad' in body['drivers_disclaimer']


def test_what_if():
    schema = client.get('/api/schema').json()
    baseline = dict(schema['presets']['critical'])
    scenario = dict(baseline)
    for name in schema['what_if_fields']:
        scenario[name] = schema['presets']['healthy'][name]
    r = client.post('/api/what-if', json={'baseline': baseline, 'scenario': scenario})
    assert r.status_code == 200
    body = r.json()
    assert 'baseline' in body and 'scenario' in body and 'delta' in body


def test_what_if_and_ten_row_csv_never_call_recommendation_engine(monkeypatch):
    monkeypatch.setenv('PRUNIN_ENABLE_OLLAMA', '1')
    monkeypatch.setattr(app_module, 'build_recommendations', lambda *args: pytest.fail('LLM must not run for what-if or CSV'))
    schema = client.get('/api/schema').json()
    baseline = dict(schema['presets']['at_risk'])
    scenario = dict(baseline)
    scenario['spi'] = schema['presets']['healthy']['spi']

    what_if_response = client.post('/api/what-if', json={'baseline': baseline, 'scenario': scenario})
    assert what_if_response.status_code == 200
    what_if_body = what_if_response.json()
    assert what_if_body['baseline']['recommendations']['engine'] == 'not_requested'
    assert what_if_body['scenario']['recommendations']['engine'] == 'not_requested'
    assert what_if_body['baseline']['timing']['genai_ms'] is None

    template = client.get('/api/csv-template')
    one_row = pd.read_csv(io.BytesIO(template.content))
    ten_rows = pd.concat([one_row] * 10, ignore_index=True).to_csv(index=False).encode()
    csv_response = client.post('/api/predict-csv', files={'file': ('input.csv', ten_rows, 'text/csv')})
    assert csv_response.status_code == 200
    assert csv_response.json()['count'] == 10
    assert all(row['prediction']['recommendations']['engine'] == 'not_requested' for row in csv_response.json()['rows'])


@pytest.mark.parametrize('status', [
    {'enabled': True, 'provider': 'ollama', 'model': 'qwen3:8b', 'available': True, 'last_error': None},
    {'enabled': False, 'provider': 'ollama', 'model': 'qwen3:8b', 'available': False, 'last_error': None},
])
def test_genai_status_endpoint(monkeypatch, status):
    monkeypatch.setattr(app_module, 'check_ollama_status', lambda: status)
    response = client.get('/api/genai-status')
    assert response.status_code == 200
    assert response.json() == status


def test_team_health_what_if_does_not_change_health_ml_output():
    schema = client.get('/api/schema').json()
    team_field = schema['team_health_features'][0]
    baseline = dict(schema['presets']['at_risk'])
    scenario = dict(baseline)
    scenario[team_field] = 0.0 if baseline[team_field] else 1.0

    response = client.post('/api/what-if', json={'baseline': baseline, 'scenario': scenario})

    assert response.status_code == 200
    body = response.json()
    assert body['baseline']['prediction']['health'] == body['scenario']['prediction']['health']
    assert body['baseline']['prediction']['team_health']['score'] != body['scenario']['prediction']['team_health']['score']
    assert body['delta']['risk_score'] != 0


def test_csv_template_and_csv_prediction():
    template = client.get('/api/csv-template')
    assert template.status_code == 200
    files = {'file': ('input.csv', template.content, 'text/csv')}
    r = client.post('/api/predict-csv', files=files)
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 1
    assert body['rows'][0]['error'] is None
    schema = client.get('/api/schema').json()
    academic_template = client.get('/api/csv-template')
    columns = set(pd.read_csv(io.BytesIO(academic_template.content)).columns)
    assert columns == set(schema['academic_template_fields'])
    assert set(schema['ml_features']) <= columns
    assert set(schema['team_health_features']) <= columns
    assert academic_template.headers['x-optional-team-health-features']
    assert not (columns & set(schema['not_used_features']))
    future_template = client.get('/api/csv-template?profile=full_future')
    assert future_template.status_code == 200
    assert len(pd.read_csv(io.BytesIO(future_template.content)).columns) == len(schema['fields'])

def test_health_readiness_and_monitoring_endpoints():
    ready = client.get('/api/ready')
    assert ready.status_code == 200
    assert ready.json()['status'] == 'ready'

    monitoring = client.get('/api/monitoring')
    assert monitoring.status_code == 200
    assert 'total_predictions' in monitoring.json()

    metrics = client.get('/metrics')
    assert metrics.status_code == 200
    assert 'prunin_predictions_total' in metrics.text
    assert 'prunin_inference_latency_p95_ms' in metrics.text


def test_static_frontend_and_qr():
    home = client.get('/')
    assert home.status_code == 200
    assert 'PRUNIN AI Core' in home.text
    qr = client.get('/api/qr', params={'url': 'https://example.com/prunin'})
    assert qr.status_code == 200
    assert qr.headers['content-type'] == 'image/png'
    assert len(qr.content) > 100
