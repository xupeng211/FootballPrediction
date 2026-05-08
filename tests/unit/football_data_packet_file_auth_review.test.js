'use strict';
/* eslint-disable max-lines -- Phase 4.72C keeps the auth review safety contract in one focused test file. */

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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_auth_review.js');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
);
const CSV_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');
const AUTH_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md'
);
const APPROVAL_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md'
);
const RUNBOOK_TEMPLATE_PATH = path.join(PROJECT_ROOT, 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md');

const AUTH_FORM_TEXT = fs.readFileSync(AUTH_FORM_PATH, 'utf8');
const SOURCE_MANIFEST_TEXT = fs.readFileSync(MANIFEST_PATH, 'utf8');
const LOCAL_CSV_TEXT = fs.readFileSync(CSV_PATH, 'utf8');
const APPROVAL_FORM_TEXT = fs.readFileSync(APPROVAL_FORM_PATH, 'utf8');
const RUNBOOK_TEMPLATE_TEXT = fs.readFileSync(RUNBOOK_TEMPLATE_PATH, 'utf8');

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
        throw new Error(`${name} should not be called by football_data_packet_file_auth_review`);
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

function loadReviewFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function baseArgs(overrides = {}) {
    return {
        authForm: AUTH_FORM_PATH,
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
        approvalForm: APPROVAL_FORM_PATH,
        runbookTemplate: RUNBOOK_TEMPLATE_PATH,
        ...overrides,
    };
}

function buildAuthValidationPayload(overrides = {}) {
    return {
        ok: true,
        authorization_status: 'not_authorized',
        final_packet_creation_confirmation: false,
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildPacketPreviewPayload(overrides = {}) {
    return {
        phase: 'PHASE4.69C_FOOTBALL_DATA_SMALL_WRITE_PACKET_ASSEMBLY',
        mode: 'football-data-small-write-packet-assembly',
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_form_found: true,
        runbook_template_found: true,
        approval_form_validation_passed: true,
        select_only_db_reads: true,
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
        proposed_match_ids: ['fd_alpha_11111111', 'fd_beta_22222222'],
        insert_candidate_table: [{ proposed_match_id: 'fd_alpha_11111111' }, { proposed_match_id: 'fd_beta_22222222' }],
        blocked_candidate_table: [],
        manual_review_table: [{ proposed_match_id: 'fd_manual_33333333' }],
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

function buildPacketFilePreflightPayload(overrides = {}) {
    return {
        phase: 'PHASE4.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT',
        mode: 'football-data-packet-file-preflight',
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_form_found: true,
        runbook_template_found: true,
        packet_preview_passed: true,
        approval_form_validation_passed: true,
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

function buildDbClient(rows = []) {
    const calls = [];
    return {
        calls,
        releaseCalled: false,
        async query(sql) {
            calls.push(sql);
            return { rows };
        },
        release() {
            this.releaseCalled = true;
        },
    };
}

function buildDependencies(overrides = {}) {
    const dbClient =
        overrides.dbClient ||
        buildDbClient([
            { table_name: 'matches', rows: '2' },
            { table_name: 'bookmaker_odds_history', rows: '2' },
            { table_name: 'raw_match_data', rows: '2' },
            { table_name: 'l3_features', rows: '2' },
            { table_name: 'match_features_training', rows: '2' },
            { table_name: 'predictions', rows: '2' },
        ]);

    return {
        cwd: PROJECT_ROOT,
        existsSync: filePath =>
            new Set([AUTH_FORM_PATH, MANIFEST_PATH, CSV_PATH, APPROVAL_FORM_PATH, RUNBOOK_TEMPLATE_PATH]).has(
                path.resolve(filePath)
            ),
        readFileSync: filePath => {
            const resolved = path.resolve(filePath);
            if (resolved === AUTH_FORM_PATH) {
                return AUTH_FORM_TEXT;
            }
            if (resolved === MANIFEST_PATH) {
                return SOURCE_MANIFEST_TEXT;
            }
            if (resolved === CSV_PATH) {
                return LOCAL_CSV_TEXT;
            }
            if (resolved === APPROVAL_FORM_PATH) {
                return APPROVAL_FORM_TEXT;
            }
            if (resolved === RUNBOOK_TEMPLATE_PATH) {
                return RUNBOOK_TEMPLATE_TEXT;
            }
            throw new Error(`unexpected readFileSync path: ${resolved}`);
        },
        runAuthValidation: () => buildAuthValidationPayload(),
        runPacketAssembly: async () => buildPacketPreviewPayload(),
        runPacketFilePreflight: async () => buildPacketFilePreflightPayload(),
        dbClient,
        ...overrides,
    };
}

async function runMain(gate, argv, dependencies = buildDependencies()) {
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
    return { status, stdout, stderr };
}

async function runJsonMain(gate, argv, dependencies = buildDependencies()) {
    const result = await runMain(gate, [...argv, '--json'], dependencies);
    return {
        ...result,
        payload: JSON.parse(result.stdout),
    };
}

function assertReviewSafetyPayload(payload) {
    assert.equal(payload.authorization_review_completed, true);
    assert.equal(payload.packet_file_creation_ready, false);
    assert.equal(payload.packet_file_creation_authorized, false);
    assert.equal(payload.authorization_status, 'not_authorized');
    assert.equal(payload.final_packet_creation_confirmation, false);
    assert.equal(payload.approval_granted, false);
    assert.equal(payload.would_create_packet_directory, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_packet_manifest, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
}

test('缺 auth form 参数时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
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
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /provide --auth-form=<path>/);
});

test('缺 source manifest 参数时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /provide --auth-form=<path>.*--source-manifest=<path>/);
});

test('缺 local CSV 参数时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /--local-csv=<path>/);
});

test('缺 approval form 参数时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /--approval-form=<path>/);
});

test('缺 runbook template 参数时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /--runbook-template=<path>/);
});

test('CLI --help 输出 usage，未知参数进入 runtime-error', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();

    const helpResult = await runMain(gate, ['--help'], buildDependencies());
    assert.equal(helpResult.status, 0);
    assert.match(helpResult.stdout, /Usage:/);
    assert.match(helpResult.stdout, /dry-run authorization review only/);

    const badArgResult = await runJsonMain(gate, ['--unknown'], buildDependencies());
    assert.equal(badArgResult.status, 1);
    assert.equal(badArgResult.payload.mode, 'runtime-error');
    assert.match(badArgResult.payload.errors.join('\n'), /Unknown argument: --unknown/);
});

test('正确 template review 成功', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 0);
    assert.equal(result.payload.ok, true);
    assert.equal(result.payload.auth_form_found, true);
    assert.equal(result.payload.source_manifest_found, true);
    assert.equal(result.payload.local_csv_found, true);
    assert.equal(result.payload.approval_form_found, true);
    assert.equal(result.payload.runbook_template_found, true);
    assert.equal(result.payload.auth_form_validation_passed, true);
    assert.equal(result.payload.packet_file_preflight_passed, true);
    assert.equal(result.payload.packet_preview_passed, true);
    assert.equal(result.payload.select_only_db_reads, true);
    assertReviewSafetyPayload(result.payload);
});

