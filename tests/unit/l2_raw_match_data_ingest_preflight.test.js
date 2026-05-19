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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_match_data_ingest_preflight.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const PREVIEW_BODY_SHA256 = '8710a3524807d4682ab3c66386f9cd6b4d374fb6eee4f98a29d7f4a6683a162c';
const BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 2,
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
        networkAuthorization: true,
        livePreviewAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: 1,
        retry: 0,
        printBody: false,
        saveBody: false,
        commit: false,
        execute: false,
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
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${args.livePreviewAuthorization ? 'yes' : 'no'}`,
        `--allow-db-write=${args.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${args.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-matches-write=${args.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--allow-browser-runtime=${args.allowBrowserRuntime ? 'yes' : 'no'}`,
        `--allow-proxy-runtime=${args.allowProxyRuntime ? 'yes' : 'no'}`,
        `--concurrency=${args.concurrency}`,
        `--retry=${args.retry}`,
        `--print-body=${args.printBody ? 'yes' : 'no'}`,
        `--save-body=${args.saveBody ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
    ];
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
            source: 'web_infiltration',
            extractedAt: 'volatile',
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

function fakeDeps(overrides = {}) {
    return {
        previewPayloadResult: fakePreviewResult(overrides.preview || {}),
        targetMatchRows: targetMatchRows(),
        existingRawMatchDataRows: [],
        protectedTableBaseline: BASELINE,
        ...overrides,
    };
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

function assertInvalid(overrides, expectedPattern) {
    const gate = loadModuleFresh();
    const validation = gate.validatePreflightInput(validArgs(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), expectedPattern);
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

function fakeReadOnlyPool() {
    const queries = [];
    return {
        queries,
        async query(sql, values = []) {
            const text = String(sql || '');
            queries.push({ text, values });
            assert.match(text.trim(), /^SELECT/i);
            assert.doesNotMatch(text, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|BEGIN|COMMIT|ROLLBACK)\b/i);
            if (text.includes('UNION ALL')) {
                return {
                    rows: Object.entries(BASELINE).map(([table_name, rows]) => ({ table_name, rows })),
                };
            }
            if (text.includes('FROM raw_match_data')) {
                return { rows: [] };
            }
            if (text.includes('FROM matches')) {
                return { rows: targetMatchRows() };
            }
            throw new Error(`unexpected query: ${text}`);
        },
        async end() {},
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
        throw new Error(`${name} should not be called by l2_raw_match_data_ingest_preflight`);
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

test('valid input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePreflightInput(validArgs());
    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /unsupported source/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route/));
test('route unsupported fails', () => assertInvalid({ route: 'api_match_details' }, /unsupported route/));
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
test('network-authorization=no fails', () =>
    assertInvalid({ networkAuthorization: false }, /network-authorization=yes is required/));
test('live-preview-authorization=no fails', () =>
    assertInvalid({ livePreviewAuthorization: false }, /live-preview-authorization=yes is required/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('retry > 0 blocked', () => assertInvalid({ retry: 1 }, /retry > 0 is blocked/));
test('concurrency > 1 blocked', () => assertInvalid({ concurrency: 2 }, /concurrency > 1 is blocked/));
test('print-body=yes blocked', () => assertInvalid({ printBody: true }, /print-body=yes is blocked/));
test('save-body=yes blocked', () => assertInvalid({ saveBody: true }, /save-body=yes is blocked/));
test('browser/proxy allowed blocked', () => {
    assertInvalid({ allowBrowserRuntime: true }, /allow-browser-runtime=yes is blocked/);
    assertInvalid({ allowProxyRuntime: true }, /allow-proxy-runtime=yes is blocked/);
});

test('normalizeBooleanFlag and parseArgs handle fallback and spaced values', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.normalizeBooleanFlag('YES'), true);
    assert.equal(gate.normalizeBooleanFlag('off'), false);
    assert.equal(gate.normalizeBooleanFlag('maybe', false), false);
    assert.equal(gate.normalizeBooleanFlag('', true), true);
    assert.equal(gate.normalizeBooleanFlag(undefined), undefined);

    const args = gate.parseArgs(['orphan', '--source', 'fotmob', '--route', 'html_hydration', '--mystery', '--help']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.route, 'html_hydration');
    assert.equal(args.help, true);
    assert.deepEqual(args.unknown, ['orphan', 'mystery']);
});

test('validatePreflightInput reports missing required flags when omitted', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePreflightInput(
        validArgs({
            networkAuthorization: undefined,
            livePreviewAuthorization: undefined,
            allowDbWrite: undefined,
            allowRawMatchDataWrite: undefined,
            allowMatchesWrite: undefined,
            allowTraining: undefined,
            allowPrediction: undefined,
            printBody: undefined,
            saveBody: undefined,
        })
    );
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /missing network-authorization=yes/);
    assert.match(validation.errors.join('\n'), /missing live-preview-authorization=yes/);
    assert.match(validation.errors.join('\n'), /missing allow-db-write=no/);
    assert.match(validation.errors.join('\n'), /missing allow-raw-match-data-write=no/);
    assert.match(validation.errors.join('\n'), /missing allow-matches-write=no/);
    assert.match(validation.errors.join('\n'), /missing allow-training=no/);
    assert.match(validation.errors.join('\n'), /missing allow-prediction=no/);
    assert.match(validation.errors.join('\n'), /missing print-body=no/);
    assert.match(validation.errors.join('\n'), /missing save-body=no/);
});

test('validatePreflightInput reports missing teams and invalid numeric safety knobs', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePreflightInput(
        validArgs({
            homeTeam: '',
            awayTeam: '',
            concurrency: 'many',
            retry: 'later',
        })
    );
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /missing home-team/);
    assert.match(validation.errors.join('\n'), /missing away-team/);
    assert.match(validation.errors.join('\n'), /concurrency must be 1/);
    assert.match(validation.errors.join('\n'), /retry must be 0/);

    const missingNumeric = gate.validatePreflightInput(validArgs({ concurrency: undefined, retry: undefined }));
    assert.match(missingNumeric.errors.join('\n'), /concurrency must be 1/);
    assert.match(missingNumeric.errors.join('\n'), /retry must be 0/);
});

test('canonicalizeJson sorts object keys recursively', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.canonicalizeJson({ z: 1, a: { c: 3, b: 2 } }), '{"a":{"b":2,"c":3},"z":1}');
});

