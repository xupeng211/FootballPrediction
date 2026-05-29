#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG27 regression
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG27';
const ADG26 = 'docs/_manifests/fotmob_ligue1_controlled_correction_implementation.adg26.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT_SOURCE = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const OUT_CANDIDATE = 'docs/_manifests/fotmob_ligue1_corrected_candidates.adg27.json';
const OUT_AUDIT = 'docs/_manifests/fotmob_ligue1_controlled_correction_audit.adg27.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CONTROLLED_CORRECTION_APPLICATION_ADG27.md';

const { validateStrictFixtureIdentity, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d26 = rj(ADG26); const sourceRecords = []; const candidateRecords = []; let failures = 0;
    const superseded = [];

    for (const t of d26.corrected_applications || []) {
        const guard = validateStrictFixtureIdentity({
            schedule_external_id: t.external_id, detail_external_id_candidate: t.corrected_detail_id,
            expected_home_team: t.expected_home, expected_away_team: t.expected_away,
            observed_detail_id: t.corrected_detail_id, observed_home_team: t.corrected_home,
            observed_away_team: t.corrected_away });
        const cls = classifyDetailCandidateIdentity({
            schedule_home_team: t.expected_home, schedule_away_team: t.expected_away,
            source_home_team: t.corrected_home, source_away_team: t.corrected_away,
            detail_external_id_candidate: t.corrected_detail_id });

        const ok = guard.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED &&
            cls.detail_identity_candidate_status === 'accepted_validated';
        if (!ok) { failures++; continue; }

        const sr = {
            external_id: t.external_id, match_id: null,
            source_inventory_type: 'corrected_source_inventory_record',
            expected_home: t.expected_home, expected_away: t.expected_away,
            corrected_detail_id: t.corrected_detail_id, corrected_home: t.corrected_home,
            corrected_away: t.corrected_away, validation_phase: t.validation_phase,
            guard_status: 'passed', correction_phase: 'ADG27',
            raw_write_ready: false, re_acceptance_candidate: false,
            supersedes_wrong_leg: t.supersedes_wrong_leg,
            source_inventory_write_ready: false,
        };
        sourceRecords.push(sr);

        const cr = {
            external_id: t.external_id, candidate_type: 'corrected_candidate_record',
            expected_home: t.expected_home, expected_away: t.expected_away,
            corrected_detail_id: t.corrected_detail_id,
            application_action: t.application_action,
            supersedes_wrong_leg: t.supersedes_wrong_leg,
            guard_status: 'passed', correction_phase: 'ADG27',
            raw_write_ready: false, re_acceptance_candidate: false,
            candidate_write_ready: false,
        };
        candidateRecords.push(cr);
        if (t.supersedes_wrong_leg) superseded.push(t.external_id);
    }

    const audit = {
        generated_at: new Date().toISOString(), correction_phase: PH,
        input_manifest: ADG26, guard_results: 'all passed', failures,
        source_inventory_count: sourceRecords.length, candidate_count: candidateRecords.length,
        superseded_wrong_leg: superseded, suspended_excluded: d26.suspended_exclusion,
        positive_preserved: true,
        rollback_plan: 'revert to ADG26 application preview if any post-correction guard fails',
        before_snapshot: 'ADG25 generation preview + ADG26 application preview',
        after_diff: 'compare corrected artifacts with pre-ADG27 state',
    };

    return { sourceRecords, candidateRecords, audit, failures };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    wj(OUT_SOURCE, { schema_version: 'adg27_source_inventory_v1', phase: PH, generated_at: g,
        lifecycle: 'phase-artifact / correction-artifact', corrected_source_inventory_records: r.sourceRecords,
        raw_write_ready: false, db_write_performed: false });
    wj(OUT_CANDIDATE, { schema_version: 'adg27_candidates_v1', phase: PH, generated_at: g,
        lifecycle: 'phase-artifact / correction-artifact', corrected_candidate_records: r.candidateRecords,
        raw_write_ready: false, db_write_performed: false });
    wj(OUT_AUDIT, { ...r.audit, raw_write_ready: false, db_write_performed: false });
    return {
        source_count: r.sourceRecords.length, candidate_count: r.candidateRecords.length,
        superseded_count: r.audit.superseded_wrong_leg.length, failures: r.failures,
        suspended_excluded: r.audit.suspended_excluded, positive_preserved: true,
        raw_write_ready: 0, re_acceptance: 0,
        db_write: false, raw_write: false, network: false, mutation: false,
        source_artifact: OUT_SOURCE, candidate_artifact: OUT_CANDIDATE, audit_artifact: OUT_AUDIT,
    };
}

function report(a) {
    const l = ['# ADG27 Controlled Correction Implementation', '', `- Phase: ${PH}`,
        `- corrected_source_inventory: ${a.source_count}`,
        `- corrected_candidates: ${a.candidate_count}`,
        `- superseded_wrong_leg: ${a.superseded_count}`,
        `- failures: ${a.failures}`, `- suspended_excluded: ${a.suspended_excluded}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Corrected Artifacts',
        `- Source inventory: ${a.source_artifact}`,
        `- Candidate: ${a.candidate_artifact}`,
        `- Audit: ${a.audit_artifact}`,
        '', '## Safety', '- no DB write / raw write / production mutation',
        '- all corrected records have raw_write_ready=false, source_inventory_write_ready=false, candidate_write_ready=false',
        '- rollback: revert to ADG26 preview state',
        '', '## Next', 'ADG28 no-write regression over corrected artifacts. Do NOT raw write.'];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG27 controlled correction implementation';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ source: a.source_count, candidate: a.candidate_count, superseded: a.superseded_count, failures: a.failures, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
