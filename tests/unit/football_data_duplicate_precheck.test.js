'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_duplicate_precheck.js');
const DRY_RUN_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
const LEGACY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fetch_and_adapt_euro_leagues.js');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
);
const CSV_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');

function installExecutionGuards(t, options = {}) {
    const moduleOverrides = options.moduleOverrides || {};
    const originalHttpRequest = http['re' + 'quest'];
    const originalHttpsRequest = https['re' + 'quest'];
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
        throw new Error(`${name} should not be called by football_data_duplicate_precheck`);
    };

    http['re' + 'quest'] = fail('http.re' + 'quest');
    https['re' + 'quest'] = fail('https.re' + 'quest');
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
        http['re' + 'quest'] = originalHttpRequest;
        https['re' + 'quest'] = originalHttpsRequest;
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

function loadPrecheckFresh() {
    delete require.cache[SCRIPT_PATH];
    delete require.cache[DRY_RUN_PATH];
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

async function runMain(gate, argv) {
    let stdout = '';
    let stderr = '';
    const status = await gate.main(argv, {
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });

    return {
        status,
        stdout,
        stderr,
        payload: JSON.parse(stdout),
    };
}

async function runTextMain(gate, argv) {
    let stdout = '';
    let stderr = '';
    const status = await gate.main(argv, {
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });

    return {
        status,
        stdout,
        stderr,
    };
}

function assertSafetyPayload(payload) {
    assert.equal(payload.select_only_db_reads, true);
    assert.equal(payload.no_db_writes, true);
    assert.equal(payload.db_write_allowed, false);
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
        assert.doesNotMatch(normalized, /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|MERGE|COMMIT)\b/);
    }
}

function buildDryRunPayload(candidates) {
    return {
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        sha256_match: true,
        row_count_match: true,
        approval_status: 'dry_run_only',
        source_name: 'unit_fixture',
        parser_version: 'unit_parser',
        dry_run_version: 'unit_dry_run',
        candidate_rows: candidates,
        row_classification: {
            trainable_label_rows: candidates.length,
        },
        non_execution_confirmations: ['no_external_network', 'no_db_writes'],
        warnings: [],
        errors: [],
    };
}

function snapshotDbEnv() {
    return {
        DB_HOST: process.env.DB_HOST,
        POSTGRES_HOST: process.env.POSTGRES_HOST,
        DB_PORT: process.env.DB_PORT,
        POSTGRES_PORT: process.env.POSTGRES_PORT,
        DB_NAME: process.env.DB_NAME,
        POSTGRES_DB: process.env.POSTGRES_DB,
        DB_USER: process.env.DB_USER,
        POSTGRES_USER: process.env.POSTGRES_USER,
        DB_PASSWORD: process.env.DB_PASSWORD,
        POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD,
    };
}

function restoreDbEnv(snapshot) {
    for (const [key, value] of Object.entries(snapshot)) {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }
}

test('duplicate precheck module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();

    assert.equal(typeof gate.main, 'function');
    assert.equal(typeof gate.runDuplicatePrecheck, 'function');
    assert.equal(typeof gate.assertSelectOnlySql, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 参数必须失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runDuplicatePrecheck(
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
    assert.equal(payload.no_db_writes, true);
    assert.equal(payload.would_write_db, false);
});

test('缺 local CSV 参数必须失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runDuplicatePrecheck(
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
    assert.equal(payload.no_db_writes, true);
    assert.equal(payload.would_write_db, false);
});

