from fastapi.testclient import TestClient
from prunin_ai.api.app import app

client = TestClient(app)


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
    assert isinstance(body['inference_ms'], (int,float))
    assert body['prediction']['final_status_source'] in {'derived_from_health','independent_model'}
    expected_status_source = (
        'derived_from_health'
        if schema['model']['final_status_mode'] == 'derived_from_health'
        else 'independent_model'
    )
    assert body['prediction']['final_status_source'] == expected_status_source


def test_what_if():
    schema = client.get('/api/schema').json()
    r = client.post('/api/what-if', json={'baseline': schema['presets']['critical'], 'scenario': schema['presets']['healthy']})
    assert r.status_code == 200
    body = r.json()
    assert 'baseline' in body and 'scenario' in body and 'delta' in body


def test_csv_template_and_csv_prediction():
    template = client.get('/api/csv-template')
    assert template.status_code == 200
    files = {'file': ('input.csv', template.content, 'text/csv')}
    r = client.post('/api/predict-csv', files=files)
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 1
    assert body['rows'][0]['error'] is None

def test_static_frontend_and_qr():
    home = client.get('/')
    assert home.status_code == 200
    assert 'PRUNIN AI Core' in home.text
    qr = client.get('/api/qr', params={'url': 'https://example.com/prunin'})
    assert qr.status_code == 200
    assert qr.headers['content-type'] == 'image/png'
    assert len(qr.content) > 100
