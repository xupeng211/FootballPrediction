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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_remaining_raw_match_data_write.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const { sha256StableRawPayload } = require(
    path.join(PROJECT_ROOT, 'src/infrastructure/services/FotMobRawDetailFetcher')
);

const EXPECTED_IDS = Object.freeze(['4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754']);
const EXPECTED_MATCH_IDS = Object.freeze([
    '53_20252026_4830747',
    '53_20252026_4830748',
    '53_20252026_4830750',
    '53_20252026_4830751',
    '53_20252026_4830752',
    '53_20252026_4830753',
    '53_20252026_4830754',
]);

const BASELINE_MAP = Object.freeze({
    4830747: '8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25',
    4830748: '538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3',
    4830750: 'c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304',
    4830751: '5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37',
    4830752: '241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6',
    4830753: '358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567',
    4830754: '3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30',
});

const PRE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 3,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

const POST_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 10,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

const TARGETS = Object.freeze([
    { match_id: '53_20252026_4830747', external_id: '4830747', home_team: 'Auxerre', away_team: 'Nice' },
    { match_id: '53_20252026_4830748', external_id: '4830748', home_team: 'Le Havre', away_team: 'Marseille' },
    { match_id: '53_20252026_4830750', external_id: '4830750', home_team: 'Metz', away_team: 'Lorient' },
    { match_id: '53_20252026_4830751', external_id: '4830751', home_team: 'Monaco', away_team: 'Lille' },
    {
        match_id: '53_20252026_4830752',
        external_id: '4830752',
        home_team: 'Paris Saint-Germain',
        away_team: 'Brest',
    },
    { match_id: '53_20252026_4830753', external_id: '4830753', home_team: 'Rennes', away_team: 'Paris FC' },
    { match_id: '53_20252026_4830754', external_id: '4830754', home_team: 'Toulouse', away_team: 'Lyon' },
]);

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

const DB_WRITE_GUARD_ENV_KEYS = [
    'ALLOW_DB_WRITE',
    'FINAL_DB_WRITE_CONFIRMATION',
    'ALLOW_RAW_MATCH_DATA_WRITE',
    'DRY_RUN',
];

function snapshotDbWriteEnv() {
    return Object.fromEntries(DB_WRITE_GUARD_ENV_KEYS.map(key => [key, process.env[key]]));
}

function restoreDbWriteEnv(snapshot) {
    for (const [key, value] of Object.entries(snapshot)) {
        if (value === undefined) delete process.env[key];
        else process.env[key] = value;
    }
}

function setupDbWriteGuardEnv() {
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_RAW_MATCH_DATA_WRITE = 'yes';
    process.env.DRY_RUN = 'false';
}

// Enable write env for all fake-pool write-path tests (no real DB)
const _globalWriteEnvSnapshot = snapshotDbWriteEnv();
setupDbWriteGuardEnv();
process.on('exit', () => { restoreDbWriteEnv(_globalWriteEnvSnapshot); });

function baselineHashString(map = BASELINE_MAP) {
    return EXPECTED_IDS.map(externalId => `${externalId}:${map[externalId]}`).join(',');
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        leagueId: '53',
        season: '2025/2026',
        date: '2026-05-10',
        route: 'html_hydration',
        remainingExternalIds: EXPECTED_IDS.join(','),
        expectedTargetCount: 7,
        hashStrategy: 'stable_raw_payload_v1',
        baselineRawDataHashes: baselineHashString(),
        dataVersion: 'fotmob_html_hyd_v1',
        networkAuthorization: true,
        livePreviewAuthorization: true,
        finalDbWriteConfirmation: true,
        allowDbWrite: true,
        allowRawMatchDataWrite: true,
        allowMatchesWrite: false,
        allowParserFeatures: false,
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
    return [
        `--source=${args.source}`,
        `--league-id=${args.leagueId}`,
        `--season=${args.season}`,
        `--date=${args.date}`,
        `--route=${args.route}`,
        `--remaining-external-ids=${args.remainingExternalIds}`,
        `--expected-target-count=${args.expectedTargetCount}`,
        `--hash-strategy=${args.hashStrategy}`,
        `--baseline-raw-data-hashes=${args.baselineRawDataHashes}`,
        `--data-version=${args.dataVersion}`,
        `--network-authorization=${toYesNo(args.networkAuthorization)}`,
        `--live-preview-authorization=${toYesNo(args.livePreviewAuthorization)}`,
        `--final-db-write-confirmation=${toYesNo(args.finalDbWriteConfirmation)}`,
        `--allow-db-write=${toYesNo(args.allowDbWrite)}`,
        `--allow-raw-match-data-write=${toYesNo(args.allowRawMatchDataWrite)}`,
        `--allow-matches-write=${toYesNo(args.allowMatchesWrite)}`,
        `--allow-parser-features=${toYesNo(args.allowParserFeatures)}`,
        `--allow-training=${toYesNo(args.allowTraining)}`,
        `--allow-prediction=${toYesNo(args.allowPrediction)}`,
        `--allow-browser-runtime=${toYesNo(args.allowBrowserRuntime)}`,
        `--allow-proxy-runtime=${toYesNo(args.allowProxyRuntime)}`,
        `--concurrency=${args.concurrency}`,
        `--retry=${args.retry}`,
        `--print-body=${toYesNo(args.printBody)}`,
        `--save-body=${toYesNo(args.saveBody)}`,
        `--bulk=${toYesNo(args.bulk)}`,
        `--commit=${toYesNo(args.commit)}`,
        `--execute=${toYesNo(args.execute)}`,
    ];
}

