'use strict';
/* eslint-disable max-lines -- This file intentionally keeps the preview gate contract matrix in one place. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const { spawnSync } = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_auth_preview.js');
const DRY_RUN_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
const PREFLIGHT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_db_write_preflight.js');
const DUPLICATE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_duplicate_precheck.js');
const INSERT_POLICY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_insert_policy_precheck.js');
const LEGACY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fetch_and_adapt_euro_leagues.js');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
);
const CSV_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');

function installExecutionGuards(t, options = {}) {
    const moduleOverrides = options.moduleOverrides || {};
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalLoad = Module._load;
    const originalWriteFileSync = fs.writeFileSync;
    const originalWriteFile = fs.writeFile;
    const originalAppendFileSync = fs.appendFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_small_write_auth_preview`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.writeFile = fail('fs.writeFile');
    fs.appendFileSync = fail('fs.appendFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
        ]);
        if (Object.prototype.hasOwnProperty.call(moduleOverrides, request)) {
            return moduleOverrides[request];
        }
        if (blockedImports.has(request) || String(request || '').includes('fetch_and_adapt_euro_leagues')) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        global.fetch = originalFetch;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.writeFile = originalWriteFile;
        fs.appendFileSync = originalAppendFileSync;
        fs.createWriteStream = originalCreateWriteStream;
        Module._load = originalLoad;
    });
}

function loadPreviewFresh() {
    delete require.cache[SCRIPT_PATH];
    delete require.cache[DRY_RUN_PATH];
    delete require.cache[PREFLIGHT_PATH];
    delete require.cache[DUPLICATE_PATH];
    delete require.cache[INSERT_POLICY_PATH];
    return require(SCRIPT_PATH);
}

function loadManifest() {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function createMockClient(queryHandler = () => ({ rows: [] })) {
    const calls = [];
    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });
            return queryHandler(String(sql), params);
        },
    };
}

function buildDryRunPayload(overrides = {}) {
    return {
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_status: 'dry_run_only',
        source_name: 'unit_fixture',
        parser_version: 'unit_parser',
        dry_run_version: 'unit_dry_run',
        sha256_match: true,
        row_count_match: true,
        candidate_rows: [
            {
                row_number: 1,
                home_team: 'Synthetic Home Winners',
                away_team: 'Synthetic Away Losers',
                match_date: '2024-08-17T17:30:00.000Z',
                actual_result: 'home_win',
            },
            {
                row_number: 2,
                home_team: 'Draw Home',
                away_team: 'Draw Away',
                match_date: '2024-08-18T17:30:00.000Z',
                actual_result: 'draw',
            },
            {
                row_number: 3,
                home_team: 'Away Winners',
                away_team: 'Home Losers',
                match_date: '2024-08-19T17:30:00.000Z',
                actual_result: 'away_win',
            },
        ],
        row_classification: {
            trainable_label_rows: 3,
        },
        non_execution_confirmations: ['no_external_network', 'no_db_writes'],
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildPreflightPayload(overrides = {}) {
    return {
        phase: 'PHASE4.64C_FOOTBALL_DATA_DB_WRITE_PREFLIGHT',
        ok: true,
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildDuplicatePayload(overrides = {}) {
    return {
        phase: 'PHASE4.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK',
        ok: true,
        exact_existing_matches: 0,
        reversed_team_matches: 0,
        nearby_date_matches: 0,
        non_execution_confirmations: ['select_only_db_reads', 'no_db_writes'],
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildInsertPolicyPayload(overrides = {}) {
    return {
        phase: 'PHASE4.66C_FOOTBALL_DATA_INSERT_POLICY',
        ok: true,
        manifest_approval_status: 'dry_run_only',
        invalid_candidates: 0,
        future_insert_candidates: 0,
        blocked_by_manifest_policy: 3,
        skip_existing_matches: 0,
        manual_review_required: 0,
        non_execution_confirmations: ['select_only_db_reads', 'no_db_writes'],
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildDbState() {
    return {
        current_db_counts: {
            matches: 2,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        current_db_schema_preview: {
            required_tables_found: [
                'bookmaker_odds_history',
                'l3_features',
                'match_features_training',
                'matches',
                'predictions',
                'raw_match_data',
            ],
            required_tables_expected: [
                'matches',
                'bookmaker_odds_history',
                'raw_match_data',
                'l3_features',
                'match_features_training',
                'predictions',
            ],
            matches_match_id: {
                column_name: 'match_id',
                data_type: 'character varying',
                character_maximum_length: 50,
                is_nullable: 'NO',
            },
        },
    };
}

async function runMain(gate, argv, dependencies = {}) {
    let stdout = '';
    let stderr = '';
    const status = await gate.main(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
            stderr: text => {
                stderr += text;
            },
        },
        dependencies
    );

    return {
        status,
        stdout,
        stderr,
        payload: JSON.parse(stdout),
    };
}

async function runTextMain(gate, argv, dependencies = {}) {
    let stdout = '';
    let stderr = '';
    const status = await gate.main(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
            stderr: text => {
                stderr += text;
            },
        },
        dependencies
    );

    return {
        status,
        stdout,
        stderr,
    };
}

function assertSafetyPayload(payload) {
    assert.equal(payload.select_only_db_reads, true);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.small_write_authorized, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.equal(payload.would_insert_matches, false);
    assert.equal(payload.would_insert_odds, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.commit_gate, 'blocked');
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
    assert.ok(payload.non_execution_confirmations.includes('select_only_db_reads'));
    assert.ok(payload.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_legacy_runtime'));
    assert.ok(payload.non_execution_confirmations.includes('no_pg_dump_execution'));
    assert.ok(payload.non_execution_confirmations.includes('no_pg_restore_execution'));
    assert.ok(payload.non_execution_confirmations.includes('no_training'));
    assert.ok(payload.non_execution_confirmations.includes('no_prediction_execution'));
}

function assertSqlCallsAreReadOnly(gate, calls) {
    assert.ok(calls.some(call => call.sql === gate.READ_ONLY_BEGIN_SQL));
    assert.ok(calls.some(call => call.sql === gate.READ_ONLY_ROLLBACK_SQL));
    for (const call of calls) {
        gate.assertSelectOnlySql(call.sql);
        const normalized = call.sql.replace(/\s+/g, ' ').trim().toUpperCase();
        assert.ok(
            normalized === 'BEGIN READ ONLY' || normalized === 'ROLLBACK' || normalized.startsWith('SELECT '),
            `unexpected SQL: ${normalized}`
        );
        assert.doesNotMatch(
            normalized,
            /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|MERGE|GRANT|REVOKE|COMMIT)\b|\\COPY/
        );
    }
}

test('small write auth preview module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();

    assert.equal(typeof gate.main, 'function');
    assert.equal(typeof gate.runSmallWriteAuthPreview, 'function');
    assert.equal(typeof gate.inspectCurrentDbState, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 参数必须失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runSmallWriteAuthPreview(
        {
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
    assert.match(payload.errors[0], /provide --source-manifest/);
});

test('缺 local CSV 参数必须失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
        },
        { dbClient: client }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
    assert.match(payload.errors[0], /provide --source-manifest/);
});

test('正确 manifest + CSV + mock DB client auth preview 成功', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(sql => {
        if (sql === gate.CURRENT_DB_COUNTS_SQL) {
            return {
                rows: [
                    { table_name: 'matches', rows: '2' },
                    { table_name: 'bookmaker_odds_history', rows: '2' },
                    { table_name: 'raw_match_data', rows: '2' },
                    { table_name: 'l3_features', rows: '2' },
                    { table_name: 'match_features_training', rows: '2' },
                    { table_name: 'predictions', rows: '2' },
                ],
            };
        }
        if (sql === gate.REQUIRED_TABLES_SQL) {
            return {
                rows: buildDbState().current_db_schema_preview.required_tables_found.map(table_name => ({
                    table_name,
                })),
            };
        }
        if (sql === gate.MATCH_ID_SCHEMA_SQL) {
            return {
                rows: [buildDbState().current_db_schema_preview.matches_match_id],
            };
        }
        return { rows: [] };
    });
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload(),
            runInsertPolicyPrecheck: async () => buildInsertPolicyPayload(),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.67C_FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW');
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.csv_dry_run_passed, true);
    assert.equal(payload.db_write_preflight_passed, true);
    assert.equal(payload.duplicate_precheck_passed, true);
    assert.equal(payload.insert_policy_precheck_passed, true);
    assert.equal(payload.select_only_db_reads, true);
    assert.equal(payload.manifest_approval_status, 'dry_run_only');
    assert.equal(payload.current_db_counts.matches, 2);
    assert.equal(payload.current_db_counts.bookmaker_odds_history, 2);
    assert.equal(payload.current_db_counts.raw_match_data, 2);
    assert.equal(payload.current_db_counts.l3_features, 2);
    assert.equal(payload.current_db_counts.match_features_training, 2);
    assert.equal(payload.current_db_counts.predictions, 2);
    assert.equal(payload.max_rows_preview, 3);
    assert.deepEqual(payload.target_tables_preview, ['matches', 'bookmaker_odds_history']);
    assertSafetyPayload(payload);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('pg_dump command preview、checklists 和 rollback preview 必须存在，但不执行', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            inspectCurrentDbState: async () => buildDbState(),
            runDryRun: () => buildDryRunPayload(),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload(),
            runInsertPolicyPrecheck: async () => buildInsertPolicyPayload(),
        }
    );

    assert.equal(payload.ok, true);
    assert.match(payload.pg_dump_command_preview, /pg_dump/);
    assert.match(payload.pg_restore_command_preview, /pg_restore/);
    assert.ok(payload.required_before_small_db_write.includes('pg_dump backup must run immediately before write'));
    assert.ok(payload.required_before_small_db_write.includes('backup file must be non-empty'));
    assert.ok(payload.post_write_validation.includes('compare before/after row counts'));
    assert.ok(payload.post_write_validation.includes('record backup path'));
    assert.ok(payload.rollback_restore_preview.includes('restore is not executed automatically'));
    assert.ok(payload.rollback_restore_preview.includes('restore command must be documented but not executed'));
    assert.ok(payload.approval_requirements.includes('future CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1 authorization'));
    assertSafetyPayload(payload);
});

test('dry_run_only manifest 下 small_write_authorized=false', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            inspectCurrentDbState: async () => buildDbState(),
            runDryRun: () => buildDryRunPayload({ approval_status: 'dry_run_only' }),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload(),
            runInsertPolicyPrecheck: async () => buildInsertPolicyPayload({ manifest_approval_status: 'dry_run_only' }),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.manifest_approval_status, 'dry_run_only');
    assert.equal(payload.small_write_authorized, false);
    assert.equal(payload.db_write_allowed, false);
});

test('approved_for_db_write manifest 也仍然 small_write_authorized=false', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            inspectCurrentDbState: async () => buildDbState(),
            runDryRun: () => buildDryRunPayload({ approval_status: 'approved_for_db_write' }),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload(),
            runInsertPolicyPrecheck: async () =>
                buildInsertPolicyPayload({ manifest_approval_status: 'approved_for_db_write' }),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.manifest_approval_status, 'approved_for_db_write');
    assert.equal(payload.small_write_authorized, false);
    assert.equal(payload.db_write_allowed, false);
    assert.match(payload.db_write_allowed_reason, /does not execute small DB writes/);
});

test('--commit 必须 blocked', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runMain(gate, [
        '--source-manifest',
        MANIFEST_PATH,
        '--local-csv',
        CSV_PATH,
        '--commit',
        '--json',
    ]);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'blocked-commit');
    assert.equal(result.payload.blocked, true);
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.67C/);
    assert.equal(result.payload.would_execute_pg_dump, false);
    assert.equal(result.payload.would_execute_pg_restore, false);
    assert.equal(result.payload.would_write_db, false);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for sha256 mismatch');
    });
    const manifest = {
        ...loadManifest(),
        sha256: '0'.repeat(64),
    };
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            dryRunDependencies: {
                readManifest: () => manifest,
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'csv-dry-run-failed');
    assert.equal(payload.sha256_match, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
});

test('row_count mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for row_count mismatch');
    });
    const manifest = {
        ...loadManifest(),
        row_count: 999,
    };
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            dryRunDependencies: {
                readManifest: () => manifest,
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'csv-dry-run-failed');
    assert.equal(payload.row_count_match, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
});

test('text output 应包含所需 summary 字段', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runTextMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH], {
        inspectCurrentDbState: async () => buildDbState(),
        runDryRun: () => buildDryRunPayload(),
        runPreflight: () => buildPreflightPayload(),
        runDuplicatePrecheck: async () => buildDuplicatePayload(),
        runInsertPolicyPrecheck: async () => buildInsertPolicyPayload(),
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /phase=PHASE4\.67C_FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW/);
    assert.match(result.stdout, /csv_dry_run_passed=true/);
    assert.match(result.stdout, /db_write_preflight_passed=true/);
    assert.match(result.stdout, /duplicate_precheck_passed=true/);
    assert.match(result.stdout, /insert_policy_precheck_passed=true/);
    assert.match(result.stdout, /db_write_allowed=false/);
    assert.match(result.stdout, /small_write_authorized=false/);
    assert.match(result.stdout, /would_execute_pg_dump=false/);
    assert.match(result.stdout, /would_execute_pg_restore=false/);
    assert.match(result.stdout, /would_write_db=false/);
    assert.match(result.stdout, /current_db_counts:/);
    assert.match(result.stdout, /pg_dump_command_preview=/);
    assert.match(result.stdout, /required_before_small_db_write:/);
    assert.match(result.stdout, /post_write_validation:/);
    assert.match(result.stdout, /rollback_restore_preview:/);
    assert.match(result.stdout, /no_pg_dump_execution/);
    assert.match(result.stdout, /no_pg_restore_execution/);
});

test('main --help 应输出 usage', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runTextMain(gate, ['--help']);

    assert.equal(result.status, 0);
    assert.match(result.stdout, /football_data_small_write_auth_preview\.js --source-manifest/);
    assert.match(result.stdout, /No DB writes, no pg_dump execution, no pg_restore execution/);
});

test('blocked commit 的文本输出应包含 blocked_reason 与 errors', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runTextMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--commit']);

    assert.equal(result.status, 1);
    assert.match(result.stdout, /mode=blocked-commit/);
    assert.match(
        result.stdout,
        /blocked_reason=BLOCKED: football-data small DB write commit is not wired in Phase 4\.67C\./
    );
    assert.match(result.stdout, /errors=BLOCKED: football-data small DB write commit is not wired in Phase 4\.67C\./);
});

test('文本输出应包含 warnings 行', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runTextMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH], {
        inspectCurrentDbState: async () => buildDbState(),
        runDryRun: () => buildDryRunPayload({ warnings: [{ code: 'warn_1', message: 'unit warning' }] }),
        runPreflight: () => buildPreflightPayload({ warnings: [{ code: 'warn_2', message: 'preflight warning' }] }),
        runDuplicatePrecheck: async () =>
            buildDuplicatePayload({ warnings: [{ code: 'warn_3', message: 'duplicate warning' }] }),
        runInsertPolicyPrecheck: async () =>
            buildInsertPolicyPayload({ warnings: [{ code: 'warn_4', message: 'policy warning' }] }),
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /warnings=\[/);
    assert.match(result.stdout, /unit warning/);
    assert.match(result.stdout, /policy warning/);
});

test('preflight 失败时应返回 db-write-preflight-failed 且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for preflight failure');
    });
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(),
            runPreflight: () => buildPreflightPayload({ ok: false, errors: ['preflight failed'] }),
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'db-write-preflight-failed');
    assert.equal(payload.csv_dry_run_passed, true);
    assert.equal(payload.db_write_preflight_passed, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
    assert.match(payload.errors[0], /preflight failed/);
});

test('duplicate precheck 失败时应返回 duplicate-precheck-failed 且不继续查 DB state', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    let inspectCalled = false;
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            inspectCurrentDbState: async () => {
                inspectCalled = true;
                return buildDbState();
            },
            runDryRun: () => buildDryRunPayload(),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload({ ok: false, errors: ['duplicate failed'] }),
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'duplicate-precheck-failed');
    assert.equal(payload.csv_dry_run_passed, true);
    assert.equal(payload.db_write_preflight_passed, true);
    assert.equal(payload.duplicate_precheck_passed, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(inspectCalled, false);
    assert.match(payload.errors[0], /duplicate failed/);
});

test('insert policy 失败时应返回 insert-policy-precheck-failed 且不继续查 DB state', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    let inspectCalled = false;
    const payload = await gate.runSmallWriteAuthPreview(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            inspectCurrentDbState: async () => {
                inspectCalled = true;
                return buildDbState();
            },
            runDryRun: () => buildDryRunPayload(),
            runPreflight: () => buildPreflightPayload(),
            runDuplicatePrecheck: async () => buildDuplicatePayload(),
            runInsertPolicyPrecheck: async () => buildInsertPolicyPayload({ ok: false, errors: ['policy failed'] }),
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'insert-policy-precheck-failed');
    assert.equal(payload.csv_dry_run_passed, true);
    assert.equal(payload.db_write_preflight_passed, true);
    assert.equal(payload.duplicate_precheck_passed, true);
    assert.equal(payload.insert_policy_precheck_passed, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(inspectCalled, false);
    assert.match(payload.errors[0], /policy failed/);
});

test('main runtime error 应返回 runtime-error payload', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--json'], {
        runDryRun: () => {
            throw new Error('boom');
        },
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'runtime-error');
    assert.equal(result.payload.select_only_db_reads, false);
    assert.match(result.payload.errors[0], /boom/);
});

test('main runtime error 的文本输出应包含 errors', async t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const result = await runTextMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH], {
        runDryRun: () => {
            throw new Error('text boom');
        },
    });

    assert.equal(result.status, 1);
    assert.match(result.stdout, /mode=runtime-error/);
    assert.match(result.stdout, /errors=text boom/);
});

test('inspectCurrentDbState 应支持 injected pool 并在缺少 schema row 时返回 null', async t => {
    installExecutionGuards(t, {
        moduleOverrides: {
            pg: {
                Pool: class FakePool {
                    constructor() {
                        this.ended = false;
                    }

                    async connect() {
                        const calls = [];
                        return {
                            calls,
                            async query(sql) {
                                calls.push(sql);
                                if (sql === 'BEGIN READ ONLY' || sql === 'ROLLBACK') {
                                    return { rows: [] };
                                }
                                if (sql.includes('FROM (')) {
                                    return {
                                        rows: [{ table_name: 'matches', rows: '2' }],
                                    };
                                }
                                if (sql.includes('FROM information_schema.tables')) {
                                    return {
                                        rows: [{ table_name: 'matches' }],
                                    };
                                }
                                if (sql.includes("table_name = 'matches'")) {
                                    return {
                                        rows: [],
                                    };
                                }
                                return { rows: [] };
                            },
                            release() {},
                        };
                    }

                    async end() {
                        this.ended = true;
                    }
                },
            },
        },
    });
    const gate = loadPreviewFresh();
    const state = await gate.inspectCurrentDbState({});

    assert.equal(state.current_db_counts.matches, 2);
    assert.equal(state.current_db_counts.bookmaker_odds_history, 0);
    assert.deepEqual(state.current_db_schema_preview.required_tables_found, ['matches']);
    assert.equal(state.current_db_schema_preview.matches_match_id, null);
});

test('script 作为真实入口执行 --help 应成功', () => {
    const result = spawnSync(process.execPath, [SCRIPT_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /football_data_small_write_auth_preview\.js --source-manifest/);
});

test('buildManifestCompatibleDryRun 应支持 approved_for_db_write manifest 并在成功后还原 approval_status', t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const manifest = {
        ...loadManifest(),
        approval_status: 'approved_for_db_write',
    };
    const wrappedDryRun = gate.buildManifestCompatibleDryRun({
        dryRunDependencies: {
            readManifest: () => manifest,
            parseFootballDataCsv: () => ({
                parser_version: 'unit_parser',
                total_rows: 5,
                parsed_rows: 5,
                candidate_rows: [],
                row_classification: {
                    trainable_label_rows: 0,
                    skipped_rows: 0,
                    invalid_date_rows: 0,
                    missing_team_rows: 0,
                    missing_score_rows: 0,
                    invalid_result_rows: 0,
                    odds_preview_rows: 0,
                },
                warnings: [],
                errors: [],
                non_execution_confirmations: ['no_external_network'],
            }),
        },
    });

    const payload = wrappedDryRun({
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
    });

    assert.equal(payload.ok, true);
    assert.equal(payload.approval_status, 'approved_for_db_write');
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
});

test('buildManifestCompatibleDryRun 在底层 dry-run 失败时应原样返回失败 payload', t => {
    installExecutionGuards(t);
    const gate = loadPreviewFresh();
    const manifest = loadManifest();
    const wrappedDryRun = gate.buildManifestCompatibleDryRun({
        dryRunDependencies: {
            readManifest: () => manifest,
        },
    });

    const payload = wrappedDryRun({
        sourceManifest: MANIFEST_PATH,
        localCsv: path.join(PROJECT_ROOT, 'tests/fixtures/football_data/missing.csv'),
    });

    assert.equal(payload.ok, false);
    assert.equal(payload.local_csv_found, false);
    assert.equal(payload.mode, 'csv-error');
});
