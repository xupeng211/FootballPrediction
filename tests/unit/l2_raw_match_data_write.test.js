/* eslint-disable max-lines */
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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_match_data_write.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const BASELINE_RAW_DATA_HASH = 'd40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6';
const PREVIEW_BODY_SHA256 = '394e4d4546ba52859b93b07167cd9000cd89758770d7cc16b3688626acee7980';
const PRE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 2,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const POST_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 3,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

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
        baselineRawDataHash: BASELINE_RAW_DATA_HASH,
        networkAuthorization: true,
        livePreviewAuthorization: true,
        finalDbWriteConfirmation: true,
        allowDbWrite: true,
        allowRawMatchDataWrite: true,
        allowMatchesWrite: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: 1,
        retry: 0,
        printBody: false,
        saveBody: false,
        bulk: false,
        commit: false,
        execute: false,
        ...overrides,
    };
}

function toYesNo(value) {
    return value ? 'yes' : 'no';
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    const pairs = [
        ['source', args.source],
        ['route', args.route],
        ['match-id', args.matchId],
        ['external-id', args.externalId],
        ['home-team', args.homeTeam],
        ['away-team', args.awayTeam],
        ['data-version', args.dataVersion],
        ['baseline-raw-data-hash', args.baselineRawDataHash],
        ['network-authorization', toYesNo(args.networkAuthorization)],
        ['live-preview-authorization', toYesNo(args.livePreviewAuthorization)],
        ['final-db-write-confirmation', toYesNo(args.finalDbWriteConfirmation)],
        ['allow-db-write', toYesNo(args.allowDbWrite)],
        ['allow-raw-match-data-write', toYesNo(args.allowRawMatchDataWrite)],
        ['allow-matches-write', toYesNo(args.allowMatchesWrite)],
        ['allow-training', toYesNo(args.allowTraining)],
        ['allow-prediction', toYesNo(args.allowPrediction)],
        ['allow-browser-runtime', toYesNo(args.allowBrowserRuntime)],
        ['allow-proxy-runtime', toYesNo(args.allowProxyRuntime)],
        ['concurrency', args.concurrency],
        ['retry', args.retry],
        ['print-body', toYesNo(args.printBody)],
        ['save-body', toYesNo(args.saveBody)],
        ['bulk', toYesNo(args.bulk)],
        ['commit', toYesNo(args.commit)],
        ['execute', toYesNo(args.execute)],
    ];
    return pairs.map(([key, value]) => `--${key}=${value}`);
}

function fakePayload() {
    return {
        matchId: '4830746',
        content: {
            stats: [{ title: 'Top stats', stats: [] }],
            lineup: { homeTeam: 'Angers', awayTeam: 'Strasbourg' },
            shotmap: [],
        },
        general: {
            matchId: '4830746',
            homeTeam: { name: 'Angers' },
            awayTeam: { name: 'Strasbourg' },
        },
        header: {
            teams: [
                { name: 'Angers', id: 982 },
                { name: 'Strasbourg', id: 984 },
            ],
        },
        _meta: {
            hasStats: true,
            hasLineup: true,
            hasShotmap: true,
        },
        fullHtmlBody: '<html>must not be copied</html>',
        httpResponseString: 'must not be copied',
    };
}

function fakePreviewResult(overrides = {}) {
    return {
        summary: {
            ok: true,
            selected_route: 'html_hydration',
            request_url: 'https://www.fotmob.com/match/4830746',
            final_url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
            http_status: 200,
            content_type: 'text/html; charset=utf-8',
            body_byte_length: 1037598,
            body_sha256: PREVIEW_BODY_SHA256,
            hydration_parse_ok: true,
            looks_like_valid_match_detail: true,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            ...overrides.summary,
        },
        payload: overrides.payload || fakePayload(),
    };
}

function fakeHtml() {
    const nextData = {
        props: {
            pageProps: {
                content: {
                    stats: [{ title: 'Top stats', stats: [] }],
                    lineup: { homeTeam: 'Angers', awayTeam: 'Strasbourg' },
                    shotmap: [],
                },
                general: {
                    matchId: '4830746',
                    homeTeam: { name: 'Angers' },
                    awayTeam: { name: 'Strasbourg' },
                },
                header: {
                    teams: [
                        { name: 'Angers', id: 982 },
                        { name: 'Strasbourg', id: 984 },
                    ],
                },
            },
        },
    };
    return `<html><body>Angers Strasbourg 4830746<script id="__NEXT_DATA__" type="application/json">${JSON.stringify(
        nextData
    )}</script></body></html>`;
}

