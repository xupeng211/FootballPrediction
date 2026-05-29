#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG29
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG29';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const CAND = 'docs/_manifests/fotmob_ligue1_corrected_candidates.adg27.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_pipeline_integration_preview.adg29.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_PIPELINE_INTEGRATION_PREVIEW_ADG29.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const si_required = ['external_id', 'corrected_detail_id', 'expected_home', 'expected_away'];
    const l2_required = [...si_required, 'corrected_home', 'corrected_away'];
    let siReady = 0, candReady = 0, l2Ready = 0, siMissing = 0, l2Missing = 0;
    const issues = [];

    for (const s of src) {
        const siOK = si_required.every(f => s[f]);
        const l2OK = l2_required.every(f => s[f]);
        if (siOK) siReady++; else { siMissing++; issues.push({ external_id: s.external_id, issue: 'source_inventory_fields_missing', missing: si_required.filter(f => !s[f]) }); }
        if (l2OK) l2Ready++; else { l2Missing++; issues.push({ external_id: s.external_id, issue: 'l2_identity_fields_missing', missing: l2_required.filter(f => !s[f]) }); }
    }

    const cand = rj(CAND).corrected_candidate_records || [];
    candReady = cand.length;

    return { si_count: src.length, si_ready: siReady, si_missing: siMissing,
        cand_count: cand.length, cand_ready: candReady,
        l2_ready: l2Ready, l2_missing: l2Missing, issues };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const gaps = [];
    if (r.si_missing > 0) gaps.push('some records missing source inventory required fields');
    if (r.l2_missing > 0) gaps.push(`${r.l2_missing} records missing L2 detail identity fields`);
    const s = { si_count: r.si_count, si_ready: r.si_ready, cand_ready: r.cand_ready,
        l2_ready: r.l2_ready, l2_missing: r.l2_missing,
        pipeline_gaps: gaps, raw_write_ready: 0, re_acceptance: 0 };
    const rec = r.l2_ready === 32
        ? '32/32 records have complete L1→L2 identity; recommend ADG30 L2 detail-fetch readiness no-write planning; do not raw write'
        : `${r.l2_missing} records need identity completion before L2 handoff; do not raw write`;
    return { schema_version: 'adg29_v1', phase: PH, generated_at: g, adg29_status: 'completed_pipeline_integration_preview',
        pipeline_integration_preview_performed: true, no_network: true, no_db_write: true, no_raw_write: true,
        full_payload_saved: false, ...s, recommended_next_step: rec, integration_issues: r.issues };
}

function report(a) {
    const l = ['# ADG29 Pipeline Integration Preview', '', `- Phase: ${a.phase}`,
        `- si_records: ${a.si_count}`, `- si_ready: ${a.si_ready}`,
        `- cand_ready: ${a.cand_ready}`, `- l2_ready: ${a.l2_ready}`,
        `- l2_missing: ${a.l2_missing}`,
        `- pipeline_gaps: ${a.pipeline_gaps.length === 0 ? 'none' : a.pipeline_gaps.join('; ')}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Safety', '- no network / DB write / raw write', '', '## Next', '', a.recommended_next_step];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG29 corrected pipeline integration preview';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ si_ready: a.si_ready, cand_ready: a.cand_ready, l2_ready: a.l2_ready, l2_missing: a.l2_missing, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
