#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG28 regression
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG28';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const CAND = 'docs/_manifests/fotmob_ligue1_corrected_candidates.adg27.json';
const AUDIT = 'docs/_manifests/fotmob_ligue1_controlled_correction_audit.adg27.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_artifacts_regression.adg28.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_ARTIFACTS_REGRESSION_ADG28.md';

const { validateStrictFixtureIdentity, classifyDetailCandidateIdentity, FIXTURE_IDENTITY_GUARD_PASSED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const cand = rj(CAND).corrected_candidate_records || [];
    const audit = rj(AUDIT);
    const results = [];
    let missing = 0, guardFailed = 0;

    for (let i = 0; i < src.length; i++) {
        const s = src[i]; const c = cand[i];
        const required = ['external_id','corrected_detail_id','expected_home','expected_away','guard_status'];
        const missingFields = required.filter(f => !s[f]);
        if (missingFields.length > 0) { missing++; results.push({ external_id: s.external_id || '?', issue: `missing_fields: ${missingFields.join(',')}`, status: 'missing_required_field' }); continue; }
        const guard = validateStrictFixtureIdentity({ schedule_external_id: s.external_id, detail_external_id_candidate: s.corrected_detail_id,
            expected_home_team: s.expected_home, expected_away_team: s.expected_away,
            observed_detail_id: s.corrected_detail_id, observed_home_team: s.corrected_home, observed_away_team: s.corrected_away });
        if (guard.fixture_identity_guard_status !== FIXTURE_IDENTITY_GUARD_PASSED) { guardFailed++; results.push({ external_id: s.external_id, issue: 'guard_failed', status: 'validation_failed' }); continue; }
        results.push({ external_id: s.external_id, expected: `${s.expected_home} vs ${s.expected_away}`, corrected_id: s.corrected_detail_id, guard: 'passed', rw: false, status: 'validated_no_write' });
    }

    return { source_count: src.length, candidate_count: cand.length, validated: results.filter(r => r.status === 'validated_no_write').length,
        missing, guardFailed, audit_consistent: audit.failures === 0 && audit.source_inventory_count === src.length,
        raw_write_ready: 0, results };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { source_count: r.source_count, candidate_count: r.candidate_count,
        validated: r.validated, missing: r.missing, guard_failed: r.guardFailed,
        audit_consistent: r.audit_consistent, raw_write_ready: 0, re_acceptance: 0 };
    const rec = s.validated === 32 && s.missing === 0 && s.guard_failed === 0
        ? '32/32 corrected artifacts validated; recommend ADG29 corrected pipeline integration preview; do not raw write'
        : 'validation issues found; fix before ADG29; do not raw write';
    return { schema_version: 'adg28_v1', phase: PH, generated_at: g, adg28_status: 'completed_no_write_regression',
        regression_performed: true, no_network: true, no_db_write: true, no_raw_write: true, no_mutation: true,
        full_payload_saved: false, ...s, recommended_next_step: rec, regression_results: r.results };
}

function report(a) {
    const l = ['# ADG28 Corrected Artifacts Regression', '', `- Phase: ${a.phase}`,
        `- source_records: ${a.source_count}`, `- candidate_records: ${a.candidate_count}`,
        `- validated: ${a.validated}`, `- missing_fields: ${a.missing}`,
        `- guard_failed: ${a.guard_failed}`, `- audit_consistent: ${a.audit_consistent}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Safety', '- no network / DB write / raw write', '- raw_write_ready=0', '', '## Next', '', a.recommended_next_step];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG28 corrected artifacts regression';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ source: a.source_count, validated: a.validated, missing: a.missing, guard_failed: a.guard_failed, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
