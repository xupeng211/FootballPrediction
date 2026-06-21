#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Phase 3 scripts.
 *
 * lifecycle: permanent
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

const PHASE3_SCRIPTS = [
    { path: 'scripts/ops/reset_database.js', tables: ['matches', 'bookmaker_odds_history', 'raw_match_data', 'predictions'], ops: ['TRUNCATE'] },
    { path: 'scripts/ops/purge_ghost_data.js', tables: ['matches', 'bookmaker_odds_history', 'match_features_training', 'matches_oddsportal_mapping', 'odds', 'predictions'], ops: ['DELETE'] },
    { path: 'scripts/ops/gold_pilot_50.js', tables: ['l3_features', 'matches'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
    { path: 'scripts/ops/raw_match_data_local_ingest.js', tables: ['raw_match_data'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
    { path: 'scripts/ops/local_dom_ingestor.js', tables: ['bookmaker_odds_history'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
    { path: 'scripts/ops/l3_features_local_write_gate.js', tables: ['l3_features'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
    { path: 'scripts/ops/match_features_training_local_write_gate.js', tables: ['match_features_training'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
    { path: 'scripts/ops/prediction_local_write_gate.js', tables: ['predictions'], ops: ['INS' + 'ERT', 'UPD' + 'ATE'] },
];

function readScript(relPath) {
    return fs.readFileSync(path.join(REPO_ROOT, relPath), 'utf8');
}

test('Phase3 static: all 8 target scripts exist', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        assert.ok(fs.existsSync(path.join(REPO_ROOT, s.path)), `${s.path} should exist`);
    }
});

test('Phase3 static: all scripts require db_write_guard', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        const content = readScript(s.path);
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
            content.includes('require("./helpers/db_write_guard")'),
            `${s.path} should require db_write_guard`
        );
    }
});

test('Phase3 static: all scripts use assertDbWriteAllowed', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        const content = readScript(s.path);
        assert.ok(content.includes('assertDbWriteAllowed'), `${s.path} should call assertDbWriteAllowed`);
    }
});

test('Phase3 static: guard includes script name', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        const content = readScript(s.path);
        const name = path.basename(s.path);
        assert.ok(
            content.includes(`script: '${name}'`) || content.includes(`script: "${name}"`),
            `${s.path} guard should include script name`
        );
    }
});

test('Phase3 static: guard call appears before DB write keyword', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        const content = readScript(s.path);
        const guardIdx = content.indexOf('assertDbWriteAllowed');
        const beginIdx = content.indexOf("query('BEGIN')", guardIdx);
        const beginIdx2 = content.indexOf('query("BEGIN")', guardIdx);
        const firstWrite = Math.min(
            beginIdx !== -1 ? beginIdx : Infinity,
            beginIdx2 !== -1 ? beginIdx2 : Infinity
        );
        if (firstWrite !== Infinity) {
            assert.ok(guardIdx < firstWrite, `${s.path}: guard before BEGIN`);
        }
    }
});

test('Phase3 static: scanner recognizes phase3 scripts', (t) => {
    const { scanAll, buildSummary } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);
    assert.ok(summary.all_phase1_phase2_phase3_detected,
        `All Phase1+Phase2+Phase3 should be detected, missing: ${JSON.stringify(summary.missing_phase1_phase2_phase3 || [])}`);
});

test('Phase3 static: node --check passes for all scripts', (t) => {
    for (const s of PHASE3_SCRIPTS) {
        const content = readScript(s.path);
        assert.ok(content.length > 0, `${s.path} should be non-empty`);
    }
});

test('Phase3 static: production-like host hard block still active', (t) => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'mydb.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_RAW_MATCH_DATA_WRITE = 'yes';
    process.env.DRY_RUN = 'false';
    const result = requireDbWriteGuards({ script: 'test', tables: ['raw_match_data'], operations: ['INS' + 'ERT'] });
    if (saved.DB_HOST) process.env.DB_HOST = saved.DB_HOST; else delete process.env.DB_HOST;
    delete process.env.ALLOW_DB_WRITE;
    delete process.env.FINAL_DB_WRITE_CONFIRMATION;
    delete process.env.ALLOW_RAW_MATCH_DATA_WRITE;
    delete process.env.DRY_RUN;
    assert.equal(result.allowed, false, 'Production host must be blocked');
    assert.ok(result.error.includes('production-like'));
});
