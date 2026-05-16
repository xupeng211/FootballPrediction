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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_post_write_canonical_read_verification.js');
const EXPECTED_HASH = 'f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc';

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        targetMatchId: '53_20252026_4830747',
        targetExternalId: '4830747',
        expectedTargetVersion: 'fotmob_pageprops_v2',
        fallbackVersion: 'fotmob_html_hyd_v1',
        expectedTargetHash: EXPECTED_HASH,
        allowDbWrite: false,
        allowNetwork: false,
        allowParserFeatures: false,
        allowTraining: false,
        allowPrediction: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        table: 'raw_match_data',
        'target-match-id': '53_20252026_4830747',
        'target-external-id': '4830747',
        'expected-target-version': 'fotmob_pageprops_v2',
        'fallback-version': 'fotmob_html_hyd_v1',
        'expected-target-hash': EXPECTED_HASH,
        'allow-db-write': 'no',
        'allow-network': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function rowCounts(overrides = {}) {
    const base = {
        matches: 10,
        raw_match_data: 11,
        bookmaker_odds_history: 2,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...overrides,
    };
    return [
        { table_name: 'matches', rows: base.matches },
        { table_name: 'bookmaker_odds_history', rows: base.bookmaker_odds_history },
        { table_name: 'raw_match_data', rows: base.raw_match_data },
        { table_name: 'l3_features', rows: base.l3_features },
        { table_name: 'match_features_training', rows: base.match_features_training },
        { table_name: 'predictions', rows: base.predictions },
    ];
}

function constraints(overrides = []) {
    return [
        {
            conname: 'raw_match_data_match_id_data_version_key',
            contype: 'u',
            definition: 'UNIQUE (match_id, data_version)',
        },
        ...overrides,
    ];
}

