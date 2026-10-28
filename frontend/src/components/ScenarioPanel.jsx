import { useEffect, useMemo, useState } from 'react';
import { Field } from './fields.jsx';

const healthLabels = { healthy: 'Saludable', at_risk: 'En riesgo', critical: 'Crítico' };
const fmtPct = value => value == null ? '—' : `${(Number(value) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
const fmtPp = value => value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${(Number(value) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} pp`;
const fmtNumber = value => value == null ? '—' : Number(value).toLocaleString('es-CO', { maximumFractionDigits: 1 });

export function ScenarioPanel({ schema, values, onRun, loading, comparison }) {
    const allowed = useMemo(() => schema.fields.filter(field => schema.what_if_fields.includes(field.name) && field.usage !== 'not_used'), [schema]);
    const initial = ['spi', 'cpi'].filter(name => allowed.some(field => field.name === name));
    const [selected, setSelected] = useState(initial);
    const [scenario, setScenario] = useState({ ...values });
    const [candidate, setCandidate] = useState('');
    useEffect(() => setScenario({ ...values }), [values]);
    const available = allowed.filter(field => !selected.includes(field.name));
    const update = (name, value) => setScenario(current => ({ ...current, [name]: value }));
    const addField = () => {
        if (!candidate || selected.includes(candidate)) return;
        setSelected(current => [...current, candidate]);
        setCandidate('');
    };
    const removeField = name => setSelected(current => current.filter(item => item !== name));
    const run = () => onRun({ ...values, ...Object.fromEntries(selected.map(name => [name, scenario[name]])) });
    const selectedFields = selected.map(name => allowed.find(field => field.name === name)).filter(Boolean);
    const mlFields = selectedFields.filter(field => field.usage === 'ml_feature');
    const teamFields = selectedFields.filter(field => field.usage === 'team_health');
    return <section className="surface content-section scenario-section" id="simulation" aria-labelledby="simulation-title">
        <div className="section-heading"><div><span className="step-number">5</span><div><p className="eyebrow">SIMULACIÓN</p><h2 id="simulation-title">Simula una mejora</h2></div></div></div>
        <p className="section-subtitle">Compara el proyecto actual con un escenario alternativo. El resto de variables conserva sus valores actuales.</p>
        <div className="scenario-toolbar"><label htmlFor="scenario-add">Agregar variable al escenario</label><select id="scenario-add" value={candidate} onChange={event => setCandidate(event.target.value)}><option value="">Seleccionar variable</option>{available.map(field => <option key={field.name} value={field.name}>{field.label}</option>)}</select><button type="button" className="secondary-button" onClick={addField} disabled={!candidate}>Agregar</button></div>
        {mlFields.length > 0 && <fieldset className="scenario-fields"><legend>Variables del modelo</legend><div className="form-grid">{mlFields.map(field => <div className="scenario-field" key={field.name}><button type="button" className="remove-scenario-field" aria-label={`Quitar ${field.label} del escenario`} onClick={() => removeField(field.name)}>×</button><Field spec={field} value={scenario[field.name]} onChange={update} idPrefix="scenario" /></div>)}</div></fieldset>}
        {teamFields.length > 0 && <fieldset className="scenario-fields operational-fields"><legend>Señales operativas · Team Health</legend><div className="form-grid">{teamFields.map(field => <div className="scenario-field" key={field.name}><button type="button" className="remove-scenario-field" aria-label={`Quitar ${field.label} del escenario`} onClick={() => removeField(field.name)}>×</button><Field spec={field} value={scenario[field.name]} onChange={update} idPrefix="scenario" /></div>)}</div></fieldset>}
        <div className="scenario-actions"><button type="button" className="text-button" onClick={() => setScenario({ ...values })}>Restablecer escenario</button><button type="button" className="primary-button" onClick={run} disabled={loading || selected.length === 0}>{loading ? <><span className="spinner" /> Simulando baseline y escenario…</> : 'Simular escenario'}</button></div>
        {loading && <p className="loading-note" role="status">El backend compara las dos inferencias; puede tardar unos segundos.</p>}
        {comparison && <ScenarioComparison data={comparison} />}
    </section>;
}

function ScenarioComparison({ data }) {
    const baseline = data.baseline.prediction;
    const scenario = data.scenario.prediction;
    const delta = data.delta;
    return <div className="scenario-comparison" id="scenario-comparison" aria-live="polite"><h3>Antes <span aria-hidden="true">→</span> Escenario</h3>
        <div className="comparison-table"><div className="comparison-head"><span>Indicador</span><span>Antes</span><span>Escenario</span><span>Diferencia</span></div>
            <ComparisonRow label="Health ML" before={healthLabels[baseline.health] || baseline.health} after={healthLabels[scenario.health] || scenario.health} />
            <ComparisonRow label="Riesgo combinado" before={fmtPct(baseline.fused_risk_score)} after={fmtPct(scenario.fused_risk_score)} delta={fmtPp(delta.risk_score)} favorable={delta.risk_score <= 0} />
            <ComparisonRow label="Retraso estimado" before={`${fmtNumber(baseline.delay_days)} días`} after={`${fmtNumber(scenario.delay_days)} días`} delta={`${delta.delay_days > 0 ? '+' : ''}${fmtNumber(delta.delay_days)} ${Math.abs(delta.delay_days) === 1 ? 'día' : 'días'}`} favorable={delta.delay_days <= 0} />
            <ComparisonRow label="Sobrecosto estimado" before={fmtPct(baseline.cost_overrun_ratio)} after={fmtPct(scenario.cost_overrun_ratio)} delta={fmtPp(delta.cost_overrun_ratio)} favorable={delta.cost_overrun_ratio <= 0} />
            <ComparisonRow label="Team Health" before={fmtPct(baseline.team_health?.score)} after={fmtPct(scenario.team_health?.score)} />
        </div><p className="science-note">Los valores y diferencias corresponden a las inferencias devueltas por el backend.</p>
    </div>;
}

function ComparisonRow({ label, before, after, delta, favorable }) {
    return <div className="comparison-row"><strong>{label}</strong><span>{before}</span><span>{after}</span><span className={delta == null ? '' : favorable ? 'good-text' : 'warn-text'}>{delta ?? '—'}</span></div>;
}