'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');
const { matchesForbiddenImport } = require('../helpers/module_load_guard');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_single_target_write_preflight.js');
const PREVIOUS_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        matchId: '53_20252026_4830747',
        externalId: '4830747',
        homeTeam: 'Auxerre',
        awayTeam: 'Nice',
        candidateVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        previousPreviewHash: PREVIOUS_HASH,
        networkAuthorization: true,
        pagepropsV2WritePreflightAuthorization: true,
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
        printFullJson: false,
        saveFullJson: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        route: 'html_hydration',
        'match-id': '53_20252026_4830747',
        'external-id': '4830747',
        'home-team': 'Auxerre',
        'away-team': 'Nice',
        'candidate-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'previous-preview-hash': PREVIOUS_HASH,
        'network-authorization': 'yes',
        'pageprops-v2-write-preflight-authorization': 'yes',
        'allow-db-write': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-matches-write': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        concurrency: '1',
        retry: '0',
        'print-body': 'no',
        'save-body': 'no',
        'print-full-json': 'no',
        'save-full-json': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function fakePageProps(overrides = {}) {
    return {
        content: {
            matchFacts: { events: [{ type: 'Goal', value: 'SECRET_VALUE_SHOULD_NOT_PRINT' }] },
            lineup: { homeTeam: { starters: [{ id: 1, name: 'Home Player' }] } },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            shotmap: { shots: [{ id: 9, xg: 0.3 }] },
        },
        general: { matchId: '4830747', leagueId: 53 },
        header: { teams: [{ name: 'Auxerre' }, { name: 'Nice' }] },
        seo: { eventJSONLD: { '@type': 'SportsEvent' } },
        translations: { hello: 'world' },
        nav: { locale: 'en' },
        ...overrides,
    };
}

function fakeNextData(pageProps = fakePageProps()) {
    return {
        props: {
            pageProps,
        },
        query: { matchId: '4830747' },
    };
}

