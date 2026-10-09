import { useEffect, useState } from 'react';

const finalStatusLabels = { derived_from_health: 'Derivado de Health', independent_model: 'Modelo independiente' };
const engineLabel = engine => engine?.startsWith('ollama:') ? `Qwen3 8B (${engine.slice(7)})` : engine === 'grounded_fallback' ? 'Motor de respaldo' : engine || '—';

export function TechnicalDrawer({ open, onClose, result, model, schema, technicalError, genaiStatus }) {
    const [showJson, setShowJson] = useState(false);
    useEffect(() => {
        if (!open) return undefined;
        const closeOnEscape = event => { if (event.key === 'Escape') onClose(); };
        window.addEventListener('keydown', closeOnEscape);
        return () => window.removeEventListener('keydown', closeOnEscape);
    }, [open, onClose]);
    useEffect(() => setShowJson(false), [result, open]);
    if (!open) return null;
    const metadata = result?.model || model;
    const recommendation = result?.recommendations;
    const items = [
        ['Versión del modelo', metadata?.version], ['Modo', metadata?.mode === 'configured' ? 'Configurado' : metadata?.mode], ['Ejecución', result?.model?.execution || (model?.mode ? 'Backend conectado' : '—')],
        ['Dataset', metadata?.dataset_source], ['Tipo de datos', /synthetic[_ ]external/i.test(metadata?.dataset_type || '') ? 'Datos sintéticos externos' : metadata?.dataset_type], ['Algoritmo', metadata?.model_type],
        ['Estado de negocio', finalStatusLabels[metadata?.final_status_mode] || metadata?.final_status_mode],
        ['Fusión', metadata?.fusion ? `${Math.round(metadata.fusion.core_weight * 100)} % ML / ${Math.round(metadata.fusion.team_health_weight * 100)} % Team Health · ${metadata.fusion.calibrated ? 'calibrada' : 'no calibrada'}` : '—'],
        ['Features entrenadas', metadata?.trained_features?.length ?? schema?.ml_features?.length ?? '—'],
        ['Cobertura de entrada', result?.prediction?.input_quality ? `${Math.round(result.prediction.input_quality.coverage * 100)} %` : '—'],
        ['ML + drivers', result?.timing?.ml_and_drivers_ms == null ? '—' : `${Number(result.timing.ml_and_drivers_ms).toLocaleString('es-CO')} ms`],
        ['Latencia GenAI', result?.genai_latency_ms == null ? '—' : `${Number(result.genai_latency_ms).toLocaleString('es-CO')} ms`],
        ['Tiempo total', result?.timing?.total_ms == null ? result?.inference_ms == null ? '—' : `${Number(result.inference_ms).toLocaleString('es-CO')} ms` : `${Number(result.timing.total_ms).toLocaleString('es-CO')} ms`],
        ['Origen de drivers', result?.driver_source === 'local_model_sensitivity' ? 'Sensibilidad local del modelo' : result?.driver_source || '—'],
        ['Prediction ID', result?.prediction_id || '—'], ['Motor de recomendaciones', engineLabel(recommendation?.engine)],
        ['Estado de GenAI', recommendation ? recommendation.genai_used ? 'Qwen3 utilizado' : recommendation.genai_attempted ? 'Intentado; respaldo utilizado' : 'Desactivada; respaldo utilizado' : genaiStatus?.enabled ? genaiStatus.available ? `Disponible · ${genaiStatus.model}` : 'No disponible' : 'Desactivada'],
        ['Ollama disponible', genaiStatus ? String(genaiStatus.available) : '—'],
        ['Último error GenAI', genaiStatus?.last_error?.failure_detail || '—'],
        ['GenAI attempted', recommendation ? String(recommendation.genai_attempted) : '—'],
        ['GenAI used', recommendation ? String(recommendation.genai_used) : '—'],
        ['Failure code', recommendation?.failure_code || '—'],
        ['Failure detail', recommendation?.failure_detail || '—'],
        ['Schema válido', recommendation?.grounding ? String(recommendation.grounding.schema_valid) : '—'],
        ['Grounded', recommendation?.grounding ? String(recommendation.grounding.grounded) : '—'],
        ['Actionability', recommendation?.grounding ? String(recommendation.grounding.actionability) : '—'],
        ['Allowed evidence', recommendation?.allowed_evidence_features?.join(', ') || '—'],
        ['Referenced evidence', recommendation?.referenced_evidence_features?.join(', ') || '—'],
    ];
    const payload = result || { model: metadata, schema: { ml_features: schema?.ml_features, team_health_features: schema?.team_health_features } };
    const copyJson = async () => { if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(JSON.stringify(payload, null, 2)); };
    const downloadJson = () => { const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = `prunin-${result?.prediction_id || 'evidencia'}.json`; link.click(); URL.revokeObjectURL(url); };
    return <div className="drawer-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}><aside className="technical-drawer" role="dialog" aria-modal="true" aria-labelledby="technical-title">
        <div className="drawer-heading"><div><p className="eyebrow">EVIDENCIA TÉCNICA</p><h2 id="technical-title">Trazabilidad de inferencia</h2></div><button type="button" className="icon-button" aria-label="Cerrar evidencia técnica" onClick={onClose}>×</button></div>
        <dl className="technical-list">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? '—'}</dd></div>)}</dl>
        {metadata?.trained_features?.length > 0 && <details className="disclosure"><summary>Features entrenadas ({metadata.trained_features.length})</summary><p className="feature-list">{metadata.trained_features.join(' · ')}</p></details>}
        {schema?.fields.some(field => field.usage === 'not_used') && <details className="disclosure"><summary>Variables previstas para futuras versiones</summary><p className="subtle-note">Estas variables no afectan el modelo académico actualmente cargado.</p><p className="feature-list">{schema.fields.filter(field => field.usage === 'not_used').map(field => field.label).join(' · ')}</p></details>}
        {result?.prediction?.team_health?.components && <details className="disclosure"><summary>Componentes Team Health en JSON</summary><pre className="technical-json">{JSON.stringify(result.prediction.team_health.components, null, 2)}</pre></details>}
        {recommendation?.genai_failure_reason && <details className="disclosure"><summary>Detalle técnico de GenAI</summary><pre className="technical-json">{recommendation.genai_failure_reason}</pre></details>}
        {recommendation?.genai_debug && <details className="disclosure"><summary>Debug GenAI (raw response y JSON analizado)</summary><pre className="technical-json">{JSON.stringify(recommendation.genai_debug, null, 2)}</pre></details>}
        {technicalError && <details className="disclosure"><summary>Error técnico de la última solicitud</summary><pre className="technical-json">{technicalError}</pre></details>}
        <div className="json-actions"><button type="button" className="secondary-button" onClick={copyJson}>Copiar JSON</button><button type="button" className="secondary-button" onClick={downloadJson}>Descargar resultados</button></div>
        <button type="button" className="text-button json-toggle" aria-expanded={showJson} onClick={() => setShowJson(value => !value)}>{showJson ? 'Ocultar JSON completo' : 'Ver JSON completo'}</button>{showJson && <pre className="technical-json full-json">{JSON.stringify(payload, null, 2)}</pre>}
    </aside></div>;
}