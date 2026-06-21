#!/usr/bin/env node
/**
 * Unit tests for DB Write Safety Gate — unified guard helper.
 *
 * lifecycle: permanent
 * scope: unit safety coverage for scripts/ops/helpers/db_write_guard.js
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

// ═══════════════════════════════════════════════════════════════════════════════
// Load module under test — reloadable via function for env mutation
// ═══════════════════════════════════════════════════════════════════════════════

function loadGuard() {
    // Clear require cache to pick up env changes
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    return require('../../scripts/ops/helpers/db_write_guard');
}

function clearEnv() {
    delete process.env.ALLOW_DB_WRITE;
    delete process.env.FINAL_DB_WRITE_CONFIRMATION;
    delete process.env.ALLOW_RAW_MATCH_DATA_WRITE;
    delete process.env.ALLOW_MATCHES_WRITE;
    delete process.env.ALLOW_SCHEMA_WRITE;
    delete process.env.ALLOW_ODDS_WRITE;
    delete process.env.ALLOW_TRAINING_WRITE;
    delete process.env.DRY_RUN;
    delete process.env.NODE_ENV;
    delete process.env.APP_ENV;
    delete process.env.DB_HOST;
    delete process.env.DATABASE_URL;
}

function setEnv(key, value) {
    process.env[key] = value;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Test helpers
// ═══════════════════════════════════════════════════════════════════════════════

function guardBlocked(t, result) {
    assert.equal(result.allowed, false, `Expected blocked, got allowed. Error: ${result.error}`);
}

function guardAllowed(t, result) {
    assert.equal(result.allowed, true, `Expected allowed, got blocked. Missing: ${result.missingGates.join(',')}`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 1: 未设置任何 env 时，DB write guard 必须 block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 1: blocks when no env vars set (dry-run default)', (t) => {
    clearEnv();
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.equal(result.dryRun, true, 'Should be dry-run by default');
});

test('Scenario 1b: blocks when no env vars set for matches', (t) => {
    clearEnv();
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.equal(result.dryRun, true);
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 2: 只设置 ALLOW_DB_WRITE=yes，但没有 FINAL_DB_WRITE_CONFIRMATION=yes，必须 block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 2: blocks with ALLOW_DB_WRITE=yes but missing FINAL_DB_WRITE_CONFIRMATION', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('FINAL_DB_WRITE_CONFIRMATION'),
        'Should report FINAL_DB_WRITE_CONFIRMATION as missing');
});

test('Scenario 2b: blocks with FINAL_DB_WRITE_CONFIRMATION=yes but missing ALLOW_DB_WRITE', (t) => {
    clearEnv();
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_DB_WRITE'),
        'Should report ALLOW_DB_WRITE as missing');
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 3: 设置通用 gate 但缺 raw_match_data gate，raw 写入必须 block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 3: blocks raw_match_data write without ALLOW_RAW_MATCH_DATA_WRITE', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_RAW_MATCH_DATA_WRITE'),
        'Should report ALLOW_RAW_MATCH_DATA_WRITE as missing');
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 4: 设置通用 gate 但缺 matches gate，matches 写入必须 block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 4: blocks matches write without ALLOW_MATCHES_WRITE', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_MATCHES_WRITE'),
        'Should report ALLOW_MATCHES_WRITE as missing');
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 5: DRY_RUN 默认 true 时，不允许真实 write-run
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 5: DRY_RUN defaults to true', (t) => {
    clearEnv();
    const { isDryRun } = loadGuard();

    assert.equal(isDryRun(), true, 'isDryRun() should return true by default');
});

test('Scenario 5b: DRY_RUN=false with all gates → write-run allowed', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardAllowed(t, result);
    assert.equal(result.dryRun, false);
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 6: DRY_RUN=false + 通用 gate + 表级 gate 都满足时，guard 才允许通过
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 6a: all gates satisfied for raw_match_data → allowed', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardAllowed(t, result);
});

test('Scenario 6b: all gates satisfied for matches → allowed', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_MATCHES_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['INSERT'],
    });

    guardAllowed(t, result);
});

test('Scenario 6c: all gates satisfied for odds → allowed', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_ODDS_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['bookmaker_odds_history'],
        operations: ['INSERT'],
    });

    guardAllowed(t, result);
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 7: DELETE / TRUNCATE / DROP 类操作缺高危 gate 必须 block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 7a: DELETE blocked without ALLOW_SCHEMA_WRITE', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_MATCHES_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['DELETE'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_SCHEMA_WRITE'),
        'Should report ALLOW_SCHEMA_WRITE as missing for DELETE');
});

test('Scenario 7b: TRUNCATE blocked without ALLOW_SCHEMA_WRITE', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['TRUNCATE'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_SCHEMA_WRITE'));
});

test('Scenario 7c: DROP blocked without ALLOW_SCHEMA_WRITE', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['DROP'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_SCHEMA_WRITE'));
});

test('Scenario 7d: DELETE allowed with ALLOW_SCHEMA_WRITE=yes + all other gates', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_MATCHES_WRITE', 'yes');
    setEnv('ALLOW_SCHEMA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['matches'],
        operations: ['DELETE'],
    });

    guardAllowed(t, result);
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 8: 错误信息必须包含缺失 gate 名称
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 8a: error message names all missing gates', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'my_script.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.error, 'Error message must exist');
    assert.ok(result.error.includes('ALLOW_DB_WRITE'), 'Error must mention ALLOW_DB_WRITE');
    assert.ok(result.error.includes('FINAL_DB_WRITE_CONFIRMATION'),
        'Error must mention FINAL_DB_WRITE_CONFIRMATION');
});

test('Scenario 8b: error message includes script name', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'backfill_historical.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    assert.ok(result.error.includes('backfill_historical.js'),
        'Error must include script name');
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 9: 目标脚本能 require guard，不出现语法错误
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 9a: guard module exports expected functions', (t) => {
    clearEnv();
    const guard = loadGuard();

    assert.equal(typeof guard.requireDbWriteGuards, 'function');
    assert.equal(typeof guard.assertDbWriteAllowed, 'function');
    assert.equal(typeof guard.isDryRun, 'function');
    assert.equal(typeof guard.describeRequiredGates, 'function');
});

test('Scenario 9b: guard can be required without side effects', (t) => {
    clearEnv();
    // Should not throw
    const guard = require('../../scripts/ops/helpers/db_write_guard');
    assert.ok(guard, 'Module should load successfully');
});

test('Scenario 9c: describeRequiredGates returns correct structure', (t) => {
    clearEnv();
    const { describeRequiredGates } = loadGuard();

    const gates = describeRequiredGates({
        tables: ['raw_match_data', 'bookmaker_odds_history'],
        operations: ['INSERT', 'DELETE'],
    });

    assert.ok(Array.isArray(gates.universal));
    assert.ok(Array.isArray(gates.tableLevel));
    assert.ok(Array.isArray(gates.schemaLevel));
    assert.ok(gates.universal.includes('ALLOW_DB_WRITE'));
    assert.ok(gates.universal.includes('FINAL_DB_WRITE_CONFIRMATION'));
    assert.ok(gates.tableLevel.includes('ALLOW_RAW_MATCH_DATA_WRITE'));
    assert.ok(gates.tableLevel.includes('ALLOW_ODDS_WRITE'));
    assert.ok(gates.schemaLevel.includes('ALLOW_SCHEMA_WRITE'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 10: Production environment detection
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 10a: NODE_ENV=production blocks write', (t) => {
    clearEnv();
    setEnv('NODE_ENV', 'production');
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.error.includes('production'), 'Error should mention production');
});

test('Scenario 10b: APP_ENV=production blocks write', (t) => {
    clearEnv();
    setEnv('APP_ENV', 'production');
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
});

test('Scenario 10c: production DB host generates warnings', (t) => {
    clearEnv();
    setEnv('DB_HOST', 'mydb.rds.amazonaws.com');
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    guardAllowed(t, result); // not blocked, but warns
    assert.ok(result.warnings.length > 0, 'Should have production DB host warnings');
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 11: assertDbWriteAllowed throws on block
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 11a: assertDbWriteAllowed throws when blocked', (t) => {
    clearEnv();
    const { assertDbWriteAllowed } = loadGuard();

    assert.throws(() => {
        assertDbWriteAllowed({
            script: 'test.js',
            tables: ['raw_match_data'],
            operations: ['INSERT'],
        });
    }, /DRY_RUN/);
});

test('Scenario 11b: assertDbWriteAllowed does NOT throw when all gates pass', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    setEnv('DRY_RUN', 'false');
    const { assertDbWriteAllowed } = loadGuard();

    assert.doesNotThrow(() => {
        assertDbWriteAllowed({
            script: 'test.js',
            tables: ['raw_match_data'],
            operations: ['INSERT'],
        });
    });
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 12: isDryRun helper
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 12a: isDryRun returns true when DRY_RUN not set', (t) => {
    clearEnv();
    const { isDryRun } = loadGuard();
    assert.equal(isDryRun(), true);
});

test('Scenario 12b: isDryRun returns true when DRY_RUN=true', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'true');
    const { isDryRun } = loadGuard();
    assert.equal(isDryRun(), true);
});

test('Scenario 12c: isDryRun returns true when DRY_RUN=yes', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'yes');
    const { isDryRun } = loadGuard();
    assert.equal(isDryRun(), true);
});

test('Scenario 12d: isDryRun returns false when DRY_RUN=false', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'false');
    const { isDryRun } = loadGuard();
    assert.equal(isDryRun(), false);
});

test('Scenario 12e: isDryRun returns false when DRY_RUN=no', (t) => {
    clearEnv();
    setEnv('DRY_RUN', 'no');
    const { isDryRun } = loadGuard();
    assert.equal(isDryRun(), false);
});

// ═══════════════════════════════════════════════════════════════════════════════
// Scenario 13: Multiple tables
// ═══════════════════════════════════════════════════════════════════════════════

test('Scenario 13: blocks when one of multiple table gates is missing', (t) => {
    clearEnv();
    setEnv('ALLOW_DB_WRITE', 'yes');
    setEnv('FINAL_DB_WRITE_CONFIRMATION', 'yes');
    setEnv('ALLOW_RAW_MATCH_DATA_WRITE', 'yes');
    // Missing ALLOW_MATCHES_WRITE
    setEnv('DRY_RUN', 'false');
    const { requireDbWriteGuards } = loadGuard();

    const result = requireDbWriteGuards({
        script: 'test.js',
        tables: ['raw_match_data', 'matches'],
        operations: ['INSERT'],
    });

    guardBlocked(t, result);
    assert.ok(result.missingGates.includes('ALLOW_MATCHES_WRITE'));
});
