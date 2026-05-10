'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_target_acquisition_network_auth_form_validate.js');
const AUTH_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md'
);
const RUNBOOK_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md'
);
const AUTH_FORM_TEXT = fs.readFileSync(AUTH_FORM_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        auth_form: AUTH_FORM_PATH,
        runbook: RUNBOOK_PATH,
        target_source: 'fotmob',
        target_engine_family: 'titan_discovery',
        target_scope_type: 'match_id',
        target_match_id: 'sample-match-001',
        terms_approval: 'no',
        network_dry_run_authorization: 'no',
        allow_browser_runtime: 'no',
        allow_proxy_runtime: 'no',
        allow_external_network: 'no',
        allow_staging_write: 'no',
        final_human_confirmation: 'no',
        ...overrides,
    };
}

function buildDependencies(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: targetPath => fs.existsSync(targetPath),
        readFileSync: (targetPath, encoding) => fs.readFileSync(targetPath, encoding),
        ...overrides,
    };
}

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
    const originalNetConnect = net.connect;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by single_target_acquisition_network_auth_form_validate`);
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
    net.connect = fail('net.connect');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
        ]);
        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/titan_discovery|DiscoveryService|FixtureRepository/i.test(request)) {
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
        net.connect = originalNetConnect;
        Module._load = originalLoad;
    });
}

function replaceInTemplate(searchValue, replaceValue) {
    assert.match(AUTH_FORM_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return AUTH_FORM_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return AUTH_FORM_TEXT.replace(`${line}\n`, '');
}

function withTempAuthForm(markdownText, callback) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phase484d-'));
    const authFormPath = path.join(tempDir, 'auth-form.md');
    fs.writeFileSync(authFormPath, markdownText, 'utf8');
    try {
        callback(authFormPath);
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }
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
    return { status, stdout, stderr };
}

function extractLastJsonObject(stdout) {
    const trimmed = String(stdout || '').trim();
    const startIndex = trimmed.lastIndexOf('\n{');
    const jsonText = startIndex >= 0 ? trimmed.slice(startIndex + 1) : trimmed;
    return JSON.parse(jsonText);
}

test('缺 auth form 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.auth_form;
    const payload = gate.runValidation(args, buildDependencies());

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing auth form/i);
});

test('缺 runbook 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.runbook;
    const payload = gate.runValidation(args, buildDependencies());

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing runbook/i);
});

test('auth form 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm('# no yaml\n', authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /missing YAML block/i);
    });
});

test('auth form invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm('```yaml\nnot yaml\n```\n', authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /invalid YAML/i);
    });
});

test('missing phase 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(
        removeLineFromTemplate('phase: PHASE4.84D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM'),
        authFormPath => {
            const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /missing required fields: phase/);
        }
    );
});

test('authorization_form_status 非 template_only 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(
        replaceInTemplate('authorization_form_status: template_only', 'authorization_form_status: approved'),
        authFormPath => {
            const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /template_only/);
        }
    );
});

test('network_dry_run_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(
        replaceInTemplate('network_dry_run_authorized: false', 'network_dry_run_authorized: true'),
        authFormPath => {
            const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /network_dry_run_authorized true/);
        }
    );
});

test('staging_write_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(
        replaceInTemplate('staging_write_authorized: false', 'staging_write_authorized: true'),
        authFormPath => {
            const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /staging_write_authorized true/);
        }
    );
});

test('db_write_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('db_write_authorized: false', 'db_write_authorized: true'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /db_write_authorized true/);
    });
});

test('training_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('training_authorized: false', 'training_authorized: true'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /training_authorized true/);
    });
});

test('prediction_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('prediction_authorized: false', 'prediction_authorized: true'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /prediction_authorized true/);
    });
});

test('final_human_confirmation=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(
        replaceInTemplate('final_human_confirmation: false', 'final_human_confirmation: true'),
        authFormPath => {
            const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /final_human_confirmation true/);
        }
    );
});

test('bulk_scope_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('bulk_scope_allowed: false', 'bulk_scope_allowed: true'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /bulk scope allowed/i);
    });
});

test('max_targets > 1 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('max_targets: 1', 'max_targets: 2'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /max_targets > 1/i);
    });
});

test('unsupported engine family 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs({ target_engine_family: 'run_production' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unsupported engine family/);
});

test('unsupported scope type bulk 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs({ target_scope_type: 'bulk' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unsupported scope type "bulk"|unsupported scope type bulk/);
});

test('target mismatch 失败', () => {
    const gate = loadValidatorFresh();
    withTempAuthForm(replaceInTemplate('    target_source:', '    target_source: other'), authFormPath => {
        const payload = gate.runValidation({ ...buildArgs(), auth_form: authFormPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /target mismatch/i);
    });
});

test('valid auth form validate 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.84D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM');
    assert.equal(payload.authorization_form_template_only, true);
    assert.equal(payload.auth_form_valid, true);
    assert.equal(payload.runbook_template_valid, true);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_execute_engine, false);
    assert.equal(payload.would_write_staging, false);
    assert.equal(payload.would_create_staging_directory, false);
    assert.equal(payload.would_write_source_manifest, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.would_spawn_child_process, false);
    assert.equal(payload.commit_gate, 'blocked');
});

test('all CLI yes 仍 no-op / not authorized', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs({
            terms_approval: 'yes',
            network_dry_run_authorization: 'yes',
            allow_browser_runtime: 'yes',
            allow_proxy_runtime: 'yes',
            allow_external_network: 'yes',
            allow_staging_write: 'yes',
            final_human_confirmation: 'yes',
        }),
        buildDependencies()
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_execute_engine, false);
    assert.equal(payload.would_write_staging, false);
    assert.equal(payload.would_write_db, false);
});

test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(
        gate,
        ['--auth-form', AUTH_FORM_PATH, '--runbook', RUNBOOK_PATH, '--commit'],
        buildDependencies()
    );

    assert.equal(result.status, 1);
    const payload = JSON.parse(result.stdout);
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.84D/);
});

test('Makefile validate 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-auth-form-validate',
            'NETWORK_AUTH_FORM_NODE=node',
            `AUTH_FORM=${AUTH_FORM_PATH}`,
            `RUNBOOK=${RUNBOOK_PATH}`,
            'TARGET_SOURCE=fotmob',
            'TARGET_ENGINE_FAMILY=titan_discovery',
            'TARGET_SCOPE_TYPE=match_id',
            'TARGET_MATCH_ID=sample-match-001',
            'TERMS_APPROVAL=no',
            'NETWORK_DRY_RUN_AUTHORIZATION=no',
            'ALLOW_BROWSER_RUNTIME=no',
            'ALLOW_PROXY_RUNTIME=no',
            'ALLOW_EXTERNAL_NETWORK=no',
            'ALLOW_STAGING_WRITE=no',
            'FINAL_HUMAN_CONFIRMATION=no',
        ],
        {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
            shell: false,
        }
    );

    assert.equal(result.status, 0, result.stderr);
    const payload = extractLastJsonObject(result.stdout);
    assert.equal(payload.ok, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-auth-form-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTH_FORM=1',
        ],
        {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
            shell: false,
        }
    );

    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.84D/);
});

test('不访问网络', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
});

test('不启动 browser', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_launch_browser, false);
});

test('不执行 proxy runtime', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_use_proxy, false);
});

test('不执行 engine', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_engine, false);
});

test('不写 staging', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_staging, false);
});

test('不创建目录', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_create_staging_directory, false);
});

test('不写 source manifest', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_source_manifest, false);
});

test('不写 packet file', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_packet_file, false);
});

test('不写 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_db, false);
});

test('不 spawn child process', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});

test('source audit: 不 import forbidden modules', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(source));
    assert.ok(!/require\s*\(\s*['"].*DiscoveryService/.test(source));
    assert.ok(!/require\s*\(\s*['"].*FixtureRepository/.test(source));
    assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]redis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]ioredis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]playwright/.test(source));
});
