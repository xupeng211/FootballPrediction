#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Confirmed Write Path Phase 2 (Batch 1).
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 *
 * Guards 3 controlled-write scripts writing to raw_match_data:
 *   - pageprops_v2_single_target_controlled_write.js
 *   - remaining_seeded_pageprops_v2_controlled_write.js
 *   - single_league_pageprops_v2_controlled_write_execute.js
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

const PHASE2_BATCH1_SCRIPTS = [
    {
        path: 'scripts/ops/pageprops_v2_single_target_controlled_write.js',
        script: 'pageprops_v2_single_target_controlled_write.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
        writeMarkers: [
            { guardFunc: 'executeTransaction', marker: "client.query('BEGIN')" },
        ],
    },
    {
        path: 'scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js',
        script: 'remaining_seeded_pageprops_v2_controlled_write.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
        writeMarkers: [
            { guardFunc: 'executeTransaction', marker: "client.query('BEGIN')" },
        ],
    },
    {
        path: 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js',
        script: 'single_league_pageprops_v2_controlled_write_execute.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
        writeMarkers: [
            { guardFunc: 'executeTransaction', marker: "queryControlledWrite(client, 'BEGIN')" },
        ],
    },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function readScript(relPath) {
    return fs.readFileSync(path.join(REPO_ROOT, relPath), 'utf8');
}

function findAllGuardCalls(content) {
    const calls = [];
    let idx = 0;
    while (true) {
        idx = content.indexOf('assertDbWriteAllowed({', idx);
        if (idx === -1) break;
        const end = content.indexOf('});', idx);
        if (end === -1) break;
        calls.push({ text: content.slice(idx, end + 3), startIdx: idx });
        idx = end + 3;
    }
    return calls;
}

// ── Tests ────────────────────────────────────────────────────────────────────

test('Phase2 Batch1 static: target scripts exist', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        assert.ok(fs.existsSync(path.join(REPO_ROOT, spec.path)), `${spec.path} should exist`);
    }
});

test('Phase2 Batch1 static: each script requires db_write_guard', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
                content.includes('require("./helpers/db_write_guard")'),
            `${spec.path} should require db_write_guard`
        );
    }
});

test('Phase2 Batch1 static: each script calls assertDbWriteAllowed', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        assert.ok(calls.length > 0, `${spec.path} should call assertDbWriteAllowed`);
    }
});

test('Phase2 Batch1 static: guard options include correct script name', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(
                call.text.includes(`script: '${spec.script}'`),
                `${spec.path} guard should reference '${spec.script}': got ${call.text.slice(0, 140)}`
            );
        }
    }
});

test('Phase2 Batch1 static: guard options include tables', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.text.includes('tables:'), `${spec.path} guard should include tables option`);
        }
    }
});

test('Phase2 Batch1 static: guard options include operations', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.text.includes('operations:'), `${spec.path} guard should include operations option`);
        }
    }
});

test('Phase2 Batch1 static: guard references correct table raw_match_data', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(
                call.text.includes("'raw_match_data'"),
                `${spec.path} guard should include raw_match_data table`
            );
        }
    }
});

test('Phase2 Batch1 static: guard call appears before write marker', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);

        for (let i = 0; i < spec.writeMarkers.length; i++) {
            const call = calls[i];
            const marker = spec.writeMarkers[i].marker;
            const markerIdx = content.indexOf(marker, call.startIdx);

            assert.notEqual(markerIdx, -1,
                `${spec.path}: write marker "${marker}" should exist after guard`);
            assert.ok(call.startIdx < markerIdx,
                `${spec.path}: guard should appear before "${marker}"`);
        }
    }
});

test('Phase2 Batch1 static: no production override env var introduced', () => {
    const guardContent = fs.readFileSync(
        path.join(REPO_ROOT, 'scripts/ops/helpers/db_write_guard.js'), 'utf8'
    );
    assert.ok(!guardContent.includes('ALLOW_PRODUCTION_DB_WRITE'),
        'db_write_guard should not contain ALLOW_PRODUCTION_DB_WRITE');

    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(!content.includes('ALLOW_PRODUCTION_DB_WRITE'),
            `${spec.path} should not introduce ALLOW_PRODUCTION_DB_WRITE`);
    }
});

test('Phase2 Batch1 static: production-like DB host hard block still active', () => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'db.production.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_RAW_MATCH_DATA_WRITE = 'yes';
    process.env.DRY_RUN = 'false';

    const result = requireDbWriteGuards({
        script: 'phase2-batch1-test.js',
        tables: ['raw_match_data'],
        operations: ['INSERT'],
    });

    if (saved.DB_HOST) process.env.DB_HOST = saved.DB_HOST;
    else delete process.env.DB_HOST;
    delete process.env.ALLOW_DB_WRITE;
    delete process.env.FINAL_DB_WRITE_CONFIRMATION;
    delete process.env.ALLOW_RAW_MATCH_DATA_WRITE;
    delete process.env.DRY_RUN;

    assert.equal(result.allowed, false);
    assert.ok(result.error.includes('production-like'));
    assert.ok(result.error.includes('No production override'));
});

test('Phase2 Batch1 static: scanner dry-run still completes successfully', () => {
    const { scanAll, buildSummary } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);

    assert.ok(summary.scanned_files_count > 0, 'scanner should scan files');
    assert.ok(summary.all_phase1_through_7_detected, 'Phase1-7 scripts should still be detected');
});

test('Phase2 Batch1 static: target scripts preserve existing write SQL for raw_match_data', () => {
    for (const spec of PHASE2_BATCH1_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(
            content.includes('raw_match_data'),
            `${spec.path} should still reference raw_match_data table`
        );
    }
});
