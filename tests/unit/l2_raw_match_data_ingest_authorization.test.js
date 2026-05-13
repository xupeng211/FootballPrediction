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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_match_data_ingest_authorization.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const PREVIEW_BODY_SHA256 = '8710a3524807d4682ab3c66386f9cd6b4d374fb6eee4f98a29d7f4a6683a162c';

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        homeTeam: 'Angers',
        awayTeam: 'Strasbourg',
        dataVersion: 'fotmob_html_hyd_v1',
        previewBodySha256: PREVIEW_BODY_SHA256,
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        userAuthorizedRawMatchDataIngest: true,
        allowRawMatchDataWriteNextPhase: true,
        allowDbWriteNow: false,
        allowRawMatchDataWriteNow: false,
        allowMatchesWrite: false,
        allowTraining: false,
        allowPrediction: false,
        finalHumanConfirmation: true,
        commit: false,
        execute: false,
        networkAuthorization: false,
        livePreviewAuthorization: false,
        ...overrides,
    };
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    return [
        `--source=${args.source}`,
        `--route=${args.route}`,
        `--match-id=${args.matchId}`,
        `--external-id=${args.externalId}`,
        `--home-team=${args.homeTeam}`,
        `--away-team=${args.awayTeam}`,
        `--data-version=${args.dataVersion}`,
        `--preview-body-sha256=${args.previewBodySha256}`,
        `--hydration-parse-ok=${args.hydrationParseOk ? 'yes' : 'no'}`,
        `--looks-like-valid-match-detail=${args.looksLikeValidMatchDetail ? 'yes' : 'no'}`,
        `--user-authorized-raw-match-data-ingest=${args.userAuthorizedRawMatchDataIngest ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write-next-phase=${args.allowRawMatchDataWriteNextPhase ? 'yes' : 'no'}`,
        `--allow-db-write-now=${args.allowDbWriteNow ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write-now=${args.allowRawMatchDataWriteNow ? 'yes' : 'no'}`,
        `--allow-matches-write=${args.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--final-human-confirmation=${args.finalHumanConfirmation ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${args.livePreviewAuthorization ? 'yes' : 'no'}`,
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
        throw new Error(`${name} should not be called by l2_raw_match_data_ingest_authorization`);
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
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
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

function assertInvalid(overrides, expectedPattern) {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs(overrides));
    assert.equal(authorization.ok, false);
    assert.match(authorization.controlled_error, expectedPattern);
    assert.equal(authorization.would_write_raw_match_data, false);
    assert.equal(authorization.would_write_db, false);
}

test('valid authorization input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validateAuthorizationInput(validArgs());
    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /unsupported source/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route/));
test('route non-html_hydration fails', () => assertInvalid({ route: 'api_match_details' }, /unsupported route/));
test('match-id missing fails', () => assertInvalid({ matchId: '' }, /missing match-id/));
test('match-id not 53_20252026_4830746 fails', () => assertInvalid({ matchId: 'x' }, /match-id must be/));
test('external-id missing fails', () => assertInvalid({ externalId: '' }, /missing external-id/));
test('external-id not 4830746 fails', () => assertInvalid({ externalId: '1' }, /external-id must be/));
test('home-team missing Angers fails', () => assertInvalid({ homeTeam: 'Paris' }, /home-team must contain Angers/));
test('away-team missing Strasbourg fails', () =>
    assertInvalid({ awayTeam: 'Lens' }, /away-team must contain Strasbourg/));
