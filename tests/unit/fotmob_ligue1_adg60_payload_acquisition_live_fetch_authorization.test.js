// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    buildLiveFetchAuthorization,
} = require('../../scripts/ops/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization');

test('ADG60 live-fetch authorization preserves target and blocker facts', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION');
    assert.equal(auth.target_count, 32);
    assert.equal(auth.current_blockers.blocked_missing_payload, 32);
    assert.equal(auth.current_blockers.blocked_requires_explicit_write_authorization, 32);
    assert.equal(auth.raw_write_ready_count, 0);
    assert.equal(auth.dry_run_matrix_count, 32);
});

test('ADG60 live-fetch authorization keeps all execution safety flags false', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.live_fetch_performed, false);
    assert.equal(auth.network_fetch_performed, false);
    assert.equal(auth.browser_automation_performed, false);
    assert.equal(auth.payload_saved, false);
    assert.equal(auth.acquisition_execution_performed, false);
    assert.equal(auth.db_write_performed, false);
    assert.equal(auth.raw_write_performed, false);
    assert.equal(auth.raw_match_data_insert_performed, false);
    assert.equal(auth.schema_migration_performed, false);
    assert.equal(auth.adg60_write_performed, false);
});

test('ADG60 live-fetch authorization contract flags are set correctly', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.authorization_contract.authorization_stage_requested, true);
    assert.equal(auth.authorization_contract.live_fetch_may_be_requested_in_next_phase, true);
    assert.equal(auth.authorization_contract.network_fetch_may_be_requested_in_next_phase, true);
    assert.equal(auth.authorization_contract.browser_automation_may_be_requested_in_next_phase, false);
    assert.equal(auth.authorization_contract.current_pr_live_fetch_performed, false);
    assert.equal(auth.authorization_contract.current_pr_network_fetch_performed, false);
    assert.equal(auth.authorization_contract.current_pr_browser_automation_performed, false);
});

test('ADG60 live-fetch authorization batch policy is correctly bounded', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.batch_policy.initial_batch_size, 1);
    assert.ok(auth.batch_policy.max_batch_size_before_review <= 3);
    assert.equal(auth.batch_policy.no_automatic_32_target_full_run_in_first_execution_pr, true);
    assert.equal(auth.batch_policy.require_manual_review_after_first_successful_target, true);
    assert.equal(auth.batch_policy.require_manual_review_after_any_mismatch, true);
    assert.equal(auth.batch_policy.batch_size_increase_requires_separate_authorization_pr, true);
});

test('ADG60 live-fetch authorization rate-limit policy prohibits parallel fetch in first execution', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.rate_limit_policy.no_parallel_fetch_in_first_execution_pr, true);
    assert.ok(auth.rate_limit_policy.minimum_delay_between_requests_seconds.min >= 10);
    assert.ok(auth.rate_limit_policy.minimum_delay_between_requests_seconds.max >= 30);
    assert.equal(auth.rate_limit_policy.no_retry_storm, true);
    assert.equal(auth.rate_limit_policy.max_requests_per_run_must_be_explicitly_declared, true);
});

test('ADG60 live-fetch authorization DB/raw write policy remains fully locked', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.db_raw_write_policy.db_write_prohibited, true);
    assert.equal(auth.db_raw_write_policy.raw_write_prohibited, true);
    assert.equal(auth.db_raw_write_policy.raw_match_data_insert_prohibited, true);
    assert.equal(auth.db_raw_write_policy.schema_migration_prohibited, true);
    assert.equal(auth.db_raw_write_policy.adg60_write_blocked, true);
    assert.equal(auth.db_raw_write_policy.raw_write_ready_count_remains_0, true);
    assert.equal(auth.db_raw_write_policy.future_payload_capture_success_does_not_imply_raw_write_ready, true);
});

test('ADG60 live-fetch authorization stop conditions include all required guards', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    const conditions = auth.stop_conditions;
    assert.ok(conditions.some(c => c.includes('target identity mismatch')));
    assert.ok(conditions.some(c => c.includes('home/away orientation mismatch')));
    assert.ok(conditions.some(c => c.includes('expected date mismatch')));
    assert.ok(conditions.some(c => c.includes('competition mismatch')));
    assert.ok(conditions.some(c => c.includes('missing corrected_hash_id')));
    assert.ok(conditions.some(c => c.includes('missing route hash')));
    assert.ok(conditions.some(c => c.includes('duplicate raw_match_data')));
    assert.ok(conditions.some(c => c.includes('git-tracked path')));
    assert.ok(conditions.some(c => c.includes('full HTML')));
    assert.ok(conditions.some(c => c.includes('full pageProps')));
    assert.ok(conditions.some(c => c.includes('DB write attempted')));
    assert.ok(conditions.some(c => c.includes('raw_match_data insert attempted')));
    assert.ok(conditions.some(c => c.includes('403')));
    assert.ok(conditions.some(c => c.includes('429')));
    assert.ok(conditions.some(c => c.includes('captcha')));
    assert.ok(conditions.some(c => c.includes('payload too large')));
    assert.ok(conditions.some(c => c.includes('automatic retry loop')));
});

test('ADG60 live-fetch authorization recommends one-target no-write next', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.recommended_next_phase, NEXT_PHASE);
    assert.equal(auth.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE');
    assert.ok(auth.next_phase_boundary.includes('at most 1 target'));
    assert.ok(auth.next_phase_boundary.includes('DB write'));
    assert.ok(auth.next_phase_boundary.includes('raw_match_data insert'));
});

test('ADG60 live-fetch authorization payload persistence policy defaults to no-persist', () => {
    const auth = buildLiveFetchAuthorization({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(auth.payload_persistence_policy.payload_saved_in_this_pr, false);
    assert.equal(auth.payload_persistence_policy.payload_persistence_must_be_separately_authorized, true);
    assert.equal(auth.payload_persistence_policy.full_raw_payload_not_committed_to_git, true);
    assert.equal(auth.payload_persistence_policy.raw_payload_storage_path_must_be_gitignored, true);
    assert.equal(auth.payload_persistence_policy.verify_gitignore_before_any_payload_persistence, true);
});
