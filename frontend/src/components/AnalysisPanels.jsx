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

function RiskAlertBanner({ status }) {
    const active = status === 'at_risk' || status === 'critical';
    return <div className={`risk-alert-banner ${active ? 'active' : 'clear'}`} role="status" aria-label="Alerta operacional de riesgo">
        <div className="risk-alert-answer"><span className="eyebrow">RESPUESTA OPERACIONAL</span><strong>{active ? 'Sí: requiere atención' : 'No: seguimiento normal'}</strong></div>
        <div className="risk-alert-copy"><p>{active ? `El modelo detecta una condición ${healthLabels[status] || status}. Conviene revisar las señales antes de que la desviación avance.` : 'El modelo clasifica el proyecto como Saludable con la información disponible.'}</p><small>La <b>alerta temprana</b> agrupa los niveles En riesgo y Crítico para responder si el proyecto necesita atención. El <b>nivel de riesgo</b> conserva el detalle de severidad.</small></div>
    </div>;
}

function TeamHealthCard({ teamHealth }) {
    const labels = { team_utilization: 'Utilización', team_capacity_ratio: 'Capacidad', average_productivity: 'Productividad', rework_ratio: 'Retrabajo', defect_rate: 'Defectos', team_stability: 'Estabilidad', collaboration_level: 'Colaboración' };
    if (!teamHealth) return <article className="metric-card"><span>Condición operativa del equipo</span><strong>—</strong><small>No hay suficientes señales disponibles</small></article>;
    return <article className="metric-card team-metric"><span>Condición operativa del equipo</span><strong>{fmtPct(teamHealth.score)}</strong><small><Tone status={teamHealth.level}>{healthLabels[teamHealth.level] || 'Atención'}</Tone> · {teamHealth.component_count ?? Object.keys(teamHealth.components || {}).length} señales</small>
        {teamHealth.components && <details className="team-breakdown"><summary>Ver detalle</summary><dl>{Object.entries(teamHealth.components).map(([key, value]) => <div key={key}><dt>{labels[key] || key}</dt><dd>{fmtPct(value)}</dd></div>)}</dl></details>}
        <small className="team-disclaimer">Indicador operativo heurístico; no evalúa salud psicológica ni moral del equipo.</small></article>;
}

export function ResultHero({ result, schema }) {
    if (!result) return <section className="surface waiting-card" aria-live="polite"><p className="eyebrow">SIGUIENTE PASO</p><h2>Aquí aparecerá la alerta del proyecto</h2><p>Elige un ejemplo o ajusta las señales y pulsa <strong>Evaluar riesgo del proyecto</strong>. PRUNIN responderá primero si requiere atención y después mostrará la severidad y sus razones.</p></section>;
    const prediction = result.prediction;
    const status = prediction.health;
    return <section className="surface result-card" id="result" aria-labelledby="result-title"><div className="section-heading"><div><span className="step-number">2</span><div><p className="eyebrow">DECISIÓN</p><h2 id="result-title">¿Este proyecto requiere atención?</h2></div></div><span className="live-indicator"><i /> Inferencia ejecutada en vivo</span></div>
        <RiskAlertBanner status={status} />
        <div className="result-summary-grid">
            <div className={`result-hero ${status}`}><span className="eyebrow">NIVEL DE RIESGO</span><h3><Tone status={status}>{healthLabels[status] || status}</Tone></h3><p>El modelo clasifica la condición del proyecto en Saludable, En riesgo o Crítico.</p>{prediction.final_status != null && <p className="business-status">Lectura de negocio: <strong>{statusLabels[prediction.final_status] || prediction.final_status}</strong><span className="help-dot" title="Derivado de Health en el modelo académico actual." aria-label="Derivado de Health en el modelo académico actual.">?</span></p>}</div>
            <div className="audience-interpretation"><span>Cómo leerlo</span><p><strong>La alerta responde si debemos prestar atención al proyecto.</strong> El nivel de riesgo indica qué tan severa es la condición detectada.</p></div>
        </div>
        <div className="metric-grid"><article className="metric-card"><span>Posible retraso</span><strong>{fmtNumber(prediction.delay_days)} <small>días</small></strong><small>Estimación complementaria. La predicción de días de retraso es el componente menos preciso de la evaluación.</small></article><article className="metric-card"><span>Posible sobrecosto</span><strong>{fmtPct(prediction.cost_overrun_ratio)}</strong><small>Estimación del modelo dentro de la evaluación académica.</small></article><TeamHealthCard teamHealth={prediction.team_health} /></div>
        <details className="model-detail"><summary>Ver detalle del modelo</summary><div className="combined-line"><span>Riesgo combinado</span><strong>{fmtPct(prediction.fused_risk_score)} · {healthLabels[prediction.fused_health] || '—'}</strong><small>Predicción principal + señal operativa del equipo; combinación experimental</small></div><div className="result-lower-grid"><div><h3>Probabilidad por nivel de riesgo</h3><ProbabilityBars probabilities={prediction.health_probabilities} /></div><div className="quality-summary"><h3>Calidad de datos</h3>{prediction.input_quality?.complete ? <p className="quality-complete">✓ Datos completos</p> : <p className="quality-warning">⚠ Se completaron automáticamente {prediction.input_quality?.missing_count ?? 0} señales faltantes</p>}{prediction.input_quality?.missing_count > 0 && <small>El sistema utilizó los valores de referencia aprendidos durante el entrenamiento.</small>}</div></div><p className="science-note">El nivel de riesgo y el indicador combinado son lecturas distintas. La combinación es experimental y no representa una probabilidad calibrada.</p></details></section>;
}

