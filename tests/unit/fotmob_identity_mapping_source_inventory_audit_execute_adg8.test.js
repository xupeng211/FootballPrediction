'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/fotmob_identity_mapping_source_inventory_audit_execute_adg8.js'
);
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json'
);
const REPORT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_reports/FOTMOB_IDENTITY_MAPPING_SOURCE_INVENTORY_AUDIT_RESULT_ADG8.md'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('ADG8 audit executes bounded source-controlled review without write readiness', () => {
    const result = mod.runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8({
        writeFiles: false,
    });

    assert.equal(result.ok, true);
    assert.equal(result.artifact.phase, 'Phase 5.21-ADG8');
    assert.equal(result.artifact.adg8_audit_execution_status, mod.STATUS);
    assert.equal(result.artifact.audit_execution_performed, true);
    assert.equal(result.artifact.audited_sample_count, 8);
    assert.equal(result.artifact.positive_control_count, 1);
    assert.equal(result.artifact.reverse_fixture_sample_count, 5);
    assert.equal(result.artifact.suspended_reference_sample_count, 2);
    assert.equal(result.artifact.correct_mapping_count, 1);
    assert.equal(result.artifact.reverse_fixture_mapping_error_count, 5);
    assert.equal(result.artifact.home_away_inversion_count, 5);
    assert.equal(result.artifact.same_team_pair_wrong_leg_count, 5);
    assert.equal(result.artifact.date_mismatch_count, 5);
    assert.equal(result.artifact.source_inventory_route_error_count, 5);
    assert.equal(result.artifact.candidate_generation_rule_defect_count, 5);
    assert.equal(result.artifact.mapping_correction_candidate_count, 5);
    assert.equal(result.artifact.suspended_reference_still_blocked_count, 2);
    assert.equal(result.artifact.raw_write_execution_ready, false);
});

test('ADG8 audit preserves positive control and suspended blockers', () => {
    const result = mod.runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8({
        writeFiles: false,
    });
    const bySchedule = new Map(result.artifact.audit_results.map(item => [item.schedule_external_id, item]));

    assert.equal(bySchedule.get('4813735').audit_classification, 'correct_mapping');
    assert.equal(bySchedule.get('4813735').mapping_correction_candidate, false);
    assert.equal(bySchedule.get('4830461').audit_classification, 'suspended_reference_still_blocked');
    assert.equal(bySchedule.get('4830463').audit_classification, 'suspended_reference_still_blocked');
    assert.equal(bySchedule.get('4830461').reference_status, 'blocked_reference_only_no_unsuspend');
    assert.equal(bySchedule.get('4830463').reference_status, 'blocked_reference_only_no_unsuspend');
});

test('ADG8 audit marks each reverse sample as correction candidate without mutation', () => {
    const result = mod.runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8({
        writeFiles: false,
    });
    const reverseSamples = result.artifact.audit_results.filter(item => item.mapping_correction_candidate === true);

    assert.deepEqual(
        reverseSamples.map(item => [item.schedule_external_id, item.observed_detail_id, item.audit_classification]),
        [
            ['4830458', '4830627', 'reverse_fixture_mapping_error'],
            ['4830459', '4830667', 'reverse_fixture_mapping_error'],
            ['4830460', '4830648', 'reverse_fixture_mapping_error'],
            ['4830462', '4830618', 'reverse_fixture_mapping_error'],
            ['4830464', '4830689', 'reverse_fixture_mapping_error'],
        ]
    );

    for (const sample of reverseSamples) {
        assert.equal(sample.home_away_orientation_status, 'reversed');
        assert.equal(sample.reverse_fixture_detected, true);
        assert.equal(sample.expected_detail_identity_missing_or_wrong, true);
        assert.equal(sample.correction_needed, true);
        assert.equal(sample.correction_type, 'reject_candidate');
        assert.equal(sample.correction_actions.includes('require_strict_home_away_date_guard'), true);
        assert.equal(sample.source_inventory_mutation_performed, false);
        assert.equal(sample.candidate_mutation_performed, false);
        assert.equal(sample.raw_write_ready, false);
    }
});

test('ADG8 committed artifacts remain small, safe, and no-write', () => {
    const manifest = readJson(MANIFEST_PATH);
    const manifestText = fs.readFileSync(MANIFEST_PATH, 'utf8');
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');

    assert.equal(manifest.db_write_performed, false);
    assert.equal(manifest.raw_match_data_insert_performed, false);
    assert.equal(manifest.raw_write_execution_performed, false);
    assert.equal(manifest.re_acceptance_execution_performed, false);
    assert.equal(manifest.suspension_reversal_performed, false);
    assert.equal(manifest.source_inventory_mutation_performed, false);
    assert.equal(manifest.candidate_mutation_performed, false);
    assert.equal(manifest.live_fetch_performed, false);
    assert.equal(manifest.network_request_performed, false);
    assert.equal(manifest.full_payload_saved, false);

    for (const text of [manifestText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