test('输出包含 ready=false / authorized=false / no-write flags', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.status, 0);
    assert.match(result.stdout, /authorization_review_completed=true/);
    assert.match(result.stdout, /packet_file_creation_ready=false/);
    assert.match(result.stdout, /packet_file_creation_authorized=false/);
    assert.match(result.stdout, /authorization_status=not_authorized/);
    assert.match(result.stdout, /final_packet_creation_confirmation=false/);
    assert.match(result.stdout, /approval_granted=false/);
    assert.match(result.stdout, /would_create_packet_directory=false/);
    assert.match(result.stdout, /would_write_packet_file=false/);
    assert.match(result.stdout, /would_write_packet_manifest=false/);
    assert.match(result.stdout, /would_write_db=false/);
});

test('missing_authorization_requirements 包含必要字段', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.deepEqual(result.payload.missing_authorization_requirements, [
        'authorization_status must be authorized_for_packet_file_creation',
        'final_packet_creation_confirmation must be true',
        'operator must be filled',
        'reviewer must be filled',
        'packet_directory must be explicit',
        'packet_file must be explicit',
        'packet_manifest_file must be explicit',
        'source_manifest must match reviewed source',
        'local_csv must match reviewed CSV',
        'approved_candidate_match_ids must be reviewed',
        'manual_review_candidate_match_ids must be excluded or resolved',
        'human_approval_note must be present',
    ]);
});

test('permission_separation 包含 DB write / pg_dump / training / prediction 分离', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.deepEqual(result.payload.permission_separation, [
        'packet file creation does not authorize DB write',
        'packet file creation does not authorize pg_dump',
        'packet file creation does not authorize pg_restore',
        'packet file creation does not authorize training',
        'packet file creation does not authorize prediction',
    ]);
});

