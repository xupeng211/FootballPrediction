#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Phase 4 scripts.
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

const PHASE4_SCRIPTS = [
    {
        path: 'scripts/ops/l3_stitch_worker.js',
        script: 'l3_stitch_worker.js',
        tables: ['l3_features'],
        operations: ['INSERT', 'UPDATE'],
        writeMarker: 'const pool = new Pool',
    },
    {
        path: 'scripts/ops/raw_match_data_versioned_schema_migration_execute.js',
        script: 'raw_match_data_versioned_schema_migration_execute.js',
        tables: ['raw_match_data'],
        operations: ['ALTER', 'DROP'],
        writeMarker: 'runMigrationExecution(validation.value',
    },
    {
        path: 'scripts/ops/score_backfill_dry_run.js',
        script: 'score_backfill_dry_run.js',
        tables: ['matches'],
        operations: ['UPDATE'],
        writeMarker: "require('./score_backfill_write')",
    },
    {
        path: 'scripts/ops/training_eligibility_after_score_dry_run.js',
        script: 'training_eligibility_after_score_dry_run.js',
        tables: ['matches'],
        operations: ['UPDATE'],
        writeMarker: 'execFileSync(',
    },
    {
        path: 'scripts/ops/l2_guarded_reconciliation_write.js',
        script: 'l2_guarded_reconciliation_write.js',
        tables: ['matches'],
        operations: ['UPDATE'],
        writeMarker: 'const connection = await openClient',
    },
    {
        path: 'scripts/ops/controlled_matches_identity_seed_execute.js',
        script: 'controlled_matches_identity_seed_execute.js',
        tables: ['matches'],
        operations: ['INSERT'],
        writeMarker: 'const input = validation.value',
    },
];

function readScript(relPath) {
    return fs.readFileSync(path.join(REPO_ROOT, relPath), 'utf8');
}

function guardCallWindow(content) {
    const idx = content.indexOf('assertDbWriteAllowed({');
    assert.notEqual(idx, -1, 'guard call should exist');
    const end = content.indexOf('});', idx);
    assert.notEqual(end, -1, 'guard call should close');
    return content.slice(idx, end + 3);
}

test('Phase4 static: all 6 target scripts exist', () => {
    for (const script of PHASE4_SCRIPTS) {
        assert.ok(fs.existsSync(path.join(REPO_ROOT, script.path)), `${script.path} should exist`);
    }
});

test('Phase4 static: all scripts import or require db_write_guard', () => {
    for (const script of PHASE4_SCRIPTS) {
        const content = readScript(script.path);
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
                content.includes('require("./helpers/db_write_guard")') ||
                content.includes("from './helpers/db_write_guard.js'"),
            `${script.path} should import/require db_write_guard`
        );
    }
});

test('Phase4 static: all scripts call assertDbWriteAllowed', () => {
    for (const script of PHASE4_SCRIPTS) {
        const content = readScript(script.path);
        assert.ok(content.includes('assertDbWriteAllowed'), `${script.path} should call assertDbWriteAllowed`);
    }
});

test('Phase4 static: guard options include script, tables, and operations', () => {
    for (const script of PHASE4_SCRIPTS) {
        const window = guardCallWindow(readScript(script.path));
        assert.ok(window.includes(`script: '${script.script}'`), `${script.path} should include script option`);
        assert.ok(window.includes('tables:'), `${script.path} should include tables option`);
        assert.ok(window.includes('operations:'), `${script.path} should include operations option`);
        for (const table of script.tables) {
            assert.ok(window.includes(`'${table}'`), `${script.path} guard should include table ${table}`);
        }
        for (const op of script.operations) {
            assert.ok(window.includes(`'${op}'`), `${script.path} guard should include operation ${op}`);
        }
    }
});

test('Phase4 static: guard call appears before the write-capable path marker', () => {
    for (const script of PHASE4_SCRIPTS) {
        const content = readScript(script.path);
        const guardIdx = content.indexOf('assertDbWriteAllowed({');
        const markerIdx = content.indexOf(script.writeMarker, guardIdx);
        assert.notEqual(markerIdx, -1, `${script.path} should contain write marker after guard`);
        assert.ok(guardIdx < markerIdx, `${script.path}: guard should appear before write marker`);
    }
});

test('Phase4 static: scanner recognizes Phase1+Phase2+Phase3+Phase4 guarded scripts', () => {
    const {
        scanAll,
        buildSummary,
        PHASE4_GUARDED,
    } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);

    assert.equal(PHASE4_GUARDED.length, PHASE4_SCRIPTS.length);
    assert.equal(summary.phase1_phase2_phase3_phase4_guarded_expected, 30);
    assert.equal(summary.phase1_phase2_phase3_phase4_guarded_detected_count, 30);
    assert.equal(summary.all_phase1_phase2_phase3_phase4_detected, true);
    assert.deepEqual(summary.missing_phase1_phase2_phase3_phase4, []);
});

test('Phase4 static: changed-files advisory remains non-failing for phase4 targets', () => {
    const { scanAdvisory } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const result = scanAdvisory(PHASE4_SCRIPTS.map(script => script.path));

    assert.equal(result.mode, 'changed_files_enforcement');
    assert.equal(result.should_fail, false);
    assert.equal(result.violation_count, 0);
    for (const script of PHASE4_SCRIPTS) {
        assert.ok(result.guarded_changed_js_ops.includes(script.path), `${script.path} should be guarded`);
    }
});

test('Phase4 static: production-like DB host hard block still active', () => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'db.production.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_MATCHES_WRITE = 'yes';
    process.env.DRY_RUN = 'false';

    const result = requireDbWriteGuards({
        script: 'phase4-test.js',
        tables: ['matches'],
        operations: ['INSERT'],
    });

    if (saved.DB_HOST) process.env.DB_HOST = saved.DB_HOST;
    else delete process.env.DB_HOST;
    delete process.env.ALLOW_DB_WRITE;
    delete process.env.FINAL_DB_WRITE_CONFIRMATION;
    delete process.env.ALLOW_MATCHES_WRITE;
    delete process.env.DRY_RUN;

    assert.equal(result.allowed, false);
    assert.ok(result.error.includes('production-like'));
    assert.ok(result.error.includes('No production override'));
});