function fakeHtml(nextData = fakeNextData()) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(
        nextData
    )}</script></body></html>`;
}

function fakeResponse({ status = 200, body = fakeHtml(), url = 'https://www.fotmob.com/match/4830747' } = {}) {
    return {
        ok: status >= 200 && status < 300,
        status,
        url,
        headers: {
            get(name) {
                return name.toLowerCase() === 'content-type' ? 'text/html; charset=utf-8' : null;
            },
        },
        async text() {
            return body;
        },
    };
}

function matchMetadata(overrides = {}) {
    return {
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        home_team: 'Auxerre',
        away_team: 'Nice',
        match_date: '2026-05-10T19:00:00.000Z',
        status: 'finished',
        ...overrides,
    };
}

function v1RawData(overrides = {}) {
    const pageProps = fakePageProps();
    return {
        _meta: { source: 'fotmob', route: 'html_hydration' },
        content: pageProps.content,
        general: pageProps.general,
        header: pageProps.header,
        matchId: '4830747',
        ...overrides,
    };
}

function rawRow(overrides = {}) {
    return {
        id: 4,
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: '8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25',
        collected_at: '2026-05-15T15:27:31.214Z',
        raw_data: v1RawData(),
        ...overrides,
    };
}

function protectedRows() {
    return [
        { table_name: 'matches', rows: '10' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '10' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ];
}

function fetchResult(body = fakeHtml()) {
    return {
        ok: true,
        request_url: 'https://www.fotmob.com/match/4830747',
        final_url: 'https://www.fotmob.com/match/4830747',
        http_status: 200,
        content_type: 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: 'body-sha',
        body,
    };
}

function successPayload(overrides = {}) {
    return mod.buildPagePropsV2SingleTargetWritePreflight({
        input: validInput(),
        matchMetadata: matchMetadata(),
        existingRows: [rawRow()],
        protectedTableRows: protectedRows(),
        fetchResult: fetchResult(),
        generatedAt: '2026-05-16T00:00:00.000Z',
        ...overrides,
    });
}

function fakeClient({ rows = [rawRow()] } = {}) {
    const queries = [];
    return {
        queries,
        async query(sql) {
            queries.push(sql);
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/i);
            if (/UNION ALL/i.test(sql)) return { rows: protectedRows() };
            if (/FROM raw_match_data/i.test(sql)) return { rows };
            if (/FROM matches/i.test(sql)) return { rows: [matchMetadata()] };
            return { rows: [] };
        },
    };
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePreflightInput(validInput()).ok, true);
});

for (const [name, override] of [
    ['source missing fails', { source: '' }],
    ['source non-fotmob fails', { source: 'other' }],
    ['route not html_hydration fails', { route: 'api_match_details' }],
    ['match-id wrong fails', { matchId: 'wrong' }],
    ['external-id wrong fails', { externalId: '4830748' }],
    ['home-team wrong fails', { homeTeam: 'Angers' }],
    ['away-team wrong fails', { awayTeam: 'Brest' }],
    ['candidate-version missing fails', { candidateVersion: '' }],
    ['candidate-version not fotmob_pageprops_v2 fails', { candidateVersion: 'fotmob_html_hyd_v1' }],
    ['hash-strategy missing fails', { hashStrategy: '' }],
    ['hash-strategy not stable_pageprops_payload_v1 fails', { hashStrategy: 'stable_raw_payload_v1' }],
    ['previous-preview-hash missing fails', { previousPreviewHash: '' }],
    ['previous-preview-hash invalid fails', { previousPreviewHash: 'not-a-hash' }],
    ['network-authorization=no fails', { networkAuthorization: false }],
    ['pageprops-v2-write-preflight-authorization=no fails', { pagepropsV2WritePreflightAuthorization: false }],
    ['allow-db-write=yes blocked', { allowDbWrite: true }],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }],
    ['allow-parser-features=yes blocked', { allowParserFeatures: true }],
    ['allow-training=yes blocked', { allowTraining: true }],
    ['allow-prediction=yes blocked', { allowPrediction: true }],
    ['concurrency > 1 blocked', { concurrency: 2 }],
    ['retry > 0 blocked', { retry: 1 }],
    ['print-body=yes blocked', { printBody: true }],
    ['save-body=yes blocked', { saveBody: true }],
    ['print-full-json=yes blocked', { printFullJson: true }],
    ['save-full-json=yes blocked', { saveFullJson: true }],
    ['browser/proxy allowed blocked', { allowBrowserRuntime: true, allowProxyRuntime: true }],
    ['bulk=yes blocked', { bulk: true }],
    ['execute=yes blocked', { execute: true }],
    ['commit=yes blocked', { commit: true }],
]) {
    test(name, () => {
        assert.equal(mod.validatePreflightInput(validInput(override)).ok, false);
    });
}

test('extracts __NEXT_DATA__ from fake HTML', () => {
    const result = mod.extractNextDataJsonFromHtml(fakeHtml());
    assert.equal(result.ok, true);
    assert.equal(result.data.props.pageProps.general.matchId, '4830747');
});

test('extracts pageProps', () => {
    const pageProps = mod.getPageProps(fakeNextData());
    assert.equal(pageProps.general.matchId, '4830747');
});

test('computes stable_pageprops_payload_v1 from pageProps only', () => {
    const pageProps = fakePageProps();
    const candidate = mod.buildPagePropsV2Candidate({
        input: validInput(),
        pageProps,
        fetchResult: fetchResult(),
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(candidate), mod.computeStablePagePropsHash(pageProps));
});

test('stable hash ignores _meta changes', () => {
    const pageProps = fakePageProps();
    const first = mod.buildPagePropsV2Candidate({
        input: validInput(),
        pageProps,
        fetchResult: { body_sha256: 'one' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    const second = mod.buildPagePropsV2Candidate({
        input: validInput(),
        pageProps,
        fetchResult: { body_sha256: 'two' },
        generatedAt: '2026-05-17T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(first), mod.computeStablePagePropsHash(second));
});

test('hash comparison matches previous preview', () => {
    const result = mod.buildHashComparison(PREVIOUS_HASH, PREVIOUS_HASH);
    assert.equal(result.hash_matches_previous_preview, true);
    assert.equal(result.hash_drift_detected, false);
});

test('hash comparison detects drift', () => {
    const result = mod.buildHashComparison('0'.repeat(64), PREVIOUS_HASH);
    assert.equal(result.hash_matches_previous_preview, false);
    assert.equal(result.hash_drift_detected, true);
});

test('existing versions v1 exists / v2 absent -> would_insert', () => {
    const result = mod.buildExistingVersionDecision({ rows: [rawRow()], targetHash: 'a'.repeat(64) });
    assert.equal(result.existing_versions.fotmob_html_hyd_v1_exists, true);
    assert.equal(result.existing_versions.fotmob_pageprops_v2_exists, false);
    assert.equal(result.decision.would_insert_count, 1);
});

test('existing versions v2 exists same hash -> would_skip', () => {
    const hash = 'a'.repeat(64);
    const result = mod.buildExistingVersionDecision({
        rows: [rawRow(), rawRow({ id: 11, data_version: 'fotmob_pageprops_v2', data_hash: hash })],
        targetHash: hash,
    });
    assert.equal(result.decision.would_skip_count, 1);
});

test('existing versions v2 exists different hash -> would_update_requires_authorization / blocked for this phase', () => {
    const result = mod.buildExistingVersionDecision({
        rows: [rawRow(), rawRow({ id: 11, data_version: 'fotmob_pageprops_v2', data_hash: 'b'.repeat(64) })],
        targetHash: 'a'.repeat(64),
    });
    assert.equal(result.decision.would_update_count, 1);
    assert.equal(result.decision.blocked_this_phase, true);
});

test('duplicate match_id,data_version -> controlled error', () => {
    assert.throws(
        () => mod.buildExistingVersionDecision({ rows: [rawRow(), rawRow({ id: 12 })], targetHash: 'a'.repeat(64) }),
        /DUPLICATE_MATCH_ID_DATA_VERSION/
    );
});

test('fake successful preflight db_write_executed=false', () => {
    const payload = successPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.db_write_executed, false);
});

test('fake successful preflight raw_match_data_write_executed=false', () => {
    const payload = successPayload();
    assert.equal(payload.raw_match_data_write_executed, false);
});

test('fake successful preflight emits would_insert and conflict target', () => {
    const payload = successPayload();
    assert.equal(payload.decision.would_insert_count, 1);
    assert.deepEqual(payload.write_plan_for_next_phase.insert_conflict_target, ['match_id', 'data_version']);
});

test('fake 403 returns controlled failure/no retry', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse({ status: 403, body: 'FORBIDDEN_BODY_SHOULD_NOT_PRINT' });
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 1);
    assert.equal(result.payload.controlled_failure, true);
    assert.equal(result.payload.retry_count, 0);
});

test('fake invalid hydration returns controlled failure/no retry', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse({ body: '<html>missing next data</html>' });
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 1);
    assert.equal(result.payload.failure_reason, 'NO_NEXT_DATA');
});

test('no full body printed/saved', async () => {
    let rendered = '';
    const body = fakeHtml(fakeNextData(fakePageProps({ secretContainer: { value: 'BODY_SECRET_VALUE' } })));
    await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => fakeResponse({ body }),
        output: payload => {
            rendered = JSON.stringify(payload);
        },
    });
    assert.equal(rendered.includes(body), false);
    assert.equal(rendered.includes('BODY_SECRET_VALUE'), false);
});

test('no full JSON printed/saved', async () => {
    let rendered = '';
    await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => fakeResponse(),
        output: payload => {
            rendered = JSON.stringify(payload);
        },
    });
    assert.equal(rendered.includes('SECRET_VALUE_SHOULD_NOT_PRINT'), false);
    assert.equal(rendered.includes(JSON.stringify(fakeNextData())), false);
});

test('no fs write / mkdir', () => {
    const originals = {
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        mkdir: fs.mkdir,
        createWriteStream: fs.createWriteStream,
    };
    let called = false;
    fs.writeFile = () => {
        called = true;
        throw new Error('fs.writeFile blocked');
    };
    fs.writeFileSync = () => {
        called = true;
        throw new Error('fs.writeFileSync blocked');
    };
    fs.mkdir = () => {
        called = true;
        throw new Error('fs.mkdir blocked');
    };
    fs.createWriteStream = () => {
        called = true;
        throw new Error('fs.createWriteStream blocked');
    };
    try {
        loadFreshModule();
        assert.equal(called, false);
    } finally {
        fs.writeFile = originals.writeFile;
        fs.writeFileSync = originals.writeFileSync;
        fs.mkdir = originals.mkdir;
        fs.createWriteStream = originals.createWriteStream;
    }
});

test('no child_process spawn', () => {
    const originals = {
        spawn: childProcess.spawn,
        exec: childProcess.exec,
        execFile: childProcess.execFile,
    };
    let called = false;
    childProcess.spawn = () => {
        called = true;
        throw new Error('spawn blocked');
    };
    childProcess.exec = () => {
        called = true;
        throw new Error('exec blocked');
    };
    childProcess.execFile = () => {
        called = true;
        throw new Error('execFile blocked');
    };
    try {
        loadFreshModule();
        assert.equal(called, false);
    } finally {
        childProcess.spawn = originals.spawn;
        childProcess.exec = originals.exec;
        childProcess.execFile = originals.execFile;
    }
});

test('no DB write', async () => {
    const client = fakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        fetchFn: async () => fakeResponse(),
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(client.queries.length, 3);
});

test('no network unless injected fetch is called', async () => {
    const originals = {
        fetch: global.fetch,
        request: http.request,
        httpsRequest: https.request,
    };
    global.fetch = () => {
        throw new Error('global fetch blocked');
    };
    http.request = () => {
        throw new Error('http.request blocked');
    };
    https.request = () => {
        throw new Error('https.request blocked');
    };
    try {
        const result = await mod.runCli(validArgv(), {
            client: fakeClient(),
            fetchFn: async () => fakeResponse(),
            output: () => {},
        });
        assert.equal(result.status, 0);
    } finally {
        global.fetch = originals.fetch;
        http.request = originals.request;
        https.request = originals.httpsRequest;
    }
});

test('no ProductionHarvester/raw ingest import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (
            matchesForbiddenImport(
                request,
                PROJECT_ROOT,
                /ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/i
            )
        ) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});

test('no parser/features/training import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (matchesForbiddenImport(request, PROJECT_ROOT, /NextDataParser|feature|train|predict/i)) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});

test('no browser/playwright import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (matchesForbiddenImport(request, PROJECT_ROOT, /playwright|puppeteer|BrowserProvider|Chromium/i)) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});