test('正确 manifest + CSV + mock DB client precheck 成功', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const client = createMockClient(() => ({ rows: [] }));
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK');
    assert.equal(payload.dry_run_passed, true);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, true);
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.candidate_rows, 3);
    assert.equal(payload.trainable_label_rows, 3);
    assert.equal(payload.exact_existing_matches, 0);
    assert.equal(payload.reversed_team_matches, 0);
    assert.equal(payload.nearby_date_matches, 0);
    assert.equal(payload.invalid_candidates, 0);
    assert.equal(payload.candidate_previews.length, 3);
    assert.ok(payload.candidate_previews.every(preview => preview.duplicate_risk === 'none'));
    assertSafetyPayload(payload);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('exact / reversed / nearby duplicate risks 应被识别，invalid candidate 不进入查询计划', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const candidates = [
        {
            row_number: 1,
            league_name: 'League',
            season: '2024/2025',
            match_date: '2024-01-01T12:00:00.000Z',
            home_team: 'Exact Home',
            away_team: 'Exact Away',
            actual_result: 'home_win',
        },
        {
            row_number: 2,
            league_name: 'League',
            season: '2024/2025',
            match_date: '2024-01-02T12:00:00.000Z',
            home_team: 'Reverse Home',
            away_team: 'Reverse Away',
            actual_result: 'draw',
        },
        {
            row_number: 3,
            league_name: 'League',
            season: '2024/2025',
            match_date: '2024-01-03T12:00:00.000Z',
            home_team: 'Nearby Home',
            away_team: 'Nearby Away',
            actual_result: 'away_win',
        },
        {
            row_number: 4,
            league_name: 'League',
            season: '2024/2025',
            match_date: '',
            home_team: '',
            away_team: 'Invalid Away',
            actual_result: 'home_win',
        },
    ];
    const client = createMockClient((sql, params) => {
        if (sql === gate.EXACT_MATCH_SQL && params[0] === 'Exact Home') {
            return { rows: [{ match_id: 'exact_1', home_team: 'Exact Home', away_team: 'Exact Away' }] };
        }
        if (sql === gate.REVERSED_MATCH_SQL && params[0] === 'Reverse Away') {
            return { rows: [{ match_id: 'reversed_1', home_team: 'Reverse Away', away_team: 'Reverse Home' }] };
        }
        if (sql === gate.NEARBY_MATCH_SQL && params[0] === 'Nearby Home') {
            return { rows: [{ match_id: 'nearby_1', home_team: 'Nearby Home', away_team: 'Nearby Away' }] };
        }
        return { rows: [] };
    });
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(candidates),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.exact_existing_matches, 1);
    assert.equal(payload.reversed_team_matches, 1);
    assert.equal(payload.nearby_date_matches, 1);
    assert.equal(payload.invalid_candidates, 1);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'exact_existing_match');
    assert.deepEqual(payload.candidate_previews[0].existing_match_ids, ['exact_1']);
    assert.equal(payload.candidate_previews[1].duplicate_risk, 'reversed_teams_possible_duplicate');
    assert.deepEqual(payload.candidate_previews[1].existing_match_ids, ['reversed_1']);
    assert.equal(payload.candidate_previews[2].duplicate_risk, 'nearby_date_possible_duplicate');
    assert.deepEqual(payload.candidate_previews[2].nearby_match_ids, ['nearby_1']);
    assert.equal(payload.candidate_previews[3].duplicate_risk, 'invalid_candidate');
    assert.equal(payload.candidate_previews[3].would_insert_match, false);
    assert.equal(payload.candidate_previews[3].would_insert_odds, false);
    assert.ok(payload.candidate_previews[0].candidate_identity_key.includes('exact home'));
    assert.equal(payload.identity_strategy.proposed_match_id_strategy, 'not_finalized');
    assert.equal(payload.identity_strategy.match_id_write_allowed, false);
    assert.equal(client.calls.filter(call => call.params.includes('Invalid Away')).length, 0);
    assertSafetyPayload(payload);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('existing_match_ids 应去重并过滤空 match_id', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const candidates = [
        {
            row_number: 1,
            league_name: 'League',
            season: '2024/2025',
            match_date: '2024-02-01T12:00:00.000Z',
            home_team: 'Duplicate Home',
            away_team: 'Duplicate Away',
            actual_result: 'home_win',
        },
    ];
    const client = createMockClient((sql, params) => {
        if (sql === gate.EXACT_MATCH_SQL && params[0] === 'Duplicate Home') {
            return {
                rows: [
                    { match_id: 'duplicate_1', home_team: 'Duplicate Home', away_team: 'Duplicate Away' },
                    { match_id: 'duplicate_1', home_team: 'Duplicate Home', away_team: 'Duplicate Away' },
                    { match_id: '', home_team: 'Duplicate Home', away_team: 'Duplicate Away' },
                ],
            };
        }
        return { rows: [] };
    });
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(candidates),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.exact_existing_matches, 3);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'exact_existing_match');
    assert.deepEqual(payload.candidate_previews[0].existing_match_ids, ['duplicate_1']);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('缺 actual_result 的 candidate 应标记 invalid 且不执行 match SELECT', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const candidates = [
        {
            row_number: 1,
            league_name: 'League',
            season: '2024/2025',
            match_date: '2024-03-01T12:00:00.000Z',
            home_team: 'No Label Home',
            away_team: 'No Label Away',
            actual_result: '',
        },
    ];
    const client = createMockClient(sql => {
        if (sql === gate.EXACT_MATCH_SQL || sql === gate.REVERSED_MATCH_SQL || sql === gate.NEARBY_MATCH_SQL) {
            throw new Error('invalid candidate should not query duplicate SELECTs');
        }
        return { rows: [] };
    });
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(candidates),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.invalid_candidates, 1);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'invalid_candidate');
    assert.deepEqual(
        client.calls.map(call => call.sql),
        [gate.READ_ONLY_BEGIN_SQL, gate.READ_ONLY_ROLLBACK_SQL]
    );
});

