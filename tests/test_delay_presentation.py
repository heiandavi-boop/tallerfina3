"""Operational policy must preserve model evidence and valid cost savings."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from prunin_ai.api.app import app, runtime
from prunin_ai.api.catalog import PRESETS
from prunin_ai.api.model_runtime import ModelRuntime


@pytest.mark.parametrize(('raw', 'display'), [(-0.3, 0.0), (0.0, 0.0), (14.5, 14.5)])
def test_runtime_preserves_raw_delay_and_only_clamps_delay(raw, display):
    evidence = {'delay_days': raw, 'cost_overrun_ratio': -0.12}
    fake = object.__new__(ModelRuntime)
    fake.manifest = {'numeric_features': ['spi'], 'categorical_features': []}
    fake.brain = SimpleNamespace(predict=lambda row: dict(evidence))
    result = fake.predict({'spi': 1.0})
    assert result['delay_days'] == display
    assert result['delay_days_raw'] == raw
    assert result['cost_overrun_ratio'] == -0.12
    assert evidence['delay_days'] == raw


def test_api_and_csv_keep_raw_prediction_for_technical_trace(monkeypatch):
    original = runtime.brain.predict
    def negative_delay(row):
        result = original(row)
        result['delay_days'] = -0.3
        result['cost_overrun_ratio'] = -0.12
        return result
    monkeypatch.setattr(runtime.brain, 'predict', negative_delay)
    client = TestClient(app)
    sample = PRESETS['at_risk']
    response = client.post('/api/predict', json=sample)
    assert response.status_code == 200
    import csv
    import io
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(sample))
    writer.writeheader()
    writer.writerow(sample)
    batch = client.post('/api/predict-csv', files={'file': ('trace.csv', stream.getvalue(), 'text/csv')})
    assert batch.status_code == 200
    row = batch.json()['rows'][0]
    assert row['error'] is None
    for prediction in [response.json()['prediction'], row['prediction']['prediction']]:
        assert prediction['delay_days'] == 0.0
        assert prediction['delay_days_raw'] == -0.3
        assert prediction['cost_overrun_ratio'] == -0.12
