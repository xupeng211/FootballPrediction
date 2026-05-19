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
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3H.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3H manifest metadata records no-write implementation only', () => {
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(manifest.phase_5_21_l2v3h_implementation_status, 'completed_no_write');
    assert.equal(manifest.schedule_detail_route_normalization_fix_implementation_status, 'implemented_no_write_guard');
    assert.equal(manifest.fetcher_contract_exposes_requested_and_observed_identity, true);
    assert.equal(manifest.raw_write_blocks_unresolved_schedule_detail_mapping, true);
    assert.equal(manifest.phase_5_21_l2v3h_route_identity_guard_blocks_proposal_only_mapping, true);
    assert.equal(manifest.proposal_mapping_used_for_raw_write, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifest.requires_separate_baseline_acceptance, true);
    assert.equal(manifest.requires_separate_final_db_write_authorization, true);
});

test('L2V3H artifacts keep candidate scope from being interpreted as write success', () => {
    const manifest = readJson(MANIFEST_PATH);
    const report = readText(REPORT_PATH);

    assert.equal(manifest.phase_5_21_l2v3g_candidate_matches_scope_count, 58);
    assert.equal(manifest.phase_5_21_l2v3g_candidate_fotmob_pageprops_v2_raw_rows, 8);
    assert.equal(manifest.phase_5_21_l2v3h_candidate_scope_is_raw_write_success, false);
    assert.equal(manifest.phase_5_21_l2v3h_candidate_v2_rows_are_l2v3h_writes, false);
    assert.match(report, /candidate_matches_count=58/);
    assert.match(report, /candidate_v2_rows_are_l2v3h_writes=false/);
    assert.match(report, /candidate_scope_is_raw_write_success=false/);
});

test('L2V3H report preserves no acceptance and no raw write semantics', () => {
    const report = readText(REPORT_PATH);

    assert.match(report, /db_write_performed=false/);
    assert.match(report, /raw_insert_performed=false/);
    assert.match(report, /matches_write_performed=false/);
    assert.match(report, /proposal_only_mapping_accepted=false/);
    assert.match(report, /accepted_mapping_artifact_created=false/);
    assert.match(report, /no identity mapping acceptance/);
    assert.match(report, /no baseline acceptance/);
    assert.match(report, /no raw write retry/);
});

test('L2V3H report does not contain full payload markers', () => {
    const report = readText(REPORT_PATH);

    assert.equal(report.includes('"raw_data":'), false);
    assert.equal(report.includes('"pageProps":'), false);
    assert.equal(report.includes('__NEXT_DATA__'), false);
    assert.equal(report.includes('<!DOCTYPE'), false);
});
