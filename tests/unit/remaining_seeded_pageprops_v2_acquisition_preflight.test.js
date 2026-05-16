'use strict';

/* eslint-disable max-lines */

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/remaining_seeded_pageprops_v2_acquisition_preflight.js');
const TARGET_EXTERNAL_IDS = '4830746,4830748,4830750,4830751,4830752,4830753,4830754';

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        targetExternalIds: TARGET_EXTERNAL_IDS,
        candidateVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        networkAuthorization: true,
        pagepropsV2RemainingPreflightAuthorization: true,
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
        'target-external-ids': TARGET_EXTERNAL_IDS,
        'candidate-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'network-authorization': 'yes',
        'pageprops-v2-remaining-preflight-authorization': 'yes',
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

const TEAM_BY_EXTERNAL_ID = Object.freeze({
    4830746: ['Angers', 'Strasbourg'],
    4830748: ['Le Havre', 'Marseille'],
    4830750: ['Metz', 'Lorient'],
    4830751: ['Monaco', 'Lille'],
    4830752: ['Paris Saint-Germain', 'Brest'],
    4830753: ['Rennes', 'Paris FC'],
    4830754: ['Toulouse', 'Lyon'],
});

function targetForExternalId(externalId) {
    return mod.EXPECTED_TARGETS.find(target => target.externalId === String(externalId));
}

function fakePageProps(externalId = '4830746', overrides = {}) {
    const [homeTeam, awayTeam] = TEAM_BY_EXTERNAL_ID[externalId] || ['Home', 'Away'];
    return {
        content: {
            matchFacts: { events: [{ type: 'Goal', value: 'SECRET_VALUE_SHOULD_NOT_PRINT' }] },
            lineup: { homeTeam: { name: homeTeam, starters: [{ id: 1, name: 'Home Player' }] } },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            shotmap: { shots: [{ id: Number(externalId), xg: 0.3 }] },
        },
        general: { matchId: externalId, leagueId: 53 },
        header: { teams: [{ name: homeTeam }, { name: awayTeam }] },
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
    };
}

function fakeHtml(externalId = '4830746', pageProps = fakePageProps(externalId)) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(
        fakeNextData(pageProps)
    )}</script></body></html>`;
}

function fetchResultFor(externalId = '4830746', overrides = {}) {
    const body = overrides.body ?? fakeHtml(externalId);
    const status = overrides.http_status ?? overrides.status ?? 200;
    return {
        ok: overrides.ok ?? (status >= 200 && status < 300),
        request_url: `https://www.fotmob.com/match/${externalId}`,
        final_url: overrides.final_url || `https://www.fotmob.com/match/${externalId}`,
        http_status: status,
        content_type: overrides.content_type || 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: `body-sha-${externalId}`,
        body,
        error: overrides.error,
    };
}

function metadataRows(overrides = []) {
    return mod.EXPECTED_TARGETS.map(target => {
        const [homeTeam, awayTeam] = TEAM_BY_EXTERNAL_ID[target.externalId];
        return {
            match_id: target.matchId,
            external_id: target.externalId,
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
        };
    }).concat(overrides);
}

function v1RawData(externalId = '4830746') {
    const pageProps = fakePageProps(externalId);
    return {
        _meta: { source: 'fotmob', route: 'html_hydration' },
        content: pageProps.content,
        general: pageProps.general,
        header: pageProps.header,
        matchId: externalId,
        secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT',
    };
}

function rawRow(externalId = '4830746', overrides = {}) {
    const target = targetForExternalId(externalId);
    return {
        id: Number(externalId) - 4830740,
        match_id: target.matchId,
        external_id: target.externalId,
        data_version: 'fotmob_html_hyd_v1',
        data_hash: `hash-${externalId}`,
        collected_at: '2026-05-16T00:00:00.000Z',
        raw_data: v1RawData(externalId),
        ...overrides,
    };
}

function existingRows(overrides = []) {
    return mod.EXPECTED_TARGETS.map(target => rawRow(target.externalId)).concat(overrides);
}

