'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const Module = require('node:module');
const { matchesForbiddenImport } = require('../helpers/module_load_guard');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/html_hydration_source_fidelity_live_compare.js');

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
        'network-authorization': 'yes',
        'live-compare-authorization': 'yes',
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

function fakeNextData() {
    return {
        buildId: 'build-id',
        props: {
            pageProps: {
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
                    deepOnly: { fromLive: true },
                },
                general: { matchId: '4830747', leagueId: 53 },
                header: { teams: [{ name: 'Auxerre' }, { name: 'Nice' }] },
                seo: {
                    eventJSONLD: { '@type': 'SportsEvent' },
                    breadcrumbJSONLD: { itemListElement: [{ name: 'Ligue 1' }] },
                },
                nav: { locale: 'en' },
            },
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
    const pageProps = fakeNextData().props.pageProps;
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
    return mod.buildHtmlHydrationSourceFidelityLiveCompare({
        input: mod.validateLiveCompareInput(validInput()).value,
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
    });
}

test('valid input succeeds', () => {
    const result = mod.validateLiveCompareInput(validInput());
    assert.equal(result.ok, true);
});

test('source missing fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ source: '' }));
    assert.equal(result.ok, false);
});

test('source non-fotmob fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ source: 'other' }));
    assert.equal(result.ok, false);
});

test('route not html_hydration fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ route: 'api_match_details' }));
    assert.equal(result.ok, false);
});

test('match-id wrong fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'match-id': 'wrong' }));
    assert.equal(result.ok, false);
});

test('external-id wrong fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'external-id': '4830748' }));
    assert.equal(result.ok, false);
});

test('home-team wrong fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'home-team': 'Angers' }));
    assert.equal(result.ok, false);
});

test('away-team wrong fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'away-team': 'Brest' }));
    assert.equal(result.ok, false);
});

test('network-authorization=no fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'network-authorization': 'no' }));
    assert.equal(result.ok, false);
});

test('live-compare-authorization=no fails', () => {
    const result = mod.validateLiveCompareInput(validInput({ 'live-compare-authorization': 'no' }));
    assert.equal(result.ok, false);
});

for (const [name, override] of [
    ['allow-db-write=yes blocked', { 'allow-db-write': 'yes' }],
    ['allow-raw-match-data-write=yes blocked', { 'allow-raw-match-data-write': 'yes' }],
    ['allow-matches-write=yes blocked', { 'allow-matches-write': 'yes' }],
    ['allow-parser-features=yes blocked', { 'allow-parser-features': 'yes' }],
    ['allow-training=yes blocked', { 'allow-training': 'yes' }],
    ['allow-prediction=yes blocked', { 'allow-prediction': 'yes' }],
]) {
    test(name, () => {
        const result = mod.validateLiveCompareInput(validInput(override));
        assert.equal(result.ok, false);
    });
}

test('concurrency > 1 blocked', () => {
    const result = mod.validateLiveCompareInput(validInput({ concurrency: '2' }));
    assert.equal(result.ok, false);
});

test('retry > 0 blocked', () => {
    const result = mod.validateLiveCompareInput(validInput({ retry: '1' }));
    assert.equal(result.ok, false);
});

for (const [name, override] of [
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
        const result = mod.validateLiveCompareInput(validInput(override));
        assert.equal(result.ok, false);
    });
}

test('extractNextDataJsonFromHtml parses fake HTML', () => {
    const result = mod.extractNextDataJsonFromHtml(fakeHtml());
    assert.equal(result.ok, true);
    assert.equal(result.data.props.pageProps.general.matchId, '4830747');
});

test('extractNextDataJsonFromHtml fails controlled when missing', () => {
    const result = mod.extractNextDataJsonFromHtml('<html></html>');
    assert.equal(result.ok, false);
    assert.equal(result.error, 'NO_NEXT_DATA');
});

test('getPageProps finds props.pageProps', () => {
    const pageProps = mod.getPageProps(fakeNextData());
    assert.equal(pageProps.general.matchId, '4830747');
});

test('listJsonPaths handles nested object/arrays', () => {
    const paths = mod.listJsonPaths({ a: [{ b: 1 }], c: { d: true } });
    assert.deepEqual(paths, ['a', 'a[]', 'a[].b', 'c', 'c.d']);
});

test('comparePathCoverage computes overlap/missing/stored-only', () => {
    const coverage = mod.comparePathCoverage(['a', 'b', 'c'], ['b', 'c', 'd']);
    assert.equal(coverage.overlap_count, 2);
    assert.equal(coverage.missing_count, 1);
    assert.equal(coverage.stored_only_count, 1);
});

test('missing path samples are capped at 50', () => {
    const source = Array.from({ length: 80 }, (_, index) => `source_${index}`);
    const coverage = mod.comparePathCoverage(source, []);
    assert.equal(coverage.missing_count, 80);
    assert.equal(coverage.missing_path_samples.length, 50);
});

test('module coverage detects seo live true stored false', () => {
    const coverage = mod.summarizeModuleCoverage(fakeNextData().props.pageProps, storedRawData());
    assert.deepEqual(coverage.seo, { live: true, stored: false });
});

test('module coverage detects content module live/stored true', () => {
    const coverage = mod.summarizeModuleCoverage(fakeNextData().props.pageProps, storedRawData());
    assert.deepEqual(coverage['content.lineup'], { live: true, stored: true });
});

test('classifyMissingPathCategory works for seo/breadcrumb/content/source-level', () => {
    assert.equal(mod.classifyMissingPathCategory('seo.eventJSONLD'), 'seo');
    assert.equal(mod.classifyMissingPathCategory('seo.breadcrumbJSONLD'), 'breadcrumb');
    assert.equal(mod.classifyMissingPathCategory('content.stats.Periods'), 'stat_level');
    assert.equal(mod.classifyMissingPathCategory('nav.locale'), 'source_level');
});

test('buildSourceFidelityAssessment marks transformed payload when stored lacks props/pageProps', () => {
    const payload = buildSuccessPayload();
    assert.equal(payload.fidelity_assessment.stored_raw_data_is_transformed_payload, true);
    assert.equal(payload.fidelity_assessment.stored_raw_data_is_full_next_data, false);
});

test('buildSourceFidelityAssessment marks storage_strategy_review_recommended when pageProps siblings missing', () => {
    const payload = buildSuccessPayload();
    assert.equal(payload.fidelity_assessment.page_props_siblings_missing, true);
    assert.equal(payload.fidelity_assessment.storage_strategy_review_recommended, true);
});

test('fake successful live compare produces db_write_executed=false', () => {
    const payload = buildSuccessPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.db_write_executed, false);
});

test('fake successful live compare produces raw_match_data_write_executed=false', () => {
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
        '<html><script id="__NEXT_DATA__" type="application/json">{"secret":"BODY_SECRET"}</script></html>';
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
    });
    assert.equal(rendered.includes('DO_NOT_PRINT_VALUE'), false);
    assert.equal(rendered.includes(JSON.stringify(fakeNextData())), false);
});

test('no fs write / mkdir', () => {
    const fs = require('node:fs');
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
    const childProcess = require('node:child_process');
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
    });
    assert.equal(result.status, 0);
    assert.equal(queries.length, 1);
});

test('no ProductionHarvester/raw ingest import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (
            matchesForbiddenImport(
                request,
                PROJECT_ROOT,
                /ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/
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
        if (matchesForbiddenImport(request, PROJECT_ROOT, /NextDataParser|feature|train|predict/)) {
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
