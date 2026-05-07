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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_db_write_preflight.js');
const DRY_RUN_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
const LEGACY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fetch_and_adapt_euro_leagues.js');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
);
const CSV_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');

function installExecutionGuards(t) {
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
        throw new Error(`${name} should not be called by football_data_db_write_preflight`);
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
            'pg',
            'pg-native',
            'net',
            'node:net',
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
        ]);
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

function loadPreflightFresh() {
    delete require.cache[SCRIPT_PATH];
    delete require.cache[DRY_RUN_PATH];
    return require(SCRIPT_PATH);
}

function loadManifest() {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function runMain(gate, argv) {
    let stdout = '';
    let stderr = '';
    const status = gate.main(argv, {
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

function runTextMain(gate, argv) {
    let stdout = '';
    let stderr = '';
    const status = gate.main(argv, {
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
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.would_insert_matches, false);
    assert.equal(payload.would_insert_odds, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.commit_gate, 'blocked');
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
    assert.ok(payload.non_execution_confirmations.includes('no_db_reads'));
    assert.ok(payload.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_legacy_runtime'));
    assert.ok(payload.non_execution_confirmations.includes('no_pg_dump_execution'));
    assert.ok(payload.non_execution_confirmations.includes('no_training'));
    assert.ok(payload.non_execution_confirmations.includes('no_prediction_execution'));
}

test('preflight module 可以 import 且不加载 legacy runtime / pg / child_process', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();

    assert.equal(typeof gate.main, 'function');
    assert.equal(typeof gate.runPreflight, 'function');
    assert.equal(typeof gate.buildRequiredBeforeDbWrite, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 参数必须失败', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = runMain(gate, ['--local-csv', CSV_PATH, '--json']);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'argument-error');
    assert.match(result.payload.errors[0], /provide --source-manifest/);
    assertSafetyPayload(result.payload);
});

test('缺 local CSV 参数必须失败', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--json']);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'argument-error');
    assert.match(result.payload.errors[0], /provide --source-manifest/);
    assertSafetyPayload(result.payload);
});

test('正确 manifest + CSV preflight 成功并输出 future DB write preview', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--json']);
    const payload = result.payload;

    assert.equal(result.status, 0);
    assert.equal(payload.phase, 'PHASE4.64C_FOOTBALL_DATA_DB_WRITE_PREFLIGHT');
    assert.equal(payload.ok, true);
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.dry_run_passed, true);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, true);
    assert.equal(payload.approval_status, 'dry_run_only');
    assert.equal(payload.candidate_rows, 3);
    assert.equal(payload.trainable_label_rows, 3);
    assert.equal(payload.odds_preview_rows, 3);
    assert.equal(payload.preflight_plan.max_rows_preview, 3);
    assert.equal(payload.preflight_plan.match_write_policy, 'future_small_batch_only_after_backup_and_authorization');
    assertSafetyPayload(payload);
});

test('required_before_db_write checklist 和 runbook preview 必须存在', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = gate.runPreflight({
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
    });

    assert.equal(payload.ok, true);
    assert.ok(payload.required_before_db_write.includes('approval_status must be approved_for_db_write'));
    assert.ok(payload.required_before_db_write.includes('pg_dump backup must be created immediately before write'));
    assert.ok(payload.required_before_db_write.includes('training/prediction must remain blocked'));
    assert.ok(payload.future_pg_dump_runbook.some(item => item.includes('Create pg_dump backup')));
    assert.ok(payload.future_validation_checklist.some(item => item.includes('post-write SELECT-only counts')));
    assertSafetyPayload(payload);
});

test('approval_status=dry_run_only 时 db_write_allowed=false', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = gate.runPreflight({
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
    });

    assert.equal(payload.approval_status, 'dry_run_only');
    assert.equal(payload.db_write_allowed, false);
    assert.match(payload.db_write_allowed_reason, /not DB write approval/);
    assertSafetyPayload(payload);
});

test('--commit 必须 blocked，即使提供 manifest 和 CSV', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--commit', '--json']);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'blocked-commit');
    assert.equal(result.payload.blocked, true);
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.64C/);
    assertSafetyPayload(result.payload);
});

test('sha256 mismatch 时 preflight 失败且 parser 不执行', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const manifest = {
        ...loadManifest(),
        sha256: '0'.repeat(64),
    };
    let parserCalled = false;
    const payload = gate.runPreflight(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dryRunDependencies: {
                readManifest: () => manifest,
                parseFootballDataCsv: () => {
                    parserCalled = true;
                    return {};
                },
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'dry-run-failed');
    assert.equal(payload.dry_run_passed, false);
    assert.equal(payload.sha256_match, false);
    assert.equal(payload.row_count_match, true);
    assert.equal(parserCalled, false);
    assert.match(payload.errors[0], /sha256 mismatch/);
    assertSafetyPayload(payload);
});

test('row_count mismatch 时 preflight 失败且 parser 不执行', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const manifest = {
        ...loadManifest(),
        row_count: 99,
    };
    let parserCalled = false;
    const payload = gate.runPreflight(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dryRunDependencies: {
                readManifest: () => manifest,
                parseFootballDataCsv: () => {
                    parserCalled = true;
                    return {};
                },
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'dry-run-failed');
    assert.equal(payload.dry_run_passed, false);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, false);
    assert.equal(parserCalled, false);
    assert.match(payload.errors[0], /row_count mismatch/);
    assertSafetyPayload(payload);
});

test('文本输出包含安全确认和 blocked commit gate', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = runTextMain(gate, [`--source-manifest=${MANIFEST_PATH}`, `--local-csv=${CSV_PATH}`]);

    assert.equal(result.status, 0);
    assert.match(result.stdout, /phase=PHASE4\.64C_FOOTBALL_DATA_DB_WRITE_PREFLIGHT/);
    assert.match(result.stdout, /dry_run_passed=true/);
    assert.match(result.stdout, /sha256_match=true/);
    assert.match(result.stdout, /row_count_match=true/);
    assert.match(result.stdout, /db_write_allowed=false/);
    assert.match(result.stdout, /would_insert_matches=false/);
    assert.match(result.stdout, /would_insert_odds=false/);
    assert.match(result.stdout, /would_write_db=false/);
    assert.match(result.stdout, /would_execute_pg_dump=false/);
    assert.match(result.stdout, /would_access_network=false/);
    assert.match(result.stdout, /would_write_files=false/);
    assert.match(result.stdout, /commit_gate=blocked/);
    assert.match(result.stdout, /required_before_db_write:/);
    assert.match(result.stdout, /approval_status must be approved_for_db_write/);
    assert.match(result.stdout, /no_external_network/);
    assert.match(result.stdout, /no_db_writes/);
    assert.match(result.stdout, /no_file_writes/);
    assert.match(result.stdout, /no_pg_dump_execution/);
});

test('source 文本不引用 legacy downloader、pg 或 child_process runtime', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /fetch_and_adapt_euro_leagues/);
    assert.doesNotMatch(source, /require\(['"]pg['"]\)/);
    assert.doesNotMatch(source, /require\(['"]node:pg['"]\)/);
    assert.doesNotMatch(source, /child_process/);
    assert.doesNotMatch(source, /spawn\(/);
    assert.doesNotMatch(source, /execFile\(/);
});
