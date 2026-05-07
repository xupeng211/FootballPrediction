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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
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
        throw new Error(`${name} should not be called by football_data_adapter_dry_run`);
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

function loadGateFresh() {
    delete require.cache[SCRIPT_PATH];
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
    assert.equal(payload.would_insert_matches, false);
    assert.equal(payload.would_insert_odds, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
    assert.ok(payload.non_execution_confirmations.includes('no_db_reads'));
    assert.ok(payload.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_legacy_runtime'));
}

test('adapter module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();

    assert.equal(typeof gate.main, 'function');
    assert.equal(typeof gate.runDryRun, 'function');
    assert.equal(typeof gate.validateManifest, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 或 local CSV 参数必须失败', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const missingManifest = runMain(gate, ['--local-csv', CSV_PATH, '--json']);
    const missingCsv = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--json']);

    assert.equal(missingManifest.status, 1);
    assert.equal(missingCsv.status, 1);
    assert.equal(missingManifest.payload.mode, 'argument-error');
    assert.equal(missingCsv.payload.mode, 'argument-error');
    assert.match(missingManifest.payload.errors[0], /provide --source-manifest/);
    assert.match(missingCsv.payload.errors[0], /provide --source-manifest/);
    assertSafetyPayload(missingManifest.payload);
    assertSafetyPayload(missingCsv.payload);
});

test('正确 manifest + CSV dry-run 成功并输出 parser summary', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const result = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--json']);
    const payload = result.payload;

    assert.equal(result.status, 0);
    assert.equal(payload.ok, true);
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, true);
    assert.equal(payload.parser_version, 'PHASE4.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER');
    assert.equal(payload.total_rows, 5);
    assert.equal(payload.trainable_label_rows, 3);
    assert.equal(payload.skipped_rows, 2);
    assert.equal(payload.invalid_date_rows, 1);
    assert.equal(payload.missing_score_rows, 1);
    assert.equal(payload.odds_preview_rows, 3);
    assert.equal(payload.candidate_preview.length, 3);
    assert.equal(payload.candidate_preview[0].would_insert_matches, false);
    assert.equal(payload.candidate_preview[0].would_insert_odds, false);
    assert.equal(payload.candidate_preview[0].odds_preview.odds_preview_only, true);
    assertSafetyPayload(payload);
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('CLI help、等号参数和文本输出应可用', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const help = runTextMain(gate, ['--help']);
    const result = runTextMain(gate, [`--source-manifest=${MANIFEST_PATH}`, `--local-csv=${CSV_PATH}`]);

    assert.equal(help.status, 0);
    assert.match(help.stdout, /football_data_adapter_dry_run\.js --source-manifest/);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /mode=football-data-csv-dry-run/);
    assert.match(result.stdout, /source_manifest_found=true/);
    assert.match(result.stdout, /local_csv_found=true/);
    assert.match(result.stdout, /sha256_match=true/);
    assert.match(result.stdout, /row_count_match=true/);
    assert.match(result.stdout, /parser_version=PHASE4\.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER/);
    assert.match(result.stdout, /candidate_preview=/);
    assert.match(result.stdout, /warnings=/);
    assert.match(result.stdout, /no_external_network/);
    assert.match(result.stdout, /no_db_writes/);
});

test('sha256 mismatch 必须失败且不调用 parser', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const manifest = {
        ...loadManifest(),
        sha256: '0'.repeat(64),
    };
    let parserCalled = false;
    const payload = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => manifest,
            parseFootballDataCsv: () => {
                parserCalled = true;
                return {};
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'integrity-error');
    assert.equal(payload.sha256_match, false);
    assert.equal(payload.row_count_match, true);
    assert.equal(parserCalled, false);
    assert.match(payload.errors[0], /sha256 mismatch/);
    assertSafetyPayload(payload);
});