export function DriversPanel({ drivers = [], fields = [] }) {
    const fieldMap = new Map(fields.map(field => [field.name, field]));
    const visible = [...drivers].sort((a, b) => Math.abs(b.risk_impact) - Math.abs(a.risk_impact)).slice(0, 5);
    const format = (driver, value) => { const spec = fieldMap.get(driver.feature); if (value == null) return '—'; return spec?.format === 'percent' ? fmtPct(value) : spec?.type === 'select' ? String(value).replaceAll('_', ' ') : fmtNumber(value, 2); };
    return <section className="surface content-section" id="explanation" aria-labelledby="drivers-title"><div className="section-heading"><div><span className="step-number">3</span><div><p className="eyebrow">SEÑALES</p><h2 id="drivers-title">¿Qué está empujando el riesgo?</h2></div></div></div><p className="section-subtitle">Estas variables cambian la lectura del modelo frente a sus referencias. Son señales de sensibilidad, no causas demostradas.</p>
        {visible.length === 0 ? <p className="empty-inline">No se identificaron señales con cambios relevantes frente a sus valores de referencia.</p> : <div className="driver-list">{visible.map(driver => <article className="driver-row" key={driver.feature}><div className="driver-info"><strong>{driver.label || fieldMap.get(driver.feature)?.label || driver.feature}</strong><span>Observado: {format(driver, driver.value)} <span aria-hidden="true">·</span> Referencia: {format(driver, driver.reference)}</span></div><span className={`driver-impact ${driver.direction === 'increases_risk' ? 'increases' : 'reduces'}`}>{driver.risk_impact > 0 ? '+' : ''}{(Number(driver.risk_impact) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} pp</span><small className="driver-direction">{driver.direction === 'increases_risk' ? 'En este análisis aumenta la señal de riesgo frente al valor de referencia' : 'En este análisis reduce la señal de riesgo frente al valor de referencia'}</small></article>)}</div>}
        <p className="science-note">Estas señales representan sensibilidad local del modelo y no demuestran causalidad.</p></section>;
}

export function RecommendationCard({ data, fields = [] }) {
    if (!data) return null;
    const genaiUsed = data.genai_used === true;
    const genaiFailed = data.genai_attempted === true && !genaiUsed;
    const groundingFailures = new Set(['unknown_evidence_feature', 'unsupported_numeric_claim', 'empty_recommendations_with_risk_drivers', 'grounding_validation_failed']);
    const formatFailures = new Set(['invalid_json', 'invalid_schema']);
    const legacyTimeout = /timeout|timed out/i.test(data.genai_failure_reason || '');
    const title = genaiUsed ? 'IA generativa local activa' : genaiFailed
        ? data.failure_code === 'ollama_timeout' || (!data.failure_code && legacyTimeout) ? 'La IA generativa no respondió dentro del tiempo esperado; se utilizó una recomendación de respaldo'
            : groundingFailures.has(data.failure_code) ? 'La respuesta de IA no cumplió las reglas de evidencia; se utilizó una recomendación de respaldo'
                : formatFailures.has(data.failure_code) ? 'La IA generativa no devolvió una respuesta válida; se utilizó una recomendación de respaldo'
                    : 'La IA generativa no está disponible; se utilizó una recomendación de respaldo'
        : 'IA generativa desactivada · Recomendación de respaldo';
    const fieldMap = new Map(fields.map(field => [field.name, field.label]));
    return <section className="surface content-section recommendations" id="recommendations" aria-labelledby="recommendations-title"><div className="section-heading"><div><span className="step-number">4</span><div><p className="eyebrow">ACCIÓN</p><h2 id="recommendations-title">¿Qué podría hacer el responsable del proyecto?</h2></div></div></div>
        <div className={`recommendation-status ${genaiUsed ? 'genai-active' : 'fallback'}`}><span aria-hidden="true">{genaiUsed ? '✦' : '↻'}</span><div><strong>{title}</strong>{genaiFailed && <small>La predicción se completó correctamente.</small>}</div></div>
        {data.actions?.length ? <ol className="action-list">{data.actions.slice(0, 5).map((action, index) => <li key={`${index}-${action}`}>{action}</li>)}</ol> : data.summary ? <p className="recommendation-summary">{data.summary}</p> : <p className="empty-inline">No hay acciones sugeridas para esta inferencia.</p>}
        {data.evidence_features?.length > 0 && <p className="evidence-line"><span>Evidencia utilizada:</span> {data.evidence_features.map(key => fieldMap.get(key) || key).join(' · ')}</p>}
        <details className="disclosure recommendation-evidence"><summary>Ver evidencia y razones</summary>{data.reasons?.length > 0 && <ul>{data.reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}</ul>}{data.summary && <p>{data.summary}</p>}{data.disclaimer && <p className="science-note">{data.disclaimer}</p>}</details></section>;
}
