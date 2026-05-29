#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG30
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG30';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_l2_detail_fetch_readiness.adg30.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_L2_DETAIL_FETCH_READINESS_ADG30.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const l2Ready = []; const l2Blocked = {};
    const l2ReqFields = ['external_id', 'corrected_detail_id', 'expected_home', 'expected_away'];

    for (const s of src) {
        const ok = l2ReqFields.every(f => s[f]);
        if (ok) l2Ready.push(s);
        else { const missing = l2ReqFields.filter(f => !s[f]); l2Blocked[s.external_id || '?'] = missing; }
    }

    // Contract definitions — source-controlled, no network, no fetch
    const inputContract = { required_fields: l2ReqFields, detail_identity: 'corrected_detail_external_id from corrected source inventory', home_away: 'expected_home / expected_away from corrected source inventory',
        identity_source: 'ADG27 corrected source inventory artifact', strict_guard: 'validateStrictFixtureIdentity + classifyDetailCandidateIdentity + selectOrientedFixtureRecord' };
    const requestContract = { path: 'FotMob match detail page-route (html_hydration)', identity: 'corrected_detail_external_id',
        locale: 'zh-Hans (default, can be adjusted)', risk: 'direct API 403 known; public page-route safer; requires explicit authorization',
        bounded: 'max 1 request per target, 10-15s delay, stop on 403/block' };
    const responseContract = { detail_id: 'must match corrected_detail_external_id', home_team: 'must match expected_home',
        away_team: 'must match expected_away', date: 'must be close to expected_match_date',
        wrong_leg: 'rejected if home/away reversed or date delta > tolerance', raw_write: 'remains false until post-fetch no-write validation' };
    const outputContract = { safe_fields: ['target_match_id','corrected_detail_external_id','expected_home','expected_away','observed_home_if_fetched','observed_away_if_fetched','detail_validation_status','raw_write_ready=false'],
        no_full_body: true, no_full_pageprops: true, no_full_raw_data: true };
    return { candidates: src.length, l2_ready: l2Ready.length, l2_blocked: Object.keys(l2Blocked).length,
        input_contract: inputContract, request_contract: requestContract,
        response_contract: responseContract, output_contract: outputContract };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { candidates: r.candidates, l2_ready: r.l2_ready, l2_blocked: r.l2_blocked, raw_write_ready: 0, re_acceptance: 0 };
    const rec = r.l2_ready === 32
        ? '32/32 L2 detail-fetch ready; recommend ADG31 bounded L2 detail-fetch execution planning; do not bypass 403; do not raw write'
        : `${r.l2_blocked} candidates blocked; fix identity before L2 fetch; do not raw write`;
    return { schema_version: 'adg30_v1', phase: PH, generated_at: g, adg30_status: 'completed_l2_readiness_preview',
        l2_readiness_preview_performed: true, no_network: true, no_db_write: true, no_raw_write: true,
        no_live_fetch: true, full_payload_saved: false,
        input_contract: r.input_contract, request_contract: r.request_contract,
        response_contract: r.response_contract, output_contract: r.output_contract,
        ...s, recommended_next_step: rec };
}

function report(a) {
    const l = ['# ADG30 L2 Detail-Fetch Readiness', '', `- Phase: ${a.phase}`,
        `- candidates: ${a.candidates}`, `- l2_ready: ${a.l2_ready}`, `- l2_blocked: ${a.l2_blocked}`,
        '', '## Contracts', '- Input: corrected_detail_external_id + expected_home/away from ADG27',
        '- Request: FotMob match detail page-route (html_hydration), bounded, stop on 403',
        '- Response: detail_id must match, home/away must match, wrong-leg rejected',
        '- Output: safe fields only, no full body/pageProps/raw_data',
        '', '## Blocker', '- direct API 403 risk documented; public page-route preferred',
        '- raw_write remains false until post-fetch no-write ADG validation',
        '', '## Next', '', a.recommended_next_step];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const c = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG30 L2 detail-fetch readiness preview';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), c.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ l2_ready: a.l2_ready, l2_blocked: a.l2_blocked, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
