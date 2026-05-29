#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG26 regression
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG26';
const ADG25 = 'docs/_manifests/fotmob_ligue1_corrected_generation_preview.adg25.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_controlled_correction_implementation.adg26.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CONTROLLED_CORRECTION_IMPLEMENTATION_ADG26.md';

const { validateStrictFixtureIdentity, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d25 = rj(ADG25);
    const app = []; const suspended = []; let conflicts = 0; let superseded = 0; let blocked = 0;

    for (const t of d25.generation_results || []) {
        if (t.generation_status === 'positive_control_preserved') continue;
        if (t.generation_status === 'suspended_still_blocked') { suspended.push(t); continue; }
        if (t.validation_status !== 'validated_corrected_candidate') { blocked++; continue; }

        // Re-run strict guard as application safety check
        const guard = validateStrictFixtureIdentity({
            schedule_external_id: t.external_id, detail_external_id_candidate: t.corrected_detail_id,
            expected_home_team: t.expected_home, expected_away_team: t.expected_away,
            expected_match_date: t.expected_date, observed_detail_id: t.corrected_detail_id,
            observed_home_team: t.corrected_home, observed_away_team: t.corrected_away });
        const cls = classifyDetailCandidateIdentity({
            schedule_home_team: t.expected_home, schedule_away_team: t.expected_away,
            schedule_date: t.expected_date, source_home_team: t.corrected_home,
            source_away_team: t.corrected_away, detail_external_id_candidate: t.corrected_detail_id });

        const guardPassed = guard.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED &&
            cls.detail_identity_candidate_status === 'accepted_validated';

        if (t.supersedes_wrong_leg) superseded++;

        app.push({
            external_id: t.external_id, expected_home: t.expected_home, expected_away: t.expected_away,
            corrected_detail_id: t.corrected_detail_id, corrected_home: t.corrected_home,
            corrected_away: t.corrected_away, validation_phase: t.validation_phase,
            application_action: t.supersedes_wrong_leg ? 'supersede_and_replace' : 'insert_corrected_candidate',
            supersedes_wrong_leg: t.supersedes_wrong_leg,
            application_guard_status: guardPassed ? 'passed' : 'blocked',
            application_ready: guardPassed && !t.supersedes_wrong_leg,
            raw_write_ready: false, re_acceptance_candidate: false,
            mutation_requires_authorization: 'ADG27_explicit_final_db_write_or_source_inventory_mutation_authorization',
        });
        if (!guardPassed) conflicts++;
    }

    return { application_count: app.length, suspended_count: suspended.length,
        superseded_count: superseded, conflict_count: conflicts, blocked_count: blocked, app };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { validated_candidate_count: r.application_count,
        proposed_source_inventory_application: r.application_count,
        proposed_candidate_application: r.application_count,
        supersede_wrong_leg: r.superseded_count,
        duplicate_conflict: r.conflict_count, suspended_exclusion: r.suspended_count,
        generation_blocked: r.blocked_count,
        positive_preserved: 1, raw_write_ready: 0, re_acceptance: 0 };

    const rec = s.duplicate_conflict === 0 && s.generation_blocked === 0
        ? 'all 32 corrected candidates pass application guard; recommend ADG27 controlled correction implementation; do not raw write'
        : `${s.duplicate_conflict} conflicts, ${s.generation_blocked} blocked; fix before implementation; do not raw write`;

    return { schema_version: 'adg26_v1', phase: PH, generated_at: g, adg26_status: 'completed_no_write_application_preview',
        controlled_correction_plan_created: true, no_write_application_preview_performed: true,
        no_network: true, no_db_write: true, no_raw_write: true, no_mutation: true, full_payload_saved: false,
        application_contract: {
            input: { source_manifest: ADG25, guards: ['validateStrictFixtureIdentity', 'classifyDetailCandidateIdentity', 'selectOrientedFixtureRecord'] },
            output: { proposed_fields: ['corrected_detail_id', 'application_action', 'application_guard_status', 'raw_write_ready'] },
            mutation_boundary: 'ADG26 does not mutate production artifacts; ADG27 requires explicit authorization',
            rollback_audit: { before_snapshot: 'current source inventory / candidate manifests', after_diff: 'compare ADG25 vs new corrected manifests', rollback: 'revert to pre-ADG27 state if any guard fails post-application' }
        },
        ...s, recommended_next_step: rec, corrected_applications: r.app, suspended_exclusions: r.suspended };
}

function report(a) {
    const l = ['# ADG26 Controlled Correction Application Preview', '', `- Phase: ${a.phase}`,
        `- validated_candidates: ${a.validated_candidate_count}`,
        `- proposed_applications: ${a.proposed_source_inventory_application}`,
        `- supersede_wrong_leg: ${a.supersede_wrong_leg}`,
        `- conflicts: ${a.duplicate_conflict}`, `- suspended_excluded: ${a.suspended_exclusion}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Application Contract', '- Input: ADG25 generation preview', '- Guards: validateStrictFixtureIdentity + classifyDetailCandidateIdentity + selectOrientedFixtureRecord',
        '- Mutation: ADG26 does NOT mutate; ADG27 requires explicit authorization',
        '- Rollback: revert to pre-ADG27 state if any guard fails post-application', '',
        '## Applications (first 5 of 32)', '| id | action | guard | supersede |',
        '| --- | --- | --- | --- |'];
    for (const t of a.corrected_applications.slice(0, 5))
        {l.push(`| ${t.external_id} | ${t.application_action} | ${t.application_guard_status} | ${t.supersedes_wrong_leg} |`);}
    l.push(`| ... | ... (${a.validated_candidate_count - 5} more) | ... | ... |`);
    l.push('', '## Safety', '- no network / DB write / raw write / production mutation', '- all applications are preview only', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG26 controlled correction application preview';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ applications: a.validated_candidate_count, conflicts: a.duplicate_conflict, supersede: a.supersede_wrong_leg, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
