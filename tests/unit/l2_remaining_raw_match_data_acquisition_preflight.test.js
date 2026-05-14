'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const http = require('node:http');
const https = require('node:https');
const crypto = require('node:crypto');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const EXPECTED_IDS = '4830747,4830748,4830750,4830751,4830752,4830753,4830754';

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
        remainingExternalIds: EXPECTED_IDS,
        expectedTargetCount: 7,
        networkAuthorization: true,
        livePreviewAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowParserFeatures: false,
        allowTraining: false,
        allowPrediction: false,
        concurrency: 1,
        retry: 0,
        printBody: false,
        saveBody: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        bulk: false,
        commit: false,
        execute: false,
        ...overrides,
    };
}

// eslint-disable-next-line complexity
function cliArgs(overrides = {}) {
    const a = validArgs(overrides);
    return [
        `--source=${a.source}`,
        `--league-id=${a.leagueId}`,
        `--season=${a.season}`,
        `--date=${a.date}`,
        `--route=${a.route}`,
        `--remaining-external-ids=${a.remainingExternalIds}`,
        `--expected-target-count=${a.expectedTargetCount}`,
        `--network-authorization=${a.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${a.livePreviewAuthorization ? 'yes' : 'no'}`,
        `--allow-db-write=${a.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${a.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-matches-write=${a.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-parser-features=${a.allowParserFeatures ? 'yes' : 'no'}`,
        `--allow-training=${a.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${a.allowPrediction ? 'yes' : 'no'}`,
        `--concurrency=${a.concurrency}`,
        `--retry=${a.retry}`,
        `--print-body=${a.printBody ? 'yes' : 'no'}`,
        `--save-body=${a.saveBody ? 'yes' : 'no'}`,
        `--allow-browser-runtime=${a.allowBrowserRuntime ? 'yes' : 'no'}`,
        `--allow-proxy-runtime=${a.allowProxyRuntime ? 'yes' : 'no'}`,
        `--bulk=${a.bulk ? 'yes' : 'no'}`,
        `--commit=${a.commit ? 'yes' : 'no'}`,
        `--execute=${a.execute ? 'yes' : 'no'}`,
    ];
}

function installExecutionGuards(t) {
    const orig = {};
    const fail = name => () => {
        throw new Error(`${name} should not be called in preflight tests`);
    };
    orig.fetch = global.fetch;
    global.fetch = fail('global.fetch');
    orig.writeFile = fs.writeFile;
    fs.writeFile = fail('fs.writeFile');
    orig.writeFileSync = fs.writeFileSync;
    fs.writeFileSync = fail('fs.writeFileSync');
    orig.mkdir = fs.mkdir;
    fs.mkdir = fail('fs.mkdir');
    orig.mkdirSync = fs.mkdirSync;
    fs.mkdirSync = fail('fs.mkdirSync');
    orig.createWriteStream = fs.createWriteStream;
    fs.createWriteStream = fail('fs.createWriteStream');
    orig.spawn = childProcess.spawn;
    childProcess.spawn = fail('child_process.spawn');
    orig.exec = childProcess.exec;
    childProcess.exec = fail('child_process.exec');
    orig.execFile = childProcess.execFile;
    childProcess.execFile = fail('child_process.execFile');
    orig.httpReq = http.request;
    http.request = fail('http.request');
    orig.httpsReq = https.request;
    https.request = fail('https.request');
    orig.load = Module._load;
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
        if (blocked.has(request)) throw new Error(`blocked import: ${request}`);
        if (/ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i.test(request))
            throw new Error(`blocked import: ${request}`);
        return orig.load.call(this, request, parent, isMain);
    };
    t.after(() => {
        Object.assign(global, { fetch: orig.fetch });
        Object.assign(fs, {
            writeFile: orig.writeFile,
            writeFileSync: orig.writeFileSync,
            mkdir: orig.mkdir,
            mkdirSync: orig.mkdirSync,
            createWriteStream: orig.createWriteStream,
        });
        Object.assign(childProcess, { spawn: orig.spawn, exec: orig.exec, execFile: orig.execFile });
        http.request = orig.httpReq;
        https.request = orig.httpsReq;
        Module._load = orig.load;
    });
}

