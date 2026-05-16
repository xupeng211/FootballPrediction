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

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_single_target_controlled_write.js');
const BASELINE_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';

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
        baselinePagepropsHash: BASELINE_HASH,
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
        'match-id': '53_20252026_4830747',
        'external-id': '4830747',
        'home-team': 'Auxerre',
        'away-team': 'Nice',
        'candidate-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'baseline-pageprops-hash': BASELINE_HASH,
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

function rawRow(overrides = {}) {
    return {
        id: 4,
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: '8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25',
        collected_at: '2026-05-15T15:27:31.214Z',
        ...overrides,
    };
}

function versionSummaryRows(overrides = []) {
    return [
        {
            ...rawRow(),
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: false,
        },
        {
            id: 11,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            data_version: 'fotmob_pageprops_v2',
            data_hash: BASELINE_HASH,
            collected_at: '2026-05-16T09:00:00.000Z',
            raw_data_type: 'object',
            has_meta: true,
            has_match_id: true,
            has_pageprops: true,
        },
        ...overrides,
    ];
}

function protectedRows(values = {}) {
    const base = {
        matches: 10,
        bookmaker_odds_history: 2,
        raw_match_data: 10,
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

function fakeClient(options = {}) {
    const queries = [];
    let countQueries = 0;
    let existingQueryIndex = 0;
    const existingRows = options.existingRows || [rawRow()];
    return {
        queries,
        async query(sql, params = []) {
            const text = typeof sql === 'string' ? sql : sql.text;
            const normalized = text.replace(/\s+/g, ' ').trim();
            queries.push({ text, params });
            if (normalized === 'BEGIN' || normalized === 'COMMIT' || normalized === 'ROLLBACK') {
                if (options.failRollback && normalized === 'ROLLBACK') throw new Error('rollback failed');
                return { rows: [], rowCount: 0 };
            }
            if (/^INSERT INTO raw_match_data/i.test(normalized)) {
                assert.doesNotMatch(normalized, /\bUPDATE\s+raw_match_data\b|\bDELETE\s+FROM\s+raw_match_data\b/i);
                assert.match(normalized, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
                return {
                    rows: options.insertRows || [
                        {
                            id: 11,
                            match_id: '53_20252026_4830747',
                            external_id: '4830747',
                            data_version: 'fotmob_pageprops_v2',
                            data_hash: BASELINE_HASH,
                            collected_at: '2026-05-16T09:00:00.000Z',
                        },
                    ],
                    rowCount: options.insertedCount ?? 1,
                };
            }
            assert.match(normalized, /^SELECT\b/i);
            assert.doesNotMatch(normalized, /\b(UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|GRANT|REVOKE|COPY|LOCK)\b/i);
            if (/UNION ALL/i.test(normalized)) {
                countQueries += 1;
                if (countQueries === 1) return { rows: options.protectedRowsBefore || protectedRows() };
                return {
                    rows: options.protectedRowsAfter || protectedRows({ raw_match_data: 11 }),
                };
            }
            if (/FROM pg_constraint/i.test(normalized)) return { rows: options.schemaRows || schemaRows() };
            if (/FROM matches/i.test(normalized)) return { rows: options.matchRows || [matchMetadata()] };
            if (/jsonb_typeof\(raw_data\)/i.test(normalized)) {
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
                return { rows: existingRows };
            }
            return { rows: [] };
        },
    };
}

async function successRun(overrides = {}) {
    const client = fakeClient(overrides.clientOptions);
    const result = await mod.runCli(validArgv(overrides.argv || {}), {
        client,
        fetchFn: async () => fakeResponse(overrides.response || {}),
        recapturedHashOverride: Object.prototype.hasOwnProperty.call(overrides, 'recapturedHashOverride')
            ? overrides.recapturedHashOverride
            : BASELINE_HASH,
        generatedAt: '2026-05-16T09:00:00.000Z',
        now: '2026-05-16T09:00:00.000Z',
        output: () => {},
    });
    return { result, client };
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

test('missing required no flag fails explicitly', () => {
    const validation = mod.validateWriteInput(validInput({ allowMatchesWrite: null }));
    assert.equal(validation.ok, false);
    assert.ok(validation.errors.some(error => /missing allow-matches-write=no/.test(error)));
});

for (const [name, override] of [
    ['source missing fails', { source: '' }],
    ['source non-fotmob fails', { source: 'other' }],
    ['route not html_hydration fails', { route: 'api_match_details' }],
    ['match-id wrong fails', { matchId: 'wrong' }],
    ['external-id wrong fails', { externalId: '4830748' }],
    ['home-team wrong fails', { homeTeam: 'Angers' }],
    ['away-team wrong fails', { awayTeam: 'Brest' }],
    ['candidate-version not fotmob_pageprops_v2 fails', { candidateVersion: 'fotmob_html_hyd_v1' }],
    ['hash-strategy not stable_pageprops_payload_v1 fails', { hashStrategy: 'stable_raw_payload_v1' }],
    ['baseline-pageprops-hash missing fails', { baselinePagepropsHash: '' }],
    ['baseline-pageprops-hash invalid fails', { baselinePagepropsHash: 'not-a-hash' }],
    ['baseline-pageprops-hash wrong valid hash fails', { baselinePagepropsHash: '0'.repeat(64) }],
    ['network-authorization=no fails', { networkAuthorization: false }],
    ['final-db-write-confirmation missing blocked', { finalDbWriteConfirmation: null }],
    ['final-db-write-confirmation=no blocked', { finalDbWriteConfirmation: false }],
    ['allow-db-write=no blocked', { allowDbWrite: false }],
    ['allow-raw-match-data-write=no blocked', { allowRawMatchDataWrite: false }],
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
    ['bulk / execute-multiple blocked', { bulk: true, executeMultiple: true }],
    ['rewrite-existing=yes blocked', { rewriteExisting: true }],
    ['drop-v1=yes blocked', { dropV1: true }],
    ['schema migration flags blocked', { allowSchemaMigration: true, alterTable: true }],
]) {
    test(name, () => {
        assert.equal(mod.validateWriteInput(validInput(override)).ok, false);
    });
}

test('extracts pageProps from fake HTML', () => {
    const preview = require('../../scripts/ops/pageprops_v2_no_write_preview');
    const extraction = preview.extractNextDataJsonFromHtml(fakeHtml());
    assert.equal(extraction.ok, true);
    assert.equal(preview.getPageProps(extraction.data).general.matchId, '4830747');
});

test('computes stable hash from pageProps only', () => {
    const pageProps = fakePageProps();
    const rawData = mod.buildPagePropsV2RawData({
        input: validInput(),
        pageProps,
        fetchResult: { body_sha256: 'body-one' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.equal(mod.computeStablePagePropsHash(rawData), mod.computeStablePagePropsHash(pageProps));
});

test('hash ignores _meta and top-level matchId', () => {
    const pageProps = fakePageProps();
    const first = mod.buildPagePropsV2RawData({
        input: validInput(),
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

test('hash drift blocks write', async () => {
    const { result, client } = await successRun({ recapturedHashOverride: null });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /HASH_DRIFT/);
    assert.equal(
        client.queries.some(query => /^INSERT INTO raw_match_data/i.test(query.text.trim())),
        false
    );
});

test('v1 exists / v2 absent -> insert allowed', () => {
    const decision = mod.buildExistingVersionDecision([rawRow()]);
    assert.equal(decision.ok_to_insert, true);
});

test('v2 exists -> no insert / blocked for this single insert phase', () => {
    const decision = mod.buildExistingVersionDecision([
        rawRow(),
        rawRow({ id: 11, data_version: 'fotmob_pageprops_v2', data_hash: BASELINE_HASH }),
    ]);
    assert.equal(decision.ok_to_insert, false);
    assert.match(decision.reason, /already exists/);
});

test('missing v1 -> blocked', () => {
    const decision = mod.buildExistingVersionDecision([]);
    assert.equal(decision.ok_to_insert, false);
    assert.match(decision.reason, /v1 row missing/);
});

test('duplicate match_id,data_version -> blocked', () => {
    assert.throws(() => mod.buildExistingVersionDecision([rawRow(), rawRow({ id: 12 })]), /DUPLICATE/);
});

test('raw_data shape includes _meta, matchId, pageProps', () => {
    const rawData = mod.buildPagePropsV2RawData({
        input: validInput(),
        pageProps: fakePageProps(),
        fetchResult: { body_sha256: 'body-sha' },
        generatedAt: '2026-05-16T00:00:00.000Z',
    });
    assert.deepEqual(Object.keys(rawData).sort(), ['_meta', 'matchId', 'pageProps']);
});

test('raw_data shape satisfies matchId check expectation', () => {
    const rawData = mod.buildPagePropsV2RawData({ input: validInput(), pageProps: fakePageProps() });
    assert.equal(Object.prototype.hasOwnProperty.call(rawData, 'matchId'), true);
    assert.deepEqual(mod.validateRawDataShape(rawData), []);
});

test('fake DB transaction commits on successful insert', async () => {
    const { result, client } = await successRun();
    assert.equal(result.status, 0);
    assert.equal(result.payload.inserted_count, 1);
    assert.equal(result.payload.transaction.committed, true);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'COMMIT'),
        true
    );
});

test('fake DB rollback on insert_count != 1', async () => {
    const { result, client } = await successRun({ clientOptions: { insertedCount: 0, insertRows: [] } });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /INSERTED_COUNT_INVALID/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('fake DB rollback on protected table row count change', async () => {
    const { result, client } = await successRun({
        clientOptions: { protectedRowsAfter: protectedRows({ raw_match_data: 11, matches: 11 }) },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /POST_WRITE_VERIFICATION_FAILED/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('fake DB rollback on postcheck failure', async () => {
    const { result, client } = await successRun({
        clientOptions: {
            versionRowsAfter: versionSummaryRows([
                { data_version: 'fotmob_pageprops_v2', has_pageprops: false },
            ]).filter(row => row.data_version !== 'fotmob_pageprops_v2' || row.has_pageprops === false),
        },
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /POST_WRITE_VERIFICATION_FAILED/);
    assert.equal(
        client.queries.some(query => query.text.trim() === 'ROLLBACK'),
        true
    );
});

test('generated SQL uses INSERT INTO raw_match_data', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        input: validInput(),
        rawData: mod.buildPagePropsV2RawData({ input: validInput(), pageProps: fakePageProps() }),
        collectedAt: '2026-05-16T09:00:00.000Z',
        dataHash: BASELINE_HASH,
    });
    assert.match(sql.text, /INSERT INTO raw_match_data/i);
});

test('generated SQL conflict target is match_id,data_version', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        input: validInput(),
        rawData: mod.buildPagePropsV2RawData({ input: validInput(), pageProps: fakePageProps() }),
        collectedAt: '2026-05-16T09:00:00.000Z',
        dataHash: BASELINE_HASH,
    });
    assert.match(sql.text, /ON CONFLICT\s*\(\s*match_id\s*,\s*data_version\s*\) DO NOTHING/i);
});

test('no UPDATE raw_match_data generated', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        input: validInput(),
        rawData: mod.buildPagePropsV2RawData({ input: validInput(), pageProps: fakePageProps() }),
        collectedAt: '2026-05-16T09:00:00.000Z',
        dataHash: BASELINE_HASH,
    });
    assert.doesNotMatch(sql.text, /\bUPDATE\s+raw_match_data\b/i);
});

test('no DELETE raw_match_data generated', () => {
    const sql = mod.buildInsertRawMatchDataSql({
        input: validInput(),
        rawData: mod.buildPagePropsV2RawData({ input: validInput(), pageProps: fakePageProps() }),
        collectedAt: '2026-05-16T09:00:00.000Z',
        dataHash: BASELINE_HASH,
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
    const body = fakeHtml(fakeNextData(fakePageProps({ secretContainer: { value: 'BODY_SECRET_VALUE' } })));
    await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => fakeResponse({ body }),
        recapturedHashOverride: BASELINE_HASH,
        output: payload => {
            rendered = JSON.stringify(payload);
        },
    });
    assert.equal(rendered.includes(body), false);
    assert.equal(rendered.includes('BODY_SECRET_VALUE'), false);
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
    assert.equal(result.payload.retry_count, 0);
    assert.equal(result.payload.raw_match_data_write_executed, false);
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
    assert.match(result.payload.failure_reason, /NO_NEXT_DATA/);
});

test('schema check blocks legacy match_id unique', () => {
    const errors = mod.validateSchemaConstraints(
        schemaRows([{ conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' }])
    );
    assert.ok(errors.some(error => /match_id_key/.test(error)));
});

test('schema check requires raw_data_has_match_id', () => {
    const errors = mod.validateSchemaConstraints(schemaRows().filter(row => row.conname !== 'raw_data_has_match_id'));
    assert.ok(errors.some(error => /raw_data_has_match_id/.test(error)));
});

test('schema check requires versioned unique definition and raw_data_not_empty', () => {
    const rows = schemaRows()
        .filter(row => row.conname !== 'raw_data_not_empty')
        .map(row =>
            row.conname === 'raw_match_data_match_id_data_version_key'
                ? { ...row, definition: 'UNIQUE (match_id)' }
                : row
        );
    const errors = mod.validateSchemaConstraints(rows);
    assert.ok(errors.some(error => /UNIQUE/.test(error)));
    assert.ok(errors.some(error => /raw_data_not_empty/.test(error)));
});

test('post-write verification requires v2 hash baseline', () => {
    const errors = mod.buildPostWriteVerificationErrors({
        beforeRows: [rawRow()],
        afterRows: versionSummaryRows([{ data_version: 'fotmob_pageprops_v2', data_hash: '0'.repeat(64) }]).filter(
            row => !(row.data_version === 'fotmob_pageprops_v2' && row.data_hash === BASELINE_HASH)
        ),
        rowCountsAfter: mod.buildProtectedTableBaseline(protectedRows({ raw_match_data: 11 })),
    });
    assert.ok(errors.some(error => /data_hash/.test(error)));
});

test('querySelectOnly blocks non-SELECT and SELECT containing write keywords', async () => {
    await assert.rejects(() => mod.querySelectOnly(fakeClient(), 'BEGIN'), /NON_SELECT_SQL_BLOCKED/);
    await assert.rejects(
        () => mod.querySelectOnly(fakeClient(), 'SELECT * FROM x FOR UPDATE'),
        /SQL_WRITE_OR_LOCK_BLOCKED/
    );
});

test('loadTargetMatchMetadata rejects missing target row', async () => {
    await assert.rejects(
        () =>
            mod.loadTargetMatchMetadata(fakeClient({ matchRows: [] }), {
                matchId: '53_20252026_4830747',
                externalId: '4830747',
            }),
        /TARGET_MATCH_ROW_COUNT:0/
    );
});

test('executeControlledWrite blocks invalid schema before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({
            schemaRows: schemaRows().filter(row => row.conname !== 'raw_match_data_match_id_data_version_key'),
        }),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse();
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /SCHEMA_CONSTRAINT_INVALID/);
});

test('executeControlledWrite blocks target metadata mismatch before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({ matchRows: [matchMetadata({ home_team: 'Wrong' })] }),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse();
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /TARGET_MATCH_INVALID/);
});

test('executeControlledWrite blocks pre-existing v2 before fetch', async () => {
    let calls = 0;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient({
            existingRows: [rawRow(), rawRow({ id: 11, data_version: 'fotmob_pageprops_v2', data_hash: BASELINE_HASH })],
        }),
        fetchFn: async () => {
            calls += 1;
            return fakeResponse();
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(calls, 0);
    assert.match(result.payload.failure_reason, /PRE_WRITE_VERSION_BLOCKED/);
});

test('executeControlledWrite blocks PAGE_PROPS_NOT_FOUND', async () => {
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        fetchFn: async () => fakeResponse({ body: fakeHtml({ props: { pageProps: null } }) }),
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /PAGE_PROPS_NOT_FOUND/);
});

test('executeControlledWrite rolls back if v2 appears during transaction recheck', async () => {
    const client = fakeClient({
        existingRowsSequence: [
            [rawRow()],
            [rawRow(), rawRow({ id: 11, data_version: 'fotmob_pageprops_v2', data_hash: BASELINE_HASH })],
        ],
    });
    const result = await mod.runCli(validArgv(), {
        client,
        fetchFn: async () => fakeResponse(),
        recapturedHashOverride: BASELINE_HASH,
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
        fetchFn: async () => fakeResponse(),
        recapturedHashOverride: BASELINE_HASH,
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
        fetchFn: async () => fakeResponse(),
        recapturedHashOverride: BASELINE_HASH,
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(released, true);
    assert.equal(ended, true);
});

test('acquire path supports queryable pool without connect', async () => {
    const client = fakeClient();
    let ended = false;
    client.end = async () => {
        ended = true;
    };
    const result = await mod.runCli(validArgv(), {
        createPool: () => client,
        fetchFn: async () => fakeResponse(),
        recapturedHashOverride: BASELINE_HASH,
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(ended, true);
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
        if (/ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/i.test(request)) {
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
        if (/NextDataParser|feature|train|predict/i.test(request)) {
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
