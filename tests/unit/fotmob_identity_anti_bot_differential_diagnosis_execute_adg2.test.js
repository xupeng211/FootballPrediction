'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const RESULT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_identity_anti_bot_differential_diagnosis_result.adg2.json'
);
const REPORT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_reports/FOTMOB_IDENTITY_ANTI_BOT_DIFFERENTIAL_DIAGNOSIS_RESULT_ADG2.md'
);

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('ADG2 records bounded execution and keeps all write paths blocked', () => {
    const result = readJson(RESULT_PATH);

    assert.equal(result.phase, 'Phase 5.21-ADG2');
    assert.equal(result.adg2_execution_performed, true);
    assert.equal(result.execution_scope.positive_sample_count, 1);
    assert.equal(result.execution_scope.suspended_sample_diagnosis_count, 3);
    assert.equal(result.execution_scope.needs_new_evidence_sample_diagnosis_count, 3);
    assert.equal(result.execution_scope.uncontrolled_retry_performed, false);
    assert.equal(result.execution_scope.bulk_fetch_performed, false);
    assert.equal(result.execution_scope.captcha_bypass_performed, false);
    assert.equal(result.execution_scope.proxy_bypass_performed, false);
    assert.equal(result.safety_status.db_write_performed, false);
    assert.equal(result.safety_status.raw_write_execution_performed, false);
    assert.equal(result.safety_status.raw_match_data_insert_performed, false);
    assert.equal(result.safety_status.re_acceptance_execution_performed, false);
    assert.equal(result.safety_status.full_payload_saved, false);
    assert.equal(result.safety_status.full_payload_printed, false);
    assert.equal(result.safety_status.raw_write_execution_ready, false);
});

test('ADG2 preserves positive sample URL hash parsing facts', () => {
    const result = readJson(RESULT_PATH);
    const parsing = result.positive_sample_url_parsing;

    assert.equal(parsing.positive_sample_url_hash_id, '4813735');
    assert.equal(parsing.positive_sample_url_path_slug, '2feiv3');
    assert.equal(parsing.parsed_url_hash_id, '4813735');
    assert.equal(parsing.parsed_url_path_slug, '2feiv3');
    assert.equal(parsing.hash_id_numeric, true);
    assert.equal(parsing.hash_id_available_before_http_request, true);
    assert.equal(parsing.fragment_sent_to_server_by_http, false);
});

test('ADG2 diagnoses hash extraction support and active manifest propagation gap', () => {
    const result = readJson(RESULT_PATH);
    const hash = result.hash_id_extraction_diagnosis;
    const discovery = result.discovery_chain_diagnosis;

    assert.equal(hash.discovery_extracts_hash_id, true);
    assert.equal(hash.discovery_persists_hash_id, true);
    assert.equal(hash.source_url_fragment_external_id_supported, true);
    assert.equal(hash.source_inventory_all_50_records_have_fragment_id, true);
    assert.equal(hash.active_proposal_candidate_targets_have_fragment_id, false);
    assert.equal(discovery.source_inventory_counts.candidate_targets_with_source_url_fragment_external_id, 50);
    assert.equal(discovery.active_proposal_sample_gap.sampled_targets_with_source_url_fragment_external_id, 0);
});

test('ADG2 diagnoses current recapture as guarded against blind schedule fallback', () => {
    const result = readJson(RESULT_PATH);
    const recapture = result.recapture_identity_usage_diagnosis;

    assert.equal(recapture.recapture_uses_detail_identity_candidate, true);
    assert.equal(recapture.recapture_falls_back_to_schedule_external_id, false);
    assert.equal(recapture.fallback_blocked_when_not_reaccepted, true);
    assert.equal(recapture.blind_schedule_route_blocked, true);
    assert.equal(recapture.legacy_issue_observed_in_prior_artifact.ao_runner_uses_schedule_match_route, true);
    assert.equal(recapture.legacy_issue_observed_in_prior_artifact.raw_write_execution_ready, false);
});

test('ADG2 records positive page route success and direct API access block without full payload', () => {
    const result = readJson(RESULT_PATH);
    const network = result.positive_sample_network_diagnosis;

    assert.equal(network.page_route_test_performed, true);
    assert.equal(network.page_http_status, 200);
    assert.equal(network.hydration_marker_present, true);
    assert.equal(network.expected_team_marker_presence.bournemouth, true);
    assert.equal(network.expected_team_marker_presence.manchester_city, true);
    assert.deepEqual(network.page_anti_bot_signs, []);
    assert.equal(network.direct_api_test_performed, true);
    assert.equal(network.direct_api_http_status, 403);
    assert.equal(network.direct_api_observed_payload_match_id, null);
    assert.equal(network.direct_api_anti_bot_signs.includes('403'), true);
    assert.equal(
        network.browser_page_route_vs_direct_api_identity_status,
        'page_route_available_but_direct_api_blocked_identity_not_comparable'
    );
});

test('ADG2 sample groups are bounded and classified', () => {
    const result = readJson(RESULT_PATH);
    const suspended = result.sample_diagnoses.suspended_targets;
    const needsEvidence = result.sample_diagnoses.needs_new_evidence_targets;

    assert.equal(suspended.length, 3);
    assert.equal(needsEvidence.length, 3);
    assert.deepEqual(
        suspended.map(item => item.schedule_external_id),
        ['4830461', '4830463', '4830465']
    );
    assert.deepEqual(
        needsEvidence.map(item => item.schedule_external_id),
        ['4830460', '4830458', '4830459']
    );

    for (const item of suspended) {
        assert.equal(item.classification.includes('url_hash_id_persisted_but_not_used'), true);
        assert.equal(item.classification.includes('reverse_fixture_or_home_away_inversion'), true);
    }
    for (const item of needsEvidence) {
        assert.equal(item.classification.includes('url_hash_id_persisted_but_not_used'), true);
        assert.equal(item.classification.includes('unknown_insufficient_evidence'), true);
    }
});

test('ADG2 recommends implementation planning but not raw write or re-acceptance', () => {
    const result = readJson(RESULT_PATH);

    assert.equal(result.raw_write_execution_ready, false);
    assert.match(result.recommended_next_step, /runtime implementation/);
    assert.match(result.recommended_next_step, /do not raw write/i);
    assert.equal(
        result.likely_root_cause.includes(
            'source_inventory_hash_identity_exists_but_is_not_propagated_to_active_candidate_manifest'
        ),
        true
    );
});

test('ADG2 artifacts do not contain full payload fields or body dumps', () => {
    const resultText = fs.readFileSync(RESULT_PATH, 'utf8');
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');

    for (const text of [resultText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__":'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('<html'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
