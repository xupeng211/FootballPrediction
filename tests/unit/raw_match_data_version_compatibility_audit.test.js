'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/raw_match_data_version_compatibility_audit.js');

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        preferredVersion: 'fotmob_pageprops_v2',
        fallbackVersion: 'fotmob_html_hyd_v1',
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowParserFeatures: false,
        allowTraining: false,
        allowPrediction: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowMigration: false,
        allowAlterTable: false,
        ...overrides,
    };
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    return [
        `--source=${args.source}`,
        `--table=${args.table}`,
        `--preferred-version=${args.preferredVersion}`,
        `--fallback-version=${args.fallbackVersion}`,
        `--allow-db-write=${args.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${args.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-parser-features=${args.allowParserFeatures ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--touch-fotmob=${args.touchFotmob ? 'yes' : 'no'}`,
        `--live-request=${args.liveRequest ? 'yes' : 'no'}`,
        `--allow-migration=${args.allowMigration ? 'yes' : 'no'}`,
        `--allow-alter-table=${args.allowAlterTable ? 'yes' : 'no'}`,
    ];
}

function fakeAuditRows(overrides = {}) {
    return {
        constraints: [
            {
                conname: 'raw_match_data_match_id_data_version_key',
                contype: 'u',
                definition: 'UNIQUE (match_id, data_version)',
            },
        ],
        distribution: [
            { data_version: 'PHASE4.23', rows: 1 },
            { data_version: 'PHASE4.43_SYNTHETIC', rows: 1 },
            { data_version: 'fotmob_html_hyd_v1', rows: 8 },
        ],
        duplicates: [],
        rawRows: [
            {
                id: 1,
                match_id: '53_20252026_4830747',
                external_id: '4830747',
                data_version: 'fotmob_html_hyd_v1',
                data_hash: 'v1',
                collected_at: '2026-05-15T00:00:00.000Z',
            },
            {
                id: 2,
                match_id: '53_20252026_4830747',
                external_id: '4830747',
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'v2',
                collected_at: '2026-05-15T00:01:00.000Z',
            },
            {
                id: 3,
                match_id: '53_20252026_SYNTHETIC',
                external_id: 'synthetic',
                data_version: 'PHASE4.43_SYNTHETIC',
                data_hash: 'synthetic',
                collected_at: '2026-05-15T00:02:00.000Z',
            },
        ],
        ...overrides,
    };
}

function assertInvalid(overrides, pattern) {
    const gate = loadModuleFresh();
    const validation = gate.validateAuditInput(validArgs(overrides));
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
        throw new Error(`${name} should not be called by raw_match_data_version_compatibility_audit`);
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
        if (/ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i.test(request)) {
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

function fakePool() {
    const queries = [];
    return {
        queries,
        async query(sql, values = []) {
            const text = String(sql || '').trim();
            queries.push({ text, values });
            assert.match(text, /^SELECT\b/i);
            assert.doesNotMatch(text, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE INDEX|DROP INDEX)\b/i);
            if (text.includes('FROM pg_constraint')) return { rows: fakeAuditRows().constraints };
            if (text.includes('GROUP BY data_version')) return { rows: fakeAuditRows().distribution };
            if (text.includes('HAVING COUNT(*) > 1')) return { rows: [] };
            if (text.includes('FROM raw_match_data')) return { rows: fakeAuditRows().rawRows };
            throw new Error(`unexpected query: ${text}`);
        },
    };
}

test('valid input succeeds', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.validateAuditInput(validArgs()).ok, true);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source=fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('table not raw_match_data fails', () => assertInvalid({ table: 'matches' }, /table must be raw_match_data/));
test('preferred-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid({ preferredVersion: 'fotmob_html_hyd_v1' }, /preferred-version must be fotmob_pageprops_v2/));
test('fallback-version not fotmob_html_hyd_v1 fails', () =>
    assertInvalid({ fallbackVersion: 'PHASE4.23' }, /fallback-version must be fotmob_html_hyd_v1/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-parser-features=yes blocked', () =>
    assertInvalid({ allowParserFeatures: true }, /allow-parser-features=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('touch-fotmob=yes blocked', () => assertInvalid({ touchFotmob: true }, /touch-fotmob=yes is blocked/));
test('live-request=yes blocked', () => assertInvalid({ liveRequest: true }, /live-request=yes is blocked/));
test('allow-migration=yes blocked', () => assertInvalid({ allowMigration: true }, /allow-migration=yes is blocked/));
test('allow-alter-table=yes blocked', () =>
    assertInvalid({ allowAlterTable: true }, /allow-alter-table=yes is blocked/));

test('fake audit confirms unique(match_id,data_version)', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), {
        auditRows: fakeAuditRows(),
    });
    assert.equal(result.ok, true);
    assert.equal(result.schema_constraint_check.unique_match_id_data_version_exists, true);
    assert.equal(result.schema_constraint_check.unique_match_id_absent, true);
});

test('fake audit flags unique(match_id) if still present', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), {
        auditRows: fakeAuditRows({
            constraints: [
                { conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' },
                {
                    conname: 'raw_match_data_match_id_data_version_key',
                    contype: 'u',
                    definition: 'UNIQUE (match_id, data_version)',
                },
            ],
        }),
    });
    assert.equal(result.schema_constraint_check.unique_match_id_exists, true);
    assert.equal(result.schema_constraint_check.unique_match_id_absent, false);
});

