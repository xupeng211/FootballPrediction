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
const MODULE_PATH = path.join(PROJECT_ROOT, 'src/infrastructure/services/FotMobRawDetailFetcher.js');

function loadFresh() {
    delete require.cache[MODULE_PATH];
    return require(MODULE_PATH);
}

function fake200Html(externalId) {
    return `<!DOCTYPE html><html><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"initialState":{"matchId":"${externalId}","matchFacts":{},"header":{"teams":[{"name":"Home FC"},{"name":"Away FC"}]}}}}}</script></body></html>`;
}

function fake403Html() {
    return '<html><body><h1>403 Forbidden</h1></body></html>';
}

function fakeHtmlNoNextData() {
    return '<html><body><h1>Hello</h1></body></html>';
}

function fakeFetch(status, bodyText, opts = {}) {
    const body = bodyText || '';
    const url = opts.url || 'https://www.fotmob.com/match/4830747';
    return async () => ({
        status,
        url,
        headers: new Map([['content-type', 'text/html; charset=utf-8']]),
        text: async () => body,
    });
}

function makeRealParser() {
    const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
    return { extractFromHtml, transformToApiFormat };
}

function makeFakeParser(matchId) {
    const id = matchId || '4830747';
    return {
        extractFromHtml: () => ({ success: true, data: { _parsed: true } }),
        transformToApiFormat: () => ({
            general: { matchId: id, homeTeam: { name: 'Home FC' }, awayTeam: { name: 'Away FC' } },
            header: { teams: [{ name: 'Home FC' }, { name: 'Away FC' }] },
            content: { matchFacts: {} },
            matchId: id,
        }),
    };
}

function makePayload(overrides = {}) {
    return {
        content: {
            matchFacts: {},
            stats: [{ title: 'Top stats', stats: [{ key: 'shotsOnTarget', home: 2, away: 3 }] }],
        },
        general: { matchId: '4830747', homeTeam: { name: 'Home FC' }, awayTeam: { name: 'Away FC' } },
        header: { teams: [{ name: 'Home FC' }, { name: 'Away FC' }] },
        matchId: '4830747',
        ...overrides,
    };
}

function installGuards(t) {
    const orig = {};
    const fail = name => () => {
        throw new Error(`${name} blocked`);
    };
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
    childProcess.spawn = fail('spawn');
    orig.exec = childProcess.exec;
    childProcess.exec = fail('exec');
    orig.execFile = childProcess.execFile;
    childProcess.execFile = fail('execFile');
    orig.httpReq = http.request;
    http.request = fail('http.request');
    orig.httpsReq = https.request;
    https.request = fail('https.request');
    orig.load = Module._load;
    Module._load = function patchedLoad(req) {
        if (/playwright|puppeteer|ProductionHarvester|backfill_historical/i.test(req)) {
            throw new Error(`blocked: ${req}`);
        }
        return orig.load.apply(this, arguments);
    };
    t.after(() => {
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

// 1-8 URL and validation
test('buildFotMobMatchUrl returns correct URL', () => {
    const fetcher = loadFresh();
    assert.equal(fetcher.buildFotMobMatchUrl('4830747'), 'https://www.fotmob.com/match/4830747');
});
test('buildFotMobMatchUrl rejects empty', () => {
    const fetcher = loadFresh();
    assert.throws(() => fetcher.buildFotMobMatchUrl(''), /INVALID_EXTERNAL_ID/);
});
test('buildFotMobMatchUrl rejects non-numeric', () => {
    const fetcher = loadFresh();
    assert.throws(() => fetcher.buildFotMobMatchUrl('abc'), /INVALID_EXTERNAL_ID/);
});
test('externalId missing fails', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({});
    assert.equal(v.ok, false);
    assert.match(v.errors.join(';'), /externalId is required/);
});
test('externalId non-numeric fails', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: 'abc' });
    assert.equal(v.ok, false);
});
test('matchId non-string fails', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: '4830747', matchId: 4830747 });
    assert.equal(v.ok, false);
    assert.match(v.errors.join(';'), /matchId must be a string/);
});
test('route non-html_hydration fails', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: '4830747', route: 'api' });
    assert.equal(v.ok, false);
    assert.match(v.errors.join(';'), /html_hydration/);
});
test('printBody=true blocked', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: '4830747', printBody: true });
    assert.equal(v.ok, false);
});
test('saveBody=true blocked', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: '4830747', saveBody: true });
    assert.equal(v.ok, false);
});
test('retry > 0 blocked', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchInput({ externalId: '4830747', retry: 1 });
    assert.equal(v.ok, false);
});
test('browser/proxy runtime blocked', () => {
    const fetcher = loadFresh();
    const v1 = fetcher.validateFetchInput({ externalId: '4830747', allowBrowserRuntime: true });
    const v2 = fetcher.validateFetchInput({ externalId: '4830747', allowProxyRuntime: true });
    assert.equal(v1.ok, false);
    assert.equal(v2.ok, false);
});

