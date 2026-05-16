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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js');
const EXPECTED_HASHES_JSON =
    '{"4830746":"7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440","4830747":"f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc","4830748":"fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04","4830750":"e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762","4830751":"de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5","4830752":"65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32","4830753":"4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413","4830754":"29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6"}';

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        targetExternalIds: '4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754',
        expectedTargetVersion: 'fotmob_pageprops_v2',
        fallbackVersion: 'fotmob_html_hyd_v1',
        expectedHashes: EXPECTED_HASHES_JSON,
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
        'target-external-ids': '4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754',
        'expected-target-version': 'fotmob_pageprops_v2',
        'fallback-version': 'fotmob_html_hyd_v1',
        'expected-hashes': EXPECTED_HASHES_JSON,
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
        raw_match_data: 18,
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
        { data_version: 'fotmob_pageprops_v2', rows: 8 },
        ...overrides,
    ];
}

function seededRows(overrides = []) {
    return mod.SEEDED_TARGETS.flatMap((target, index) => [
        {
            id: index + 1,
            match_id: target.matchId,
            external_id: target.externalId,
            data_version: 'fotmob_html_hyd_v1',
            data_hash: `v1-hash-${target.externalId}`,
            collected_at: '2026-05-16T13:37:39.108Z',
            has_meta: true,
            has_match_id: true,
            has_pageprops: false,
        },
        {
            id: index + 101,
            match_id: target.matchId,
            external_id: target.externalId,
            data_version: 'fotmob_pageprops_v2',
            data_hash: target.expectedHash,
            collected_at: '2026-05-16T13:37:39.108Z',
            has_meta: true,
            has_match_id: true,
            has_pageprops: true,
        },
    ]).concat(overrides);
}

function legacyRows(overrides = []) {
    return [
        {
            id: 1001,
            match_id: 'legacy_phase423_match',
            external_id: 'legacy423',
            data_version: 'PHASE4.23',
            data_hash: 'legacy-phase423-hash',
            collected_at: '2026-05-16T00:00:00.000Z',
            raw_data: { secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT' },
        },
        {
            id: 1002,
            match_id: 'legacy_synthetic_match',
            external_id: 'legacySynthetic',
            data_version: 'PHASE4.43_SYNTHETIC',
            data_hash: 'legacy-phase443-hash',
            collected_at: '2026-05-16T00:00:00.000Z',
            raw_data: { secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT' },
        },
        {
            id: 1003,
            match_id: 'legacy_unknown_match',
            external_id: 'legacyUnknown',
            data_version: 'untracked_version',
            data_hash: 'legacy-unknown-hash',
            collected_at: '2026-05-16T00:00:00.000Z',
            raw_data: { secret: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT' },
        },
        ...overrides,
    ];
}

function verificationRows(overrides = {}) {
    return {
        rowCounts: rowCounts(overrides.rowCounts),
        constraints: overrides.constraints || constraints(),
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
        throw new Error(`${name} should not be called by all_seeded_pageprops_v2_canonical_read_verification`);
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
            if (text.includes('WHERE match_id = ANY')) return { rows: rows.seededRows };
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

test('parseArgs supports equals syntax and unknown positional args', () => {
    const parsed = mod.parseArgs(['--source=fotmob', 'positional', '--allow-db-write=no', '--bad-flag=yes']);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.allowDbWrite, false);
    assert.deepEqual(parsed.unknown, ['positional', 'bad-flag']);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source=fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('table missing fails', () => assertInvalid({ table: '' }, /missing table=raw_match_data/));
test('table not raw_match_data fails', () => assertInvalid({ table: 'matches' }, /table must be raw_match_data/));
test('target-external-ids missing fails', () =>
    assertInvalid({ targetExternalIds: '' }, /missing target-external-ids/));
test('target-external-ids wrong list fails', () =>
    assertInvalid({ targetExternalIds: '4830747,4830746' }, /target-external-ids must be exactly/));
test('target-external-ids missing one seeded target fails', () =>
    assertInvalid(
        { targetExternalIds: '4830746,4830747,4830748,4830750,4830751,4830752,4830753' },
        /target-external-ids must be exactly/
    ));
test('target-external-ids extra target fails', () =>
    assertInvalid(
        { targetExternalIds: '4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754,9999999' },
        /target-external-ids must be exactly/
    ));
test('expected-target-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid(
        { expectedTargetVersion: 'fotmob_html_hyd_v1' },
        /expected-target-version must be fotmob_pageprops_v2/
    ));
test('fallback-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ fallbackVersion: 'PHASE4.23' }, /fallback-version must be fotmob_html_hyd_v1/));
test('expected-hashes missing fails', () => assertInvalid({ expectedHashes: '' }, /missing expected-hashes/));
test('expected-hashes invalid JSON fails', () =>
    assertInvalid({ expectedHashes: '{bad' }, /expected-hashes must be valid JSON/));
test('expected-hashes non-object JSON fails', () =>
    assertInvalid({ expectedHashes: '[]' }, /expected-hashes must be a JSON object/));
test('expected-hashes missing one target fails', () => {
    const hashes = JSON.parse(EXPECTED_HASHES_JSON);
    delete hashes['4830754'];
    assertInvalid({ expectedHashes: JSON.stringify(hashes) }, /expected-hashes missing 4830754/);
});
test('expected-hashes extra target fails', () =>
    assertInvalid(
        { expectedHashes: JSON.stringify({ ...mod.EXPECTED_HASHES, 9999999: '0'.repeat(64) }) },
        /unexpected target 9999999/
    ));
test('expected-hashes invalid hash fails', () =>
    assertInvalid(
        {
            expectedHashes: JSON.stringify({
                ...mod.EXPECTED_HASHES,
                4830746: 'NOT_HEX',
            }),
        },
        /4830746 must be a 64-char lowercase hex string/
    ));
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

test('fake dataset all 8 select v2', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.ok, true);
    assert.equal(result.seeded_verification.seeded_matches_checked, 8);
    assert.equal(result.seeded_verification.canonical_v2_count, 8);
    assert.equal(result.seeded_verification.hash_match_count, 8);
    assert.equal(result.seeded_verification.fallback_to_v1_count, 0);
});

test('fake dataset hash mismatch reports controlled failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows().map(row =>
            row.external_id === '4830750' && row.data_version === 'fotmob_pageprops_v2'
                ? { ...row, data_hash: '0'.repeat(64) }
                : row
        ),
    });
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830750 selected hash mismatch/);
});