function distribution(overrides = []) {
    return [
        { data_version: 'PHASE4.23', rows: 1 },
        { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
        { data_version: 'fotmob_html_hyd_v1', rows: 8 },
        { data_version: 'fotmob_pageprops_v2', rows: 1 },
        ...overrides,
    ];
}

function rawRow(overrides = {}) {
    return {
        id: 1,
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        data_version: 'fotmob_html_hyd_v1',
        data_hash: `hash-${overrides.external_id || '4830746'}`,
        collected_at: '2026-05-16T00:00:00.000Z',
        has_meta: true,
        has_match_id: true,
        has_content: true,
        has_pageprops: false,
        ...overrides,
    };
}

function seededRows(overrides = []) {
    return [
        rawRow({ id: 1, match_id: '53_20252026_4830746', external_id: '4830746' }),
        rawRow({
            id: 4,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            data_version: 'fotmob_html_hyd_v1',
            data_hash: 'v1-hash',
        }),
        rawRow({
            id: 11,
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            data_version: 'fotmob_pageprops_v2',
            data_hash: EXPECTED_HASH,
            has_content: false,
            has_pageprops: true,
        }),
        rawRow({ id: 3, match_id: '53_20252026_4830748', external_id: '4830748' }),
        rawRow({ id: 5, match_id: '53_20252026_4830750', external_id: '4830750' }),
        rawRow({ id: 6, match_id: '53_20252026_4830751', external_id: '4830751' }),
        rawRow({ id: 7, match_id: '53_20252026_4830752', external_id: '4830752' }),
        rawRow({ id: 8, match_id: '53_20252026_4830753', external_id: '4830753' }),
        rawRow({ id: 9, match_id: '53_20252026_4830754', external_id: '4830754' }),
        ...overrides,
    ];
}

function legacyRows(overrides = []) {
    return [
        {
            id: 100,
            match_id: 'legacy_phase423',
            external_id: 'legacy423',
            data_version: 'PHASE4.23',
            data_hash: 'legacy-hash',
            raw_data: { secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT' },
        },
        {
            id: 101,
            match_id: 'legacy_synthetic',
            external_id: 'synthetic',
            data_version: 'PHASE4.43_SYNTHETIC',
            data_hash: 'synthetic-hash',
            raw_data: { secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT' },
        },
        ...overrides,
    ];
}

function verificationRows(overrides = {}) {
    return {
        rowCounts: rowCounts(overrides.rowCounts),
        constraints: constraints(overrides.constraints),
        seededRows: overrides.seededRows || seededRows(),
        legacyRows: overrides.legacyRows || legacyRows(),
        distribution: overrides.distribution || distribution(),
        duplicates: overrides.duplicates || [],
    };
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validateVerificationInput(validInput(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
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
        throw new Error(`${name} should not be called by pageprops_v2_post_write_canonical_read_verification`);
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
            /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data|parser|features|training/i.test(
                request
            )
        ) {
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

function fakePool(rows = verificationRows()) {
    const queries = [];
    return {
        queries,
        async query(sql, values = []) {
            const text = String(sql || '').trim();
            queries.push({ text, values });
            assert.match(text, /^SELECT\b/i);
            assert.doesNotMatch(
                text,
                /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|MERGE|COPY|BEGIN|COMMIT|ROLLBACK)\b/i
            );
            if (text.includes("'matches' AS table_name")) return { rows: rows.rowCounts };
            if (text.includes('FROM pg_constraint')) return { rows: rows.constraints };
            if (text.includes('WHERE r.match_id = ANY')) return { rows: rows.seededRows };
            if (text.includes('WHERE data_version <> ALL')) return { rows: rows.legacyRows };
            if (text.includes('GROUP BY data_version')) return { rows: rows.distribution };
            if (text.includes('HAVING COUNT(*) > 1')) return { rows: rows.duplicates };
            throw new Error(`unexpected query: ${text}`);
        },
    };
}

test('valid input succeeds', () => {
    assert.equal(mod.validateVerificationInput(validInput()).ok, true);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source=fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('table missing fails', () => assertInvalid({ table: '' }, /missing table=raw_match_data/));
test('table not raw_match_data fails', () => assertInvalid({ table: 'matches' }, /table must be raw_match_data/));
test('target-match-id wrong fails', () =>
    assertInvalid({ targetMatchId: '53_20252026_4830748' }, /target-match-id must be 53_20252026_4830747/));
test('target-external-id wrong fails', () =>
    assertInvalid({ targetExternalId: '4830748' }, /target-external-id must be 4830747/));
test('expected-target-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid(
        { expectedTargetVersion: 'fotmob_html_hyd_v1' },
        /expected-target-version must be fotmob_pageprops_v2/
    ));
test('fallback-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ fallbackVersion: 'PHASE4.23' }, /fallback-version must be fotmob_html_hyd_v1/));
test('expected-target-hash missing fails', () =>
    assertInvalid({ expectedTargetHash: '' }, /missing expected-target-hash/));
test('expected-target-hash invalid fails', () =>
    assertInvalid({ expectedTargetHash: 'NOT_HEX' }, /64-char lowercase hex/));
test('expected-target-hash wrong valid hash fails', () =>
    assertInvalid({ expectedTargetHash: 'a'.repeat(64) }, /expected-target-hash must equal/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-network=yes blocked', () => assertInvalid({ allowNetwork: true }, /allow-network=yes is blocked/));
test('allow-parser-features=yes blocked', () =>
    assertInvalid({ allowParserFeatures: true }, /allow-parser-features=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('touch-fotmob=yes blocked', () => assertInvalid({ touchFotmob: true }, /touch-fotmob=yes is blocked/));
test('live-request=yes blocked', () => assertInvalid({ liveRequest: true }, /live-request=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-schema-migration=yes blocked', () =>
    assertInvalid({ allowSchemaMigration: true }, /allow-schema-migration=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));

test('parseArgs supports equals syntax and unknown args', () => {
    const parsed = mod.parseArgs([...validArgv(), '--unknown-flag=yes', 'positional']);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.allowDbWrite, false);
    assert.deepEqual(parsed.unknown, ['unknown-flag', 'positional']);
});

test('fake dataset selects v2 for target with v1+v2', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.ok, true);
    assert.deepEqual(result.target_verification.available_versions, ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2']);
    assert.equal(result.target_verification.canonical_selected_version, 'fotmob_pageprops_v2');
    assert.equal(result.target_verification.canonical_selected_hash, EXPECTED_HASH);
    assert.equal(result.target_verification.hash_matches_expected, true);
    assert.equal(result.target_verification.has_meta, true);
    assert.equal(result.target_verification.has_matchId, true);
    assert.equal(result.target_verification.has_pageProps, true);
});

test('fake dataset hash mismatch reports controlled failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows([
            rawRow({
                id: 12,
                match_id: '53_20252026_4830747',
                external_id: '4830747',
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'b'.repeat(64),
                has_pageprops: true,
            }),
        ]).filter(row => !(row.id === 11)),
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /hash mismatch/);
});

test('fake dataset target missing v2 reports failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(row => row.data_version !== 'fotmob_pageprops_v2'),
        distribution: [
            { data_version: 'PHASE4.23', rows: 1 },
            { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
            { data_version: 'fotmob_html_hyd_v1', rows: 8 },
            { data_version: 'fotmob_pageprops_v2', rows: 1 },
        ],
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /target fotmob_pageprops_v2 row is missing/);
});

test('fake dataset target missing v1 but has v2 still selects v2 and reports warning', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(
            row => !(row.match_id === '53_20252026_4830747' && row.data_version === 'fotmob_html_hyd_v1')
        ),
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.target_verification.canonical_selected_version, 'fotmob_pageprops_v2');
    assert.match(result.warnings.join('\n'), /target fotmob_html_hyd_v1 row is missing/);
});

test('fake dataset remaining seeded matches fallback to v1', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.fallback_verification.seeded_matches_checked, 7);
    assert.equal(result.fallback_verification.fallback_to_v1_count, 7);
    assert.equal(result.fallback_verification.unexpected_missing_count, 0);
    assert.equal(result.fallback_verification.unexpected_v2_count, 0);
});

test('fake dataset remaining seeded missing v1 reports failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(row => row.match_id !== '53_20252026_4830754'),
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830754 missing fotmob_html_hyd_v1/);
});