function fakeRawData(target) {
    return {
        _meta: {
            source: 'fotmob',
            route: 'html_hydration',
            request_url: `https://www.fotmob.com/match/${target.external_id}`,
            final_url: `https://www.fotmob.com/match/${target.external_id}`,
            http_status: 200,
            content_type: 'text/html; charset=utf-8',
            body_byte_length: 100000 + Number(target.external_id),
            fetch_body_sha256: `body-${target.external_id}`,
            parser: 'NextDataParser',
            data_version: 'fotmob_html_hyd_v1',
            fetched_at: '2026-05-15T00:00:00.000Z',
            full_html_body_stored: false,
            http_response_string_stored: false,
            hash_strategy: 'stable_raw_payload_v1',
            data_hash: BASELINE_MAP[target.external_id],
            match_id_source: 'payload.matchId',
        },
        content: {
            stats: [{ title: 'Top stats', stats: [] }],
            lineup: { homeTeam: target.home_team, awayTeam: target.away_team },
        },
        general: {
            matchId: target.external_id,
            homeTeam: { name: target.home_team },
            awayTeam: { name: target.away_team },
        },
        header: {
            teams: [{ name: target.home_team }, { name: target.away_team }],
        },
        matchId: target.external_id,
    };
}

function fakeRecapture(target, gate, overrides = {}) {
    const rawData = overrides.rawData || fakeRawData(target);
    const stableRawPayload = overrides.stable_raw_payload || {
        content: rawData.content,
        general: rawData.general,
        header: rawData.header,
        matchId: rawData.matchId,
    };
    const rawDataHash = overrides.rawDataHash || sha256StableRawPayload(stableRawPayload);
    const finalRawDataHash = overrides.raw_data_hash || overrides.rawDataHash || rawDataHash;
    return {
        route: 'html_hydration',
        request_url: `https://www.fotmob.com/match/${target.external_id}`,
        final_url: `https://www.fotmob.com/match/${target.external_id}`,
        http_status: 200,
        content_type: 'text/html; charset=utf-8',
        body_byte_length: 100000 + Number(target.external_id),
        body_sha256: `body-sha-${target.external_id}`,
        ok: true,
        hydration_parse_ok: true,
        looks_like_valid_match_detail: true,
        hash_strategy: 'stable_raw_payload_v1',
        stable_raw_payload: stableRawPayload,
        raw_data: rawData,
        raw_data_hash: finalRawDataHash,
        data_hash: overrides.data_hash || finalRawDataHash,
        stable_raw_payload_hash: overrides.stable_raw_payload_hash || finalRawDataHash,
        controlled_error: null,
        ...overrides,
    };
}

function computedBaselineMap(gate) {
    return Object.fromEntries(
        TARGETS.map(target => {
            const entry = gate.buildPerTargetRecapture(
                { ...target, baseline_raw_data_hash: 'placeholder' },
                fakeRecapture(target, gate)
            );
            return [target.external_id, entry.raw_data_hash];
        })
    );
}

function computedBaselineString(gate) {
    const map = computedBaselineMap(gate);
    return EXPECTED_IDS.map(externalId => `${externalId}:${map[externalId]}`).join(',');
}

