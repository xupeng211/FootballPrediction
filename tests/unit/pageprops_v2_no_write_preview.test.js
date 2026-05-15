'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_preview.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        'match-id': '53_20252026_4830747',
        'external-id': '4830747',
        'home-team': 'Auxerre',
        'away-team': 'Nice',
        'candidate-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'network-authorization': 'yes',
        'pageprops-v2-preview-authorization': 'yes',
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
}

function validArgv(overrides = {}) {
    return Object.entries(validInput(overrides)).flatMap(([key, value]) => [`--${key}`, value]);
}

function fakePageProps(overrides = {}) {
    return {
        content: {
            matchFacts: { events: [{ type: 'Goal', secretValue: 'DO_NOT_PRINT_VALUE' }] },
            lineup: { homeTeam: { starters: [{ id: 1, name: 'Home Player' }] } },
            liveticker: { events: [{ time: 1, text: 'Kickoff' }] },
            playerStats: { 1: { stats: { top_stats: { stats: [{ key: 'rating', value: 7.1 }] } } } },
            shotmap: { shots: [{ id: 11, expectedGoals: 0.2 }] },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            h2h: { matches: [{ id: 'h2h-1' }] },
            table: { all: [{ team: 'Auxerre' }] },
            momentum: { main: { data: [1, 2, 3] } },
        },
        general: { matchId: '4830747', leagueId: 53 },
        header: { teams: [{ name: 'Auxerre' }, { name: 'Nice' }] },
        seo: {
            eventJSONLD: { '@type': 'SportsEvent' },
            breadcrumbJSONLD: { itemListElement: [{ name: 'Ligue 1' }] },
        },
        translations: { hello: 'world' },
        fallback: false,
        nav: { locale: 'en' },
        ongoing: false,
        ssr: true,
        ...overrides,
    };
}

function fakeNextData(pageProps = fakePageProps()) {
    return {
        buildId: 'build-id',
        props: {
            pageProps,
        },
        query: { matchId: '4830747' },
    };
}

function fakeHtml(nextData = fakeNextData()) {
    return `<html><head></head><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(
        nextData
    )}</script></body></html>`;
}

function storedRawData(overrides = {}) {
    const pageProps = fakePageProps();
    return {
        _meta: {
            source: 'fotmob',
            route: 'html_hydration',
            full_html_body_stored: false,
        },
        content: pageProps.content,
        general: pageProps.general,
        header: pageProps.header,
        matchId: '4830747',
        ...overrides,
    };
}