test('human_only_fields 包含 authorization_status / final_packet_creation_confirmation', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.human_only_fields.includes('authorization_status'));
    assert.ok(result.payload.human_only_fields.includes('final_packet_creation_confirmation'));
    assert.ok(result.payload.human_only_fields.includes('human_approval_note'));
});

test('authorized-looking form 也不能在 Phase 4.72C 执行写动作', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const fakeAuthorizedForm = AUTH_FORM_TEXT.replace(
        'authorization_status: not_authorized',
        'authorization_status: authorized_for_packet_file_creation'
    )
        .replace('final_packet_creation_confirmation: false', 'final_packet_creation_confirmation: true')
        .replace('operator:', 'operator: Alice')
        .replace('reviewer:', 'reviewer: Bob')
        .replace('packet_directory:', 'packet_directory: docs/_packets/football_data/small_write/20260509_fixture')
        .replace('packet_file:', 'packet_file: football_data_small_write_packet_fixture_preview.json')
        .replace(
            'packet_manifest_file:',
            'packet_manifest_file: football_data_small_write_packet_manifest_fixture_preview.json'
        )
        .replace(
            'source_manifest:',
            'source_manifest: tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json'
        )
        .replace('local_csv:', 'local_csv: tests/fixtures/football_data/football_data_sample_phase462c.csv')
        .replace(
            'approved_candidate_match_ids: []',
            'approved_candidate_match_ids:\n  - fd_alpha_11111111\n  - fd_beta_22222222'
        )
        .replace('manual_review_candidate_match_ids: []', 'manual_review_candidate_match_ids:\n  - fd_manual_33333333')
        .replace('packet_creation_reason:', 'packet_creation_reason: human reviewed')
        .replace('human_approval_note:', 'human_approval_note: reviewed manually');

    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            readFileSync: filePath => {
                const resolved = path.resolve(filePath);
                if (resolved === AUTH_FORM_PATH) {
                    return fakeAuthorizedForm;
                }
                if (resolved === MANIFEST_PATH) {
                    return SOURCE_MANIFEST_TEXT;
                }
                if (resolved === CSV_PATH) {
                    return LOCAL_CSV_TEXT;
                }
                if (resolved === APPROVAL_FORM_PATH) {
                    return APPROVAL_FORM_TEXT;
                }
                if (resolved === RUNBOOK_TEMPLATE_PATH) {
                    return RUNBOOK_TEMPLATE_TEXT;
                }
                throw new Error(`unexpected read path: ${resolved}`);
            },
        })
    );

    assert.equal(result.status, 0);
    assert.equal(result.payload.packet_file_creation_ready, false);
    assert.equal(result.payload.packet_file_creation_authorized, false);
    assert.equal(result.payload.approval_granted, false);
    assert.equal(result.payload.would_write_db, false);
    assert.equal(result.payload.would_write_packet_file, false);
    assert.equal(result.payload.would_create_packet_directory, false);
});

test('路径不存在时分别返回 manifest / csv / approval / runbook 错误', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();

    const missingManifest = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            existsSync: filePath => path.resolve(filePath) !== MANIFEST_PATH,
        })
    );
    assert.equal(missingManifest.status, 1);
    assert.equal(missingManifest.payload.mode, 'manifest-error');

    const missingCsv = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            existsSync: filePath => path.resolve(filePath) !== CSV_PATH,
        })
    );
    assert.equal(missingCsv.status, 1);
    assert.equal(missingCsv.payload.mode, 'csv-error');

    const missingApproval = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            existsSync: filePath => path.resolve(filePath) !== APPROVAL_FORM_PATH,
        })
    );
    assert.equal(missingApproval.status, 1);
    assert.equal(missingApproval.payload.mode, 'approval-form-error');

    const missingRunbook = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            existsSync: filePath => path.resolve(filePath) !== RUNBOOK_TEMPLATE_PATH,
        })
    );
    assert.equal(missingRunbook.status, 1);
    assert.equal(missingRunbook.payload.mode, 'runbook-template-error');
});

test('auth form 文件不存在时返回 auth-form-error', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            existsSync: filePath => path.resolve(filePath) !== AUTH_FORM_PATH,
        })
    );

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'auth-form-error');
    assert.match(result.payload.errors.join('\n'), /auth form not found/);
});

