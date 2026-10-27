import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || '';
const number = value => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('es-CO', { maximumFractionDigits: 3 });
const percent = value => value == null || !Number.isFinite(Number(value)) ? '—' : `${(Number(value) * 100).toLocaleString('es-CO', { maximumFractionDigits: 1 })} %`;
const statusNames = { ready: 'Disponible', not_trained: 'Sin entrenar', unavailable: 'No disponible' };

function metric(model, candidates, key) {
    for (const name of candidates) {
        const values = model?.metrics?.[name];
        const result = values?.project_level_metrics?.test?.[key] ?? values?.test?.[key];
        if (result != null) return result;
    }
    return null;
}

function healthMacroF1(model) {
    return model?.metrics?.health?.project_level_metrics?.test?.macro_f1 ?? model?.metrics?.health?.test?.macro_f1;
}

function costMaePercentagePoints(model) {
    const reported = metric(model, ['cost_overrun_ratio', 'cost'], 'mae_percentage_points');
    return reported ?? (metric(model, ['cost_overrun_ratio', 'cost'], 'mae') == null ? null : metric(model, ['cost_overrun_ratio', 'cost'], 'mae') * 100);
}

function metricCards(model) {
    return [
        { label: 'Health · Macro F1', value: number(healthMacroF1(model)) },
        { label: 'Delay · MAE (días)', value: number(metric(model, ['delay', 'delay_days'], 'mae')) },
        { label: 'Cost · MAE (pp BAC)', value: number(costMaePercentagePoints(model)) },
    ];
}

export function PredictionComparison({ data }) {
    if (!data) return null;
    const entries = [['Academic', data.academic], ['Empirical', data.empirical]];
    const value = (result, key) => result?.prediction?.[key];
    return <section className="surface model-prediction-comparison" aria-labelledby="prediction-comparison-title">
        <div className="section-heading"><div><p className="eyebrow">COMPARACIÓN DE PREDICCIONES</p><h2 id="prediction-comparison-title">Mismo input, dos modelos</h2></div></div>
        <div className="prediction-model-columns">{entries.map(([label, result]) => <div key={label} className="prediction-model-column"><h3>{label}</h3>{result?.prediction ? <dl>
            <div><dt>Health</dt><dd>{value(result, 'health') || 'No disponible'}</dd></div>
            <div><dt>Delay raw</dt><dd>{number(value(result, 'delay_days_raw'))} días</dd></div>
            <div><dt>Cost overrun</dt><dd>{percent(value(result, 'cost_overrun_ratio'))}</dd></div>
            <div><dt>Modelo</dt><dd>{result.model?.version || '—'}</dd></div>
        </dl> : <p role="status">No compatible: {result?.error || 'el input no cubre las features requeridas.'}</p>}</div>)}</div>
        <p className="science-note">{data.comparison?.note || 'Las diferencias no identifican cuál predicción es correcta.'}</p>
    </section>;
}

