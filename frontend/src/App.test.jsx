// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Experience from './Experience.jsx';

const fields = [
  { name: 'planned_duration_weeks', label: 'Duración planificada', group: 'Proyecto', type: 'number', usage: 'ml_feature', min: 1, max: 520, step: 1, reference: 52, description: 'Duración base.' },
  { name: 'planned_budget', label: 'Presupuesto planificado', group: 'Proyecto', type: 'number', usage: 'ml_feature', min: 1, max: 200000000000, step: 1000000, reference: 1000000000, description: 'Presupuesto.' },
  { name: 'project_type', label: 'Tipo de proyecto', group: 'Proyecto', type: 'select', usage: 'ml_feature', options: ['software', 'transformation'], description: 'Tipo.' },
  { name: 'methodology', label: 'Metodología', group: 'Proyecto', type: 'select', usage: 'ml_feature', options: ['hybrid', 'scrum'], description: 'Método.' },
  { name: 'true_progress', label: 'Avance real', group: 'Ejecución', type: 'range', usage: 'ml_feature', min: 0, max: 1, step: .01, format: 'percent', reference: .5, description: 'Avance.' },
  { name: 'spi', label: 'SPI', group: 'Ejecución', type: 'range', usage: 'ml_feature', min: .1, max: 1.5, step: .01, reference: 1, description: 'Índice de cronograma.' },
  { name: 'cpi', label: 'CPI', group: 'Ejecución', type: 'range', usage: 'ml_feature', min: .1, max: 1.5, step: .01, reference: 1, description: 'Índice de costo.' },
  { name: 'team_utilization', label: 'Utilización', group: 'Equipo', type: 'range', usage: 'team_health', min: 0, max: 1.5, step: .01, reference: .85, format: 'percent', description: 'Utilización.' },
  { name: 'future_feature', label: 'Variable futura', group: 'Futuro', type: 'number', usage: 'not_used', description: 'No se usa.' },
];
const preset = { planned_duration_weeks: 52, planned_budget: 2500000000, project_type: 'transformation', methodology: 'hybrid', true_progress: .47, spi: .82, cpi: .91, team_utilization: .96, future_feature: 5 };
const model = { version: '0.9.0-academic', mode: 'academic', dataset_source: 'Mendeley Data 2p5sz57wh2 v2', dataset_type: 'synthetic_external', model_type: 'LightGBM', final_status_mode: 'derived_from_health', minimum_feature_coverage: .6, trained_features: fields.filter(field => field.usage === 'ml_feature').map(field => field.name), fusion: { core_weight: .85, team_health_weight: .15, calibrated: false } };
const schema = { fields, ml_features: model.trained_features, team_health_features: ['team_utilization'], not_used_features: ['future_feature'], what_if_fields: [...model.trained_features, 'team_utilization'], model, presets: { healthy: { ...preset, spi: 1.04, cpi: 1.02 }, at_risk: preset, critical: { ...preset, spi: .61, cpi: .72 } } };
const fallback = { engine: 'grounded_fallback', genai_attempted: false, genai_used: false, evidence_features: ['cpi', 'true_progress'], reasons: ['CPI muestra una señal de mayor riesgo.'], actions: ['Revisar la proyección de costos y la estimación a la conclusión.'], disclaimer: 'Validar con criterio profesional.' };

function prediction(recommendations = fallback, complete = true) {
  return { prediction_id: 'test-prediction', model: { ...model, execution: 'LIVE' }, inference_ms: 64.2, driver_source: 'local_model_sensitivity', drivers: [{ feature: 'cpi', label: 'CPI', value: .38, reference: 1, risk_impact: .231, direction: 'increases_risk' }, { feature: 'spi', label: 'SPI', value: .54, reference: 1, risk_impact: -.132, direction: 'reduces_risk' }], recommendations, prediction: { health: 'critical', fused_health: 'critical', fused_risk_score: .702, delay_days: 68.3, cost_overrun_ratio: .234, final_status: 'critical', final_status_source: 'derived_from_health', health_probabilities: { healthy: .005, at_risk: .455, critical: .54 }, input_quality: { complete, coverage: complete ? 1 : .86, missing_count: complete ? 0 : 1 }, team_health: { score: .667, level: 'attention', component_count: 7, weight_coverage: 1, components: { team_utilization: .667, team_capacity_ratio: .72 } } } };
}
const whatIfResult = { baseline: prediction(), scenario: prediction(), delta: { risk_score: -.256, delay_days: -7.1, cost_overrun_ratio: -.261 } };
const csvPrediction = prediction();
csvPrediction.prediction.final_status = 'challenged';
const csvResult = { count: 1, rows: [{ row_number: 1, error: null, prediction: csvPrediction }] };
const jsonResponse = (body, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(body) });