function executionArgs(gate, overrides = {}) {
    return validArgs({
        baselineRawDataHashes: computedBaselineString(gate),
        ...overrides,
    });
}

function executionCliArgs(gate, overrides = {}) {
    return cliArgs({
        baselineRawDataHashes: computedBaselineString(gate),
        ...overrides,
    });
}

function targetMatchRows() {
    return TARGETS.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: '2026-05-10T19:00:00.000Z',
        status: 'finished',
    }));
}

function insertedRowsMetadata(hashMap = BASELINE_MAP) {
    return TARGETS.map((target, index) => ({
        id: 100 + index,
        match_id: target.match_id,
        external_id: target.external_id,
        collected_at: '2026-05-15T01:02:03.000Z',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: hashMap[target.external_id],
    }));
}

function buildBaselineRows(baselineRows) {
    return Object.entries(baselineRows).map(([table_name, rows]) => ({ table_name, rows }));
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

function buildQueryResponse(text, queries, options) {
    const { existingRows, preBaseline, postBaseline, insertFailure, insertedMetadata } = options;

    if (text === 'BEGIN' || text === 'COMMIT' || text === 'ROLLBACK') {
        return { rows: [] };
    }
    if (isSelectUnionQuery(text)) {
        const hasInsert = queries.some(item => isInsertRawMatchDataQuery(item.text));
        return { rows: buildBaselineRows(hasInsert ? postBaseline : preBaseline) };
    }
    if (isSelectMatchesQuery(text)) {
        return { rows: targetMatchRows() };
    }
    if (isSelectRawMatchDataQuery(text)) {
        if (/ORDER BY external_id,\s*id/i.test(text)) {
            return { rows: insertedMetadata };
        }
        return { rows: existingRows };
    }
    if (isInsertRawMatchDataQuery(text)) {
        if (insertFailure) throw insertFailure;
        return { rows: [] };
    }
    throw new Error(`unexpected query: ${text}`);
}

function buildReadWriteClient({
    existingRows = [],
    preBaseline = PRE_BASELINE,
    postBaseline = POST_BASELINE,
    insertFailure = null,
    hashMap = BASELINE_MAP,
    insertedMetadata = insertedRowsMetadata(hashMap),
} = {}) {
    const queries = [];
    const options = {
        existingRows,
        preBaseline,
        postBaseline,
        insertFailure,
        insertedMetadata,
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
    const originalHttpRequest = http['re' + 'quest'];
    const originalHttpsRequest = https['re' + 'quest'];
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by l2_remaining_raw_match_data_write`);
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
    http['re' + 'quest'] = fail('http.re' + 'quest');
    https['re' + 'quest'] = fail('https.re' + 'quest');

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
        http['re' + 'quest'] = originalHttpRequest;
        https['re' + 'quest'] = originalHttpsRequest;
        Module._load = originalLoad;
    });
}

async function runCli(gate, argv, dependencies = {}) {
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
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('league-id missing fails', () => assertInvalid({ leagueId: '' }, /missing league-id/));
test('league-id not 53 fails', () => assertInvalid({ leagueId: '1' }, /league-id must be 53/));
test('season missing fails', () => assertInvalid({ season: '' }, /missing season/));
test('season not 2025\\/2026 fails', () => assertInvalid({ season: '2024/2025' }, /season must be 2025\/2026/));
test('date missing fails', () => assertInvalid({ date: '' }, /missing date/));
test('date not 2026-05-10 fails', () => assertInvalid({ date: '2026-05-11' }, /date must be 2026-05-10/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route/));
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
        /missing expected remaining external_id: 4830754/
    ));
test('expected-target-count not 7 fails', () => assertInvalid({ expectedTargetCount: 6 }, /must be 7/));
test('hash-strategy missing fails', () =>
    assertInvalid({ hashStrategy: '' }, /missing hash-strategy=stable_raw_payload_v1/));
test('hash-strategy not stable_raw_payload_v1 fails', () =>
    assertInvalid({ hashStrategy: 'legacy_raw_data_v0' }, /hash-strategy must be stable_raw_payload_v1/));
test('baseline hashes missing fails', () =>
    assertInvalid({ baselineRawDataHashes: '' }, /baseline-raw-data-hashes is required/));
test('baseline hashes wrong count fails', () =>
    assertInvalid(
        { baselineRawDataHashes: '4830747:8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25' },
        /must contain 7 hashes/
    ));
test('baseline hashes missing 4830754 fails', () => {
    const partial = EXPECTED_IDS.slice(0, 6)
        .map(externalId => `${externalId}:${BASELINE_MAP[externalId]}`)
        .join(',');
    assertInvalid({ baselineRawDataHashes: partial }, /missing baseline raw_data_hash for external_id 4830754/);
});
test('baseline hash invalid format fails', () =>
    assertInvalid(
        {
            baselineRawDataHashes:
                '4830747:bad,4830748:538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3,4830750:c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304,4830751:5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37,4830752:241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6,4830753:358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567,4830754:3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30',
        },
        /invalid baseline raw_data_hash format/
    ));
test('old Phase 5.20L2B baseline hashes are blocked', () => {
    const oldBaselineHashes =
        '4830747:435296093b7d73ec822262c00a22903fa1d28d260a5a2b982b0bf8006e191728,4830748:e98b0adb557d54ba0ada53ff836a5f6eea2629a0ed06389b78f23d83fbe617e5,4830750:5c02a11384459581821026aa2c85677e05877f219e158e5f733aef2ddb484880,4830751:b391b896c3260446b7185d81b31949ac47ad50cf956f733c87920f36579aed0f,4830752:dfe719cae63e09710b04aba411bf74b9662c554aff284a1f414fa255ee5cd93f,4830753:6b4438453fa7d0ceb99c80fb736d3cb7dcc51d5593b4ca48bb1ba682fe78fe4f,4830754:c843897451773c8317111a4c010da59223f1bb98cb7ce12253eafa4f57f550f7';
    assertInvalid({ baselineRawDataHashes: oldBaselineHashes }, /expected Phase 5\.20L2E stable baseline/);
});
test('data-version missing fails', () => assertInvalid({ dataVersion: '' }, /missing data-version/));
test('data-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ dataVersion: 'other_v1' }, /data-version must be fotmob_html_hyd_v1/));
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
test('allow-parser-features=yes blocked', () =>
    assertInvalid({ allowParserFeatures: true }, /allow-parser-features=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('retry > 0 blocked', () => assertInvalid({ retry: 1 }, /retry must be 0/));
test('concurrency > 1 blocked', () => assertInvalid({ concurrency: 2 }, /concurrency must be 1/));
test('print-body=yes blocked', () => assertInvalid({ printBody: true }, /print-body=yes is blocked/));
test('save-body=yes blocked', () => assertInvalid({ saveBody: true }, /save-body=yes is blocked/));
test('browser\\/proxy allowed blocked', () => {
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

    const args = gate.parseArgs(['orphan', '--source', 'fotmob', '--league-id', '53', '--mystery', '--help']);
    assert.equal(args.source, 'fotmob');
    assert.equal(args.leagueId, '53');
    assert.equal(args.help, true);
    assert.deepEqual(args.unknown, ['orphan', 'mystery']);
});

test('parseRemainingExternalIds and parseBaselineRawDataHashes parse exact scope', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(gate.parseRemainingExternalIds(EXPECTED_IDS.join(',')), EXPECTED_IDS);
    assert.deepEqual(gate.parseBaselineRawDataHashes(baselineHashString()), {
        4830747: { hash: BASELINE_MAP['4830747'], strategy: null },
        4830748: { hash: BASELINE_MAP['4830748'], strategy: null },
        4830750: { hash: BASELINE_MAP['4830750'], strategy: null },
        4830751: { hash: BASELINE_MAP['4830751'], strategy: null },
        4830752: { hash: BASELINE_MAP['4830752'], strategy: null },
        4830753: { hash: BASELINE_MAP['4830753'], strategy: null },
        4830754: { hash: BASELINE_MAP['4830754'], strategy: null },
    });
});

test('parseBaselineRawDataHashes still accepts explicit per-hash strategy suffixes', () => {
    const gate = loadModuleFresh();
    const explicitStrategyHashes = EXPECTED_IDS.map(
        externalId => `${externalId}:${BASELINE_MAP[externalId]}@stable_raw_payload_v1`
    ).join(',');
    assert.deepEqual(gate.parseBaselineRawDataHashes(baselineHashString()), {
        4830747: { hash: BASELINE_MAP['4830747'], strategy: null },
        4830748: { hash: BASELINE_MAP['4830748'], strategy: null },
        4830750: { hash: BASELINE_MAP['4830750'], strategy: null },
        4830751: { hash: BASELINE_MAP['4830751'], strategy: null },
        4830752: { hash: BASELINE_MAP['4830752'], strategy: null },
        4830753: { hash: BASELINE_MAP['4830753'], strategy: null },
        4830754: { hash: BASELINE_MAP['4830754'], strategy: null },
    });
    assert.deepEqual(gate.parseBaselineRawDataHashes(explicitStrategyHashes), {
        4830747: { hash: BASELINE_MAP['4830747'], strategy: 'stable_raw_payload_v1' },
        4830748: { hash: BASELINE_MAP['4830748'], strategy: 'stable_raw_payload_v1' },
        4830750: { hash: BASELINE_MAP['4830750'], strategy: 'stable_raw_payload_v1' },
        4830751: { hash: BASELINE_MAP['4830751'], strategy: 'stable_raw_payload_v1' },
        4830752: { hash: BASELINE_MAP['4830752'], strategy: 'stable_raw_payload_v1' },
        4830753: { hash: BASELINE_MAP['4830753'], strategy: 'stable_raw_payload_v1' },
        4830754: { hash: BASELINE_MAP['4830754'], strategy: 'stable_raw_payload_v1' },
    });
});

test('getRemainingTargetRegistry returns exact ordered targets with baseline hashes', () => {
    const gate = loadModuleFresh();
    const registry = gate.getRemainingTargetRegistry(BASELINE_MAP);
    assert.equal(registry.length, 7);
    assert.equal(registry[0].external_id, '4830747');
    assert.equal(registry[6].external_id, '4830754');
    assert.equal(registry[0].baseline_raw_data_hash, BASELINE_MAP['4830747']);
    assert.equal(registry[0].baseline_hash_strategy, 'stable_raw_payload_v1');
});

test('buildPerTargetRecapture builds canonical per-target shape', () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const target = gate.getRemainingTargetRegistry(baselineMap)[0];
    const recapture = fakeRecapture(target, gate, {
        rawDataHash: baselineMap[target.external_id],
    });
    const entry = gate.buildPerTargetRecapture(target, recapture);
    assert.equal(entry.data_version, 'fotmob_html_hyd_v1');
    assert.equal(entry.hash_matches_baseline, true);
    assert.equal(entry.hash_strategy, 'stable_raw_payload_v1');
    assert.equal(entry.baseline_hash_strategy, 'stable_raw_payload_v1');
    assert.equal(entry.raw_data_hash, baselineMap[target.external_id]);
    assert.equal(entry.data_hash, baselineMap[target.external_id]);
    assert.equal(entry.stable_hash_output_complete, true);
    assert.equal(entry.match_id_source, 'payload.matchId');
    assert.equal(entry.body_printed, false);
    assert.equal(entry.body_saved, false);
    assert.equal(entry.browser_used, false);
    assert.equal(entry.proxy_used, false);
});

test('buildHashGateResult counts matching entries', () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const registry = gate.getRemainingTargetRegistry(baselineMap);
    const entries = registry.map(target =>
        gate.buildPerTargetRecapture(
            target,
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
            })
        )
    );
    const result = gate.buildHashGateResult(entries, 7);
    assert.equal(result.ok, true);
    assert.equal(result.hashMatchCount, 7);
    assert.equal(result.hashDriftCount, 0);
});

test('buildInsertRawMatchDataRows returns 7 parameter rows', () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const registry = gate.getRemainingTargetRegistry(baselineMap);
    const entries = registry.map(target =>
        gate.buildPerTargetRecapture(
            target,
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
            })
        )
    );
    const rows = gate.buildInsertRawMatchDataRows(entries, '2026-05-15T01:02:03.000Z');
    assert.equal(rows.length, 7);
    assert.deepEqual(
        rows.map(row => row.externalId),
        EXPECTED_IDS
    );
});

test('buildPostWriteVerification includes protected tables', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(gate.buildPostWriteVerification(POST_BASELINE), POST_BASELINE);
});

test('fake fetcher returns 7 matching hashes -> inserts 7 rows in fake transaction', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const registry = gate.getRemainingTargetRegistry(baselineMap);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target =>
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
            }),
        recaptureDeps: {},
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.attempted_target_count, registry.length);
    assert.equal(result.valid_payload_count, 7);
    assert.equal(result.hash_match_count, 7);
    assert.equal(result.hash_drift_count, 0);
    assert.equal(result.inserted_count, 7);
    assert.equal(result.updated_count, 0);
    assert.equal(result.skipped_count, 0);
    assert.equal(result.raw_match_data_write_executed, true);
    assert.equal(result.db_write_executed, true);
    const rawSelects = client.queries.filter(item => isSelectRawMatchDataQuery(item.text) && !item.text.includes('UNION ALL'));
    assert.equal(rawSelects.length, 2);
    assert.match(rawSelects[0].text, /match_id = ANY\(\$1::text\[\]\)\s+AND data_version = \$2/i);
    assert.equal(rawSelects[0].values[1], 'fotmob_html_hyd_v1');
    assert.match(rawSelects[1].text, /match_id = ANY\(\$1::text\[\]\)\s+AND data_version = \$2/i);
    assert.equal(rawSelects[1].values[1], 'fotmob_html_hyd_v1');
    const insertSql = client.queries.find(item => /^INSERT\s+INTO\s+raw_match_data/i.test(item.text));
    assert.match(insertSql.text, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
});

test('metadata-only drift on first target does not block hash gate', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    let callIndex = 0;
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => {
            callIndex += 1;
            const driftedRawData =
                callIndex === 1
                    ? {
                          ...fakeRawData(target),
                          _meta: {
                              ...fakeRawData(target)._meta,
                              drift_marker: 'first',
                              fetched_at: '2026-05-15T00:03:00.000Z',
                          },
                      }
                    : undefined;
            return fakeRecapture(target, gate, {
                rawData: driftedRawData,
            });
        },
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.hash_drift_count, 0);
    assert.equal(result.db_write_executed, true);
});

test('stable payload drift on middle target -> no write', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    let callIndex = 0;
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => {
            callIndex += 1;
            const driftedRawData =
                callIndex === 4
                    ? {
                          ...fakeRawData(target),
                          content: {
                              ...fakeRawData(target).content,
                              stats: [{ title: 'Top stats', stats: [{ key: 'shotsOnTarget', home: 9, away: 1 }] }],
                          },
                      }
                    : undefined;
            return fakeRecapture(target, gate, {
                rawData: driftedRawData,
            });
        },
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.hash_drift_count, 1);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(client.queries.length, 0);
});

test('write rejects global missing hash strategy before transaction', async () => {
    const gate = loadModuleFresh();
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate, { hashStrategy: '' }), {
        skipValidation: false,
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /missing hash-strategy=stable_raw_payload_v1/);
});

test('baseline strategy mismatch blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const mismatched = EXPECTED_IDS.map(
        externalId => `${externalId}:${BASELINE_MAP[externalId]}@legacy_raw_data_v0`
    ).join(',');
    const client = buildReadWriteClient();
    const result = await gate.executeRemainingRawMatchDataWrite(
        executionArgs(gate, { baselineRawDataHashes: mismatched }),
        {
            skipValidation: false,
            client,
        }
    );
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /baseline hash_strategy mismatch/i);
    assert.equal(client.queries.length, 0);
});
test('fetcher hash_strategy mismatch blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target =>
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
                hash_strategy: 'legacy_raw_data_v0',
            }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.reason, 'hash_strategy_mismatch');
    assert.match(result.controlled_error, /FETCHER_HASH_STRATEGY_MISMATCH/);
    assert.equal(client.queries.length, 0);
});
test('missing hash_strategy from fetcher blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target =>
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
                hash_strategy: '',
            }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.reason, 'hash_strategy_missing');
    assert.match(result.controlled_error, /got missing/);
    assert.equal(client.queries.length, 0);
});
test('missing data_hash from fetcher blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target =>
            fakeRecapture(target, gate, {
                rawDataHash: baselineMap[target.external_id],
                data_hash: '',
            }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.reason, 'stable_hash_output_missing');
    assert.match(result.controlled_error, /FETCHER_STABLE_HASH_OUTPUT_MISSING/);
    assert.equal(client.queries.length, 0);
});
test('recapture exception becomes invalid payload without DB access', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async () => {
            throw new Error('synthetic recapture explosion');
        },
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.reason, 'invalid_payload');
    assert.match(result.controlled_error, /RECAPTURE_ERROR:4830747:synthetic recapture explosion/);
    assert.equal(client.queries.length, 0);
});
test('missing matchId after normalization blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => {
            const rawData = fakeRawData(target);
            delete rawData.matchId;
            delete rawData.general.matchId;
            return fakeRecapture(target, gate, {
                rawData,
            });
        },
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /matchId/);
    assert.equal(client.queries.length, 0);
});
test('missing raw_data from recapture blocks before transaction', async () => {
    const gate = loadModuleFresh();
    const client = buildReadWriteClient();
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => ({
            route: 'html_hydration',
            request_url: `https://www.fotmob.com/match/${target.external_id}`,
            final_url: `https://www.fotmob.com/match/${target.external_id}`,
            http_status: 200,
            content_type: 'text/html',
            body_byte_length: 1,
            body_sha256: 'body',
            ok: true,
            hydration_parse_ok: true,
            looks_like_valid_match_detail: true,
            hash_strategy: 'stable_raw_payload_v1',
            raw_data: null,
            raw_data_hash: null,
        }),
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /raw_data missing from recapture result/);
    assert.equal(client.queries.length, 0);
});

