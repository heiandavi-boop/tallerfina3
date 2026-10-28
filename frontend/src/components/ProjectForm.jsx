import { Field } from './fields.jsx';

function audienceSpec(spec) {
    if (spec.name === 'spi') return { ...spec, label: 'Cumplimiento del cronograma (SPI)', description: 'Compara el avance logrado con el avance planificado. Un valor menor que 1 indica atraso frente al plan.' };
    if (spec.name === 'cpi') return { ...spec, label: 'Eficiencia del costo (CPI)', description: 'Compara el valor logrado con el costo utilizado. Un valor menor que 1 indica presión de costo.' };
    return spec;
}

export function ProjectForm({ schema, values, onChange, onAnalyze, loading, activePreset, onPreset, coverage }) {
    const mlFields = schema.fields.filter(field => field.usage === 'ml_feature');
    const teamFields = schema.fields.filter(field => field.usage === 'team_health');
    const projectFields = mlFields.filter(field => field.group !== 'Ejecución');
    const executionFields = mlFields.filter(field => field.group === 'Ejecución');
    const underMinimum = coverage.ratio < coverage.minimum;
    return <section className="surface project-card" id="project" aria-labelledby="project-title">
        <div className="section-heading"><div><span className="step-number">1</span><div><p className="eyebrow">OBSERVA</p><h2 id="project-title">¿Qué está pasando en el proyecto?</h2></div></div><span className="quiet-label">{mlFields.length} señales utilizadas</span></div>
        <p className="section-explainer">Ingresa o ajusta la foto actual del proyecto. Para la demo puedes partir de uno de estos ejemplos y observar cómo cambia la alerta.</p>
        <div className="preset-row" role="group" aria-label="Escenarios de demostración"><span>Ejemplos de entrada</span><div>
            <button type="button" className={`preset healthy ${activePreset === 'healthy' ? 'selected' : ''}`} aria-pressed={activePreset === 'healthy'} onClick={() => onPreset('healthy')}>Ejemplo saludable</button>
            <button type="button" className={`preset at-risk ${activePreset === 'at_risk' ? 'selected' : ''}`} aria-pressed={activePreset === 'at_risk'} onClick={() => onPreset('at_risk')}>Ejemplo en riesgo</button>
            <button type="button" className={`preset critical ${activePreset === 'critical' ? 'selected' : ''}`} aria-pressed={activePreset === 'critical'} onClick={() => onPreset('critical')}>Ejemplo crítico</button>
        </div></div>
        <div className="field-groups"><fieldset className="field-group"><legend>Proyecto</legend><div className="form-grid">{projectFields.map(spec => <Field key={spec.name} spec={audienceSpec(spec)} value={values[spec.name]} onChange={onChange} />)}</div></fieldset>
            {executionFields.length > 0 && <fieldset className="field-group execution-group"><legend>Ejecución</legend><p className="indicator-cheat-sheet"><b>Lectura rápida:</b> Cumplimiento del cronograma (SPI) &lt; 1 indica atraso frente al plan · Eficiencia del costo (CPI) &lt; 1 indica presión de costo · En ambos casos, 1 representa el comportamiento esperado.</p><div className="form-grid">{executionFields.map(spec => <Field key={spec.name} spec={audienceSpec(spec)} value={values[spec.name]} onChange={onChange} />)}</div></fieldset>}
        </div>
        {teamFields.length > 0 && <details className="disclosure team-inputs"><summary>Señales operativas opcionales <span>{teamFields.length} variables del equipo</span></summary><p className="subtle-note">Sirven para una lectura complementaria del funcionamiento del equipo; no cambian la predicción principal del nivel de riesgo.</p><div className="form-grid">{teamFields.map(spec => <Field key={spec.name} spec={spec} value={values[spec.name]} onChange={onChange} />)}</div></details>}
        <div className="form-footer"><div className="input-quality" aria-live="polite">{coverage.missing === 0 ? <span className="quality-complete">✓ Datos completos</span> : <span className={underMinimum ? 'quality-low' : 'quality-warning'}>⚠ {coverage.missing} señal(es) requeridas sin valor</span>}{underMinimum && <small>Completa variables para alcanzar la cobertura mínima de {Math.round(coverage.minimum * 100)} %.</small>}</div>
            <button type="button" className="primary-button" onClick={onAnalyze} disabled={loading || underMinimum}>{loading ? <><span className="spinner" /> Evaluando riesgo…</> : 'Evaluar riesgo del proyecto'}</button></div>
    </section>;
}