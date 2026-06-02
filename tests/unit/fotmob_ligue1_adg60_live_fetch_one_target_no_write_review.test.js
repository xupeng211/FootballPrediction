// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    REVIEWED_PR,
    REVIEWED_MERGE_COMMIT,
    buildReview,
} = require('../../scripts/ops/fotmob_ligue1_adg60_live_fetch_one_target_no_write_review');

test('ADG60 one-target review has correct phase and reviewed PR', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE-REVIEW');
    assert.equal(review.review_scope.reviewed_pr, REVIEWED_PR);
    assert.equal(review.review_scope.reviewed_pr, 1407);
    assert.equal(review.review_scope.reviewed_merge_commit, REVIEWED_MERGE_COMMIT);
});

test('ADG60 one-target review confirms source result facts', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.reviewed_fetch_result.request_count, 1);
    assert.equal(review.reviewed_fetch_result.http_status, 200);
    assert.equal(review.reviewed_fetch_result.minimal_schema_flags.hasNextDataMarker, true);
    assert.equal(review.reviewed_fetch_result.minimal_schema_flags.hasPagePropsMarker, true);
    assert.equal(review.reviewed_fetch_result.body_persisted, false);
    assert.equal(review.reviewed_fetch_result.body_logged, false);
    assert.equal(review.reviewed_fetch_result.body_committed, false);
});

test('ADG60 one-target review accessibility verdict is pass', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.accessibility_review.route_reachable, true);
    assert.equal(review.accessibility_review.verdict, 'pass');
});

test('ADG60 one-target review payload shape verdict is pass', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.payload_shape_review.hasNextDataMarker_supports_nextjs_extraction, true);
    assert.equal(review.payload_shape_review.hasPagePropsMarker_supports_pageprops_route, true);
    assert.equal(review.payload_shape_review.verdict, 'pass');
});

test('ADG60 one-target review safety verdict is pass', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.safety_review.body_persisted, false);
    assert.equal(review.safety_review.db_write_performed, false);
    assert.equal(review.safety_review.raw_match_data_insert_performed, false);
    assert.equal(review.safety_review.adg60_write_performed, false);
    assert.equal(review.safety_review.raw_write_ready_marked, false);
    assert.equal(review.safety_review.verdict, 'pass');
});

test('ADG60 one-target review evidence quality is sufficient_for_next_authorization_phase_only', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.evidence_quality_review.does_not_support_raw_write_ready_true, true);
    assert.equal(review.evidence_quality_review.does_not_authorize_db_write, true);
    assert.equal(review.evidence_quality_review.does_not_authorize_raw_match_data_insert, true);
    assert.equal(review.evidence_quality_review.does_not_authorize_full_32_target_run, true);
    assert.equal(review.evidence_quality_review.verdict, 'sufficient_for_next_authorization_phase_only');
});

test('ADG60 one-target review readiness confirms next authorization phase only', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.readiness_decision.ready_for_next_phase, true);
    assert.equal(review.readiness_decision.next_phase_is_authorization_only, true);
    assert.equal(review.readiness_decision.next_phase_is_not_execution, true);
    assert.equal(review.readiness_decision.raw_write_ready_remains_false, true);
    assert.equal(review.readiness_decision.db_write_remains_prohibited, true);
    assert.equal(review.readiness_decision.adg60_write_remains_blocked, true);
});

test('ADG60 one-target review recommends three-target authorization next', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.recommended_next_phase, NEXT_PHASE);
    assert.equal(review.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-AUTHORIZATION');
    assert.ok(review.next_phase_gates.some(g => g.includes('Batch size max=3')));
    assert.ok(review.next_phase_gates.some(g => g.includes('Still no DB write')));
    assert.ok(review.next_phase_gates.some(g => g.includes('Still no body commit')));
});

test('ADG60 one-target review has no new live/network/browser fetch', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.new_live_fetch_performed, false);
    assert.equal(review.new_network_fetch_performed, false);
    assert.equal(review.new_browser_automation_performed, false);
});

test('ADG60 one-target review all write flags remain false', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(review.db_write_performed, false);
    assert.equal(review.raw_write_performed, false);
    assert.equal(review.raw_match_data_insert_performed, false);
    assert.equal(review.schema_migration_performed, false);
    assert.equal(review.adg60_write_performed, false);
    assert.equal(review.raw_write_ready_marked, false);
    assert.equal(review.payload_saved, false);
    assert.equal(review.response_body_saved, false);
});

test('ADG60 one-target review next phase gates include all required constraints', () => {
    const review = buildReview({ generatedAt: '2026-06-02T00:00:00.000Z' });

    const gates = review.next_phase_gates;
    assert.ok(gates.some(g => g.includes('Still no DB write')));
    assert.ok(gates.some(g => g.includes('Still no body commit')));
    assert.ok(gates.some(g => g.includes('Batch size max=3')));
    assert.ok(gates.some(g => g.includes('No parallel fetch')));
    assert.ok(gates.some(g => g.includes('Stop on any 403')));
    assert.ok(gates.some(g => g.includes('Review required after 3 targets')));
    assert.ok(gates.some(g => g.includes('Browser automation remains prohibited')));
});
