import { useEffect, useMemo, useRef, useState } from 'react';
import { ProjectForm } from './components/ProjectForm.jsx';
import { ResultHero, DriversPanel, RecommendationCard } from './components/AnalysisPanels.jsx';
import { ScenarioPanel } from './components/ScenarioPanel.jsx';
import { CsvAnalyzer } from './components/CsvAnalyzer.jsx';
import { TechnicalDrawer } from './components/TechnicalDrawer.jsx';

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
    const genaiText = genai
        ? genai.genai_used ? 'IA generativa local activa'
            : !genai.genai_attempted ? 'IA generativa desactivada · respuesta de respaldo'
                : genai.failure_code === 'ollama_timeout' ? 'La IA generativa no respondió a tiempo · respaldo activo'
                    : evidenceFailures.has(genai.failure_code) ? 'Respuesta de IA rechazada por validación de evidencia · respaldo activo'
                        : formatFailures.has(genai.failure_code) ? 'Respuesta de IA inválida · respaldo activo'
                            : 'IA generativa no disponible · respaldo activo'
        : !genaiStatus ? 'Consultando IA generativa…'
            : !genaiStatus.enabled ? 'IA generativa desactivada'
                : genaiStatus.available ? `IA generativa local disponible`
                    : 'IA generativa no disponible';
    return <div className="status-bar" aria-label="Estado de la plataforma">
        <span className={`status-chip ${model ? demo ? 'amber' : 'green' : 'neutral'}`}><i />{model ? demo ? `Modelo demo · ${model.version}` : `Modelo académico · ${model.version}` : 'Cargando modelo'}</span>
        <span className={`status-chip ${apiReady ? 'green' : 'amber'}`}><i />{apiReady ? 'API disponible' : 'API no disponible'}</span>
        <span className={`status-chip ${genai?.genai_used || (!genai && genaiStatus?.available) ? 'green' : genai?.genai_attempted || (genaiStatus?.enabled && !genaiStatus?.available) ? 'amber' : 'neutral'}`}><i />{genaiText}</span>
        <span className={`status-chip ${result?.model?.execution === 'LIVE' ? 'green' : 'neutral'}`}><i />{result?.model?.execution === 'LIVE' ? 'Análisis en vivo' : 'Análisis real al ejecutar'}</span>
    </div>;
}

function AppHeader({ model, apiReady, result, genaiStatus, onTechnical }) {
    return <header className="app-header">
        <div className="header-inner">
            <a className="brand" href="#top" aria-label="PRUNIN AI Core, inicio"><span className="brand-mark">P</span><span><strong>PRUNIN AI Core</strong><small>Predicción temprana de riesgo de proyectos</small></span></a>
            <div className="header-actions"><span className="tagline">Anticipa <i>·</i> Explica <i>·</i> Recomienda <i>·</i> Simula</span>{result && <button type="button" className="evidence-button" onClick={onTechnical}><span aria-hidden="true">⚙</span> Ver evidencia técnica</button>}</div>
        </div>
        <div className="header-inner status-wrap"><StatusBar model={model} apiReady={apiReady} result={result} genaiStatus={genaiStatus} /></div>
    </header>;
}

