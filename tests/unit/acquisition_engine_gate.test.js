'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/acquisition_engine_gate.js');
const REGISTRY_PATH = path.join(PROJECT_ROOT, 'config/acquisition_engines.phase454.json');
const SOURCE_MANIFEST = 'tests/fixtures/real_source_manifests/local_sample_history_phase452.json';
const REQUIRED_ENGINE_FIELDS = [
    'id',
    'category',
    'entrypoint',
    'accesses_network',
    'writes_db',
    'supports_dry_run',
    'dry_run_trust_level',
    'supports_commit',
    'bulk_risk',
    'tos_license_risk',
    'provenance_required',
    'safe_for_ai_default',
    'phase454_policy',
];
const REQUIRED_GOVERNANCE_FIELDS = [
    'owner',
    'status',
    'intended_layer',
    'replacement_plan',
    'deprecation_status',
    'canonical_entrypoint',
    'allowed_next_phase',
    'test_coverage',
];
const ALLOWED_STATUS_VALUES = new Set([
    'canonical',
    'gate_only',
    'quarantine',
    'deprecation_candidate',
    'adapter_candidate',
    'legacy_blocked',
]);
const ALLOWED_INTENDED_LAYER_VALUES = new Set([
    'layer_0_registry_policy',
    'layer_1_source_manifest',
    'layer_2_discovery',
    'layer_3_single_target_acquisition',
    'layer_4_local_staging_normalization',
    'layer_5_local_staging_dry_run',
    'layer_6_small_db_write',
    'layer_7_feature_dry_run',
    'layer_8_training_prediction',
    'legacy_bulk_pipeline',
    'legacy_production_path',
    'unknown',
]);
const ALLOWED_DEPRECATION_STATUS_VALUES = new Set([
    'not_deprecated',
    'watch',
    'quarantine',
    'deprecation_candidate',
    'deprecated_do_not_use',
]);
const ALLOWED_NEXT_PHASE_VALUES = new Set([
    'allowed_read_only',
    'requires_user_authorization',
    'requires_future_network_dry_run_authorization',
    'requires_future_db_write_authorization',
    'blocked',
    'blocked_legacy',
]);
const ALLOWED_TEST_COVERAGE_VALUES = new Set([
    'unit_covered',
    'gate_covered',
    'needs_unit_tests',
    'needs_integration_tests',
    'not_covered',
]);

function runGate(args) {
    const result = spawnSync(process.execPath, [SCRIPT_PATH, ...args], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    return {
        status: result.status ?? 1,
        stdout: result.stdout || '',
        stderr: result.stderr || '',
    };
}

function parseJsonOutput(result) {
    const payload = (result.stdout || '').trim();
    assert.notEqual(payload, '', 'expected JSON payload in stdout');
    return JSON.parse(payload);
}

function assertNoExecutionFlags(payload) {
    assert.ok(Array.isArray(payload.non_execution_confirmations));
    assert.ok(payload.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
    assert.ok(payload.non_execution_confirmations.includes('no_engine_execution'));
}

test('acquisition_engine_gate registry JSON 可解析且包含必需字段', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));

    assert.equal(registry.phase, '4.54');
    assert.equal(registry.registry_type, 'acquisition_engine_governance_registry');
    assert.ok(Array.isArray(registry.engines));
    assert.ok(registry.engines.length >= 13);

    for (const engine of registry.engines) {
        for (const field of REQUIRED_ENGINE_FIELDS) {
            assert.ok(field in engine, `missing field ${field} for engine ${engine.id}`);
        }
        for (const field of REQUIRED_GOVERNANCE_FIELDS) {
            assert.ok(field in engine, `missing governance field ${field} for engine ${engine.id}`);
        }
        assert.ok(ALLOWED_STATUS_VALUES.has(engine.status), `invalid status for ${engine.id}: ${engine.status}`);
        assert.ok(
            ALLOWED_INTENDED_LAYER_VALUES.has(engine.intended_layer),
            `invalid intended_layer for ${engine.id}: ${engine.intended_layer}`
        );
        assert.ok(
            ALLOWED_DEPRECATION_STATUS_VALUES.has(engine.deprecation_status),
            `invalid deprecation_status for ${engine.id}: ${engine.deprecation_status}`
        );
        assert.ok(
            ALLOWED_NEXT_PHASE_VALUES.has(engine.allowed_next_phase),
            `invalid allowed_next_phase for ${engine.id}: ${engine.allowed_next_phase}`
        );
        assert.ok(
            ALLOWED_TEST_COVERAGE_VALUES.has(engine.test_coverage),
            `invalid test_coverage for ${engine.id}: ${engine.test_coverage}`
        );
        assert.equal(typeof engine.canonical_entrypoint, 'boolean');
    }
});

