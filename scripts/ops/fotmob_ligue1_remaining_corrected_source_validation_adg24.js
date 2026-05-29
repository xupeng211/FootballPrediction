#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG24 regression
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG24';
const ADG23 = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_discovery.adg23.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_validation.adg24.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_REMAINING_CORRECTED_SOURCE_VALIDATION_ADG24.md';

const { validateStrictFixtureIdentity, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d23 = rj(ADG23); const results = [];
    for (const t of d23.discovery_results || []) {
        if (t.is_pc) { results.push({ ...t, validation_status: 'positive_control_preserved', rw: false }); continue; }
        if (t.is_suspended) { results.push({ ...t, validation_status: 'suspended_still_blocked', rw: false }); continue; }
        if (t.is_adg22_control) { results.push({ ...t, validation_status: 'adg22_validated_control_preserved', rw: false }); continue; }

        const guard = validateStrictFixtureIdentity({
            schedule_external_id: t.external_id, detail_external_id_candidate: t.selected_id || t.external_id,
            expected_home_team: t.expH, expected_away_team: t.expA, expected_match_date: t.expD,
            observed_detail_id: t.selected_id, observed_home_team: t.selected_home, observed_away_team: t.selected_away });
        const cls = classifyDetailCandidateIdentity({
            schedule_home_team: t.expH, schedule_away_team: t.expA, schedule_date: t.expD,
            source_home_team: t.selected_home, source_away_team: t.selected_away,
            detail_external_id_candidate: t.selected_id });

        const ok = guard.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED &&
            cls.detail_identity_candidate_status === 'accepted_validated';
        results.push({ ...t, validation_status: ok ? 'corrected_candidate_validated_no_write' : 'corrected_candidate_validation_failed',
            guard_status: guard.fixture_identity_guard_status, candidate_status: cls.detail_identity_candidate_status,
            orientation: cls.home_away_orientation, delta: cls.date_delta_days, rw: false, validated: ok });
    }
    return results;
}

function cnt(l, p) { return l.filter(p).length; }
function build() {
    const g = new Date().toISOString(); const r = run();
    const remaining = r.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control);
    const s = { corrected_count: remaining.length,
        validated: cnt(remaining, t => t.validation_status === 'corrected_candidate_validated_no_write'),
        failed: cnt(remaining, t => t.validation_status === 'corrected_candidate_validation_failed'),
        adg22_controls: cnt(r, t => t.is_adg22_control),
        positive: cnt(r, t => t.is_pc), suspended: cnt(r, t => t.is_suspended),
        raw_write_ready: 0, re_acceptance: 0 };
    const rec = s.validated === 27
        ? 'all 27 corrected candidates validated; recommend ADG25 corrected generation preview for 32 validated candidates; do not raw write'
        : `${s.validated}/27 validated; fix failures before generation preview; do not raw write`;
    return { schema_version: 'adg24_v1', phase: PH, generated_at: g, adg24_status: 'completed_no_write_validation',
        validation_performed: true, no_network: true, no_db_write: true, no_raw_write: true, no_mutation: true,
        full_payload_saved: false, ...s, recommended_next_step: rec, validation_results: r };
}

function report(a) {
    const l = ['# ADG24 Remaining Corrected Source Validation', '', `- Phase: ${a.phase}`,
        `- corrected_validated: ${a.validated}`, `- corrected_failed: ${a.failed}`,
        `- adg22_controls: ${a.adg22_controls}`, `- positive: ${a.positive}, suspended: ${a.suspended}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Results', '| id | validation | guard | candidate_status |', '| --- | --- | --- | --- |'];
    for (const t of a.validation_results.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control))
        {l.push(`| ${t.external_id} | ${t.validation_status} | ${t.guard_status} | ${t.candidate_status} |`);}
    l.push('', '## Safety', '- no network / DB write / raw write / mutation', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG24 remaining corrected source validation';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ validated: a.validated, failed: a.failed, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
