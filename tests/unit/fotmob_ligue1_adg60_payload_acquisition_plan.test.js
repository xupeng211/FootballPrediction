// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    buildPlan,
} = require('../../scripts/ops/fotmob_ligue1_adg60_payload_acquisition_plan');

test('ADG60 payload acquisition plan keeps execution safety flags false', () => {
    const plan = buildPlan({ generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(plan.acquisition_performed, false);
    assert.equal(plan.payload_saved, false);
    assert.equal(plan.db_write_performed, false);
    assert.equal(plan.raw_write_performed, false);
    assert.equal(plan.raw_match_data_insert_performed, false);
    assert.equal(plan.adg60_write_performed, false);
    assert.equal(plan.safety.live_fetch_performed, false);
    assert.equal(plan.safety.network_fetch_performed, false);
    assert.equal(plan.safety.browser_automation_performed, false);
    assert.equal(plan.safety.schema_migration_performed, false);
});

test('ADG60 payload acquisition plan preserves target and blocker facts', () => {
    const plan = buildPlan({ generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(plan.authorization_required, true);
    assert.equal(plan.target_count, 32);
    assert.equal(plan.accepted_count, 32);
    assert.equal(plan.suspension_resolved_count, 32);
    assert.equal(plan.raw_write_ready_count, 0);
    assert.equal(plan.current_blockers.blocked_missing_payload, 32);
    assert.equal(plan.current_blockers.blocked_requires_explicit_write_authorization, 32);
});

test('ADG60 payload acquisition plan forbids dangerous execution paths', () => {
    const plan = buildPlan({ generatedAt: '2026-06-01T00:00:00.000Z' });
    const forbidden = new Set(plan.forbidden_execution_paths.map(item => item.path));
    assert.ok(forbidden.has('scripts/ops/single_league_pageprops_v2_controlled_write_execute.js'));
    assert.ok(forbidden.has('scripts/ops/renewed_pageprops_v2_raw_write_execute.js'));
    assert.ok(forbidden.has('scripts/ops/backfill_historical_raw_match_data.js'));
    assert.ok(plan.forbidden_execution_paths.every(item => item.reason));
});

test('ADG60 payload acquisition plan recommends authorization gate before execution', () => {
    const plan = buildPlan({ generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(plan.recommended_next_phase, NEXT_PHASE);
    assert.notEqual(plan.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-EXECUTION');
    assert.equal(plan.target_scope.allow_extra_target_discovery, false);
    assert.equal(plan.target_scope.allow_scope_expansion, false);
});
