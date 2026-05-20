'use strict';
/* eslint-disable max-lines -- L2V3N safety contract stays together for auditability. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_expanded_date_rule_verification.js');

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

function syntheticTarget(overrides = {}) {
    return {
        match_id: '53_20252026_9000001',
        external_id: '9000001',
        home_team: 'Home FC',
        away_team: 'Away FC',
        match_date: '2025-08-15T18:45:00.000Z',
        kickoff_time: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        season: '2025/2026',
        page_url_base: '/matches/home-fc-vs-away-fc/testslug',
        ...overrides,
    };
}

function syntheticReview(overrides = {}) {
    return {
        schedule_external_id: '9000001',
        detail_external_id: '9000001',
        page_url_base: '/matches/home-fc-vs-away-fc/testslug',
        home_team: 'Away FC',
        away_team: 'Home FC',
        detail_match_date: '2025-08-15T18:45:00.000Z',
        season: '2025/2026',
        ...overrides,
    };
}

test('L2V3N artifact records no-write expanded verification only', () => {
    const artifact = readJson(mod.VERIFICATION_ARTIFACT_PATH);
    const manifest = readJson(mod.MANIFEST_PATH);

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3N');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.source_controlled_metadata_only, true);
    assert.equal(artifact.live_source_check_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);

    assert.equal(manifest.phase_5_21_l2v3n_verification_status, 'completed_no_write_source_controlled_metadata_only');
    assert.equal(manifest.phase_5_21_l2v3n_accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('expanded verification covers 50 targets and does not accept mappings', () => {
    const artifact = readJson(mod.VERIFICATION_ARTIFACT_PATH);

    assert.equal(artifact.target_summaries.length, 50);
    assert.equal(artifact.checked_target_count, 50);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.counts.accepted_mapping_count, 0);
    assert.equal(artifact.verification_contract.expanded_verification_result_is_not_accepted_mapping, true);
    assert.equal(artifact.verification_contract.safe_to_consider_for_future_review_is_not_accepted_mapping, true);

    for (const summary of artifact.target_summaries) {
        assert.equal(summary.accepted_mapping, false, summary.schedule_external_id);
        assert.equal(summary.raw_write_authorized, false, summary.schedule_external_id);
    }
});

test('8 known L2V3L mappings remain reverse_fixture_detected and blocked', () => {
    const artifact = readJson(mod.VERIFICATION_ARTIFACT_PATH);
    const expected = new Map([
        ['4830466', '4830759'],
        ['4830461', '4830758'],
        ['4830481', '4830763'],
        ['4830496', '4830757'],
        ['4830511', '4830760'],
        ['4830463', '4830622'],
        ['4830465', '4830619'],
        ['4830508', '4830620'],
    ]);

    assert.equal(artifact.reverse_fixture_detected_count, 8);
    assert.equal(artifact.known_mappings_classification.length, 8);

    for (const [scheduleId, detailId] of expected.entries()) {
        const summary = artifact.target_summaries.find(item => item.schedule_external_id === scheduleId);
        assert.equal(summary.observed_detail_external_id, detailId, scheduleId);
        assert.equal(summary.date_rule_status, 'reverse_fixture_detected', scheduleId);
        assert.equal(summary.raw_write_blocked, true, scheduleId);
        assert.equal(summary.review_blocked, true, scheduleId);
        assert.equal(summary.accepted_mapping, false, scheduleId);
        assert.equal(summary.safety_blockers.includes('reverse_fixture_detected'), true, scheduleId);
    }
});

test('remaining targets without observed detail metadata stay unknown and blocked', () => {
    const artifact = readJson(mod.VERIFICATION_ARTIFACT_PATH);
    const unknownSummaries = artifact.target_summaries.filter(item => item.date_rule_status === 'unknown');

    assert.equal(artifact.unknown_count, 42);
    assert.equal(unknownSummaries.length, 42);
    assert.equal(artifact.raw_write_blocked_count, 50);
    assert.equal(artifact.identity_mapping_acceptance_blocked_count, 50);
    assert.equal(artifact.safe_to_consider_for_future_review_count, 0);

    for (const summary of unknownSummaries) {
        assert.equal(summary.raw_write_blocked, true, summary.schedule_external_id);
        assert.equal(summary.identity_mapping_acceptance_blocker_status, 'blocked', summary.schedule_external_id);
        assert.equal(summary.accepted_mapping, false, summary.schedule_external_id);
        assert.equal(summary.safety_blockers.includes('unknown'), true, summary.schedule_external_id);
    }
});

test('date_match and same_utc_day are review evidence, not accepted mappings', () => {
    const dateMatch = mod.buildTargetSummary(syntheticTarget(), syntheticReview());
    const sameUtcDay = mod.buildTargetSummary(
        syntheticTarget({ external_id: '9000002', match_id: '53_20252026_9000002' }),
        syntheticReview({
            schedule_external_id: '9000002',
            detail_external_id: '9000002',
            detail_match_date: '2025-08-15T20:00:00.000Z',
        })
    );

    assert.equal(dateMatch.date_rule_status, 'date_match');
    assert.equal(dateMatch.safe_to_consider_for_future_review, true);
    assert.equal(dateMatch.accepted_mapping, false);
    assert.equal(dateMatch.raw_write_authorized, false);

    assert.equal(sameUtcDay.date_rule_status, 'same_utc_day');
    assert.equal(sameUtcDay.safe_to_consider_for_future_review, true);
    assert.equal(sameUtcDay.accepted_mapping, false);
    assert.equal(sameUtcDay.raw_write_authorized, false);
});

test('unresolved_large_gap and unknown remain blocked in L2V3N summaries', () => {
    const unresolvedLargeGap = mod.buildTargetSummary(
        syntheticTarget(),
        syntheticReview({ detail_match_date: '2026-01-30T18:45:00.000Z' })
    );
    const unknown = mod.buildTargetSummary(syntheticTarget(), null);

    assert.equal(unresolvedLargeGap.date_rule_status, 'unresolved_large_gap');
    assert.equal(unresolvedLargeGap.raw_write_blocked, true);
    assert.equal(unresolvedLargeGap.identity_mapping_acceptance_blocker_status, 'blocked');
    assert.equal(unresolvedLargeGap.accepted_mapping, false);

    assert.equal(unknown.date_rule_status, 'unknown');
    assert.equal(unknown.raw_write_blocked, true);
    assert.equal(unknown.identity_mapping_acceptance_blocker_status, 'blocked');
    assert.equal(unknown.accepted_mapping, false);
});

test('L2V3N artifacts avoid full raw_data pageProps and source body payloads', () => {
    const texts = [readText(mod.VERIFICATION_ARTIFACT_PATH), readText(mod.REPORT_PATH), readText(mod.MANIFEST_PATH)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