function protectedRows(overrides = {}) {
    const rows = {
        matches: 10,
        raw_match_data: 11,
        bookmaker_odds_history: 2,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...overrides,
    };
    return [
        { table_name: 'matches', rows: rows.matches },
        { table_name: 'bookmaker_odds_history', rows: rows.bookmaker_odds_history },
        { table_name: 'raw_match_data', rows: rows.raw_match_data },
        { table_name: 'l3_features', rows: rows.l3_features },
        { table_name: 'match_features_training', rows: rows.match_features_training },
        { table_name: 'predictions', rows: rows.predictions },
    ];
}

function schemaConstraints(overrides = []) {
    return [
        {
            conname: 'raw_match_data_match_id_data_version_key',
            contype: 'u',
            definition: 'UNIQUE (match_id, data_version)',
        },
        ...overrides,
    ];
}

async function buildPayload(overrides = {}) {
    return mod.buildRemainingSeededPagePropsV2AcquisitionPreflight({
        input: validInput(),
        metadataRows: metadataRows(),
        existingRows: existingRows(),
        protectedTableRows: protectedRows(),
        schemaConstraintRows: schemaConstraints(),
        generatedAt: '2026-05-16T00:00:00.000Z',
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                const externalId = requestUrl.split('/').pop();
                return fetchResultFor(externalId);
            },
        },
        ...overrides,
    });
}

function fakeClient() {
    const queries = [];
    return {
        queries,
        async query(sql) {
            queries.push(sql);
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/i);
            if (/pg_constraint/i.test(sql)) return { rows: schemaConstraints() };
            if (/UNION ALL/i.test(sql)) return { rows: protectedRows() };
            if (/FROM matches/i.test(sql)) return { rows: metadataRows() };
            if (/FROM raw_match_data/i.test(sql)) return { rows: existingRows() };
            return { rows: [] };
        },
    };
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validatePreflightInput(validInput(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePreflightInput(validInput()).ok, true);
});

for (const [name, override, pattern] of [
    ['source missing fails', { source: '' }, /missing source=fotmob/],
    ['source non-fotmob fails', { source: 'other' }, /source must be fotmob/],
    ['route not html_hydration fails', { route: 'api_match_details' }, /route must be html_hydration/],
    ['target-external-ids missing fails', { targetExternalIds: '' }, /missing target-external-ids/],
    ['target-external-ids wrong list fails', { targetExternalIds: '4830746,4830748' }, /must be exactly/],
    [
        'target-external-ids include 4830747 blocked',
        { targetExternalIds: `4830746,4830747` },
        /must not include 4830747/,
    ],
    ['target-external-ids duplicate blocked', { targetExternalIds: `${TARGET_EXTERNAL_IDS},4830754` }, /duplicates/],
    [
        'candidate-version not fotmob_pageprops_v2 fails',
        { candidateVersion: 'fotmob_html_hyd_v1' },
        /candidate-version must be fotmob_pageprops_v2/,
    ],
    [
        'hash-strategy not stable_pageprops_payload_v1 fails',
        { hashStrategy: 'stable_raw_payload_v1' },
        /hash-strategy must be stable_pageprops_payload_v1/,
    ],
    ['network-authorization=no fails', { networkAuthorization: false }, /network-authorization=yes is required/],
    [
        'pageprops-v2-remaining-preflight-authorization=no fails',
        { pagepropsV2RemainingPreflightAuthorization: false },
        /pageprops-v2-remaining-preflight-authorization=yes is required/,
    ],
    ['allow-db-write=yes blocked', { allowDbWrite: true }, /allow-db-write=yes is blocked/],
    [
        'allow-raw-match-data-write=yes blocked',
        { allowRawMatchDataWrite: true },
        /allow-raw-match-data-write=yes is blocked/,
    ],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }, /allow-matches-write=yes is blocked/],
    ['allow-parser-features=yes blocked', { allowParserFeatures: true }, /allow-parser-features=yes is blocked/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training=yes is blocked/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction=yes is blocked/],
    ['concurrency > 1 blocked', { concurrency: 2 }, /concurrency=1 is required/],
    ['retry > 0 blocked', { retry: 1 }, /retry=0 is required/],
    ['print-body=yes blocked', { printBody: true }, /print-body=yes is blocked/],
    ['save-body=yes blocked', { saveBody: true }, /save-body=yes is blocked/],
    ['print-full-json=yes blocked', { printFullJson: true }, /print-full-json=yes is blocked/],
    ['save-full-json=yes blocked', { saveFullJson: true }, /save-full-json=yes is blocked/],
    [
        'browser/proxy allowed blocked',
        { allowBrowserRuntime: true, allowProxyRuntime: true },
        /allow-browser-runtime=yes is blocked/,
    ],
    ['bulk-write=yes blocked', { bulkWrite: true }, /bulk-write=yes is blocked/],
    ['execute=yes blocked', { execute: true }, /execute=yes is blocked/],
    ['commit=yes blocked', { commit: true }, /commit=yes is blocked/],
    [
        'include-4830747=yes blocked',
        { include4830747: true },
        /include4830747=yes is blocked|include4830747=yes is blocked/i,
    ],
]) {
    test(name, () => {
        assertInvalid(override, pattern);
    });
}