test('row_count mismatch 必须失败且不调用 parser', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const manifest = {
        ...loadManifest(),
        row_count: 99,
    };
    let parserCalled = false;
    const payload = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => manifest,
            parseFootballDataCsv: () => {
                parserCalled = true;
                return {};
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'integrity-error');
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, false);
    assert.equal(parserCalled, false);
    assert.match(payload.errors[0], /row_count mismatch/);
    assertSafetyPayload(payload);
});

test('approval_status 不允许 dry-run 时必须失败', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const manifest = {
        ...loadManifest(),
        approval_status: 'not_approved',
    };
    const payload = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => manifest,
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'manifest-error');
    assert.equal(payload.approval_status_allowed, false);
    assert.match(payload.errors.join('\n'), /approval_status is not allowed/);
    assertSafetyPayload(payload);
});

test('local CSV 缺失和 manifest JSON 解析失败必须失败且不执行 parser', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const missingCsv = gate.runDryRun({
        sourceManifest: MANIFEST_PATH,
        localCsv: path.join(PROJECT_ROOT, 'tests/fixtures/football_data/missing.csv'),
    });
    const invalidJson = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => {
                throw new Error('synthetic invalid json');
            },
        }
    );

    assert.equal(missingCsv.ok, false);
    assert.equal(missingCsv.mode, 'csv-error');
    assert.equal(missingCsv.source_manifest_found, true);
    assert.equal(missingCsv.local_csv_found, false);
    assert.match(missingCsv.errors[0], /local CSV not found/);
    assert.equal(invalidJson.ok, false);
    assert.equal(invalidJson.mode, 'manifest-error');
    assert.equal(invalidJson.source_manifest_found, true);
    assert.equal(invalidJson.local_csv_found, true);
    assert.match(invalidJson.errors[0], /unable to parse source manifest/);
    assertSafetyPayload(missingCsv);
    assertSafetyPayload(invalidJson);
});

test('manifest row_count 类型非法和未知参数必须失败', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const manifest = {
        ...loadManifest(),
        row_count: '5',
    };
    const invalidRowCount = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => manifest,
        }
    );
    const unknownArg = runMain(gate, ['--unknown-option', '--json']);

    assert.equal(invalidRowCount.ok, false);
    assert.equal(invalidRowCount.mode, 'manifest-error');
    assert.match(invalidRowCount.errors.join('\n'), /row_count must be a non-negative integer/);
    assert.equal(unknownArg.status, 1);
    assert.equal(unknownArg.payload.mode, 'argument-error');
    assert.match(unknownArg.payload.errors[0], /Unknown argument/);
    assertSafetyPayload(invalidRowCount);
    assertSafetyPayload(unknownArg.payload);
});

test('--commit 必须 blocked，即使提供确认参数语义也不写入', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const result = runMain(gate, ['--source-manifest', MANIFEST_PATH, '--local-csv', CSV_PATH, '--commit', '--json']);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'blocked-commit');
    assert.equal(result.payload.blocked, true);
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.63C/);
    assertSafetyPayload(result.payload);
});

test('missing files 和 manifest required fields 失败时也保持 non-execution flags', t => {
    installExecutionGuards(t);
    const gate = loadGateFresh();
    const missingFile = gate.runDryRun({
        sourceManifest: path.join(PROJECT_ROOT, 'tests/fixtures/football_data/source_manifests/missing.json'),
        localCsv: CSV_PATH,
    });
    const invalidManifest = gate.runDryRun(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            readManifest: () => ({
                source_name: 'football_data_local_synthetic_fixture',
                approval_status: 'dry_run_only',
                sha256: loadManifest().sha256,
                row_count: 5,
            }),
        }
    );

    assert.equal(missingFile.ok, false);
    assert.equal(missingFile.source_manifest_found, false);
    assert.match(missingFile.errors[0], /source manifest not found/);
    assert.equal(invalidManifest.ok, false);
    assert.equal(invalidManifest.manifest_required_fields_present, false);
    assert.ok(invalidManifest.manifest_missing_fields.includes('local_csv_path'));
    assert.ok(invalidManifest.manifest_missing_fields.includes('mapping_version'));
    assertSafetyPayload(missingFile);
    assertSafetyPayload(invalidManifest);
});