function storedRow(overrides = {}) {
    return {
        id: 4,
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: '8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25',
        collected_at: '2026-05-15T15:27:31.214Z',
        raw_data: storedRawData(),
        ...overrides,
    };
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

function buildSuccessPayload() {
    return mod.buildPagePropsV2NoWritePreview({
        input: mod.validatePreviewInput(validInput()).value,
        storedRow: storedRow(),
        fetchResult: {
            ok: true,
            request_url: 'https://www.fotmob.com/match/4830747',
            final_url: 'https://www.fotmob.com/match/4830747',
            http_status: 200,
            content_type: 'text/html; charset=utf-8',
            body_byte_length: Buffer.byteLength(fakeHtml(), 'utf8'),
            body_sha256: 'hash',
            body: fakeHtml(),
        },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
}

test('valid input succeeds', () => {
    const result = mod.validatePreviewInput(validInput());
    assert.equal(result.ok, true);
});

for (const [name, override] of [
    ['source missing fails', { source: '' }],
    ['source non-fotmob fails', { source: 'other' }],
    ['route not html_hydration fails', { route: 'api_match_details' }],
    ['match-id wrong fails', { 'match-id': 'wrong' }],
    ['external-id wrong fails', { 'external-id': '4830748' }],
    ['home-team wrong fails', { 'home-team': 'Angers' }],
    ['away-team wrong fails', { 'away-team': 'Brest' }],
    ['candidate-version missing fails', { 'candidate-version': '' }],
    ['candidate-version not fotmob_pageprops_v2 fails', { 'candidate-version': 'fotmob_html_hyd_v1' }],
    ['hash-strategy missing fails', { 'hash-strategy': '' }],
    ['hash-strategy not stable_pageprops_payload_v1 fails', { 'hash-strategy': 'stable_raw_payload_v1' }],
    ['network-authorization=no fails', { 'network-authorization': 'no' }],
    ['pageprops-v2-preview-authorization=no fails', { 'pageprops-v2-preview-authorization': 'no' }],
    ['allow-db-write=yes blocked', { 'allow-db-write': 'yes' }],
    ['allow-raw-match-data-write=yes blocked', { 'allow-raw-match-data-write': 'yes' }],
    ['allow-matches-write=yes blocked', { 'allow-matches-write': 'yes' }],
    ['allow-parser-features=yes blocked', { 'allow-parser-features': 'yes' }],
    ['allow-training=yes blocked', { 'allow-training': 'yes' }],
    ['allow-prediction=yes blocked', { 'allow-prediction': 'yes' }],
    ['concurrency > 1 blocked', { concurrency: '2' }],
    ['retry > 0 blocked', { retry: '1' }],
    ['print-body=yes blocked', { 'print-body': 'yes' }],
    ['save-body=yes blocked', { 'save-body': 'yes' }],
    ['print-full-json=yes blocked', { 'print-full-json': 'yes' }],
    ['save-full-json=yes blocked', { 'save-full-json': 'yes' }],
    ['browser/proxy allowed blocked', { 'allow-browser-runtime': 'yes', 'allow-proxy-runtime': 'yes' }],
    ['bulk=yes blocked', { bulk: 'yes' }],
    ['execute=yes blocked', { execute: 'yes' }],
    ['commit=yes blocked', { commit: 'yes' }],
]) {
    test(name, () => {
        const result = mod.validatePreviewInput(validInput(override));
        assert.equal(result.ok, false);
    });
}

test('extractNextDataJsonFromHtml parses fake HTML', () => {
    const result = mod.extractNextDataJsonFromHtml(fakeHtml());
    assert.equal(result.ok, true);
    assert.equal(result.data.props.pageProps.general.matchId, '4830747');
});

test('getPageProps finds props.pageProps', () => {
    const pageProps = mod.getPageProps(fakeNextData());
    assert.equal(pageProps.general.matchId, '4830747');
});

test('buildPagePropsV2Candidate includes _meta and pageProps', () => {
    const candidate = mod.buildPagePropsV2Candidate({
        input: mod.validatePreviewInput(validInput()).value,
        pageProps: fakePageProps(),
        fetchResult: {
            request_url: 'https://www.fotmob.com/match/4830747',
            final_url: 'https://www.fotmob.com/match/4830747',
            http_status: 200,
            content_type: 'text/html; charset=utf-8',
            body_byte_length: 123,
            body_sha256: 'body-hash',
        },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    assert.equal(candidate._meta.data_version, 'fotmob_pageprops_v2');
    assert.equal(candidate._meta.hash_strategy, 'stable_pageprops_payload_v1');
    assert.equal(candidate.pageProps.general.matchId, '4830747');
});

test('buildPagePropsV2Candidate does not include full HTML body', () => {
    const candidate = mod.buildPagePropsV2Candidate({
        input: mod.validatePreviewInput(validInput()).value,
        pageProps: fakePageProps(),
        fetchResult: {
            request_url: 'https://www.fotmob.com/match/4830747',
            body: '<html>FULL_BODY_SHOULD_NOT_BE_INCLUDED</html>',
            body_sha256: 'body-hash',
        },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    assert.equal(JSON.stringify(candidate).includes('FULL_BODY_SHOULD_NOT_BE_INCLUDED'), false);
});

test('stable_pageprops hash excludes _meta', () => {
    const pageProps = fakePageProps();
    const candidate = mod.buildPagePropsV2Candidate({
        input: mod.validatePreviewInput(validInput()).value,
        pageProps,
        fetchResult: { request_url: 'https://www.fotmob.com/match/4830747' },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(candidate), mod.computeStablePagePropsHash(pageProps));
});

test('stable_pageprops hash changes when pageProps content changes', () => {
    const first = mod.computeStablePagePropsHash(fakePageProps());
    const second = mod.computeStablePagePropsHash(fakePageProps({ nav: { locale: 'fr' } }));
    assert.notEqual(first, second);
});

test('stable_pageprops hash stable when only _meta changes', () => {
    const pageProps = fakePageProps();
    const first = mod.buildPagePropsV2Candidate({
        input: mod.validatePreviewInput(validInput()).value,
        pageProps,
        fetchResult: { request_url: 'https://www.fotmob.com/match/4830747', body_sha256: 'one' },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    const second = mod.buildPagePropsV2Candidate({
        input: mod.validatePreviewInput(validInput()).value,
        pageProps,
        fetchResult: { request_url: 'https://www.fotmob.com/match/4830747', body_sha256: 'two' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(first), mod.computeStablePagePropsHash(second));
});

test('listJsonPaths handles nested object/arrays', () => {
    const paths = mod.listJsonPaths({ a: [{ b: 1 }], c: { d: true } });
    assert.deepEqual(paths, ['a', 'a[]', 'a[].b', 'c', 'c.d']);
});

test('comparePathCoverage computes v2-only/v1-only/overlap', () => {
    const coverage = mod.comparePathCoverage(['a', 'b', 'c'], ['b', 'c', 'd']);
    assert.equal(coverage.overlap_count, 2);
    assert.equal(coverage.v2_only_count, 1);
    assert.equal(coverage.v1_only_count, 1);
});

test('samples capped at 50', () => {
    const v2 = Array.from({ length: 80 }, (_, index) => `source_${index}`);
    const coverage = mod.comparePathCoverage(v2, []);
    assert.equal(coverage.v2_only_count, 80);
    assert.equal(coverage.v2_only_path_samples.length, 50);
});

test('module coverage detects seo/translations/fallback in v2 and missing in v1', () => {
    const coverage = mod.summarizeModuleCoverage(storedRawData(), fakePageProps());
    assert.deepEqual(coverage.seo, { v1: false, v2: true });
    assert.deepEqual(coverage.translations, { v1: false, v2: true });
    assert.deepEqual(coverage.fallback, { v1: false, v2: true });
});

test('fake successful preview db_write_executed=false', () => {
    const payload = buildSuccessPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.db_write_executed, false);
});

test('fake successful preview raw_match_data_write_executed=false', () => {
    const payload = buildSuccessPayload();
    assert.equal(payload.raw_match_data_write_executed, false);
});

test('fake 403 returns controlled failure/no retry', async () => {
    let calls = 0;
    const outputs = [];
    const result = await mod.runCli(validArgv(), {
        storedRow: storedRow(),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse({ status: 403, body: 'forbidden body that must not print' });
        },
        output: payload => outputs.push(payload),
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 1);
    assert.equal(outputs[0].controlled_failure, true);
    assert.equal(outputs[0].retry_count, 0);
});

test('fake invalid hydration returns controlled failure/no retry', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        storedRow: storedRow(),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse({ body: '<html>missing hydration</html>' });
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 1);
    assert.equal(result.payload.failure_reason, 'NO_NEXT_DATA');
});

test('no full HTML body printed/saved', async () => {
    let rendered = '';
    const secretBody =
        '<html><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"content":{},"bodySecret":"BODY_SECRET"}}}</script></html>';
    await mod.runCli(validArgv(), {
        storedRow: storedRow(),
        fetchFn: async () => fakeResponse({ body: secretBody }),
        output: payload => {
            rendered = JSON.stringify(payload);
        },
    });
    assert.equal(rendered.includes(secretBody), false);
    assert.equal(rendered.includes('BODY_SECRET'), false);
});

test('no full JSON printed/saved', async () => {
    let rendered = '';
    await mod.runCli(validArgv(), {
        storedRow: storedRow(),
        fetchFn: async () => fakeResponse(),
        output: payload => {
            rendered = JSON.stringify(payload);
        },
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    assert.equal(rendered.includes('DO_NOT_PRINT_VALUE'), false);
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
    const queries = [];
    const result = await mod.runCli(validArgv(), {
        client: {
            async query(sql) {
                queries.push(sql);
                assert.match(sql.trim().toLowerCase(), /^select\b/);
                assert.doesNotMatch(sql, /\b(insert|update|delete|truncate|alter|drop|for update)\b/i);
                return { rows: [storedRow()] };
            },
        },
        fetchFn: async () => fakeResponse(),
        output: () => {},
        generatedAt: '2026-05-15T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(queries.length, 1);
});

test('no ProductionHarvester/raw ingest import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/.test(request)) {
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
        if (/NextDataParser|feature|train|predict/.test(request)) {
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
        if (/playwright|puppeteer|BrowserProvider|Chromium/i.test(request)) {
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