test('commit blocked', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
            '--commit',
        ],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /review commit is not wired in Phase 4\.72C/);
});

test('packet file preflight 失败时返回 packet-file-preflight-failed', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const dbClient = buildDbClient();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            dbClient,
            runPacketFilePreflight: async () => ({
                ok: false,
                errors: ['packet file preflight failed'],
                warnings: ['preview warning'],
            }),
        })
    );

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'packet-file-preflight-failed');
    assert.match(result.payload.errors.join('\n'), /packet file preflight failed/);
    assert.deepEqual(dbClient.calls, []);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const dbClient = buildDbClient();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            dbClient,
            runPacketAssembly: async () =>
                buildPacketPreviewPayload({
                    ok: false,
                    errors: ['sha256 mismatch between source manifest and local CSV'],
                    warnings: [],
                }),
        })
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /sha256 mismatch/);
    assert.deepEqual(dbClient.calls, []);
});

test('approval form invalid 时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            runPacketAssembly: async () => ({
                ok: false,
                errors: ['approval form validation failed'],
                warnings: [],
            }),
        })
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /approval form validation failed/);
});

test('auth form invalid 时失败', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            runAuthValidation: () => ({
                ok: false,
                errors: ['authorization_status must remain not_authorized in the Phase 4.71C template'],
                warnings: [],
            }),
        })
    );

    assert.equal(result.status, 1);
    assert.match(result.payload.errors.join('\n'), /authorization_status must remain not_authorized/);
});

test('auth form 缺少 YAML block 时进入 runtime-error', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            runAuthValidation: () => buildAuthValidationPayload(),
            readFileSync: filePath => {
                const resolved = path.resolve(filePath);
                if (resolved === AUTH_FORM_PATH) {
                    return '# no yaml block here';
                }
                if (resolved === MANIFEST_PATH) {
                    return SOURCE_MANIFEST_TEXT;
                }
                if (resolved === CSV_PATH) {
                    return LOCAL_CSV_TEXT;
                }
                if (resolved === APPROVAL_FORM_PATH) {
                    return APPROVAL_FORM_TEXT;
                }
                if (resolved === RUNBOOK_TEMPLATE_PATH) {
                    return RUNBOOK_TEMPLATE_TEXT;
                }
                throw new Error(`unexpected read path: ${resolved}`);
            },
        })
    );

    assert.equal(result.status, 1);
    assert.equal(result.payload.mode, 'runtime-error');
    assert.match(result.payload.errors.join('\n'), /YAML fenced block not found in packet file authorization form/);
});

test('不访问外网', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_external_network'));
    assert.equal(result.payload.would_access_network, false);
});

test('不写文件', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_file_writes'));
    assert.equal(result.payload.would_write_files, false);
});

test('不创建目录', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_packet_directory_create'));
    assert.equal(result.payload.would_create_packet_directory, false);
});

test('不写 packet 文件', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_packet_file_write'));
    assert.equal(result.payload.would_write_packet_file, false);
});

test('不执行 pg_dump', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_pg_dump_execution'));
    assert.equal(result.payload.would_execute_pg_dump, false);
});

test('不执行 pg_restore', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.ok(result.payload.non_execution_confirmations.includes('no_pg_restore_execution'));
    assert.equal(result.payload.would_execute_pg_restore, false);
});

test('不 spawn child process', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies()
    );

    assert.equal(result.payload.would_spawn_child_process, false);
});

