'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_raw_completeness_audit.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const EXPECTED_TARGETS = mod.EXPECTED_TARGET_EXTERNAL_IDS.join(',');

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        targetExternalIds: EXPECTED_TARGETS,
        dataVersion: 'fotmob_pageprops_v2',
        allowDbWrite: false,
        allowNetwork: false,
        allowParserFeatures: false,
        allowTraining: false,
        allowPrediction: false,
        printFullRawData: false,
        saveFullRawData: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        printFullJson: false,
        saveFullJson: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        table: 'raw_match_data',
        'target-external-ids': EXPECTED_TARGETS,
        'data-version': 'fotmob_pageprops_v2',
        'allow-db-write': 'no',
        'allow-network': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        'print-full-raw-data': 'no',
        'save-full-raw-data': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function basePageProps(externalId) {
    return {
        content: {
            lineup: {
                homeTeam: { starters: [{ id: 1, name: `Home Starter ${externalId}` }] },
                awayTeam: { starters: [{ id: 2, name: `Away Starter ${externalId}` }] },
            },
            matchFacts: { events: [{ minute: 12, type: 'Goal' }] },
            playerStats: { players: [{ id: 1, stats: { shots: 2, xg: 0.4 } }] },
            shotmap: { shots: [{ x: 1, y: 2, expectedGoals: 0.1 }] },
            stats: { Periods: { All: { stats: [{ title: 'xG', stats: [1.1, 0.7] }] } } },
            h2h: { matches: [{ id: 101, result: '2-1' }] },
            table: { rows: [{ teamId: 1, position: 1 }] },
            momentum: { main: [{ minute: 1, value: 4 }] },
        },
        fallback: false,
        fetchingLeagueData: false,
        general: {
            matchId: externalId,
            leagueId: 53,
            leagueName: 'Ligue 1',
            matchName: `Home ${externalId} vs Away ${externalId}`,
            coverageLevel: 'full',
            homeTeam: { id: Number(externalId), name: `Home ${externalId}` },
            awayTeam: { id: Number(externalId) + 1000, name: `Away ${externalId}` },
        },
        hasPendingVAR: false,
        header: {
            teams: [{ name: `Home ${externalId}` }, { name: `Away ${externalId}` }],
            status: { finished: true },
            events: [{ id: 1 }],
        },
        nav: { tabs: ['summary', 'lineups', 'stats'] },
        ongoing: null,
        seo: {
            eventJSONLD: [{ '@type': 'SportsEvent', name: `Match ${externalId}` }],
            breadcrumbJSONLD: [{ '@type': 'BreadcrumbList', itemListElement: [] }],
        },
        ssr: true,
        translations: { summary: 'Summary', lineups: 'Lineups' },
    };
}

function baseRawData(externalId) {
    return {
        _meta: {
            source: 'fotmob',
            data_version: 'fotmob_pageprops_v2',
            hash_strategy: 'stable_pageprops_payload_v1',
            secret_marker: 'SECRET_RAW_DATA_SHOULD_NOT_PRINT',
        },
        matchId: externalId,
        pageProps: basePageProps(externalId),
    };
}

function targetRows(overridesByExternalId = {}) {
    return mod.SEEDED_TARGETS.map((target, index) => {
        const override = overridesByExternalId[target.externalId] || {};
        const rawData = override.raw_data || baseRawData(target.externalId);
        return {
            id: index + 1,
            match_id: target.matchId,
            external_id: target.externalId,
            data_version: override.data_version || 'fotmob_pageprops_v2',
            data_hash: override.data_hash || `pageprops-v2-hash-${target.externalId}`,
            collected_at: '2026-05-16T00:00:00.000Z',
            raw_data: rawData,
        };
    });
}

