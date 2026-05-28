'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_request_contract_page_route_validation_plan.adg5.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/FOTMOB_REQUEST_CONTRACT_PAGE_ROUTE_VALIDATION_PLAN_ADG5.md');

function readManifest() {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function readReport() {
    return fs.readFileSync(REPORT_PATH, 'utf8');
}

test('ADG5 plan stays bounded, planning-only, and authorization-gated', () => {
    const manifest = readManifest();

    assert.equal(manifest.phase, 'Phase 5.21-ADG5');
    assert.equal(manifest.plan_status, 'completed_bounded_request_contract_page_route_validation_planning_only');
    assert.equal(manifest.pr_type, 'spike-planning / governance-only');
    assert.equal(manifest.runtime_code_change, false);
    assert.equal(manifest.helper_scaffolding_added, false);
    assert.equal(manifest.planning_performed, true);
    assert.equal(manifest.validation_scope, 'bounded_request_contract_page_route_validation');
    assert.equal(manifest.positive_sample_included, true);
    assert.equal(manifest.positive_sample_detail_external_id_candidate, '4813735');
    assert.equal(manifest.request_contract_validation_required_target_count, 42);
    assert.equal(manifest.planned_42_target_sample_count, 5);
    assert.equal(manifest.planned_suspended_reference_sample_count, 2);
    assert.equal(manifest.planned_validation_fields_count, 26);
    assert.equal(manifest.planned_classification_count, 11);
    assert.equal(manifest.expected_outputs.adg6_requires_explicit_authorization, true);
    assert.equal(manifest.safety_status.live_fetch_performed, false);
    assert.equal(manifest.safety_status.network_request_performed, false);
    assert.equal(manifest.safety_status.direct_api_probing_performed, false);
    assert.equal(manifest.safety_status.browser_automation_performed, false);
    assert.equal(manifest.safety_status.db_write_performed, false);
    assert.equal(manifest.safety_status.raw_write_execution_performed, false);
    assert.equal(manifest.safety_status.re_acceptance_execution_performed, false);
    assert.equal(manifest.safety_status.suspension_reversal_performed, false);
    assert.equal(manifest.safety_status.raw_write_execution_ready, false);
});

test('ADG5 plan includes bounded samples and the required field/classification schema', () => {
    const manifest = readManifest();
    const samples = manifest.planned_samples;

    assert.equal(samples.request_contract_validation_required_samples.length, 5);
    assert.equal(samples.suspended_reference_samples.length, 2);
    assert.equal(samples.positive_sample.detail_external_id_candidate, '4813735');
    assert.equal(samples.positive_sample.source_url_path_slug, '2feiv3');
    assert.equal(samples.positive_sample.source_url_fragment_external_id, '4813735');

    for (const sample of samples.request_contract_validation_required_samples) {
        assert.equal(sample.sample_group, 'request_contract_validation_required');
        assert.equal(sample.detail_identity_source, 'url_hash_fragment');
        assert.equal(sample.current_local_classification, 'request_contract_validation_required');
        assert.equal(sample.current_local_blockers.includes('missing_re_acceptance'), true);
    }

    for (const sample of samples.suspended_reference_samples) {
        assert.equal(sample.sample_group, 'suspended_reference');
        assert.equal(sample.detail_identity_source, 'url_hash_fragment');
        assert.equal(sample.current_local_classification, 'suspended_reverse_fixture_blocked');
        assert.equal(sample.current_local_blockers.includes('reverse_fixture_detected'), true);
        assert.equal(sample.current_local_blockers.includes('suspended_mapping_or_baseline'), true);
    }

    assert.deepEqual(manifest.planned_validation_fields, [
        'sample_id',
        'source_page_url',
        'source_url_path_slug',
        'source_url_fragment_external_id',
        'detail_external_id_candidate',
        'detail_identity_source',
        'expected_home_team',
        'expected_away_team',
        'expected_match_date',
        'expected_competition',
        'page_route_url_without_fragment',
        'page_http_status',
        'page_content_type',
        'redirect_summary',
        'hydration_marker_present',
        'safe_identity_marker_present',
        'observed_detail_id_if_safely_available',
        'observed_home_team_if_safely_available',
        'observed_away_team_if_safely_available',
        'observed_date_if_safely_available',
        'anti_bot_signs',
        'request_contract_status',
        'validation_classification',
        'no_full_body_saved',
        'no_db_write',
        'no_raw_write',
    ]);

    assert.deepEqual(manifest.planned_classifications, [
        'page_route_identity_validated',
        'page_route_available_but_identity_not_observed',
        'direct_api_request_contract_blocked',
        'request_contract_headers_session_locale_required',
        'anti_bot_or_access_block',
        'redirect_or_locale_mismatch',
        'hydration_marker_missing',
        'identity_mismatch',
        'reverse_fixture_or_home_away_inversion',
        'suspended_reference_blocked',
        'insufficient_safe_evidence',
    ]);
});

test('ADG5 artifacts avoid full payload markers', () => {
    const manifestText = fs.readFileSync(MANIFEST_PATH, 'utf8');
    const reportText = readReport();

    for (const text of [manifestText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