// 9-14 fetch with fake
test('missing fetchFn fails', async () => {
    const fetcher = loadFresh();
    const result = await fetcher.fetchFotMobRawDetail({ externalId: '4830747' }, {});
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /FETCH_DEPENDENCY/);
});
test('fake fetch HTTP 200 with hydration succeeds', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), { url: 'https://www.fotmob.com/match/4830747' });
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747', homeTeam: 'Home FC', awayTeam: 'Away FC' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.ok, true);
    assert.equal(result.http_status, 200);
    assert.equal(result.hydration_parse_ok, true);
    assert.equal(result.looks_like_valid_match_detail, true);
});
test('final_url captured', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), { url: 'https://www.fotmob.com/match/4830747' });
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.ok(result.final_url);
});
test('body_sha256 computed', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const html = fake200Html('4830747');
    const fn = fakeFetch(200, html, {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.body_sha256.length, 64);
});
test('hydration_parse_ok=true', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.hydration_parse_ok, true);
});
test('raw_data contains _meta/content/general/header/matchId', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    const raw = result.raw_data;
    assert.ok(raw._meta);
    assert.ok(raw.content || raw.general);
    assert.ok(raw._meta.source === 'fotmob');
    assert.ok(raw._meta.fetch_body_sha256);
});
test('raw_data does NOT contain full HTML body', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    const rawStr = JSON.stringify(result.raw_data);
    assert.doesNotMatch(rawStr, /__NEXT_DATA__/);
    assert.doesNotMatch(rawStr, /<!DOCTYPE/);
});
test('raw_data_hash stable and excludes fetched_at metadata drift', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const html = fake200Html('4830747');
    const fn1 = fakeFetch(200, html, {});
    const fn2 = fakeFetch(200, html, {});
    const r1 = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn1, parser: makeFakeParser(), now: () => '2026-01-01T00:00:00Z' }
    );
    const r2 = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn2, parser: makeFakeParser(), now: () => '2026-01-01T00:01:00Z' }
    );
    assert.equal(r1.raw_data_hash, r2.raw_data_hash);
    assert.notEqual(r1.raw_data_with_meta_hash, r2.raw_data_with_meta_hash);
    assert.equal(r1.raw_data_hash.length, 64);
});
test('stable hash excludes fetched_at/collected_at/body_sha256/url/http metadata', () => {
    const fetcher = loadFresh();
    const stablePayload = fetcher.buildStableRawPayload(makePayload(), { externalId: '4830747' }, {});
    const stableHash = fetcher.sha256StableRawPayload(stablePayload);
    const rawA = fetcher.buildRawDataFromStablePayload(
        stablePayload,
        fetcher.buildFetchMetadata({
            requestUrl: 'https://www.fotmob.com/match/4830747',
            finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
            httpStatus: 200,
            contentType: 'text/html; charset=utf-8',
            bodyByteLength: 1000,
            bodySha256: 'body-a',
            fetchedAt: '2026-05-15T10:00:00.000Z',
            dataHash: stableHash,
            matchIdSource: 'payload.matchId',
        })
    );
    const rawB = fetcher.buildRawDataFromStablePayload(
        stablePayload,
        fetcher.buildFetchMetadata({
            requestUrl: 'https://www.fotmob.com/match/4830747?ref=drift',
            finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc?tab=stats',
            httpStatus: 206,
            contentType: 'text/html; charset=iso-8859-1',
            bodyByteLength: 2000,
            bodySha256: 'body-b',
            fetchedAt: '2026-05-15T10:01:00.000Z',
            dataHash: stableHash,
            matchIdSource: 'payload.matchId',
        })
    );
    const hashA = fetcher.computeRawDetailHashes(stablePayload, rawA);
    const hashB = fetcher.computeRawDetailHashes(stablePayload, rawB);
    assert.equal(hashA.raw_data_hash, hashB.raw_data_hash);
    assert.equal(hashA.data_hash, hashB.data_hash);
    assert.notEqual(hashA.raw_data_with_meta_hash, hashB.raw_data_with_meta_hash);
});
test('stable hash changes when stable content changes', () => {
    const fetcher = loadFresh();
    const payloadA = fetcher.buildStableRawPayload(makePayload(), { externalId: '4830747' }, {});
    const payloadB = fetcher.buildStableRawPayload(
        makePayload({
            content: {
                matchFacts: {},
                stats: [{ title: 'Top stats', stats: [{ key: 'shotsOnTarget', home: 4, away: 3 }] }],
            },
        }),
        { externalId: '4830747' },
        {}
    );
    assert.notEqual(fetcher.sha256StableRawPayload(payloadA), fetcher.sha256StableRawPayload(payloadB));
});
test('matchId fallback uses input externalId when payload matchId missing and markers pass', () => {
    const fetcher = loadFresh();
    const payload = makePayload({
        matchId: undefined,
        general: { homeTeam: { name: 'Auxerre' }, awayTeam: { name: 'Nice' } },
    });
    const resolved = fetcher.normalizeMatchId(
        payload,
        { externalId: '4830747', homeTeam: 'Auxerre', awayTeam: 'Nice' },
        {
            requestUrl: 'https://www.fotmob.com/match/4830747',
            finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
        }
    );
    assert.equal(resolved.matchId, '4830747');
    assert.equal(resolved.matchIdSource, 'input_external_id_fallback');
});
test('matchId unresolved when payload matchId missing and markers fail', () => {
    const fetcher = loadFresh();
    const payload = { content: {}, general: {}, header: {} };
    const resolved = fetcher.normalizeMatchId(
        payload,
        { externalId: 'abc', homeTeam: 'Auxerre', awayTeam: 'Nice' },
        {
            requestUrl: 'https://www.fotmob.com/match/unknown',
            finalUrl: 'https://www.fotmob.com/matches/unknown',
        }
    );
    assert.equal(resolved.matchId, null);
    assert.equal(resolved.matchIdSource, 'unresolved');
});
test('looks_like_valid_match_detail fails if matchId cannot be established', () => {
    const fetcher = loadFresh();
    const raw = fetcher.buildRawDataFromStablePayload(
        { content: {}, general: {}, header: {}, matchId: null },
        fetcher.buildFetchMetadata({ dataHash: 'x', matchIdSource: 'unresolved' })
    );
    assert.equal(
        fetcher.looksLikeValidRawDetail(raw, { externalId: '4830747', homeTeam: 'Home FC', awayTeam: 'Away FC' }),
        false
    );
});
test('hash_strategy is stable_raw_payload_v1 and raw_data_hash equals stable payload hash', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747', homeTeam: 'Home FC', awayTeam: 'Away FC' },
        {
            fetchFn: fakeFetch(200, fake200Html('4830747')),
            parser: makeFakeParser(),
            now: () => '2026-05-15T10:00:00.000Z',
        }
    );
    assert.equal(result.hash_strategy, 'stable_raw_payload_v1');
    assert.equal(result.raw_data_hash, result.stable_raw_payload_hash);
    assert.equal(result.data_hash, result.stable_raw_payload_hash);
});
test('canonicalizeJson sorts object keys recursively', () => {
    const fetcher = loadFresh();
    const input = { b: 1, a: { d: 2, c: 3 } };
    const result = fetcher.canonicalizeJson(input);
    assert.equal(JSON.stringify(result), '{"a":{"c":3,"d":2},"b":1}');
});
test('canonicalizeJson preserves array order', () => {
    const fetcher = loadFresh();
    const input = { arr: [3, 1, 2] };
    const result = fetcher.canonicalizeJson(input);
    assert.equal(JSON.stringify(result), '{"arr":[3,1,2]}');
});
test('contains external_id true', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.contains_external_id, true);
});
test('contains home_team true', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747', homeTeam: 'Home FC' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.contains_home_team, true);
});
test('contains away_team true', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747', awayTeam: 'Away FC' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.contains_away_team, true);
});
test('looks_like_valid_match_detail true', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.looks_like_valid_match_detail, true);
});

