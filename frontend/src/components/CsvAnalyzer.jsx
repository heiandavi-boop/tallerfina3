import { useRef, useState } from 'react';

const healthLabels = { healthy: 'Saludable', at_risk: 'En riesgo', critical: 'Crítico' };
const statusLabels = { successful: 'Exitoso', challenged: 'Con desviaciones', critical: 'Crítico', incomplete: 'Incompleto' };
const fmtPct = value => value == null ? '—' : `${(Number(value) * 100).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
const fmtNumber = value => value == null ? '—' : Number(value).toLocaleString('es-CO', { maximumFractionDigits: 1 });

export function CsvAnalyzer({ onAnalyze, loading, results, error }) {
    const [file, setFile] = useState(null);
    const inputRef = useRef(null);
    const chooseFile = event => {
        const selected = event.target.files?.[0] || null;
        if (selected && selected.size > 5_000_000) {
            setFile(null);
            event.target.value = '';
            onAnalyze(null, 'El archivo supera el límite de 5 MB.');
            return;
        }
        setFile(selected);
        onAnalyze(null, '');
    };
    return <div className="csv-mode" id="csv-mode"><section className="surface csv-card" aria-labelledby="csv-title">
        <div className="section-heading"><div><span className="step-number">VARIOS</span><div><p className="eyebrow">VARIOS PROYECTOS</p><h2 id="csv-title">Analizar varios proyectos desde un archivo</h2></div></div></div>
        <p className="section-subtitle">Puedes analizar hasta 100 proyectos a la vez. Cada fila del archivo representa un proyecto.</p>
        <div className="csv-controls"><input ref={inputRef} className="visually-hidden" type="file" accept=".csv,text/csv" aria-label="Seleccionar archivo de proyectos" onChange={chooseFile} />
            <button type="button" className="file-picker" onClick={() => inputRef.current?.click()}><span aria-hidden="true">＋</span><strong>{file?.name || 'Seleccionar archivo de proyectos'}</strong><small>Archivo de tabla (.csv) · máximo 5 MB y 100 filas</small></button>
            <a className="secondary-button link-button" href={`${import.meta.env.VITE_API_URL || ''}/api/csv-template`}>Descargar plantilla</a>
            <button type="button" className="primary-button" disabled={!file || loading} onClick={() => onAnalyze(file, '')}>{loading ? <><span className="spinner" /> Analizando archivo…</> : 'Analizar archivo'}</button>
        </div>
        {error && <p className="inline-error" role="alert">{error}</p>}{loading && <p className="loading-note" role="status">Procesando filas con el modelo activo…</p>}
    </section>{results && <CsvResults data={results} />}</div>;
}

function CsvResults({ data }) {
    const successCount = data.rows.filter(row => row.prediction && !row.error).length;
    const showTeamHealth = data.rows.some(row => {
        if (row.error || !row.prediction) return false;
        const score = row.prediction.prediction?.team_health?.score;
        return typeof score === 'number' && Number.isFinite(score);
    });
    const errorColumnSpan = showTeamHealth ? 5 : 4;
    return <section className="surface csv-results" aria-labelledby="csv-results-title"><div className="section-heading"><div><p className="eyebrow">RESULTADOS DEL ARCHIVO</p><h2 id="csv-results-title">{successCount} de {data.count} proyectos analizados</h2></div></div>
        <div className="table-scroll"><table><thead><tr><th>Fila</th><th>Nivel de riesgo</th><th>Retraso</th><th>Sobrecosto</th>{showTeamHealth && <th>Condición del equipo</th>}<th>Estado</th></tr></thead><tbody>{data.rows.map(row => {
            const prediction = row.prediction?.prediction;
            return <tr key={row.row_number}><th scope="row">{row.row_number}</th>{row.error || !prediction ? <td colSpan={errorColumnSpan} className="table-error">{friendlyRowError(row.error)}</td> : <><td><span className={`table-health ${prediction.health}`}>{healthLabels[prediction.health] || prediction.health}</span></td><td>{fmtNumber(prediction.delay_days)} días</td><td>{fmtPct(prediction.cost_overrun_ratio)}</td>{showTeamHealth && <td>{fmtPct(prediction.team_health?.score)}</td>}<td>{statusLabels[prediction.final_status] || prediction.final_status}</td></>}</tr>;
        })}</tbody></table></div></section>;
}

function friendlyRowError(error) {
    if (/cobertura insuficiente/i.test(error || '')) return 'Datos incompletos: no se alcanza la cobertura mínima para analizar esta fila.';
    return 'No fue posible validar los datos de esta fila. Revisa los valores y el formato de la plantilla.';
}