function fakeFetchImpl() {
    return async url => ({
        status: 200,
        statusCode: 200,
        ok: true,
        url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
        headers: {
            get: name => (String(name).toLowerCase() === 'content-type' ? 'text/html; charset=utf-8' : ''),
        },
        text: async () => {
            assert.equal(String(url), 'https://www.fotmob.com/match/4830746');
            return fakeHtml();
        },
    });
}

function targetMatchRows() {
    return [
        {
            match_id: '53_20252026_4830746',
            external_id: '4830746',
            home_team: 'Angers',
            away_team: 'Strasbourg',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
        },
    ];
}

function insertedRow(overrides = {}) {
    return {
        id: 99,
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        collected_at: '2026-05-14T10:11:12.000Z',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: BASELINE_RAW_DATA_HASH,
        ...overrides,
    };
}

function fakeDeps(overrides = {}) {
    return {
        previewPayloadResult: fakePreviewResult(overrides.preview || {}),
        now: '2026-05-14T10:11:12.000Z',
        rawDataHashOverride: BASELINE_RAW_DATA_HASH,
        ...overrides,
    };
}

function isSelectUnionQuery(text) {
    return /^SELECT/i.test(text) && text.includes('UNION ALL');
}

function isSelectMatchesQuery(text) {
    return /^SELECT/i.test(text) && text.includes('FROM matches');
}

function isSelectRawMatchDataQuery(text) {
    return /^SELECT/i.test(text) && text.includes('FROM raw_match_data');
}

function isInsertRawMatchDataQuery(text) {
    return /^INSERT\s+INTO\s+raw_match_data/i.test(text);
}

function buildBaselineRows(baselineRows) {
    return Object.entries(baselineRows).map(([table_name, rows]) => ({ table_name, rows }));
}

function resolveBaselineRows(queries, existingRows, preBaseline, postBaseline) {
    return queries.some(item => isInsertRawMatchDataQuery(item.text)) || existingRows.length > 0
        ? postBaseline
        : preBaseline;
}

function resolveRawMatchRows(queries, existingRows, verificationRow) {
    const selectCount = queries.filter(item => isSelectRawMatchDataQuery(item.text)).length;
    if (existingRows.length > 0) {
        return existingRows;
    }
    if (selectCount === 1) {
        return [];
    }
    return verificationRow ? [verificationRow] : [];
}

function buildQueryResponse(text, queries, options) {
    const { existingRows, preBaseline, postBaseline, insertFailure, verificationRow } = options;

    if (text === 'BEGIN' || text === 'COMMIT' || text === 'ROLLBACK') {
        return { rows: [] };
    }
    if (isSelectUnionQuery(text)) {
        return {
            rows: buildBaselineRows(resolveBaselineRows(queries, existingRows, preBaseline, postBaseline)),
        };
    }
    if (isSelectMatchesQuery(text)) {
        return { rows: targetMatchRows() };
    }
    if (isSelectRawMatchDataQuery(text)) {
        return {
            rows: resolveRawMatchRows(queries, existingRows, verificationRow),
        };
    }
    if (isInsertRawMatchDataQuery(text)) {
        if (insertFailure) {
            throw insertFailure;
        }
        return {
            rows: verificationRow ? [verificationRow] : [],
        };
    }
    throw new Error(`unexpected query: ${text}`);
}

function buildReadWriteClient({
    existingRows = [],
    preBaseline = PRE_BASELINE,
    postBaseline = POST_BASELINE,
    insertFailure = null,
    verificationRow = insertedRow(),
} = {}) {
    const queries = [];
    const options = {
        existingRows,
        preBaseline,
        postBaseline,
        insertFailure,
        verificationRow,
    };
    return {
        queries,
        async query(sql, values = []) {
            const text = String(sql || '').trim();
            queries.push({ text, values });
            return buildQueryResponse(text, queries, options);
        },
    };
}