function PresentationOverview() {
    return <div className="presentation-overview">
        <section className="presentation-hero" aria-labelledby="overview-title">
            <div className="presentation-copy">
                <p className="eyebrow">PRUNIN · ALERTA TEMPRANA PARA PROYECTOS</p>
                <h1 id="overview-title">¿Podemos detectar un proyecto en riesgo antes de que sea demasiado tarde?</h1>
                <p className="hero-lead">PRUNIN analiza señales de avance, cronograma y costo para ayudar al responsable del proyecto a decidir <strong>dónde intervenir antes del cierre</strong>.</p>
                <div className="original-promise"><span>Promesa original</span><strong>Detectar tempranamente ≥75 % de los proyectos críticos o en alto riesgo.</strong></div>
            </div>
            <aside className="research-result" aria-label="Resultado principal del experimento">
                <span>Resultado experimental</span>
                <strong>75,9 %</strong>
                <p>de todos los proyectos de prueba que finalmente quedaron <b>en riesgo o críticos</b> ya estaban detectados al <b>60 % de avance</b>.</p>
                <div><b>96 %</b> de los proyectos de prueba podían evaluarse <i>·</i> <b>82,45 %</b> detección final</div>
            </aside>
        </section>

        <section className="plain-flow" aria-label="Cómo funciona PRUNIN">
            <article><span>1</span><div><strong>Observa</strong><p>Avance, cumplimiento del cronograma, comportamiento del costo, duración y presupuesto.</p></div></article>
            <article><span>2</span><div><strong>Detecta</strong><p>Activa una alerta cuando el nivel de riesgo queda <b>En riesgo</b> o <b>Crítico</b>.</p></div></article>
            <article><span>3</span><div><strong>Explica</strong><p>Muestra señales que empujan el riesgo y propone acciones revisables.</p></div></article>
            <article><span>4</span><div><strong>Simula</strong><p>Permite explorar qué cambia si mejoran indicadores del proyecto.</p></div></article>
        </section>

        <section className="reading-guide" aria-label="Cómo leer los resultados">
            <article><span className="guide-dot risk" /><div><strong>Alerta temprana</strong><p>Responde: <b>¿requiere atención ahora?</b></p></div></article>
            <article><span className="guide-dot health" /><div><strong>Nivel de riesgo</strong><p>Responde: <b>¿qué tan severa es la condición?</b></p></div></article>
            <article><span className="guide-dot estimate" /><div><strong>Retraso + sobrecosto</strong><p>Estiman la posible magnitud de las desviaciones.</p></div></article>
        </section>
        <details className="plain-glossary">
            <summary>¿Qué significan los términos que aparecen en la demo?</summary>
            <div className="glossary-grid">
                <div><strong>Alerta temprana</strong><p>Indica si el proyecto necesita atención.</p></div>
                <div><strong>Nivel de riesgo</strong><p>Clasifica el proyecto como Saludable, En riesgo o Crítico.</p></div>
                <div><strong>SPI</strong><p>Mide cumplimiento del cronograma. Menor que 1 indica atraso frente al plan.</p></div>
                <div><strong>CPI</strong><p>Mide eficiencia del costo. Menor que 1 indica presión de costo.</p></div>
                <div><strong>Posible retraso</strong><p>Estimación de días de desviación del cronograma.</p></div>
                <div><strong>Posible sobrecosto</strong><p>Estimación del aumento del costo frente al presupuesto.</p></div>
            </div>
        </details>
        <p className="experiment-scope">Resultados de una evaluación académica con datos simulados externos publicados. No equivale a una validación empresarial ni a uso en producción.</p>
    </div>;
}

function StepNav({ result, mode }) {
    if (mode !== 'project') return null;
    const steps = [['project', '1 · Qué está pasando'], ['result', '2 · ¿Hay alerta?'], ['explanation', '3 · ¿Por qué?'], ['recommendations', '4 · ¿Qué hacer?'], ['simulation', '5 · ¿Qué pasa si…?']];
    return <nav className="step-nav" aria-label="Etapas del análisis">{steps.map(([id, label], index) => <a key={id} className={!result && index > 0 ? 'disabled-step' : ''} href={result || index === 0 ? `#${id}` : undefined} aria-disabled={!result && index > 0}>{index > 0 && <span aria-hidden="true">›</span>}{label}</a>)}</nav>;
}

function friendlyError(error) {
    if (error?.message) return error.message;
    return 'No fue posible conectar con PRUNIN. Verifica que la API esté disponible.';
}