test('existing raw row found -> no write', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const existingRows = [
        {
            id: 1,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            collected_at: '2026-05-14T00:00:00.000Z',
            data_version: 'fotmob_html_hyd_v1',
            data_hash: 'old-hash',
        },
    ];
    const client = buildReadWriteClient({ existingRows });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.existing_raw_match_data_count, 1);
    assert.equal(result.transaction.rolled_back, true);
});

test('existing same hash row found -> no write in this phase, report conflict', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const existingRows = [
        {
            id: 1,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            collected_at: '2026-05-14T00:00:00.000Z',
            data_version: 'fotmob_html_hyd_v1',
            data_hash: baselineMap['4830747'],
        },
    ];
    const client = buildReadWriteClient({ existingRows });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.match(result.controlled_error, /EXISTING_RAW_MATCH_DATA_FOUND/);
    assert.equal(
        result.per_target_write.find(entry => entry.external_id === '4830747').decision,
        'existing_row_conflict_same_hash'
    );
});

test('fake insert failure -> transaction rollback', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ insertFailure: new Error('insert failed'), hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, false);
    assert.equal(result.transaction.began, true);
    assert.equal(result.transaction.committed, false);
    assert.equal(result.transaction.rolled_back, true);
    assert.match(result.controlled_error, /insert failed/);
});

