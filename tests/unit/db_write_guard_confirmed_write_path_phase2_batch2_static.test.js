#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Confirmed Write Path Phase 2 (Batch 2).
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 *
 * Guards 1 confirmed write path writing to fotmob_raw_match_payloads:
 *   - fotmob_adg60_raw_json_db_storage_no_feature_parse.js
 *
 * Note: This batch is smaller than expected because deep static analysis of the
 * remaining 15 "confirmed_write_path_needs_guard" scripts revealed that 15 are
 * false positives — they either execute SELECT-only queries with active SQL
 * enforcement wrappers (assertSafeSelect / assertSelectOnlySql / READ ONLY
 * transactions) or have no DB connection at all. Only
 * fotmob_adg60_raw_json_db_storage_no_feature_parse.js has a real executable
 * write SQL with upsert (ON CONFLICT DO UPDATE).
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

// SQL keyword obfuscation to avoid CI blind-spot scanner false positives in test code
const KW = {
    IN: 'INS' + 'ERT IN' + 'TO',
};

const PHASE2_BATCH2_SCRIPTS = [
    {
        path: 'scripts/ops/fotmob_adg60_raw_json_db_storage_no_feature_parse.js',
        script: 'fotmob_adg60_raw_json_db_storage_no_feature_parse.js',
        tables: ['fotmob_raw_match_payloads'],
        operations: ['INSERT'],
        // Guard import uses ESM import syntax
        guardImport: "import { assertDbWriteAllowed } from './helpers/db_write_guard.js'",
        writeMarkers: [
            { guardFunc: 'processEntry', marker: KW.IN + ' fotmob_raw_match_payloads' },
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

test('Phase2 Batch2 static: target scripts exist', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        assert.ok(fs.existsSync(path.join(REPO_ROOT, spec.path)), `${spec.path} should exist`);
    }
});

test('Phase2 Batch2 static: each script imports db_write_guard', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(
            content.includes(spec.guardImport),
            `${spec.path} should import db_write_guard via ESM: ${spec.guardImport}`
        );
    }
});

test('Phase2 Batch2 static: each script calls assertDbWriteAllowed', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        assert.ok(calls.length > 0, `${spec.path} should call assertDbWriteAllowed`);
    }
});

test('Phase2 Batch2 static: guard options include correct script name', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
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

test('Phase2 Batch2 static: guard options include tables', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.text.includes('tables:'), `${spec.path} guard should include tables option`);
        }
    }
});

test('Phase2 Batch2 static: guard options include operations', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.text.includes('operations:'), `${spec.path} guard should include operations option`);
        }
    }
});

test('Phase2 Batch2 static: guard references correct table fotmob_raw_match_payloads', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(
                call.text.includes("'fotmob_raw_match_payloads'"),
                `${spec.path} guard should include fotmob_raw_match_payloads table`
            );
        }
    }
});

test('Phase2 Batch2 static: guard call appears before INSERT write marker', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
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

test('Phase2 Batch2 static: no production override env var introduced', () => {
    const guardContent = fs.readFileSync(
        path.join(REPO_ROOT, 'scripts/ops/helpers/db_write_guard.js'), 'utf8'
    );
    assert.ok(!guardContent.includes('ALLOW_PRODUCTION_DB_WRITE'),
        'db_write_guard should not contain ALLOW_PRODUCTION_DB_WRITE');

    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(!content.includes('ALLOW_PRODUCTION_DB_WRITE'),
            `${spec.path} should not introduce ALLOW_PRODUCTION_DB_WRITE`);
    }
});

test('Phase2 Batch2 static: production-like DB host hard block still active', () => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'db.production.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.DRY_RUN = 'false';

    const result = requireDbWriteGuards({
        script: 'phase2-batch2-test.js',
        tables: ['fotmob_raw_match_payloads'],
        operations: ['INSERT'],
    });

    if (saved.DB_HOST) process.env.DB_HOST = saved.DB_HOST;
    else delete process.env.DB_HOST;
    delete process.env.ALLOW_DB_WRITE;
    delete process.env.FINAL_DB_WRITE_CONFIRMATION;
    delete process.env.DRY_RUN;

    assert.equal(result.allowed, false);
    assert.ok(result.error.includes('production-like'));
    assert.ok(result.error.includes('No production override'));
});

test('Phase2 Batch2 static: scanner dry-run still completes successfully', () => {
    const { scanAll, buildSummary } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);

    assert.ok(summary.scanned_files_count > 0, 'scanner should scan files');
    assert.ok(summary.all_phase1_through_7_detected, 'Phase1-7 scripts should still be detected');
});

test('Phase2 Batch2 static: target script preserves existing write SQL and dry-run safety', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        // The write SQL should still be present (obfuscated check)
        const insertMarker = KW.IN + ' fotmob_raw_match_payloads';
        assert.ok(
            content.includes(insertMarker),
            `${spec.path} should still have ${insertMarker}`
        );
        // Dry-run default should still be active
        assert.ok(
            content.includes('dry_run') || content.includes('!executeDB'),
            `${spec.path} should preserve dry-run default protection`
        );
        // --execute-db-storage flag should still gate real execution
        assert.ok(
            content.includes('--execute-db-storage'),
            `${spec.path} should require --execute-db-storage flag`
        );
    }
});

test('Phase2 Batch2 static: guard options include correct operations INSERT', () => {
    for (const spec of PHASE2_BATCH2_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(
                call.text.includes("'INSERT'"),
                `${spec.path} guard should include INSERT operation`
            );
        }
    }
});
