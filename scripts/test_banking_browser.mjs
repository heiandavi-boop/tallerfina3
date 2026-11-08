import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const packageRef = process.env.PRUNIN_PLAYWRIGHT_MODULE || 'playwright-core';
const { chromium } = require(packageRef);
const root = fileURLToPath(new URL('../', import.meta.url));
const baseURL = new URL(process.argv[2] || 'http://127.0.0.1:8001');
assert.ok(['localhost', '127.0.0.1'].includes(baseURL.hostname));
assert.equal(baseURL.protocol, 'http:');
const output = resolve(root, process.argv[3] || 'reports/recommendations_closure_2026-11-08/browser-e2e');
assert.ok(output.startsWith(join(root, 'reports') + sep));
await mkdir(output);
const fixture = join(root, 'tests/fixtures/banking_recommendations.csv');
const expected = {
    planned_duration_weeks: 52, planned_budget: 2500000000, true_progress: 0.47,
    spi: 0.72, cpi: 0.81, team_utilization: 1.12, team_capacity_ratio: 0.72,
    average_productivity: 0.68, rework_ratio: 0.19, defect_rate: 0.11,
    dependency_delay_days: 15, normalized_risk_exposure: 0.49,
};
const report = {
    started_at: new Date().toISOString(), base_url: baseURL.href,
    node: process.version, playwright: require(`${packageRef}/package.json`).version,
    fixture: relative(root, fixture), fixture_sha256: createHash('sha256').update(await readFile(fixture)).digest('hex'),
    recommender_sha256: createHash('sha256').update(await readFile(join(root, 'src/prunin_ai/api/recommendations.py'))).digest('hex'),
    mocked_llm: false, checks: {}, page_errors: [],
};
const writeEvidence = (name, value) => writeFile(join(output, name), JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
let browser;
try {
    browser = await chromium.launch({
        executablePath: process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        headless: true,
    });
    report.browser_version = browser.version();
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on('pageerror', error => report.page_errors.push(error.message));
    const individualRequests = [];
    page.on('request', request => {
        if (request.method() === 'POST' && request.url().endsWith('/api/predict')) individualRequests.push(request.postDataJSON());
    });
    const statusResponse = await context.request.get(new URL('/api/genai-status', baseURL).href);
    assert.equal(statusResponse.status(), 200);
    report.ollama = await statusResponse.json();
    await page.goto(baseURL.href, { waitUntil: 'networkidle' });
    await page.getByRole('tab', { name: 'Analizar varios proyectos', exact: true }).click();
    await page.getByLabel('Seleccionar archivo de proyectos', { exact: true }).setInputFiles(fixture);
    const batchPromise = page.waitForResponse(response => response.url().endsWith('/api/predict-csv'));
    await page.getByRole('button', { name: 'Analizar archivo', exact: true }).click();
    const batchResponse = await batchPromise;
    assert.equal(batchResponse.status(), 200);
    const batch = await batchResponse.json();
    await writeEvidence('batch-response.json', batch);
    assert.equal(batch.count, 1);
    const row = batch.rows[0];
    assert.equal(row.error, null);
    assert.equal(row.prediction.recommendations.engine, 'not_requested');
    assert.equal(row.prediction.recommendations.genai_attempted, false);
    assert.equal(row.prediction.timing.genai_ms, null);
    assert.equal(individualRequests.length, 0);
    for (const [feature, value] of Object.entries(expected)) assert.equal(row.input[feature], value);
    report.checks.csv_validated_without_llm = true;
    const individualPromise = page.waitForResponse(response => response.url().endsWith('/api/predict'), { timeout: 45000 });
    await page.getByRole('button', { name: 'Ver análisis completo de fila 1', exact: true }).click();
    const individualResponse = await individualPromise;
    assert.equal(individualResponse.status(), 200);
    const body = await individualResponse.json();
    await writeEvidence('individual-response.json', body);
    assert.equal(individualRequests.length, 1);
    assert.deepEqual(individualRequests[0], row.input);
    assert.deepEqual(body.input, row.input);
    assert.deepEqual(body.prediction, row.prediction.prediction);
    report.checks.individual_preserves_input_and_ml = true;
    const recommendation = body.recommendations;
    report.engine = recommendation.engine;
    report.genai_used = recommendation.genai_used;
    report.genai_failure_code = recommendation.failure_code;
    const validation = recommendation.genai_used ? recommendation.grounding : recommendation.fallback_validation;
    assert.equal(validation.grounded, true);
    if (report.ollama.enabled && report.ollama.available) assert.equal(recommendation.genai_used, true);
    else assert.equal(recommendation.engine, 'grounded_fallback');
    const evidence = recommendation.evidence_context;
    const pairs = new Set(evidence.actionable_evidence.map(item => `${item.source}:${item.feature}`));
    const actions = recommendation.recommendations;
    assert.ok(actions.length >= 1 && actions.length <= 4);
    assert.equal(new Set(actions.map(item => item.evidence_feature)).size, actions.length);
    for (const action of actions) {
        assert.ok(pairs.has(`${action.evidence_source}:${action.evidence_feature}`));
        assert.ok(['alta', 'media', 'baja'].includes(action.priority));
        assert.ok(action.reason && action.action && action.follow_up);
    }
    for (const signal of evidence.operational_signals) {
        assert.equal(signal.source, 'observed_operational_signal');
        assert.equal(signal.value, body.input[signal.feature]);
        assert.equal(signal.rule.heuristic, true);
    }
    report.checks.action_evidence_and_provenance_valid = true;
    await page.locator('#recommendations .recommendation-action').first().waitFor();
    assert.equal(await page.getByText(recommendation.summary, { exact: true }).count(), 1);
    assert.equal(await page.locator('#recommendations .recommendation-action').count(), actions.length);
    const priorities = await page.locator('#recommendations .recommendation-priority').allTextContents();
    const order = { Alta: 0, Media: 1, Baja: 2 };
    assert.deepEqual(priorities.map(priority => order[priority]), priorities.map(priority => order[priority]).sort());
    report.checks.unique_summary_and_priority_order = true;
    await page.locator('#recommendations').screenshot({ path: join(output, 'desktop.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    report.mobile = await page.evaluate(() => ({
        viewport_width: innerWidth, document_width: document.documentElement.scrollWidth,
        card_overflow: [...document.querySelectorAll('#recommendations .recommendation-action')].some(card => card.scrollWidth > card.clientWidth + 1),
    }));
    assert.ok(report.mobile.document_width <= report.mobile.viewport_width);
    assert.equal(report.mobile.card_overflow, false);
    await page.locator('#recommendations').screenshot({ path: join(output, 'mobile.png') });
    report.checks.mobile_layout = true;
    await page.getByRole('button', { name: 'Ver evidencia técnica', exact: true }).first().click();
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await page.getByRole('button', { name: 'Descargar resultados', exact: true }).click();
    const download = await downloadPromise;
    await download.saveAs(join(output, 'technical-download.json'));
    assert.equal(await download.failure(), null);
    const downloaded = JSON.parse(await readFile(join(output, 'technical-download.json'), 'utf8'));
    assert.deepEqual(downloaded, body);
    report.download_name = download.suggestedFilename();
    report.download_sha256 = createHash('sha256').update(await readFile(join(output, 'technical-download.json'))).digest('hex');
    report.checks.download_matches_individual_response = true;
    assert.deepEqual(report.page_errors, []);
    report.checks.no_browser_errors = true;
    report.status = 'passed';
} catch (error) {
    report.status = 'failed';
    report.error = error.message;
    process.exitCode = 1;
} finally {
    report.finished_at = new Date().toISOString();
    await writeEvidence('browser-report.json', report);
    await browser?.close();
}
console.log(JSON.stringify(report, null, 2));