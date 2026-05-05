'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const GATE_SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/acquisition_engine_gate.js');
const LEGACY_SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/titan_discovery.js');
const REGISTRY_PATH = path.join(PROJECT_ROOT, 'config/acquisition_engines.phase454.json');
const SOURCE_MANIFEST = 'tests/fixtures/real_source_manifests/local_sample_history_phase452.json';
const ENGINE_ID = 'titan_discovery';

function loadRegistryEngine(engineId) {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    const engines = Array.isArray(registry?.engines) ? registry.engines : [];
    return engines.find(engine => engine.id === engineId) || null;
}

function runGate(args) {
    return spawnSync(process.execPath, [GATE_SCRIPT_PATH, ...args], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
}

function parseJsonOutput(result) {
    const payload = String(result.stdout || '').trim();
    assert.notEqual(payload, '', 'expected JSON payload in stdout');
    return JSON.parse(payload);
}

function assertNoExecutionFlags(payload) {
    assert.ok(Array.isArray(payload.non_execution_confirmations));
    assert.ok(payload.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
    assert.ok(payload.non_execution_confirmations.includes('no_engine_execution'));
}

test('titan_discovery 在 registry 中保持 adapter_candidate 治理状态', () => {
    const engine = loadRegistryEngine(ENGINE_ID);

    assert.ok(engine, 'registry should contain titan_discovery');
    assert.equal(engine.status, 'adapter_candidate');
    assert.equal(engine.safe_for_ai_default, false);
    assert.equal(engine.canonical_entrypoint, false);
    assert.equal(engine.allowed_next_phase, 'requires_future_network_dry_run_authorization');
    assert.equal(engine.phase454_policy, 'blocked');
    assert.equal(engine.accesses_network, true);
    assert.equal(engine.writes_db, true);
    assert.equal(engine.supports_dry_run, true);
    assert.equal(engine.dry_run_trust_level, 'low');
    assert.equal(engine.test_coverage, 'gate_covered');
    assert.match(engine.notes, /dry-run trust is insufficient/i);
    assert.match(engine.replacement_plan, /Layer 2 discovery-only adapter/i);
});

test('titan_discovery legacy runtime file 存在但不得在测试中执行', () => {
    assert.equal(fs.existsSync(LEGACY_SCRIPT_PATH), true);
});

test('acquisition gate 对 titan_discovery 保持 scaffold-only blocked 且不触网不写库', () => {
    const result = runGate([
        '--engine',
        ENGINE_ID,
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
    assert.equal(payload.engine_id, ENGINE_ID);
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

test('acquisition gate 对 titan_discovery 的 --commit 必须 blocked', () => {
    const result = runGate([
        '--engine',
        ENGINE_ID,
        '--target-match-id',
        '47_20242025_900002',
        '--source-manifest',
        SOURCE_MANIFEST,
        '--commit',
        '--json',
    ]);
    const payload = parseJsonOutput(result);

    assert.notEqual(result.status, 0);
    assert.equal(payload.mode, 'blocked-commit');
    assert.equal(payload.engine_id, ENGINE_ID);
    assert.match(payload.blocked_reason, /not wired in Phase 4\.54/);
    assertNoExecutionFlags(payload);
});
