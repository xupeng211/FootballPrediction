'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
    assertRawWriteIdentityGate,
    reconcileRouteIdentity,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);
const ARTIFACT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_artifact_design.phase521l2v3i.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3I.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3I artifact is design-only and not accepted mapping', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3I');
    assert.equal(artifact.design_only, true);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_runner_read_design.design_artifact_usable_by_raw_write, false);
    assert.equal(manifest.phase_5_21_l2v3i_design_status, 'completed_design_only');
    assert.equal(manifest.phase_5_21_l2v3i_design_artifact_is_accepted_mapping, false);
    assert.equal(manifest.phase_5_21_l2v3i_design_artifact_usable_by_raw_write, false);
});

test('L2V3I design entries remain blocked when date mismatch is unresolved', () => {
    const artifact = readJson(ARTIFACT_PATH);

    assert.equal(artifact.candidate_review_entries_design.length, 8);
    for (const entry of artifact.candidate_review_entries_design) {
        assert.equal(entry.date_match_status, 'mismatch_unresolved');
        assert.equal(entry.acceptance_status, 'blocked_design_only_not_accepted');
        assert.equal(entry.mapping_confidence, 'medium');
        assert.equal(entry.raw_write_eligible_after_acceptance, false);
        assert.equal(entry.safety_blockers.includes('date_mismatch_unresolved'), true);
        assert.equal(entry.reviewer_required, true);
        assert.equal(entry.accepted_by, null);
        assert.equal(entry.accepted_at, null);
    }
});

test('L2V3I blocking rules cover mismatch and conflict failure modes', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const blockers = artifact.blocking_rules;

    assert.equal(blockers.includes('date_mismatch_unresolved'), true);
    assert.equal(blockers.includes('team_mismatch'), true);
    assert.equal(blockers.includes('page_url_base_mismatch'), true);
    assert.equal(blockers.includes('multiple_detail_ids_for_same_schedule_id'), true);
    assert.equal(blockers.includes('multiple_schedule_ids_for_same_detail_id'), true);
    assert.equal(blockers.includes('unstable_detail_identity'), true);
    assert.equal(blockers.includes('missing_observed_detail_id'), true);
    assert.equal(blockers.includes('fetch_or_parse_failure'), true);
    assert.equal(blockers.includes('block_or_captcha'), true);
    assert.equal(blockers.includes('proposal_only_mapping_available'), true);
    assert.equal(blockers.includes('human_review_missing'), true);
});

test('design artifact does not clear raw write guard without accepted mapping', () => {
    const result = reconcileRouteIdentity({
        target: {
            external_id: '4830466',
            home_team: 'Rennes',
            away_team: 'Marseille',
            match_date: '2025-08-15T18:45:00.000Z',
            page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
        },
        pageProps: {
            general: {
                matchId: '4830759',
                homeTeam: { name: 'Marseille' },
                awayTeam: { name: 'Rennes' },
                matchTimeUTC: '2026-05-17T19:00:00.000Z',
                pageUrl: '/matches/marseille-vs-rennes/2t9n7h#4830759',
            },
        },
        proposalOnlyMapping: true,
        acceptedIdentityMappingPresent: false,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.identity_reconciliation_status, 'unresolved_schedule_detail_mapping');
    assert.equal(result.proposal_mapping_used_for_raw_write, false);
    assert.equal(result.safety_blockers.includes('proposal_only_mapping_not_accepted'), true);
    assert.equal(result.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('identity mapping acceptance remains separate from baseline and DB authorization', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(artifact.raw_write_runner_read_design.accepted_artifact_does_not_accept_baseline, true);
    assert.equal(artifact.raw_write_runner_read_design.accepted_artifact_does_not_authorize_db_write, true);
    assert.equal(artifact.raw_write_runner_read_design.raw_write_still_requires_separate_baseline_acceptance, true);
    assert.equal(
        artifact.raw_write_runner_read_design.raw_write_still_requires_separate_final_db_write_authorization,
        true
    );
    assert.equal(manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifest.requires_separate_baseline_acceptance, true);
    assert.equal(manifest.requires_separate_final_db_write_authorization, true);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('L2V3I artifact and report avoid full payload markers', () => {
    const artifactText = readText(ARTIFACT_PATH);
    const reportText = readText(REPORT_PATH);

    for (const text of [artifactText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
    }
});