export default function Experience() {
    const [schema, setSchema] = useState(null);
    const [values, setValues] = useState({});
    const [activePreset, setActivePreset] = useState('at_risk');
    const [mode, setMode] = useState('project');
    const [result, setResult] = useState(null);
    const [comparison, setComparison] = useState(null);
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
        ]).then(([data, ready, genai]) => {
            if (!active) return;
            setSchema(data);
            setValues({ ...data.presets.at_risk });
            setApiReady(ready);
            setGenaiStatus(genai);
        }).catch(() => { if (active) setError('No fue posible conectar con PRUNIN. Verifica que la API esté disponible.'); });
        return () => { active = false; };
    }, []);

    const trainedFeatures = schema?.model?.trained_features || schema?.ml_features || [];
    const minimumCoverage = Number(schema?.model?.minimum_feature_coverage ?? 0.6);
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
            const response = await fetch(`${API}/api/predict`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
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
            const response = await fetch(`${API}/api/what-if`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseline: values, scenario }) });
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
            const response = await fetch(`${API}/api/predict-csv`, { method: 'POST', body: form });
            setCsvResults(await responseJson(response));
        } catch (requestError) {
            setError(friendlyError(requestError));
            setTechnicalError(requestError.technical || requestError.message || String(requestError));
        } finally { setCsvLoading(false); }
    };

    if (!schema) return <div className="boot-screen"><span className="brand-mark">P</span><h1>PRUNIN AI Core</h1><p role={error ? 'alert' : 'status'}>{error || 'Conectando con la API…'}</p></div>;
    const loadingMessages = ['Evaluando el nivel de riesgo…', 'Identificando las señales más influyentes…', genaiStatus?.enabled && genaiStatus?.available ? 'Generando una explicación con IA…' : 'Preparando una recomendación de respaldo…'];

    return <div id="top" className="app-shell">
        <AppHeader model={schema.model} apiReady={apiReady} result={result} genaiStatus={genaiStatus} onTechnical={() => setDrawerOpen(true)} />
        <main className="page-content">
            {schema.model.mode === 'synthetic_demo' && <aside className="mode-notice" role="note">Modelo de demostración con datos sintéticos. La versión académica se indicará aquí cuando esté cargada.</aside>}
            <PresentationOverview />
            <div className="mode-switch" role="tablist" aria-label="Modo de análisis">
                <button type="button" role="tab" aria-selected={mode === 'project'} className={mode === 'project' ? 'active' : ''} onClick={() => { setMode('project'); setError(''); }}>Analizar proyecto</button>
                <button type="button" role="tab" aria-selected={mode === 'csv'} className={mode === 'csv' ? 'active' : ''} onClick={() => { setMode('csv'); setError(''); }}>Analizar CSV</button>
            </div>
            <StepNav result={result} mode={mode} />
            {error && mode === 'project' && <div className="error-banner" role="alert"><span>{error}</span><button type="button" aria-label="Cerrar mensaje" onClick={() => setError('')}>×</button></div>}

            {mode === 'project' ? <>
                <ProjectForm schema={schema} values={values} onChange={change} onAnalyze={analyze} loading={loading} activePreset={activePreset} onPreset={choosePreset} coverage={coverage} />
                {loading && <div className="analysis-loading" role="status" aria-live="polite"><span className="spinner large" /><div><strong>{loadingMessages[loadingStage]}</strong><small>{genaiStatus?.enabled && genaiStatus?.available ? 'La explicación con IA puede tardar unos segundos.' : 'El sistema ejecuta el análisis y prepara una respuesta de respaldo.'}</small></div></div>}
                <div ref={resultRef}><ResultHero result={result} schema={schema} /></div>
                {result && <>
                    <DriversPanel drivers={result.drivers} fields={schema.fields} />
                    <RecommendationCard data={result.recommendations} fields={schema.fields} />
                    <ScenarioPanel schema={schema} values={values} onRun={simulate} loading={simulationLoading} comparison={comparison} />
                    <div className="technical-action"><button type="button" className="evidence-button large-evidence" onClick={() => setDrawerOpen(true)}><span aria-hidden="true">⚙</span> Ver evidencia técnica</button></div>
                </>}
            </> : <CsvAnalyzer onAnalyze={analyzeCsv} loading={csvLoading} results={csvResults} error={error} />}

            <footer className="app-footer"><strong>PRUNIN AI Core</strong><span>Proyecto académico · Análisis trazable · Las señales explican el modelo, no prueban causas</span></footer>
        </main>
        <TechnicalDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} result={result} model={schema.model} schema={schema} technicalError={technicalError} genaiStatus={genaiStatus} />
    </div>;
}