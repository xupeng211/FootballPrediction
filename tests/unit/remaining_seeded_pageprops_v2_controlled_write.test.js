'use strict';

/* eslint-disable complexity, max-lines */

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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js');
const BASELINE_HASHES_JSON =
    '{"4830746":"7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440","4830748":"fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04","4830750":"e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762","4830751":"de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5","4830752":"65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32","4830753":"4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413","4830754":"29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6"}';

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        baselineHashes: BASELINE_HASHES_JSON,
        candidateVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        networkAuthorization: true,
        finalDbWriteConfirmation: true,
        allowDbWrite: true,
        allowRawMatchDataWrite: true,
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
        'baseline-hashes': BASELINE_HASHES_JSON,
        'candidate-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'network-authorization': 'yes',
        'final-db-write-confirmation': 'yes',
        'allow-db-write': 'yes',
        'allow-raw-match-data-write': 'yes',
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

function expectedTarget(externalId) {
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

function fakeResponseFor(externalId = '4830746', overrides = {}) {
    const body = overrides.body ?? fakeHtml(externalId);
    const status = overrides.status ?? overrides.http_status ?? 200;
    return {
        ok: overrides.ok ?? (status >= 200 && status < 300),
        status,
        url: overrides.final_url || `https://www.fotmob.com/match/${externalId}`,
        headers: {
            get(name) {
                return name.toLowerCase() === 'content-type'
                    ? overrides.content_type || 'text/html; charset=utf-8'
                    : null;
            },
        },
        async text() {
            return body;
        },
    };
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
        error: overrides.error || (status >= 200 && status < 300 ? null : `HTTP_${status}`),
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

function rawRow(externalId = '4830746', overrides = {}) {
    const target = expectedTarget(externalId) || { matchId: `53_20252026_${externalId}`, externalId };
    return {
        id: Number(externalId) - 4830700,
        match_id: target.matchId,
        external_id: target.externalId,
        data_version: 'fotmob_html_hyd_v1',
        data_hash: `v1-hash-${externalId}`,
        collected_at: '2026-05-15T15:27:31.214Z',
        ...overrides,
    };
}

function existingRows(overrides = []) {
    return mod.EXPECTED_TARGETS.map(target => rawRow(target.externalId)).concat(overrides);
}

function excluded4830747Rows(overrides = []) {
    return [
        {
            id: 47,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            data_version: 'fotmob_html_hyd_v1',
            data_hash: 'v1-hash-4830747',
            collected_at: '2026-05-15T15:27:31.214Z',
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: false,
        },
        {
            id: 48,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            data_version: 'fotmob_pageprops_v2',
            data_hash: 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc',
            collected_at: '2026-05-16T09:00:00.000Z',
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: true,
        },
        ...overrides,
    ];
}

function versionSummaryRows(overrides = []) {
    return mod.EXPECTED_TARGETS.flatMap(target => [
        {
            ...rawRow(target.externalId),
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: false,
        },
        {
            id: Number(target.externalId) - 4830600,
            match_id: target.matchId,
            external_id: target.externalId,
            data_version: 'fotmob_pageprops_v2',
            data_hash: mod.BASELINE_HASHES[target.externalId],
            collected_at: '2026-05-16T09:00:00.000Z',
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: true,
        },
    ]).concat(overrides);
}

function protectedRows(values = {}) {
    const base = {
        matches: 10,
        bookmaker_odds_history: 2,
        raw_match_data: 11,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...values,
    };
    return [
        { table_name: 'matches', rows: String(base.matches) },
        { table_name: 'bookmaker_odds_history', rows: String(base.bookmaker_odds_history) },
        { table_name: 'raw_match_data', rows: String(base.raw_match_data) },
        { table_name: 'l3_features', rows: String(base.l3_features) },
        { table_name: 'match_features_training', rows: String(base.match_features_training) },
        { table_name: 'predictions', rows: String(base.predictions) },
    ];
}

function schemaRows(overrides = []) {
    return [
        {
            conname: 'collected_at_not_null',
            contype: 'c',
            definition: 'CHECK ((collected_at IS NOT NULL))',
        },
        {
            conname: 'raw_data_has_match_id',
            contype: 'c',
            definition: "CHECK (((raw_data ? 'matchId') OR (raw_data ? 'general') OR (raw_data ? 'header')))",
        },
        {
            conname: 'raw_data_not_empty',
            contype: 'c',
            definition: "CHECK (((raw_data IS NOT NULL) AND (raw_data <> '{}'::jsonb)))",
        },
        {
            conname: 'raw_match_data_match_id_data_version_key',
            contype: 'u',
            definition: 'UNIQUE (match_id, data_version)',
        },
        ...overrides,
    ];
}

function insertRows() {
    return mod.EXPECTED_TARGETS.map(target => ({
        id: Number(target.externalId) - 4830600,
        match_id: target.matchId,
        external_id: target.externalId,
        data_version: 'fotmob_pageprops_v2',
        data_hash: mod.BASELINE_HASHES[target.externalId],
        collected_at: '2026-05-16T09:00:00.000Z',
    }));
}

function fakeClient(options = {}) {
    const queries = [];
    let countQueries = 0;
    let existingQueryIndex = 0;
    let summaryQueryIndex = 0;
    return {
        queries,
        async query(sql, params = []) {
            const text = typeof sql === 'string' ? sql : sql.text;
            const normalized = text.replace(/\s+/g, ' ').trim();
            queries.push({ text, params });
            if (normalized === 'BEGIN' || normalized === 'COMMIT' || normalized === 'ROLLBACK') {
                return { rows: [], rowCount: 0 };
            }
            if (/^INSERT INTO raw_match_data/i.test(normalized)) {
                assert.doesNotMatch(normalized, /\bUPDATE\s+raw_match_data\b|\bDELETE\s+FROM\s+raw_match_data\b/i);
                assert.match(normalized, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
                assert.equal(params.length, 42);
                return {
                    rows: options.insertRows || insertRows(),
                    rowCount: options.insertedCount ?? 7,
                };
            }
            assert.match(normalized, /^SELECT\b/i);
            assert.doesNotMatch(normalized, /\b(UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|GRANT|REVOKE|COPY|LOCK)\b/i);
            if (/GROUP BY match_id, data_version HAVING COUNT\(\*\) > 1/i.test(normalized)) {
                return { rows: options.duplicateRows || [] };
            }
            if (/UNION ALL/i.test(normalized)) {
                countQueries += 1;
                if (countQueries === 1) return { rows: options.protectedRowsBefore || protectedRows() };
                return { rows: options.protectedRowsAfter || protectedRows({ raw_match_data: 18 }) };
            }
            if (/FROM pg_constraint/i.test(normalized)) return { rows: options.schemaRows || schemaRows() };
            if (/FROM matches/i.test(normalized)) return { rows: options.metadataRows || metadataRows() };
            if (/jsonb_typeof\(raw_data\)/i.test(normalized)) {
                const ids = params[0] || [];
                if (ids.includes('53_20252026_4830747')) {
                    if (summaryQueryIndex === 0) {
                        summaryQueryIndex += 1;
                        return { rows: options.excludedBeforeRows || excluded4830747Rows() };
                    }
                    return { rows: options.excludedAfterRows || excluded4830747Rows() };
                }
                return { rows: options.versionRowsAfter || versionSummaryRows() };
            }
            if (/FROM raw_match_data/i.test(normalized)) {
                if (options.existingRowsSequence) {
                    const sequenceRows =
                        options.existingRowsSequence[
                            Math.min(existingQueryIndex, options.existingRowsSequence.length - 1)
                        ];
                    existingQueryIndex += 1;
                    return { rows: sequenceRows };
                }
                return { rows: options.existingRows || existingRows() };
            }
            return { rows: [] };
        },
    };
}

async function successRun(overrides = {}) {
    const client = fakeClient(overrides.clientOptions);
    const fetchCalls = [];
    const result = await mod.runCli(validArgv(overrides.argv || {}), {
        client,
        fetchFn: async requestUrl => {
            fetchCalls.push(requestUrl);
            const externalId = requestUrl.split('/').pop();
            return fakeResponseFor(
                externalId,
                overrides.responseByExternalId?.[externalId] || overrides.response || {}
            );
        },
        recapturedHashesByExternalId: overrides.recapturedHashesByExternalId || mod.BASELINE_HASHES,
        generatedAt: '2026-05-16T09:00:00.000Z',
        now: '2026-05-16T09:00:00.000Z',
        output: overrides.output || (() => {}),
    });
    return { result, client, fetchCalls };
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validateWriteInput(validInput(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

test('valid input succeeds', () => {
    assert.equal(mod.validateWriteInput(validInput()).ok, true);
});

test('parseArgs supports equals syntax, unknown positional args, and implicit booleans', () => {
    const parsed = mod.parseArgs([
        '--source=fotmob',
        'positional',
        '--final-db-write-confirmation',
        '--unknown-flag=yes',
    ]);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.finalDbWriteConfirmation, true);
    assert.deepEqual(parsed.unknown, ['positional', 'unknown-flag']);
});

test('normalizeBooleanFlag returns fallback for unknown values', () => {
    assert.equal(mod.normalizeBooleanFlag('maybe', false), false);
});

for (const [name, override, pattern] of [
    ['source missing fails', { source: '' }, /missing source=fotmob/],
    ['source non-fotmob fails', { source: 'other' }, /source must be fotmob/],
    ['route not html_hydration fails', { route: 'api_match_details' }, /route must be html_hydration/],
    ['baseline-hashes missing fails', { baselineHashes: '' }, /missing baseline-hashes/],
    ['baseline-hashes invalid JSON fails', { baselineHashes: '{bad' }, /valid JSON/],
    [
        'baseline-hashes missing one target fails',
        { baselineHashes: JSON.stringify({ ...mod.BASELINE_HASHES, 4830754: undefined }) },
        /missing 4830754|unexpected target/,
    ],
    [
        'baseline-hashes contains 4830747 blocked',
        { baselineHashes: JSON.stringify({ ...mod.BASELINE_HASHES, 4830747: '0'.repeat(64) }) },
        /must not contain 4830747/,
    ],
    [
        'baseline-hashes extra target blocked',
        { baselineHashes: JSON.stringify({ ...mod.BASELINE_HASHES, 999: '0'.repeat(64) }) },
        /unexpected target 999/,
    ],
    [
        'candidate-version not fotmob_pageprops_v2 fails',
        { candidateVersion: 'fotmob_html_hyd_v1' },
        /candidate-version/,
    ],
    ['hash-strategy not stable_pageprops_payload_v1 fails', { hashStrategy: 'stable_raw_payload_v1' }, /hash-strategy/],
    ['network-authorization=no fails', { networkAuthorization: false }, /network-authorization=yes/],
    [
        'final-db-write-confirmation missing blocked',
        { finalDbWriteConfirmation: null },
        /missing final-db-write-confirmation/,
    ],
    ['final-db-write-confirmation=no blocked', { finalDbWriteConfirmation: false }, /final-db-write-confirmation=yes/],
    ['allow-db-write=no blocked', { allowDbWrite: false }, /allow-db-write=yes/],
    ['allow-raw-match-data-write=no blocked', { allowRawMatchDataWrite: false }, /allow-raw-match-data-write=yes/],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }, /allow-matches-write=yes is blocked/],
    ['allow-parser-features=yes blocked', { allowParserFeatures: true }, /allow-parser-features=yes is blocked/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training=yes is blocked/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction=yes is blocked/],
    ['concurrency > 1 blocked', { concurrency: 2 }, /concurrency=1/],
    ['retry > 0 blocked', { retry: 1 }, /retry=0/],
    ['print-body=yes blocked', { printBody: true }, /print-body=yes is blocked/],
    ['save-body=yes blocked', { saveBody: true }, /save-body=yes is blocked/],
    ['print-full-json=yes blocked', { printFullJson: true }, /print-full-json=yes is blocked/],
    ['save-full-json=yes blocked', { saveFullJson: true }, /save-full-json=yes is blocked/],
    [
        'browser/proxy allowed blocked',
        { allowBrowserRuntime: true, allowProxyRuntime: true },
        /browser-runtime=yes is blocked/,
    ],
    ['bulk-unbounded=yes blocked', { bulkUnbounded: true }, /bulk-unbounded=yes is blocked/],
    ['include-4830747=yes blocked', { include4830747: true }, /include4830747|include-4830747/i],
    ['partial-write=yes blocked', { partialWrite: true }, /partial-write=yes is blocked/],
    ['rewrite-existing=yes blocked', { rewriteExisting: true }, /rewrite-existing=yes is blocked/],
    ['drop-v1=yes blocked', { dropV1: true }, /drop-v1=yes is blocked/],
    [
        'schema migration flags blocked',
        { allowSchemaMigration: true, alterTable: true },
        /schema-migration=yes is blocked/,
    ],
]) {
    test(name, () => {
        assertInvalid(override, pattern);
    });
}

test('baseline-hashes duplicate target blocked', () => {
    const duplicateJson = `{"4830746":"${mod.BASELINE_HASHES['4830746']}","4830746":"${mod.BASELINE_HASHES['4830746']}"}`;
    assertInvalid({ baselineHashes: duplicateJson }, /duplicate target 4830746/);
});

test('baseline-hashes non-object JSON fails', () => {
    assertInvalid({ baselineHashes: '[]' }, /JSON object/);
});

test('fake metadata requires exactly 7 targets', () => {
    assert.throws(
        () => mod.validateTargetMetadataRows(metadataRows([{ match_id: 'x', external_id: 'x' }])),
        /ROW_COUNT:8/
    );
});

test('fake metadata missing target -> controlled error', async () => {
    const { result } = await successRun({
        clientOptions: { metadataRows: metadataRows().filter(row => row.external_id !== '4830754') },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /TARGET_METADATA_ROW_COUNT:6/);
});

test('fake existing versions v1 exists/v2 absent -> insert allowed', () => {
    const decision = mod.buildExistingVersionDecision([rawRow('4830746')]);
    assert.equal(decision.ok_to_insert, true);
});

test('fake existing versions v2 exists -> blocked', () => {
    const decision = mod.buildExistingVersionDecision([
        rawRow('4830746'),
        rawRow('4830746', { id: 99, data_version: 'fotmob_pageprops_v2' }),
    ]);
    assert.equal(decision.ok_to_insert, false);
    assert.match(decision.reason, /already exists/);
});

test('fake missing v1 -> blocked', () => {
    const decision = mod.buildExistingVersionDecision([]);
    assert.equal(decision.ok_to_insert, false);
    assert.match(decision.reason, /v1 row missing/);
});

test('duplicate match_id,data_version -> blocked', () => {
    assert.throws(
        () => mod.buildExistingVersionDecision([rawRow('4830746'), rawRow('4830746', { id: 88 })]),
        /DUPLICATE/
    );
});

test('extracts pageProps from fake HTML', () => {
    const preview = require('../../scripts/ops/pageprops_v2_no_write_preview');
    const extraction = preview.extractNextDataJsonFromHtml(fakeHtml('4830746'));
    assert.equal(extraction.ok, true);
    assert.equal(preview.getPageProps(extraction.data).general.matchId, '4830746');
});

test('computes stable hash from pageProps only', () => {
    const target = { match_id: '53_20252026_4830746', external_id: '4830746' };
    const pageProps = fakePageProps('4830746');
    const rawData = mod.buildPagePropsV2RawData({
        input: validInput(),
        target,
        pageProps,
        fetchResult: { body_sha256: 'body-one' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(rawData), mod.computeStablePagePropsHash(pageProps));
});

test('hash ignores _meta and top-level matchId', () => {
    const target = { match_id: '53_20252026_4830746', external_id: '4830746' };
    const pageProps = fakePageProps('4830746');
    const first = mod.buildPagePropsV2RawData({
        input: validInput(),
        target,
        pageProps,
        fetchResult: { body_sha256: 'one' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    const second = {
        ...first,
        _meta: { ...first._meta, generated_at: '2026-05-17T00:00:00.000Z', fetch_body_sha256: 'two' },
        matchId: 9999999,
    };
    assert.equal(mod.computeStablePagePropsHash(first), mod.computeStablePagePropsHash(second));
});

test('any hash drift blocks all writes', async () => {
    const drifts = { ...mod.BASELINE_HASHES, 4830750: '0'.repeat(64) };
    const { result, client } = await successRun({ recapturedHashesByExternalId: drifts });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /HASH_DRIFT/);
    assert.equal(
        client.queries.some(query => /^INSERT INTO raw_match_data/i.test(query.text.trim())),
        false
    );
});

test('any target 403 blocks all writes and no retry', async () => {
    const { result, client, fetchCalls } = await successRun({
        responseByExternalId: { 4830750: { status: 403, body: 'FORBIDDEN_BODY_SHOULD_NOT_PRINT' } },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /HTTP_403/);
    assert.equal(fetchCalls.filter(url => url.endsWith('/4830750')).length, 1);
    assert.equal(result.payload.retry_count, 0);
    assert.equal(
        client.queries.some(query => /^INSERT INTO raw_match_data/i.test(query.text.trim())),
        false
    );
});

test('any invalid hydration blocks all writes', async () => {
    const { result, client } = await successRun({
        responseByExternalId: { 4830751: { body: '<html>missing next data</html>' } },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /NO_NEXT_DATA/);
    assert.equal(
        client.queries.some(query => /^INSERT INTO raw_match_data/i.test(query.text.trim())),
        false
    );
});

test('all 7 hashes match -> transaction commits', async () => {
    const { result, client, fetchCalls } = await successRun();
    assert.equal(result.status, 0);
    assert.equal(result.payload.inserted_count, 7);
    assert.equal(result.payload.hash_match_count, 7);
    assert.equal(result.payload.transaction.committed, true);
    assert.equal(fetchCalls.length, 7);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'COMMIT'),
        true
    );
});

test('inserted_count != 7 -> rollback', async () => {
    const { result, client } = await successRun({
        clientOptions: { insertedCount: 6, insertRows: insertRows().slice(0, 6) },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /INSERTED_COUNT_INVALID:6/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('protected table row count drift -> rollback', async () => {
    const { result, client } = await successRun({
        clientOptions: { protectedRowsAfter: protectedRows({ raw_match_data: 18, matches: 11 }) },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /POST_WRITE_VERIFICATION_FAILED/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('postcheck failure -> rollback', async () => {
    const broken = versionSummaryRows().map(row =>
        row.external_id === '4830752' && row.data_version === 'fotmob_pageprops_v2'
            ? { ...row, has_pageprops: false }
            : row
    );
    const { result, client } = await successRun({ clientOptions: { versionRowsAfter: broken } });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /POST_WRITE_VERIFICATION_FAILED/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('post-write verification reports duplicate, excluded target, v1, hash, and shape failures', () => {
    const afterRows = versionSummaryRows()
        .map(row =>
            row.external_id === '4830746' && row.data_version === 'fotmob_html_hyd_v1'
                ? { ...row, data_hash: 'changed-v1-hash' }
                : row
        )
        .map(row =>
            row.external_id === '4830748' && row.data_version === 'fotmob_pageprops_v2'
                ? { ...row, data_hash: '0'.repeat(64) }
                : row
        )
        .map(row =>
            row.external_id === '4830750' && row.data_version === 'fotmob_pageprops_v2'
                ? { ...row, has_meta: false }
                : row
        )
        .map(row =>
            row.external_id === '4830751' && row.data_version === 'fotmob_pageprops_v2'
                ? { ...row, has_match_id: false }
                : row
        )
        .map(row =>
            row.external_id === '4830752' && row.data_version === 'fotmob_pageprops_v2'
                ? { ...row, has_pageprops: false }
                : row
        )
        .filter(row => !(row.external_id === '4830753' && row.data_version === 'fotmob_pageprops_v2'));
    const changedExcluded = excluded4830747Rows().map(row =>
        row.data_version === 'fotmob_pageprops_v2' ? { ...row, data_hash: 'changed-excluded-v2' } : row
    );
    const errors = mod.buildPostWriteVerificationErrors({
        rowCountsAfter: mod.buildProtectedTableBaseline(protectedRows({ raw_match_data: 18 })),
        beforeTargetRows: existingRows(),
        afterTargetRows: afterRows,
        excludedBeforeRows: excluded4830747Rows(),
        excludedAfterRows: changedExcluded,
        duplicateRowsAfter: [{ match_id: 'x', data_version: 'y', rows: 2 }],
    });
    assert.ok(errors.some(error => /duplicate/.test(error)));
    assert.ok(errors.some(error => /4830747 rows changed/.test(error)));
    assert.ok(errors.some(error => /4830746:v1 row changed/.test(error)));
    assert.ok(errors.some(error => /4830748:v2 data_hash/.test(error)));
    assert.ok(errors.some(error => /4830750:v2 raw_data missing _meta/.test(error)));
    assert.ok(errors.some(error => /4830751:v2 raw_data missing top-level matchId/.test(error)));
    assert.ok(errors.some(error => /4830752:v2 raw_data missing pageProps/.test(error)));
    assert.ok(errors.some(error => /4830753:post-write v2 missing/.test(error)));
});

test('raw_data shape includes _meta, matchId, pageProps', () => {
    const rawData = mod.buildPagePropsV2RawData({
        input: validInput(),
        target: { match_id: '53_20252026_4830746', external_id: '4830746' },
        pageProps: fakePageProps('4830746'),
        fetchResult: fetchResultFor('4830746'),
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.deepEqual(Object.keys(rawData).sort(), ['_meta', 'matchId', 'pageProps']);
    assert.deepEqual(mod.validateRawDataShape(rawData), []);
});

test('generated SQL uses INSERT INTO raw_match_data', () => {
    const rawData = mod.buildPagePropsV2RawData({
        target: { match_id: '53_20252026_4830746', external_id: '4830746' },
        pageProps: fakePageProps('4830746'),
    });
    const sql = mod.buildInsertRawMatchDataSql({
        recapturedTargets: [{ match_id: '53_20252026_4830746', external_id: '4830746', rawData, recaptured_hash: 'x' }],
        collectedAt: '2026-05-16T09:00:00.000Z',
    });
    assert.match(sql.text, /INSERT INTO raw_match_data/i);
});

test('generated SQL conflict target is match_id,data_version', () => {
    const rawData = mod.buildPagePropsV2RawData({
        target: { match_id: '53_20252026_4830746', external_id: '4830746' },
        pageProps: fakePageProps('4830746'),
    });
    const sql = mod.buildInsertRawMatchDataSql({
        recapturedTargets: [{ match_id: '53_20252026_4830746', external_id: '4830746', rawData, recaptured_hash: 'x' }],
        collectedAt: '2026-05-16T09:00:00.000Z',
    });
    assert.match(sql.text, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
});

test('no UPDATE raw_match_data generated', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        recapturedTargets: [],
        collectedAt: '2026-05-16T09:00:00.000Z',
    });
    assert.doesNotMatch(sql.text, /\bUPDATE\s+raw_match_data\b/i);
});

test('no DELETE raw_match_data generated', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        recapturedTargets: [],
        collectedAt: '2026-05-16T09:00:00.000Z',
    });
    assert.doesNotMatch(sql.text, /\bDELETE\s+FROM\s+raw_match_data\b/i);
});

test('no matches write generated', async () => {
    const { client } = await successRun();
    assert.equal(
        client.queries.some(query => /\bINSERT\s+INTO\s+matches\b|\bUPDATE\s+matches\b/i.test(query.text)),
        false
    );
});

test('no schema migration SQL generated', async () => {
    const { client } = await successRun();
    assert.equal(
        client.queries.some(query => /\bALTER\s+TABLE\b|\bCREATE\s+INDEX\b|\bDROP\s+INDEX\b/i.test(query.text)),
        false
    );
});

test('no full body/json print/save', async () => {
    let rendered = '';
    const body = fakeHtml('4830746', fakePageProps('4830746', { secretContainer: { value: 'BODY_SECRET_VALUE' } }));
    const { result } = await successRun({
        responseByExternalId: { 4830746: { body } },
        output: payload => {
            rendered = JSON.stringify(payload);
        },
    });
    assert.equal(result.status, 0);
    assert.equal(rendered.includes(body), false);
    assert.equal(rendered.includes('BODY_SECRET_VALUE'), false);
});

test('schema check blocks legacy match_id unique and missing checks', () => {
    const errors = mod.validateSchemaConstraints(
        schemaRows([{ conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' }]).filter(
            row => row.conname !== 'raw_data_not_empty'
        )
    );
    assert.ok(errors.some(error => /match_id_key/.test(error)));
    assert.ok(errors.some(error => /raw_data_not_empty/.test(error)));
});

test('querySelectOnly blocks non-SELECT and SELECT containing write keywords', async () => {
    await assert.rejects(() => mod.querySelectOnly(fakeClient(), 'BEGIN'), /NON_SELECT_SQL_BLOCKED/);
    await assert.rejects(
        () => mod.querySelectOnly(fakeClient(), 'SELECT * FROM x FOR UPDATE'),
        /SQL_WRITE_OR_LOCK_BLOCKED/
    );
});

test('executeControlledWrite blocks invalid schema before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({
            schemaRows: schemaRows().filter(row => row.conname !== 'raw_match_data_match_id_data_version_key'),
        }),
        fetchFn: async requestUrl => {
            calls += 1;
            return fakeResponseFor(requestUrl.split('/').pop());
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /SCHEMA_CONSTRAINT_INVALID/);
});

test('executeControlledWrite blocks pre-existing v2 before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({
            existingRows: existingRows([
                rawRow('4830748', {
                    id: 99,
                    data_version: 'fotmob_pageprops_v2',
                    data_hash: mod.BASELINE_HASHES['4830748'],
                }),
            ]),
        }),
        fetchFn: async requestUrl => {
            calls += 1;
            return fakeResponseFor(requestUrl.split('/').pop());
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /PRE_WRITE_VERSION_BLOCKED/);
});

test('executeControlledWrite blocks duplicate before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({ duplicateRows: [{ match_id: 'x', data_version: 'y', rows: 2 }] }),
        fetchFn: async requestUrl => {
            calls += 1;
            return fakeResponseFor(requestUrl.split('/').pop());
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /DUPLICATE_MATCH_ID_DATA_VERSION/);
});

test('executeControlledWrite rolls back if v2 appears during transaction recheck', async () => {
    const client = fakeClient({
        existingRowsSequence: [
            existingRows(),
            existingRows([
                rawRow('4830753', {
                    id: 100,
                    data_version: 'fotmob_pageprops_v2',
                    data_hash: mod.BASELINE_HASHES['4830753'],
                }),
            ]),
        ],
    });
    const result = await mod.runCli(validArgv(), {
        client,
        fetchFn: async requestUrl => fakeResponseFor(requestUrl.split('/').pop()),
        recapturedHashesByExternalId: mod.BASELINE_HASHES,
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /TX_VERSION_BLOCKED/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('executeControlledWrite catch path rolls back on insert throw', async () => {
    const client = fakeClient();
    const originalQuery = client.query;
    client.query = async (sql, params) => {
        const text = typeof sql === 'string' ? sql : sql.text;
        if (/INSERT INTO raw_match_data/i.test(text)) {
            throw new Error('insert failed');
        }
        return originalQuery.call(client, sql, params);
    };
    const result = await mod.runCli(validArgv(), {
        client,
        fetchFn: async requestUrl => fakeResponseFor(requestUrl.split('/').pop()),
        recapturedHashesByExternalId: mod.BASELINE_HASHES,
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /insert failed/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('acquire path supports pool.connect with release and end', async () => {
    let released = false;
    let ended = false;
    const client = fakeClient();
    client.release = () => {
        released = true;
    };
    const pool = {
        async connect() {
            return client;
        },
        async end() {
            ended = true;
        },
    };
    const result = await mod.runCli(validArgv(), {
        createPool: () => pool,
        fetchFn: async requestUrl => fakeResponseFor(requestUrl.split('/').pop()),
        recapturedHashesByExternalId: mod.BASELINE_HASHES,
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(released, true);
    assert.equal(ended, true);
});

test('no fs write / mkdir', () => {
    const originals = {
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        mkdir: fs.mkdir,
        mkdirSync: fs.mkdirSync,
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
    fs.mkdirSync = () => {
        called = true;
        throw new Error('fs.mkdirSync blocked');
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
        fs.mkdirSync = originals.mkdirSync;
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

test('no unexpected network when injected fetch is used', async () => {
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
        const { result } = await successRun();
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
