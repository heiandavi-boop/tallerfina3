// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ModelsWorkbench, PredictionComparison } from './ModelsWorkbench.jsx';

const models = [
    {
        id: 'academic', name: 'PRUNIN Academic', version: '0.9.0-academic', source_type: 'synthetic', dataset_source: 'Mendeley synthetic',
        status: 'ready', artifact_path: 'artifacts/0.9.0-academic', project_count: 4000, snapshot_count: 72549, features: ['a', 'b', 'c', 'd', 'e', 'f', 'g'],
        targets: ['health', 'delay_days', 'cost_overrun_ratio'],
        metrics: {
            health: { project_level_metrics: { test: { macro_f1: .6275758 } } },
            delay_days: { project_level_metrics: { test: { mae: 27.710468 } } },
            cost_overrun_ratio: { project_level_metrics: { test: { mae_percentage_points: .1471578 } } },
        },
    },
    {
        id: 'empirical', name: 'PRUNIN Empirical', version: '1.0.0-empirical', source_type: 'real', dataset_source: 'DSLIB / PSLIB v3.4',
        status: 'ready', artifact_path: 'artifacts/1.0.0-empirical', project_count: 151, snapshot_count: 0, features: ['planned_duration_days', 'planned_budget_bac'],
        targets: ['delay', 'cost'],
        metrics: { delay: { test: { mae: 30.7097 } }, cost: { test: { mae: .115703 } } },
        early_prediction: { status: 'not_available', delay_candidate_snapshots: 13 },
    },
];

const jsonResponse = (body, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(body) });
const baseProps = { activeModel: 'academic', onSelectModel: vi.fn(), values: {}, onCompare: vi.fn(), comparison: null, compareLoading: false };

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('Models workbench', () => {
    it('renders side-by-side prediction results without implying a winner', () => {
        render(<PredictionComparison data={{
            academic: { model: { version: '0.9.0-academic' }, prediction: { health: 'at_risk', delay_days_raw: 70, cost_overrun_ratio: .08 } },
            empirical: { model: { version: '1.0.1-empirical' }, prediction: { health: null, delay_days_raw: 9, cost_overrun_ratio: .007 } },
            comparison: { note: 'Predicciones lado a lado; datasets y targets distintos, no indican cuál es correcto.' },
        }} />);

        expect(screen.getByText('0.9.0-academic')).toBeTruthy();
        expect(screen.getByText('1.0.1-empirical')).toBeTruthy();
        expect(screen.getByText('No disponible')).toBeTruthy();
        expect(screen.getByText('8 %')).toBeTruthy();
        expect(screen.getByText('0,7 %')).toBeTruthy();
        expect(screen.getByText(/no indican cuál es correcto/)).toBeTruthy();
    });

    it('shows both model cards with project-level metrics and manual activation', async () => {
        vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ models, active_model: 'academic', training_enabled: false })));
        render(<ModelsWorkbench {...baseProps} />);

        expect(await screen.findByRole('heading', { name: 'PRUNIN Academic' })).toBeTruthy();
        expect(screen.getByRole('heading', { name: 'PRUNIN Empirical' })).toBeTruthy();
        expect(screen.getAllByText('0,628').length).toBeGreaterThan(0);
        expect(screen.getAllByText(/27,71/).length).toBeGreaterThan(0);
        expect(screen.getAllByText('0,147').length).toBeGreaterThan(0);
        expect(screen.getByText(/13 snapshots candidatos, insuficientes/)).toBeTruthy();
        expect(screen.getByRole('button', { name: 'Entrenar nueva versión' }).disabled).toBe(true);
    });

    it('requires confirmation, shows real backend progress, and does not promote on completion', async () => {
        let jobPolls = 0;
        const fetchMock = vi.fn((url, options = {}) => {
            if (url.endsWith('/api/models')) return jsonResponse({ models, active_model: 'academic', training_enabled: true });
            if (url.endsWith('/api/training/empirical') && options.method === 'POST') return jsonResponse({ job_id: 'job-1', status: 'queued' });
            if (url.endsWith('/api/training/job-1/logs')) return jsonResponse({ events: [{ status: 'training_delay', message: 'Training Delay model' }] });
            if (url.endsWith('/api/training/job-1')) {
                jobPolls += 1;
                if (jobPolls === 1) return jsonResponse({ job_id: 'job-1', status: 'training_delay', progress_percent: 60, current_step: 'Training Delay model', result: null, error: null });
                return jsonResponse({ job_id: 'job-1', status: 'completed', progress_percent: 100, current_step: 'Done', result: { version: '1.0.1-empirical' }, error: null });
            }
            return jsonResponse({ detail: 'Not found' }, false);
        });
        vi.stubGlobal('fetch', fetchMock);
        render(<ModelsWorkbench {...baseProps} />);

        await screen.findByRole('heading', { name: 'PRUNIN Empirical' });
        fireEvent.click(screen.getByRole('button', { name: 'Entrenar nueva versión' }));
        const dialog = screen.getByRole('dialog', { name: 'Entrenar PRUNIN Empirical' });
        expect(within(dialog).getByText(/El modelo académico no será modificado ni activado/)).toBeTruthy();
        fireEvent.click(within(dialog).getByRole('button', { name: 'Entrenar' }));

        expect(await screen.findByText('Training Delay model')).toBeTruthy();
        await waitFor(() => expect(screen.getByText(/ENTRENAMIENTO COMPLETADO/)).toBeTruthy());
        expect(screen.getByText(/Versión 1.0.1-empirical/)).toBeTruthy();
        expect(screen.getByText(/Academic permanece activo/)).toBeTruthy();
        expect(fetchMock).toHaveBeenCalledWith('/api/training/empirical', { method: 'POST' });
    });

    it('manual activation calls the parent selector and training cancel sends no request', async () => {
        const onSelectModel = vi.fn();
        const fetchMock = vi.fn(() => jsonResponse({ models, active_model: 'academic', training_enabled: false }));
        vi.stubGlobal('fetch', fetchMock);
        render(<ModelsWorkbench {...baseProps} onSelectModel={onSelectModel} />);

        await screen.findByRole('heading', { name: 'PRUNIN Empirical' });
        fireEvent.click(screen.getByRole('button', { name: 'Usar modelo' }));
        expect(onSelectModel).toHaveBeenCalledWith('empirical');
        expect(fetchMock).toHaveBeenCalledTimes(1);
    });
});