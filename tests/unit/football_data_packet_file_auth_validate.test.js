'use strict';

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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/football_data_packet_file_auth_validate.js');
const TEMPLATE_PATH = path.join(PROJECT_ROOT, 'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md');
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
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_packet_file_auth_validate`);
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
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
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

test('缺 auth form 参数时失败', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, [], buildDependencies());

    assert.equal(result.status, 1);
    assert.match(result.stdout, /ERROR: provide --auth-form=<path>/);
});

test('正确 template validation 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { authForm: 'docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md' },
        buildDependencies()
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.authorization_status, 'not_authorized');
    assert.equal(payload.final_packet_creation_confirmation, false);
    assert.equal(payload.approved_output_root, 'docs/_packets/football_data/small_write');
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
    const result = runMain(gate, ['--auth-form=auth.md', '--json'], buildDependencies());
    const payload = JSON.parse(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.ok, true);
    assert.equal(payload.authorization_status, 'not_authorized');
});

test('text output 包含 required summary 字段', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--auth-form', 'auth.md'], buildDependencies());

    assert.equal(result.status, 0);
    assert.match(result.stdout, /validation_summary=passed/);
    assert.match(result.stdout, /approved_output_root=docs\/_packets\/football_data\/small_write/);
    assert.match(result.stdout, /approved_packet_sections=/);
    assert.match(result.stdout, /source_manifest_summary/);
    assert.match(result.stdout, /non_execution_confirmations=/);
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

test('auth form 文件不存在时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { authForm: 'missing/auth.md' },
        {
            cwd: PROJECT_ROOT,
            existsSync: () => false,
            readFileSync: () => {
                throw new Error('readFileSync should not run for missing auth form');
            },
        }
    );

    assert.equal(payload.ok, false);
    assert.equal(payload.auth_form_found, false);
    assert.match(payload.errors.join('\n'), /auth form not found: missing\/auth\.md/);
});

test('YAML block 缺失时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies('# missing yaml\n'));

    assert.equal(payload.ok, false);
    assert.equal(payload.yaml_block_found, false);
    assert.match(payload.errors.join('\n'), /YAML fenced block not found/);
});

test('YAML 顶层格式不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies('```yaml\nnot yaml\n```\n'));

    assert.equal(payload.ok, false);
    assert.equal(payload.yaml_block_found, true);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML line/);
});

test('YAML nested 格式不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { authForm: 'auth.md' },
        buildDependencies('```yaml\napproved_packet_sections:\n  not yaml\n```\n')
    );

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML line/);
});

test('YAML indentation 不支持时失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        { authForm: 'auth.md' },
        buildDependencies('```yaml\n  authorization_status:\n```\n')
    );

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unable to parse YAML block: unsupported YAML indentation/);
});

test('YAML scalar parser 支持注释、数组、引号、数字和 nested overwrite', () => {
    const gate = loadValidatorFresh();
    const parsed = gate.parseYamlBlock(
        [
            'phase: PHASE4_PACKET_FILE_CREATION_AUTH # inline comment',
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

    assert.equal(parsed.phase, 'PHASE4_PACKET_FILE_CREATION_AUTH');
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
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.deepEqual(payload.missing_fields, ['operator']);
    assert.match(payload.errors.join('\n'), /missing required fields: operator/);
});

test('phase 不是模板 phase 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'phase: PHASE4_PACKET_FILE_CREATION_AUTH',
        'phase: PHASE4_OTHER_PACKET_FILE_AUTH'
    );
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /phase must remain PHASE4_PACKET_FILE_CREATION_AUTH/);
});

test('authorization_status 不是 not_authorized 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'authorization_status: not_authorized',
        'authorization_status: authorized_for_packet_file_creation'
    );
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /authorization_status must remain not_authorized/);
});

test('allow_packet_directory_creation=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'allow_packet_directory_creation: false',
        'allow_packet_directory_creation: true'
    );
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_packet_directory_creation must be false/);
});

test('allow_packet_file_write=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_packet_file_write: false', 'allow_packet_file_write: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_packet_file_write must be false/);
});

test('allow_packet_manifest_write=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_packet_manifest_write: false', 'allow_packet_manifest_write: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_packet_manifest_write must be false/);
});

test('allow_db_write=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_db_write: false', 'allow_db_write: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_db_write must be false/);
});

test('allow_pg_dump=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_pg_dump: false', 'allow_pg_dump: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_pg_dump must be false/);
});

test('allow_pg_restore=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_pg_restore: false', 'allow_pg_restore: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_pg_restore must be false/);
});

test('allow_external_network=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_external_network: false', 'allow_external_network: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_external_network must be false/);
});

test('allow_training=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_training: false', 'allow_training: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_training must be false/);
});

test('allow_prediction=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate('allow_prediction: false', 'allow_prediction: true');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /allow_prediction must be false/);
});

test('final_packet_creation_confirmation=true 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'final_packet_creation_confirmation: false',
        'final_packet_creation_confirmation: true'
    );
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /final_packet_creation_confirmation must be false/);
});

test('approved_output_root 不在允许目录时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = replaceInTemplate(
        'approved_output_root: docs/_packets/football_data/small_write',
        'approved_output_root: docs/_packets/football_data/other'
    );
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(
        payload.errors.join('\n'),
        /approved_output_root must stay inside docs\/_packets\/football_data\/small_write/
    );
});

test('approved_packet_sections 缺少必要 section 时失败', () => {
    const gate = loadValidatorFresh();
    const markdownText = removeLineFromTemplate('  - rollback_restore_preview');
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies(markdownText));

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /approved_packet_sections is missing required sections/);
    assert.ok(payload.approved_packet_sections_missing.includes('rollback_restore_preview'));
});

test('--commit 始终 blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--auth-form', 'auth.md', '--commit'], buildDependencies());

    assert.equal(result.status, 1);
    assert.match(
        result.stdout,
        /BLOCKED: football-data packet file creation authorization commit is not wired in Phase 4.71C/
    );
});

test('validator 不访问外网', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
});

test('validator 不读 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_read_db, false);
});

test('validator 不写 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_db, false);
});

test('validator 不写文件', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_files, false);
});

test('validator 不创建目录', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_create_packet_directory, false);
});

test('validator 不执行 pg_dump', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_dump, false);
});

test('validator 不执行 pg_restore', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_pg_restore, false);
});

test('validator 不 spawn child process', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation({ authForm: 'auth.md' }, buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});

test('script 作为真实入口执行 --help 应成功', () => {
    const result = spawnSync('node', [SCRIPT_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Usage:/);
    assert.match(result.stdout, /Phase 4\.71C validates a local packet file creation authorization template only/);
});
