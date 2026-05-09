'use strict';
/* eslint-disable max-lines -- Phase 4.76C closure safety contract is intentionally explicit. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_preauthorization_closure.js');
const CLOSURE_TEMPLATE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_PREAUTHORIZATION_CLOSURE_TEMPLATE.md'
);
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
    CLOSURE_TEMPLATE_PATH,
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
    const original = {
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
        throw new Error(`${name} should not be called by preauthorization closure script`);
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
        return original.load.call(this, request, parent, isMain);
    };

    t.after(() => {
        Object.assign(http, { request: original.httpRequest });
        Object.assign(https, { request: original.httpsRequest });
        global.fetch = original.fetch;
        Object.assign(childProcess, {
            spawn: original.spawn,
            exec: original.exec,
            execFile: original.execFile,
        });
        Object.assign(fs, {
            writeFile: original.writeFile,
            writeFileSync: original.writeFileSync,
            createWriteStream: original.createWriteStream,
            mkdir: original.mkdir,
            mkdirSync: original.mkdirSync,
        });
        Module._load = original.load;
    });
}

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function baseArgs(overrides = {}) {
    return {
        closureTemplate: CLOSURE_TEMPLATE_PATH,
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

function buildDbClient(rows = defaultDbRows()) {
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
    return {
        dbClient: overrides.dbClient || buildDbClient(),
        existsSync: fs.existsSync.bind(fs),
        readFileSync: fs.readFileSync.bind(fs),
        ...overrides,
    };
}

function fakeExistsSync(allowed) {
    return filePath => allowed.some(allowedPath => path.resolve(allowedPath) === path.resolve(filePath));
}

function overrideReadFile(targetPath, content) {
    return filePath =>
        path.resolve(filePath) === path.resolve(targetPath) ? content : fs.readFileSync(filePath, 'utf8');
}

for (const [field, label] of [
    ['closureTemplate', 'closure template'],
    ['consolidationTemplate', 'consolidation template'],
    ['draftTemplate', 'draft template'],
    ['readinessChecklist', 'readiness checklist'],
    ['authForm', 'auth form'],
    ['sourceManifest', 'source manifest'],
    ['localCsv', 'local CSV'],
    ['approvalForm', 'approval form'],
    ['runbookTemplate', 'runbook template'],
]) {
    test(`缺 ${label} 参数时失败`, async t => {
        installExecutionGuards(t);
        const { runPreauthorizationClosure } = loadFresh();
        const args = baseArgs({ [field]: '' });
        const result = await runPreauthorizationClosure(args, buildDependencies());
        assert.strictEqual(result.ok, false);
        assert.ok(result.errors.some(error => error.includes('provide --closure-template')));
    });
}

test('正确 closure review 成功', async t => {
    installExecutionGuards(t);
    const { runPreauthorizationClosure } = loadFresh();
    const result = await runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.closure_review_completed, true);
    assert.strictEqual(result.closure_status, 'preauthorization_closed_not_authorized');
});

test('输出核心 false / blocked 状态', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.consolidation_status, 'draft_review_only');
    assert.strictEqual(result.draft_status, 'draft_only');
    assert.strictEqual(result.readiness_status, 'not_ready');
    assert.strictEqual(result.authorization_status, 'not_authorized');
    assert.strictEqual(result.ready_for_packet_file_creation, false);
    assert.strictEqual(result.authorized_for_packet_file_creation, false);
    assert.strictEqual(result.packet_file_creation_ready, false);
    assert.strictEqual(result.packet_file_creation_authorized, false);
    assert.strictEqual(result.final_packet_creation_confirmation, false);
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.commit_gate, 'blocked');
});

test('preauthorization_closure_sections 完整', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    for (const section of [
        'chain_inventory',
        'gate_inventory',
        'template_inventory',
        'status_summary',
        'human_only_missing_fields',
        'unresolved_readiness_items',
        'consolidated_blocking_reasons',
        'permission_separation',
        'future_authorization_requirements',
        'final_non_authorization_decision',
    ]) {
        assert.ok(result.preauthorization_closure_sections.includes(section), section);
    }
});

test('closure_blocking_reasons 包含必要字段', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    const reasons = result.closure_blocking_reasons;
    assert.ok(reasons.includes('closure_status is preauthorization_closed_not_authorized'));
    assert.ok(reasons.includes('consolidation_status is draft_review_only'));
    assert.ok(reasons.includes('draft_status is draft_only'));
    assert.ok(reasons.includes('readiness_status is not_ready'));
    assert.ok(reasons.includes('authorization_status is not_authorized'));
    assert.ok(reasons.includes('ready_for_packet_file_creation is false'));
    assert.ok(reasons.includes('authorized_for_packet_file_creation is false'));
    assert.ok(reasons.includes('human-only fields remain empty'));
    assert.ok(reasons.includes('packet file creation is not authorized in this phase'));
});

test('permission_separation 包含 packet / DB write / pg_dump / training / prediction 分离', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    const items = result.permission_separation;
    assert.ok(items.includes('pre-authorization closure does not authorize packet file creation'));
    assert.ok(items.includes('packet file creation does not authorize DB write'));
    assert.ok(items.includes('packet file creation does not authorize pg_dump'));
    assert.ok(items.includes('packet file creation does not authorize pg_restore'));
    assert.ok(items.includes('packet file creation does not authorize training'));
    assert.ok(items.includes('packet file creation does not authorize prediction'));
});

test('next_phase_requirements 包含 human authorization 条件', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    const items = result.next_phase_requirements;
    assert.ok(items.includes('explicit user authorization for packet file creation'));
    assert.ok(items.includes('real reviewed auth form'));
    assert.ok(items.includes('real reviewed readiness checklist'));
    assert.ok(items.includes('explicit packet output directory'));
    assert.ok(items.includes('explicit packet file path'));
    assert.ok(items.includes('explicit packet manifest path'));
    assert.ok(items.includes('final_packet_creation_confirmation=true set only by human'));
});

test('approved-looking closure 也不能在 Phase 4.76C 执行写动作', async t => {
    installExecutionGuards(t);
    const approvedLooking = fs
        .readFileSync(CLOSURE_TEMPLATE_PATH, 'utf8')
        .replace('preauthorization_closed_not_authorized', 'approved')
        .replace('ready_for_packet_file_creation: false', 'ready_for_packet_file_creation: true');
    const dbClient = buildDbClient();
    const result = await loadFresh().runPreauthorizationClosure(
        baseArgs(),
        buildDependencies({
            dbClient,
            existsSync: fakeExistsSync(ALL_PATHS),
            readFileSync: overrideReadFile(CLOSURE_TEMPLATE_PATH, approvedLooking),
        })
    );
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.would_write_db, false);
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.strictEqual(dbClient.calls.length, 0);
});

test('--commit blocked', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs({ commit: true }), buildDependencies());
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.mode, 'blocked-commit');
    assert.ok(result.blocked);
    assert.ok(result.blocked_reason.includes('not wired in Phase 4.76C'));
});

test('sha256 mismatch 时失败且不查 DB', async t => {
    installExecutionGuards(t);
    const badManifest = fs
        .readFileSync(MANIFEST_PATH, 'utf8')
        .replace(
            'd6681446dc08f44987aa50fec79e50091b12ff18a6808e2b4d4b703ed806605d',
            '00001446dc08f44987aa50fec79e50091b12ff18a6808e2b4d4b703ed806605d'
        );
    const dbClient = buildDbClient();
    const result = await loadFresh().runPreauthorizationClosure(
        baseArgs(),
        buildDependencies({
            dbClient,
            existsSync: fakeExistsSync(ALL_PATHS),
            readFileSync: overrideReadFile(MANIFEST_PATH, badManifest),
        })
    );
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(error => error.includes('sha256 mismatch')));
    assert.strictEqual(result.select_only_db_reads, false);
    assert.strictEqual(dbClient.calls.length, 0);
});

for (const [targetPath, label, badContent, expected] of [
    [CLOSURE_TEMPLATE_PATH, 'closure template', '# Bad\n```yaml\nphase: WRONG\n```\n', 'closure template'],
    [CONSOLIDATION_TEMPLATE_PATH, 'consolidation template', '# Bad\n```yaml\nphase: WRONG\n```\n', 'consolidation'],
    [DRAFT_TEMPLATE_PATH, 'draft template', '# Bad\n```yaml\nphase: WRONG\n```\n', 'draft template'],
    [READINESS_CHECKLIST_PATH, 'readiness checklist', '# Bad\n```yaml\nphase: WRONG\n```\n', 'readiness checklist'],
    [AUTH_FORM_PATH, 'auth form', '# Bad\nNo YAML.\n', 'auth form template invalid'],
]) {
    test(`${label} invalid 时失败`, async t => {
        installExecutionGuards(t);
        const result = await loadFresh().runPreauthorizationClosure(
            baseArgs(),
            buildDependencies({
                existsSync: fakeExistsSync(ALL_PATHS),
                readFileSync: overrideReadFile(targetPath, badContent),
            })
        );
        assert.strictEqual(result.ok, false);
        assert.ok(result.errors.some(error => error.includes(expected)));
    });
}

test('不访问外网', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_access_network, false);
    assert.ok(result.non_execution_confirmations.includes('no_external_network'));
});

test('不写文件', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_files, false);
    assert.ok(result.non_execution_confirmations.includes('no_file_writes'));
});

test('不创建目录', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_create_packet_directory, false);
    assert.ok(result.non_execution_confirmations.includes('no_packet_directory_create'));
});

test('不写 packet 文件', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_write_packet_file, false);
    assert.strictEqual(result.would_write_packet_manifest, false);
    assert.ok(result.non_execution_confirmations.includes('no_packet_file_write'));
});

test('不执行 pg_dump', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_dump, false);
    assert.ok(result.non_execution_confirmations.includes('no_pg_dump_execution'));
});

test('不执行 pg_restore', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.would_execute_pg_restore, false);
    assert.ok(result.non_execution_confirmations.includes('no_pg_restore_execution'));
});

test('不 spawn child process', async t => {
    installExecutionGuards(t);
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies());
    assert.strictEqual(result.closure_review_completed, true);
});

test('SQL 只允许 SELECT / BEGIN READ ONLY / ROLLBACK', async t => {
    installExecutionGuards(t);
    const dbClient = buildDbClient();
    const result = await loadFresh().runPreauthorizationClosure(baseArgs(), buildDependencies({ dbClient }));
    assert.strictEqual(result.closure_review_completed, true);
    assert.ok(dbClient.calls.length > 0);
    for (const sql of dbClient.calls) {
        const upperSql = sql.trim().toUpperCase();
        assert.ok(
            upperSql.startsWith('SELECT') || upperSql.startsWith('BEGIN READ ONLY') || upperSql.startsWith('ROLLBACK'),
            `SQL not SELECT/BEGIN READ ONLY/ROLLBACK: ${sql.substring(0, 80)}`
        );
        for (const keyword of ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COPY']) {
            assert.ok(!upperSql.includes(keyword), `SQL has ${keyword}: ${sql.substring(0, 80)}`);
        }
    }
});
