#!/usr/bin/env node
/**
 * Static integration tests for DB Write Safety Gate — Confirmed Write Path Phase 1.
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 *
 * Guards two highest-risk browser+DB scripts:
 *   - odds_sniper.js (Playwright + Pool + UPSERT to odds + L3 features)
 *   - fixture_harvester_l1.js (Playwright + Pool + UPSERT to matches)
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

const PHASE1_CONFIRMED_WRITE_SCRIPTS = [
    {
        path: 'scripts/ops/odds_sniper.js',
        script: 'odds_sniper.js',
        tables: ['matches_oddsportal_mapping', 'bookmaker_odds_history', 'l3_features'],
        operations: ['INSERT', 'UPDATE'],
        // There are two guard points: upsertMappingAndOdds and runTargetedStitch
        // The first guard appears before the BEGIN in upsertMappingAndOdds
        writeMarkers: [
            { guardFunc: 'upsertMappingAndOdds', marker: "client.query('BEGIN')" },
            { guardFunc: 'runTargetedStitch', marker: 'UPSERT_L3_SQL' },
        ],
    },
    {
        path: 'scripts/ops/fixture_harvester_l1.js',
        script: 'fixture_harvester_l1.js',
        tables: ['matches'],
        operations: ['INSERT', 'UPDATE'],
        writeMarkers: [
            { guardFunc: 'persistFixtures', marker: "client.query('BEGIN')" },
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
        calls.push(content.slice(idx, end + 3));
        idx = end + 3;
    }
    return calls;
}

// ── Tests ────────────────────────────────────────────────────────────────────

test('Confirmed Write Path Phase1 static: target scripts exist', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        assert.ok(
            fs.existsSync(path.join(REPO_ROOT, script.path)),
            `${script.path} should exist`
        );
    }
});

test('Confirmed Write Path Phase1 static: script requires db_write_guard', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(script.path);
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
                content.includes('require("./helpers/db_write_guard")'),
            `${script.path} should import/require db_write_guard`
        );
    }
});

test('Confirmed Write Path Phase1 static: script calls assertDbWriteAllowed', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(script.path);
        const calls = findAllGuardCalls(content);
        assert.ok(calls.length > 0, `${script.path} should call assertDbWriteAllowed at least once`);
    }
});

test('Confirmed Write Path Phase1 static: guard options include script name', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(script.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(
                call.includes(`script: '${script.script}'`),
                `${script.path} guard should reference correct script name: got ${call.slice(0, 120)}`
            );
        }
    }
});

test('Confirmed Write Path Phase1 static: guard options include tables', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(script.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.includes('tables:'), `${script.path} guard should include tables option`);
        }
    }
});

test('Confirmed Write Path Phase1 static: guard options include operations', () => {
    for (const script of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(script.path);
        const calls = findAllGuardCalls(content);
        for (const call of calls) {
            assert.ok(call.includes('operations:'), `${script.path} guard should include operations option`);
        }
    }
});

test('Confirmed Write Path Phase1 static: odds_sniper guard calls reference correct tables', () => {
    const oddsSniper = PHASE1_CONFIRMED_WRITE_SCRIPTS[0];
    const content = readScript(oddsSniper.path);
    const calls = findAllGuardCalls(content);

    // First guard call (upsertMappingAndOdds) should reference matches_oddsportal_mapping and bookmaker_odds_history
    const firstCall = calls[0];
    assert.ok(
        firstCall.includes("'matches_oddsportal_mapping'"),
        'upsertMappingAndOdds guard should include matches_oddsportal_mapping'
    );
    assert.ok(
        firstCall.includes("'bookmaker_odds_history'"),
        'upsertMappingAndOdds guard should include bookmaker_odds_history'
    );

    // Second guard call (runTargetedStitch) should reference l3_features
    const secondCall = calls[1];
    assert.ok(
        secondCall.includes("'l3_features'"),
        'runTargetedStitch guard should include l3_features'
    );
});

test('Confirmed Write Path Phase1 static: fixture_harvester_l1 guard references matches table', () => {
    const fixtureHarvester = PHASE1_CONFIRMED_WRITE_SCRIPTS[1];
    const content = readScript(fixtureHarvester.path);
    const calls = findAllGuardCalls(content);

    assert.ok(
        calls[0].includes("'matches'"),
        'persistFixtures guard should include matches table'
    );
});

test('Confirmed Write Path Phase1 static: guard call appears before write marker', () => {
    for (const spec of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(spec.path);
        const calls = findAllGuardCalls(content);

        for (let i = 0; i < spec.writeMarkers.length; i++) {
            const guardCall = calls[i];
            const marker = spec.writeMarkers[i].marker;

            const guardIdx = content.indexOf(guardCall);
            const markerIdx = content.indexOf(marker, guardIdx);

            assert.notEqual(
                guardIdx,
                -1,
                `${spec.path}: guard call ${i + 1} should exist`
            );
            assert.notEqual(
                markerIdx,
                -1,
                `${spec.path}: write marker "${marker}" should exist after guard call ${i + 1}`
            );
            assert.ok(
                guardIdx < markerIdx,
                `${spec.path}: guard call ${i + 1} (${spec.writeMarkers[i].guardFunc}) should appear before "${marker}"`
            );
        }
    }
});

test('Confirmed Write Path Phase1 static: odds_sniper preserves existing dryRun check', () => {
    const content = readScript('scripts/ops/odds_sniper.js');
    assert.ok(
        content.includes('options.dryRun'),
        'odds_sniper.js should preserve existing dryRun check'
    );
});

test('Confirmed Write Path Phase1 static: production-like DB host hard block still active', () => {
    delete require.cache[require.resolve('../../scripts/ops/helpers/db_write_guard')];
    const { requireDbWriteGuards } = require('../../scripts/ops/helpers/db_write_guard');
    const saved = { DB_HOST: process.env.DB_HOST };
    process.env.DB_HOST = 'db.production.rds.amazonaws.com';
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_MATCHES_WRITE = 'yes';
    process.env.DRY_RUN = 'false';

    const result = requireDbWriteGuards({
        script: 'phase1-confirmed-write-test.js',
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

test('Confirmed Write Path Phase1 static: no production override env var introduced', () => {
    const guardContent = fs.readFileSync(
        path.join(REPO_ROOT, 'scripts/ops/helpers/db_write_guard.js'),
        'utf8'
    );
    // Verify no ALLOW_PRODUCTION_DB_WRITE was added
    assert.ok(
        !guardContent.includes('ALLOW_PRODUCTION_DB_WRITE'),
        'db_write_guard should not contain ALLOW_PRODUCTION_DB_WRITE'
    );

    // Verify target scripts don't introduce bypass variables
    for (const spec of PHASE1_CONFIRMED_WRITE_SCRIPTS) {
        const content = readScript(spec.path);
        assert.ok(
            !content.includes('ALLOW_PRODUCTION_DB_WRITE'),
            `${spec.path} should not introduce ALLOW_PRODUCTION_DB_WRITE`
        );
        assert.ok(
            !content.includes('ALLOW_PRODUCTION_DB'),
            `${spec.path} should not introduce production bypass`
        );
    }
});

test('Confirmed Write Path Phase1 static: target scripts default to dry-run safe', () => {
    // Verify DRY_RUN defaults to true in the guard (no script overrides this default)
    const { isDryRun } = require('../../scripts/ops/helpers/db_write_guard');
    // Without DRY_RUN env set, isDryRun() should return true
    delete process.env.DRY_RUN;
    assert.equal(isDryRun(), true, 'isDryRun() should default to true');
});

test('Confirmed Write Path Phase1 static: scanner dry-run still completes successfully', () => {
    const { scanAll, buildSummary } = require('../../scripts/ops/db_write_guard_static_enforcement_dry_run');
    const results = scanAll();
    const summary = buildSummary(results);

    // Scanner should still complete without errors
    assert.ok(summary.scanned_files_count > 0, 'scanner should scan files');
    assert.ok(
        summary.all_phase1_through_7_detected,
        'all Phase1-7 scripts should still be detected'
    );
    assert.equal(
        summary.phase1_through_7_guarded_detected_count,
        summary.phase1_through_7_guarded_expected,
        'Phase1-7 guarded count should match expected'
    );
});
