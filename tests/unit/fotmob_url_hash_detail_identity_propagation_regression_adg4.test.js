'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/fotmob_url_hash_detail_identity_propagation_regression_adg4.js'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

test('ADG4 validates URL hash/detail identity propagation without writes', () => {
    const result = mod.runFotmobUrlHashDetailIdentityPropagationRegressionAdg4(
        { writeFiles: false },
        { generatedAt: '2026-05-28T02:00:00.000Z' }
    );

    assert.equal(result.ok, true);
    assert.equal(result.artifact.proposal_phase, 'Phase 5.21-ADG4');
    assert.equal(result.artifact.artifact_status, mod.EXECUTION_STATUS);
    assert.equal(result.artifact.regression_execution_performed, true);
    assert.equal(result.artifact.runtime_behavior_validated, true);
    assert.equal(result.artifact.runtime_code_change, false);
    assert.equal(result.artifact.source_controlled_local_no_write_regression, true);
    assert.equal(result.artifact.total_batch_target_count, 50);
    assert.equal(result.artifact.source_inventory_hash_records_count, 50);
    assert.equal(result.artifact.active_candidate_hash_propagation_count, 50);
    assert.equal(result.artifact.candidate_detail_external_id_candidate_count, 50);
    assert.equal(result.artifact.suspended_target_count, 8);
    assert.equal(result.artifact.needs_new_evidence_target_count_before, 42);
    assert.equal(result.artifact.detail_identity_candidate_present_count, 42);
    assert.equal(result.artifact.source_inventory_hash_missing_count, 0);
    assert.equal(result.artifact.propagation_failed_count, 0);
    assert.equal(result.artifact.request_contract_validation_required_count, 42);
    assert.equal(result.artifact.remains_needs_new_evidence_count, 0);
    assert.equal(result.artifact.suspended_reverse_fixture_blocked_count, 8);
    assert.equal(result.artifact.raw_write_ready_count, 0);
    assert.equal(result.artifact.re_acceptance_candidate_count, 0);
    assert.equal(result.artifact.recapture_expected_identity_uses_detail_candidate, true);
    assert.equal(result.artifact.schedule_external_id_blind_fallback_blocked, true);
    assert.equal(result.artifact.direct_api_request_contract_blocked, true);
    assert.equal(result.artifact.safety_status.live_fetch_performed, false);
    assert.equal(result.artifact.safety_status.network_request_performed, false);
    assert.equal(result.artifact.safety_status.db_write_performed, false);
    assert.equal(result.artifact.safety_status.raw_write_execution_performed, false);
    assert.equal(result.artifact.safety_status.re_acceptance_execution_performed, false);
    assert.equal(result.artifact.safety_status.suspension_reversal_performed, false);
});

test('ADG4 positive sample keeps hash parsing local and recapture request blocked', () => {
    const positiveSample = mod.buildPositiveSampleSummary('2026-05-28T02:00:00.000Z');
    const recapture = mod.buildRecaptureIdentityPositiveSample(positiveSample);

    assert.equal(positiveSample.source_url_path_slug, '2feiv3');
    assert.equal(positiveSample.source_url_fragment_external_id, '4813735');
    assert.equal(positiveSample.detail_external_id_candidate, '4813735');
    assert.equal(positiveSample.detail_identity_source, 'url_hash_fragment');
    assert.equal(positiveSample.no_http_request_required, true);

    assert.equal(recapture.recapture_expected_identity, '4813735');
    assert.equal(recapture.recapture_request_identity, null);
    assert.equal(recapture.recapture_expected_identity_uses_detail_candidate, true);
    assert.equal(recapture.schedule_external_id_blind_fallback_blocked, true);
    assert.equal(recapture.raw_write_execution_ready, false);
    assert.equal(recapture.blockers.includes('missing_accepted_detail_external_id'), true);
    assert.equal(recapture.blockers.includes('missing_re_acceptance'), true);
});

test('ADG4 target-level classifications are precise for blocked and suspended cases', () => {
    const blocked = mod.classifyNeedsNewEvidenceTarget({
        target_id: 'blocked:4830460',
        match_id: '53_20252026_4830460',
        external_id: '4830460',
        source_page_url: '/matches/brest-vs-lille/2fo2ub#4830460',
        source_page_url_base: '/matches/brest-vs-lille/2fo2ub',
        source_url_path_slug: '2fo2ub',
        source_url_fragment_external_id: '4830460',
        detail_external_id_candidate: '4830460',
        detail_identity_source: 'url_hash_fragment',
    });
    const suspended = mod.classifySuspendedTarget({
        target_id: 'suspended:4830461',
        match_id: '53_20252026_4830461',
        external_id: '4830461',
        source_page_url: '/matches/lens-vs-lyon/2s3gtg#4830461',
        source_page_url_base: '/matches/lens-vs-lyon/2s3gtg',
        source_url_path_slug: '2s3gtg',
        source_url_fragment_external_id: '4830461',
        detail_external_id_candidate: '4830461',
        detail_identity_source: 'url_hash_fragment',
    });

    assert.equal(blocked.classification, 'request_contract_validation_required');
    assert.equal(blocked.recapture_expected_identity, '4830460');
    assert.equal(blocked.recapture_request_identity, null);
    assert.equal(blocked.raw_write_execution_ready, false);
    assert.equal(blocked.identity_contract_blockers.includes('page_url_base_alone_insufficient'), true);

    assert.equal(suspended.classification, 'suspended_reverse_fixture_blocked');
    assert.equal(suspended.recapture_expected_identity, '4830461');
    assert.equal(suspended.recapture_request_identity, null);
    assert.equal(suspended.raw_write_execution_ready, false);
    assert.equal(suspended.identity_contract_blockers.includes('suspended_mapping_or_baseline'), true);
    assert.equal(suspended.identity_contract_blockers.includes('reverse_fixture_detected'), true);
});

test('ADG4 report avoids full payload markers', () => {
    const result = mod.runFotmobUrlHashDetailIdentityPropagationRegressionAdg4(
        { writeFiles: false },
        { generatedAt: '2026-05-28T02:00:00.000Z' }
    );
    const texts = [JSON.stringify(result.artifact), result.report];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