test('canonicalizeJson preserves array order', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.canonicalizeJson({ items: [{ b: 1, a: 2 }, { c: 3 }] }), '{"items":[{"a":2,"b":1},{"c":3}]}');
});

test('canonicalizeJson handles undefined and non-finite values', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.canonicalizeJson(undefined), undefined);
    assert.equal(
        gate.canonicalizeJson({
            z: undefined,
            a: [1, undefined, () => {}, Symbol('x'), Number.NaN, Number.POSITIVE_INFINITY],
            b: { y: undefined, x: 1 },
            c: Number.NaN,
            d: Number.POSITIVE_INFINITY,
            e: Number.NEGATIVE_INFINITY,
        }),
        '{"a":[1,null,null,null,null,null],"b":{"x":1},"c":null,"d":null,"e":null}'
    );
});

test('sha256CanonicalJson stable for equivalent objects', () => {
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
    const preview = fakePreviewResult();
    const rawData = gate.buildRawDataFromPreviewPayload(null, preview.summary, validArgs());
    assert.deepEqual(rawData.content, {});
    assert.deepEqual(rawData.general, {});
    assert.deepEqual(rawData.header, {});
    assert.equal(rawData.matchId, '4830746');
    assert.equal(rawData._meta.has_stats, false);
    assert.equal(rawData._meta.full_html_body_stored, false);
    assert.equal(rawData._meta.http_response_string_stored, false);
});

test('no existing row -> would_insert', () => {
    const gate = loadModuleFresh();
    const affected = gate.buildAffectedPreview({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        dataVersion: 'fotmob_html_hyd_v1',
        existingRows: [],
        rawDataHash: 'abc',
    });
    assert.equal(affected.decision, 'would_insert');
    assert.equal(affected.data_version, 'fotmob_html_hyd_v1');
    assert.match(affected.reason, /match_id,data_version/);
});

test('same existing data_hash -> would_skip', () => {
    const gate = loadModuleFresh();
    const affected = gate.buildAffectedPreview({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        existingRows: [{ data_hash: 'abc' }],
        rawDataHash: 'abc',
    });
    assert.equal(affected.decision, 'would_skip');
});

test('different existing data_hash -> would_update', () => {
    const gate = loadModuleFresh();
    const affected = gate.buildAffectedPreview({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        existingRows: [{ data_hash: 'old' }],
        rawDataHash: 'new',
    });
    assert.equal(affected.decision, 'would_update');
});

test('output preflight_only=true', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), fakeDeps());
    assert.equal(result.ok, true);
    assert.equal(result.preflight_only, true);
});

