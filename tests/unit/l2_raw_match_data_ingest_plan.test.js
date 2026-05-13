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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_match_data_ingest_plan.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');
const PREVIEW_BODY_SHA256 = '8710a3524807d4682ab3c66386f9cd6b4d374fb6eee4f98a29d7f4a6683a162c';

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        homeTeam: 'Angers',
        awayTeam: 'Strasbourg',
        previewBodySha256: PREVIEW_BODY_SHA256,
        previewBodyByteLength: '1037598',
        hydrationParseOk: true,
        looksLikeValidMatchDetail: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowTraining: false,
        allowPrediction: false,
        commit: false,
        execute: false,
        networkAuthorization: false,
        ...overrides,
    };
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    return [
        `--source=${args.source}`,
        `--route=${args.route}`,
        `--match-id=${args.matchId}`,
        `--external-id=${args.externalId}`,
        `--home-team=${args.homeTeam}`,
        `--away-team=${args.awayTeam}`,
        `--preview-body-sha256=${args.previewBodySha256}`,
        `--preview-body-byte-length=${args.previewBodyByteLength}`,
        `--hydration-parse-ok=${args.hydrationParseOk ? 'yes' : 'no'}`,
        `--looks-like-valid-match-detail=${args.looksLikeValidMatchDetail ? 'yes' : 'no'}`,
        `--allow-db-write=${args.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${args.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-matches-write=${args.allowMatchesWrite ? 'yes' : 'no'}`,
        `--allow-training=${args.allowTraining ? 'yes' : 'no'}`,
        `--allow-prediction=${args.allowPrediction ? 'yes' : 'no'}`,
        `--commit=${args.commit ? 'yes' : 'no'}`,
        `--execute=${args.execute ? 'yes' : 'no'}`,
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
    ];
}

async function runCli(gate, argv) {
    let stdout = '';
    const status = await gate.runCli(argv, {
        stdout: text => {
            stdout += text;
        },
    });
    return {
        status,
        stdout,
        payload: stdout.trim().startsWith('{') ? JSON.parse(stdout) : null,
    };
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
        throw new Error(`${name} should not be called by l2_raw_match_data_ingest_plan`);
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
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
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

function assertInvalid(overrides, expectedPattern) {
    const gate = loadModuleFresh();
    const plan = gate.buildRawMatchDataIngestPlan(validArgs(overrides));
    assert.equal(plan.ok, false);
    assert.match(plan.controlled_error, expectedPattern);
    assert.equal(plan.would_write_raw_match_data, false);
    assert.equal(plan.would_write_db, false);
}

test('valid planning input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePlanningInput(validArgs());
    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /unsupported source/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route/));
test('route non-html_hydration fails for this phase', () =>
    assertInvalid({ route: 'api_match_details' }, /unsupported route/));
test('match-id missing fails', () => assertInvalid({ matchId: '' }, /missing match-id/));
test('match-id not 53_20252026_4830746 fails', () => assertInvalid({ matchId: 'x' }, /match-id must be/));
test('external-id missing fails', () => assertInvalid({ externalId: '' }, /missing external-id/));
test('external-id not 4830746 fails', () => assertInvalid({ externalId: '1' }, /external-id must be/));
test('home-team missing Angers fails', () => assertInvalid({ homeTeam: 'Paris' }, /home-team must contain Angers/));
test('away-team missing Strasbourg fails', () =>
    assertInvalid({ awayTeam: 'Lens' }, /away-team must contain Strasbourg/));
test('preview-body-sha256 missing fails', () =>
    assertInvalid({ previewBodySha256: '' }, /missing preview-body-sha256/));
test('preview-body-byte-length <= 0 fails', () =>
    assertInvalid({ previewBodyByteLength: '0' }, /byte-length must be > 0/));
test('hydration-parse-ok=no fails', () =>
    assertInvalid({ hydrationParseOk: false }, /hydration-parse-ok=yes is required/));
