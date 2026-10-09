import { useEffect, useState } from 'react';

const formatNumber = value => Number(value).toLocaleString('es-CO', { maximumFractionDigits: 0 });

export function Field({ spec, value, onChange, idPrefix = 'field' }) {
    const id = `${idPrefix}-${spec.name}`;
    const label = <span className="field-label">{spec.label}<span className="help-dot" title={spec.description} aria-label={spec.description}>?</span></span>;
    if (spec.name === 'planned_budget') return <BudgetField spec={spec} value={value} onChange={onChange} id={id} label={label} />;
    if (spec.type === 'select') return <label className="field" htmlFor={id} title={spec.description}>{label}<select id={id} value={value ?? ''} onChange={event => onChange(spec.name, event.target.value)}>{(spec.options || []).map(option => <option key={option} value={option}>{String(option).replaceAll('_', ' ')}</option>)}</select></label>;
    if (spec.type === 'range') {
        const shownValue = value == null ? '—' : spec.format === 'percent' ? `${(Number(value) * 100).toFixed(0)} %` : Number(value).toFixed(2);
        const reference = spec.reference == null ? null : spec.format === 'percent' ? `${(Number(spec.reference) * 100).toFixed(0)} %` : Number(spec.reference).toFixed(2);
        return <div className={`field range-field ${['spi', 'cpi'].includes(spec.name) ? 'index-field' : ''}`} title={spec.description}><div className="range-heading"><label className="field-label" htmlFor={id}>{label}</label><output htmlFor={id}>{shownValue}</output></div><input id={id} type="range" min={spec.min} max={spec.max} step={spec.step} value={value ?? spec.reference ?? spec.min} onChange={event => onChange(spec.name, Number(event.target.value))} /><span className="field-reference">{reference != null && <>Referencia: {reference}</>}</span></div>;
    }
    return <label className="field" htmlFor={id} title={spec.description}>{label}<input id={id} type="number" min={spec.min} max={spec.max} step={spec.step} value={value ?? ''} onChange={event => onChange(spec.name, event.target.value === '' ? null : Number(event.target.value))} /></label>;
}

function BudgetField({ spec, value, onChange, id, label }) {
    const [focused, setFocused] = useState(false);
    const [draft, setDraft] = useState(value == null ? '' : String(value));
    useEffect(() => setDraft(value == null ? '' : String(value)), [value]);
    return <label className="field" htmlFor={id} title={spec.description}>{label}<div className="money-input"><span>$</span><input id={id} type="text" inputMode="numeric" value={focused ? draft : value == null ? '' : formatNumber(value)} onFocus={() => { setDraft(value == null ? '' : String(value)); setFocused(true); }} onBlur={() => setFocused(false)} onChange={event => { const next = event.target.value.replace(/[^\d]/g, ''); setDraft(next); onChange(spec.name, next ? Number(next) : null); }} /></div></label>;
}