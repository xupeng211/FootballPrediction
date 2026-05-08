'use strict';
/* eslint-disable max-lines -- Phase 4.70C keeps the packet file preflight safety contract in one test file. */

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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_preflight.js');
const PACKET_ASSEMBLY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_packet_assembly.js');
const LEGACY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fetch_and_adapt_euro_leagues.js');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
);
const CSV_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');
const APPROVAL_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md'
);
const RUNBOOK_TEMPLATE_PATH = path.join(PROJECT_ROOT, 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md');

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_packet_file_preflight`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
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
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.createWriteStream = originalCreateWriteStream;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        Module._load = originalLoad;
    });
}

function loadPreflightFresh() {
    for (const modulePath of [SCRIPT_PATH, PACKET_ASSEMBLY_PATH]) {
        delete require.cache[modulePath];
    }
    return require(SCRIPT_PATH);
}

function baseArgs(overrides = {}) {
    return {
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
        approvalForm: APPROVAL_FORM_PATH,
        runbookTemplate: RUNBOOK_TEMPLATE_PATH,
        ...overrides,
    };
}

function buildPacketPayload(overrides = {}) {
    return {
        phase: 'PHASE4.69C_FOOTBALL_DATA_SMALL_WRITE_PACKET_ASSEMBLY',
        mode: 'football-data-small-write-packet-assembly',
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_form_found: true,
        runbook_template_found: true,
        csv_dry_run_passed: true,
        db_write_preflight_passed: true,
        duplicate_precheck_passed: true,
        insert_policy_precheck_passed: true,
        small_write_auth_preview_passed: true,
        approval_form_validation_passed: true,
        select_only_db_reads: true,
        packet_write_allowed: false,
        db_write_allowed: false,
        small_write_authorized: false,
        would_write_packet_file: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        commit_gate: 'blocked',
        approval_status: 'not_approved',
        final_human_confirmation: false,
        approval_form_is_template: true,
        approval_granted: false,
        packet_sections: [
            'source_manifest_summary',
            'local_csv_summary',
            'csv_dry_run_summary',
            'db_write_preflight_summary',
            'duplicate_precheck_summary',
            'insert_policy_summary',
            'small_write_auth_preview_summary',
            'runbook_template_summary',
            'approval_form_summary',
            'proposed_match_ids',
            'insert_candidate_table',
            'blocked_candidate_table',
            'manual_review_table',
            'pg_dump_command_preview',
            'post_write_validation_checklist',
            'rollback_restore_preview',
            'final_human_approval_required',
        ],
        source_manifest_summary: {
            path: 'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json',
            source_name: 'football_data_local_synthetic_fixture',
            sha256: 'abcdef1234567890fedcba0987654321abcdef1234567890fedcba0987654321',
            row_count: 3,
        },
        local_csv_summary: {
            path: 'tests/fixtures/football_data/football_data_sample_phase462c.csv',
            actual_sha256: 'abcdef1234567890fedcba0987654321abcdef1234567890fedcba0987654321',
            expected_sha256: 'abcdef1234567890fedcba0987654321abcdef1234567890fedcba0987654321',
            actual_row_count: 3,
            expected_row_count: 3,
        },
        csv_dry_run_summary: {
            phase: 'PHASE4.63C_FOOTBALL_DATA_ADAPTER_DRY_RUN',
            ok: true,
        },
        db_write_preflight_summary: {
            phase: 'PHASE4.64C_FOOTBALL_DATA_DB_WRITE_PREFLIGHT',
            ok: true,
        },
        duplicate_precheck_summary: {
            phase: 'PHASE4.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK',
            ok: true,
        },
        insert_policy_summary: {
            phase: 'PHASE4.66C_FOOTBALL_DATA_INSERT_POLICY',
            ok: true,
        },
        small_write_auth_preview_summary: {
            phase: 'PHASE4.67C_FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW',
            ok: true,
        },
        runbook_template_summary: {
            path: 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md',
        },
        approval_form_summary: {
            path: 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md',
            approval_status: 'not_approved',
            final_human_confirmation: false,
        },
        proposed_match_ids: ['fd_alpha_11111111', 'fd_beta_22222222'],
        insert_candidate_table: [{ proposed_match_id: 'fd_alpha_11111111' }],
        blocked_candidate_table: [{ proposed_match_id: 'fd_beta_22222222' }],
        manual_review_table: [],
        pg_dump_command_preview: 'docker compose -f docker-compose.dev.yml exec -T db pg_dump ...',
        pg_restore_command_preview: 'docker compose -f docker-compose.dev.yml exec -T db pg_restore ...',
        post_write_validation_checklist: ['compare before/after row counts'],
        rollback_restore_preview: ['restore is not executed automatically'],
        final_human_approval_required: {
            required: true,
            approval_granted: false,
        },
        current_db_counts: {
            matches: 2,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildDependencies(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        runPacketAssembly: async () => buildPacketPayload(),
        ...overrides,
    };
}

async function runJsonMain(gate, argv, dependencies = buildDependencies()) {
    let stdout = '';
    let stderr = '';
    const status = await gate.main(
        [...argv, '--json'],
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

function assertSafetyPayload(payload) {
    assert.equal(payload.packet_file_generation_allowed, false);
    assert.equal(payload.packet_write_allowed, false);
    assert.equal(payload.would_create_packet_directory, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_packet_manifest, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.approval_granted, false);
}

test('packet file preflight module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();

    assert.equal(typeof gate.runPacketFilePreflight, 'function');
    assert.equal(typeof gate.main, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs({ sourceManifest: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /provide --source-manifest/);
});

test('缺 local CSV 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs({ localCsv: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /provide --source-manifest/);
});

test('缺 approval form 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs({ approvalForm: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /approval-form/);
});

test('缺 runbook template 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs({ runbookTemplate: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /runbook-template/);
});

test('正确输入 + mock packet preview 成功', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT');
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.approval_form_found, true);
    assert.equal(payload.runbook_template_found, true);
    assert.equal(payload.packet_preview_passed, true);
    assert.equal(payload.approval_form_validation_passed, true);
    assert.equal(payload.select_only_db_reads, true);
    assertSafetyPayload(payload);
});

test('输出 future packet preview 和 metadata', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.match(payload.future_packet_directory_preview, /^docs\/_packets\/football_data\/small_write\/<timestamp>_/);
    assert.match(payload.future_packet_file_preview, /^football_data_small_write_packet_[a-z0-9_]+_[a-z0-9]{8}\.json$/);
    assert.match(
        payload.future_packet_manifest_preview,
        /^football_data_small_write_packet_manifest_[a-z0-9_]+_[a-z0-9]{8}\.json$/
    );
    assert.deepEqual(Object.keys(payload.future_packet_metadata), gate.FUTURE_PACKET_METADATA_FIELDS);
});

test('approval 默认 not_approved 且 final_human_confirmation=false', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.approval_status, 'not_approved');
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.approval_form_is_template, true);
    assert.equal(payload.approval_granted, false);
});

test('--commit blocked', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const result = await runJsonMain(gate, [
        '--source-manifest',
        MANIFEST_PATH,
        '--local-csv',
        CSV_PATH,
        '--approval-form',
        APPROVAL_FORM_PATH,
        '--runbook-template',
        RUNBOOK_TEMPLATE_PATH,
        '--commit',
    ]);

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'blocked-commit');
    assert.equal(result.payload.blocked, true);
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.70C/);
    assertSafetyPayload(result.payload);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    let packetPreviewCalled = false;
    const payload = await gate.runPacketFilePreflight(
        baseArgs(),
        buildDependencies({
            runPacketAssembly: async () => {
                packetPreviewCalled = true;
                return buildPacketPayload({
                    ok: false,
                    mode: 'csv-dry-run-failed',
                    select_only_db_reads: false,
                    errors: ['sha256 mismatch; parser was not executed'],
                });
            },
        })
    );

    assert.equal(packetPreviewCalled, true);
    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'packet-preview-failed');
    assert.equal(payload.select_only_db_reads, false);
});

test('row_count mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(
        baseArgs(),
        buildDependencies({
            runPacketAssembly: async () =>
                buildPacketPayload({
                    ok: false,
                    mode: 'csv-dry-run-failed',
                    select_only_db_reads: false,
                    errors: ['row_count mismatch; parser was not executed'],
                }),
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'packet-preview-failed');
    assert.equal(payload.select_only_db_reads, false);
});

test('approval form invalid 时失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(
        baseArgs(),
        buildDependencies({
            runPacketAssembly: async () =>
                buildPacketPayload({
                    ok: false,
                    mode: 'approval-form-validation-failed',
                    approval_form_validation_passed: false,
                    errors: ['approval_status must remain not_approved'],
                }),
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'packet-preview-failed');
    assert.match(payload.errors.join('\n'), /not_approved/);
});

test('packet sections 缺失时失败', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(
        baseArgs(),
        buildDependencies({
            runPacketAssembly: async () =>
                buildPacketPayload({
                    packet_sections: ['source_manifest_summary'],
                }),
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'packet-section-validation-failed');
    assert.equal(payload.packet_preview_passed, true);
    assert.equal(payload.packet_sections_complete, false);
    assert.ok(payload.packet_sections_missing.includes('local_csv_summary'));
});

test('packet file preflight 不访问外网', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
});

test('packet file preflight 不写文件、不创建目录、不写 packet 文件', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.would_create_packet_directory, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_packet_manifest, false);
    assert.ok(payload.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_packet_directory_create'));
    assert.ok(payload.non_execution_confirmations.includes('no_packet_file_write'));
});

test('packet file preflight 不执行 pg_dump / pg_restore', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.match(payload.pg_dump_command_preview, /pg_dump/);
    assert.match(payload.pg_restore_command_preview, /pg_restore/);
});

test('packet file preflight 不 spawn child process', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const payload = await gate.runPacketFilePreflight(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});

test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    const allowedSql = [
        gate.READ_ONLY_BEGIN_SQL,
        gate.READ_ONLY_ROLLBACK_SQL,
        'SELECT table_name FROM information_schema.tables',
    ];

    for (const sql of allowedSql) {
        assert.doesNotThrow(() => gate.assertSelectOnlySql(sql));
    }
    for (const sql of [
        'INSERT INTO matches(match_id) VALUES ($1)',
        'UPDATE matches SET status=$1',
        'DELETE FROM matches',
        'CREATE TABLE unsafe(id int)',
        'ALTER TABLE matches ADD COLUMN unsafe text',
        'DROP TABLE matches',
        'TRUNCATE matches',
        'COPY matches TO STDOUT',
        '\\copy matches to file',
        'COMMIT',
    ]) {
        assert.throws(() => gate.assertSelectOnlySql(sql), /Unsafe SQL rejected/);
    }
});

test('CLI --help、等号参数、未知参数和 runtime error 分支可用', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    let helpStdout = '';
    const helpStatus = await gate.main(['--help'], {
        stdout: text => {
            helpStdout += text;
        },
        stderr: () => {},
    });
    const equalsResult = await runJsonMain(gate, [
        `--source-manifest=${MANIFEST_PATH}`,
        `--local-csv=${CSV_PATH}`,
        `--approval-form=${APPROVAL_FORM_PATH}`,
        `--runbook-template=${RUNBOOK_TEMPLATE_PATH}`,
    ]);
    const unknownResult = await runJsonMain(gate, ['--unknown']);
    const runtimeResult = await runJsonMain(
        gate,
        [
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        {
            ...buildDependencies(),
            runPacketAssembly: async () => {
                throw new Error('synthetic packet preview failure');
            },
        }
    );

    assert.equal(helpStatus, 0);
    assert.match(helpStdout, /Usage:/);
    assert.equal(equalsResult.status, 0);
    assert.equal(equalsResult.payload.ok, true);
    assert.equal(unknownResult.status, 1);
    assert.equal(unknownResult.payload.mode, 'runtime-error');
    assert.match(unknownResult.payload.errors.join('\n'), /Unknown argument: --unknown/);
    assert.equal(runtimeResult.status, 1);
    assert.equal(runtimeResult.payload.mode, 'runtime-error');
    assert.match(runtimeResult.payload.errors.join('\n'), /synthetic packet preview failure/);
});

test('text output 包含 required summary 字段', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();
    let stdout = '';
    const status = await gate.main(
        [
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        {
            stdout: text => {
                stdout += text;
            },
            stderr: () => {},
        },
        buildDependencies()
    );

    assert.equal(status, 0);
    assert.match(stdout, /phase=PHASE4\.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT/);
    assert.match(stdout, /packet_file_generation_allowed=false/);
    assert.match(stdout, /future_packet_directory_preview=docs\/_packets\/football_data\/small_write\//);
    assert.match(stdout, /future_packet_file_preview=football_data_small_write_packet_/);
    assert.match(stdout, /future_packet_manifest_preview=football_data_small_write_packet_manifest_/);
    assert.match(stdout, /approval_status=not_approved/);
});

test('helper functions 覆盖空路径、fallback slug/hash 和 failure text 分支', t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();

    assert.equal(
        gate.buildFuturePacketPreviews(
            baseArgs(),
            buildPacketPayload({
                source_manifest_summary: {},
                local_csv_summary: {},
                csv_dry_run_summary: {},
            })
        ).future_packet_file_preview,
        'football_data_small_write_packet_football_data_sample_phase463c_manifest_preview0.json'
    );

    const metadata = gate.buildFuturePacketMetadata(
        baseArgs({ sourceManifest: '', localCsv: '', approvalForm: '', runbookTemplate: '' }),
        buildPacketPayload({ current_db_counts: null }),
        {
            sourceSlug: 'source',
            sourceHash8: 'preview0',
            future_packet_directory_preview: 'docs/_packets/football_data/small_write/<timestamp>_source/',
            future_packet_file_preview: 'football_data_small_write_packet_source_preview0.json',
            future_packet_manifest_preview: 'football_data_small_write_packet_manifest_source_preview0.json',
        },
        PROJECT_ROOT
    );

    assert.equal(metadata.packet_version, 'PHASE4.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT');
    assert.equal(metadata.source_manifest_path, null);
    assert.equal(metadata.local_csv_path, null);
    assert.equal(metadata.approval_form_path, null);
    assert.equal(metadata.runbook_template_path, null);
    assert.equal(metadata.source_sha256, 'abcdef1234567890fedcba0987654321abcdef1234567890fedcba0987654321');
    assert.equal(metadata.row_count, 3);
    assert.deepEqual(metadata.proposed_match_ids, ['fd_alpha_11111111', 'fd_beta_22222222']);
    assert.equal(metadata.insert_candidate_count, 1);
    assert.equal(metadata.blocked_candidate_count, 1);
    assert.equal(metadata.manual_review_count, 0);
    assert.equal(metadata.db_counts_before_preview, null);
    assert.match(metadata.pg_dump_command_preview, /pg_dump/);
    assert.deepEqual(metadata.post_write_validation_checklist, ['compare before/after row counts']);
    assert.deepEqual(metadata.rollback_restore_preview, ['restore is not executed automatically']);
    assert.equal(metadata.generated_at_preview_only, '<generated_at_preview_only>');
    assert.equal(metadata.generated_by_preview_only, '<generated_by_preview_only>');

    const failureText = gate.payloadToText({
        ...buildPacketPayload(),
        phase: 'PHASE4.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT',
        mode: 'blocked-commit',
        ok: false,
        packet_preview_passed: false,
        approval_form_validation_passed: false,
        packet_file_generation_allowed: false,
        packet_write_allowed: false,
        would_create_packet_directory: false,
        would_write_packet_file: false,
        would_write_packet_manifest: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        blocked_reason: 'synthetic blocked reason',
        errors: ['synthetic error'],
        warnings: ['synthetic warning'],
        current_db_counts: null,
        future_packet_directory_preview: null,
        future_packet_file_preview: null,
        future_packet_manifest_preview: null,
        future_packet_metadata: {},
        packet_sections_missing: [],
        non_execution_confirmations: gate.buildNonExecutionConfirmations(),
        future_real_packet_file_requirements: gate.buildFutureRealPacketFileRequirements(),
        approval_granted: false,
    });

    assert.match(failureText, /blocked_reason=synthetic blocked reason/);
    assert.match(failureText, /errors=synthetic error/);
    assert.match(failureText, /warnings=\["synthetic warning"\]/);
});

test('helper functions 覆盖 source slug / sha / row_count fallback 和默认失败信息', async t => {
    installExecutionGuards(t);
    const gate = loadPreflightFresh();

    const previewFromSourceType = gate.buildFuturePacketPreviews(
        baseArgs({ sourceManifest: '???.json' }),
        buildPacketPayload({
            source_manifest_summary: { source_type: 'Áccented Type' },
            csv_dry_run_summary: {},
            local_csv_summary: { actual_sha256: '', expected_sha256: 'AB-CD' },
        })
    );
    assert.equal(previewFromSourceType.sourceSlug, 'accented_type');
    assert.equal(previewFromSourceType.sourceHash8, 'abcdprev');

    const previewFromEmptyFallback = gate.buildFuturePacketPreviews(
        baseArgs({ sourceManifest: '' }),
        buildPacketPayload({
            source_manifest_summary: {},
            csv_dry_run_summary: { source_name: '' },
            local_csv_summary: { actual_sha256: '', expected_sha256: '' },
        })
    );
    assert.equal(previewFromEmptyFallback.sourceSlug, 'source');
    assert.equal(previewFromEmptyFallback.sourceHash8, 'preview0');

    const metadataFromExpectedRowCount = gate.buildFuturePacketMetadata(
        baseArgs({
            sourceManifest: PROJECT_ROOT,
            localCsv: PROJECT_ROOT,
            approvalForm: PROJECT_ROOT,
            runbookTemplate: PROJECT_ROOT,
        }),
        buildPacketPayload({
            source_manifest_summary: {},
            local_csv_summary: {
                actual_sha256: '',
                expected_sha256: '',
                actual_row_count: undefined,
                expected_row_count: 9,
            },
            proposed_match_ids: null,
            insert_candidate_table: null,
            blocked_candidate_table: null,
            manual_review_table: null,
            current_db_counts: undefined,
            pg_dump_command_preview: '',
            post_write_validation_checklist: null,
            rollback_restore_preview: null,
        }),
        previewFromEmptyFallback,
        PROJECT_ROOT
    );
    assert.equal(metadataFromExpectedRowCount.source_manifest_path, '.');
    assert.equal(metadataFromExpectedRowCount.local_csv_path, '.');
    assert.equal(metadataFromExpectedRowCount.approval_form_path, '.');
    assert.equal(metadataFromExpectedRowCount.runbook_template_path, '.');
    assert.equal(metadataFromExpectedRowCount.source_sha256, null);
    assert.equal(metadataFromExpectedRowCount.row_count, 9);
    assert.deepEqual(metadataFromExpectedRowCount.proposed_match_ids, []);
    assert.equal(metadataFromExpectedRowCount.insert_candidate_count, 0);
    assert.equal(metadataFromExpectedRowCount.blocked_candidate_count, 0);
    assert.equal(metadataFromExpectedRowCount.manual_review_count, 0);
    assert.equal(metadataFromExpectedRowCount.db_counts_before_preview, null);
    assert.equal(metadataFromExpectedRowCount.pg_dump_command_preview, null);
    assert.deepEqual(metadataFromExpectedRowCount.post_write_validation_checklist, []);
    assert.deepEqual(metadataFromExpectedRowCount.rollback_restore_preview, []);

    const metadataFromSourceRowCount = gate.buildFuturePacketMetadata(
        baseArgs(),
        buildPacketPayload({
            source_manifest_summary: { row_count: 12 },
            local_csv_summary: {
                actual_sha256: '',
                expected_sha256: '',
                actual_row_count: undefined,
                expected_row_count: undefined,
            },
        }),
        previewFromEmptyFallback,
        PROJECT_ROOT
    );
    assert.equal(metadataFromSourceRowCount.row_count, 12);

    const failurePayload = await gate.runPacketFilePreflight(
        baseArgs(),
        buildDependencies({
            runPacketAssembly: async () => ({
                ok: false,
                source_manifest_found: true,
                local_csv_found: true,
                approval_form_found: true,
                runbook_template_found: true,
            }),
        })
    );
    assert.equal(failurePayload.ok, false);
    assert.equal(failurePayload.mode, 'packet-preview-failed');
    assert.deepEqual(failurePayload.errors, ['football-data packet preview failed']);
    assert.deepEqual(failurePayload.warnings, []);
    assert.equal(failurePayload.packet_preview_failure_mode, null);
});

test('script 作为真实入口执行 --help 应成功', () => {
    const result = spawnSync(process.execPath, [SCRIPT_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Phase 4\.70C previews future packet file generation only/);
});