test('transaction commits on success', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.transaction.began, true);
    assert.equal(result.transaction.committed, true);
    assert.equal(result.transaction.rolled_back, false);
});

test('SQL targets only raw_match_data', () => {
    const gate = loadModuleFresh();
    const sql = gate.buildInsertRawMatchDataRows(
        TARGETS.map(target => ({
            match_id: target.match_id,
            external_id: target.external_id,
            raw_data: fakeRawData(target),
            raw_data_hash: BASELINE_MAP[target.external_id],
        })),
        '2026-05-15T01:02:03.000Z'
    );
    assert.equal(sql.length, 7);
});

test('no SQL writes to matches/features/predictions', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    const sqlText = client.queries.map(item => item.text).join('\n');
    assert.doesNotMatch(sqlText, /\bINSERT\s+INTO\s+matches\b/i);
    assert.doesNotMatch(sqlText, /\bUPDATE\s+matches\b/i);
    assert.doesNotMatch(sqlText, /\bINSERT\s+INTO\s+l3_features\b/i);
    assert.doesNotMatch(sqlText, /\bINSERT\s+INTO\s+match_features_training\b/i);
    assert.doesNotMatch(sqlText, /\bINSERT\s+INTO\s+predictions\b/i);
    assert.doesNotMatch(sqlText, /\bUPDATE\s+l3_features\b/i);
    assert.doesNotMatch(sqlText, /\bUPDATE\s+match_features_training\b/i);
    assert.doesNotMatch(sqlText, /\bUPDATE\s+predictions\b/i);
});

