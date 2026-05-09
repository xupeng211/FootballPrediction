'use strict';
/* eslint-disable max-lines -- Phase 4.75C keeps the consolidation review safety contract in one focused test file. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_auth_review_consolidation.js');
const CONSOLIDATION_TEMPLATE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_REVIEW_CONSOLIDATION_TEMPLATE.md'
);
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

const ALL_PATHS = [
    CONSOLIDATION_TEMPLATE_PATH,
    DRAFT_TEMPLATE_PATH,
    READINESS_CHECKLIST_PATH,
    AUTH_FORM_PATH,
    MANIFEST_PATH,
    CSV_PATH,
    APPROVAL_FORM_PATH,
    RUNBOOK_TEMPLATE_PATH,
];

function installExecutionGuards(t) {
    const orig = {
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
    const fail = n => () => {
        throw new Error(`${n} should not be called by consolidation script`);
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
        if (['http', 'node:http', 'https', 'node:https', 'child_process', 'node:child_process'].includes(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return orig.load.call(this, request, parent, isMain);
    };
    t.after(() => {
        Object.assign(http, { request: orig.httpRequest });
        Object.assign(https, { request: orig.httpsRequest });
        global.fetch = orig.fetch;
        Object.assign(childProcess, { spawn: orig.spawn, exec: orig.exec, execFile: orig.execFile });
        Object.assign(fs, {
            writeFile: orig.writeFile,
            writeFileSync: orig.writeFileSync,
            createWriteStream: orig.createWriteStream,
            mkdir: orig.mkdir,
            mkdirSync: orig.mkdirSync,
        });
        Module._load = orig.load;
    });
}

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function baseArgs(overrides = {}) {
    return {
        consolidationTemplate: CONSOLIDATION_TEMPLATE_PATH,
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

function fakeExistsSync(allowed) {
    return fp => allowed.some(a => path.resolve(a) === path.resolve(fp));
}

// Tests 1-8: missing param errors
for (const [i, [field, label]] of [
    ['consolidationTemplate', 'consolidation template'],
    ['draftTemplate', 'draft template'],
    ['readinessChecklist', 'readiness checklist'],
    ['authForm', 'auth form'],
    ['sourceManifest', 'source manifest'],
    ['localCsv', 'local CSV'],
    ['approvalForm', 'approval form'],
    ['runbookTemplate', 'runbook template'],
].entries()) {
    test(`缺 ${label} 参数时失败`, async t => {
        installExecutionGuards(t);
        const { runConsolidationReview } = loadFresh();
        const a = baseArgs();
        a[field] = '';
        const result = await runConsolidationReview(a, buildDependencies());
        assert.strictEqual(result.ok, false);
        assert.ok(result.errors.some(e => e.includes(field.replace(/([A-Z])/g, '-$1').toLowerCase())));
    });
}

// Test 9: correct consolidation review
test('正确 consolidation review 成功', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.consolidation_review_completed, true);
    assert.strictEqual(result.consolidation_status, 'draft_review_only');
    assert.strictEqual(result.consolidation_template_found, true);
});

// Test 10: all key fields false
test('输出关键字段全为 false', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.consolidation_review_completed, true);
    assert.strictEqual(result.consolidation_status, 'draft_review_only');
    assert.strictEqual(result.draft_status, 'draft_only');
    assert.strictEqual(result.readiness_status, 'not_ready');
    assert.strictEqual(result.authorization_status, 'not_authorized');
    assert.strictEqual(result.ready_for_human_review, false);
    assert.strictEqual(result.ready_for_packet_file_creation, false);
    assert.strictEqual(result.authorized_for_packet_file_creation, false);
    assert.strictEqual(result.packet_file_creation_ready, false);
    assert.strictEqual(result.packet_file_creation_authorized, false);
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.commit_gate, 'blocked');
});

// Test 11: consolidated_review_sections 完整
test('consolidated_review_sections 完整', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    assert.ok(result.consolidated_review_sections.includes('packet_creation_scope'));
    assert.ok(result.consolidated_review_sections.includes('readiness_review_summary'));
    assert.ok(result.consolidated_review_sections.includes('authorization_review_summary'));
    assert.ok(result.consolidated_review_sections.includes('final_human_decision_required'));
});

// Test 12: consolidated_blocking_reasons 包含必要字段
test('consolidated_blocking_reasons 包含必要字段', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    const items = result.consolidated_blocking_reasons;
    assert.ok(items.some(i => i.includes('consolidation_status is draft_review_only')));
    assert.ok(items.some(i => i.includes('draft_status is draft_only')));
    assert.ok(items.some(i => i.includes('readiness_status is not_ready')));
    assert.ok(items.some(i => i.includes('authorization_status is not_authorized')));
    assert.ok(items.some(i => i.includes('ready_for_packet_file_creation is false')));
    assert.ok(items.some(i => i.includes('human-only fields remain empty')));
});

// Test 13: permission_separation
test('permission_separation 包含分离声明', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    const items = result.permission_separation;
    assert.ok(items.some(i => i.includes('review consolidation does not authorize packet file creation')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize DB write')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize pg_dump')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize training')));
    assert.ok(items.some(i => i.includes('packet file creation does not authorize prediction')));
});

// Test 14: cannot execute write actions
test('draft-looking approved consolidation 也不能在 Phase 4.75C 执行写动作', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.would_execute_pg_dump, false);
    assert.strictEqual(result.would_execute_pg_restore, false);
    assert.strictEqual(result.would_access_network, false);
});

// Test 15: --commit blocked
test('--commit blocked', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs({ commit: true }), buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.mode, 'blocked-commit');
    assert.ok(result.blocked);
    assert.ok(result.blocked_reason.includes('not wired in Phase 4.75C'));
});

// Test 16: sha256 mismatch passes
test('sha256 mismatch 时仍完成 review 且不写 DB', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const result = await runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.consolidation_review_completed, true);
});

// Tests 17-20: template invalid
test('consolidation template invalid 时失败', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const bad = '# Bad\n```yaml\nphase: WRONG\n```\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: fp =>
            path.resolve(fp) === path.resolve(CONSOLIDATION_TEMPLATE_PATH) ? bad : fs.readFileSync(fp, 'utf8'),
    });
    const result = await runConsolidationReview(baseArgs(), deps);
    assert.ok(result.errors.some(e => e.includes('phase must be')));
});

test('draft template invalid 时仍完成', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const bad = '## No YAML\nNo block.\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: fp =>
            path.resolve(fp) === path.resolve(DRAFT_TEMPLATE_PATH) ? bad : fs.readFileSync(fp, 'utf8'),
    });
    const result = await runConsolidationReview(baseArgs(), deps);
    assert.strictEqual(result.consolidation_review_completed, true);
});

test('readiness checklist invalid 时仍完成', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const bad = '# Bad\n```yaml\nphase: WRONG\ndraft_status: approved\n```\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: fp =>
            path.resolve(fp) === path.resolve(READINESS_CHECKLIST_PATH) ? bad : fs.readFileSync(fp, 'utf8'),
    });
    const result = await runConsolidationReview(baseArgs(), deps);
    assert.strictEqual(result.consolidation_review_completed, true);
});

test('auth form invalid 时仍完成', async t => {
    installExecutionGuards(t);
    const { runConsolidationReview } = loadFresh();
    const bad = '# Just markdown\nNo YAML block.\n';
    const deps = buildDependencies({
        existsSync: fakeExistsSync(ALL_PATHS),
        readFileSync: fp => (path.resolve(fp) === path.resolve(AUTH_FORM_PATH) ? bad : fs.readFileSync(fp, 'utf8')),
    });
    const result = await runConsolidationReview(baseArgs(), deps);
    assert.strictEqual(result.consolidation_review_completed, true);
});

// Tests 21-28: safety guards
test('不访问外网', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_access_network, false);
    assert.ok(result.non_execution_confirmations.includes('no_external_network'));
});
test('不写文件', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_files, false);
    assert.ok(result.non_execution_confirmations.includes('no_file_writes'));
});
test('不创建目录', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.ok(result.non_execution_confirmations.includes('no_packet_directory_create'));
});
test('不写 packet 文件', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
});
test('不执行 pg_dump', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_dump, false);
});
test('不执行 pg_restore', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_restore, false);
});
test('不 spawn child process', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies());
    assert.strictEqual(result.consolidation_review_completed, true);
});
test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', async t => {
    installExecutionGuards(t);
    const dbClient = buildDbClient(defaultDbRows());
    const result = await loadFresh().runConsolidationReview(baseArgs(), buildDependencies({ dbClient }));
    assert.strictEqual(result.consolidation_review_completed, true);
    for (const sql of dbClient.calls) {
        const u = sql.trim().toUpperCase();
        assert.ok(
            u.startsWith('SELECT') || u.startsWith('BEGIN') || u.startsWith('ROLLBACK'),
            `SQL not SELECT/BEGIN/ROLLBACK: ${sql.substring(0, 50)}`
        );
        for (const kw of ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COPY']) {
            assert.ok(!u.includes(kw), `SQL has ${kw}: ${sql.substring(0, 50)}`);
        }
    }
});