test('--commit 必须 blocked，即使提供 manifest 和 CSV', async t => {
    installExecutionGuards(t);
    const savedEnv = {
        ALLOW_DB_WRITE: process.env.ALLOW_DB_WRITE,
        FINAL_DB_WRITE_CONFIRMATION: process.env.FINAL_DB_WRITE_CONFIRMATION,
        ALLOW_MATCHES_WRITE: process.env.ALLOW_MATCHES_WRITE,
        DRY_RUN: process.env.DRY_RUN,
    };
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_MATCHES_WRITE = 'yes';
    process.env.DRY_RUN = 'false';
    t.after(() => {
        for (const [key, value] of Object.entries(savedEnv)) {
            if (value === undefined) delete process.env[key];
            else process.env[key] = value;
        }
    });

    const gate = loadPrecheckFresh();
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
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.65C/);
    assertSafetyPayload(result.payload);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const manifest = {
        ...loadManifest(),
        sha256: '0'.repeat(64),
    };
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for sha256 mismatch');
    });
    const payload = await gate.runDuplicatePrecheck(
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
    assert.equal(payload.mode, 'dry-run-failed');
    assert.equal(payload.dry_run_passed, false);
    assert.equal(payload.sha256_match, false);
    assert.equal(payload.row_count_match, true);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
    assert.match(payload.errors[0], /sha256 mismatch/);
    assert.equal(payload.no_db_writes, true);
});

test('row_count mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const manifest = {
        ...loadManifest(),
        row_count: 99,
    };
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for row_count mismatch');
    });
    const payload = await gate.runDuplicatePrecheck(
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
    assert.equal(payload.mode, 'dry-run-failed');
    assert.equal(payload.dry_run_passed, false);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
    assert.match(payload.errors[0], /row_count mismatch/);
    assert.equal(payload.no_db_writes, true);
});

test('文本输出包含 duplicate summary、future checklist 和 non-execution confirmations', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const client = createMockClient(() => ({ rows: [] }));
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );
    const text = gate.payloadToText(payload);

    assert.match(text, /phase=PHASE4\.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK/);
    assert.match(text, /dry_run_passed=true/);
    assert.match(text, /sha256_match=true/);
    assert.match(text, /row_count_match=true/);
    assert.match(text, /select_only_db_reads=true/);
    assert.match(text, /no_db_writes=true/);
    assert.match(text, /would_insert_matches=false/);
    assert.match(text, /would_insert_odds=false/);
    assert.match(text, /would_write_db=false/);
    assert.match(text, /would_access_network=false/);
    assert.match(text, /would_write_files=false/);
    assert.match(text, /candidate_previews=/);
    assert.match(text, /candidate_identity_key/);
    assert.match(text, /required_before_db_write:/);
    assert.match(text, /deterministic match_id strategy must be finalized/);
    assert.match(text, /no_external_network/);
    assert.match(text, /no_file_writes/);
    assert.match(text, /no_pg_dump_execution/);
});