function ModelCard({ model, activeModel, onSelect }) {
    const isAcademic = model.id === 'academic';
    const values = metricCards(model);
    const featureCount = model.features?.length ?? 0;
    return <article className={`model-card ${model.id}`}>
        <div className="model-card-heading"><div><p className="eyebrow">{isAcademic ? 'SYNTHETIC' : 'REAL DATA'}</p><h3>{model.name}</h3></div><span className={`model-state ${model.status}`}>{statusNames[model.status] || model.status}</span></div>
        <p className="model-version">{model.version}</p>
        <dl className="model-facts"><div><dt>Fuente</dt><dd>{model.dataset_source}</dd></div><div><dt>Proyectos de entrenamiento</dt><dd>{number(model.project_count)}</dd></div><div><dt>Snapshots</dt><dd>{number(model.snapshot_count)}</dd></div><div><dt>Features</dt><dd>{number(featureCount)}</dd></div><div><dt>Targets</dt><dd>{(model.targets || []).join(' · ') || '—'}</dd></div></dl>
        <div className="model-metrics">{values.map(item => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}</div>
        {model.id === 'empirical' && model.status === 'ready' && <p className="model-caveat">No se entrenó Health. Delay/Cost seleccionaron la baseline mediana; su TEST no demuestra ventaja frente a esa baseline.</p>}
        {model.id === 'academic' && <p className="model-caveat">Mendeley sintético externo. Mantiene el comportamiento académico y es el modelo predeterminado.</p>}
        {model.status === 'unavailable' && <p className="model-caveat" role="alert">Empirical model unavailable; Academic model remains active. {model.availability_warning}</p>}
        <div className="model-card-actions"><span className={activeModel === model.id ? 'active-model-label' : 'quiet-label'}>{activeModel === model.id ? 'MODELO ACTIVO' : ' '}</span><button type="button" className={activeModel === model.id ? 'secondary-button' : 'primary-button'} onClick={() => onSelect(model.id)} disabled={model.status !== 'ready' || activeModel === model.id}>{activeModel === model.id ? 'En uso' : 'Usar modelo'}</button></div>
        {model.id === 'empirical' && model.status === 'ready' && <a className="model-report-link" href={`${API}/api/models/empirical/report`}>Ver reporte de entrenamiento</a>}
        <small className="artifact-path">Artifact: {model.artifact_path || '—'}</small>
    </article>;
}

export function ModelsWorkbench({ activeModel, onSelectModel, values, onCompare, comparison, compareLoading }) {
    const [models, setModels] = useState([]);
    const [trainingEnabled, setTrainingEnabled] = useState(false);
    const [job, setJob] = useState(null);
    const [events, setEvents] = useState([]);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [starting, setStarting] = useState(false);
    const [error, setError] = useState('');

    const refreshModels = async () => {
        const response = await fetch(`${API}/api/models`);
        if (!response.ok) throw new Error('No fue posible consultar el registry de modelos.');
        const payload = await response.json();
        setModels(payload.models || []);
        setTrainingEnabled(payload.training_enabled === true);
    };

    useEffect(() => { refreshModels().catch(() => setError('No fue posible cargar el Model Registry.')); }, []);

    useEffect(() => {
        if (!job?.job_id || ['completed', 'failed'].includes(job.status)) return undefined;
        let cancelled = false;
        let timer;
        const poll = async () => {
            try {
                const [statusResponse, logsResponse] = await Promise.all([
                    fetch(`${API}/api/training/${job.job_id}`),
                    fetch(`${API}/api/training/${job.job_id}/logs`),
                ]);
                if (!statusResponse.ok || !logsResponse.ok) throw new Error('No fue posible consultar el job.');
                const status = await statusResponse.json();
                const logs = await logsResponse.json();
                if (cancelled) return;
                setJob(status);
                setEvents(logs.events || []);
                if (['completed', 'failed'].includes(status.status)) {
                    if (status.status === 'completed') await refreshModels();
                    return;
                }
                timer = window.setTimeout(poll, 1200);
            } catch {
                if (!cancelled) setError('Se perdió la consulta del progreso. El backend puede seguir entrenando; vuelve a abrir Models para revisar el job.');
            }
        };
        poll();
        return () => { cancelled = true; window.clearTimeout(timer); };
    }, [job?.job_id, job?.status]);

    const startTraining = async () => {
        setStarting(true);
        setError('');
        try {
            const response = await fetch(`${API}/api/training/empirical`, { method: 'POST' });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || 'No fue posible iniciar el entrenamiento.');
            setJob({ job_id: payload.job_id, status: 'queued', progress_percent: 0, current_step: 'Entrenamiento en cola.' });
            setEvents([{ status: 'queued', message: 'Entrenamiento en cola.' }]);
            setConfirmOpen(false);
        } catch (requestError) {
            setError(requestError.message);
        } finally { setStarting(false); }
    };

    const academic = models.find(model => model.id === 'academic');
    const empirical = models.find(model => model.id === 'empirical');
    const busy = job && !['completed', 'failed'].includes(job.status);
    const comparisonWarning = 'Las métricas de ambos modelos describen dominios, targets y splits propios; no representan una comparación head-to-head.';

    return <div className="models-workbench">
        <section className="models-intro"><div><p className="eyebrow">MODEL REGISTRY</p><h2>Dos líneas, evidencia separada</h2><p>Academic conserva su pipeline original. Empirical usa únicamente proyectos DSLIB y se activa solo por selección manual.</p></div><span className="active-model-banner"><small>MODELO ACTIVO</small><strong>{activeModel === 'empirical' ? `PRUNIN Empirical · ${empirical?.version || ''}` : `PRUNIN Academic · ${academic?.version || ''}`}</strong></span></section>
        {error && <div className="model-error" role="alert">{error}</div>}
        <div className="model-card-grid">{models.map(model => <ModelCard key={model.id} model={model} activeModel={activeModel} onSelect={onSelectModel} />)}</div>
        <section className="model-comparison-table surface" aria-labelledby="model-comparison-title">
            <div className="section-heading"><div><p className="eyebrow">COMPARACIÓN</p><h2 id="model-comparison-title">Alcance y métricas por dominio</h2></div></div>
            <p className="science-note">{comparisonWarning}</p>
            <div className="registry-comparison"><div className="registry-comparison-head"><span>Métrica</span><strong>Academic</strong><strong>Empirical</strong></div>
                <div><span>Origen / población</span><span>{academic?.dataset_source || '—'} · {number(academic?.project_count)} proyectos</span><span>{empirical?.dataset_source || '—'} · {number(empirical?.project_count)} proyectos de entrenamiento</span></div>
                <div><span>Health · Macro F1</span><span>{number(healthMacroF1(academic))}</span><span>No disponible: sin etiqueta Health</span></div>
                <div><span>Delay · MAE</span><span>{number(metric(academic, ['delay_days', 'delay'], 'mae'))} días</span><span>{number(metric(empirical, ['delay'], 'mae'))} días</span></div>
                <div><span>Cost · MAE (pp BAC)</span><span>{number(costMaePercentagePoints(academic))}</span><span>{number(costMaePercentagePoints(empirical))}</span></div>
                <div><span>Early prediction</span><span>Evaluación por cutoffs reportada</span><span>No disponible: {number(empirical?.early_prediction?.delay_candidate_snapshots)} snapshots candidatos, insuficientes</span></div>
            </div>
        </section>
        <section className="training-panel surface" aria-labelledby="training-title">
            <div className="section-heading"><div><p className="eyebrow">TRAINING</p><h2 id="training-title">Entrenamiento empírico</h2></div><span className={`model-state ${trainingEnabled ? 'ready' : 'unavailable'}`}>{trainingEnabled ? 'Habilitado' : 'Deshabilitado'}</span></div>
            <div className="training-controls"><div><strong>DSLIB / PSLIB v3.4</strong><span>Salida versionada en artifacts/ · 151 proyectos por target, según los datos auditados.</span></div><button type="button" className="primary-button" onClick={() => setConfirmOpen(true)} disabled={!trainingEnabled || busy || starting}>{busy ? 'Entrenamiento en curso…' : empirical?.status === 'ready' ? 'Entrenar nueva versión' : 'Entrenar modelo empírico'}</button></div>
            {!trainingEnabled && <p className="quiet-label">Training UI deshabilitada por configuración del backend.</p>}
            {job && <div className="training-job" aria-live="polite"><div className="training-job-heading"><strong>{job.status === 'completed' ? 'ENTRENAMIENTO COMPLETADO' : job.status === 'failed' ? 'ENTRENAMIENTO FALLIDO' : 'ENTRENANDO PRUNIN EMPIRICAL'}</strong><span>{number(job.progress_percent)} %</span></div><progress max="100" value={job.progress_percent || 0} aria-label="Progreso real del entrenamiento" /><p>{job.current_step}</p>
                {job.status === 'completed' && <p className="training-success">Versión {job.result?.version}. Academic permanece activo; la promoción es manual.</p>}
                {job.error && <p className="model-error" role="alert">{job.error}</p>}
                <details className="training-events"><summary>Eventos y detalle técnico</summary><ol>{events.map((event, index) => <li key={`${event.timestamp || ''}-${index}`}><span>{event.status}</span>{event.message}</li>)}</ol></details>
            </div>}
        </section>
        <section className="prediction-compare-controls surface"><div><p className="eyebrow">INPUT ACTUAL</p><h2>Comparar predicciones</h2><p>Ejecuta ambos modelos con el mismo input disponible en Analizar proyecto.</p></div><button type="button" className="secondary-button" onClick={onCompare} disabled={compareLoading}>{compareLoading ? 'Comparando…' : 'Comparar modelos'}</button></section>
        <PredictionComparison data={comparison} />
        {confirmOpen && <div className="confirmation-backdrop"><section className="training-confirmation" role="dialog" aria-modal="true" aria-labelledby="training-confirm-title"><p className="eyebrow">CONFIRMACIÓN</p><h2 id="training-confirm-title">Entrenar PRUNIN Empirical</h2><p>Este proceso entrenará una nueva versión con datos reales de DSLIB y puede consumir CPU y memoria. El modelo académico no será modificado ni activado.</p><dl><div><dt>Dataset</dt><dd>DSLIB / PSLIB v3.4</dd></div><div><dt>Destino</dt><dd>artifacts/[nueva-versión]-empirical</dd></div></dl><div className="confirmation-actions"><button type="button" className="secondary-button" onClick={() => setConfirmOpen(false)} disabled={starting}>Cancelar</button><button type="button" className="primary-button" onClick={startTraining} disabled={starting}>{starting ? 'Iniciando…' : 'Entrenar'}</button></div></section></div>}
    </div>;
}