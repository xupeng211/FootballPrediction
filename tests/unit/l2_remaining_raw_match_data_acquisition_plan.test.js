'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_remaining_raw_match_data_acquisition_plan.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');

const SEEDED_MATCHES = Object.freeze([
    {
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        home_team: 'Angers',
        away_team: 'Strasbourg',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        home_team: 'Auxerre',
        away_team: 'Nice',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830748',
        external_id: '4830748',
        home_team: 'Le Havre',
        away_team: 'Marseille',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830750',
        external_id: '4830750',
        home_team: 'Metz',
        away_team: 'Lorient',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830751',
        external_id: '4830751',
        home_team: 'Monaco',
        away_team: 'Lille',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830752',
        external_id: '4830752',
        home_team: 'Paris Saint-Germain',
        away_team: 'Brest',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830753',
        external_id: '4830753',
        home_team: 'Rennes',
        away_team: 'Paris FC',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
    {
        match_id: '53_20252026_4830754',
        external_id: '4830754',
        home_team: 'Toulouse',
        away_team: 'Lyon',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
    },
]);

const RAW_COVERAGE = Object.freeze([
    {
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        home_team: 'Angers',
        away_team: 'Strasbourg',
        match_date: '2026-05-10 19:00:00+00',
        status: 'finished',
        raw_id: 3,
        data_version: 'fotmob_html_hyd_v1',
        data_hash: 'd40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6',
        collected_at: '2026-05-14 06:30:34.233+00',
        raw_status: 'has_raw',
    },
    ...SEEDED_MATCHES.slice(1).map(match => ({
        ...match,
        raw_id: null,
        data_version: null,
        data_hash: null,
        collected_at: null,
        raw_status: 'missing_raw',
    })),
]);

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        leagueId: '53',
        season: '2025/2026',
        date: '2026-05-10',
        expectedSeededCount: 8,
        expectedExistingRawCount: 1,
        expectedMissingRawCount: 7,
        allowNetwork: false,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowTraining: false,
        allowPrediction: false,
        networkAuthorization: false,
        livePreviewAuthorization: false,
        commit: false,
        execute: false,
        seededMatchesJson: JSON.stringify(SEEDED_MATCHES),
        rawCoverageJson: JSON.stringify(RAW_COVERAGE),
        ...overrides,
    };
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    return [
        `--source=${args.source}`,
        `--league-id=${args.leagueId}`,
        `--season=${args.season}`,
        `--date=${args.date}`,
        `--expected-seeded-count=${args.expectedSeededCount}`,
        `--expected-existing-raw-count=${args.expectedExistingRawCount}`,
        `--expected-missing-raw-count=${args.expectedMissingRawCount}`,
        `--allow-network=${args.allowNetwork ? 'yes' : 'no'}`,
        `--allow-db-write=${args.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${args.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-matches-write=${args.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${args.livePreviewAuthorization ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
        `--seeded-matches-json=${args.seededMatchesJson}`,
        `--raw-coverage-json=${args.rawCoverageJson}`,
    ];
}

async function runCli(gate, argv) {
    let stdout = '';
    const status = await gate.runCli(argv, {
        stdout: text => {
            stdout += text;
        },
    });
    return {
        status,
        stdout,
        payload: stdout.trim().startsWith('{') ? JSON.parse(stdout) : null,
    };
}

function installExecutionGuards(t) {
    const originalFetch = global.fetch;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by l2_remaining_raw_match_data_acquisition_plan`);
    };

    global.fetch = fail('global.fetch');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    http.request = fail('http.request');
    https.request = fail('https.request');

    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'pg',
            'playwright',
            'playwright-core',
            'puppeteer',
            'child_process',
            'node:child_process',
            'http',
            'node:http',
            'https',
            'node:https',
        ]);
        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        global.fetch = originalFetch;
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        fs.createWriteStream = originalCreateWriteStream;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        Module._load = originalLoad;
    });
}

function assertInvalid(overrides, pattern) {
    const gate = loadModuleFresh();
    const validation = gate.validatePlanningInput(validArgs(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

test('valid planning input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePlanningInput(validArgs());
    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /unsupported source/));
test('league-id missing fails', () => assertInvalid({ leagueId: '' }, /missing league-id/));
test('league-id not 53 fails', () => assertInvalid({ leagueId: '1' }, /league-id must be 53/));
test('season missing fails', () => assertInvalid({ season: '' }, /missing season/));
test('season not 2025/2026 fails', () => assertInvalid({ season: '2024/2025' }, /season must be 2025\/2026/));
test('date missing fails', () => assertInvalid({ date: '' }, /missing date/));
test('date not 2026-05-10 fails', () => assertInvalid({ date: '2026-05-11' }, /date must be 2026-05-10/));
test('expected-seeded-count not 8 fails', () =>
    assertInvalid({ expectedSeededCount: 7 }, /expected-seeded-count must be 8/));
test('expected-existing-raw-count not 1 fails', () =>
    assertInvalid({ expectedExistingRawCount: 0 }, /expected-existing-raw-count must be 1/));
test('expected-missing-raw-count not 7 fails', () =>
    assertInvalid({ expectedMissingRawCount: 6 }, /expected-missing-raw-count must be 7/));
test('allow-network=yes blocked', () => assertInvalid({ allowNetwork: true }, /allow-network=yes is blocked/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('live-preview-authorization=yes blocked', () =>
    assertInvalid({ livePreviewAuthorization: true }, /live-preview-authorization=yes is blocked/));
test('network-authorization=yes blocked', () =>
    assertInvalid({ networkAuthorization: true }, /network-authorization=yes is blocked/));

test('parseArgs and normalizeBooleanFlag handle unknown args and booleans', () => {
    const gate = loadModuleFresh();
    const args = gate.parseArgs(['orphan', '--source', 'fotmob', '--allow-network', 'no', '--mystery']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.allowNetwork, false);
    assert.deepEqual(args.unknown, ['orphan', 'mystery']);
    assert.equal(gate.normalizeBooleanFlag('YES'), true);
    assert.equal(gate.normalizeBooleanFlag('off'), false);
    assert.equal(gate.normalizeBooleanFlag('maybe', false), false);
});

test('remaining_targets count = 7', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.equal(plan.ok, true);
    assert.equal(plan.remaining_targets.length, 7);
});

test('already_ingested_targets count = 1', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.equal(plan.already_ingested_targets.length, 1);
});

test('4830746 is already ingested', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.deepEqual(plan.already_ingested_targets[0], {
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        home_team: 'Angers',
        away_team: 'Strasbourg',
        raw_status: 'has_raw',
    });
});

test('4830747/4830748/4830750/4830751/4830752/4830753/4830754 are remaining', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.deepEqual(
        plan.remaining_targets.map(row => row.match_id),
        [
            '53_20252026_4830747',
            '53_20252026_4830748',
            '53_20252026_4830750',
            '53_20252026_4830751',
            '53_20252026_4830752',
            '53_20252026_4830753',
            '53_20252026_4830754',
        ]
    );
});

