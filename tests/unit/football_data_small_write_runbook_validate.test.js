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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_small_write_runbook_validate.js');
const TEMPLATE_PATH = path.join(PROJECT_ROOT, 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md');
const TEMPLATE_TEXT = fs.readFileSync(TEMPLATE_PATH, 'utf8');

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalLoad = Module._load;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_small_write_runbook_validate`);
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
            'pg',
        ]);
        if (blockedImports.has(request)) {
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

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildDependencies(markdownText = TEMPLATE_TEXT) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: () => true,
        readFileSync: () => markdownText,
    };
}

function replaceInTemplate(searchValue, replaceValue) {
    assert.match(TEMPLATE_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return TEMPLATE_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return TEMPLATE_TEXT.replace(`${line}\n`, '');
}

function runMain(gate, argv, dependencies = buildDependencies()) {
    let stdout = '';
    let stderr = '';
    const status = gate.main(
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

    return {
        status,
        stdout,
        stderr,
    };
}

test('缺 approval form 参数时失败', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, [], buildDependencies());

    assert.equal(result.status, 1);
    assert.match(result.stdout, /ERROR: provide --approval-form=<path>/);
});

test('正确 approval form template validation 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { approvalForm: 'docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md' },
        buildDependencies()
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.approval_status, 'not_approved');
    assert.deepEqual(payload.target_tables, ['matches']);
    assert.equal(payload.would_read_db, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_execute_pg_dump, false);
    assert.equal(payload.would_execute_pg_restore, false);
});

test('CLI --help 输出 usage', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--help'], buildDependencies());

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Usage:/);
    assert.match(result.stdout, /No DB reads, no DB writes/);
});

test('CLI 支持等号参数和 JSON 输出', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--approval-form=approval.md', '--json'], buildDependencies());
    const payload = JSON.parse(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.ok, true);
    assert.equal(payload.approval_status, 'not_approved');
});

test('未知参数失败且保持 non-execution flags', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--unknown', '--json'], buildDependencies());
    const payload = JSON.parse(result.stdout);

    assert.equal(result.status, 1);
    assert.equal(payload.would_read_db, false);
    assert.equal(payload.would_write_db, false);
    assert.match(payload.errors.join('\n'), /Unknown argument: --unknown/);
});

test('approval form 文件不存在时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { approvalForm: 'missing/approval.md' },
        {
            cwd: PROJECT_ROOT,
            existsSync: () => false,
            readFileSync: () => {
                throw new Error('readFileSync should not run for missing approval form');
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.approval_form_found, false);
    assert.match(payload.errors.join('\n'), /approval form not found: missing\/approval.md/);
});

test('YAML block 缺失时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies('# missing yaml\n'));

    assert.equal(payload.ok, false);
    assert.equal(payload.yaml_block_found, false);
    assert.match(payload.errors.join('\n'), /YAML fenced block not found/);
});

test('YAML 顶层格式不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies('```yaml\nnot yaml\n```\n'));

    assert.equal(payload.ok, false);
    assert.equal(payload.yaml_block_found, true);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML line/);
});

test('YAML nested 格式不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { approvalForm: 'approval.md' },
        buildDependencies('```yaml\nexpected_before_counts:\n  not yaml\n```\n')
    );

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML line/);
});

test('YAML indentation 不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { approvalForm: 'approval.md' },
        buildDependencies('```yaml\n  matches:\n```\n')
    );

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML indentation/);
});

test('YAML scalar parser 支持注释、数组、引号、数字和 nested overwrite', () => {
    const gate = loadValidatorFresh();
    const parsed = gate.parseYamlBlock(
        [
            'phase: PHASE # inline comment',
            'empty_value:',
            'empty_array: []',
            'inline_array: [matches, 2, true]',
            'quoted: "hello"',
            "single_quoted: 'world'",
            'number_value: 7',
            'parent: scalar',
            '  child:',
        ].join('\n')
    );

    assert.equal(parsed.phase, 'PHASE');
    assert.equal(parsed.empty_value, null);
    assert.deepEqual(parsed.empty_array, []);
    assert.deepEqual(parsed.inline_array, ['matches', 2, true]);
    assert.equal(parsed.quoted, 'hello');
    assert.equal(parsed.single_quoted, 'world');
    assert.equal(parsed.number_value, 7);
    assert.deepEqual(parsed.parent, { child: null });
});

test('required field 缺失时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = removeLineFromTemplate('operator:');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.deepEqual(payload.missing_fields, ['operator']);
    assert.match(payload.errors.join('\n'), /missing required fields: operator/);
});

test('nested required count field 缺失时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = removeLineFromTemplate('  bookmaker_odds_history:');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.deepEqual(payload.missing_fields, ['expected_before_counts.bookmaker_odds_history']);
    assert.match(payload.errors.join('\n'), /expected_before_counts\.bookmaker_odds_history/);
});

test('approval_status 不是 not_approved 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('approval_status: not_approved', 'approval_status: approved_for_db_write');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /approval_status must remain not_approved/);
});

test('target_tables 包含非 matches 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('  - matches', '  - matches\n  - bookmaker_odds_history');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /target_tables must contain only matches/);
});

test('allow_odds_insert=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_odds_insert: false', 'allow_odds_insert: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_odds_insert must be false/);
});

test('allow_raw_insert=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_raw_insert: false', 'allow_raw_insert: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_raw_insert must be false/);
});

test('allow_l3_insert=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_l3_insert: false', 'allow_l3_insert: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_l3_insert must be false/);
});

test('allow_training=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_training: false', 'allow_training: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_training must be false/);
});

test('allow_prediction=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_prediction: false', 'allow_prediction: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_prediction must be false/);
});

test('require_pg_dump=false 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('require_pg_dump: true', 'require_pg_dump: false');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /require_pg_dump must be true/);
});

test('post_write_validation_required=false 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'post_write_validation_required: true',
        'post_write_validation_required: false'
    );
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /post_write_validation_required must be true/);
});

test('final_human_confirmation=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('final_human_confirmation: false', 'final_human_confirmation: true');
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /final_human_confirmation must be false/);
});

test('--commit 始终 blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--approval-form', 'approval.md', '--commit'], buildDependencies());

    assert.equal(result.status, 1);
    assert.match(result.stdout, /BLOCKED: football-data small write runbook commit is not wired in Phase 4.68C/);
});

test('validator 不访问外网', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
});

test('validator 不读 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_read_db, false);
});

test('validator 不写 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_db, false);
});

test('validator 不写文件', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_files, false);
});

test('validator 不执行 pg_dump', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_dump, false);
});

test('validator 不执行 pg_restore', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_restore, false);
});

test('validator 不 spawn child process', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ approvalForm: 'approval.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});