test('reviewCurrentDbCounts 支持 injected pool，并在 createPool 模式下关闭新建 pool', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();

    const pooledClient = buildDbClient([
        { table_name: 'matches', rows: '2' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '2' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ]);
    const injectedPool = {
        ended: false,
        async connect() {
            return pooledClient;
        },
        async end() {
            this.ended = true;
        },
    };

    const pooledState = await gate.reviewCurrentDbCounts({ pool: injectedPool });
    assert.equal(pooledState.current_db_counts.matches, 2);
    assert.equal(injectedPool.ended, false);
    assert.equal(pooledClient.releaseCalled, true);

    const createdClient = buildDbClient([
        { table_name: 'matches', rows: '2' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '2' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ]);
    const createdPool = {
        ended: false,
        async connect() {
            return createdClient;
        },
        async end() {
            this.ended = true;
        },
    };

    const createdState = await gate.reviewCurrentDbCounts({
        createPool: () => createdPool,
    });
    assert.equal(createdState.current_db_counts.predictions, 2);
    assert.equal(createdPool.ended, true);
    assert.equal(createdClient.releaseCalled, true);
});

test('reviewCurrentDbCounts 默认 createPool 分支可通过 pg mock 覆盖', async t => {
    const originalLoad = Module._load;
    const fakeClient = buildDbClient([
        { table_name: 'matches', rows: '2' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '2' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ]);
    const fakePool = {
        ended: false,
        async connect() {
            return fakeClient;
        },
        async end() {
            this.ended = true;
        },
    };

    Module._load = function patchedLoad(request, parent, isMain) {
        if (request === 'pg' || request === 'node:pg') {
            return {
                Pool: class Pool {
                    constructor() {
                        return fakePool;
                    }
                },
            };
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        Module._load = originalLoad;
    });

    const gate = loadReviewFresh();
    const state = await gate.reviewCurrentDbCounts({});

    assert.equal(state.current_db_counts.matches, 2);
    assert.equal(fakePool.ended, true);
    assert.equal(fakeClient.releaseCalled, true);
});

test('text output 包含 blocked_reason / errors / warnings', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();

    const blockedResult = await runMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
            '--commit',
        ],
        buildDependencies()
    );
    assert.equal(blockedResult.status, 1);
    assert.match(blockedResult.stdout, /blocked_reason=BLOCKED:/);
    assert.match(blockedResult.stdout, /errors=BLOCKED:/);

    const warningResult = await runMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({
            runPacketFilePreflight: async () => ({
                ok: false,
                errors: ['packet file preflight failed'],
                warnings: ['warning text'],
            }),
        })
    );
    assert.equal(warningResult.status, 1);
    assert.match(warningResult.stdout, /errors=packet file preflight failed/);
    assert.match(warningResult.stdout, /warnings=\["warning text"\]/);
});

test('source/local 绝对路径匹配时不应再报告 reviewed source/csv 缺失', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const authFormData = {
        authorization_status: 'not_authorized',
        final_packet_creation_confirmation: false,
        operator: '',
        reviewer: '',
        packet_directory: '',
        packet_file: '',
        packet_manifest_file: '',
        source_manifest: MANIFEST_PATH,
        local_csv: CSV_PATH,
        approved_candidate_match_ids: [],
        excluded_candidate_match_ids: ['fd_manual_33333333'],
        manual_review_candidate_match_ids: ['fd_manual_33333333'],
        human_approval_note: '',
    };
    const missing = gate.buildMissingAuthorizationRequirements(authFormData, {
        cwd: PROJECT_ROOT,
        pathContext: {
            sourceManifestPath: MANIFEST_PATH,
            localCsvPath: CSV_PATH,
        },
        packetPreviewPayload: buildPacketPreviewPayload(),
    });

    assert.equal(missing.includes('source_manifest must match reviewed source'), false);
    assert.equal(missing.includes('local_csv must match reviewed CSV'), false);
});

test('路径 helper 应覆盖空路径、绝对路径与当前目录回退', () => {
    const gate = loadReviewFresh();

    assert.equal(gate.resolveLocalPath('', PROJECT_ROOT), '');
    assert.equal(gate.toRelativePath('', PROJECT_ROOT), '');
    assert.equal(gate.toRelativePath(PROJECT_ROOT, PROJECT_ROOT), '.');

    const absoluteFixturePath = path.resolve(MANIFEST_PATH);
    assert.equal(gate.resolveLocalPath(absoluteFixturePath, PROJECT_ROOT), absoluteFixturePath);
});

