// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    REVIEWED_PR,
    REVIEWED_ONE_TARGET_PR,
    MAX_FUTURE_TARGET_COUNT,
    CANDIDATE_TARGET_INDICES,
    buildAuthorization,
} = require('../../scripts/ops/fotmob_ligue1_adg60_three_target_no_write_authorization');

test('ADG60 three-target authorization has correct phase and review refs', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-AUTHORIZATION');
    assert.equal(auth.reviewed_pr, REVIEWED_PR);
    assert.equal(auth.reviewed_pr, 1408);
    assert.equal(auth.reviewed_one_target_pr, REVIEWED_ONE_TARGET_PR);
    assert.equal(auth.reviewed_one_target_pr, 1407);
});

test('ADG60 three-target authorization has max 3 targets', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.max_future_target_count, MAX_FUTURE_TARGET_COUNT);
    assert.equal(auth.max_future_target_count, 3);
    assert.deepStrictEqual(auth.candidate_target_indices, CANDIDATE_TARGET_INDICES);
    assert.deepStrictEqual(auth.candidate_target_indices, [2, 3, 4]);
});

test('ADG60 three-target authorization candidates have valid route hashes', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.candidates.length, 3);
    for (const c of auth.candidates) {
        assert.ok(c.target_index >= 2 && c.target_index <= 4);
        assert.ok(c.identity_status === 'accepted_suspension_resolved');
        assert.ok(c.route_hash_available);
        assert.ok(c.corrected_hash_id);
        assert.ok(c.corrected_route_hash_pair);
    }
});

test('ADG60 three-target authorization all safety flags false', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.live_fetch_performed, false);
    assert.equal(auth.network_fetch_performed, false);
    assert.equal(auth.browser_automation_performed, false);
    assert.equal(auth.payload_saved, false);
    assert.equal(auth.response_body_saved, false);
    assert.equal(auth.db_write_performed, false);
    assert.equal(auth.raw_write_performed, false);
    assert.equal(auth.raw_match_data_insert_performed, false);
    assert.equal(auth.schema_migration_performed, false);
    assert.equal(auth.adg60_write_performed, false);
    assert.equal(auth.raw_write_ready_marked, false);
});

test('ADG60 three-target authorization write policy all blocked', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.write_policy.db_write_prohibited, true);
    assert.equal(auth.write_policy.raw_write_prohibited, true);
    assert.equal(auth.write_policy.raw_match_data_insert_prohibited, true);
    assert.equal(auth.write_policy.schema_migration_prohibited, true);
    assert.equal(auth.write_policy.adg60_write_blocked, true);
    assert.equal(auth.write_policy.raw_write_ready_remains_false, true);
});

test('ADG60 three-target authorization browser policy all prohibited', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.browser_policy.browser_automation_prohibited, true);
    assert.equal(auth.browser_policy.playwright_prohibited, true);
    assert.equal(auth.browser_policy.chromium_prohibited, true);
});

test('ADG60 three-target authorization execution policy is sequential only', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.future_execution_policy.max_network_requests, 3);
    assert.equal(auth.future_execution_policy.sequential_only, true);
    assert.equal(auth.future_execution_policy.no_parallel_fetch, true);
    assert.equal(auth.future_execution_policy.no_retry, true);
});

test('ADG60 three-target authorization review policy blocks auto-expansion', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.review_policy.review_required_after_3_targets, true);
    assert.equal(auth.review_policy.no_automatic_next_batch, true);
    assert.equal(auth.review_policy.no_automatic_32_target_run, true);
    assert.equal(auth.review_policy.any_failure_blocks_expansion, true);
});

test('ADG60 three-target authorization recommends three-target no-write execution next', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.recommended_next_phase, NEXT_PHASE);
    assert.equal(auth.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE');
    assert.equal(auth.readiness_decision.ready_for_next_authorization_phase, true);
    assert.equal(auth.readiness_decision.execution_deferred_to_separate_pr, true);
});

test('ADG60 three-target authorization stop conditions cover all required guards', () => {
    const auth = buildAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    const sc = auth.stop_conditions;
    assert.ok(sc.some(c => c.includes('403')));
    assert.ok(sc.some(c => c.includes('429')));
    assert.ok(sc.some(c => c.includes('captcha')));
    assert.ok(sc.some(c => c.includes('identity mismatch')));
    assert.ok(sc.some(c => c.includes('DB write attempted')));
    assert.ok(sc.some(c => c.includes('raw_match_data insert attempted')));
    assert.ok(sc.some(c => c.includes('parallel fetch attempted')));
    assert.ok(sc.some(c => c.includes('browser automation attempted')));
    assert.ok(sc.some(c => c.includes('more targets than authorized batch')));
});
