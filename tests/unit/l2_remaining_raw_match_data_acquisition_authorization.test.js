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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_remaining_raw_match_data_acquisition_authorization.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');

const EXPECTED_EXTERNAL_IDS = '4830747,4830748,4830750,4830751,4830752,4830753,4830754';

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
        route: 'html_hydration',
        expectedSeededCount: 8,
        expectedExistingRawCount: 1,
        expectedMissingRawCount: 7,
        remainingExternalIds: EXPECTED_EXTERNAL_IDS,
        userAuthorizedRemainingRawAcquisition: true,
        allowNetworkNextPhase: true,
        allowRawMatchDataWriteFuturePhase: true,
        allowNetworkThisPhase: false,
        allowDbWriteThisPhase: false,
        allowRawMatchDataWriteThisPhase: false,
        allowMatchesWrite: false,
        allowParserFeatures: false,
        allowTraining: false,
        allowPrediction: false,
        finalHumanConfirmation: true,
        networkAuthorization: false,
        livePreviewAuthorization: false,
        commit: false,
        execute: false,
        ...overrides,
    };
}

// eslint-disable-next-line complexity
function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    return [
        `--source=${args.source}`,
        `--league-id=${args.leagueId}`,
        `--season=${args.season}`,
        `--date=${args.date}`,
        `--route=${args.route}`,
        `--expected-seeded-count=${args.expectedSeededCount}`,
        `--expected-existing-raw-count=${args.expectedExistingRawCount}`,
        `--expected-missing-raw-count=${args.expectedMissingRawCount}`,
        `--remaining-external-ids=${args.remainingExternalIds}`,
        `--user-authorized-remaining-raw-acquisition=${args.userAuthorizedRemainingRawAcquisition ? 'yes' : 'no'}`,
        `--allow-network-next-phase=${args.allowNetworkNextPhase ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write-future-phase=${args.allowRawMatchDataWriteFuturePhase ? 'yes' : 'no'}`,
        `--allow-network-this-phase=${args.allowNetworkThisPhase ? 'yes' : 'no'}`,
        `--allow-db-write-this-phase=${args.allowDbWriteThisPhase ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write-this-phase=${args.allowRawMatchDataWriteThisPhase ? 'yes' : 'no'}`,
        `--allow-matches-write=${args.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-parser-features=${args.allowParserFeatures ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--final-human-confirmation=${args.finalHumanConfirmation ? 'yes' : 'no'}`,
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${args.livePreviewAuthorization ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
    ];
}

