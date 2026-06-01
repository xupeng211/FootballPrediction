// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    USER_AUTHORIZATION_QUOTE,
    buildAuthorizationGate,
} = require('../../scripts/ops/fotmob_ligue1_adg60_payload_acquisition_authorization_gate');

test('ADG60 authorization gate captures user authorization without write authorization', () => {
    const gate = buildAuthorizationGate({ generatedAt: '2026-06-02T00:00:00.000Z' });
    assert.equal(gate.user_authorization_quote, USER_AUTHORIZATION_QUOTE);
    assert.equal(gate.authorization_interpretation.authorization_gate_only, true);
    assert.equal(gate.authorization_interpretation.db_write_authorized, false);
    assert.equal(gate.authorization_interpretation.raw_match_data_write_authorized, false);
    assert.notEqual(gate.authorization_interpretation.summary, 'DB write authorization');
    assert.notEqual(gate.authorization_interpretation.summary, 'raw_match_data write authorization');
});

test('ADG60 authorization gate preserves target and blocker facts', () => {
    const gate = buildAuthorizationGate({ generatedAt: '2026-06-02T00:00:00.000Z' });
    assert.equal(gate.target_count, 32);
    assert.equal(gate.current_blockers.blocked_missing_payload, 32);
    assert.equal(gate.current_blockers.blocked_requires_explicit_write_authorization, 32);
    assert.equal(gate.current_blockers.raw_write_ready_count, 0);
});

test('ADG60 authorization gate keeps execution safety flags false', () => {
    const gate = buildAuthorizationGate({ generatedAt: '2026-06-02T00:00:00.000Z' });
    assert.equal(gate.live_fetch_performed, false);
    assert.equal(gate.network_fetch_performed, false);
    assert.equal(gate.browser_automation_performed, false);
    assert.equal(gate.payload_saved, false);
    assert.equal(gate.acquisition_execution_performed, false);
    assert.equal(gate.db_write_performed, false);
    assert.equal(gate.raw_write_performed, false);
    assert.equal(gate.raw_match_data_insert_performed, false);
    assert.equal(gate.schema_migration_performed, false);
    assert.equal(gate.adg60_write_performed, false);
});

test('ADG60 authorization gate recommends dry-run no-write next phase', () => {
    const gate = buildAuthorizationGate({ generatedAt: '2026-06-02T00:00:00.000Z' });
    assert.equal(gate.recommended_next_phase, NEXT_PHASE);
    assert.equal(gate.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE');
    assert.ok(gate.next_phase_boundary.includes('must not write DB or raw_match_data'));
});