function buildConnectablePool(client) {
    let released = false;
    let ended = false;
    return {
        pool: {
            async connect() {
                return {
                    query: client.query.bind(client),
                    release() {
                        released = true;
                    },
                };
            },
            async end() {
                ended = true;
            },
        },
        get released() {
            return released;
        },
        get ended() {
            return ended;
        },
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
        throw new Error(`${name} should not be called by l2_raw_match_data_write`);
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

async function runCli(gate, argv, dependencies = fakeDeps()) {
    let stdout = '';
    const status = await gate.runCli(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
        },
        dependencies
    );
    return {
        status,
        stdout,
        payload: stdout.trim().startsWith('{') ? JSON.parse(stdout) : null,
    };
}

function assertInvalid(overrides, pattern) {
    const gate = loadModuleFresh();
    const validation = gate.validateWriteInput(validArgs(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

test('valid input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validateWriteInput(validArgs());
    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /unsupported source/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route/));
test('route unsupported fails', () => assertInvalid({ route: 'auto' }, /unsupported route/));
test('match-id missing fails', () => assertInvalid({ matchId: '' }, /missing match-id/));
test('match-id not 53_20252026_4830746 fails', () => assertInvalid({ matchId: 'x' }, /match-id must be/));
test('external-id missing fails', () => assertInvalid({ externalId: '' }, /missing external-id/));
test('external-id not 4830746 fails', () => assertInvalid({ externalId: '1' }, /external-id must be/));
test('home-team missing Angers fails', () => assertInvalid({ homeTeam: 'Paris' }, /home-team must contain Angers/));
test('away-team missing Strasbourg fails', () =>
    assertInvalid({ awayTeam: 'Lens' }, /away-team must contain Strasbourg/));
test('data-version missing fails', () => assertInvalid({ dataVersion: '' }, /missing data-version/));
test('data-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ dataVersion: 'other_v1' }, /data-version must be/));
test('baseline hash missing fails', () => assertInvalid({ baselineRawDataHash: '' }, /missing baseline-raw-data-hash/));
test('baseline hash wrong fails', () =>
    assertInvalid({ baselineRawDataHash: 'abc' }, /baseline-raw-data-hash must be/));
test('network-authorization=no fails', () =>
    assertInvalid({ networkAuthorization: false }, /network-authorization=yes is required/));
test('live-preview-authorization=no fails', () =>
    assertInvalid({ livePreviewAuthorization: false }, /live-preview-authorization=yes is required/));
test('final-db-write-confirmation=no fails', () =>
    assertInvalid({ finalDbWriteConfirmation: false }, /final-db-write-confirmation=yes is required/));
test('allow-db-write=no fails', () => assertInvalid({ allowDbWrite: false }, /allow-db-write=yes is required/));
test('allow-raw-match-data-write=no fails', () =>
    assertInvalid({ allowRawMatchDataWrite: false }, /allow-raw-match-data-write=yes is required/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('retry > 0 blocked', () => assertInvalid({ retry: 1 }, /retry > 0 is blocked/));
test('concurrency > 1 blocked', () => assertInvalid({ concurrency: 2 }, /concurrency > 1 is blocked/));
test('print-body=yes blocked', () => assertInvalid({ printBody: true }, /print-body=yes is blocked/));
test('save-body=yes blocked', () => assertInvalid({ saveBody: true }, /save-body=yes is blocked/));
test('browser/proxy allowed blocked', () => {
    assertInvalid({ allowBrowserRuntime: true }, /allow-browser-runtime=yes is blocked/);
    assertInvalid({ allowProxyRuntime: true }, /allow-proxy-runtime=yes is blocked/);
});
test('bulk=yes blocked', () => assertInvalid({ bulk: true }, /bulk=yes is blocked/));

test('normalizeBooleanFlag handles fallback and parseArgs handles unknown arguments', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.normalizeBooleanFlag('YES'), true);
    assert.equal(gate.normalizeBooleanFlag('off'), false);
    assert.equal(gate.normalizeBooleanFlag('maybe', false), false);
    assert.equal(gate.normalizeBooleanFlag('', true), true);

    const args = gate.parseArgs(['orphan', '--source', 'fotmob', '--route', 'html_hydration', '--mystery', '--help']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.route, 'html_hydration');
    assert.equal(args.help, true);
    assert.deepEqual(args.unknown, ['orphan', 'mystery']);
});

test('validateWriteInput reports missing required flags and invalid numeric knobs', () => {
    const gate = loadModuleFresh();
    const validation = gate.validateWriteInput(
        validArgs({
            networkAuthorization: undefined,
            livePreviewAuthorization: undefined,
            finalDbWriteConfirmation: undefined,
            allowDbWrite: undefined,
            allowRawMatchDataWrite: undefined,
            allowMatchesWrite: undefined,
            allowTraining: undefined,
            allowPrediction: undefined,
            printBody: undefined,
            saveBody: undefined,
            homeTeam: '',
            awayTeam: '',
            concurrency: 'many',
            retry: 'later',
        })
    );
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /missing network-authorization=yes/);
    assert.match(validation.errors.join('\n'), /missing live-preview-authorization=yes/);
    assert.match(validation.errors.join('\n'), /missing final-db-write-confirmation=yes/);
    assert.match(validation.errors.join('\n'), /missing allow-db-write=yes/);
    assert.match(validation.errors.join('\n'), /missing allow-raw-match-data-write=yes/);
    assert.match(validation.errors.join('\n'), /missing allow-matches-write=no/);
    assert.match(validation.errors.join('\n'), /missing allow-training=no/);
    assert.match(validation.errors.join('\n'), /missing allow-prediction=no/);
    assert.match(validation.errors.join('\n'), /missing print-body=no/);
    assert.match(validation.errors.join('\n'), /missing save-body=no/);
    assert.match(validation.errors.join('\n'), /missing home-team/);
    assert.match(validation.errors.join('\n'), /missing away-team/);
    assert.match(validation.errors.join('\n'), /concurrency must be 1/);
    assert.match(validation.errors.join('\n'), /retry must be 0/);
});

test('canonicalizeJson stable', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.canonicalizeJson({ z: 1, a: { c: 3, b: 2 } }), '{"a":{"b":2,"c":3},"z":1}');
});

test('sha256CanonicalJson stable', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.sha256CanonicalJson({ b: 2, a: 1 }), gate.sha256CanonicalJson({ a: 1, b: 2 }));
});