function installFetch({ recommendation = fallback, complete = true, csv = csvResult } = {}) {
  global.fetch = vi.fn((url) => {
    if (url.endsWith('/api/schema')) return jsonResponse(schema);
    if (url.endsWith('/api/ready')) return Promise.resolve({ ok: true });
    if (url.endsWith('/api/predict')) return jsonResponse(prediction(recommendation, complete));
    if (url.endsWith('/api/what-if')) return jsonResponse(whatIfResult);
    if (url.endsWith('/api/predict-csv')) return jsonResponse(csv);
    return jsonResponse({ detail: 'Not found' }, false);
  });
}

beforeEach(() => {
  installFetch();
  Element.prototype.scrollIntoView = vi.fn();
  window.requestAnimationFrame = callback => window.setTimeout(callback, 0);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

async function openProject() {
  render(<Experience />);
  await screen.findByRole('heading', { name: 'Analizar proyecto' });
}

describe('Playground ejecutivo', () => {
  it('presenta la marca, modos principales y solo variables ML en el formulario inicial', async () => {
    await openProject();
    expect(within(screen.getByRole('banner')).getByText('PRUNIN AI Core')).toBeTruthy();
    expect(document.querySelector('.tagline').textContent.replace(/\s+/g, ' ')).toContain('Predice · Explica · Recomienda · Simula');
    expect(screen.getByRole('tab', { name: 'Analizar proyecto' }).getAttribute('aria-selected')).toBe('true');
    expect(screen.getByRole('tab', { name: 'Analizar CSV' })).toBeTruthy();
    expect(screen.getByLabelText(/SPI/)).toBeTruthy();
    expect(screen.queryByText('Variable futura')).toBeNull();
    expect(screen.getByText(/Datos completos/)).toBeTruthy();
  });

  it('muestra loading inmediato, el resultado Health y la calidad de entrada del backend', async () => {
    const user = userEvent.setup();
    let resolvePrediction;
    global.fetch = vi.fn(url => {
      if (url.endsWith('/api/schema')) return jsonResponse(schema);
      if (url.endsWith('/api/ready')) return Promise.resolve({ ok: true });
      if (url.endsWith('/api/predict')) return new Promise(resolve => { resolvePrediction = resolve; });
      return jsonResponse(whatIfResult);
    });
    await openProject();
    await user.click(screen.getByRole('button', { name: 'Analizar proyecto' }));
    const loadingButton = await screen.findByRole('button', { name: /Analizando proyecto/ });
    expect(loadingButton.disabled).toBe(true);
    expect(screen.getByText(/Calculando predicciones/)).toBeTruthy();
    resolvePrediction(await jsonResponse(prediction(fallback, false)));
    expect(await screen.findByRole('heading', { name: 'Resultado del análisis' })).toBeTruthy();
    expect(screen.getAllByText('Crítico').length).toBeGreaterThan(0);
    expect(screen.getByText(/imputaron 1/)).toBeTruthy();
  });

  it('distingue la recomendación de respaldo y revela trazabilidad sin JSON por defecto', async () => {
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('button', { name: 'Analizar proyecto' }));
    expect(await screen.findByText(/IA generativa desactivada · Recomendación de respaldo/)).toBeTruthy();
    expect(screen.getByText(/Revisar la proyección de costos/)).toBeTruthy();
    await user.click(screen.getAllByRole('button', { name: /Ver evidencia técnica/ })[0]);
    const drawer = await screen.findByRole('dialog', { name: 'Trazabilidad de inferencia' });
    expect(within(drawer).getByText('Mendeley Data 2p5sz57wh2 v2')).toBeTruthy();
    expect(within(drawer).getByText('Ejecución')).toBeTruthy();
    expect(within(drawer).queryByText(/"prediction_id"/)).toBeNull();
    await user.click(within(drawer).getByRole('button', { name: 'Ver JSON completo' }));
    expect(within(drawer).getByText(/"prediction_id": "test-prediction"/)).toBeTruthy();
  });

  it('identifica Qwen3 cuando el backend confirma que GenAI fue utilizada', async () => {
    installFetch({ recommendation: { ...fallback, engine: 'ollama:qwen3:8b', genai_attempted: true, genai_used: true, actions: ['Revisar el cronograma.'] } });
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('button', { name: 'Analizar proyecto' }));
    expect(await screen.findByText('Qwen3 8B · IA generativa activa')).toBeTruthy();
  });

  it('explica de forma moderada el timeout de Qwen y confirma el uso de respaldo', async () => {
    installFetch({ recommendation: { ...fallback, genai_attempted: true, genai_failure_reason: 'ReadTimeout: Ollama did not respond', genai_used: false } });
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('button', { name: 'Analizar proyecto' }));
    expect(await screen.findByText(/Qwen3 no respondió dentro del tiempo esperado; se utilizó recomendación de respaldo/)).toBeTruthy();
    expect(screen.getByText('La predicción se completó correctamente.')).toBeTruthy();
    expect(screen.queryByText(/ReadTimeout/)).toBeNull();
    await user.click(screen.getAllByRole('button', { name: /Ver evidencia técnica/ })[0]);
    const drawer = await screen.findByRole('dialog', { name: 'Trazabilidad de inferencia' });
    await user.click(within(drawer).getByText('Detalle técnico de GenAI'));
    expect(within(drawer).getByText('ReadTimeout: Ollama did not respond')).toBeTruthy();
  });

  it('envía baseline y escenario completos y muestra la comparación del endpoint what-if', async () => {
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('button', { name: 'Analizar proyecto' }));
    await screen.findByRole('heading', { name: 'Simula una mejora' });
    const simulation = screen.getByRole('region', { name: 'Simula una mejora' });
    expect(within(simulation).queryByRole('option', { name: 'Variable futura' })).toBeNull();
    const spi = simulation.querySelector('#scenario-spi');
    fireEvent.change(spi, { target: { value: '1.1' } });
    await user.click(screen.getByRole('button', { name: 'Simular escenario' }));
    expect(await screen.findByText('Antes')).toBeTruthy();
    const request = global.fetch.mock.calls.find(([url]) => url.endsWith('/api/what-if'));
    const body = JSON.parse(request[1].body);
    expect(body.baseline.spi).toBe(.82);
    expect(body.scenario.spi).toBe(1.1);
    expect(body.scenario.cpi).toBe(.91);
    expect(screen.getByText('-26,1 pp')).toBeTruthy();
  });

  it('cambia al modo CSV, descarga plantilla y presenta resultados tabulares', async () => {
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('tab', { name: 'Analizar CSV' }));
    expect(await screen.findByRole('heading', { name: 'Carga masiva de proyectos' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Analizar proyecto' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Descargar plantilla' }).getAttribute('href')).toContain('/api/csv-template');
    const file = new File(['planned_duration_weeks\n52'], 'projects.csv', { type: 'text/csv' });
    await user.upload(screen.getByLabelText('Seleccionar archivo CSV'), file);
    await user.click(screen.getByRole('button', { name: 'Analizar CSV' }));
    expect(await screen.findByRole('heading', { name: '1 de 1 proyectos analizados' })).toBeTruthy();
    expect(screen.getByText('68,3 días')).toBeTruthy();
    expect(screen.getByText('Con desviaciones')).toBeTruthy();
  });

  it('traduce una fila CSV por debajo de cobertura a un mensaje claro', async () => {
    installFetch({ csv: { count: 1, rows: [{ row_number: 1, prediction: null, error: 'Cobertura insuficiente de features: 28%. Se requiere al menos 60%.' }] } });
    const user = userEvent.setup();
    await openProject();
    await user.click(screen.getByRole('tab', { name: 'Analizar CSV' }));
    await screen.findByRole('heading', { name: 'Carga masiva de proyectos' });
    const file = new File(['planned_duration_weeks\n52'], 'partial.csv', { type: 'text/csv' });
    await user.upload(screen.getByLabelText('Seleccionar archivo CSV'), file);
    await user.click(screen.getByRole('button', { name: 'Analizar CSV' }));
    expect(await screen.findByText(/Datos incompletos: no se alcanza la cobertura mínima/)).toBeTruthy();
  });
});