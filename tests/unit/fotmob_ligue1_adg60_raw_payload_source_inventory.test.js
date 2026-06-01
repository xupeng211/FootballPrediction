// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    buildInventory,
} = require('../../scripts/ops/fotmob_ligue1_adg60_raw_payload_source_inventory');

test('ADG60 raw payload inventory keeps all execution safety flags false', () => {
    const inventory = buildInventory({ generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(inventory.acquisition_performed, false);
    assert.equal(inventory.payload_saved, false);
    assert.equal(inventory.db_write_performed, false);
    assert.equal(inventory.raw_write_performed, false);
    assert.equal(inventory.adg60_write_performed, false);
    assert.equal(inventory.safety.live_fetch_performed, false);
    assert.equal(inventory.safety.network_fetch_performed, false);
    assert.equal(inventory.safety.browser_automation_performed, false);
    assert.equal(inventory.safety.raw_match_data_insert_performed, false);
    assert.equal(inventory.safety.schema_migration_performed, false);
});

test('ADG60 raw payload inventory identifies pageProps and raw_match_data code paths', () => {
    const inventory = buildInventory({ generatedAt: '2026-06-01T00:00:00.000Z' });
    const files = new Set(inventory.candidate_files);
    assert.ok(files.has('scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js'));
    assert.ok(files.has('scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js'));
    assert.ok(files.has('scripts/ops/raw_match_data_completeness_fidelity_audit.js'));
    assert.ok(files.has('src/infrastructure/services/FotMobRawDetailFetcher.js'));
});

test('ADG60 raw payload inventory marks write-capable paths as not directly reusable', () => {
    const inventory = buildInventory({ generatedAt: '2026-06-01T00:00:00.000Z' });
    const writeCapable = inventory.per_file_classification.filter(
        item => item.safety_level === 'dangerous_write_capable'
    );
    assert.ok(writeCapable.length > 0);
    assert.ok(writeCapable.every(item => ['reference_only', 'do_not_use'].includes(item.reuse_for_adg60)));
});

test('ADG60 raw payload inventory preserves current blocker context', () => {
    const inventory = buildInventory({ generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(inventory.current_blocker.blocked_missing_payload, 32);
    assert.equal(inventory.current_blocker.raw_match_data_exists, 0);
    assert.equal(inventory.current_blocker.target_count, 32);
    assert.equal(inventory.target_adaptability.authorization_required_before_execution, true);
    assert.equal(inventory.target_adaptability.plan_only_possible_without_fetch, true);
});