test('buildRawData excludes full HTML body', () => {
    const gate = loadModuleFresh();
    const preview = fakePreviewResult();
    const rawData = gate.buildRawDataFromPreviewPayload(preview.payload, preview.summary, validArgs());
    assert.equal(rawData.fullHtmlBody, undefined);
    assert.equal(rawData.httpResponseString, undefined);
    assert.equal(JSON.stringify(rawData).includes('<html>must not be copied</html>'), false);
});

test('buildRawData includes _meta/content/general/header/matchId', () => {
    const gate = loadModuleFresh();
    const preview = fakePreviewResult();
    const rawData = gate.buildRawDataFromPreviewPayload(preview.payload, preview.summary, validArgs());
    assert.deepEqual(Object.keys(rawData).sort(), ['_meta', 'content', 'general', 'header', 'matchId'].sort());
    assert.equal(rawData.matchId, '4830746');
});

test('buildRawData handles non-object payload without HTML body fields', () => {
    const gate = loadModuleFresh();
    const rawData = gate.buildRawDataFromPreviewPayload(null, fakePreviewResult().summary, validArgs());
    assert.deepEqual(rawData.content, {});
    assert.deepEqual(rawData.general, {});
    assert.deepEqual(rawData.header, {});
    assert.equal(rawData.matchId, '4830746');
    assert.equal(rawData._meta.has_stats, false);
    assert.equal(rawData._meta.full_html_body_stored, false);
    assert.equal(rawData._meta.http_response_string_stored, false);
});

test('invalid preview summary returns controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps({
            preview: {
                summary: {
                    ok: false,
                    controlled_error: 'NO_VALID_ROUTE_PAYLOAD',
                    selected_route: 'none',
                    http_status: 403,
                    hydration_parse_ok: false,
                    looks_like_valid_match_detail: false,
                    body_printed: true,
                    body_saved: true,
                    browser_used: true,
                    proxy_used: true,
                },
            },
        }),
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /NO_VALID_ROUTE_PAYLOAD/);
    assert.match(result.controlled_error, /body_printed=true is blocked/);
    assert.match(result.controlled_error, /body_saved=true is blocked/);
    assert.match(result.controlled_error, /browser_used=true is blocked/);
    assert.match(result.controlled_error, /proxy_used=true is blocked/);
});

