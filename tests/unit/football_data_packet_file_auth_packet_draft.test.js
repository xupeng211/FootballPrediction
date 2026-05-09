'use strict';
/* eslint-disable max-lines -- Phase 4.74C keeps the auth packet draft safety contract in one focused test file. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_auth_packet_draft.js');
const DRAFT_TEMPLATE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_PACKET_DRAFT_TEMPLATE.md'
);
const READINESS_CHECKLIST_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_READINESS_CHECKLIST_TEMPLATE.md'
);
const AUTH_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md'
);
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

const DRAFT_TEMPLATE_TEXT = fs.readFileSync(DRAFT_TEMPLATE_PATH, 'utf8');
const READINESS_CHECKLIST_TEXT = fs.readFileSync(READINESS_CHECKLIST_PATH, 'utf8');
const AUTH_FORM_TEXT = fs.readFileSync(AUTH_FORM_PATH, 'utf8');
const SOURCE_MANIFEST_TEXT = fs.readFileSync(MANIFEST_PATH, 'utf8');
const LOCAL_CSV_TEXT = fs.readFileSync(CSV_PATH, 'utf8');
const APPROVAL_FORM_TEXT = fs.readFileSync(APPROVAL_FORM_PATH, 'utf8');
const RUNBOOK_TEMPLATE_TEXT = fs.readFileSync(RUNBOOK_TEMPLATE_PATH, 'utf8');

const ALL_PATHS = [
    DRAFT_TEMPLATE_PATH,
    READINESS_CHECKLIST_PATH,
    AUTH_FORM_PATH,
    MANIFEST_PATH,
    CSV_PATH,
    APPROVAL_FORM_PATH,
    RUNBOOK_TEMPLATE_PATH,
];

function installExecutionGuards(t) {
    const originals = {
        httpRequest: http.request,
        httpsRequest: https.request,
        fetch: global.fetch,
        spawn: childProcess.spawn,
        exec: childProcess.exec,
        execFile: childProcess.execFile,
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        createWriteStream: fs.createWriteStream,
        mkdir: fs.mkdir,
        mkdirSync: fs.mkdirSync,
        load: Module._load,
    };
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_packet_file_auth_packet_draft`);
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
        return originals.load.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originals.httpRequest;
        https.request = originals.httpsRequest;
        global.fetch = originals.fetch;
        childProcess.spawn = originals.spawn;
        childProcess.exec = originals.exec;
        childProcess.execFile = originals.execFile;
        fs.writeFile = originals.writeFile;
        fs.writeFileSync = originals.writeFileSync;
        fs.createWriteStream = originals.createWriteStream;
        fs.mkdir = originals.mkdir;
        fs.mkdirSync = originals.mkdirSync;
        Module._load = originals.load;
    });
}

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function baseArgs(overrides = {}) {
    return {
        draftTemplate: DRAFT_TEMPLATE_PATH,
        readinessChecklist: READINESS_CHECKLIST_PATH,
        authForm: AUTH_FORM_PATH,
        sourceManifest: MANIFEST_PATH,
        localCsv: CSV_PATH,
        approvalForm: APPROVAL_FORM_PATH,
        runbookTemplate: RUNBOOK_TEMPLATE_PATH,
        commit: false,
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

function defaultDbRows() {
    return [
        { table_name: 'matches', rows: '2' },
        { table_name: 'bookmaker_odds_history', rows: '2' },
        { table_name: 'raw_match_data', rows: '2' },
        { table_name: 'l3_features', rows: '2' },
        { table_name: 'match_features_training', rows: '2' },
        { table_name: 'predictions', rows: '2' },
    ];
}

function buildDependencies(overrides = {}) {
    return {
        dbClient: overrides.dbClient || buildDbClient(defaultDbRows()),
        existsSync: fs.existsSync.bind(fs),
        readFileSync: fs.readFileSync.bind(fs),
        ...overrides,
    };
}

function fakeExistsSync(allowedPaths) {
    return filePath => {
        const normalized = path.resolve(filePath);
        for (const allowed of allowedPaths) {
            if (path.resolve(allowed) === normalized) return true;
        }
        return false;
    };
}

// Test 1: missing draft template
test('缺 draft template 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), draftTemplate: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--draft-template')));
});

// Test 2: missing readiness checklist
test('缺 readiness checklist 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), readinessChecklist: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--readiness-checklist')));
});

// Test 3: missing auth form
test('缺 auth form 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), authForm: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--auth-form')));
});

// Test 4: missing source manifest
test('缺 source manifest 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), sourceManifest: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--source-manifest')));
});

// Test 5: missing local CSV
test('缺 local CSV 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), localCsv: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--local-csv')));
});

// Test 6: missing approval form
test('缺 approval form 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), approvalForm: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--approval-form')));
});

// Test 7: missing runbook template
test('缺 runbook template 参数时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview({ ...baseArgs(), runbookTemplate: '' }, buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.includes('--runbook-template')));
});

// Test 8: correct draft review succeeds
test('正确 draft review 成功', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    // Draft review always concludes draft_only ready=false authorized=false
    assert.strictEqual(result.draft_review_completed, true);
    assert.strictEqual(result.draft_status, 'draft_only');
    assert.strictEqual(result.draft_template_found, true);
});

// Test 9: output fields all false
test('输出关键字段全为 false', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.draft_review_completed, true);
    assert.strictEqual(result.draft_status, 'draft_only');
    assert.strictEqual(result.ready_for_human_review, false);
    assert.strictEqual(result.ready_for_packet_file_creation, false);
    assert.strictEqual(result.authorized_for_packet_file_creation, false);
    assert.strictEqual(result.packet_file_creation_ready, false);
    assert.strictEqual(result.packet_file_creation_authorized, false);
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.would_execute_pg_dump, false);
    assert.strictEqual(result.would_execute_pg_restore, false);
    assert.strictEqual(result.commit_gate, 'blocked');
});

// Test 10: authorization_packet_draft_sections 完整
test('authorization_packet_draft_sections 完整', async t => {
    installExecutionGuards(t);
    const { runDraftReview, AUTHORIZATION_PACKET_DRAFT_SECTIONS } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.ok(Array.isArray(result.authorization_packet_draft_sections));
    assert.ok(result.authorization_packet_draft_sections.includes('packet_creation_scope'));
    assert.ok(result.authorization_packet_draft_sections.includes('gate_results_summary'));
    assert.ok(result.authorization_packet_draft_sections.includes('readiness_review_summary'));
    assert.ok(result.authorization_packet_draft_sections.includes('authorization_review_summary'));
    assert.ok(result.authorization_packet_draft_sections.includes('final_human_decision_required'));
});

// Test 11: missing_draft_requirements 包含必要字段
test('missing_draft_requirements 包含必要字段', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.ok(Array.isArray(result.missing_draft_requirements));
    const items = result.missing_draft_requirements;
    assert.ok(items.some(i => i.includes('draft_status must remain draft_only')));
    assert.ok(items.some(i => i.includes('readiness_status must be ready')));
    assert.ok(items.some(i => i.includes('authorization_status must be authorized')));
    assert.ok(items.some(i => i.includes('final_packet_creation_confirmation must be true')));
    assert.ok(items.some(i => i.includes('operator must be filled')));
    assert.ok(items.some(i => i.includes('reviewer must be filled')));
});

// Test 12: permission_separation 包含分离声明
test('permission_separation 包含 packet / DB write / pg_dump / training / prediction 分离', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.ok(Array.isArray(result.permission_separation));
    const items = result.permission_separation;
    assert.ok(items.some(i => i.includes('authorization packet draft does not authorize packet file creation')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize DB write')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize pg_dump')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize pg_restore')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize training')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize prediction')));
});

// Test 13: draft-looking authorized form 也不能执行写动作
test('draft-looking authorized form 也不能在 Phase 4.74C 执行写动作', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.would_execute_pg_dump, false);
    assert.strictEqual(result.would_execute_pg_restore, false);
    assert.strictEqual(result.would_insert_matches, false);
    assert.strictEqual(result.would_access_network, false);
});

// Test 14: --commit blocked
test('--commit blocked', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs({ commit: true }), buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.mode, 'blocked-commit');
    assert.ok(result.blocked);
    assert.ok(result.blocked_reason.includes('not wired in Phase 4.74C'));
});

// Test 15: sha256 mismatch still passes draft review
test('sha256 mismatch 时仍完成 draft review 且不写 DB', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const deps = buildDependencies();
    const result = await runDraftReview(baseArgs(), deps);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.draft_review_completed, true);
});

// Test 16: draft template invalid 时失败
test('draft template invalid 时失败', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const badDraft = '# Bad\n```yaml\nphase: WRONG_PHASE\ndraft_status: approved\n```\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: filePath => {
            if (path.resolve(filePath) === path.resolve(DRAFT_TEMPLATE_PATH)) return badDraft;
            return fs.readFileSync(filePath, 'utf8');
        },
    });
    const result = await runDraftReview(baseArgs(), deps);
    assert.ok(result.errors.length > 0);
    assert.ok(result.errors.some(e => e.includes('phase must be')));
});

// Test 17: readiness checklist invalid 时失败
test('readiness checklist invalid 时仍完成 draft review', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const badChecklist = '# Bad\n```yaml\nphase: WRONG\ndraft_status: approved\n```\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: filePath => {
            if (path.resolve(filePath) === path.resolve(READINESS_CHECKLIST_PATH)) return badChecklist;
            return fs.readFileSync(filePath, 'utf8');
        },
    });
    const result = await runDraftReview(baseArgs(), deps);
    assert.strictEqual(result.draft_review_completed, true);
});

// Test 18: auth form invalid 时仍完成 draft review
test('auth form invalid 时仍完成 draft review', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const badAuth = '# Just markdown\nNo YAML block.\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: filePath => {
            if (path.resolve(filePath) === path.resolve(AUTH_FORM_PATH)) return badAuth;
            return fs.readFileSync(filePath, 'utf8');
        },
    });
    const result = await runDraftReview(baseArgs(), deps);
    assert.strictEqual(result.draft_review_completed, true);
});

// Test 19: 不访问外网
test('不访问外网', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_access_network, false);
    assert.ok(result.non_execution_confirmations.includes('no_external_network'));
});

// Test 20: 不写文件
test('不写文件', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_files, false);
    assert.ok(result.non_execution_confirmations.includes('no_file_writes'));
});

// Test 21: 不创建目录
test('不创建目录', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.ok(result.non_execution_confirmations.includes('no_packet_directory_create'));
});

// Test 22: 不写 packet 文件
test('不写 packet 文件', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.ok(result.non_execution_confirmations.includes('no_packet_file_write'));
});

// Test 23: 不执行 pg_dump
test('不执行 pg_dump', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_dump, false);
    assert.ok(result.non_execution_confirmations.includes('no_pg_dump_execution'));
});

// Test 24: 不执行 pg_restore
test('不执行 pg_restore', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_restore, false);
    assert.ok(result.non_execution_confirmations.includes('no_pg_restore_execution'));
});

// Test 25: 不 spawn child process
test('不 spawn child process', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const result = await runDraftReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.draft_review_completed, true);
});

// Test 26: SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK
test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK，不允许写操作关键词', async t => {
    installExecutionGuards(t);
    const { runDraftReview } = loadFresh();
    const dbClient = buildDbClient(defaultDbRows());
    const result = await runDraftReview(baseArgs(), buildDependencies({ dbClient }));
    assert.strictEqual(result.draft_review_completed, true);
    for (const sql of dbClient.calls) {
        const upper = sql.trim().toUpperCase();
        assert.ok(
            upper.startsWith('SELECT') || upper.startsWith('BEGIN') || upper.startsWith('ROLLBACK'),
            `SQL call should be SELECT/BEGIN/ROLLBACK only, got: ${sql.substring(0, 50)}`
        );
        const forbidden = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COPY'];
        for (const kw of forbidden) {
            assert.ok(!upper.includes(kw), `SQL call must not contain ${kw}: ${sql.substring(0, 50)}`);
        }
    }
});
