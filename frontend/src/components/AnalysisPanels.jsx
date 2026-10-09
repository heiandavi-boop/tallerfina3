const healthLabels = { healthy: 'Saludable', at_risk: 'En riesgo', critical: 'Crítico' };
const statusLabels = { successful: 'Exitoso', challenged: 'Con desviaciones', critical: 'Crítico', incomplete: 'Incompleto' };
const fmtPct = value => value == null ? '—' : `${(Number(value) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
const fmtNumber = (value, digits = 1) => value == null ? '—' : Number(value).toLocaleString('es-CO', { maximumFractionDigits: digits });

function Tone({ status, children }) {
    const tone = status === 'healthy' ? 'healthy' : status === 'critical' ? 'critical' : 'at-risk';
    return <span className={`status-text ${tone}`}><span className="status-mark" aria-hidden="true" />{children}</span>;
}

function ProbabilityBars({ probabilities }) {
    if (!probabilities) return null;
    return <div className="probability-list">{Object.entries(probabilities).sort((a, b) => Number(b[1]) - Number(a[1])).map(([key, value]) => <div className="probability-row" key={key}><div className="probability-label"><Tone status={key}>{healthLabels[key] || key}</Tone><strong>{fmtPct(value)}</strong></div><div className="probability-track" role="img" aria-label={`${healthLabels[key] || key}: ${fmtPct(value)}`}><span className={`probability-fill ${key}`} style={{ width: `${Math.max(0, Math.min(100, Number(value) * 100))}%` }} /></div></div>)}</div>;
}

function TeamHealthCard({ teamHealth }) {
    const labels = { team_utilization: 'Utilización', team_capacity_ratio: 'Capacidad', average_productivity: 'Productividad', rework_ratio: 'Retrabajo', defect_rate: 'Defectos', team_stability: 'Estabilidad', collaboration_level: 'Colaboración' };
    if (!teamHealth) return <article className="metric-card"><span>Team Health</span><strong>—</strong><small>No disponible</small></article>;
    return <article className="metric-card team-metric"><span>Team Health</span><strong>{fmtPct(teamHealth.score)}</strong><small><Tone status={teamHealth.level}>{healthLabels[teamHealth.level] || 'Atención'}</Tone> · {teamHealth.component_count ?? Object.keys(teamHealth.components || {}).length} señales</small>
        {teamHealth.components && <details className="team-breakdown"><summary>Ver detalle</summary><dl>{Object.entries(teamHealth.components).map(([key, value]) => <div key={key}><dt>{labels[key] || key}</dt><dd>{fmtPct(value)}</dd></div>)}</dl></details>}
        <small className="team-disclaimer">Indicador operativo heurístico; no evalúa salud psicológica ni moral del equipo.</small></article>;
}

export function ResultHero({ result, schema }) {
    if (!result) return <section className="surface waiting-card" aria-live="polite"><p className="eyebrow">RESULTADO</p><h2>El análisis aparecerá aquí</h2><p>Selecciona un escenario o ajusta los datos y pulsa <strong>Analizar proyecto</strong>. La predicción se ejecuta en el backend.</p></section>;
    const prediction = result.prediction;
    const status = prediction.health;
    return <section className="surface result-card" id="result" aria-labelledby="result-title"><div className="section-heading"><div><span className="step-number">2</span><div><p className="eyebrow">RESULTADO</p><h2 id="result-title">Resultado del análisis</h2></div></div><span className="live-indicator"><i /> Predicción del modelo supervisado</span></div>
        <div className={`result-hero ${status}`}><span className="eyebrow">HEALTH ML</span><h3><Tone status={status}>{healthLabels[status] || status}</Tone></h3><p>Clasificación del modelo académico</p>{prediction.final_status != null && <p className="business-status">Estado de negocio: <strong>{statusLabels[prediction.final_status] || prediction.final_status}</strong><span className="help-dot" title="Derivado de Health en el modelo académico actual." aria-label="Derivado de Health en el modelo académico actual.">?</span></p>}</div>
        <div className="metric-grid"><article className="metric-card"><span>Retraso estimado</span><strong>{fmtNumber(prediction.delay_days)} <small>días</small></strong><small>Predicción ML</small></article><article className="metric-card"><span>Sobrecosto estimado</span><strong>{fmtPct(prediction.cost_overrun_ratio)}</strong><small>Predicción ML</small></article><TeamHealthCard teamHealth={prediction.team_health} /></div>
        <div className="combined-line"><span>Riesgo combinado</span><strong>{fmtPct(prediction.fused_risk_score)} · {healthLabels[prediction.fused_health] || '—'}</strong><small>ML + señal operativa Team Health</small></div>
        <div className="result-lower-grid"><div><h3>Probabilidad del modelo</h3><ProbabilityBars probabilities={prediction.health_probabilities} /></div><div className="quality-summary"><h3>Calidad de datos</h3>{prediction.input_quality?.complete ? <p className="quality-complete">✓ Datos completos</p> : <p className="quality-warning">⚠ Se imputaron {prediction.input_quality?.missing_count ?? 0} variables ML</p>}{prediction.input_quality?.missing_count > 0 && <small>Imputación según el pipeline de entrenamiento.</small>}</div></div>
        <p className="science-note">Health ML y riesgo combinado son indicadores distintos. La fusión es una regla operativa no calibrada.</p></section>;
}

export function DriversPanel({ drivers = [], fields = [] }) {
    const fieldMap = new Map(fields.map(field => [field.name, field]));
    const visible = [...drivers].sort((a, b) => Math.abs(b.risk_impact) - Math.abs(a.risk_impact)).slice(0, 5);
    const format = (driver, value) => { const spec = fieldMap.get(driver.feature); if (value == null) return '—'; return spec?.format === 'percent' ? fmtPct(value) : spec?.type === 'select' ? String(value).replaceAll('_', ' ') : fmtNumber(value, 2); };
    return <section className="surface content-section" id="explanation" aria-labelledby="drivers-title"><div className="section-heading"><div><span className="step-number">3</span><div><p className="eyebrow">EXPLICACIÓN</p><h2 id="drivers-title">¿Por qué presenta este nivel de riesgo?</h2></div></div></div><p className="section-subtitle">Principales señales detectadas por el modelo</p>
        {visible.length === 0 ? <p className="empty-inline">No se detectaron impactos locales relevantes.</p> : <div className="driver-list">{visible.map(driver => <article className="driver-row" key={driver.feature}><div className="driver-info"><strong>{driver.label || fieldMap.get(driver.feature)?.label || driver.feature}</strong><span>Observado: {format(driver, driver.value)} <span aria-hidden="true">·</span> Referencia: {format(driver, driver.reference)}</span></div><span className={`driver-impact ${driver.direction === 'increases_risk' ? 'increases' : 'reduces'}`}>{driver.risk_impact > 0 ? '+' : ''}{(Number(driver.risk_impact) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} pp</span><small className="driver-direction">{driver.direction === 'increases_risk' ? 'En esta inferencia aumenta el score frente al valor de referencia' : 'En esta inferencia reduce el score frente al valor de referencia'}</small></article>)}</div>}
        <p className="science-note">Estas señales representan sensibilidad local del modelo y no demuestran causalidad.</p></section>;
}

export function RecommendationCard({ data, fields = [] }) {
    if (!data) return null;
    const genaiUsed = data.genai_used === true;
    const genaiFailed = data.genai_attempted === true && !genaiUsed;
    const timeout = /timeout|timed out/i.test(data.genai_failure_reason || '');
    const title = genaiUsed ? 'Qwen3 8B · IA generativa activa' : genaiFailed ? `${timeout ? 'Qwen3 no respondió dentro del tiempo esperado' : 'Qwen3 no pudo generar una recomendación válida'}; se utilizó recomendación de respaldo` : 'IA generativa desactivada · Recomendación de respaldo';
    const fieldMap = new Map(fields.map(field => [field.name, field.label]));
    return <section className="surface content-section recommendations" id="recommendations" aria-labelledby="recommendations-title"><div className="section-heading"><div><span className="step-number">4</span><div><p className="eyebrow">ACCIONES</p><h2 id="recommendations-title">¿Qué recomienda PRUNIN?</h2></div></div></div>
        <div className={`recommendation-status ${genaiUsed ? 'genai-active' : 'fallback'}`}><span aria-hidden="true">{genaiUsed ? '✦' : '↻'}</span><div><strong>{title}</strong>{genaiFailed && <small>La predicción se completó correctamente.</small>}</div></div>
        {data.actions?.length ? <ol className="action-list">{data.actions.slice(0, 5).map((action, index) => <li key={`${index}-${action}`}>{action}</li>)}</ol> : <p className="empty-inline">No hay acciones sugeridas para esta inferencia.</p>}
        {data.evidence_features?.length > 0 && <p className="evidence-line"><span>Evidencia utilizada:</span> {data.evidence_features.map(key => fieldMap.get(key) || key).join(' · ')}</p>}
        <details className="disclosure recommendation-evidence"><summary>Ver evidencia y razones</summary>{data.reasons?.length > 0 && <ul>{data.reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}</ul>}{data.summary && <p>{data.summary}</p>}{data.disclaimer && <p className="science-note">{data.disclaimer}</p>}</details></section>;
}