test('target match validation failures return controlled error', async () => {
    const gate = loadModuleFresh();
    const missingTargetClient = buildReadWriteClient();
    missingTargetClient.query = async (sql, values = []) => {
        const text = String(sql || '').trim();
        missingTargetClient.queries.push({ text, values });
        if (text === 'BEGIN' || text === 'COMMIT' || text === 'ROLLBACK') {
            return { rows: [] };
        }
        if (isSelectMatchesQuery(text)) {
            return { rows: [] };
        }
        return buildQueryResponse(text, missingTargetClient.queries, {
            existingRows: [],
            preBaseline: PRE_BASELINE,
            postBaseline: POST_BASELINE,
            insertFailure: null,
            verificationRow: insertedRow(),
        });
    };
    const missingResult = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: missingTargetClient,
    });
    assert.equal(missingResult.execution_completed, false);
    assert.match(missingResult.controlled_error, /TARGET_MATCH_VALIDATION_FAILED/);

    const mismatchClient = buildReadWriteClient();
    mismatchClient.query = async (sql, values = []) => {
        const text = String(sql || '').trim();
        mismatchClient.queries.push({ text, values });
        if (text === 'BEGIN' || text === 'COMMIT' || text === 'ROLLBACK') {
            return { rows: [] };
        }
        if (isSelectMatchesQuery(text)) {
            return {
                rows: [
                    {
                        match_id: '53_20252026_4830746',
                        external_id: '999',
                        home_team: 'Paris',
                        away_team: 'Lens',
                    },
                ],
            };
        }
        return buildQueryResponse(text, mismatchClient.queries, {
            existingRows: [],
            preBaseline: PRE_BASELINE,
            postBaseline: POST_BASELINE,
            insertFailure: null,
            verificationRow: insertedRow(),
        });
    };
    const mismatchResult = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: mismatchClient,
    });
    assert.equal(mismatchResult.execution_completed, false);
    assert.match(mismatchResult.controlled_error, /target external_id mismatch/);
    assert.match(mismatchResult.controlled_error, /target home_team must contain Angers/);
    assert.match(mismatchResult.controlled_error, /target away_team must contain Strasbourg/);
});

test('multiple existing raw rows return controlled error', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        existingRows: [insertedRow({ id: 1 }), insertedRow({ id: 2 })],
        preBaseline: POST_BASELINE,
        postBaseline: POST_BASELINE,
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /EXISTING_RAW_MATCH_DATA_VALIDATION_FAILED/);
});

test('existing raw row with wrong data_version returns controlled error', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        existingRows: [insertedRow({ data_version: 'fotmob_pageprops_v2' })],
        preBaseline: POST_BASELINE,
        postBaseline: POST_BASELINE,
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /expected data_version fotmob_html_hyd_v1/);
});

test('pre-write baseline mismatch returns controlled error', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        preBaseline: {
            ...PRE_BASELINE,
            raw_match_data: 9,
        },
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /PRE_WRITE_BASELINE_MISMATCH/);
});

test('post-write verification failure rolls back', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        verificationRow: null,
        postBaseline: {
            ...POST_BASELINE,
            raw_match_data: 2,
        },
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.transaction.rolled_back, true);
    assert.match(result.controlled_error, /POST_WRITE_VERIFICATION_FAILED/);
});

test('hash drift stops before DB write', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
        rawDataHashOverride: 'hash-drift',
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.hash_matches_preflight_baseline, false);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(client.queries.length, 0);
});

test('executeRawMatchDataWrite supports connectable pool cleanup and now() function', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const pooled = buildConnectablePool(client);
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps({
            now: () => '2026-05-14T10:11:12.000Z',
        }),
        createPool: () => pooled.pool,
    });
    assert.equal(result.execution_completed, true);
    assert.equal(pooled.released, true);
    assert.equal(pooled.ended, true);
});

test('skipValidation path can execute with provided dependencies', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        skipValidation: true,
        client: buildReadWriteClient(),
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.inserted_count, 1);
});

test('existing same hash skips without write', async () => {
    const gate = loadModuleFresh();
    const existing = insertedRow();
    const client = buildReadWriteClient({
        existingRows: [existing],
        preBaseline: POST_BASELINE,
        postBaseline: POST_BASELINE,
        verificationRow: existing,
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.skipped_count, 1);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.reason, 'same_hash_existing_row');
    assert.equal(
        client.queries.some(item => /^INSERT/i.test(item.text)),
        false
    );
});

