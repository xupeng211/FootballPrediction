'use strict';
/* eslint-disable max-lines -- L2V3O safety contract stays together for auditability. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_continued_date_rule_investigation.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

function readText(repoPath) {
    return fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8');
}

test('L2V3O artifact records no-write source-controlled investigation only', () => {
    const artifact = readJson(mod.INVESTIGATION_ARTIFACT_PATH);
    const manifest = readJson(mod.MANIFEST_PATH);

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3O');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.source_controlled_artifact_only, true);
    assert.equal(artifact.controlled_metadata_check_performed, false);
    assert.equal(artifact.live_source_check_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);

    assert.equal(manifest.phase_5_21_l2v3o_investigation_status, 'completed_no_write_source_controlled_artifact_only');
    assert.equal(
        manifest.continued_expanded_date_rule_investigation_status,
        'completed_no_write_source_controlled_artifact_only'
    );
    assert.equal(manifest.phase_5_21_l2v3o_controlled_metadata_check_performed, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('L2V3O investigates 42 unknown targets and keeps them blocked', () => {
    const artifact = readJson(mod.INVESTIGATION_ARTIFACT_PATH);

    assert.equal(artifact.unknown_target_investigation.length, 42);
    assert.equal(artifact.checked_unknown_target_count, 42);
    assert.equal(artifact.still_unknown_count, 42);
    assert.equal(artifact.raw_write_blocked_count, 42);
    assert.equal(artifact.identity_mapping_acceptance_blocked_count, 42);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.newly_classified_reverse_fixture_count, 0);
    assert.equal(artifact.newly_classified_date_match_count, 0);
    assert.equal(artifact.newly_classified_same_utc_day_count, 0);
    assert.equal(artifact.newly_classified_unresolved_large_gap_count, 0);

    for (const entry of artifact.unknown_target_investigation) {
        assert.equal(entry.accepted_mapping, false, entry.schedule_external_id);
        assert.equal(entry.raw_write_authorized, false, entry.schedule_external_id);
        assert.equal(entry.raw_write_blocker_status, 'blocked', entry.schedule_external_id);
        assert.equal(entry.identity_mapping_acceptance_blocker_status, 'blocked', entry.schedule_external_id);
        assert.equal(entry.classification_labels.includes('not_checked_live'), true, entry.schedule_external_id);
    }
});

test('L2V3O explains the unknown gap as artifact coverage plus missing observed detail metadata', () => {
    const artifact = readJson(mod.INVESTIGATION_ARTIFACT_PATH);

    assert.equal(artifact.missing_observed_detail_metadata_count, 42);
    assert.equal(artifact.missing_page_url_base_count, 42);
    assert.equal(artifact.missing_schedule_date_count, 0);
    assert.equal(artifact.missing_team_metadata_count, 0);
    assert.equal(artifact.not_checked_live_count, 42);
    assert.equal(artifact.source_inventory_gap_count, 42);
    assert.equal(artifact.artifact_coverage_gap_count, 42);

    assert.equal(artifact.investigation_findings.l2v3f_checked_targets_count, 8);
    assert.equal(artifact.investigation_findings.l2v3f_unchecked_targets_count, 42);
    assert.equal(artifact.investigation_findings.l2v3k_review_entries_count, 8);
    assert.equal(artifact.investigation_findings.manifest_candidate_targets_missing_page_url_base_count, 50);
    assert.equal(artifact.investigation_findings.unknown_targets_with_requested_schedule_date_count, 42);
    assert.equal(artifact.investigation_findings.unknown_targets_with_requested_team_metadata_count, 42);
});

test('metadata-only check remains unperformed and cannot imply acceptance or raw write readiness', () => {
    const artifact = readJson(mod.INVESTIGATION_ARTIFACT_PATH);

    assert.equal(artifact.controlled_metadata_check_performed, false);
    assert.equal(artifact.metadata_check_success_count, 0);
    assert.equal(artifact.metadata_check_blocked_count, 0);
    assert.equal(artifact.metadata_check_failed_count, 0);
    assert.equal(artifact.safety_contract.metadata_only_check_result_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.metadata_check_success_does_not_equal_raw_write_ready, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3P: controlled no-write metadata-only detail check');
});

test('controlled metadata check guard refuses any DB write intent', () => {
    assert.equal(mod.assertControlledMetadataCheckNoWrite(), true);
    assert.throws(() => mod.assertControlledMetadataCheckNoWrite({ dbWriteRequested: true }), /must remain no-write/);
    assert.throws(() => mod.assertControlledMetadataCheckNoWrite({ rawInsertRequested: true }), /must remain no-write/);
    assert.throws(
        () => mod.assertControlledMetadataCheckNoWrite({ matchesWriteRequested: true }),
        /must remain no-write/
    );
});

test('L2V3O artifacts avoid full raw_data pageProps and source body payloads', () => {
    const texts = [readText(mod.INVESTIGATION_ARTIFACT_PATH), readText(mod.REPORT_PATH), readText(mod.MANIFEST_PATH)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