test('output would_write_raw_match_data=false', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), fakeDeps());
    assert.equal(result.would_write_raw_match_data, false);
});

test('output db_write_allowed_this_phase=false', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), fakeDeps());
    assert.equal(result.db_write_allowed_this_phase, false);
});

test('output body_printed=false/body_saved=false', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), fakeDeps());
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
});

test('protected baseline included', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), fakeDeps());
    assert.deepEqual(result.protected_table_baseline, BASELINE);
});

test('buildAffectedPreview treats empty existing hashes as null on update', () => {
    const gate = loadModuleFresh();
    const affected = gate.buildAffectedPreview({
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        existingRows: [{ data_hash: '' }],
        rawDataHash: 'new',
    });
    assert.equal(affected.decision, 'would_update');
    assert.equal(affected.existing_data_hash, null);
});

test('custom dependency functions are used without pool and array baselines', async () => {
    const gate = loadModuleFresh();
    const preview = fakePreviewResult();
    const rawData = gate.buildRawDataFromPreviewPayload(preview.payload, preview.summary, validArgs());
    const rawDataHash = gate.sha256CanonicalJson(rawData);

    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), {
        resolvePreviewPayload: async ({ input }) => {
            assert.equal(input.matchId, '53_20252026_4830746');
            return preview;
        },
        selectTargetMatch: async ({ input }) => {
            assert.equal(input.externalId, '4830746');
            return targetMatchRows();
        },
        selectExistingRawMatchData: async ({ input }) => {
            assert.equal(input.matchId, '53_20252026_4830746');
            assert.equal(input.dataVersion, 'fotmob_html_hyd_v1');
            return [
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_html_hyd_v1',
                    data_hash: rawDataHash,
                },
            ];
        },
        selectProtectedTableBaseline: async () => [
            { table_name: 'matches', rows: 10 },
            { table_name: 'raw_match_data', rows: 2 },
            { table_name: 'bookmaker_odds_history', rows: 2 },
            { table_name: 'l3_features', rows: 2 },
            { table_name: 'match_features_training', rows: 2 },
            { table_name: 'predictions', rows: 2 },
        ],
    });

    assert.equal(result.ok, true);
    assert.equal(result.existing_raw_match_data_found, true);
    assert.deepEqual(result.existing_raw_match_data_lookup.conflict_target, ['match_id', 'data_version']);
    assert.equal(result.would_skip, true);
    assert.deepEqual(result.protected_table_baseline, BASELINE);
});

test('buildProtectedTableBaseline handles row arrays and invalid input', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(
        gate.buildProtectedTableBaseline([
            { table_name: 'matches', rows: '10' },
            { table_name: 'raw_match_data', rows: '2' },
            { table_name: 'bookmaker_odds_history', rows: '2' },
            { table_name: 'l3_features', rows: '2' },
            { table_name: 'match_features_training', rows: '2' },
            { table_name: 'predictions', rows: '2' },
        ]),
        BASELINE
    );
    assert.deepEqual(gate.buildProtectedTableBaseline(null), {
        matches: 0,
        raw_match_data: 0,
        bookmaker_odds_history: 0,
        l3_features: 0,
        match_features_training: 0,
        predictions: 0,
    });
});

test('same hash output would_skip_count=1', async () => {
    const gate = loadModuleFresh();
    const preview = fakePreviewResult();
    const rawData = gate.buildRawDataFromPreviewPayload(preview.payload, preview.summary, validArgs());
    const rawHash = gate.sha256CanonicalJson(rawData);
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            preview,
            existingRawMatchDataRows: [
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_html_hyd_v1',
                    data_hash: rawHash,
                },
            ],
        })
    );
    assert.equal(result.would_skip, true);
    assert.equal(result.would_skip_count, 1);
});

test('different hash output would_update_count=1', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            existingRawMatchDataRows: [
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_html_hyd_v1',
                    data_hash: 'old',
                },
            ],
        })
    );
    assert.equal(result.would_update, true);
    assert.equal(result.would_update_count, 1);
});

test('Makefile preflight target can run via container target', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-raw-match-data-ingest-preflight:/m);
    assert.match(makefile, /scripts\/ops\/l2_raw_match_data_ingest_preflight\.js/);
    assert.doesNotMatch(makefile, /^data-l2-raw-match-data-ingest-commit:/m);
});

test('runCli uses fake route selector payload and fake read-only DB without fs writes or spawn', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const pool = fakeReadOnlyPool();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: fakeFetchImpl(),
        pool,
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.selected_route, 'html_hydration');
    assert.equal(result.payload.would_insert_count, 1);
    assert.equal(pool.queries.length, 3);
});