test('parseArgs maps CLI flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.targetExternalIds, TARGET_EXTERNAL_IDS);
    assert.equal(parsed.pagepropsV2RemainingPreflightAuthorization, true);
});

test('fake metadata requires exactly 7 targets', async () => {
    const payload = await buildPayload({ metadataRows: metadataRows().slice(0, 6) });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /TARGET_METADATA_ROW_COUNT:6/);
});

test('fake metadata missing target returns controlled error', async () => {
    const rows = metadataRows().filter(row => row.external_id !== '4830754');
    rows.push({ ...metadataRows()[0], external_id: '9999999' });
    const payload = await buildPayload({ metadataRows: rows });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /TARGET_METADATA_MISSING:4830754/);
});

test('fake existing versions v1 exists and v2 absent returns would_insert', () => {
    const decision = mod.buildExistingVersionDecision([rawRow('4830746')]);
    assert.equal(decision.decision, 'would_insert');
    assert.equal(decision.would_insert_count, 1);
    assert.deepEqual(decision.existing_versions, ['fotmob_html_hyd_v1']);
});

test('fake existing versions v2 exists returns already_exists skip decision', () => {
    const decision = mod.buildExistingVersionDecision([
        rawRow('4830746'),
        rawRow('4830746', { id: 101, data_version: 'fotmob_pageprops_v2', data_hash: 'a'.repeat(64) }),
    ]);
    assert.equal(decision.decision, 'would_skip');
    assert.equal(decision.would_skip_count, 1);
    assert.equal(decision.target_version_exists, true);
});

test('fake duplicate match_id,data_version returns controlled error', async () => {
    const duplicate = rawRow('4830746', { id: 999 });
    const payload = await buildPayload({ existingRows: existingRows([duplicate]) });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /DUPLICATE_MATCH_ID_DATA_VERSION/);
});

test('fake HTML extracts __NEXT_DATA__', () => {
    const result = mod.extractNextDataJsonFromHtml(fakeHtml('4830746'));
    assert.equal(result.ok, true);
    assert.equal(result.data.props.pageProps.general.matchId, '4830746');
});

