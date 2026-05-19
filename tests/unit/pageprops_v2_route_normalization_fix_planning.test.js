'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);
const PROPOSAL_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.route_normalization_fix_proposal.phase521l2v3g.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3G.md');
const rawWrite = require('../../scripts/ops/renewed_pageprops_v2_raw_write_execute');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3G artifacts describe a no-write planning phase only', () => {
    const manifest = readJson(MANIFEST_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const report = readText(REPORT_PATH);

    assert.equal(proposal.proposal_phase, 'Phase 5.21L2V3G');
    assert.equal(proposal.no_write, true);
    assert.equal(proposal.db_write_performed, false);
    assert.equal(proposal.raw_insert_performed, false);
    assert.equal(proposal.matches_write_performed, false);
    assert.equal(proposal.identity_mapping_acceptance_performed, false);
    assert.equal(proposal.baseline_acceptance_performed, false);
    assert.equal(proposal.raw_write_retry_performed, false);
    assert.equal(proposal.raw_write_ready_for_execution, false);

    assert.equal(manifest.phase_5_21_l2v3g_planning_status, 'completed_no_write');
    assert.equal(manifest.route_normalization_fix_required, true);
    assert.equal(manifest.phase_5_21_l2v3g_identity_mapping_acceptance_performed, false);
    assert.equal(manifest.phase_5_21_l2v3g_baseline_acceptance_performed, false);
    assert.equal(manifest.phase_5_21_l2v3g_raw_write_retry_performed, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.match(report, /db_write_performed=false/);
    assert.match(report, /raw_insert_performed=false/);
});

test('route normalization proposal keeps requested schedule id and observed detail id separate', () => {
    const proposal = readJson(PROPOSAL_PATH);

    assert.equal(
        proposal.route_identity_findings.current_detail_fetch_route_identity_source,
        'manifest_target_external_id'
    );
    assert.equal(
        proposal.proposed_fetcher_contract.must_not_silently_treat_requested_external_id_as_canonical_detail_identity,
        true
    );
    assert.equal(proposal.proposed_fetcher_contract.must_expose_requested_schedule_external_id, true);
    assert.equal(proposal.proposed_fetcher_contract.must_expose_observed_detail_external_id_separately, true);
    assert.equal(proposal.checked_route_mismatch_targets.length, 8);

    for (const target of proposal.checked_route_mismatch_targets) {
        assert.notEqual(target.requested_schedule_external_id, target.observed_detail_external_id);
        assert.equal(target.page_url_base_match_status, 'match');
        assert.equal(target.team_date_status_match_status, 'date_mismatch');
        assert.equal(target.mapping_confidence, 'medium');
        assert.equal(target.route_normalization_status, 'fix_required_unresolved_mapping');
        assert.equal(target.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    }
});

test('date mismatch and proposal-only mapping block high-confidence acceptance and raw write retry', () => {
    const manifest = readJson(MANIFEST_PATH);
    const proposal = readJson(PROPOSAL_PATH);

    assert.equal(
        proposal.proposed_raw_write_precondition
            .requested_schedule_external_id_mismatch_observed_detail_external_id_blocks_raw_write_without_accepted_mapping,
        true
    );
    assert.equal(proposal.proposed_raw_write_precondition.proposal_only_mapping_is_insufficient, true);
    assert.equal(proposal.proposed_raw_write_precondition.date_mismatch_blocks_high_confidence_acceptance, true);
    assert.equal(proposal.accepted_identity_mapping_artifact.required_before_baseline_acceptance, true);
    assert.equal(proposal.accepted_identity_mapping_artifact.required_before_raw_write_retry, true);
    assert.equal(proposal.accepted_identity_mapping_artifact.status, 'not_created_in_l2v3g');
    assert.equal(manifest.phase_5_21_l2v3g_raw_write_blocked_without_accepted_identity_mapping, true);
    assert.equal(manifest.phase_5_21_l2v3g_page_url_base_match_date_mismatch_high_confidence_blocked, true);
});

test('candidate matches=58 and candidate v2 rows=8 are not write success', () => {
    const manifest = readJson(MANIFEST_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const report = readText(REPORT_PATH);

    assert.equal(proposal.candidate_scope.candidate_matches_count, 58);
    assert.equal(proposal.candidate_scope.manifest_schedule_targets_count, 50);
    assert.equal(proposal.candidate_scope.preexisting_seeded_pageprops_v2_match_count, 8);
    assert.equal(proposal.candidate_scope.candidate_fotmob_pageprops_v2_raw_rows, 8);
    assert.equal(proposal.candidate_scope.candidate_count_is_schedule_targets_plus_observed_detail_ids, false);
    assert.equal(proposal.candidate_scope.candidate_scope_is_write_success, false);
    assert.equal(proposal.candidate_scope.candidate_v2_rows_are_l2v3g_writes, false);
    assert.equal(manifest.phase_5_21_l2v3g_candidate_scope_is_raw_write_success, false);
    assert.equal(manifest.phase_5_21_l2v3g_candidate_v2_rows_are_l2v3g_writes, false);
    assert.match(report, /candidate_scope_is_raw_write_success=false/);
});

test('raw write runner still rejects the L2V3G unresolved planning manifest', () => {
    const manifest = readJson(MANIFEST_PATH);
    const gate = rawWrite.validateManifestGate(manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /next_required_step|raw_write|baseline|identity/i);
});

test('L2V3G report and proposal do not contain full payload markers', () => {
    const proposalText = readText(PROPOSAL_PATH);
    const reportText = readText(REPORT_PATH);

    for (const text of [proposalText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('full_html_body'), false);
    }
});