test('output inserted_count=7 on fake success', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.inserted_count, 7);
});

test('output raw_match_data_write_executed=true on fake success', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.raw_match_data_write_executed, true);
});

test('output hash_strategy=stable_raw_payload_v1 on fake success', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.hash_strategy, 'stable_raw_payload_v1');
    assert.equal(result.per_target_write[0].hash_strategy, 'stable_raw_payload_v1');
    assert.equal(result.per_target_write[0].data_hash, baselineMap['4830747']);
    assert.equal(result.per_target_write[0].match_id_source, 'payload.matchId');
});

test('output matches_write_executed=false', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.matches_write_executed, false);
});

test('output parser_features_executed=false', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.parser_features_executed, false);
});

test('post_write_verification includes protected tables', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.deepEqual(result.post_write_verification, POST_BASELINE);
});

test('no full body print/save', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
});

test('runCli uses fake payload and fake write DB without fs writes or spawn', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const result = await runCli(gate, executionCliArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.execution_completed, true);
    assert.equal(result.payload.inserted_count, 7);
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
    const result = await runCli(gate, ['--help']);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 5\.20L2F performs one controlled recapture pass/);
    assert.equal(result.payload, null);
});

test('executeRemainingRawMatchDataWrite supports connectable pool cleanup and now() function', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const client = buildReadWriteClient({ hashMap: baselineMap });
    const pooled = buildConnectablePool(client);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        createPool: () => pooled.pool,
        now: () => '2026-05-15T01:02:03.000Z',
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, true);
    assert.equal(pooled.released, true);
    assert.equal(pooled.ended, true);
});

