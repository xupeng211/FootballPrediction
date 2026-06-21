#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Phase 5 scripts.
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

const PHASE5_SCRIPTS = [
    {
        path: 'scripts/ops/synthetic_l3_preflight.js',
        script: 'synthetic_l3_preflight.js',
        tables: ['l3_features'],
        operations: ['INSERT'],
        writeMarker: 'console.error(\'BLOCKED: synthetic L3 commit is not wired',
    },
    {
        path: 'scripts/ops/synthetic_prediction_preflight.js',
        script: 'synthetic_prediction_preflight.js',
        tables: ['predictions'],
        operations: ['INSERT'],
        writeMarker: 'console.error(\'BLOCKED: synthetic prediction commit is not wired',
    },
    {
        path: 'scripts/ops/synthetic_training_feature_preflight.js',
        script: 'synthetic_training_feature_preflight.js',
        tables: ['match_features_training'],
        operations: ['INSERT'],
        writeMarker: 'console.error(\'BLOCKED: synthetic training feature commit is not wired',
    },
    {
        path: 'scripts/ops/finished_csv_local_dry_run.js',
        script: 'finished_csv_local_dry_run.js',
        tables: ['matches'],
        operations: ['INSERT'],
        writeMarker: 'console.error(JSON.stringify(buildBlockedCommitPayload',
    },
    {
        path: 'scripts/ops/real_finished_csv_staging_dry_run.js',
        script: 'real_finished_csv_staging_dry_run.js',
        tables: ['matches', 'bookmaker_odds_history'],
        operations: ['INSERT'],
        writeMarker: 'console.error(JSON.stringify(buildBlockedCommitPayload',
    },
    {
        path: 'scripts/ops/finished_match_backfill_preflight.js',
        script: 'finished_match_backfill_preflight.js',
        tables: ['raw_match_data', 'matches', 'l3_features', 'match_features_training', 'predictions'],
        operations: ['INSERT', 'UPDATE'],
        writeMarker: 'console.error(\'BLOCKED: finished match backfill commit is not wired',
    },
    {
        path: 'scripts/ops/raw_fixture_adapter_dry_run.js',
        script: 'raw_fixture_adapter_dry_run.js',
        tables: ['raw_match_data', 'matches'],
        operations: ['INSERT'],
        writeMarker: 'console.error(\'BLOCKED: raw fixture adapter commit is not wired',
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

test('Phase5 static: all 7 target scripts exist', () => {
    for (const script of PHASE5_SCRIPTS) {
        assert.ok(fs.existsSync(path.join(REPO_ROOT, script.path)), `${script.path} should exist`);
    }
});

test('Phase5 static: all scripts require db_write_guard', () => {
    for (const script of PHASE5_SCRIPTS) {
        const content = readScript(script.path);
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
                content.includes('require("./helpers/db_write_guard")') ||
                content.includes("from './helpers/db_write_guard.js'"),
            `${script.path} should import/require db_write_guard`
        );
    }
});

test('Phase5 static: all scripts call assertDbWriteAllowed', () => {
    for (const script of PHASE5_SCRIPTS) {
        const content = readScript(script.path);
        assert.ok(content.includes('assertDbWriteAllowed'), `${script.path} should call assertDbWriteAllowed`);
    }
});

test('Phase5 static: guard options include script, tables, and operations', () => {
    for (const script of PHASE5_SCRIPTS) {
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

test('Phase5 static: guard call appears in commit handler before blocked error', () => {
    for (const script of PHASE5_SCRIPTS) {
        const content = readScript(script.path);
        const guardIdx = content.indexOf('assertDbWriteAllowed({');
        const markerIdx = content.indexOf(script.writeMarker, guardIdx);
        assert.notEqual(markerIdx, -1, `${script.path} should contain write marker after guard`);
        assert.ok(guardIdx < markerIdx, `${script.path}: guard should appear before write marker`);
    }
});

test('Phase5 static: scanner recognizes Phase1+Phase2+Phase3+Phase4+Phase5 guarded scripts', () => {
    const {
        scanAll,
        buildSummary,
        PHASE5_GUARDED,
    } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);

    assert.equal(PHASE5_GUARDED.length, PHASE5_SCRIPTS.length);
    assert.equal(summary.phase1_phase2_phase3_phase4_phase5_guarded_expected, 37);
    assert.equal(summary.phase1_phase2_phase3_phase4_phase5_guarded_detected_count, 37);
    assert.equal(summary.all_phase1_phase2_phase3_phase4_phase5_detected, true);
    assert.deepEqual(summary.missing_phase1_phase2_phase3_phase4_phase5, []);
});

test('Phase5 static: changed-files advisory remains non-failing for phase5 targets', () => {
    const { scanAdvisory } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const result = scanAdvisory(PHASE5_SCRIPTS.map(script => script.path));

    assert.equal(result.mode, 'changed_files_enforcement');
    assert.equal(result.should_fail, false);
    assert.equal(result.violation_count, 0);
    for (const script of PHASE5_SCRIPTS) {
        assert.ok(result.guarded_changed_js_ops.includes(script.path), `${script.path} should be guarded`);
    }
});

test('Phase5 static: production-like DB host hard block still active', () => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'db.production.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_MATCHES_WRITE = 'yes';
    process.env.DRY_RUN = 'false';

    const result = requireDbWriteGuards({
        script: 'phase5-test.js',
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