test('fake pageProps hash stable from pageProps only', () => {
    const pageProps = fakePageProps('4830746');
    const candidate = mod.buildPagePropsV2Candidate({
        input: validInput(),
        target: metadataRows()[0],
        pageProps,
        fetchResult: fetchResultFor('4830746'),
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(candidate), mod.computeStablePagePropsHash(pageProps));
});

test('hash ignores _meta and top-level matchId', () => {
    const pageProps = fakePageProps('4830746');
    const first = mod.buildPagePropsV2Candidate({
        input: validInput(),
        target: metadataRows()[0],
        pageProps,
        fetchResult: fetchResultFor('4830746'),
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    const second = {
        ...first,
        _meta: { ...first._meta, generated_at: '2099-01-01T00:00:00.000Z' },
        matchId: 9999999,
    };
    assert.equal(mod.computeStablePagePropsHash(first), mod.computeStablePagePropsHash(second));
});

test('fake all 7 successful returns would_insert_count=7 sequentially', async () => {
    const requests = [];
    const payload = await buildPayload({
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                requests.push(requestUrl);
                return fetchResultFor(requestUrl.split('/').pop());
            },
        },
    });
    assert.equal(payload.ok, true);
    assert.equal(payload.attempted_target_count, 7);
    assert.equal(payload.valid_payload_count, 7);
    assert.equal(payload.failed_target_count, 0);
    assert.equal(payload.would_insert_count, 7);
    assert.equal(payload.would_update_count, 0);
    assert.equal(payload.would_skip_count, 0);
    assert.deepEqual(
        requests,
        mod.EXPECTED_EXTERNAL_IDS.map(externalId => `https://www.fotmob.com/match/${externalId}`)
    );
});

test('fake one target 403 returns controlled failure and no retry', async () => {
    const calls = [];
    const payload = await buildPayload({
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                calls.push(requestUrl);
                const externalId = requestUrl.split('/').pop();
                if (externalId === '4830748') {
                    return fetchResultFor(externalId, { ok: false, status: 403, error: 'HTTP_403' });
                }
                return fetchResultFor(externalId);
            },
        },
    });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /4830748:HTTP_403/);
    assert.equal(calls.filter(url => url.endsWith('/4830748')).length, 1);
    assert.equal(payload.retry_count, 0);
});

test('fake invalid hydration returns controlled failure and no retry', async () => {
    const calls = [];
    const payload = await buildPayload({
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                calls.push(requestUrl);
                const externalId = requestUrl.split('/').pop();
                if (externalId === '4830748') {
                    return fetchResultFor(externalId, { body: '<html>no next data</html>' });
                }
                return fetchResultFor(externalId);
            },
        },
    });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /4830748:NO_NEXT_DATA/);
    assert.equal(calls.filter(url => url.endsWith('/4830748')).length, 1);
});

test('no full body/json printed or saved in payload', async () => {
    const payload = await buildPayload();
    const serialized = JSON.stringify(payload);
    assert.doesNotMatch(serialized, /SECRET_VALUE_SHOULD_NOT_PRINT/);
    assert.doesNotMatch(serialized, /SECRET_RAW_DATA_SHOULD_NOT_PRINT/);
    assert.equal(payload.body_printed, false);
    assert.equal(payload.body_saved, false);
    assert.equal(payload.full_json_printed, false);
    assert.equal(payload.full_json_saved, false);
});

test('runCli performs no DB write', async () => {
    const client = fakeClient();
    const outputs = [];
    const result = await mod.runCli(validArgv(), {
        client,
        fetchHtmlFn: async requestUrl => fetchResultFor(requestUrl.split('/').pop()),
        output: payload => outputs.push(payload),
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(outputs[0].db_write_executed, false);
    assert.equal(outputs[0].raw_match_data_write_executed, false);
    assert.equal(client.queries.length, 4);
});

test('no fs write or mkdir is used', async t => {
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const fail = name => () => {
        throw new Error(`${name} should not be called`);
    };
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    t.after(() => {
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
    });

    const payload = await buildPayload();
    assert.equal(payload.ok, true);
});

test('no child_process spawn is used', async t => {
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const fail = name => () => {
        throw new Error(`${name} should not be called`);
    };
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    t.after(() => {
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
    });

    const payload = await buildPayload();
    assert.equal(payload.ok, true);
});

test('blocked runtime imports are not used', t => {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
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
        if (
            /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data|parser|feature_engine|training|predict_pipeline/i.test(
                request
            )
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
    assert.doesNotThrow(() => loadFreshModule());
});

test('queryReadOnly blocks non SELECT SQL', async () => {
    const client = { query: async () => ({ rows: [] }) };
    await assert.rejects(
        () => mod.queryReadOnly(client, 'UPDATE raw_match_data SET data_hash = $1', ['x']),
        /NON_SELECT|BLOCKED/
    );
});
