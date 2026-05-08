'use strict';
/* eslint-disable max-lines -- Phase 4.69C keeps the packet assembly safety contract in one test file. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_packet_assembly.js');
const DRY_RUN_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
const PREFLIGHT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_db_write_preflight.js');
const DUPLICATE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_duplicate_precheck.js');
const INSERT_POLICY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_insert_policy_precheck.js');
const AUTH_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_auth_preview.js');
const RUNBOOK_VALIDATE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_runbook_validate.js');
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

const APPROVAL_FORM_TEXT = fs.readFileSync(APPROVAL_FORM_PATH, 'utf8');
const RUNBOOK_TEMPLATE_TEXT = fs.readFileSync(RUNBOOK_TEMPLATE_PATH, 'utf8');
const MANIFEST_TEXT = fs.readFileSync(MANIFEST_PATH, 'utf8');

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
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_small_write_packet_assembly`);
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
        Module._load = originalLoad;
    });
}

function loadPacketFresh() {
    for (const modulePath of [
        SCRIPT_PATH,
        DRY_RUN_PATH,
        PREFLIGHT_PATH,
        DUPLICATE_PATH,
        INSERT_POLICY_PATH,
        AUTH_PATH,
        RUNBOOK_VALIDATE_PATH,
    ]) {
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

function createReadFileSync(overrides = {}) {
    return filePath => {
        const normalized = path.resolve(String(filePath));
        if (Object.prototype.hasOwnProperty.call(overrides, normalized)) {
            return overrides[normalized];
        }
        if (normalized === APPROVAL_FORM_PATH) {
            return APPROVAL_FORM_TEXT;
        }
        if (normalized === RUNBOOK_TEMPLATE_PATH) {
            return RUNBOOK_TEMPLATE_TEXT;
        }
        if (normalized === MANIFEST_PATH) {
            return MANIFEST_TEXT;
        }
        return fs.readFileSync(normalized, 'utf8');
    };
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
        source_name: 'football_data_local_synthetic_fixture',
        source_type: 'local_csv_fixture',
        approval_status: 'dry_run_only',
        dry_run_version: 'PHASE4.63C_FOOTBALL_DATA_ADAPTER_DRY_RUN',
        parser_version: 'PHASE4.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER',
        expected_sha256: 'expected-sha',
        actual_sha256: 'expected-sha',
        sha256_match: true,
        expected_row_count: 3,
        actual_row_count: 3,
        row_count_match: true,
        total_rows: 3,
        parsed_rows: 3,
        candidate_rows: [
            {
                row_number: 1,
                home_team: 'Alpha Home',
                away_team: 'Beta Away',
                match_date: '2024-08-17',
                actual_result: 'home_win',
            },
            {
                row_number: 2,
                home_team: 'Gamma Home',
                away_team: 'Delta Away',
                match_date: '2024-08-18',
                actual_result: 'draw',
            },
            {
                row_number: 3,
                home_team: 'Manual Home',
                away_team: 'Manual Away',
                match_date: '2024-08-19',
                actual_result: 'away_win',
            },
        ],
        row_classification: {
            trainable_label_rows: 3,
            odds_preview_rows: 1,
            skipped_rows: 0,
        },
        trainable_label_rows: 3,
        skipped_rows: 0,
        odds_preview_rows: 1,
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
        preflight_plan: {
            target_tables_preview: ['matches', 'bookmaker_odds_history_preview_only'],
            max_rows_preview: 3,
            match_write_policy: 'future_small_batch_only_after_backup_and_authorization',
            odds_write_policy: 'blocked_preview_only_in_phase_4_64c',
        },
        commit_gate: 'blocked',
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildDuplicatePayload(overrides = {}) {
    return {
        phase: 'PHASE4.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK',
        ok: true,
        candidate_rows: 3,
        exact_existing_matches: 0,
        reversed_team_matches: 0,
        nearby_date_matches: 0,
        invalid_candidates: 0,
        insert_risk_summary: {
            duplicate_free_candidates: 3,
        },
        commit_gate: 'blocked',
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
        match_id_strategy: 'fd_<league>_<season>_<date>_<home>_<away>_<hash8>',
        match_id_strategy_finalized: false,
        manifest_approval_status: 'dry_run_only',
        candidate_rows: 3,
        future_insert_candidates: 1,
        blocked_by_manifest_policy: 1,
        skip_existing_matches: 0,
        manual_review_required: 1,
        invalid_candidates: 0,
        candidate_previews: [
            {
                row_number: 1,
                proposed_match_id: 'fd_sp2_2024_20240817_alpha_beta_11111111',
                home_team: 'Alpha Home',
                away_team: 'Beta Away',
                match_date: '2024-08-17',
                insert_policy: 'future_insert_candidate',
                duplicate_risk: 'none',
                policy_reason: 'clean candidate',
            },
            {
                row_number: 2,
                proposed_match_id: 'fd_sp2_2024_20240818_gamma_delta_22222222',
                home_team: 'Gamma Home',
                away_team: 'Delta Away',
                match_date: '2024-08-18',
                insert_policy: 'blocked_by_manifest_policy',
                duplicate_risk: 'none',
                policy_reason: 'manifest not approved',
                skip_reason: 'manifest_not_approved_for_db_write',
            },
            {
                row_number: 3,
                proposed_match_id: 'fd_sp2_2024_20240819_manual_33333333',
                home_team: 'Manual Home',
                away_team: 'Manual Away',
                match_date: '2024-08-19',
                insert_policy: 'manual_review_required',
                duplicate_risk: 'nearby_date_possible_duplicate',
                policy_reason: 'nearby date requires review',
                review_reason: 'nearby_date_possible_duplicate',
            },
        ],
        commit_gate: 'blocked',
        non_execution_confirmations: ['select_only_db_reads', 'no_db_writes'],
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildAuthPayload(overrides = {}) {
    return {
        phase: 'PHASE4.67C_FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW',
        ok: true,
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
        },
        max_rows_preview: 3,
        target_tables_preview: ['matches', 'bookmaker_odds_history'],
        pg_dump_command_preview: 'docker compose -f docker-compose.dev.yml exec -T db pg_dump ...',
        pg_restore_command_preview: 'docker compose -f docker-compose.dev.yml exec -T db pg_restore ...',
        post_write_validation: ['compare before/after row counts', 'record backup path'],
        rollback_restore_preview: ['restore is not executed automatically'],
        small_write_authorized: false,
        db_write_allowed: false,
        commit_gate: 'blocked',
        warnings: [],
        errors: [],
        ...overrides,
    };
}

function buildDependencies(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: filePath => Boolean(filePath) && !String(filePath).includes('/missing/'),
        readFileSync: createReadFileSync(),
        runDryRun: () => buildDryRunPayload(),
        runPreflight: () => buildPreflightPayload(),
        runDuplicatePrecheck: async () => buildDuplicatePayload(),
        runInsertPolicyPrecheck: async () => buildInsertPolicyPayload(),
        runSmallWriteAuthPreview: async () => buildAuthPayload(),
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
    assert.equal(payload.packet_write_allowed, false);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.small_write_authorized, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.equal(payload.would_insert_matches, false);
    assert.equal(payload.would_insert_odds, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.approval_granted, false);
}

test('packet assembly module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();

    assert.equal(typeof gate.runPacketAssembly, 'function');
    assert.equal(typeof gate.main, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs({ sourceManifest: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /provide --source-manifest/);
});

test('缺 local CSV 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs({ localCsv: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /provide --source-manifest/);
});

test('缺 approval form 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs({ approvalForm: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /approval-form/);
});

test('缺 runbook template 失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs({ runbookTemplate: '' }), buildDependencies());

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'argument-error');
    assert.match(payload.errors.join('\n'), /runbook-template/);
});

test('路径不存在时返回对应错误且不进入 gate', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    let dryRunCalled = false;
    const payload = await gate.runPacketAssembly(
        baseArgs({ sourceManifest: path.join(PROJECT_ROOT, 'missing/source.json') }),
        buildDependencies({
            runDryRun: () => {
                dryRunCalled = true;
                return buildDryRunPayload();
            },
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.source_manifest_found, false);
    assert.equal(dryRunCalled, false);
    assert.match(payload.errors.join('\n'), /source manifest not found/);
});

test('local CSV / approval form / runbook template 路径不存在时分别失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const missingCsv = await gate.runPacketAssembly(
        baseArgs({ localCsv: path.join(PROJECT_ROOT, 'missing/local.csv') }),
        buildDependencies()
    );
    const missingApproval = await gate.runPacketAssembly(
        baseArgs({ approvalForm: path.join(PROJECT_ROOT, 'missing/approval.md') }),
        buildDependencies()
    );
    const missingRunbook = await gate.runPacketAssembly(
        baseArgs({ runbookTemplate: path.join(PROJECT_ROOT, 'missing/runbook.md') }),
        buildDependencies()
    );

    assert.equal(missingCsv.mode, 'csv-error');
    assert.equal(missingCsv.local_csv_found, false);
    assert.match(missingCsv.errors.join('\n'), /local CSV not found/);
    assert.equal(missingApproval.mode, 'approval-form-error');
    assert.equal(missingApproval.approval_form_found, false);
    assert.match(missingApproval.errors.join('\n'), /approval form not found/);
    assert.equal(missingRunbook.mode, 'runbook-template-error');
    assert.equal(missingRunbook.runbook_template_found, false);
    assert.match(missingRunbook.errors.join('\n'), /runbook template not found/);
});

test('正确输入 + mock gate 成功', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.69C_FOOTBALL_DATA_SMALL_WRITE_PACKET_ASSEMBLY');
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.approval_form_found, true);
    assert.equal(payload.runbook_template_found, true);
    assert.equal(payload.csv_dry_run_passed, true);
    assert.equal(payload.db_write_preflight_passed, true);
    assert.equal(payload.duplicate_precheck_passed, true);
    assert.equal(payload.insert_policy_precheck_passed, true);
    assert.equal(payload.small_write_auth_preview_passed, true);
    assert.equal(payload.approval_form_validation_passed, true);
    assert.equal(payload.select_only_db_reads, true);
    assertSafetyPayload(payload);
});

test('输出 safety flags 全部保持 false/blocked', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const result = await runJsonMain(gate, [
        '--source-manifest',
        MANIFEST_PATH,
        '--local-csv',
        CSV_PATH,
        '--approval-form',
        APPROVAL_FORM_PATH,
        '--runbook-template',
        RUNBOOK_TEMPLATE_PATH,
    ]);

    assert.equal(result.status, 0);
    assert.equal(result.payload.csv_dry_run_passed, true);
    assert.equal(result.payload.db_write_preflight_passed, true);
    assert.equal(result.payload.duplicate_precheck_passed, true);
    assert.equal(result.payload.insert_policy_precheck_passed, true);
    assert.equal(result.payload.small_write_auth_preview_passed, true);
    assert.equal(result.payload.approval_form_validation_passed, true);
    assert.equal(result.payload.commit_gate, 'blocked');
    assertSafetyPayload(result.payload);
});

test('packet_sections 完整', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.deepEqual(payload.packet_sections, gate.PACKET_SECTIONS);
    assert.ok(payload.packet_sections.includes('source_manifest_summary'));
    assert.ok(payload.packet_sections.includes('final_human_approval_required'));
});

test('approval form 默认 not_approved 且 final_human_confirmation=false', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.approval_status, 'not_approved');
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.approval_form_is_template, true);
    assert.equal(payload.approval_granted, false);
    assert.deepEqual(payload.approval_form_summary.target_tables, ['matches']);
});

test('candidate tables 包含 proposed、blocked 和 manual review 列表', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.deepEqual(payload.proposed_match_ids, [
        'fd_sp2_2024_20240817_alpha_beta_11111111',
        'fd_sp2_2024_20240818_gamma_delta_22222222',
        'fd_sp2_2024_20240819_manual_33333333',
    ]);
    assert.equal(payload.insert_candidate_table.length, 1);
    assert.equal(payload.insert_candidate_table[0].approved_to_insert, false);
    assert.equal(payload.blocked_candidate_table.length, 1);
    assert.equal(payload.manual_review_table.length, 1);
});

test('--commit blocked', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
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
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.69C/);
    assertSafetyPayload(result.payload);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for sha256 mismatch');
    });
    const payload = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            dbClient: client,
            runDryRun: () =>
                buildDryRunPayload({
                    ok: false,
                    sha256_match: false,
                    row_count_match: true,
                    errors: ['sha256 mismatch; parser was not executed'],
                }),
            runDuplicatePrecheck: async () => {
                throw new Error('duplicate precheck should not run');
            },
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'csv-dry-run-failed');
    assert.equal(payload.sha256_match, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
});

test('row_count mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for row_count mismatch');
    });
    const payload = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            dbClient: client,
            runDryRun: () =>
                buildDryRunPayload({
                    ok: false,
                    sha256_match: true,
                    row_count_match: false,
                    errors: ['row_count mismatch; parser was not executed'],
                }),
            runDuplicatePrecheck: async () => {
                throw new Error('duplicate precheck should not run');
            },
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'csv-dry-run-failed');
    assert.equal(payload.row_count_match, false);
    assert.equal(payload.select_only_db_reads, false);
    assert.equal(client.calls.length, 0);
});

test('approval form invalid 时失败', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    let dryRunCalled = false;
    const invalidApproval = APPROVAL_FORM_TEXT.replace('approval_status: not_approved', 'approval_status: approved');
    const payload = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            readFileSync: createReadFileSync({
                [APPROVAL_FORM_PATH]: invalidApproval,
            }),
            runDryRun: () => {
                dryRunCalled = true;
                return buildDryRunPayload();
            },
        })
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.mode, 'approval-form-validation-failed');
    assert.equal(payload.approval_form_validation_passed, false);
    assert.equal(dryRunCalled, false);
    assert.match(payload.errors.join('\n'), /approval_status must remain not_approved/);
});

test('approval YAML 缺失或解析失败时不会授予 approval', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const noYaml = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            readFileSync: createReadFileSync({
                [APPROVAL_FORM_PATH]: '# no yaml block\n',
            }),
            runApprovalValidation: () => ({ ok: true, target_tables: ['matches'], warnings: [], errors: [] }),
        })
    );
    const malformedYaml = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            readFileSync: createReadFileSync({
                [APPROVAL_FORM_PATH]: '```yaml\nnot yaml\n```\n',
            }),
            runApprovalValidation: () => ({ ok: true, target_tables: ['matches'], warnings: [], errors: [] }),
        })
    );

    assert.equal(noYaml.ok, true);
    assert.equal(noYaml.approval_status, null);
    assert.equal(noYaml.approval_granted, false);
    assert.equal(malformedYaml.ok, true);
    assert.equal(malformedYaml.approval_status, null);
    assert.equal(malformedYaml.approval_granted, false);
});

test('manifest JSON 解析失败只进入 summary，不触发写入', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            readFileSync: createReadFileSync({
                [MANIFEST_PATH]: '{not json',
            }),
        })
    );

    assert.equal(payload.ok, true);
    assert.match(payload.source_manifest_summary.path, /football_data_sample_phase463c_manifest\.json/);
    assert.equal(payload.source_manifest_summary.source_name, null);
    assert.equal(payload.would_write_db, false);
});

test('preflight / duplicate / insert policy / auth preview 失败时短路', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const preflightFailed = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            runPreflight: () => ({ ok: false, errors: ['preflight failed'], warnings: ['preflight warning'] }),
        })
    );
    const duplicateFailed = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            runDuplicatePrecheck: async () => ({ ok: false, errors: ['duplicate failed'], warnings: [] }),
        })
    );
    const insertFailed = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            runInsertPolicyPrecheck: async () => ({ ok: false, errors: ['insert policy failed'], warnings: [] }),
        })
    );
    const authFailed = await gate.runPacketAssembly(
        baseArgs(),
        buildDependencies({
            runSmallWriteAuthPreview: async () => ({ ok: false, errors: ['auth failed'], warnings: [] }),
        })
    );

    assert.equal(preflightFailed.mode, 'db-write-preflight-failed');
    assert.equal(preflightFailed.csv_dry_run_passed, true);
    assert.match(preflightFailed.errors.join('\n'), /preflight failed/);
    assert.deepEqual(preflightFailed.warnings, ['preflight warning']);
    assert.equal(duplicateFailed.mode, 'duplicate-precheck-failed');
    assert.equal(duplicateFailed.db_write_preflight_passed, true);
    assert.match(duplicateFailed.errors.join('\n'), /duplicate failed/);
    assert.equal(insertFailed.mode, 'insert-policy-precheck-failed');
    assert.equal(insertFailed.duplicate_precheck_passed, true);
    assert.match(insertFailed.errors.join('\n'), /insert policy failed/);
    assert.equal(authFailed.mode, 'small-write-auth-preview-failed');
    assert.equal(authFailed.insert_policy_precheck_passed, true);
    assert.match(authFailed.errors.join('\n'), /auth failed/);
});

test('packet assembly 不访问外网', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
    assert.ok(payload.non_execution_confirmations.includes('no_external_network'));
});

test('packet assembly 不写文件或 packet 文件', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_files, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.ok(payload.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(payload.non_execution_confirmations.includes('no_packet_file_write'));
});

test('packet assembly 不执行 pg_dump / pg_restore', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
    assert.match(payload.pg_dump_command_preview, /pg_dump/);
    assert.match(payload.pg_restore_command_preview, /pg_restore/);
});

test('packet assembly 不 spawn child process', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});

test('packet assembly 不训练和不预测', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
    const payload = await gate.runPacketAssembly(baseArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_train_model, false);
    assert.equal(payload.would_execute_prediction, false);
    assert.ok(payload.non_execution_confirmations.includes('no_training'));
    assert.ok(payload.non_execution_confirmations.includes('no_prediction_execution'));
});

test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
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
    const gate = loadPacketFresh();
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
            existsSync: () => {
                throw new Error('synthetic exists failure');
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
    assert.match(runtimeResult.payload.errors.join('\n'), /synthetic exists failure/);
});

test('failure text output 包含 errors 和 warnings', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
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
        buildDependencies({
            runPreflight: () => ({ ok: false, errors: ['preflight failed'], warnings: ['preview warning'] }),
        })
    );

    assert.equal(status, 1);
    assert.match(stdout, /mode=db-write-preflight-failed/);
    assert.match(stdout, /errors=preflight failed/);
    assert.match(stdout, /warnings=\["preview warning"\]/);
});

test('text output 包含 required summary 字段', async t => {
    installExecutionGuards(t);
    const gate = loadPacketFresh();
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
    assert.match(stdout, /phase=PHASE4\.69C_FOOTBALL_DATA_SMALL_WRITE_PACKET_ASSEMBLY/);
    assert.match(stdout, /csv_dry_run_passed=true/);
    assert.match(stdout, /db_write_preflight_passed=true/);
    assert.match(stdout, /duplicate_precheck_passed=true/);
    assert.match(stdout, /insert_policy_precheck_passed=true/);
    assert.match(stdout, /small_write_auth_preview_passed=true/);
    assert.match(stdout, /approval_form_validation_passed=true/);
    assert.match(stdout, /packet_write_allowed=false/);
    assert.match(stdout, /db_write_allowed=false/);
    assert.match(stdout, /small_write_authorized=false/);
    assert.match(stdout, /would_write_packet_file=false/);
    assert.match(stdout, /would_execute_pg_dump=false/);
    assert.match(stdout, /would_execute_pg_restore=false/);
    assert.match(stdout, /would_write_db=false/);
    assert.match(stdout, /approval_status=not_approved/);
    assert.match(stdout, /final_human_confirmation=false/);
    assert.match(stdout, /future_real_packet_requirements:/);
});