test('acquisition_engine_gate --list 应成功并暴露 registry 摘要', () => {
    const result = runGate(['--list', '--json']);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 0);
    assert.equal(payload.mode, 'acquisition-engine-list');
    assert.equal(payload.registry_found, true);
    assert.equal(payload.registry_valid, true);
    assert.ok(payload.total_engines >= 13);
    assert.ok(payload.safe_for_ai_default_count >= 1);
    assert.ok(payload.blocked_count >= 1);
    assertNoExecutionFlags(payload);
});

test('acquisition_engine_gate --audit 应成功并标记高风险 engine', () => {
    const result = runGate(['--audit', '--json']);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 0);
    assert.equal(payload.mode, 'acquisition-engine-audit');
    assert.equal(payload.registry_found, true);
    assert.equal(payload.registry_valid, true);
    assert.equal(payload.governance_fields_complete, true);
    assert.deepEqual(payload.missing_governance_fields, []);
    assert.ok(payload.high_risk_engines.includes('run_production'));
    assert.ok(payload.blocked_engines.includes('run_production'));
    assert.ok(payload.allowed_read_only_engines.includes('real_finished_csv_staging_dry_run'));
    assert.ok(payload.canonical_engines.includes('real_finished_csv_staging_dry_run'));
    assert.ok(payload.gate_only_engines.includes('csv_bulk_loader'));
    assert.ok(payload.quarantine_engines.includes('recon_scanner'));
    assert.ok(payload.adapter_candidate_engines.includes('titan_discovery'));
    assert.ok(payload.legacy_blocked_engines.includes('run_production'));
    assert.ok(payload.engines_requiring_user_authorization.includes('real_finished_csv_staging_dry_run'));
    assert.ok(payload.engines_requiring_future_network_authorization.includes('titan_discovery'));
    assert.ok(payload.engines_requiring_future_db_write_authorization.includes('csv_bulk_loader'));
    assert.ok(payload.engines_needing_unit_tests.includes('csv_bulk_loader'));
    assert.deepEqual(payload.engines_missing_provenance_requirement, []);
    assertNoExecutionFlags(payload);
});

test('高风险 engine run_production 在 --engine 模式下必须 blocked 且不触网不写库', () => {
    const result = runGate([
        '--engine',
        'run_production',
        '--target-match-id',
        '47_20242025_900002',
        '--source-manifest',
        SOURCE_MANIFEST,
        '--json',
    ]);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 1);
    assert.equal(payload.mode, 'single-target-network-scaffold');
    assert.equal(payload.engine_found, true);
    assert.equal(payload.engine_id, 'run_production');
    assert.equal(payload.phase454_policy, 'blocked');
    assert.equal(payload.accesses_network, true);
    assert.equal(payload.writes_db, true);
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.missing_source_manifest, false);
    assert.equal(payload.missing_target_scope, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_execute_engine, false);
    assert.match(payload.blocked_reason, /Phase 4\.54 is scaffold-only/);
    assertNoExecutionFlags(payload);
});

test('acquisition_engine_gate --commit 必须立即 blocked', () => {
    const result = runGate([
        '--engine',
        'run_production',
        '--target-match-id',
        '47_20242025_900002',
        '--source-manifest',
        SOURCE_MANIFEST,
        '--commit',
        '--json',
    ]);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 1);
    assert.equal(payload.mode, 'blocked-commit');
    assert.equal(payload.engine_id, 'run_production');
    assert.match(payload.blocked_reason, /not wired in Phase 4\.54/);
    assertNoExecutionFlags(payload);
});

test('acquisition_engine_gate 缺少 SOURCE_MANIFEST 时必须失败且不执行引擎', () => {
    const result = runGate(['--engine', 'run_production', '--target-match-id', '47_20242025_900002', '--json']);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 1);
    assert.equal(payload.engine_found, true);
    assert.equal(payload.missing_source_manifest, true);
    assert.equal(payload.missing_target_scope, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_execute_engine, false);
    assert.match(payload.blocked_reason, /missing SOURCE_MANIFEST/);
    assertNoExecutionFlags(payload);
});

test('acquisition_engine_gate 缺少 TARGET_MATCH_ID 时必须失败且不执行引擎', () => {
    const result = runGate(['--engine', 'run_production', '--source-manifest', SOURCE_MANIFEST, '--json']);
    const payload = parseJsonOutput(result);

    assert.equal(result.status, 1);
    assert.equal(payload.engine_found, true);
    assert.equal(payload.missing_source_manifest, false);
    assert.equal(payload.missing_target_scope, true);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_execute_engine, false);
    assert.match(payload.blocked_reason, /missing TARGET_MATCH_ID/);
    assertNoExecutionFlags(payload);
});

test('acquisition_engine_gate 缺少模式参数时必须失败', () => {
    const result = runGate([]);

    assert.equal(result.status, 1);
    assert.match(result.stderr, /ERROR: provide --list, --audit, or --engine <id>/);
    assert.match(result.stderr, /Usage:/);
});