function assertInvalid(overrides, pattern) {
    const gate = loadModuleFresh();
    const v = gate.validatePreflightInput(validArgs(overrides));
    assert.equal(v.ok, false);
    assert.match(v.errors.join('\n'), pattern);
}

// 1-16 input validation
test('valid input succeeds', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.validatePreflightInput(validArgs()).ok, true);
});
test('source missing fails', () => assertInvalid({ source: '' }, /source must be fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('league-id not 53 fails', () => assertInvalid({ leagueId: '1' }, /league-id must be 53/));
test('season not 2025/2026 fails', () => assertInvalid({ season: '2024/2025' }, /season must be 2025/));
test('date not 2026-05-10 fails', () => assertInvalid({ date: '2026-05-11' }, /date must be 2026-05-10/));
test('route not html_hydration fails', () => assertInvalid({ route: 'api' }, /route must be html_hydration/));
test('remaining-external-ids missing fails', () =>
    assertInvalid({ remainingExternalIds: '' }, /remaining-external-ids is required/));
test('remaining-external-ids wrong count fails', () =>
    assertInvalid({ remainingExternalIds: '4830747' }, /must have 7 ids/));
test('remaining-external-ids includes 4830746 fails', () =>
    assertInvalid(
        { remainingExternalIds: '4830746,4830747,4830748,4830750,4830751,4830752,4830753' },
        /already ingested/
    ));
test('remaining-external-ids missing 4830754 fails', () =>
    assertInvalid(
        { remainingExternalIds: '4830747,4830748,4830750,4830751,4830752,4830753,9999999' },
        /missing expected/
    ));
test('expected-target-count not 7 fails', () => assertInvalid({ expectedTargetCount: 6 }, /must be 7/));
test('network-authorization=no fails', () =>
    assertInvalid({ networkAuthorization: false }, /network-authorization=yes is required/));
test('live-preview-authorization=no fails', () =>
    assertInvalid({ livePreviewAuthorization: false }, /live-preview-authorization=yes is required/));

// 19-30 blocked this phase
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-parser-features=yes blocked', () =>
    assertInvalid({ allowParserFeatures: true }, /allow-parser-features=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('concurrency > 1 blocked', () => assertInvalid({ concurrency: 3 }, /concurrency must be 1/));
test('retry > 0 blocked', () => assertInvalid({ retry: 2 }, /retry must be 0/));
test('print-body=yes blocked', () => assertInvalid({ printBody: true }, /print-body=yes is blocked/));
test('save-body=yes blocked', () => assertInvalid({ saveBody: true }, /save-body=yes is blocked/));
test('allow-browser-runtime=yes blocked', () =>
    assertInvalid({ allowBrowserRuntime: true }, /allow-browser-runtime=yes is blocked/));
test('allow-proxy-runtime=yes blocked', () =>
    assertInvalid({ allowProxyRuntime: true }, /allow-proxy-runtime=yes is blocked/));
test('bulk=yes blocked', () => assertInvalid({ bulk: true }, /bulk=yes is blocked/));

// 32-37 target registry and canonicalize
test('target registry contains exactly 7 targets', () => {
    const gate = loadModuleFresh();
    const registry = gate.getRemainingTargetRegistry();
    assert.equal(registry.length, 7);
});
test('target registry order stable', () => {
    const gate = loadModuleFresh();
    const registry = gate.getRemainingTargetRegistry();
    assert.equal(registry[0].external_id, '4830747');
    assert.equal(registry[6].external_id, '4830754');
});
test('canonicalizeJson stable sorted keys', () => {
    const gate = loadModuleFresh();
    const input = { b: 1, a: 2, c: [3, 1, 2] };
    const result = gate.canonicalizeJson(input);
    assert.equal(JSON.stringify(result), '{"a":2,"b":1,"c":[3,1,2]}');
});
test('sha256CanonicalJson stable', () => {
    const gate = loadModuleFresh();
    const h1 = gate.sha256CanonicalJson({ b: 1, a: 2 });
    const h2 = gate.sha256CanonicalJson({ a: 2, b: 1 });
    assert.equal(h1, h2);
    assert.equal(h1.length, 64);
});
test('buildRawData excludes full HTML body and includes _meta/matchId', () => {
    const gate = loadModuleFresh();
    const preview = {
        _meta: { ver: '1' },
        content: { matchFacts: {} },
        general: { matchId: 'x' },
        header: { teams: [] },
        matchId: '4830747',
        rawHtml: '<html>...LARGE...</html>',
        fullBody: 'HUGE',
    };
    const raw = gate.buildRawDataFromPreviewPayload(preview);
    assert.ok(raw._meta);
    assert.ok(raw.content);
    assert.ok(raw.general);
    assert.ok(raw.header);
    assert.ok(raw.matchId);
    assert.equal(raw.rawHtml, undefined);
    assert.equal(raw.fullBody, undefined);
});

// 38-41 decision logic
test('buildPerTargetPreflight: all no existing rows -> would_insert', () => {
    const gate = loadModuleFresh();
    const target = { match_id: '53_20252026_4830747', external_id: '4830747', home_team: 'A', away_team: 'B' };
    const recapture = {
        requestUrl: 'u',
        finalUrl: 'u',
        httpStatus: 200,
        bodyByteLength: 100,
        bodySha256: 'abc',
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        payload: { matchId: '4830747' },
    };
    const entry = gate.buildPerTargetPreflight(target, recapture, null);
    assert.equal(entry.decision, 'would_insert');
    assert.equal(entry.existing_raw_match_data_found, false);
});
test('buildPerTargetPreflight: same hash existing row -> would_skip', () => {
    const gate = loadModuleFresh();
    const target = { match_id: '53_20252026_4830747', external_id: '4830747', home_team: 'A', away_team: 'B' };
    const recapture = {
        requestUrl: 'u',
        finalUrl: 'u',
        httpStatus: 200,
        bodyByteLength: 100,
        bodySha256: 'abc',
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        payload: { matchId: '4830747' },
    };
    const raw = gate.buildRawDataFromPreviewPayload(recapture.payload || recapture);
    const hash = gate.sha256CanonicalJson(raw);
    const entry = gate.buildPerTargetPreflight(target, recapture, { data_hash: hash });
    assert.equal(entry.decision, 'would_skip');
    assert.equal(entry.existing_raw_match_data_found, true);
});
test('buildPerTargetPreflight: different hash existing row -> would_update', () => {
    const gate = loadModuleFresh();
    const target = { match_id: '53_20252026_4830747', external_id: '4830747', home_team: 'A', away_team: 'B' };
    const recapture = {
        requestUrl: 'u',
        finalUrl: 'u',
        httpStatus: 200,
        bodyByteLength: 100,
        bodySha256: 'abc',
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        payload: { matchId: '4830747' },
    };
    const entry = gate.buildPerTargetPreflight(target, recapture, { data_hash: 'different_hash_value' });
    assert.equal(entry.decision, 'would_update');
});

// 42-46 output assertions
test('preflight output with fake recapture yields 7 would_insert', async () => {
    const gate = loadModuleFresh();
    const fakeRecapture = async target => ({
        requestUrl: 'https://www.fotmob.com/en-GB/match-script/?matchId=' + target.external_id,
        finalUrl: 'https://www.fotmob.com/match/' + target.external_id,
        httpStatus: 200,
        contentType: 'text/html',
        bodyByteLength: 50000,
        bodySha256: crypto.createHash('sha256').update(target.external_id).digest('hex'),
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        payload: { _meta: { ver: '1' }, general: { matchId: target.external_id }, matchId: target.external_id },
    });
    const plan = await gate.buildRemainingRawMatchDataAcquisitionPreflight(validArgs(), { recaptureFn: fakeRecapture });
    assert.equal(plan.ok, true);
    assert.equal(plan.preflight_only, true);
    assert.equal(plan.attempted_target_count, 7);
    assert.equal(plan.valid_payload_count, 7);
    assert.equal(plan.failed_target_count, 0);
    assert.equal(plan.would_insert_count, 7);
    assert.equal(plan.would_update_count, 0);
    assert.equal(plan.would_skip_count, 0);
    assert.equal(plan.would_write_db, false);
    assert.equal(plan.would_write_raw_match_data, false);
    assert.equal(plan.would_parse_features, false);
    assert.equal(plan.would_train, false);
    assert.equal(plan.would_predict, false);
    assert.equal(plan.parser_features_allowed, false);
    assert.equal(plan.training_allowed, false);
    assert.ok(plan.protected_table_baseline);
});

test('preflight with one failed target -> failed count = 1', async () => {
    const gate = loadModuleFresh();
    let calls = 0;
    const mixedRecapture = async target => {
        calls += 1;
        if (calls === 3) {
            return {
                requestUrl: 'url',
                finalUrl: 'url',
                httpStatus: 503,
                contentType: null,
                bodyByteLength: 0,
                bodySha256: null,
                hydrationParseOk: false,
                looksLikeValidMatchDetail: false,
            };
        }
        return {
            requestUrl: 'url',
            finalUrl: 'url',
            httpStatus: 200,
            contentType: 'text/html',
            bodyByteLength: 50000,
            bodySha256: crypto.createHash('sha256').update(target.external_id).digest('hex'),
            hydrationParseOk: true,
            looksLikeValidMatchDetail: true,
            payload: { matchId: target.external_id },
        };
    };
    const plan = await gate.buildRemainingRawMatchDataAcquisitionPreflight(validArgs(), {
        recaptureFn: mixedRecapture,
    });
    assert.equal(plan.valid_payload_count, 6);
    assert.equal(plan.failed_target_count, 1);
});

test('runCli help returns usage', async () => {
    const gate = loadModuleFresh();
    let stdout = '';
    const status = await gate.runCli(['--help'], {
        stdout: text => {
            stdout += text;
        },
    });
    assert.equal(status, 0);
    assert.match(stdout, /Phase 5\.19L2 is preflight-only/);
});

// Makefile target
test('Makefile preflight target exists', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-remaining-raw-match-data-acquisition-preflight:/m);
    assert.match(makefile, /l2_remaining_raw_match_data_acquisition_preflight\.js/);
});

// Source audits
test('source audit: no fs write', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});
test('source audit: no ProductionHarvester / raw ingest', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});
test('source audit: no DB write SQL', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /\bINSERT\s+INTO\b/i);
    assert.doesNotMatch(source, /\bUPDATE\s+\w+\s+SET\b/i);
    assert.doesNotMatch(source, /\bDELETE\s+FROM\b/i);
});

// Utility tests
test('parseRemainingExternalIds with various inputs', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(gate.parseRemainingExternalIds(EXPECTED_IDS), [
        '4830747',
        '4830748',
        '4830750',
        '4830751',
        '4830752',
        '4830753',
        '4830754',
    ]);
    assert.deepEqual(gate.parseRemainingExternalIds(['4830747', '4830748']), ['4830747', '4830748']);
    assert.deepEqual(gate.parseRemainingExternalIds(''), []);
});

test('parseArgs basic', () => {
    const gate = loadModuleFresh();
    const args = gate.parseArgs(['--source', 'fotmob', '--allow-db-write', 'yes']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.allowDbWrite, true);
});

test('buildProtectedTableBaseline defaults and overrides', () => {
    const gate = loadModuleFresh();
    const b1 = gate.buildProtectedTableBaseline({});
    assert.equal(b1.matches, 10);
    assert.equal(b1.raw_match_data, 3);
    const b2 = gate.buildProtectedTableBaseline({ matches: 15, raw_match_data: 8 });
    assert.equal(b2.matches, 15);
    assert.equal(b2.raw_match_data, 8);
});