test('runCli returns non-zero for blocked DB write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowDbWrite: true }));
    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.match(result.payload.controlled_error, /allow-db-write=yes is blocked/);
});

test('runCli help returns usage without executing preflight', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--help'], fakeDeps());
    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 5\.15L2 is preflight-only/);
    assert.equal(result.payload, null);
});

test('auto route is accepted but selected route remains html_hydration', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs({ route: 'auto' }), fakeDeps());
    assert.equal(result.ok, true);
    assert.equal(result.requested_route, 'auto');
    assert.equal(result.route, 'html_hydration');
});

test('invalid preview summary returns controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
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
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /NO_VALID_ROUTE_PAYLOAD/);
    assert.match(result.controlled_error, /body_printed=true is blocked/);
    assert.match(result.controlled_error, /body_saved=true is blocked/);
    assert.match(result.controlled_error, /browser_used=true is blocked/);
    assert.match(result.controlled_error, /proxy_used=true is blocked/);
});

test('raw_data shape validation blocks missing payload keys', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            preview: {
                payload: {
                    matchId: '4830746',
                    content: null,
                    general: null,
                    header: null,
                    _meta: {},
                },
            },
        })
    );
    assert.equal(result.ok, true);
    assert.deepEqual(Object.keys(result.protected_table_baseline).sort(), Object.keys(BASELINE).sort());
});

test('target match mismatch returns controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            targetMatchRows: [
                {
                    match_id: 'wrong',
                    external_id: '4830746',
                    home_team: 'Angers',
                    away_team: 'Strasbourg',
                },
            ],
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /target match_id mismatch/);
});

test('target match SELECT validates missing row and target identity fields', async () => {
    const gate = loadModuleFresh();
    const missing = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            targetMatchRows: [],
        })
    );
    assert.equal(missing.ok, false);
    assert.match(missing.controlled_error, /target match SELECT expected exactly 1 row, got 0/);

    const mismatchedFields = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            targetMatchRows: [
                {
                    match_id: '53_20252026_4830746',
                    external_id: '999',
                    home_team: 'Paris',
                    away_team: 'Lens',
                },
            ],
        })
    );
    assert.equal(mismatchedFields.ok, false);
    assert.match(mismatchedFields.controlled_error, /target external_id mismatch/);
    assert.match(mismatchedFields.controlled_error, /target home_team must contain Angers/);
    assert.match(mismatchedFields.controlled_error, /target away_team must contain Strasbourg/);
});

test('multiple existing raw rows return controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            existingRawMatchDataRows: [
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_html_hyd_v1',
                    data_hash: 'a',
                },
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_html_hyd_v1',
                    data_hash: 'b',
                },
            ],
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /expected <=\s*1 row/);
});

test('existing raw row with wrong data_version returns controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            existingRawMatchDataRows: [
                {
                    match_id: '53_20252026_4830746',
                    data_version: 'fotmob_pageprops_v2',
                    data_hash: 'a',
                },
            ],
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /expected data_version fotmob_html_hyd_v1/);
});

test('existing raw rows must be an array', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), {
        previewPayloadResult: fakePreviewResult(),
        targetMatchRows: targetMatchRows(),
        protectedTableBaseline: BASELINE,
        selectExistingRawMatchData: async () => ({ data_hash: 'abc' }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /existing raw_match_data SELECT did not return an array/);
});

test('protected baseline mismatch returns controlled error', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(
        validArgs(),
        fakeDeps({
            protectedTableBaseline: {
                ...BASELINE,
                raw_match_data: 3,
            },
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /raw_match_data baseline expected 2, got 3/);
});

test('default pg pool path uses SELECT-only queries', async () => {
    const gate = loadModuleFresh();
    const pool = fakeReadOnlyPool();
    let ended = false;
    pool.end = async () => {
        ended = true;
    };
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), {
        previewPayloadResult: fakePreviewResult(),
        createPool: () => pool,
    });
    assert.equal(result.ok, true);
    assert.equal(ended, true);
    assert.equal(pool.queries.length, 3);
    const rawLookup = pool.queries.find(item => item.text.includes('FROM raw_match_data'));
    assert.match(rawLookup.text, /match_id = \$1\s+AND data_version = \$2/i);
    assert.deepEqual(rawLookup.values, ['53_20252026_4830746', 'fotmob_html_hyd_v1']);
});