// 23-25 error cases
test('fake 403 returns controlled invalid', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(403, fake403Html(), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        {
            fetchFn: fn,
            parser: { extractFromHtml: () => ({ success: true, data: null }), transformToApiFormat: () => null },
        }
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /HYDRATION_PARSE_FAILED/);
});
test('fake HTML without __NEXT_DATA__ fails', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fakeHtmlNoNextData(), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        {
            fetchFn: fn,
            parser: { extractFromHtml: () => ({ success: false, data: null }), transformToApiFormat: () => null },
        }
    );
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /HYDRATION_PARSE_FAILED/);
});

// 26-29 safety flags
test('body_printed=false, body_saved=false, browser_used=false, proxy_used=false', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    assert.equal(result.body_printed, false);
    assert.equal(result.body_saved, false);
    assert.equal(result.browser_used, false);
    assert.equal(result.proxy_used, false);
});

// 30-34 audits
test('source audit: no fs write', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});
test('source audit: no child_process', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});
test('source audit: no DB write', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b/i);
    assert.doesNotMatch(source, /require\(['"]pg['"]\)/);
});
test('source audit: no ProductionHarvester', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});
test('source audit: no browser/playwright import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /playwright|puppeteer/);
});

// More helpers
test('sha256Text consistent', () => {
    const fetcher = loadFresh();
    assert.equal(fetcher.sha256Text('hello'), fetcher.sha256Text('hello'));
    assert.equal(fetcher.sha256Text('hello').length, 64);
});
test('buildFotMobHtmlHydrationRequest returns correct shape', () => {
    const fetcher = loadFresh();
    const req = fetcher.buildFotMobHtmlHydrationRequest('4830747');
    assert.equal(req.method, 'GET');
    assert.match(req.url, /4830747/);
    assert.equal(req.route, 'html_hydration');
});
test('validateFetchDependencies ok with fetchFn', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchDependencies({ fetchFn: () => {} });
    assert.equal(v.ok, true);
});
test('validateFetchDependencies fails without fetchFn', () => {
    const fetcher = loadFresh();
    const v = fetcher.validateFetchDependencies({});
    assert.equal(v.ok, false);
});
test('extractHydrationPayload fails without parser deps', () => {
    const fetcher = loadFresh();
    const r = fetcher.extractHydrationPayload('<html></html>', {});
    assert.equal(r.ok, false);
});
test('extractHydrationPayload fails with empty HTML', () => {
    const fetcher = loadFresh();
    const r = fetcher.extractHydrationPayload('', makeRealParser());
    assert.equal(r.ok, false);
});
test('extractHydrationPayload surfaces extract and transform failures', () => {
    const fetcher = loadFresh();
    const extractFail = fetcher.extractHydrationPayload('<html></html>', {
        extractFromHtml: () => {
            throw new Error('boom-extract');
        },
        transformToApiFormat: () => ({}),
    });
    assert.equal(extractFail.ok, false);
    assert.match(extractFail.error, /EXTRACT_ERROR:boom-extract/);

    const transformFail = fetcher.extractHydrationPayload('<html></html>', {
        extractFromHtml: () => ({ success: true, data: { ok: true } }),
        transformToApiFormat: () => {
            throw new Error('boom-transform');
        },
    });
    assert.equal(transformFail.ok, false);
    assert.match(transformFail.error, /TRANSFORM_ERROR:boom-transform/);
});
test('extractHydrationPayload rejects empty transformed object shape', () => {
    const fetcher = loadFresh();
    const r = fetcher.extractHydrationPayload('<html></html>', {
        extractFromHtml: () => ({ success: true, data: { ok: true } }),
        transformToApiFormat: () => null,
    });
    assert.equal(r.ok, false);
    assert.match(r.error, /TRANSFORM_FAILED/);
});
test('validateCanonicalRawDataShape reports missing keys and invalid flags', () => {
    const fetcher = loadFresh();
    assert.deepEqual(fetcher.validateCanonicalRawDataShape(null), ['raw_data must be a plain object']);
    const errors = fetcher.validateCanonicalRawDataShape({
        _meta: { full_html_body_stored: true, http_response_string_stored: true },
        content: {},
        matchId: 'x',
    });
    assert.match(errors.join(';'), /raw_data missing general/);
    assert.match(errors.join(';'), /raw_data missing header/);
    assert.match(errors.join(';'), /raw_data.matchId must be numeric/);
    assert.match(errors.join(';'), /full_html_body_stored must be false/);
    assert.match(errors.join(';'), /http_response_string_stored must be false/);
});
test('fetcher result does NOT include full HTML body', async t => {
    installGuards(t);
    const fetcher = loadFresh();
    const fn = fakeFetch(200, fake200Html('4830747'), {});
    const result = await fetcher.fetchFotMobRawDetail(
        { externalId: '4830747' },
        { fetchFn: fn, parser: makeFakeParser() }
    );
    const resultStr = JSON.stringify(result);
    assert.doesNotMatch(resultStr, /<script id="__NEXT_DATA__"/);
});
