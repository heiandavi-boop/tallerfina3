import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_URL || '';
const healthLabel = { healthy: 'Saludable', at_risk: 'En riesgo', critical: 'Crítico', attention: 'Atención', insufficient_data: 'Datos insuficientes' };
const statusLabel = { successful: 'Exitoso', challenged: 'Con desviaciones', critical: 'Crítico', incomplete: 'Incompleto' };
const fmtPct = v => v == null ? '—' : `${(Number(v) * 100).toFixed(1)} %`;
const fmtNum = (v, d = 2) => v == null ? '—' : Number(v).toLocaleString('es-CO', { maximumFractionDigits: d });
const fmtMoney = v => v == null ? '—' : Number(v).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });

function Badge({ children, tone = 'neutral' }) { return <span className={`badge ${tone}`}>{children}</span> }
function Spinner() { return <span className="spinner" aria-label="cargando" /> }

function Header({ model }) {
  const demo = model?.mode === 'synthetic_demo';
  return <header className="topbar">
    <div className="brand"><div className="mark">P</div><div><strong>PRUNIN AI Core</strong><span>Live Playground</span></div></div>
    <div className="topmeta">
      <Badge tone={demo ? 'warning' : 'success'}>{demo ? 'MODELO DEMO SINTÉTICO' : 'MODELO ACADÉMICO'}</Badge>
      <span className="mono">{model?.version || 'cargando…'}</span>
      <span className="liveDot">● LIVE</span>
    </div>
  </header>
}

function Field({ spec, value, onChange, disabled = false }) {
  const display = spec.format === 'percent' && value != null ? `${Math.round(Number(value) * 100)} %` : (spec.name === 'planned_budget' ? fmtMoney(value) : value ?? '');
  if (spec.type === 'select') return <label className="field"><span>{spec.label}</span><select disabled={disabled} value={value ?? ''} onChange={e => onChange(spec.name, e.target.value)}>{spec.options.map(o => <option key={o} value={o}>{o.replaceAll('_', ' ')}</option>)}</select><small>{spec.description}</small></label>;
  if (spec.type === 'range') return <label className="field rangeField"><div className="fieldHead"><span>{spec.label}</span><b>{display}</b></div><input disabled={disabled} type="range" min={spec.min} max={spec.max} step={spec.step} value={value ?? spec.reference} onChange={e => onChange(spec.name, Number(e.target.value))} /><small>{spec.description}</small></label>;
  return <label className="field"><span>{spec.label}</span><input disabled={disabled} type="number" min={spec.min} max={spec.max} step={spec.step} value={value ?? ''} onChange={e => onChange(spec.name, e.target.value === '' ? null : Number(e.target.value))} /><small>{spec.description}</small></label>;
}

function FormPanel({ fields, values, onChange, onAnalyze, loading, presets, onPreset, title = 'Datos del proyecto' }) {
  const groups = [...new Set(fields.map(f => f.group))];
  return <section className="panel inputPanel">
    <div className="panelTitle"><div><span className="eyebrow">ENTRADA</span><h2>{title}</h2></div><div className="presetRow">
      <button onClick={() => onPreset('healthy')} className="mini good">Saludable</button>
      <button onClick={() => onPreset('at_risk')} className="mini warn">En riesgo</button>
      <button onClick={() => onPreset('critical')} className="mini bad">Crítico</button>
    </div></div>
    {groups.map(g => <details key={g} open={g === 'Ejecución' || g === 'Equipo'}><summary>{g}</summary><div className="gridFields">{fields.filter(f => f.group === g).map(f => <Field key={f.name} spec={f} value={values[f.name]} onChange={onChange} />)}</div></details>)}
    <button className="primary" onClick={onAnalyze} disabled={loading}>{loading ? <><Spinner /> Analizando…</> : 'Analizar proyecto'}</button>
  </section>
}

function ProbabilityBars({ probs }) {
  if (!probs) return null;
  return <div className="probBars">{Object.entries(probs).map(([k, v]) => <div key={k}><div className="barHead"><span>{healthLabel[k] || statusLabel[k] || k}</span><b>{fmtPct(v)}</b></div><div className="bar"><i style={{ width: `${Math.max(0, Math.min(100, v * 100))}%` }} /></div></div>)}</div>
}

