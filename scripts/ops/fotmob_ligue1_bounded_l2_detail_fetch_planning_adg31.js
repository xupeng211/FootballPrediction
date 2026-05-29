#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG31
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG31';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_planning.adg31.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_BOUNDED_L2_DETAIL_FETCH_PLANNING_ADG31.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    // Select 3 samples deterministically: first, middle, last
    const samples = [src[0], src[15], src[31]].filter(Boolean).map((s, i) => ({
        target_id: s.external_id,
        corrected_detail: s.corrected_detail_id,
        expected_home: s.expected_home, expected_away: s.expected_away,
        reason: i === 0 ? 'first_corrected_candidate' : i === 1 ? 'mid_range_sample' : 'last_corrected_candidate',
        planned_requests: 1, raw_write_ready: false }));
    const contract = {
        request: { max_samples: 3, max_per_target: 1, delay: '10-15 seconds', path: 'FotMob html_hydration page-route',
            identity: 'corrected_detail_external_id', no_browser: true, no_proxy: true, stop_on_403: true,
            requires_explicit_authorization: true },
        response: { no_full_html: true, no_full_pageprops: true, no_full_raw_data: true, in_memory_parse_only: true },
        validation: { detail_id_match: true, home_away_match: true, wrong_leg_reject: true, raw_write_remains_false: true },
        output: { safe_fields: ['target_id','corrected_detail','request_status','http_status','observed_home_if_safe','observed_away_if_safe','validation','raw_write_ready=false'] },
        risks: ['direct API 403 known', 'public page-route preferred', 'anti-bot/block risk', 'no browser/proxy bypass'],
    };
    return { samples, total_candidates: src.length, planned_count: samples.length, planned_requests: samples.length,
        ready_for_fetch: samples.length, blocked: 0, raw_write_ready: 0, contract };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { total: r.total_candidates, planned: r.planned_count, planned_requests: r.planned_requests,
        ready: r.ready_for_fetch, blocked: r.blocked, raw_write_ready: 0, re_acceptance: 0 };
    return { schema_version: 'adg31_v1', phase: PH, generated_at: g, adg31_status: 'completed_fetch_planning',
        execution_planning_performed: true, no_live_fetch: true, no_network: true, no_db_write: true, no_raw_write: true,
        full_payload_saved: false, future_execution_contract: r.contract,
        ...s, planned_samples: r.samples,
        recommended_next_step: 'ADG32 bounded L2 detail-fetch execution for 3 planned samples; requires explicit user authorization; do not fetch until authorized; do not raw write' };
}

function report(a) {
    const l = ['# ADG31 Bounded L2 Detail-Fetch Planning', '', `- Phase: ${a.phase}`,
        `- total_candidates: ${a.total}`, `- planned_samples: ${a.planned}`,
        `- ready: ${a.ready}`, `- blocked: ${a.blocked}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Planned Samples', '| id | corrected_detail | expected | reason |',
        '| --- | --- | --- | --- |'];
    for (const s of a.planned_samples) l.push(`| ${s.target_id} | ${s.corrected_detail} | ${s.expected_home} vs ${s.expected_away} | ${s.reason} |`);
    l.push('', '## Contract', '- Request: html_hydration page-route, max 3 samples, 1 req/target, stop on 403',
        '- Response: in-memory parse, no full HTML/pageProps/raw_data saved',
        '- Validation: detail_id match, home/away match, wrong-leg rejected',
        '- Output: safe fields only, raw_write_ready=false',
        '- Risks: direct API 403 known, anti-bot/block risk, no browser/proxy bypass',
        '', '## Authorization', 'ADG32 execution requires EXPLICIT user authorization. Do NOT fetch until authorized.',
        '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const c = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG31 bounded L2 detail-fetch planning';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), c.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ planned: a.planned, ready: a.ready, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