test('existing different hash stops without update', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        existingRows: [insertedRow({ data_hash: 'old-hash' })],
        preBaseline: POST_BASELINE,
        postBaseline: POST_BASELINE,
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.transaction.rolled_back, true);
    assert.match(result.controlled_error, /EXISTING_ROW_HASH_MISMATCH_REQUIRES_UPDATE_AUTHORIZATION/);
});

test('no existing row inserts exactly one row in fake DB transaction', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.inserted_count, 1);
    assert.equal(result.updated_count, 0);
    assert.equal(result.skipped_count, 0);
    assert.equal(client.queries.filter(item => /^INSERT/i.test(item.text)).length, 1);
    const rawSelects = client.queries.filter(item => isSelectRawMatchDataQuery(item.text) && !item.text.includes('UNION ALL'));
    assert.ok(rawSelects.length >= 2);
    for (const rawSelect of rawSelects) {
        assert.match(rawSelect.text, /match_id = \$1\s+AND data_version = \$2/i);
        assert.deepEqual(rawSelect.values, ['53_20252026_4830746', 'fotmob_html_hyd_v1']);
    }
});

test('transaction commits on success', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.transaction.began, true);
    assert.equal(result.transaction.committed, true);
    assert.equal(result.transaction.rolled_back, false);
});

test('transaction rolls back on insert failure', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient({
        insertFailure: new Error('insert failed'),
    });
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.transaction.began, true);
    assert.equal(result.transaction.committed, false);
    assert.equal(result.transaction.rolled_back, true);
    assert.match(result.controlled_error, /insert failed/);
});

test('SQL plan only targets raw_match_data', () => {
    const gate = loadModuleFresh();
    const rawData = gate.buildRawDataFromPreviewPayload(fakePayload(), fakePreviewResult().summary, validArgs());
    const sql = gate.buildInsertRawMatchDataSql({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        rawData,
        collectedAt: '2026-05-14T10:11:12.000Z',
        dataVersion: 'fotmob_html_hyd_v1',
        dataHash: BASELINE_RAW_DATA_HASH,
    });
    assert.match(sql.text, /INSERT INTO raw_match_data/i);
    assert.match(sql.text, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
    assert.equal(sql.values[4], 'fotmob_html_hyd_v1');
});

test('SQL plan does not mention matches update', () => {
    const gate = loadModuleFresh();
    const rawData = gate.buildRawDataFromPreviewPayload(fakePayload(), fakePreviewResult().summary, validArgs());
    const sql = gate.buildInsertRawMatchDataSql({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        rawData,
        collectedAt: '2026-05-14T10:11:12.000Z',
        dataVersion: 'fotmob_html_hyd_v1',
        dataHash: BASELINE_RAW_DATA_HASH,
    });
    assert.doesNotMatch(sql.text, /\bUPDATE\s+matches\b/i);
});

test('SQL plan does not mention features/predictions', () => {
    const gate = loadModuleFresh();
    const rawData = gate.buildRawDataFromPreviewPayload(fakePayload(), fakePreviewResult().summary, validArgs());
    const sql = gate.buildInsertRawMatchDataSql({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        rawData,
        collectedAt: '2026-05-14T10:11:12.000Z',
        dataVersion: 'fotmob_html_hyd_v1',
        dataHash: BASELINE_RAW_DATA_HASH,
    });
    assert.doesNotMatch(sql.text, /\b(l3_features|match_features_training|predictions)\b/i);
});

test('output inserted_count=1 on fake success', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: buildReadWriteClient(),
    });
    assert.equal(result.inserted_count, 1);
});

test('output raw_match_data_write_executed=true on fake success', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: buildReadWriteClient(),
    });
    assert.equal(result.raw_match_data_write_executed, true);
});

test('output matches_write_executed=false', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: buildReadWriteClient(),
    });
    assert.equal(result.matches_write_executed, false);
});

test('post_write_verification includes protected tables', () => {
    const gate = loadModuleFresh();
    const verification = gate.buildPostWriteVerification(POST_BASELINE, insertedRow());
    assert.deepEqual(verification, {
        raw_match_data_row_found: true,
        matches: 10,
        raw_match_data: 3,
        bookmaker_odds_history: 2,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
    });
});