function rowCountRows(overrides = {}) {
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

function constraintRows(overrides = []) {
    return [
        {
            conname: 'raw_match_data_match_id_data_version_key',
            contype: 'u',
            definition: 'UNIQUE (match_id, data_version)',
        },
        ...overrides,
    ];
}

function distributionRows(overrides = []) {
    return [
        { data_version: 'PHASE4.23', rows: 1 },
        { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
        { data_version: 'fotmob_html_hyd_v1', rows: 8 },
        { data_version: 'fotmob_pageprops_v2', rows: 8 },
        ...overrides,
    ];
}

function excludedRows(overrides = []) {
    return [
        {
            external_id: 'legacy423',
            match_id: 'legacy_phase423_match',
            data_version: 'PHASE4.23',
            data_hash: 'legacy-phase423-hash',
        },
        {
            external_id: 'legacySynthetic',
            match_id: 'legacy_synthetic_match',
            data_version: 'PHASE4.43_SYNTHETIC',
            data_hash: 'legacy-phase443-hash',
        },
        {
            external_id: 'legacyUnknown',
            match_id: 'legacy_unknown_match',
            data_version: 'unknown_version',
            data_hash: 'legacy-unknown-hash',
        },
        ...overrides,
    ];
}

function auditRows(overrides = {}) {
    return {
        rowCountRows: overrides.rowCountRows || rowCountRows(),
        constraintRows: overrides.constraintRows || constraintRows(),
        targetRows: overrides.targetRows || targetRows(),
        distributionRows: overrides.distributionRows || distributionRows(),
        duplicateRows: overrides.duplicateRows || [],
        excludedRows: overrides.excludedRows || excludedRows(),
    };
}

function fakePool(rows = auditRows()) {
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
            if (text.includes("'matches' AS table_name")) return { rows: rows.rowCountRows };
            if (text.includes('FROM pg_constraint')) return { rows: rows.constraintRows };
            if (text.includes('WHERE external_id = ANY')) return { rows: rows.targetRows };
            if (text.includes('GROUP BY data_version')) return { rows: rows.distributionRows };
            if (text.includes('HAVING COUNT(*) > 1')) return { rows: rows.duplicateRows };
            if (text.includes('WHERE data_version <> ALL')) return { rows: rows.excludedRows };
            throw new Error(`unexpected query: ${text}`);
        },
    };
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validateAuditInput(validInput(overrides));
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
        throw new Error(`${name} should not be called by pageprops_v2_raw_completeness_audit`);
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

test('valid input succeeds', () => {
    assert.equal(mod.validateAuditInput(validInput()).ok, true);
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
    assertInvalid({ targetExternalIds: `${EXPECTED_TARGETS},9999999` }, /target-external-ids must be exactly/));
test('data-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid({ dataVersion: 'fotmob_html_hyd_v1' }, /data-version must be fotmob_pageprops_v2/));
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
test('print-full-raw-data=yes blocked', () =>
    assertInvalid({ printFullRawData: true }, /print-full-raw-data=yes is blocked/));
test('save-full-raw-data=yes blocked', () =>
    assertInvalid({ saveFullRawData: true }, /save-full-raw-data=yes is blocked/));
test('print-full-json=yes blocked', () => assertInvalid({ printFullJson: true }, /print-full-json=yes is blocked/));
test('save-full-json=yes blocked', () => assertInvalid({ saveFullJson: true }, /save-full-json=yes is blocked/));

test('fake 8 v2 rows inventory succeeds', () => {
    const result = mod.buildAuditSummary({
        ...auditRows(),
        input: validInput(),
    });
    assert.equal(result.ok, true);
    assert.equal(result.target_count, 8);
    assert.equal(result.all_target_rows_found, true);
    assert.equal(result.module_coverage.content, '8/8');
    assert.equal(result.coverage_tier, 'seeded_pageprops_v2_high_coverage');
});

test('missing v2 row fails', () => {
    const rows = targetRows().filter(row => row.external_id !== '4830754');
    const result = mod.buildAuditSummary({
        ...auditRows({ targetRows: rows }),
        input: validInput(),
    });
    assert.equal(result.ok, false);
    assert.ok(result.errors.some(error => error.includes('missing v2 row for external_id=4830754')));
});

test('raw_data missing pageProps fails', () => {
    const rows = targetRows({
        4830754: {
            raw_data: {
                _meta: { source: 'fotmob' },
                matchId: '4830754',
            },
        },
    });
    const result = mod.buildAuditSummary({
        ...auditRows({ targetRows: rows }),
        input: validInput(),
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /4830754 raw_data missing pageProps/);
});

test('pageProps missing content marks incomplete', () => {
    const rawData = baseRawData('4830753');
    delete rawData.pageProps.content;
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830753: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    const target = result.per_target.find(row => row.external_id === '4830753');
    assert.equal(target.coverage_tier, 'seeded_pageprops_v2_incomplete');
    assert.ok(result.suspicious.missing_core_modules.some(row => row.external_id === '4830753'));
});

test('module coverage counts 8/8', () => {
    const result = mod.buildAuditSummary({
        ...auditRows(),
        input: validInput(),
    });
    assert.equal(result.module_coverage['content.lineup'], '8/8');
    assert.equal(result.module_coverage['seo.eventJSONLD'], '8/8');
    assert.equal(result.module_coverage.translations, '8/8');
});

test('module coverage counts partial module correctly', () => {
    const rawData = baseRawData('4830748');
    delete rawData.pageProps.seo.breadcrumbJSONLD;
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830748: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    assert.equal(result.module_coverage['seo.breadcrumbJSONLD'], '7/8');
    assert.deepEqual(result.module_coverage_missing_external_ids['seo.breadcrumbJSONLD'], ['4830748']);
});

test('common paths counted correctly', () => {
    const result = mod.buildPathCoverage([
        { external_id: '4830746', match_id: 'm1', pageprops_paths: ['a', 'b', 'nested.c'] },
        { external_id: '4830747', match_id: 'm2', pageprops_paths: ['a', 'b', 'nested.d'] },
    ]);
    assert.equal(result.common_paths_count, 2);
    assert.equal(result.unique_paths_count, 4);
    assert.deepEqual(result.common_path_samples, ['a', 'b']);
});

test('partial paths counted correctly', () => {
    const result = mod.buildPathCoverage([
        { external_id: '4830746', match_id: 'm1', pageprops_paths: ['a', 'b'] },
        { external_id: '4830747', match_id: 'm2', pageprops_paths: ['a', 'c'] },
    ]);
    assert.equal(result.partial_paths_count, 2);
    assert.equal(result.partial_path_samples.length, 2);
    assert.deepEqual(
        result.partial_path_samples.map(sample => sample.path),
        ['b', 'c']
    );
});

test('missing_by_target samples capped', () => {
    const longPaths = Array.from({ length: 40 }, (_, index) => `path.${index}`);
    const result = mod.buildPathCoverage([
        { external_id: '4830746', match_id: 'm1', pageprops_paths: longPaths },
        { external_id: '4830747', match_id: 'm2', pageprops_paths: [] },
    ]);
    const target = result.missing_by_target_samples.find(sample => sample.external_id === '4830747');
    assert.equal(target.missing_path_count, 40);
    assert.equal(target.missing_paths_sample.length, 25);
});

test('suspicious small payload detected', () => {
    const rawData = baseRawData('4830747');
    rawData.pageProps = {
        content: {
            lineup: {},
            matchFacts: {},
            playerStats: {},
            shotmap: {},
            stats: {},
            h2h: {},
            table: {},
            momentum: {},
        },
        fallback: false,
        general: {
            matchId: '4830747',
            homeTeam: { name: 'Home 4830747' },
            awayTeam: { name: 'Away 4830747' },
        },
        header: {},
        nav: {},
        seo: {},
        translations: {},
    };
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830747: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    assert.ok(result.suspicious.small_payloads.some(row => row.external_id === '4830747'));
});

test('block/error markers detected', () => {
    const rawData = baseRawData('4830750');
    rawData.pageProps.seo.eventJSONLD = 'Access denied by Cloudflare captcha placeholder';
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830750: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    const target = result.suspicious.block_or_error_markers.find(row => row.external_id === '4830750');
    assert.ok(target);
    assert.ok(target.marker_names.includes('access_denied'));
    assert.ok(target.marker_names.includes('captcha'));
});

test('coverage tier high coverage when core modules 8/8', () => {
    const result = mod.buildAuditSummary({
        ...auditRows(),
        input: validInput(),
    });
    assert.equal(result.coverage_tier, 'seeded_pageprops_v2_high_coverage');
});

test('coverage tier partial when optional modules missing', () => {
    const rawData = baseRawData('4830751');
    delete rawData.pageProps.ongoing;
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830751: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    assert.equal(result.coverage_tier, 'seeded_pageprops_v2_partial_coverage');
});

test('coverage tier incomplete when core content missing', () => {
    const rawData = baseRawData('4830752');
    delete rawData.pageProps.content.matchFacts;
    const result = mod.buildAuditSummary({
        ...auditRows({
            targetRows: targetRows({
                4830752: { raw_data: rawData },
            }),
        }),
        input: validInput(),
    });
    assert.equal(result.coverage_tier, 'seeded_pageprops_v2_incomplete');
});

test('no full raw_data print', async () => {
    const rows = auditRows({
        targetRows: targetRows({
            4830746: {
                raw_data: (() => {
                    const rawData = baseRawData('4830746');
                    rawData.pageProps.general.secret = 'SECRET_PAGEPROPS_SHOULD_NOT_PRINT';
                    return rawData;
                })(),
            },
        }),
    });
    let rendered = '';
    const result = await mod.runCli(validArgv(), {
        rows,
        output: payload => {
            rendered += JSON.stringify(payload);
        },
    });
    assert.equal(result.status, 0);
    assert.equal(rendered.includes('SECRET_RAW_DATA_SHOULD_NOT_PRINT'), false);
    assert.equal(rendered.includes('SECRET_PAGEPROPS_SHOULD_NOT_PRINT'), false);
});

test('no DB write', async () => {
    const client = fakePool();
    const result = await mod.runCli(validArgv(), {
        client,
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(
        client.queries.every(query => /^SELECT\b/i.test(query.text.trim())),
        true
    );
});

test('no network', async t => {
    installExecutionGuards(t);
    const result = await mod.runCli(validArgv(), {
        rows: auditRows(),
        output: () => {},
    });
    assert.equal(result.status, 0);
});

test('no fs write / mkdir', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('no child_process spawn', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile|exec\(/);
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
