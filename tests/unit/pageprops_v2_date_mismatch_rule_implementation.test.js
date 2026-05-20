'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
    reconcileRouteIdentity,
    assertRawWriteIdentityGate,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);
const ARTIFACT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json'
);
const REVIEW_RESULT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3M.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3M artifact records no-write implementation only', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(artifact.implementation_only, true);
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);

    assert.equal(manifest.phase_5_21_l2v3m_implementation_status, 'completed_no_write');
    assert.equal(manifest.date_rule_engine_implemented, true);
    assert.equal(manifest.phase_5_21_l2v3m_accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('date rule engine status contract is complete', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const statuses = new Set(artifact.date_rule_engine_statuses);

    for (const status of [
        'date_match',
        'same_utc_day',
        'timezone_only_mismatch',
        'postponed_or_rescheduled_explained',
        'reverse_fixture_detected',
        'cross_season_slug_reuse',
        'unresolved_large_gap',
        'unknown',
    ]) {
        assert.equal(statuses.has(status), true, status);
    }

    assert.equal(artifact.rule_contract.reverse_fixture_detected_blocks_identity_mapping_acceptance, true);
    assert.equal(artifact.rule_contract.reverse_fixture_detected_blocks_raw_write, true);
    assert.equal(artifact.rule_contract.unresolved_large_gap_blocks_raw_write, true);
    assert.equal(artifact.rule_contract.pageurl_base_match_alone_blocks_acceptance, true);
});

test('all 8 L2V3L mappings classify as reverse_fixture_detected and remain blocked', () => {
    const review = readJson(REVIEW_RESULT_PATH);
    const artifact = readJson(ARTIFACT_PATH);
    const entries = review.review_entries;

    assert.equal(entries.length, 8);
    assert.equal(artifact.known_mappings.length, 8);

    for (const entry of entries) {
        const result = reconcileRouteIdentity({
            requestedScheduleExternalId: entry.schedule_external_id,
            requestedPageUrlBase: entry.page_url_base,
            requestedHomeTeam: entry.home_team,
            requestedAwayTeam: entry.away_team,
            requestedMatchDate: entry.schedule_match_date,
            requestedStatus: 'finished',
            requestedSeason: entry.season,
            observedDetailExternalId: entry.detail_external_id,
            observedPageUrlBase: entry.page_url_base,
            observedHomeTeam: entry.away_team,
            observedAwayTeam: entry.home_team,
            observedMatchDate: entry.detail_match_date,
            observedStatus: 'finished',
            observedSeason: entry.season,
            acceptedIdentityMappingPresent: true,
        });
        const gate = assertRawWriteIdentityGate(result);

        assert.equal(result.date_compatibility_status, 'reverse_fixture_detected', entry.schedule_external_id);
        assert.equal(result.reverse_fixture_detected, true);
        assert.equal(result.safety_blockers.includes('reverse_fixture_detected'), true);
        assert.equal(result.raw_write_blocked, true);
        assert.equal(gate.ok, false);
        assert.equal(gate.transaction_began, false);
        assert.equal(gate.inserted_raw_match_data_count, 0);
    }
});

test('L2V3M artifact keeps accepted and ready counts blocked', () => {
    const artifact = readJson(ARTIFACT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.review_blocked_count, 8);
    assert.equal(artifact.reverse_fixture_detected_count, 8);
    assert.equal(artifact.raw_write_guard_result.transaction_began, false);
    assert.equal(artifact.raw_write_guard_result.inserted_raw_match_data_count, 0);

    assert.equal(manifest.phase_5_21_l2v3m_review_blocked_count, 8);
    assert.equal(manifest.phase_5_21_l2v3m_raw_write_retry_performed, false);
    assert.equal(manifest.phase_5_21_l2v3m_transaction_began, false);
    assert.equal(manifest.phase_5_21_l2v3m_inserted_raw_match_data_count, 0);
});

test('L2V3M report and artifact avoid full payload markers', () => {
    const texts = [readText(ARTIFACT_PATH), readText(REPORT_PATH), readText(MANIFEST_PATH)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
    }
});