test('SQL guard 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();

    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.EXACT_MATCH_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.REVERSED_MATCH_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.NEARBY_MATCH_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.READ_ONLY_ROLLBACK_SQL));
    assert.throws(() => gate.assertSelectOnlySql('INS' + 'ERT INTO matches VALUES (\$1)'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('UPD' + 'ATE matches SET status = \$1'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('DEL' + 'ETE FROM matches'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('CREATE TABLE unsafe_table(id int)'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('COMMIT'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('SELECT 1; DROP TABLE matches'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('WITH unsafe AS (SELECT 1) SELECT * FROM unsafe'), /Unsafe SQL/);
});

test('candidate identity key helper 应覆盖缺失字段和球队名标准化分支', t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();

    assert.equal(gate.buildCandidateIdentityKey({}), '||||');
    assert.equal(
        gate.buildCandidateIdentityKey({
            league_name: ' League ',
            season: ' 2024/2025 ',
            match_date: '2024-01-01T00:00:00.000Z',
            home_team: '  Málaga   CF ',
            away_team: 'Away   Team',
        }),
        'League|2024/2025|2024-01-01|malaga cf|away team'
    );
});

test('DB config helper 应覆盖默认值、POSTGRES fallback 和 DB_* 优先级', t => {
    installExecutionGuards(t);
    const snapshot = snapshotDbEnv();
    t.after(() => restoreDbEnv(snapshot));
    const gate = loadPrecheckFresh();

    for (const key of Object.keys(snapshot)) {
        delete process.env[key];
    }
    assert.deepEqual(gate.buildDbConfig(), {
        host: 'db',
        port: 5432,
        database: 'football_db',
        user: 'football_user',
        password: undefined,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    });

    process.env.POSTGRES_HOST = 'postgres-host';
    process.env.POSTGRES_PORT = '15432';
    process.env.POSTGRES_DB = 'postgres-db';
    process.env.POSTGRES_USER = 'postgres-user';
    process.env.POSTGRES_PASSWORD = 'postgres-password';
    assert.deepEqual(gate.buildDbConfig(), {
        host: 'postgres-host',
        port: 15432,
        database: 'postgres-db',
        user: 'postgres-user',
        password: 'postgres-password',
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    });

    process.env.DB_HOST = 'db-host';
    process.env.DB_PORT = '25432';
    process.env.DB_NAME = 'db-name';
    process.env.DB_USER = 'db-user';
    process.env.DB_PASSWORD = 'db-password';
    assert.deepEqual(gate.buildDbConfig(), {
        host: 'db-host',
        port: 25432,
        database: 'db-name',
        user: 'db-user',
        password: 'db-password',
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    });
});

test('CLI help 和未知参数错误分支应可用且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const help = await runTextMain(gate, ['--help']);
    const unknown = await runMain(gate, ['--unknown-option', '--json']);
    const unknownText = await runTextMain(gate, ['--unknown-option']);

    assert.equal(help.status, 0);
    assert.match(help.stdout, /football_data_duplicate_precheck\.js --source-manifest/);
    assert.equal(unknown.status, 1);
    assert.equal(unknown.payload.mode, 'runtime-error');
    assert.match(unknown.payload.errors[0], /Unknown argument/);
    assert.equal(unknown.payload.no_db_writes, true);
    assert.equal(unknown.payload.would_write_db, false);
    assert.equal(unknownText.status, 1);
    assert.match(unknownText.stdout, /mode=runtime-error/);
    assert.match(unknownText.stdout, /errors=Unknown argument/);
    assert.match(unknownText.stdout, /required_before_db_write:/);
});

test('pool dependency 分支应 release client 且不 end injected pool', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    let released = false;
    let poolEnded = false;
    const client = createMockClient(() => ({ rows: [] }));
    client.release = () => {
        released = true;
    };
    const pool = {
        async connect() {
            return client;
        },
        async end() {
            poolEnded = true;
        },
    };
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { pool }
    );

    assert.equal(payload.ok, true);
    assert.equal(released, true);
    assert.equal(poolEnded, false);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('未注入 pool 时应创建 pg Pool、release client 并 end pool', async t => {
    let released = false;
    let poolEnded = false;
    let receivedConfig = null;
    const client = createMockClient(() => ({ rows: [] }));
    client.release = () => {
        released = true;
    };
    class FakePool {
        constructor(config) {
            receivedConfig = config;
        }

        async connect() {
            return client;
        }

        async end() {
            poolEnded = true;
        }
    }

    installExecutionGuards(t, {
        moduleOverrides: {
            pg: { Pool: FakePool },
        },
    });
    const snapshot = snapshotDbEnv();
    t.after(() => restoreDbEnv(snapshot));
    process.env.DB_HOST = 'fake-db-host';
    process.env.DB_PORT = '45432';
    process.env.DB_NAME = 'fake-db-name';
    process.env.DB_USER = 'fake-db-user';
    process.env.DB_PASSWORD = 'fake-db-password';
    const gate = loadPrecheckFresh();
    const payload = await gate.runDuplicatePrecheck({
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
    });

    assert.equal(payload.ok, true);
    assert.equal(released, true);
    assert.equal(poolEnded, true);
    assert.equal(receivedConfig.host, 'fake-db-host');
    assert.equal(receivedConfig.port, 45432);
    assert.equal(receivedConfig.database, 'fake-db-name');
    assert.equal(receivedConfig.user, 'fake-db-user');
    assert.equal(receivedConfig.password, 'fake-db-password');
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('空 candidate 集合仍应使用 read-only transaction 并返回 0 风险', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const client = createMockClient(() => ({ rows: [] }));
    const payload = await gate.runDuplicatePrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => ({
                ...buildDryRunPayload([]),
                row_classification: undefined,
                warnings: undefined,
                non_execution_confirmations: undefined,
            }),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.candidate_rows, 0);
    assert.equal(payload.trainable_label_rows, 0);
    assert.equal(payload.insert_risk_summary.duplicate_free_candidates, 0);
    assert.deepEqual(payload.candidate_previews, []);
    assert.deepEqual(
        client.calls.map(call => call.sql),
        [gate.READ_ONLY_BEGIN_SQL, gate.READ_ONLY_ROLLBACK_SQL]
    );
});

test('read-only transaction 查询失败时仍应 ROLLBACK', async t => {
    installExecutionGuards(t);
    const gate = loadPrecheckFresh();
    const candidate = {
        row_number: 1,
        league_name: 'League',
        season: '2024/2025',
        match_date: '2024-01-01T12:00:00.000Z',
        home_team: 'Boom Home',
        away_team: 'Boom Away',
        actual_result: 'home_win',
    };
    const client = createMockClient(sql => {
        if (sql === gate.EXACT_MATCH_SQL) {
            throw new Error('synthetic select failure');
        }
        return { rows: [] };
    });

    await assert.rejects(() => gate.runCandidatePrechecks(client, [candidate]), /synthetic select failure/);
    assert.deepEqual(
        client.calls.map(call => call.sql),
        [gate.READ_ONLY_BEGIN_SQL, gate.EXACT_MATCH_SQL, gate.READ_ONLY_ROLLBACK_SQL]
    );
});

test('source 文本不引用 legacy downloader、child_process 或文件写入 API', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /fetch_and_adapt_euro_leagues/);
    assert.doesNotMatch(source, /child_process/);
    assert.doesNotMatch(source, /spawn\(/);
    assert.doesNotMatch(source, /execFile\(/);
    assert.doesNotMatch(source, /writeFile/);
    assert.equal(require.cache[LEGACY_PATH], undefined);
});