test('recapture path uses fake fetch and does not save or print body', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), {
        fetchImpl: fakeFetchImpl(),
        targetMatchRows: targetMatchRows(),
        existingRawMatchDataRows: [],
        protectedTableBaseline: BASELINE,
    });
    assert.equal(result.ok, true);
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
    assert.equal(result.selected_route, 'html_hydration');
});

test('recapture path fails closed when fetch is unavailable', async t => {
    const originalFetch = global.fetch;
    global.fetch = undefined;
    t.after(() => {
        global.fetch = originalFetch;
    });

    const gate = loadModuleFresh();
    await assert.rejects(
        () =>
            gate.buildRawMatchDataIngestPreflight(validArgs(), {
                targetMatchRows: targetMatchRows(),
                existingRawMatchDataRows: [],
                protectedTableBaseline: BASELINE,
            }),
        /FETCH_UNAVAILABLE/
    );
});

test('recapture path fails closed when hydration payload cannot be parsed', async () => {
    const gate = loadModuleFresh();
    await assert.rejects(
        () =>
            gate.buildRawMatchDataIngestPreflight(validArgs(), {
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
                targetMatchRows: targetMatchRows(),
                existingRawMatchDataRows: [],
                protectedTableBaseline: BASELINE,
            }),
        /NEXT_DATA_PARSE_FAILED|NO_NEXT_DATA|__NEXT_DATA__/
    );
});

test('recapture path fails closed when selector captures no preview body', async () => {
    const gate = loadModuleFresh();
    await assert.rejects(
        () =>
            gate.buildRawMatchDataIngestPreflight(validArgs(), {
                fetchImpl: async () => ({
                    status: 200,
                    statusCode: 200,
                    ok: true,
                    url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
                    headers: {
                        get: () => 'text/html; charset=utf-8',
                    },
                    text: async () => '',
                }),
                runFotMobDetailRouteSelector: async () => ({
                    ok: true,
                    attempts: [],
                    selected_route: 'html_hydration',
                }),
                buildRouteSelectorPreviewSummary: () => ({
                    ok: true,
                    selected_route: 'html_hydration',
                    request_url: 'https://www.fotmob.com/match/4830746',
                    final_url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
                    http_status: 200,
                    hydration_parse_ok: true,
                    looks_like_valid_match_detail: true,
                }),
                targetMatchRows: targetMatchRows(),
                existingRawMatchDataRows: [],
                protectedTableBaseline: BASELINE,
            }),
        /NO_CAPTURED_PREVIEW_BODY|NO_NEXT_DATA|NEXT_DATA_PARSE_FAILED|INVALID_INPUT/
    );
});

test('CLI main catch branch emits safe controlled error payload', () => {
    const tempDir = fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'l2-ingest-cli-'));
    const preloadPath = path.join(tempDir, 'block-fetch.js');
    fs.writeFileSync(
        preloadPath,
        "global.fetch = async () => { throw new Error('SAFE_TEST_FETCH_BLOCKED'); };\n",
        'utf8'
    );
    const result = childProcess.spawnSync(process.execPath, ['--require', preloadPath, SCRIPT_PATH, ...cliArgs()], {
        cwd: tempDir,
        encoding: 'utf8',
        env: {
            ...process.env,
            DB_HOST: '127.0.0.1',
            DB_PORT: '1',
        },
    });

    assert.notEqual(result.status, 0);
    const output = JSON.parse(result.stdout);
    assert.equal(output.preflight_only, true);
    assert.equal(output.ok, false);
    assert.equal(output.raw_match_data_write_allowed_this_phase, false);
    assert.equal(output.db_write_allowed_this_phase, false);
    assert.equal(output.would_write_raw_match_data, false);
    assert.equal(output.body_printed, false);
    assert.equal(output.body_saved, false);
    assert.equal(result.stdout.includes('<html>'), false);
    assert.equal(result.stdout.includes('__NEXT_DATA__'), false);
});

test('no fs write / mkdir source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('no child_process spawn source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});

test('no DB write occurs with fake pool', async () => {
    const gate = loadModuleFresh();
    const pool = fakeReadOnlyPool();
    const result = await gate.buildRawMatchDataIngestPreflight(validArgs(), {
        previewPayloadResult: fakePreviewResult(),
        pool,
    });
    assert.equal(result.ok, true);
    assert.equal(pool.queries.length, 3);
});

test('no ProductionHarvester / raw ingest commit import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no browser/proxy import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"].*(playwright|puppeteer|chromium|BrowserProvider|socks-proxy-agent)/);
});