test('payloadToText 应覆盖 current_db_counts 和列表输出分支', () => {
    const gate = loadReviewFresh();
    const text = gate.payloadToText({
        phase: gate.PACKET_FILE_AUTH_REVIEW_PHASE,
        mode: 'football-data-packet-file-auth-review',
        ok: true,
        auth_form_found: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_form_found: true,
        runbook_template_found: true,
        auth_form_validation_passed: true,
        packet_file_preflight_passed: true,
        packet_preview_passed: true,
        select_only_db_reads: true,
        authorization_review_completed: true,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        authorization_status: 'not_authorized',
        final_packet_creation_confirmation: false,
        approval_granted: false,
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
        commit_gate: 'blocked',
        current_db_counts: {
            matches: 2,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        missing_authorization_requirements: ['operator must be filled'],
        permission_separation: ['packet file creation does not authorize DB write'],
        human_only_fields: ['authorization_status'],
        non_execution_confirmations: ['no_external_network'],
        errors: [],
        warnings: [],
    });

    assert.match(text, /current_db_counts:/);
    assert.match(text, /- matches=2/);
    assert.match(text, /missing_authorization_requirements:/);
    assert.match(text, /- operator must be filled/);
    assert.match(text, /permission_separation:/);
    assert.match(text, /human_only_fields:/);
    assert.match(text, /non_execution_confirmations:/);
});

test('默认 stage 回退路径在未注入 override 时仍可成功', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const result = await gate.runAuthorizationReview(baseArgs(), {
        cwd: PROJECT_ROOT,
        existsSync: filePath =>
            new Set([AUTH_FORM_PATH, MANIFEST_PATH, CSV_PATH, APPROVAL_FORM_PATH, RUNBOOK_TEMPLATE_PATH]).has(
                path.resolve(filePath)
            ),
        readFileSync: filePath => {
            const resolved = path.resolve(filePath);
            if (resolved === AUTH_FORM_PATH) {
                return AUTH_FORM_TEXT;
            }
            if (resolved === MANIFEST_PATH) {
                return SOURCE_MANIFEST_TEXT;
            }
            if (resolved === CSV_PATH) {
                return LOCAL_CSV_TEXT;
            }
            if (resolved === APPROVAL_FORM_PATH) {
                return APPROVAL_FORM_TEXT;
            }
            if (resolved === RUNBOOK_TEMPLATE_PATH) {
                return RUNBOOK_TEMPLATE_TEXT;
            }
            throw new Error(`unexpected read path: ${resolved}`);
        },
        dbClient: buildDbClient([
            { table_name: 'matches', rows: '2' },
            { table_name: 'bookmaker_odds_history', rows: '2' },
            { table_name: 'raw_match_data', rows: '2' },
            { table_name: 'l3_features', rows: '2' },
            { table_name: 'match_features_training', rows: '2' },
            { table_name: 'predictions', rows: '2' },
        ]),
    });

    assert.equal(result.ok, true);
    assert.equal(result.packet_file_creation_ready, false);
    assert.equal(result.packet_file_creation_authorized, false);
    assert.equal(result.commit_gate, 'blocked');
});

test('script 作为真实入口执行 --help 应成功', () => {
    const result = spawnSync('node', [SCRIPT_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Usage:/);
    assert.match(result.stdout, /No packet file writes, no packet directory creation/);
});

test('main runtime error 分支应返回 runtime-error payload', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    let stdout = '';
    const status = await gate.main(
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
            '--json',
        ],
        {
            stdout: text => {
                stdout += text;
            },
        },
        {
            ...buildDependencies(),
            runPacketAssembly: async () => {
                throw new Error('forced runtime failure');
            },
        }
    );

    const payload = JSON.parse(stdout);
    assert.equal(status, 1);
    assert.equal(payload.mode, 'runtime-error');
    assert.match(payload.errors.join('\n'), /forced runtime failure/);
});

test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', async t => {
    installExecutionGuards(t);
    const gate = loadReviewFresh();
    const dbClient = buildDbClient([
        { table_name: 'matches', rows: '2' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '2' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ]);

    const result = await runJsonMain(
        gate,
        [
            '--auth-form',
            AUTH_FORM_PATH,
            '--source-manifest',
            MANIFEST_PATH,
            '--local-csv',
            CSV_PATH,
            '--approval-form',
            APPROVAL_FORM_PATH,
            '--runbook-template',
            RUNBOOK_TEMPLATE_PATH,
        ],
        buildDependencies({ dbClient })
    );

    assert.equal(result.status, 0);
    assert.ok(dbClient.calls.length >= 3);
    for (const sql of dbClient.calls) {
        const normalized = String(sql || '')
            .replace(/\s+/g, ' ')
            .trim()
            .toUpperCase();
        const allowed =
            normalized === gate.READ_ONLY_BEGIN_SQL ||
            normalized === gate.READ_ONLY_ROLLBACK_SQL ||
            normalized.startsWith('SELECT ');
        const forbidden =
            /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|MERGE|GRANT|REVOKE|COMMIT)\b|\\COPY/.test(
                normalized
            );
        assert.equal(allowed, true, `unexpected SQL: ${normalized}`);
        assert.equal(forbidden, false, `forbidden SQL: ${normalized}`);
    }
});
