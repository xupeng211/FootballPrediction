#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG22 regression
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG22';

const ADG21 = 'docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_source_validation.adg22.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_SOURCE_VALIDATION_ADG22.md';

const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity, validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d21 = rj(ADG21);
    const results = [];

    for (const t of d21.discovery_results || []) {
        if (t.is_pc) { results.push({ ...t, validation_status: 'positive_control_preserved', rw: false }); continue; }
        if (t.is_suspended) { results.push({ ...t, validation_status: 'suspended_still_blocked', rw: false }); continue; }

        // Validate corrected candidate using source-controlled evidence only (no network)
        const guard = validateStrictFixtureIdentity({
            schedule_external_id: t.external_id,
            detail_external_id_candidate: t.selected_id || t.external_id,
            expected_home_team: t.expH, expected_away_team: t.expA,
            expected_match_date: t.expD, observed_detail_id: t.selected_id,
            observed_home_team: t.selected_home, observed_away_team: t.selected_away,
        });
        const cls = classifyDetailCandidateIdentity({
            schedule_home_team: t.expH, schedule_away_team: t.expA,
            schedule_date: t.expD, source_home_team: t.selected_home,
            source_away_team: t.selected_away, detail_external_id_candidate: t.selected_id,
        });

        const validated = guard.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED &&
            cls.detail_identity_candidate_status === 'accepted_validated';
        results.push({ ...t, validation_status: validated ? 'corrected_candidate_validated_no_write' : 'corrected_candidate_validation_failed',
            guard_status: guard.fixture_identity_guard_status, candidate_status: cls.detail_identity_candidate_status,
            orientation: cls.home_away_orientation, delta: cls.date_delta_days, rw: false, validated });
    }
    return results;
}

function cnt(l, p) { return l.filter(p).length; }

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { corrected_candidate_count: cnt(r, t => !t.is_pc && !t.is_suspended),
        corrected_validated: cnt(r, t => t.validation_status === 'corrected_candidate_validated_no_write'),
        corrected_failed: cnt(r, t => t.validation_status === 'corrected_candidate_validation_failed'),
        old_wrong_leg_rejected: cnt(r, t => t.selection_status === 'rejected_reverse_fixture_mapping'),
        positive_preserved: cnt(r, t => t.is_pc), suspended_blocked: cnt(r, t => t.is_suspended),
        raw_write_ready: 0, re_acceptance: 0 };
    const rec = s.corrected_validated === 5
        ? 'all 5 corrected candidates validated; recommend ADG23 bounded discovery for remaining 27 pending targets; do not raw write'
        : `validated=${s.corrected_validated}/5; fix failures before expanding; do not raw write`;
    return { schema_version: 'adg22_v1', phase: PH, generated_at: g, adg22_status: 'completed_no_write_validation',
        validation_performed: true, no_network: true, no_live_fetch: true, no_db_write: true, no_raw_write: true,
        no_mutation: true, full_payload_saved: false, ...s, recommended_next_step: rec, validation_results: r };
}

function report(a) {
    const l = ['# ADG22 Corrected Source Validation', '', `- Phase: ${a.phase}`,
        `- corrected_validated: ${a.corrected_validated}`, `- corrected_failed: ${a.corrected_failed}`,
        `- old_wrong_leg_rejected: ${a.old_wrong_leg_rejected}`,
        `- suspended_blocked: ${a.suspended_blocked}`, `- raw_write_ready: ${a.raw_write_ready}`,
        '', '## Results', '| id | validation | guard | candidate_status |', '| --- | --- | --- | --- |'];
    for (const t of a.validation_results || []) l.push(`| ${t.external_id} | ${t.validation_status} | ${t.guard_status} | ${t.candidate_status || 'n/a'} |`);
    l.push('', '## Safety', '- no network / DB write / raw write / mutation', '- raw_write_ready=0', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG22 no-write corrected source validation';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ validated: a.corrected_validated, failed: a.corrected_failed, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