test('fake dataset unexpected v2 in fallback set reports failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows([
            rawRow({
                id: 99,
                match_id: '53_20252026_4830754',
                external_id: '4830754',
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'unexpected',
                has_pageprops: true,
            }),
        ]),
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830754 unexpectedly has fotmob_pageprops_v2/);
});

test('synthetic excluded by default', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.excluded_versions_verification.synthetic_excluded, true);
    const synthetic = result.excluded_versions_verification.excluded_rows.find(
        row => row.data_version === 'PHASE4.43_SYNTHETIC'
    );
    assert.equal(synthetic.canonical_selected_version, null);
});

test('unknown legacy PHASE4.23 excluded by default', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.excluded_versions_verification.phase4_23_excluded, true);
    const phase423 = result.excluded_versions_verification.excluded_rows.find(row => row.data_version === 'PHASE4.23');
    assert.equal(phase423.canonical_selected_version, null);
});

test('arbitrary unknown versions are excluded by default', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            legacyRows: legacyRows([{ id: 102, match_id: 'unknown', external_id: 'unknown', data_version: 'mystery' }]),
        }),
    });
    assert.equal(result.excluded_versions_verification.unknown_excluded, true);
});

test('duplicate match_id,data_version controlled error', async () => {
    const rows = verificationRows({
        duplicates: [{ match_id: '53_20252026_4830747', data_version: 'fotmob_pageprops_v2', rows: 2 }],
        seededRows: seededRows([
            rawRow({
                id: 12,
                match_id: '53_20252026_4830747',
                external_id: '4830747',
                data_version: 'fotmob_pageprops_v2',
                data_hash: EXPECTED_HASH,
                has_pageprops: true,
            }),
        ]),
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /duplicate match_id,data_version/);
});

test('schema unique(match_id,data_version) required', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({ constraints: [] }),
    });
    assert.equal(result.schema.unique_match_id_data_version, true);
});

