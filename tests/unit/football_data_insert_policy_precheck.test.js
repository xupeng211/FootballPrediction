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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_insert_policy_precheck.js');
const DRY_RUN_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_adapter_dry_run.js');
const DUPLICATE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_duplicate_precheck.js');
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
        throw new Error(`${name} should not be called by football_data_insert_policy_precheck`);
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

function loadPolicyFresh() {
    delete require.cache[SCRIPT_PATH];
    delete require.cache[DRY_RUN_PATH];
    delete require.cache[DUPLICATE_PATH];
    return require(SCRIPT_PATH);
}

function loadManifest() {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function baseCandidate(overrides = {}) {
    return {
        row_number: 1,
        league_code: 'SP2',
        league_name: 'Segunda Division',
        season: '2024/2025',
        match_date: '2024-08-17T17:30:00.000Z',
        home_team: 'Synthetic Home Winners',
        away_team: 'Synthetic Away Losers',
        home_score: 1,
        away_score: 0,
        actual_result: 'home_win',
        odds_preview: {
            available: true,
            values: {
                home: 2.5,
                draw: 3.1,
                away: 2.9,
            },
        },
        ...overrides,
    };
}

function buildDryRunPayload(candidates, approvalStatus = 'dry_run_only') {
    return {
        ok: true,
        source_manifest_found: true,
        local_csv_found: true,
        sha256_match: true,
        row_count_match: true,
        approval_status: approvalStatus,
        source_name: 'unit_fixture',
        parser_version: 'unit_parser',
        dry_run_version: 'unit_dry_run',
        candidate_rows: candidates,
        row_classification: {
            trainable_label_rows: candidates.length,
        },
        warnings: [],
        errors: [],
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

function createDefaultQueryHandler(gate, options = {}) {
    const maxLength = options.maxLength || 50;
    return (sql, params = []) => {
        if (sql === gate.MATCH_ID_COLUMN_SQL) {
            return {
                rows: [
                    {
                        column_name: 'match_id',
                        data_type: 'character varying',
                        character_maximum_length: maxLength,
                        is_nullable: 'NO',
                        column_default: null,
                    },
                ],
            };
        }
        if (sql === gate.MATCHES_CONSTRAINT_SQL) {
            return {
                rows: [
                    {
                        constraint_name: 'matches_pkey',
                        constraint_type: 'PRIMARY KEY',
                        column_name: 'match_id',
                    },
                ],
            };
        }
        if (params[0] === 'Exact Home' && params[1] === 'Exact Away') {
            return { rows: [{ match_id: 'exact_1', home_team: 'Exact Home', away_team: 'Exact Away' }] };
        }
        if (params[0] === 'Reverse Away' && params[1] === 'Reverse Home') {
            return { rows: [{ match_id: 'reversed_1', home_team: 'Reverse Away', away_team: 'Reverse Home' }] };
        }
        if (params[0] === 'Nearby Home' && String(sql).includes('BETWEEN')) {
            return { rows: [{ match_id: 'nearby_1', home_team: 'Nearby Home', away_team: 'Nearby Away' }] };
        }
        return { rows: [] };
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
        assert.doesNotMatch(
            normalized,
            /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|MERGE|GRANT|REVOKE|COMMIT)\b/
        );
    }
}

test('insert policy module 可以 import 且不加载 legacy runtime', t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();

    assert.equal(typeof gate.main, 'function');
    assert.equal(typeof gate.runInsertPolicyPrecheck, 'function');
    assert.equal(typeof gate.buildProposedMatchId, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('缺 source manifest 参数必须失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runInsertPolicyPrecheck(
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
});

test('缺 local CSV 参数必须失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for missing args');
    });
    const payload = await gate.runInsertPolicyPrecheck(
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
});

test('正确 manifest + CSV + mock DB client insert policy precheck 成功', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.66C_FOOTBALL_DATA_INSERT_POLICY');
    assert.equal(payload.source_manifest_found, true);
    assert.equal(payload.local_csv_found, true);
    assert.equal(payload.dry_run_passed, true);
    assert.equal(payload.duplicate_precheck_passed, true);
    assert.equal(payload.sha256_match, true);
    assert.equal(payload.row_count_match, true);
    assert.equal(payload.manifest_approval_status, 'dry_run_only');
    assert.equal(payload.match_id_strategy, 'fd_<league>_<season>_<date>_<home>_<away>_<hash8>');
    assert.equal(payload.match_id_strategy_finalized, false);
    assert.equal(payload.match_id_schema.match_id_max_length, 50);
    assert.equal(payload.match_id_schema.match_id_primary_key, true);
    assert.equal(payload.match_id_schema.match_id_unique, true);
    assert.equal(payload.candidate_rows, 3);
    assert.equal(payload.future_insert_candidates, 0);
    assert.equal(payload.blocked_by_manifest_policy, 3);
    assert.equal(payload.skip_existing_matches, 0);
    assert.equal(payload.manual_review_required, 0);
    assert.equal(payload.invalid_candidates, 0);
    assert.ok(payload.candidate_previews.every(preview => preview.insert_policy === 'blocked_by_manifest_policy'));
    assert.ok(payload.candidate_previews.every(preview => preview.proposed_match_id_length <= 50));
    assertSafetyPayload(payload);
    assertSqlCallsAreReadOnly(gate, client.calls);
});