async function runCli(gate, argv) {
    let stdout = '';
    const status = await gate.runCli(argv, {
        stdout: text => {
            stdout += text;
        },
    });
    return { status, stdout, payload: stdout.trim().startsWith('{') ? JSON.parse(stdout) : null };
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
        throw new Error(`${name} should not be called by authorization script`);
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
        const blocked = new Set([
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
        if (blocked.has(request)) {
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
    const validation = gate.validateAuthorizationInput(validArgs(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

// 1
test('valid authorization input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validateAuthorizationInput(validArgs());
    assert.equal(validation.ok, true);
});

// 2-11 scope validation
test('source missing fails', () => assertInvalid({ source: '' }, /source must be fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('league-id missing fails', () => assertInvalid({ leagueId: '' }, /league-id must be 53/));
test('league-id not 53 fails', () => assertInvalid({ leagueId: '1' }, /league-id must be 53/));
test('season missing fails', () => assertInvalid({ season: '' }, /season must be 2025/));
test('season not 2025/2026 fails', () => assertInvalid({ season: '2024/2025' }, /season must be 2025/));
test('date missing fails', () => assertInvalid({ date: '' }, /date must be 2026-05-10/));
test('date not 2026-05-10 fails', () => assertInvalid({ date: '2026-05-11' }, /date must be 2026-05-10/));
test('route missing fails', () => assertInvalid({ route: '' }, /route must be html_hydration/));
test('route not html_hydration fails', () => assertInvalid({ route: 'api' }, /route must be html_hydration/));

// 12-14 count validation
test('expected-seeded-count not 8 fails', () =>
    assertInvalid({ expectedSeededCount: 7 }, /expected-seeded-count must be 8/));
test('expected-existing-raw-count not 1 fails', () =>
    assertInvalid({ expectedExistingRawCount: 0 }, /expected-existing-raw-count must be 1/));
test('expected-missing-raw-count not 7 fails', () =>
    assertInvalid({ expectedMissingRawCount: 6 }, /expected-missing-raw-count must be 7/));

// 15-19 remaining-external-ids validation
test('remaining-external-ids missing fails', () =>
    assertInvalid({ remainingExternalIds: '' }, /remaining-external-ids is required/));
test('remaining-external-ids wrong count fails', () =>
    assertInvalid({ remainingExternalIds: '4830747,4830748' }, /must have exactly 7 ids/));
test('remaining-external-ids missing 4830754 fails', () =>
    assertInvalid(
        { remainingExternalIds: '4830747,4830748,4830750,4830751,4830752,4830753,9999999' },
        /missing expected remaining external_id: 4830754/
    ));
test('remaining-external-ids includes 4830746 fails', () =>
    assertInvalid(
        { remainingExternalIds: '4830746,4830747,4830748,4830750,4830751,4830752,4830753' },
        /4830746 is already ingested/
    ));
test('remaining-external-ids includes unexpected id fails', () =>
    assertInvalid(
        { remainingExternalIds: '4830747,4830748,4830750,4830751,4830752,4830753,9999999' },
        /unexpected remaining external_id/
    ));

// 20-23 required yes flags
test('user-authorized-remaining-raw-acquisition=no fails', () =>
    assertInvalid(
        { userAuthorizedRemainingRawAcquisition: false },
        /user-authorized-remaining-raw-acquisition=yes is required/
    ));
test('allow-network-next-phase=no fails', () =>
    assertInvalid({ allowNetworkNextPhase: false }, /allow-network-next-phase=yes is required/));
test('allow-raw-match-data-write-future-phase=no fails', () =>
    assertInvalid(
        { allowRawMatchDataWriteFuturePhase: false },
        /allow-raw-match-data-write-future-phase=yes is required/
    ));
test('final-human-confirmation=no fails', () =>
    assertInvalid({ finalHumanConfirmation: false }, /final-human-confirmation=yes is required/));

// 24-30 blocked this phase
test('allow-network-this-phase=yes blocked', () =>
    assertInvalid({ allowNetworkThisPhase: true }, /allow-network-this-phase=yes is blocked/));
test('allow-db-write-this-phase=yes blocked', () =>
    assertInvalid({ allowDbWriteThisPhase: true }, /allow-db-write-this-phase=yes is blocked/));
test('allow-raw-match-data-write-this-phase=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWriteThisPhase: true }, /allow-raw-match-data-write-this-phase=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-parser-features=yes blocked', () =>
    assertInvalid({ allowParserFeatures: true }, /allow-parser-features=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));

// 31-34 additional blocked
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('live-preview-authorization=yes blocked', () =>
    assertInvalid({ livePreviewAuthorization: true }, /live-preview-authorization=yes is blocked/));
test('network-authorization=yes blocked', () =>
    assertInvalid({ networkAuthorization: true }, /network-authorization=yes is blocked/));

// 35-48 output assertions
test('output authorization_only=true', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.authorization_only, true);
});
test('network_allowed_next_phase=true', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.network_allowed_next_phase, true);
});
test('network_allowed_this_phase=false', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.network_allowed_this_phase, false);
});
test('raw_match_data_write_allowed_this_phase=false', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.raw_match_data_write_allowed_this_phase, false);
});
test('authorized_remaining_targets count=7', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.authorized_remaining_targets.length, 7);
});
test('already_ingested_targets count=1', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.already_ingested_targets.length, 1);
});
test('authorized_scope rows_limit=7', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildAuthorizedScope().rows_limit, 7);
});
test('authorized_scope concurrency=1', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildAuthorizedScope().concurrency, 1);
});
test('authorized_scope retry=0', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildAuthorizedScope().retry, 0);
});
test('parser_deferred_until_training_design=true', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.buildAuthorizedScope().parser_deferred_until_training_design, true);
});
test('blocked actions include live_preview/write_db/parser_features/training', () => {
    const gate = loadModuleFresh();
    const blocked = gate.buildBlockedActionsThisPhase();
    assert.ok(blocked.includes('live_preview'));
    assert.ok(blocked.includes('write_db'));
    assert.ok(blocked.includes('parser_features'));
    assert.ok(blocked.includes('training'));
});
test('next_phase_requirements include preflight and would_insert/update/skip', () => {
    const gate = loadModuleFresh();
    const requirements = gate.buildNextPhaseRequirements();
    assert.ok(requirements.some(r => r.includes('preflight')));
    assert.ok(requirements.some(r => r.includes('would_insert')));
});
test('would_write_db=false', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.would_write_db, false);
});
test('would_write_raw_match_data=false', () => {
    const gate = loadModuleFresh();
    const result = gate.buildRemainingRawMatchDataAcquisitionAuthorization(validArgs());
    assert.equal(result.would_write_raw_match_data, false);
});

// 49 Makefile target
test('Makefile authorization target succeeds', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-remaining-raw-match-data-acquisition-authorization:/m);
    assert.match(makefile, /l2_remaining_raw_match_data_acquisition_authorization\.js/);
});

// 50-54 source audits
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

// CLI tests
test('runCli succeeds for valid authorization', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs());
    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.authorized_remaining_targets.length, 7);
});
test('runCli returns non-zero for blocked write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowDbWriteThisPhase: true }));
    assert.equal(result.status, 1);
});
test('runCli help returns usage', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--help']);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 5\.18L2 is authorization-only/);
});

// Utility tests
test('parseRemainingExternalIds handles array and string inputs', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(gate.parseRemainingExternalIds('4830747,4830748'), ['4830747', '4830748']);
    assert.deepEqual(gate.parseRemainingExternalIds(['4830747', '4830748']), ['4830747', '4830748']);
    assert.deepEqual(gate.parseRemainingExternalIds(''), []);
    assert.deepEqual(gate.parseRemainingExternalIds(null), []);
});
test('parseArgs and normalizeBooleanFlag basics', () => {
    const gate = loadModuleFresh();
    const args = gate.parseArgs(['--source', 'fotmob', '--allow-training', 'yes']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.allowTraining, true);
    assert.equal(gate.normalizeBooleanFlag('no'), false);
    assert.equal(gate.normalizeBooleanFlag('1'), true);
});