function ResultCards({ result }) {
  if (!result) return <div className="emptyState"><div className="pulseOrb" /><h3>Listo para analizar</h3><p>Modifica las variables o selecciona un proyecto de ejemplo. La inferencia se ejecutará en el backend con el modelo cargado.</p></div>;
  const p = result.prediction;
  const h = p.fused_health || p.health;
  const tone = h === 'healthy' ? 'good' : h === 'critical' ? 'bad' : 'warn';
  return <div className="resultsWrap">
    <div className="heroResult"><div><span className="eyebrow">SALUD DEL PROYECTO</span><h1 className={tone}>{healthLabel[h] || h}</h1><p>Riesgo fusionado: <b>{fmtPct(p.fused_risk_score)}</b></p></div><div className={`scoreRing ${tone}`}><span>{p.fused_risk_score != null ? Math.round(p.fused_risk_score * 100) : '—'}</span><small>riesgo</small></div></div>
    <div className="metricGrid">
      <article><span>Retraso estimado</span><strong>{fmtNum(p.delay_days, 1)} días</strong><small>Predicción ML</small></article>
      <article><span>Sobrecosto estimado</span><strong>{fmtPct(p.cost_overrun_ratio)}</strong><small>Predicción ML</small></article>
      <article><span>Estado final</span><strong>{statusLabel[p.final_status] || p.final_status}</strong><small>{p.final_status_source === 'derived_from_health' ? 'Derived business status' : 'Predicción ML'}</small></article>
      <article><span>Team Health</span><strong>{p.team_health?.score == null ? '—' : fmtPct(p.team_health.score)}</strong><small>{healthLabel[p.team_health?.level] || p.team_health?.level}</small></article>
    </div>
    <div className="splitBox"><div><h3>Probabilidad Health</h3><ProbabilityBars probs={p.health_probabilities} /></div><div><h3>Calidad de entrada</h3><p className={p.input_quality?.complete ? 'goodText' : 'warnText'}>{p.input_quality?.complete ? '✓ Todas las features entrenadas presentes' : `⚠ ${p.input_quality?.missing_count} feature(s) faltante(s)`}</p>{p.input_quality?.missing_count > 0 && <small>{p.input_quality.missing_trained_features.join(', ')}</small>}</div></div>
  </div>
}

function Drivers({ drivers = [] }) {
  return <section className="panel"><span className="eyebrow">EXPLICABILIDAD</span><h2>¿Qué está influyendo?</h2>{drivers.length === 0 ? <p className="muted">No se detectaron impactos locales relevantes.</p> : <div className="driverList">{drivers.map(d => <div className="driver" key={d.feature}><div><b>{d.label}</b><small>{d.direction === 'increases_risk' ? 'Aumenta riesgo' : 'Reduce riesgo'} · referencia {String(d.reference)}</small></div><span className={d.direction === 'increases_risk' ? 'impact bad' : 'impact good'}>{d.risk_impact > 0 ? '+' : ''}{(d.risk_impact * 100).toFixed(1)} pp</span></div>)}</div>}</section>
}