test('fake dataset missing v2 reports failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(
            row => !(row.external_id === '4830751' && row.data_version === 'fotmob_pageprops_v2')
        ),
    });
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830751 missing fotmob_pageprops_v2/);
});

test('fake dataset missing v1 but has v2 reports controlled failure', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(
            row => !(row.external_id === '4830752' && row.data_version === 'fotmob_html_hyd_v1')
        ),
    });
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830752 missing fotmob_html_hyd_v1/);
});

test('fake dataset fallback to v1 should not happen for all-seeded post-write state', async () => {
    const rows = verificationRows({
        seededRows: seededRows().filter(
            row => !(row.external_id === '4830753' && row.data_version === 'fotmob_pageprops_v2')
        ),
    });
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), { verificationRows: rows });
    assert.equal(result.ok, false);
    assert.equal(result.seeded_verification.fallback_to_v1_count, 1);
    assert.match(result.controlled_error, /4830753 unexpectedly fell back to fotmob_html_hyd_v1/);
});

test('synthetic excluded by default', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.excluded_versions_verification.synthetic_excluded, true);
});

test('unknown excluded by default', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.excluded_versions_verification.unknown_excluded, true);
});

test('duplicate match_id,data_version controlled error', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            duplicates: [{ match_id: '53_20252026_4830746', data_version: 'fotmob_pageprops_v2', rows: 2 }],
        }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /duplicate match_id,data_version rows found: 1/);
});

test('schema unique(match_id,data_version) required', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            constraints: [{ conname: 'other_constraint', contype: 'u', definition: 'UNIQUE (id)' }],
        }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /UNIQUE\(match_id,data_version\) is missing/);
});

test('schema unique(match_id only) absent required', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            constraints: constraints([
                { conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' },
            ]),
        }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /legacy UNIQUE\(match_id\) is still present/);
});

test('row count expectation raw_match_data=18', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({ rowCounts: { raw_match_data: 17 } }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /row count raw_match_data expected 18, got 17/);
});

test('data_version distribution expectation v1=8/v2=8', async () => {
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows({
            distribution: [
                { data_version: 'PHASE4.23', rows: 1 },
                { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
                { data_version: 'fotmob_html_hyd_v1', rows: 8 },
                { data_version: 'fotmob_pageprops_v2', rows: 7 },
            ],
        }),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /data_version distribution fotmob_pageprops_v2 expected 8, got 7/);
});

test('no raw_data full print', async () => {
    let rendered = '';
    const result = await mod.runCli(
        validArgv(),
        {
            stdout: payload => {
                rendered += payload;
            },
        },
        {
            verificationRows: verificationRows(),
        }
    );
    assert.equal(result, 0);
    assert.equal(rendered.includes('SECRET_RAW_DATA_SHOULD_NOT_PRINT'), false);
});

test('no DB write', async () => {
    const client = fakePool();
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), { pool: client });
    assert.equal(result.ok, true);
    assert.equal(
        client.queries.every(query => /^SELECT\b/i.test(query.text.trim())),
        true
    );
});

test('no network', async t => {
    installExecutionGuards(t);
    const result = await mod.buildAllSeededCanonicalReadVerification(validInput(), {
        verificationRows: verificationRows(),
    });
    assert.equal(result.ok, true);
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

test('no parser/features/training import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/parser|feature_engine|training|predict_pipeline/i.test(request)) {
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

test('no ProductionHarvester/raw ingest import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i.test(request)) {
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
