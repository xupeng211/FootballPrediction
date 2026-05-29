#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG38 validation
/* eslint-disable complexity, no-promise-executor-return */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG38';
const PLAN = 'docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_planning.adg31.json';
const ENR = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_route_code_reexecution.adg38.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_BOUNDED_L2_DETAIL_FETCH_ROUTE_CODE_REEXECUTION_ADG38.md';
const DELAY_MIN = 10000; const DELAY_MAX = 15000;
const { buildCorrectedFotmobDetailUrl, validateStrictFixtureIdentity, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const { extractFromHtml } = require('../../src/parsers/fotmob/NextDataParser');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchOne(url) {
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 20000);
    try { const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51)' } });
        clearTimeout(t); if (res.status !== 200) return { http: res.status, html: null };
        return { http: 200, html: await res.text() }; }
    catch (e) { clearTimeout(t); return { http: 0, html: null, error: e.message }; }
}

async function run() {
    const plan = rj(PLAN); const enrichedMap = new Map();
    for (const t of rj(ENR).enriched_targets || []) if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t);
    const results = []; let stopped = false; let attempts = 0;

    for (const s of plan.planned_samples || []) {
        if (stopped) { results.push({ ...s, status: 'not_attempted', rw: false }); continue; }
        const enr = enrichedMap.get(s.target_id) || {};
        const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: s.corrected_detail, expectedHomeTeam: s.expected_home, expectedAwayTeam: s.expected_away, historicalSourcePageUrl: enr.source_page_url || null });
        if (!built.ok) { results.push({ ...s, status: 'url_construction_failed', rw: false, reason: built.reason }); stopped = true; continue; }
        // ADG38 critical check: 4830473 must NOT use 2o4ahb
        if (s.target_id === '4830473' && built.url.includes('2o4ahb')) { results.push({ ...s, status: 'route_code_regression', rw: false }); stopped = true; continue; }
        const { http, html } = await fetchOne(built.url); attempts++;
        if (http !== 200 || !html) { if (http === 403 || http === 0) stopped = true;
            results.push({ ...s, status: http === 403 ? 'blocked_403' : 'network_error', http, rw: false, url: built.url }); continue; }
        const parsed = extractFromHtml(html); const pp = parsed?.data?.props?.pageProps; const g = pp?.general || {};
        const oh = g.homeTeam?.name || null; const oa = g.awayTeam?.name || null; const od = String(g.matchId || pp?.matchId || '');
        if (!oh || !oa) { results.push({ ...s, status: 'hydration_identity_missing', http, rw: false, url: built.url }); continue; }
        const guard = validateStrictFixtureIdentity({ schedule_external_id: s.target_id, detail_external_id_candidate: s.corrected_detail,
            expected_home_team: s.expected_home, expected_away_team: s.expected_away, observed_detail_id: od, observed_home_team: oh, observed_away_team: oa });
        const cls = classifyDetailCandidateIdentity({ schedule_home_team: s.expected_home, schedule_away_team: s.expected_away,
            source_home_team: oh, source_away_team: oa, detail_external_id_candidate: s.corrected_detail });
        const ok = guard.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED && cls.detail_identity_candidate_status === 'accepted_validated';
        if (s.target_id === '4830473' && !ok) stopped = true;
        results.push({ ...s, status: ok ? 'success_validated_no_write' : 'validation_failed', http, observed_id: od,
            observed_home: oh, observed_away: oa, guard: guard.fixture_identity_guard_status, orientation: cls.home_away_orientation,
            rw: false, url: built.url, route_code_verified: s.target_id === '4830473' && ok });
        if (plan.planned_samples.indexOf(s) < plan.planned_samples.length - 1 && !stopped) {
            const d = Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1) + DELAY_MIN); await sleep(d); }
    }
    return { results, attempts, total: plan.planned_samples.length };
}
function cnt(l, p) { return l.filter(p).length; }
function build(d) {
    const g = new Date().toISOString(); const r = d.results || [];
    const r0 = r[0] || {};
    return { schema_version: 'adg38_v1', phase: PH, generated_at: g, adg38_status: 'completed_route_code_reexecution',
        planned: d.total, attempted: d.attempts,
        success: cnt(r, t => t.status === 'success_validated_no_write'),
        validation_failed: cnt(r, t => t.status === 'validation_failed'),
        not_attempted: cnt(r, t => t.status === 'not_attempted'),
        route_code_fix_verified: r0.status === 'success_validated_no_write',
        a4830473_orientation: r0.orientation || 'unknown',
        rw: 0, re_acceptance: 0,
        recommended_next_step: r0.status === 'success_validated_no_write'
            ? 'ADG39: route code fix verified; consider broader corrected L2 strategy; do not raw write'
            : 'ADG39: investigate remaining route code / detail ID issues; do not raw write',
        no_browser: true, no_proxy: true, no_db_write: true, no_raw_write: true, full_payload_saved: false,
        fetch_results: r };
}
function report(a) {
    const l = ['# ADG38 Route Code Fix Verification', '', `- Phase: ${a.phase}`, `- planned: ${a.planned}`, `- attempted: ${a.attempted}`,
        `- success: ${a.success}`, `- validation_failed: ${a.validation_failed}`, `- route_code_fix_verified: ${a.route_code_fix_verified}`,
        `- 4830473_orientation: ${a.a4830473_orientation}`, `- rw: ${a.rw}`, '',
        '## Results', '| id | status | observed | orientation |', '| --- | --- | --- | --- |'];
    for (const t of a.fetch_results) l.push(`| ${t.target_id} | ${t.status} | ${t.observed_home || '?'} vs ${t.observed_away || '?'} | ${t.orientation || '?'} |`);
    l.push('', '## Next', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}
async function main() {
    process.stdout.write('ADG38: verifying route code fix — 4830473 first\n');
    const d = await run(); const a = build(d); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG38 route code fix verification';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ success: a.success, verified: a.route_code_fix_verified, orientation: a.a4830473_orientation, rw: a.rw }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { main().then(r => process.exitCode = r.status).catch(e => { process.stderr.write(e.stack + '\n'); process.exitCode = 1; }); }