test('data-version missing fails', () => assertInvalid({ dataVersion: '' }, /missing data-version/));
test('data-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ dataVersion: 'fotmob_html_hydration_v1' }, /data-version must be/));
test('preview-body-sha256 missing fails', () =>
    assertInvalid({ previewBodySha256: '' }, /missing preview-body-sha256/));
test('hydration-parse-ok=no fails', () =>
    assertInvalid({ hydrationParseOk: false }, /hydration-parse-ok=yes is required/));
test('looks-like-valid-match-detail=no fails', () =>
    assertInvalid({ looksLikeValidMatchDetail: false }, /looks-like-valid-match-detail=yes is required/));
test('user-authorized-raw-match-data-ingest=no fails', () =>
    assertInvalid(
        { userAuthorizedRawMatchDataIngest: false },
        /user-authorized-raw-match-data-ingest=yes is required/
    ));
test('allow-raw-match-data-write-next-phase=no fails', () =>
    assertInvalid({ allowRawMatchDataWriteNextPhase: false }, /allow-raw-match-data-write-next-phase=yes is required/));
test('final-human-confirmation=no fails', () =>
    assertInvalid({ finalHumanConfirmation: false }, /final-human-confirmation=yes is required/));
test('allow-db-write-now=yes blocked', () =>
    assertInvalid({ allowDbWriteNow: true }, /allow-db-write-now=yes is blocked/));
test('allow-raw-match-data-write-now=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWriteNow: true }, /allow-raw-match-data-write-now=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('network-authorization=yes blocked', () =>
    assertInvalid({ networkAuthorization: true }, /network-authorization=yes is blocked/));
test('live-preview-authorization=yes blocked', () =>
    assertInvalid({ livePreviewAuthorization: true }, /live-preview-authorization=yes is blocked/));

test('output authorization_only=true', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.ok, true);
    assert.equal(authorization.authorization_only, true);
});

test('raw_match_data_write_allowed_next_phase=true', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.raw_match_data_write_allowed_next_phase, true);
});

test('raw_match_data_write_allowed_this_phase=false', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.raw_match_data_write_allowed_this_phase, false);
});

test('db_write_allowed_this_phase=false', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.db_write_allowed_this_phase, false);
});

test('would_write_raw_match_data=false', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.would_write_raw_match_data, false);
});

test('would_write_db=false', () => {
    const gate = loadModuleFresh();
    const authorization = gate.buildRawMatchDataIngestAuthorization(validArgs());
    assert.equal(authorization.would_write_db, false);
});

test('authorized_scope target_table=raw_match_data', () => {
    const gate = loadModuleFresh();
    const scope = gate.buildAuthorizedScope();
    assert.equal(scope.target_table, 'raw_match_data');
});

test('authorized_scope rows_limit=1', () => {
    const gate = loadModuleFresh();
    const scope = gate.buildAuthorizedScope();
    assert.equal(scope.rows_limit, 1);
});

test('authorization_gates include network_authorization_this_phase=false', () => {
    const gate = loadModuleFresh();
    const gates = gate.buildAuthorizationGates();
    assert.ok(gates.includes('network_authorization_this_phase=false'));
});

test('blocked_actions include write_raw_match_data', () => {
    const gate = loadModuleFresh();
    const blocked = gate.buildBlockedActionsThisPhase();
    assert.ok(blocked.includes('write_raw_match_data'));
});

test('blocked_actions include run_live_preview', () => {
    const gate = loadModuleFresh();
    const blocked = gate.buildBlockedActionsThisPhase();
    assert.ok(blocked.includes('run_live_preview'));
});

test('next_phase_requirements include would_insert/update/skip', () => {
    const gate = loadModuleFresh();
    const requirements = gate.buildNextPhaseRequirements().join('\n');
    assert.match(requirements, /would_insert \/ would_update \/ would_skip/);
});

test('Makefile authorization target is present and maps to authorization script', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-raw-match-data-ingest-authorization:/m);
    assert.match(makefile, /scripts\/ops\/l2_raw_match_data_ingest_authorization\.js/);
});

test('runCli succeeds with valid input and does not access network or DB', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs());
    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.authorization_only, true);
    assert.equal(result.payload.db_write_allowed_this_phase, false);
});

test('runCli returns non-zero for blocked DB write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowDbWriteNow: true }));
    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.match(result.payload.controlled_error, /allow-db-write-now=yes is blocked/);
});

test('source audit: no network access', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]node:http['"]\)|require\(['"]http['"]\)/);
    assert.doesNotMatch(source, /require\(['"]node:https['"]\)|require\(['"]https['"]\)/);
    assert.doesNotMatch(source, /\bfetch\s*\(/);
});

test('source audit: no DB write or pg client', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]pg['"]\)/);
    assert.doesNotMatch(source, /\.query\s*\(/);
    assert.doesNotMatch(source, /\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b/i);
    assert.doesNotMatch(source, /\b(TRUNCATE|ALTER\s+TABLE|DROP\s+TABLE|MERGE\s+INTO)\b/i);
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
