'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_plan.adg7.json'
);
const REPORT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_reports/FOTMOB_IDENTITY_MAPPING_SOURCE_INVENTORY_AUDIT_PLAN_ADG7.md'
);

function readManifest() {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function readReport() {
    return fs.readFileSync(REPORT_PATH, 'utf8');
}

test('ADG7 plan stays planning-only and keeps raw/write gates closed', () => {
    const manifest = readManifest();

    assert.equal(manifest.phase, 'Phase 5.21-ADG7');
    assert.equal(
        manifest.adg7_planning_status,
        'completed_bounded_identity_mapping_correction_source_inventory_audit_planning_only'
    );
    assert.equal(manifest.pr_type, 'audit-planning / governance-only');
    assert.equal(manifest.runtime_code_change, false);
    assert.equal(manifest.helper_scaffolding_added, false);
    assert.equal(manifest.planning_performed, true);
    assert.equal(manifest.audit_scope, 'identity_mapping_correction_source_inventory_audit');
    assert.equal(manifest.reverse_fixture_sample_count, 5);
    assert.equal(manifest.suspended_reference_sample_count, 2);
    assert.equal(manifest.positive_control_count, 1);
    assert.equal(manifest.future_full_population_scope_count, 42);
    assert.equal(manifest.planned_audit_fields.length, manifest.planned_audit_fields_count);
    assert.equal(manifest.planned_audit_classifications.length, manifest.planned_audit_classifications_count);
    assert.equal(manifest.adg8_plan.adg8_requires_explicit_authorization, true);
    assert.equal(manifest.adg8_plan.adg8_must_not_perform_raw_write, true);
    assert.equal(manifest.adg8_plan.adg8_must_not_perform_re_acceptance, true);
    assert.equal(manifest.adg8_plan.adg8_must_not_perform_suspension_reversal, true);

    for (const value of Object.values(manifest.safety_status)) {
        assert.equal(value, false);
    }
});

test('ADG7 plan preserves ADG6 positive, reverse fixture, and suspended samples', () => {
    const manifest = readManifest();
    const samples = manifest.planned_audit_samples;

    assert.equal(samples.positive_control.length, 1);
    assert.equal(samples.positive_control[0].sample_id, 'positive_bournemouth_mancity_4813735');
    assert.equal(samples.positive_control[0].observed_detail_id, '4813735');
    assert.equal(samples.positive_control[0].adg6_classification, 'page_route_identity_validated');

    assert.deepEqual(
        samples.reverse_fixture_samples.map(sample => [
            sample.schedule_external_id,
            sample.observed_detail_id,
            sample.adg6_classification,
        ]),
        [
            ['4830458', '4830627', 'reverse_fixture_or_home_away_inversion'],
            ['4830459', '4830667', 'reverse_fixture_or_home_away_inversion'],
            ['4830460', '4830648', 'reverse_fixture_or_home_away_inversion'],
            ['4830462', '4830618', 'reverse_fixture_or_home_away_inversion'],
            ['4830464', '4830689', 'reverse_fixture_or_home_away_inversion'],
        ]
    );

    assert.deepEqual(
        samples.suspended_reference_samples.map(sample => [
            sample.schedule_external_id,
            sample.observed_detail_id,
            sample.adg6_classification,
            sample.adg8_role,
        ]),
        [
            ['4830461', '4830758', 'suspended_reference_blocked', 'blocked_reference_only_no_unsuspend'],
            ['4830463', '4830622', 'suspended_reference_blocked', 'blocked_reference_only_no_unsuspend'],
        ]
    );
});

test('ADG7 plan defines strict audit fields, classifications, and correction strategy', () => {
    const manifest = readManifest();
    const strategy = manifest.planned_correction_strategy;

    assert.equal(manifest.planned_audit_fields.includes('target_match_id'), true);
    assert.equal(manifest.planned_audit_fields.includes('source_inventory_record_key'), true);
    assert.equal(manifest.planned_audit_fields.includes('home_away_orientation_status'), true);
    assert.equal(manifest.planned_audit_fields.includes('mapping_correction_candidate'), true);
    assert.equal(manifest.planned_audit_classifications.includes('reverse_fixture_mapping_error'), true);
    assert.equal(manifest.planned_audit_classifications.includes('same_team_pair_wrong_leg'), true);
    assert.equal(manifest.planned_audit_classifications.includes('suspended_reference_still_blocked'), true);
    assert.equal(strategy.correction_strategy_planned, true);
    assert.equal(strategy.strict_fixture_identity_matching_required, true);
    assert.equal(strategy.do_not_accept_detail_external_id_candidate_based_only_on_url_hash, true);
    assert.equal(strategy.preserve_suspended_blockers, true);
    assert.equal(strategy.raw_write_execution_ready_until_correction_and_no_write_validation, false);
});

test('ADG7 artifacts avoid full payload markers and point to ADG8 audit execution', () => {
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

    assert.equal(reportText.includes('ADG8 bounded identity mapping/source inventory audit execution'), true);
    assert.equal(reportText.includes('ADG7 does not execute live fetch'), true);
});