test('schema unique(match_id,data_version) missing fails', async () => {
    const rows = verificationRows({
        constraints: [{ conname: 'other_constraint', contype: 'u', definition: 'UNIQUE (external_id)' }],
    });
    rows.constraints = [{ conname: 'other_constraint', contype: 'u', definition: 'UNIQUE (external_id)' }];
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.equal(result.schema.unique_match_id_data_version, false);
});

test('schema unique(match_id only) absent required', async () => {
    const rows = verificationRows({
        constraints: [{ conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' }],
    });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.equal(result.schema.unique_match_id_only, true);
});

test('row count expectation raw_match_data=11', async () => {
    const rows = verificationRows({ rowCounts: { raw_match_data: 10 } });
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /raw_match_data expected 11/);
});

test('data_version distribution expectation includes v2=1', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            distribution: [
                { data_version: 'PHASE4.23', rows: 1 },
                { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
                { data_version: 'fotmob_html_hyd_v1', rows: 8 },
                { data_version: 'fotmob_pageprops_v2', rows: 0 },
            ],
        }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /fotmob_pageprops_v2 expected 1/);
});

test('no raw_data full print', async () => {
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.doesNotMatch(JSON.stringify(result), /SECRET_RAW_DATA_SHOULD_NOT_PRINT/);
});

test('no DB write through fake pool', async () => {
    const pool = fakePool();
    const result = await mod.buildPostWriteCanonicalReadVerification(validInput(), { pool });
    assert.equal(result.ok, true);
    assert.equal(result.db_write_executed, false);
    assert.equal(result.raw_match_data_write_executed, false);
    assert.equal(pool.queries.length, 6);
    for (const query of pool.queries) {
        assert.match(query.text, /^SELECT\b/i);
        assert.doesNotMatch(query.text, /\bINSERT|UPDATE|DELETE|ALTER|DROP|CREATE\b/i);
    }
});

test('no network/fs/child_process/import side effects when guarded', async t => {
    installExecutionGuards(t);
    const gate = loadFreshModule();
    const result = await gate.buildPostWriteCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.ok, true);
    assert.equal(result.network_executed, false);
});

test('assertSelectOnly blocks non-SELECT and SELECT containing writes', () => {
    assert.throws(() => mod.assertSelectOnly('UPDATE raw_match_data SET data_hash = $1'), /NON_SELECT_SQL_BLOCKED/);
    assert.throws(
        () => mod.assertSelectOnly('SELECT * FROM raw_match_data; DELETE FROM raw_match_data'),
        /NON_SELECT_SQL_BLOCKED/
    );
});

test('runCli returns JSON and status 0 with fake rows', async () => {
    let stdout = '';
    const status = await mod.runCli(
        validArgv(),
        {
            stdout: text => {
                stdout += text;
            },
        },
        { verificationRows: verificationRows() }
    );
    assert.equal(status, 0);
    const payload = JSON.parse(stdout);
    assert.equal(payload.verification_only, true);
    assert.equal(payload.target_verification.canonical_selected_version, 'fotmob_pageprops_v2');
});

test('runCli returns status 1 for invalid input', async () => {
    let stdout = '';
    const status = await mod.runCli(['--source=fotmob'], {
        stdout: text => {
            stdout += text;
        },
    });
    assert.equal(status, 1);
    const payload = JSON.parse(stdout);
    assert.equal(payload.ok, false);
    assert.match(payload.controlled_error, /INVALID_CANONICAL_READ_VERIFICATION_INPUT/);
});

test('module source does not import forbidden runtimes', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
    assert.doesNotMatch(source, /playwright|puppeteer|node:http|node:https|child_process/);
});