function Recommendations({ data }) {
  if (!data) return null;
  return <section className="panel"><div className="panelTitle"><div><span className="eyebrow">ACCIONES</span><h2>Recomendaciones</h2></div><Badge>{data.engine}</Badge></div>
    {data.reasons?.length > 0 && <><h3>Señales observadas</h3><ul>{data.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
    <h3>Acciones sugeridas</h3><ul>{data.actions?.map((x, i) => <li key={i}>{x}</li>)}</ul><p className="fineprint">{data.disclaimer}</p>
  </section>
}

function Technical({ result, model }) {
  const [open, setOpen] = useState(false);
  return <section className="panel tech"><button className="techToggle" onClick={() => setOpen(!open)}><span><span className="eyebrow">EVIDENCIA TÉCNICA</span><b>Detalles de inferencia</b></span><span>{open ? '−' : '+'}</span></button>{open && <div className="techBody">
    <div className="techGrid"><div><span>Model version</span><b>{model?.version}</b></div><div><span>Dataset source</span><b>{model?.dataset_source}</b></div><div><span>Dataset type</span><b>{model?.dataset_type}</b></div><div><span>Model type</span><b>{model?.model_type}</b></div><div><span>Final Status</span><b>{model?.final_status_mode === 'derived_from_health' ? 'Derived business status' : 'Independent model'}</b></div><div><span>Trained features</span><b>{model?.trained_features?.length ?? 0}</b></div><div><span>Inference time</span><b>{result?.inference_ms ?? '—'} ms</b></div><div><span>Prediction ID</span><b className="mono tiny">{result?.prediction_id ?? '—'}</b></div></div>
    {model?.trained_features?.length > 0 && <small className="muted">Features: {model.trained_features.join(', ')}</small>}
    {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
  </div>}</section>
}

function WhatIf({ fields, baseline, onRun, loading }) {
  const [scenario, setScenario] = useState({ ...baseline });
  useEffect(() => setScenario({ ...baseline }), [baseline]);
  const focusNames = ['spi', 'cpi', 'team_utilization', 'team_capacity_ratio', 'average_productivity', 'defect_rate', 'rework_ratio', 'scope_growth_ratio', 'dependency_delay_days', 'normalized_risk_exposure', 'governance_health_score'];
  const focus = fields.filter(f => focusNames.includes(f.name));
  const change = (n, v) => setScenario(s => ({ ...s, [n]: v }));
  return <section className="panel whatif"><span className="eyebrow">SIMULACIÓN</span><h2>¿Qué pasa si…?</h2><p className="muted">Parte del escenario actual, modifica acciones operativas y vuelve a ejecutar el mismo modelo.</p><div className="gridFields compact">{focus.map(f => <Field key={f.name} spec={f} value={scenario[f.name]} onChange={change} />)}</div><button className="secondary" disabled={loading} onClick={() => onRun(scenario)}>{loading ? <><Spinner /> Simulando…</> : 'Simular escenario'}</button></section>
}

function DeltaCard({ whatif }) {
  if (!whatif) return null;
  const d = whatif.delta; const base = whatif.baseline.prediction; const sc = whatif.scenario.prediction;
  return <section className="panel delta"><span className="eyebrow">COMPARACIÓN</span><h2>Impacto del escenario</h2><div className="deltaGrid">
    <div><span>Health</span><b>{healthLabel[base.fused_health || base.health]} → {healthLabel[sc.fused_health || sc.health]}</b></div>
    <div><span>Riesgo</span><b className={d.risk_score <= 0 ? 'goodText' : 'badText'}>{d.risk_score > 0 ? '+' : ''}{fmtPct(d.risk_score)}</b></div>
    <div><span>Retraso</span><b className={d.delay_days <= 0 ? 'goodText' : 'badText'}>{d.delay_days > 0 ? '+' : ''}{fmtNum(d.delay_days, 1)} días</b></div>
    <div><span>Sobrecosto</span><b className={d.cost_overrun_ratio <= 0 ? 'goodText' : 'badText'}>{d.cost_overrun_ratio > 0 ? '+' : ''}{fmtPct(d.cost_overrun_ratio)}</b></div>
  </div></section>
}

function CsvPanel({ onResults }) {
  const [file, setFile] = useState(null); const [busy, setBusy] = useState(false); const ref = useRef();
  const upload = async () => { if (!file) return; setBusy(true); try { const fd = new FormData(); fd.append('file', file); const r = await fetch(`${API}/api/predict-csv`, { method: 'POST', body: fd }); const j = await r.json(); if (!r.ok) throw new Error(j.detail || 'Error CSV'); onResults(j); } catch (e) { alert(e.message) } finally { setBusy(false) } };
  return <section className="panel csvPanel"><span className="eyebrow">PRUEBA PÚBLICA</span><h2>Cargar CSV</h2><p className="muted">Procesa hasta 100 filas. Cada fila se valida antes de inferencia.</p><div className="fileBox" onClick={() => ref.current?.click()}><input ref={ref} hidden type="file" accept=".csv,text/csv" onChange={e => setFile(e.target.files?.[0] || null)} /><b>{file ? file.name : 'Seleccionar archivo CSV'}</b><small>Máx. 5 MB</small></div><div className="buttonRow"><a className="linkButton" href={`${API}/api/csv-template`}>Descargar plantilla</a><button className="secondary" onClick={upload} disabled={!file || busy}>{busy ? <Spinner /> : 'Analizar CSV'}</button></div></section>
}

function CsvResults({ data }) {
  if (!data) return null;
  return <section className="panel"><span className="eyebrow">RESULTADOS CSV</span><h2>{data.count} fila(s) procesadas</h2><div className="tableWrap"><table><thead><tr><th>Fila</th><th>Health</th><th>Delay</th><th>Cost</th><th>Estado</th></tr></thead><tbody>{data.rows.map(r => <tr key={r.row_number}><td>{r.row_number}</td>{r.error ? <td colSpan="4" className="badText">{r.error}</td> : <><td>{healthLabel[r.prediction.prediction.fused_health || r.prediction.prediction.health]}</td><td>{fmtNum(r.prediction.prediction.delay_days, 1)} d</td><td>{fmtPct(r.prediction.prediction.cost_overrun_ratio)}</td><td>{statusLabel[r.prediction.prediction.final_status]}</td></>}</tr>)}</tbody></table></div></section>
}

function App() {
  const [schema, setSchema] = useState(null), [values, setValues] = useState({}), [result, setResult] = useState(null), [loading, setLoading] = useState(false), [whatif, setWhatif] = useState(null), [whatBusy, setWhatBusy] = useState(false), [csv, setCsv] = useState(null), [error, setError] = useState('');
  useEffect(() => { fetch(`${API}/api/schema`).then(r => r.json()).then(j => { setSchema(j); setValues(j.presets.at_risk) }).catch(e => setError(String(e))) }, []);
  const change = (n, v) => setValues(s => ({ ...s, [n]: v })); const preset = k => { setValues({ ...schema.presets[k] }); setResult(null); setWhatif(null) };
  const analyze = async () => { setLoading(true); setError(''); try { const r = await fetch(`${API}/api/predict`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) }); const j = await r.json(); if (!r.ok) throw new Error(j.detail || 'Error de inferencia'); setResult(j); setWhatif(null) } catch (e) { setError(e.message) } finally { setLoading(false) } };
  const simulate = async scenario => { setWhatBusy(true); try { const r = await fetch(`${API}/api/what-if`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseline: values, scenario }) }); const j = await r.json(); if (!r.ok) throw new Error(j.detail || 'Error what-if'); setWhatif(j) } catch (e) { setError(e.message) } finally { setWhatBusy(false) } };
  if (!schema) return <div className="boot"><div className="mark big">P</div><h2>PRUNIN AI Core</h2>{error ? <p>{error}</p> : <Spinner />}</div>;
  return <><Header model={schema.model} /><main>
    {schema.model.mode === 'synthetic_demo' && <div className="notice"><b>Modo demostración:</b> el backend está ejecutando modelos entrenados con datos sintéticos de smoke test. Cuando exista <code>artifacts/0.9.0-academic</code>, la aplicación lo seleccionará automáticamente.</div>}
    {error && <div className="errorBox">{error}</div>}
    <section className="intro"><div><span className="eyebrow">PREDICCIÓN DE RIESGO DE PROYECTOS</span><h1>Prueba el modelo. Cambia los datos. Comprueba la respuesta.</h1><p>Health, estado final, retraso, sobrecosto y salud operativa del equipo ejecutados en vivo.</p></div><div className="legend"><span><i className="dot observed" />Dato observado</span><span><i className="dot derived" />Variable derivada</span><span><i className="dot predicted" />Predicción ML</span></div></section>
    <div className="twoCol"><FormPanel fields={schema.fields} values={values} onChange={change} onAnalyze={analyze} loading={loading} presets={schema.presets} onPreset={preset} /><section className="panel resultPanel"><span className="eyebrow">RESULTADO</span><ResultCards result={result} /></section></div>
    {result && <><div className="twoCol lower"><Drivers drivers={result.drivers} /><Recommendations data={result.recommendations} /></div><WhatIf fields={schema.fields} baseline={values} onRun={simulate} loading={whatBusy} /><DeltaCard whatif={whatif} /></>}
    <div className="twoCol lower"><CsvPanel onResults={setCsv} /><Technical result={result} model={schema.model} /></div><CsvResults data={csv} />
    <footer><b>PRUNIN AI Core</b><span>Proyecto académico · Inferencia trazable · Sin valores ocultos hardcodeados</span></footer>
  </main></>
}

createRoot(document.getElementById('root')).render(<App />);