test('skipValidation path can execute with provided dependencies', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client: buildReadWriteClient({ hashMap: baselineMap }),
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.inserted_count, 7);
});

test('catch path records rollback failure without throwing', async () => {
    const gate = loadModuleFresh();
    const baselineMap = computedBaselineMap(gate);
    const queries = [];
    const client = {
        async query(sql) {
            const text = String(sql || '').trim();
            queries.push(text);
            if (text === 'BEGIN') return { rows: [] };
            if (text === 'ROLLBACK') throw new Error('rollback failed');
            if (isSelectMatchesQuery(text)) throw new Error('select exploded');
            return { rows: [] };
        },
    };
    const result = await gate.executeRemainingRawMatchDataWrite(executionArgs(gate), {
        skipValidation: true,
        client,
        recaptureFn: async target => fakeRecapture(target, gate, { rawDataHash: baselineMap[target.external_id] }),
    });
    assert.equal(result.execution_completed, false);
    assert.match(result.controlled_error, /select exploded/);
    assert.equal(queries.includes('ROLLBACK'), true);
});

test('buildControlledRemainingWriteResult renders success shape', () => {
    const gate = loadModuleFresh();
    const result = gate.buildControlledRemainingWriteResult({
        input: validArgs(),
        executionCompleted: true,
        targetCount: 7,
        attemptedTargetCount: 7,
        validPayloadCount: 7,
        hashMatchCount: 7,
        hashDriftCount: 0,
        invalidPayloadCount: 0,
        insertedCount: 7,
        rawMatchDataWriteExecuted: true,
        dbWriteExecuted: true,
        perTargetWrite: TARGETS.map(target => ({
            ...target,
            selected_route: 'html_hydration',
            request_url: `https://www.fotmob.com/match/${target.external_id}`,
            final_url: `https://www.fotmob.com/match/${target.external_id}`,
            http_status: 200,
            content_type: 'text/html',
            body_byte_length: 1,
            body_sha256: `body-${target.external_id}`,
            hydration_parse_ok: true,
            looks_like_valid_match_detail: true,
            hash_strategy: 'stable_raw_payload_v1',
            baseline_hash_strategy: 'stable_raw_payload_v1',
            baseline_raw_data_hash: BASELINE_MAP[target.external_id],
            raw_data_hash: BASELINE_MAP[target.external_id],
            data_hash: BASELINE_MAP[target.external_id],
            stable_hash_output_complete: true,
            match_id_source: 'payload.matchId',
            hash_matches_baseline: true,
            existing_raw_match_data_found: false,
            decision: 'inserted',
        })),
        transaction: { began: true, committed: true, rolled_back: false },
        postWriteVerification: POST_BASELINE,
        insertedRowsMetadata: insertedRowsMetadata(),
    });
    assert.equal(result.execution_completed, true);
    assert.equal(result.inserted_row_metadata.length, 7);
    assert.equal(result.per_target_write[0].match_id, EXPECTED_MATCH_IDS[0]);
});

test('Makefile write target exists and points to remaining writer script', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-remaining-raw-match-data-write:/m);
    assert.match(makefile, /scripts\/ops\/l2_remaining_raw_match_data_write\.js/);
    assert.match(makefile, /--hash-strategy="\$\(HASH_STRATEGY\)"/);
});

test('no child_process spawn source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});

test('no fs write or mkdir source usage', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('no ProductionHarvester\\/raw ingest commit import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no browser\\/proxy import', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"].*(playwright|puppeteer|chromium|BrowserProvider|socks-proxy-agent)/);
});
