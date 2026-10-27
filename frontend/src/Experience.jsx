import { useEffect, useMemo, useRef, useState } from 'react';
import { ProjectForm } from './components/ProjectForm.jsx';
import { ResultHero, DriversPanel, RecommendationCard } from './components/AnalysisPanels.jsx';
import { ScenarioPanel } from './components/ScenarioPanel.jsx';
import { CsvAnalyzer } from './components/CsvAnalyzer.jsx';
import { TechnicalDrawer } from './components/TechnicalDrawer.jsx';
import { ModelsWorkbench, PredictionComparison } from './components/ModelsWorkbench.jsx';

const API = import.meta.env.VITE_API_URL || '';

async function responseJson(response) {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = typeof payload.detail === 'string' ? payload.detail : 'La solicitud no pudo completarse.';
        const message = /cobertura insuficiente/i.test(detail)
            ? 'Datos incompletos: la cobertura está por debajo del mínimo para analizar. Completa más variables del proyecto.'
            : /csv supera 5 mb/i.test(detail)
                ? 'El archivo supera el límite de 5 MB.'
                : /100 filas|maximo 100/i.test(detail)
                    ? 'El archivo supera el máximo de 100 filas.'
                    : 'No fue posible completar el análisis. Revisa los datos e inténtalo de nuevo.';
        const error = new Error(message);
        error.technical = detail;
        throw error;
    }
    return payload;
}

function StatusBar({ model, apiReady, result, genaiStatus }) {
    const demo = model?.mode === 'synthetic_demo';
    const genai = result?.recommendations;
    const evidenceFailures = new Set(['unknown_evidence_feature', 'unsupported_numeric_claim', 'empty_recommendations_with_risk_drivers', 'grounding_validation_failed']);
    const formatFailures = new Set(['invalid_json', 'invalid_schema']);
    const empiricalUnavailable = genai?.engine === 'not_available_for_empirical_targets';
    const genaiText = empiricalUnavailable ? 'Recomendaciones no disponibles · sin Health empírico' : genai
        ? genai.genai_used ? 'Qwen3 8B · IA generativa'
            : !genai.genai_attempted ? 'IA generativa desactivada · respaldo'
                : genai.failure_code === 'ollama_timeout' ? 'Qwen3 no respondió a tiempo · respaldo activo'
                    : evidenceFailures.has(genai.failure_code) ? 'Respuesta Qwen3 rechazada por grounding · respaldo activo'
                        : formatFailures.has(genai.failure_code) ? 'Formato Qwen3 inválido · respaldo activo'
                            : 'Qwen3 no disponible · respaldo activo'
        : !genaiStatus ? 'Consultando Qwen3…'
            : !genaiStatus.enabled ? 'IA generativa desactivada'
                : genaiStatus.available ? `Qwen3 conectado · ${genaiStatus.model}`
                    : 'Qwen3 no disponible';
    return <div className="status-bar" aria-label="Estado de la plataforma">
        <span className={`status-chip ${model ? demo ? 'amber' : 'green' : 'neutral'}`}><i />{model ? demo ? `Modelo demo · ${model.version}` : model.id === 'empirical' ? `Modelo empírico · ${model.version}` : `Modelo académico · ${model.version}` : 'Cargando modelo'}</span>
        <span className={`status-chip ${apiReady ? 'green' : 'amber'}`}><i />{apiReady ? 'API disponible' : 'API no disponible'}</span>
        <span className={`status-chip ${genai?.genai_used || (!genai && genaiStatus?.available) ? 'green' : genai?.genai_attempted || (genaiStatus?.enabled && !genaiStatus?.available) ? 'amber' : 'neutral'}`}><i />{genaiText}</span>
        <span className={`status-chip ${result?.model?.execution === 'LIVE' ? 'green' : 'neutral'}`}><i />{result?.model?.execution === 'LIVE' ? 'Ejecución LIVE' : 'Inferencia real al analizar'}</span>
    </div>;
}

function AppHeader({ model, apiReady, result, genaiStatus, onTechnical }) {
    return <header className="app-header">
        <div className="header-inner">
            <a className="brand" href="#top" aria-label="PRUNIN AI Core, inicio"><span className="brand-mark">P</span><span><strong>PRUNIN AI Core</strong><small>Predicción temprana de riesgo de proyectos</small></span></a>
            <div className="header-actions"><span className="tagline">Predice <i>·</i> Explica <i>·</i> Recomienda <i>·</i> Simula</span>{result && <button type="button" className="evidence-button" onClick={onTechnical}><span aria-hidden="true">⚙</span> Ver evidencia técnica</button>}</div>
        </div>
        <div className="header-inner status-wrap"><StatusBar model={model} apiReady={apiReady} result={result} genaiStatus={genaiStatus} /></div>
    </header>;
}