test('fake audit canonical selects v2', async () => {
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), {
        auditRows: fakeAuditRows(),
    });
    const entry = result.canonical_selector_dry_run.find(item => item.match_id === '53_20252026_4830747');
    assert.equal(entry.selected_canonical_version, 'fotmob_pageprops_v2');
    assert.equal(entry.selected_row_id, 2);
});

test('fake audit canonical fallback to v1', async () => {
    const gate = loadModuleFresh();
    const rows = fakeAuditRows({
        rawRows: [
            {
                id: 11,
                match_id: '53_20252026_4830748',
                external_id: '4830748',
                data_version: 'fotmob_html_hyd_v1',
            },
        ],
    });
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), { auditRows: rows });
    assert.equal(result.canonical_selector_dry_run[0].selected_canonical_version, 'fotmob_html_hyd_v1');
    assert.equal(result.canonical_selector_dry_run[0].selected_row_id, 11);
});

test('fake audit excludes synthetic/unknown', async () => {
    const gate = loadModuleFresh();
    const rows = fakeAuditRows({
        rawRows: [
            {
                id: 21,
                match_id: '53_20252026_SYNTHETIC',
                external_id: 'synthetic',
                data_version: 'PHASE4.43_SYNTHETIC',
            },
            {
                id: 22,
                match_id: '53_20252026_UNKNOWN',
                external_id: 'unknown',
                data_version: 'mystery',
            },
        ],
    });
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), { auditRows: rows });
    assert.equal(result.canonical_selector_dry_run[0].selected_canonical_version, null);
    assert.equal(result.canonical_selector_dry_run[0].synthetic_unknown_excluded, true);
    assert.equal(result.canonical_selector_dry_run[1].selected_canonical_version, null);
});

test('no DB write', async () => {
    const gate = loadModuleFresh();
    const pool = fakePool();
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), { pool });
    assert.equal(result.ok, true);
    assert.equal(result.execution_flags.db_write_executed, false);
    assert.equal(result.execution_flags.raw_match_data_write_executed, false);
    assert.equal(pool.queries.length, 4);
});

test('no network/fs write/child_process when guarded', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await gate.buildRawMatchDataVersionCompatibilityAudit(validArgs(), {
        auditRows: fakeAuditRows(),
    });
    assert.equal(result.ok, true);
    assert.equal(result.execution_flags.fotmob_access_executed, false);
});

test('runCli returns audit JSON with fake rows', async () => {
    const gate = loadModuleFresh();
    let stdout = '';
    const status = await gate.runCli(
        cliArgs(),
        {
            stdout: text => {
                stdout += text;
            },
        },
        { auditRows: fakeAuditRows() }
    );
    assert.equal(status, 0);
    const payload = JSON.parse(stdout);
    assert.equal(payload.audit_only, true);
    assert.equal(payload.risk_inventory.controlled_paths_updated.length, 4);
});