test('deterministic match_id 对同一 candidate_identity_key 稳定', t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidate = baseCandidate();
    const identityKey = gate.buildCandidateIdentityKey(candidate, 'unit_fixture');
    const first = gate.buildProposedMatchId(candidate, {
        sourceName: 'unit_fixture',
        candidateIdentityKey: identityKey,
        maxLength: 50,
    });
    const second = gate.buildProposedMatchId(candidate, {
        sourceName: 'unit_fixture',
        candidateIdentityKey: identityKey,
        maxLength: 50,
    });

    assert.equal(first.proposed_match_id, second.proposed_match_id);
    assert.equal(first.hash8, second.hash8);
    assert.equal(first.proposed_match_id_valid_length, true);
    assert.match(first.proposed_match_id, /^fd_[a-z0-9]+_[a-z0-9]+_[0-9]{8}_[a-z0-9_]+_[a-z0-9_]+_[a-f0-9]{8}$/);
});

test('match_id identity 不包含 score / actual_result / odds / row_number', t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidateA = baseCandidate({
        row_number: 1,
        home_score: 1,
        away_score: 0,
        actual_result: 'home_win',
        odds_preview: { available: true, values: { home: 2.5 } },
    });
    const candidateB = baseCandidate({
        row_number: 99,
        home_score: 9,
        away_score: 9,
        actual_result: 'away_win',
        odds_preview: { available: true, values: { home: 99.9 } },
    });

    const identityA = gate.buildCandidateIdentityKey(candidateA, 'unit_fixture');
    const identityB = gate.buildCandidateIdentityKey(candidateB, 'unit_fixture');
    const idA = gate.buildProposedMatchId(candidateA, {
        sourceName: 'unit_fixture',
        candidateIdentityKey: identityA,
        maxLength: 50,
    });
    const idB = gate.buildProposedMatchId(candidateB, {
        sourceName: 'unit_fixture',
        candidateIdentityKey: identityB,
        maxLength: 50,
    });

    assert.equal(identityA, identityB);
    assert.equal(idA.proposed_match_id, idB.proposed_match_id);
    assert.doesNotMatch(identityA, /home_win|away_win|99\.9|row_number/);
    assert.doesNotMatch(idA.proposed_match_id, /home_win|away_win|99/);
});

test('proposed_match_id 不超过模拟 schema 最大长度', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const client = createMockClient(createDefaultQueryHandler(gate, { maxLength: 50 }));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );

    assert.equal(payload.ok, true);
    assert.ok(payload.candidate_previews.every(preview => preview.proposed_match_id_length <= 50));
    assert.ok(payload.candidate_previews.every(preview => preview.proposed_match_id_valid_length));
});

test('schema 缺少 match_id 长度时默认使用 64 并保留 unique 约束信息', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const schema = gate.deriveMatchIdSchema(
        [],
        [
            {
                constraint_name: 'matches_match_id_key',
                constraint_type: 'UNIQUE',
                column_name: 'match_id',
            },
        ]
    );

    assert.equal(schema.match_id_column_found, false);
    assert.equal(schema.match_id_max_length, 64);
    assert.equal(schema.match_id_max_length_source, 'default_64');
    assert.equal(schema.match_id_primary_key, false);
    assert.equal(schema.match_id_unique, true);
});

test('过短 match_id 长度限制必须失败而不是输出非法 proposed_match_id', t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();

    assert.throws(
        () =>
            gate.buildProposedMatchId(baseCandidate(), {
                sourceName: 'unit_fixture',
                maxLength: 10,
            }),
        /cannot fit match_id max length/
    );
});

test('dry_run_only manifest 下 policy 必须 blocked_by_manifest_policy', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidate = baseCandidate();
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload([candidate], 'dry_run_only'),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.future_insert_candidates, 0);
    assert.equal(payload.blocked_by_manifest_policy, 1);
    assert.equal(payload.candidate_previews[0].insert_policy, 'blocked_by_manifest_policy');
    assert.equal(payload.candidate_previews[0].would_insert_match, false);
});

test('缺少 duplicate preview 时 candidate 必须按 invalid_candidate 处理', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidate = baseCandidate();
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload([candidate], 'approved_for_db_write'),
            duplicatePreviews: [],
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.invalid_candidates, 1);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'invalid_candidate');
    assert.equal(payload.candidate_previews[0].insert_policy, 'invalid_candidate');
});

test('approved_for_db_write manifest + clean candidate 只能成为 future_insert_candidate preview', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const approvedManifest = {
        ...loadManifest(),
        approval_status: 'approved_for_db_write',
    };
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            dryRunDependencies: {
                readManifest: () => approvedManifest,
            },
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.manifest_approval_status, 'approved_for_db_write');
    assert.equal(payload.future_insert_candidates, 3);
    assert.ok(payload.candidate_previews.every(preview => preview.insert_policy === 'future_insert_candidate'));
    assert.ok(payload.candidate_previews.every(preview => preview.would_insert_match === false));
    assert.equal(payload.would_write_db, false);
});