function StepNav({ result, mode }) {
    if (mode !== 'project') return null;
    const steps = [['project', 'Proyecto'], ['result', 'Resultado'], ['explanation', 'Explicación'], ['recommendations', 'Acciones'], ['simulation', 'Simulación']];
    return <nav className="step-nav" aria-label="Etapas del análisis">{steps.map(([id, label], index) => <a key={id} className={!result && index > 0 ? 'disabled-step' : ''} href={result || index === 0 ? `#${id}` : undefined} aria-disabled={!result && index > 0}>{index > 0 && <span aria-hidden="true">›</span>}{label}</a>)}</nav>;
}

function friendlyError(error) {
    if (error?.message) return error.message;
    return 'No fue posible conectar con PRUNIN. Verifica que la API esté disponible.';
}

export default function Experience() {
    const [schema, setSchema] = useState(null);
    const [activeModelSchema, setActiveModelSchema] = useState(null);
    const [page, setPage] = useState('analysis');
    const [activeModel, setActiveModel] = useState('academic');
    const [modelRecords, setModelRecords] = useState([]);
    const [values, setValues] = useState({});
    const [activePreset, setActivePreset] = useState('at_risk');
    const [mode, setMode] = useState('project');
    const [result, setResult] = useState(null);
    const [comparison, setComparison] = useState(null);
    const [modelComparison, setModelComparison] = useState(null);
    const [modelCompareLoading, setModelCompareLoading] = useState(false);
    const [csvResults, setCsvResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [simulationLoading, setSimulationLoading] = useState(false);
    const [csvLoading, setCsvLoading] = useState(false);
    const [error, setError] = useState('');
    const [technicalError, setTechnicalError] = useState('');
    const [apiReady, setApiReady] = useState(false);
    const [genaiStatus, setGenaiStatus] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [loadingStage, setLoadingStage] = useState(0);
    const resultRef = useRef(null);

    useEffect(() => {
        let active = true;
        Promise.all([
            fetch(`${API}/api/schema`).then(response => responseJson(response)),
            fetch(`${API}/api/ready`).then(response => response.ok).catch(() => false),
            fetch(`${API}/api/genai-status`).then(response => response.ok ? response.json() : null).catch(() => null),
            fetch(`${API}/api/models`).then(response => response.ok ? response.json() : null).catch(() => null),
        ]).then(([data, ready, genai, catalog]) => {
            if (!active) return;
            setSchema(data);
            setValues({ ...data.presets.at_risk });
            setApiReady(ready);
            setGenaiStatus(genai);
            if (catalog) {
                setModelRecords(catalog.models || []);
                setActiveModel(catalog.active_model || 'academic');
            }
        }).catch(() => { if (active) setError('No fue posible conectar con PRUNIN. Verifica que la API esté disponible.'); });
        return () => { active = false; };
    }, []);

    useEffect(() => {
        if (activeModel === 'academic') {
            setActiveModelSchema(null);
            return undefined;
        }
        let cancelled = false;
        fetch(`${API}/api/models/${activeModel}/schema`)
            .then(response => responseJson(response))
            .then(data => { if (!cancelled) setActiveModelSchema(data); })
            .catch(requestError => { if (!cancelled) setError(friendlyError(requestError)); });
        return () => { cancelled = true; };
    }, [activeModel]);

    const activeRecord = modelRecords.find(model => model.id === activeModel);
    const modelQuery = activeModel === 'academic' ? '' : `?model_id=${activeModel}`;
    const empiricalInputFields = Object.keys(activeModelSchema?.input_adapter || {});
    const activeFields = activeModel === 'empirical'
        ? schema?.fields.filter(field => empiricalInputFields.includes(field.name) || field.usage === 'team_health').map(field => empiricalInputFields.includes(field.name) ? ({ ...field, usage: 'ml_feature', trained: true, affects_ml_prediction: true }) : field)
        : schema?.fields;
    const empiricalWhatIfFields = [...empiricalInputFields, ...(schema?.team_health_features || [])];
    const activeMlFeatures = activeModel === 'empirical' ? empiricalInputFields : schema?.ml_features;
    const activeSchema = schema ? {
        ...schema,
        fields: activeFields,
        ml_features: activeMlFeatures,
        team_health_features: schema.team_health_features,
        what_if_fields: activeModel === 'empirical' ? empiricalWhatIfFields : schema.what_if_fields,
        model: {
            ...schema.model,
            id: activeModel,
            version: activeRecord?.version || schema.model.version,
            mode: activeModel === 'empirical' ? 'empirical_real_data' : schema.model.mode,
            dataset_source: activeRecord?.dataset_source || schema.model.dataset_source,
            dataset_type: activeModel === 'empirical' ? 'empirical_real' : schema.model.dataset_type,
            trained_features: activeMlFeatures,
            health_available: activeModel !== 'empirical',
        },
    } : null;
    const trainedFeatures = activeSchema?.model?.trained_features || activeSchema?.ml_features || [];
    const minimumCoverage = activeModel === 'empirical' ? 1 : Number(activeSchema?.model?.minimum_feature_coverage ?? 0.6);
    const coverage = useMemo(() => {
        const missing = trainedFeatures.filter(name => values[name] == null || values[name] === '').length;
        return { missing, minimum: minimumCoverage, ratio: trainedFeatures.length ? (trainedFeatures.length - missing) / trainedFeatures.length : 1 };
    }, [trainedFeatures, minimumCoverage, values]);

    const change = (name, value) => { setValues(current => ({ ...current, [name]: value })); setActivePreset(null); setError(''); };
    const choosePreset = name => {
        setValues({ ...schema.presets[name] });
        setActivePreset(name);
        setResult(null);
        setComparison(null);
        setError('');
    };

    const analyze = async () => {
        if (loading || coverage.ratio < coverage.minimum) return;
        setLoading(true);
        setLoadingStage(0);
        setError('');
        setTechnicalError('');
        setResult(null);
        const stageOne = window.setTimeout(() => setLoadingStage(1), 700);
        const stageTwo = window.setTimeout(() => setLoadingStage(2), 1700);
        try {
            const response = await fetch(`${API}/api/predict${modelQuery}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
            const data = await responseJson(response);
            setResult(data);
            setComparison(null);
            window.requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
        } catch (requestError) {
            setError(friendlyError(requestError));
            setTechnicalError(requestError.technical || requestError.message || String(requestError));
        } finally {
            window.clearTimeout(stageOne);
            window.clearTimeout(stageTwo);
            setLoading(false);
            setLoadingStage(0);
        }
    };

    const simulate = async scenario => {
        setSimulationLoading(true);
        setError('');
        setTechnicalError('');
        try {
            const response = await fetch(`${API}/api/what-if${modelQuery}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseline: values, scenario }) });
            const data = await responseJson(response);
            setComparison(data);
            window.requestAnimationFrame(() => document.getElementById('scenario-comparison')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }));
        } catch (requestError) {
            setError(friendlyError(requestError));
            setTechnicalError(requestError.technical || requestError.message || String(requestError));
        } finally { setSimulationLoading(false); }
    };

    const analyzeCsv = async (file, selectionError) => {
        if (selectionError) { setError(selectionError); return; }
        if (!file) return;
        setCsvLoading(true);
        setError('');
        setTechnicalError('');
        try {
            const form = new FormData();
            form.append('file', file);
            const response = await fetch(`${API}/api/predict-csv${modelQuery}`, { method: 'POST', body: form });
            setCsvResults(await responseJson(response));
        } catch (requestError) {
            setError(friendlyError(requestError));
            setTechnicalError(requestError.technical || requestError.message || String(requestError));
        } finally { setCsvLoading(false); }
    };

    const compareModels = async () => {
        setModelCompareLoading(true);
        setError('');
        try {
            const response = await fetch(`${API}/api/compare-models`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
            setModelComparison(await responseJson(response));
        } catch (requestError) {
            setError(friendlyError(requestError));
        } finally { setModelCompareLoading(false); }
    };

    const changeActiveModel = async modelId => {
        const response = await fetch(`${API}/api/models/select`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_id: modelId }) });
        const payload = await responseJson(response);
        setActiveModel(payload.active_model);
        setResult(null);
        setComparison(null);
        setModelComparison(null);
        setError('');
        const catalogResponse = await fetch(`${API}/api/models`);
        if (catalogResponse.ok) setModelRecords((await catalogResponse.json()).models || []);
    };

    if (!schema) return <div className="boot-screen"><span className="brand-mark">P</span><h1>PRUNIN AI Core</h1><p role={error ? 'alert' : 'status'}>{error || 'Conectando con la API…'}</p></div>;
    const loadingMessages = ['Calculando predicciones ML…', 'Evaluando drivers locales…', genaiStatus?.enabled && genaiStatus?.available ? 'Generando recomendación con Qwen3…' : 'Preparando recomendación de respaldo…'];

    return <div id="top" className="app-shell">
        <AppHeader model={activeSchema.model} apiReady={apiReady} result={result} genaiStatus={genaiStatus} onTechnical={() => setDrawerOpen(true)} />
        <main className="page-content">
            {activeSchema.model.mode === 'synthetic_demo' && <aside className="mode-notice" role="note">Modelo de demostración con datos sintéticos. La versión académica se indicará aquí cuando esté cargada.</aside>}
            <section className="intro-block"><div><p className="eyebrow">PRUNIN · PLAYGROUND ACADÉMICO</p><h1>Una lectura clara del riesgo del proyecto.</h1><p>Analiza el resultado, comprende las señales y explora un escenario alternativo.</p></div></section>
            <nav className="main-navigation" role="tablist" aria-label="Secciones principales">
                <button type="button" role="tab" aria-selected={page === 'analysis'} className={page === 'analysis' ? 'active' : ''} onClick={() => setPage('analysis')}>Análisis</button>
                <button type="button" role="tab" aria-selected={page === 'models'} className={page === 'models' ? 'active' : ''} onClick={() => setPage('models')}>Models</button>
            </nav>
            {page === 'models' ? <ModelsWorkbench activeModel={activeModel} onSelectModel={changeActiveModel} values={values} onCompare={compareModels} comparison={modelComparison} compareLoading={modelCompareLoading} /> : <>
                <div className="mode-switch" role="tablist" aria-label="Modo de análisis">
                    <button type="button" role="tab" aria-selected={mode === 'project'} className={mode === 'project' ? 'active' : ''} onClick={() => { setMode('project'); setError(''); }}>Analizar proyecto</button>
                    <button type="button" role="tab" aria-selected={mode === 'csv'} className={mode === 'csv' ? 'active' : ''} onClick={() => { setMode('csv'); setError(''); }}>Analizar CSV</button>
                </div>
                <StepNav result={result} mode={mode} />
                {error && mode === 'project' && <div className="error-banner" role="alert"><span>{error}</span><button type="button" aria-label="Cerrar mensaje" onClick={() => setError('')}>×</button></div>}

                {mode === 'project' ? <>
                    <ProjectForm schema={activeSchema} values={values} onChange={change} onAnalyze={analyze} onCompare={compareModels} compareLoading={modelCompareLoading} loading={loading} activePreset={activePreset} onPreset={choosePreset} coverage={coverage} />
                    <PredictionComparison data={modelComparison} />
                    {loading && <div className="analysis-loading" role="status" aria-live="polite"><span className="spinner large" /><div><strong>{loadingMessages[loadingStage]}</strong><small>{genaiStatus?.enabled && genaiStatus?.available ? 'La generación local puede tardar hasta el timeout configurado.' : 'La API ejecuta la inferencia real y prepara el motor de respaldo.'}</small></div></div>}
                    <div ref={resultRef}><ResultHero result={result} schema={activeSchema} /></div>
                    {result && <>
                        <DriversPanel drivers={result.drivers} fields={activeSchema.fields} unavailable={result.model.id === 'empirical'} />
                        <RecommendationCard data={result.recommendations} fields={activeSchema.fields} />
                        <ScenarioPanel schema={activeSchema} values={values} onRun={simulate} loading={simulationLoading} comparison={comparison} />
                        <div className="technical-action"><button type="button" className="evidence-button large-evidence" onClick={() => setDrawerOpen(true)}><span aria-hidden="true">⚙</span> Ver evidencia técnica</button></div>
                    </>}
                </> : <CsvAnalyzer modelId={activeModel} onAnalyze={analyzeCsv} loading={csvLoading} results={csvResults} error={error} />}
            </>}

            <footer className="app-footer"><strong>PRUNIN AI Core</strong><span>Proyecto académico · Inferencia trazable · Sensibilidad no causal</span></footer>
        </main>
        <TechnicalDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} result={result} model={activeSchema.model} schema={activeSchema} technicalError={technicalError} genaiStatus={genaiStatus} />
    </div>;
}