test('looks-like-valid-match-detail=no fails', () =>
    assertInvalid({ looksLikeValidMatchDetail: false }, /looks-like-valid-match-detail=yes is required/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('network-authorization=yes blocked', () =>
    assertInvalid({ networkAuthorization: true }, /network-authorization=yes is blocked/));

test('output planning_only=true and target_table=raw_match_data', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRawMatchDataIngestPlan(validArgs());
    assert.equal(plan.ok, true);
    assert.equal(plan.planning_only, true);
    assert.equal(plan.target_table, 'raw_match_data');
});

test('output would_write_raw_match_data=false', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildRawMatchDataIngestPlan(validArgs());
    assert.equal(plan.raw_match_data_write_allowed_this_phase, false);
    assert.equal(plan.db_write_allowed_this_phase, false);
    assert.equal(plan.would_write_raw_match_data, false);
    assert.equal(plan.would_write_db, false);
});

test('raw_data_policy forbids full HTML body', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildRawDataPolicy(validArgs());
    assert.equal(policy.exclude_full_html_body, true);
    assert.equal(policy.raw_data_must_not_be_page_html, true);
});

test('raw_data_policy includes transformed_api_format', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildRawDataPolicy(validArgs());
    assert.match(policy.recommended_source, /transformed_api_format/);
    assert.ok(policy.required_top_level_keys.includes('content'));
    assert.ok(policy.preserve_paths.includes('content.matchFacts'));
});

test('hash_policy uses SHA-256 canonical JSON', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildHashPolicy();
    assert.equal(policy.data_hash_algorithm, 'sha256');
    assert.equal(policy.data_hash_input, 'canonical_json(raw_data)');
    assert.equal(policy.canonical_json_requires_stable_key_ordering, true);
});

test('hash_policy separates body_sha256 from data_hash', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildHashPolicy();
    assert.equal(policy.html_body_hash_is_data_hash, false);
    assert.equal(policy.body_sha256_metadata_field, 'raw_data._meta.fetch_body_sha256');
});

test('data_version_policy contains fotmob_html_hydration_v1', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildDataVersionPolicy();
    assert.equal(policy.semantic_label, 'fotmob_html_hydration_v1');
    assert.equal(policy.data_version, 'fotmob_html_hyd_v1');
});

test('collected_at_policy uses write-time UTC', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildCollectedAtPolicy();
    assert.equal(policy.collected_at_source, 'write_phase_utc_timestamp');
    assert.equal(policy.timezone, 'UTC');
});

test('upsert_policy uses match_id unique', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildUpsertPolicy();
    assert.equal(policy.conflict_key, 'match_id');
    assert.equal(policy.unique_constraint, 'raw_match_data_match_id_key');
});

test('upsert_policy requires transaction', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildUpsertPolicy();
    assert.equal(policy.transaction_required, true);
    assert.equal(policy.first_write_max_rows, 1);
});

test('protected_tables_policy protects matches/features/predictions', () => {
    const gate = loadModuleFresh();
    const policy = gate.buildProtectedTablesPolicy();
    assert.equal(policy.future_write_allowed_table, 'raw_match_data');
    assert.equal(policy.protected_tables.matches, 'read_only');
    assert.equal(policy.protected_tables.l3_features, 'unchanged');
    assert.equal(policy.protected_tables.predictions, 'unchanged');
});

test('Makefile plan target is present and maps to planning script', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l2-raw-match-data-ingest-plan:/m);
    assert.match(makefile, /scripts\/ops\/l2_raw_match_data_ingest_plan\.js/);
});

test('runCli succeeds with valid input and does not access network or DB', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs());
    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.external_network_used, false);
    assert.equal(result.payload.would_write_db, false);
});

test('runCli returns non-zero for blocked DB write', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ allowDbWrite: true }));
    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.match(result.payload.controlled_error, /allow-db-write=yes is blocked/);
});

test('source audit: no network clients', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]node:http['"]\)|require\(['"]http['"]\)/);
    assert.doesNotMatch(source, /require\(['"]node:https['"]\)|require\(['"]https['"]\)/);
    assert.doesNotMatch(source, /\bfetch\s*\(/);
});

test('source audit: no DB write or pg client', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /require\(['"]pg['"]\)/);
    assert.doesNotMatch(source, /\.query\s*\(/);
    assert.doesNotMatch(source, /\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b/i);
    assert.doesNotMatch(source, /\b(TRUNCATE|ALTER\s+TABLE|DROP\s+TABLE|MERGE\s+INTO)\b/i);
});

test('source audit: no fs write / mkdir', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('source audit: no child_process spawn', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile/);
});

test('source audit: no ProductionHarvester / raw ingest commit', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});
