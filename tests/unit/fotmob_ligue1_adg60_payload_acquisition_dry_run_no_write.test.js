// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    NEXT_PHASE,
    buildDryRun,
} = require('../../scripts/ops/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write');

test('ADG60 dry-run no-write preserves target and blocker facts', () => {
    const dryRun = buildDryRun({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(dryRun.target_count, 32);
    assert.equal(dryRun.current_blockers.blocked_missing_payload, 32);
    assert.equal(dryRun.current_blockers.blocked_requires_explicit_write_authorization, 32);
    assert.equal(dryRun.raw_write_ready_count, 0);
    assert.equal(dryRun.dry_run_matrix.length, 32);
});

test('ADG60 dry-run no-write keeps execution safety flags false', () => {
    const dryRun = buildDryRun({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(dryRun.live_fetch_performed, false);
    assert.equal(dryRun.network_fetch_performed, false);
    assert.equal(dryRun.browser_automation_performed, false);
    assert.equal(dryRun.payload_saved, false);
    assert.equal(dryRun.acquisition_execution_performed, false);
    assert.equal(dryRun.db_write_performed, false);
    assert.equal(dryRun.raw_write_performed, false);
    assert.equal(dryRun.raw_match_data_insert_performed, false);
    assert.equal(dryRun.adg60_write_performed, false);
});

test('ADG60 dry-run no-write command preview is not executed', () => {
    const dryRun = buildDryRun({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(dryRun.command_preview.command_preview_only, true);
    assert.equal(dryRun.command_preview.executed, false);
    assert.equal(dryRun.command_preview.network_performed, false);
    assert.equal(dryRun.command_preview.payload_saved, false);
    assert.equal(dryRun.command_preview.db_write_performed, false);
});

test('ADG60 dry-run no-write matrix remains planned only', () => {
    const dryRun = buildDryRun({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(dryRun.dry_run_matrix.every(target => target.dry_run_action === 'planned_only'), true);
    assert.equal(dryRun.dry_run_matrix.every(target => target.network_fetch_allowed_in_this_pr === false), true);
    assert.equal(dryRun.dry_run_matrix.every(target => target.payload_save_allowed_in_this_pr === false), true);
    assert.equal(dryRun.dry_run_matrix.every(target => target.raw_match_data_insert_allowed_in_this_pr === false), true);
});

test('ADG60 dry-run no-write recommends live-fetch authorization next', () => {
    const dryRun = buildDryRun({ generatedAt: '2026-06-02T00:00:00.000Z' });

    assert.equal(dryRun.recommended_next_phase, NEXT_PHASE);
    assert.equal(dryRun.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION');
    assert.ok(dryRun.next_phase_boundary.includes('separately authorize live/network access'));
});
