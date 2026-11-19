import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || '';
const pct = value => value == null ? '—' : `${(Number(value) * 100).toLocaleString('es-CO', { maximumFractionDigits: 1 })} %`;
const secs = value => value == null ? '—' : `${(Number(value) / 1000).toLocaleString('es-CO', { maximumFractionDigits: 1 })} s`;
const CRITERIA = { grounding: 'Grounding', actionability: 'Accionabilidad', json_compliance: 'Cumplimiento JSON', latency: 'Latencia', robustness: 'Robustez', repeatability: 'Repetibilidad' };
const QUALITY = [
    ['accepted_rate', 'Respuestas aceptadas'],
    ['json_valid_rate', 'JSON válido'],
    ['schema_valid_rate', 'Esquema válido'],
    ['grounded_rate', 'Grounding'],
    ['actionability_rate', 'Accionabilidad'],
    ['follow_up_verifiable_rate', 'Seguimiento verificable'],
];
const RELIABILITY = [
    ['unsupported_numeric_claim_rate', 'Cifras no soportadas'],
    ['contradiction_rate', 'Contradicciones'],
    ['operational_error_rate', 'Fallos operativos'],
];

function Bars({ models, rows, format = pct, max = 1 }) {
    return <div className="mc-bars">
        {rows.map(([key, label]) =>         <div className="mc-bar-row" key={label}>
            <span className="mc-bar-label">{label}</span>
            <div className="mc-bar-group">
                {models.map(([id, model], index) => {
                    const value = typeof key === 'function' ? key(model) : model.metrics?.[key];
                    const width = value == null ? 0 : Math.min(100, (Number(value) / max) * 100);
                    return <div className={`mc-bar mc-bar-${index}`} key={id} title={`${model.display_name}: ${format(value)}`}>
                        <i style={{ width: `${width}%` }} /><b>{model.display_name}</b><em>{format(value)}</em>
                    </div>;
                })}
            </div>
        </div>)}
    </div>;
}

export function ModelComparison() {
    const [data, setData] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        let active = true;
        // Read-only: only fetches results that were generated beforehand by the local command.
        fetch(`${API}/api/genai-comparison`)
            .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
            .then(body => { if (active) setData(body); })
            .catch(() => { if (active) setFailed(true); });
        return () => { active = false; };
    }, []);

    const heading = <div className="section-heading"><div><p className="eyebrow">EVIDENCIA · IA GENERATIVA</p><h2 id="model-comparison-title">Comparación de modelos IA</h2></div></div>;
    if (failed || !data) {
        return <section className="surface content-section model-comparison" id="model-comparison" aria-labelledby="model-comparison-title">
            {heading}<p role="status">{failed ? 'No fue posible consultar la comparación.' : 'Cargando comparación…'}</p>
        </section>;
    }
    if (data.status === 'not_available') {
        return <section className="surface content-section model-comparison" id="model-comparison" aria-labelledby="model-comparison-title">
            {heading}<p>Aún no hay una comparación Qwen3 8B vs. GPT-OSS 20B generada. El experimento se ejecuta solo con el comando local autorizado; esta vista no lanza inferencias.</p>
        </section>;
    }

    const models = Object.entries(data.models || {});
    const decision = data.decision || {};
    const recommended = data.valid && decision.defensible && decision.winner ? data.models[decision.winner]?.display_name : null;
    const latencyMax = Math.max(1, ...models.map(([, model]) => Number(model.metrics?.latency_ms_p95) || 0));

    return <section className="surface content-section model-comparison" id="model-comparison" aria-labelledby="model-comparison-title">
        {heading}
        <p className="mc-intro">{models.map(([, model]) => model.display_name).join(' vs. ')} · mismos {data.cases} casos TEST · {data.repeat_cases} casos × {data.repeats} repeticiones · {data.hardware?.chip || 'equipo local'} {data.hardware?.memory_gb ? `${data.hardware.memory_gb} GB` : ''} · Ollama {data.ollama_version}</p>
        {!data.valid && <div className="mc-warning" role="alert"><strong>Resultados no validados.</strong> {(data.errors || []).join(' ')} No se muestra recomendación.</div>}

        <div className="mc-grid">
            <div className="mc-card">
                <h3>Calidad y estructura</h3>
                <Bars models={models} rows={QUALITY} />
            </div>
            <div className="mc-card">
                <h3>Tiempos de respuesta</h3>
                <Bars models={models} rows={[['latency_ms_median', 'Mediana'], ['latency_ms_mean', 'Media'], ['latency_ms_p95', 'Percentil 95']]} format={secs} max={latencyMax} />
                <h3>Confiabilidad (menor es mejor)</h3>
                <Bars models={models} rows={RELIABILITY} />
                <h3>Repetibilidad</h3>
                <Bars models={models} rows={[[model => model.metrics?.repeatability?.consistent_case_rate, 'Casos consistentes']]} />
            </div>
        </div>

        <div className="mc-card">
            <h3>Matriz de decisión</h3>
            <div className="mc-table-wrap">
                <table className="mc-table">
                    <thead><tr><th>Criterio</th><th>Peso</th>{models.map(([id, model]) => <th key={id}>{model.display_name}</th>)}</tr></thead>
                    <tbody>
                        {Object.entries(decision.weights || {}).map(([key, weight]) => <tr key={key}>
                            <td>{CRITERIA[key] || key}</td><td>{pct(weight)}</td>
                            {models.map(([id]) => <td key={id}>{decision.scores?.[id]?.[key] == null ? '—' : Number(decision.scores[id][key]).toFixed(3)}</td>)}
                        </tr>)}
                        <tr className="mc-total"><td>Total ponderado</td><td>100 %</td>{models.map(([id]) => <td key={id}>{decision.totals?.[id] == null ? '—' : Number(decision.totals[id]).toFixed(3)}</td>)}</tr>
                    </tbody>
                </table>
            </div>
            <div className={`mc-verdict ${recommended ? 'has-winner' : ''}`}>
                <strong>{recommended ? `Modelo recomendado: ${recommended}` : 'Sin modelo recomendado: la evidencia no permite una elección defendible'}</strong>
                <ul>{(decision.reasons || []).map(reason => <li key={reason}>{reason}</li>)}</ul>
                {decision.significance && <p>McNemar exacto sobre aceptación pareada: p = {Number(decision.significance.p_value).toFixed(4)}.</p>}
            </div>
        </div>
        <p className="mc-note">Indicadores automáticos del validador de PRUNIN; no incluyen evaluación semántica humana. El modelo configurado en la aplicación no cambia automáticamente.</p>
    </section>;
}