test('no full body print/save', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client: buildReadWriteClient(),
    });
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
});

test('runCli uses fake payload and fake write DB without fs writes or spawn', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await runCli(gate, cliArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.execution_completed, true);
    assert.equal(result.payload.inserted_count, 1);
});

test('runCli returns non-zero for blocked allow-matches-write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowMatchesWrite: true }));
    assert.equal(result.status, 1);
    assert.equal(result.payload.execution_completed, false);
    assert.match(result.payload.controlled_error, /allow-matches-write=yes is blocked/);
});

test('runCli help returns usage without executing write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--help'], fakeDeps());
    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 5\.16L2 performs one controlled live recapture/);
    assert.equal(result.payload, null);
});

test('recapture path uses fake fetch and does not save or print body', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        fetchImpl: fakeFetchImpl(),
        rawDataHashOverride: BASELINE_RAW_DATA_HASH,
        client: buildReadWriteClient(),
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.selected_route, 'html_hydration');
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
});

test('recapture path fails closed when fetch is unavailable', async t => {
    const originalFetch = global.fetch;
    global.fetch = undefined;
    t.after(() => {
        global.fetch = originalFetch;
    });

    const gate = loadModuleFresh();
    await assert.rejects(
        () => gate.executeRawMatchDataWrite(validArgs(), { client: buildReadWriteClient() }),
        /FETCH_UNAVAILABLE/
    );
});

test('recapture path fails closed when hydration payload cannot be parsed', async () => {
    const gate = loadModuleFresh();
    await assert.rejects(
        () =>
            gate.executeRawMatchDataWrite(validArgs(), {
                fetchImpl: async () => ({
                    status: 200,
                    statusCode: 200,
                    ok: true,
                    url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
                    headers: {
                        get: () => 'text/html; charset=utf-8',
                    },
                    text: async () => '<html><body>Angers Strasbourg 4830746</body></html>',
                }),
                client: buildReadWriteClient(),
            }),
        /NEXT_DATA_PARSE_FAILED|NO_NEXT_DATA|__NEXT_DATA__/
    );
});

test('catch path records rollback failure without throwing', async () => {
    const gate = loadModuleFresh();
    const queries = [];
    const client = {
        async query(sql) {
            const text = String(sql || '').trim();
            queries.push(text);
            if (text === 'BEGIN') {
                return { rows: [] };
            }
            if (text === 'ROLLBACK') {
                throw new Error('rollback failed');
            }
            if (isSelectMatchesQuery(text)) {
                throw new Error('select exploded');
            }
            return { rows: [] };
        },
    };
    const result = await gate.executeRawMatchDataWrite(validArgs(), {
        ...fakeDeps(),
        client,
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /select exploded/);
    assert.equal(queries.includes('ROLLBACK'), true);
});

test('buildControlledWriteResult renders success shape', () => {
    const gate = loadModuleFresh();
    const result = gate.buildControlledWriteResult({
        input: validArgs(),
        previewSummary: fakePreviewResult().summary,
        rawDataHash: BASELINE_RAW_DATA_HASH,
        executionCompleted: true,
        existingRawMatchDataFound: false,
        insertedCount: 1,
        rawMatchDataWriteExecuted: true,
        dbWriteExecuted: true,
        transaction: {
            began: true,
            committed: true,
            rolled_back: false,
        },
        postWriteVerification: gate.buildPostWriteVerification(POST_BASELINE, insertedRow()),
        insertedRow: insertedRow(),
        hashMatchesPreflightBaseline: true,
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.inserted_row_metadata.match_id, '53_20252026_4830746');
});

test('Makefile write target exists and no legacy commit target added', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-raw-match-data-write:/m);
    assert.match(makefile, /scripts\/ops\/l2_raw_match_data_write\.js/);
    assert.doesNotMatch(makefile, /^data-l2-raw-match-data-ingest-commit:/m);
});

test('no child_process spawn source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});

test('no fs write or mkdir source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('no ProductionHarvester/raw ingest commit import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no browser/proxy import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"].*(playwright|puppeteer|chromium|BrowserProvider|socks-proxy-agent)/);
});