test('exact existing match 必须 skip_existing_match', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidate = baseCandidate({
        home_team: 'Exact Home',
        away_team: 'Exact Away',
    });
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload([candidate], 'approved_for_db_write'),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.skip_existing_matches, 1);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'exact_existing_match');
    assert.equal(payload.candidate_previews[0].insert_policy, 'skip_existing_match');
    assert.equal(payload.candidate_previews[0].skip_reason, 'exact_existing_match');
});

test('reversed / nearby duplicate 必须 manual_review_required', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidates = [
        baseCandidate({
            row_number: 1,
            home_team: 'Reverse Home',
            away_team: 'Reverse Away',
        }),
        baseCandidate({
            row_number: 2,
            home_team: 'Nearby Home',
            away_team: 'Nearby Away',
        }),
    ];
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload(candidates, 'approved_for_db_write'),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.manual_review_required, 2);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'reversed_teams_possible_duplicate');
    assert.equal(payload.candidate_previews[0].insert_policy, 'manual_review_required');
    assert.equal(payload.candidate_previews[1].duplicate_risk, 'nearby_date_possible_duplicate');
    assert.equal(payload.candidate_previews[1].insert_policy, 'manual_review_required');
});

test('invalid candidate 必须 invalid_candidate 且不进入 future insert', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const candidate = baseCandidate({
        match_date: '',
        actual_result: '',
    });
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        {
            dbClient: client,
            runDryRun: () => buildDryRunPayload([candidate], 'approved_for_db_write'),
        }
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.invalid_candidates, 1);
    assert.equal(payload.future_insert_candidates, 0);
    assert.equal(payload.candidate_previews[0].duplicate_risk, 'invalid_candidate');
    assert.equal(payload.candidate_previews[0].insert_policy, 'invalid_candidate');
    assert.equal(payload.candidate_previews[0].would_insert_match, false);
});

test('--commit 必须 blocked，即使提供 manifest 和 CSV', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
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
    assert.match(result.payload.blocked_reason, /not wired in Phase 4\.66C/);
    assertSafetyPayload(result.payload);
});

test('main --help 输出 usage 且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    let stdout = '';
    const status = await gate.main(['--help'], {
        stdout: text => {
            stdout += text;
        },
    });

    assert.equal(status, 0);
    assert.match(stdout, /football_data_insert_policy_precheck\.js/);
    assert.match(stdout, /Phase 4\.66C is SELECT-only insert policy preview/);
});

test('main runtime error 返回 runtime-error payload', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const result = await runMain(gate, ['--unknown-option', '--json']);

    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.equal(result.payload.mode, 'runtime-error');
    assert.match(result.payload.errors[0], /Unknown argument/);
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const manifest = {
        ...loadManifest(),
        sha256: '0'.repeat(64),
    };
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for sha256 mismatch');
    });
    const payload = await gate.runInsertPolicyPrecheck(
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
});

test('row_count mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const manifest = {
        ...loadManifest(),
        row_count: 99,
    };
    const client = createMockClient(() => {
        throw new Error('DB should not be queried for row_count mismatch');
    });
    const payload = await gate.runInsertPolicyPrecheck(
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
});

test('SQL guard 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();

    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.MATCH_ID_COLUMN_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.MATCHES_CONSTRAINT_SQL));
    assert.doesNotThrow(() => gate.assertSelectOnlySql(gate.READ_ONLY_ROLLBACK_SQL));
    assert.throws(() => gate.assertSelectOnlySql('INSERT INTO matches VALUES ($1)'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('UPDATE matches SET status = $1'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('DELETE FROM matches'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('CREATE TABLE unsafe_table(id int)'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('COMMIT'), /Unsafe SQL/);
    assert.throws(() => gate.assertSelectOnlySql('SELECT 1; DROP TABLE matches'), /Unsafe SQL/);
});

test('文本输出包含策略摘要、candidate preview 和 non-execution confirmations', async t => {
    installExecutionGuards(t);
    const gate = loadPolicyFresh();
    const client = createMockClient(createDefaultQueryHandler(gate));
    const payload = await gate.runInsertPolicyPrecheck(
        {
            sourceManifest: MANIFEST_PATH,
            localCsv: CSV_PATH,
        },
        { dbClient: client }
    );
    const text = gate.payloadToText(payload);

    assert.match(text, /phase=PHASE4\.66C_FOOTBALL_DATA_INSERT_POLICY/);
    assert.match(text, /duplicate_precheck_passed=true/);
    assert.match(text, /match_id_strategy=fd_<league>_<season>_<date>_<home>_<away>_<hash8>/);
    assert.match(text, /match_id_strategy_finalized=false/);
    assert.match(text, /blocked_by_manifest_policy=3/);
    assert.match(text, /candidate_previews=/);
    assert.match(text, /proposed_match_id/);
    assert.match(text, /no_external_network/);
    assert.match(text, /no_db_writes/);
    assert.match(text, /no_file_writes/);
    assert.match(text, /no_pg_dump_execution/);
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