test('strategy concurrency=1', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildRecommendedAcquisitionStrategy(7).concurrency, 1);
});

test('strategy retry=0', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildRecommendedAcquisitionStrategy(7).retry, 0);
});

test('strategy browser=false/proxy=false', () => {
    const gate = loadModuleFresh();
    const strategy = gate.buildRecommendedAcquisitionStrategy(7);
    assert.equal(strategy.browser, false);
    assert.equal(strategy.proxy, false);
});

test('strategy raw_match_data_only=true', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildRecommendedAcquisitionStrategy(7).raw_match_data_only, true);
});

test('parser_deferred_until_training_design=true', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.equal(plan.parser_deferred_until_training_design, true);
});

test('protected tables policy protects matches/features/predictions', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(gate.buildProtectedTablesPolicy(), {
        matches: 'read_only',
        bookmaker_odds_history: 'unchanged',
        l3_features: 'unchanged',
        match_features_training: 'unchanged',
        predictions: 'unchanged',
    });
});

test('output would_write_db=false', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.equal(plan.would_write_db, false);
});

test('output would_train=false', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRemainingRawMatchDataAcquisitionPlan(validArgs());
    assert.equal(plan.would_train, false);
});

test('Makefile plan target succeeds', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-remaining-raw-match-data-acquisition-plan:/m);
    assert.match(makefile, /scripts\/ops\/l2_remaining_raw_match_data_acquisition_plan\.js/);
});

test('buildSeededMatchCoverage merges seeded matches and raw coverage', () => {
    const gate = loadModuleFresh();
    const coverage = gate.buildSeededMatchCoverage(JSON.stringify(SEEDED_MATCHES), JSON.stringify(RAW_COVERAGE));
    assert.equal(coverage.length, 8);
    assert.equal(coverage[0].data_hash, 'd40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6');
    assert.equal(coverage[1].raw_status, 'missing_raw');
});

test('coverage mismatch fails closed', () => {
    const gate = loadModuleFresh();
    const mismatchedCoverage = RAW_COVERAGE.map((row, index) =>
        index === 1
            ? {
                  ...row,
                  raw_id: 10,
                  raw_status: 'has_raw',
              }
            : row
    );
    const result = gate.buildRemainingRawMatchDataAcquisitionPlan(
        validArgs({
            rawCoverageJson: JSON.stringify(mismatchedCoverage),
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /COVERAGE_VALIDATION_FAILED/);
});

test('missing coverage input fails closed', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionPlan(
        validArgs({
            seededMatchesJson: '',
            rawCoverageJson: '',
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /COVERAGE_INPUT_REQUIRED/);
});

test('runCli succeeds without network access', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs());
    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.missing_raw_match_data_count, 7);
});

test('runCli returns non-zero for blocked DB write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowDbWrite: true }));
    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.match(result.payload.controlled_error, /allow-db-write=yes is blocked/);
});

test('runCli help returns usage without executing plan', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--help']);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 5\.17L2 is planning-only/);
    assert.equal(result.payload, null);
});

test('source audit: no network access', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]node:http['"]\)|require\(['"]http['"]\)/);
    assert.doesNotMatch(source, /require\(['"]node:https['"]\)|require\(['"]https['"]\)/);
    assert.doesNotMatch(source, /\bfetch\s*\(/);
});

test('source audit: no DB write', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]pg['"]\)/);
    assert.doesNotMatch(source, /\.query\s*\(/);
    assert.doesNotMatch(source, /\bINSERT\s+INTO\b/i);
    assert.doesNotMatch(source, /\bUPDATE\s+\w+\s+SET\b/i);
    assert.doesNotMatch(source, /\bDELETE\s+FROM\b/i);
    assert.doesNotMatch(source, /\bTRUNCATE\s+TABLE\b/i);
    assert.doesNotMatch(source, /\bALTER\s+TABLE\b/i);
    assert.doesNotMatch(source, /\bDROP\s+TABLE\b/i);
});

test('source audit: no fs write / mkdir', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('source audit: no child_process spawn', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});

test('source audit: no ProductionHarvester / raw ingest commit', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});
