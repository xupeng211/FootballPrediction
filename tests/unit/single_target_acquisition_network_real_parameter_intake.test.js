'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_target_acquisition_network_real_parameter_intake.js');
const INTAKE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md'
);
const BLOCKED_SUMMARY_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md'
);
const INTAKE_TEXT = fs.readFileSync(INTAKE_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        intake: INTAKE_PATH,
        blocked_summary: BLOCKED_SUMMARY_PATH,
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

function buildTextDependencies(markdownText, targetPath = INTAKE_PATH) {
    return buildDependencies({
        existsSync: currentPath => currentPath === targetPath || fs.existsSync(currentPath),
        readFileSync: (currentPath, encoding) => {
            if (currentPath === targetPath) return markdownText;
            return fs.readFileSync(currentPath, encoding);
        },
    });
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
        throw new Error(`${name} should not be called by single_target_acquisition_network_real_parameter_intake`);
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
        if (blockedImports.has(request)) throw new Error(`blocked import: ${request}`);
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
    assert.match(INTAKE_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return INTAKE_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return INTAKE_TEXT.replace(`${line}\n`, '');
}

function runMain(gate, argv, dependencies = buildDependencies()) {
    let stdout = '';
    const status = gate.main(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
        },
        dependencies
    );
    return { status, stdout };
}

function extractLastJsonObject(stdout) {
    const trimmed = String(stdout || '').trim();
    const startIndex = trimmed.lastIndexOf('\n{');
    const jsonText = startIndex >= 0 ? trimmed.slice(startIndex + 1) : trimmed;
    return JSON.parse(jsonText);
}

test('缺 intake 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.intake;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing intake/i);
});

test('缺 blocked summary 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.blocked_summary;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing blocked summary/i);
});

test('intake 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDependencies('# no yaml\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing YAML block/i);
});

test('intake invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDependencies('```yaml\nnot yaml\n```\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /invalid YAML/i);
});

test('missing phase 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            removeLineFromTemplate('phase: PHASE4_90D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing required fields: phase|phase must be/);
});

test('intake_status 非 template_only 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('intake_status: template_only', 'intake_status: ready'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /template_only/);
});

[
    [
        'real_parameters_provided=true 失败',
        'real_parameters_provided: false',
        'real_parameters_provided: true',
        /real_parameters_provided true/,
    ],
    [
        'network_dry_run_authorized=true 失败',
        'network_dry_run_authorized: false',
        'network_dry_run_authorized: true',
        /network_dry_run_authorized true/,
    ],
    [
        'network_dry_run_execution_allowed=true 失败',
        'network_dry_run_execution_allowed: false',
        'network_dry_run_execution_allowed: true',
        /network_dry_run_execution_allowed true/,
    ],
    [
        'staging_write_authorized=true 失败',
        'staging_write_authorized: false',
        'staging_write_authorized: true',
        /staging_write_authorized true/,
    ],
    [
        'db_write_authorized=true 失败',
        'db_write_authorized: false',
        'db_write_authorized: true',
        /db_write_authorized true/,
    ],
    [
        'training_authorized=true 失败',
        'training_authorized: false',
        'training_authorized: true',
        /training_authorized true/,
    ],
    [
        'prediction_authorized=true 失败',
        'prediction_authorized: false',
        'prediction_authorized: true',
        /prediction_authorized true/,
    ],
    [
        'final_human_confirmation=true 失败',
        'final_human_confirmation: false',
        'final_human_confirmation: true',
        /final_human_confirmation true/,
    ],
].forEach(([name, searchValue, replaceValue, pattern]) => {
    test(name, () => {
        const gate = loadValidatorFresh();
        const payload = gate.runValidation(
            buildArgs(),
            buildTextDependencies(replaceInTemplate(searchValue, replaceValue))
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

[
    [
        'real_target.target_source.provided=true 失败',
        'target_source:\n        required: true\n        provided: false',
        'target_source:\n        required: true\n        provided: true',
        /real_target\.target_source\.provided true/,
    ],
    [
        'real_target.target_scope_type.provided=true 失败',
        'target_scope_type:\n        required: true\n        provided: false',
        'target_scope_type:\n        required: true\n        provided: true',
        /real_target\.target_scope_type\.provided true/,
    ],
    [
        'source_terms.terms_url.provided=true 失败',
        'terms_url:\n        required: true\n        provided: false',
        'terms_url:\n        required: true\n        provided: true',
        /source_terms\.terms_url\.provided true/,
    ],
    [
        'network_authorization.network_dry_run_authorization.provided=true 失败',
        'network_dry_run_authorization:\n        required: true\n        provided: false',
        'network_dry_run_authorization:\n        required: true\n        provided: true',
        /network_authorization\.network_dry_run_authorization\.provided true/,
    ],
    [
        'proxy_browser_network_policy.proxy_policy.provided=true 失败',
        'proxy_policy:\n        required: true\n        provided: false',
        'proxy_policy:\n        required: true\n        provided: true',
        /proxy_browser_network_policy\.proxy_policy\.provided true/,
    ],
    [
        'staging_policy.output_root.provided=true 失败',
        'output_root:\n        required: true\n        provided: false',
        'output_root:\n        required: true\n        provided: true',
        /staging_policy\.output_root\.provided true/,
    ],
    [
        'no_db_training_prediction_policy.no_db_write_confirmation.provided=true 失败',
        'no_db_write_confirmation:\n        required: true\n        provided: false',
        'no_db_write_confirmation:\n        required: true\n        provided: true',
        /no_db_training_prediction_policy\.no_db_write_confirmation\.provided true/,
    ],
    [
        'final_human_confirmation.provided=true 失败',
        'final_human_confirmation:\n    required: true\n    provided: false',
        'final_human_confirmation:\n    required: true\n    provided: true',
        /final_human_confirmation\.provided true/,
    ],
].forEach(([name, searchValue, replaceValue, pattern]) => {
    test(name, () => {
        const gate = loadValidatorFresh();
        const payload = gate.runValidation(
            buildArgs(),
            buildTextDependencies(replaceInTemplate(searchValue, replaceValue))
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

test('bulk_scope_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('    bulk_scope_allowed: false', '    bulk_scope_allowed: true'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /bulk_scope_allowed true|bulk scope/i);
});

test('max_targets > 1 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('    max_targets: 1', '    max_targets: 2'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /max_targets > 1/i);
});

test('target_engine_family 不是 titan_discovery 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('        value: titan_discovery', '        value: run_production'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /target_engine_family not titan_discovery/);
});

test('safety would_access_network=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('    would_access_network: false', '    would_access_network: true'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /safety\.would_access_network/);
});

test('safety would_write_db=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('    would_write_db: false', '    would_write_db: true'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /safety\.would_write_db/);
});

test('safety would_write_real_parameter_intake_file=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate(
                '    would_write_real_parameter_intake_file: false',
                '    would_write_real_parameter_intake_file: true'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /safety\.would_write_real_parameter_intake_file/);
});

test('Codex self-filled real parameter 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('        value:\n', '        value: fotmob\n'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /Codex self-filled real parameter/);
});

test('valid intake preview 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.90D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE');
    assert.equal(payload.real_parameter_intake_template_only, true);
    assert.equal(payload.intake_valid, true);
    assert.equal(payload.blocked_summary_valid, true);
    assert.equal(payload.real_parameters_provided, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.final_human_confirmation, false);
    assert.deepEqual(payload.missing_parameter_groups, [
        'real_target',
        'source_terms',
        'network_authorization',
        'proxy_browser_network_policy',
        'staging_policy',
        'no_db_training_prediction_policy',
        'final_human_confirmation',
    ]);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_execute_engine, false);
    assert.equal(payload.would_execute_legacy_titan_discovery, false);
    assert.equal(payload.would_write_staging, false);
    assert.equal(payload.would_create_staging_directory, false);
    assert.equal(payload.would_write_source_manifest, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_approval_packet_file, false);
    assert.equal(payload.would_write_blocked_summary_file, false);
    assert.equal(payload.would_write_real_parameter_intake_file, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.would_spawn_child_process, false);
    assert.equal(payload.commit_gate, 'blocked');
});

test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(
        gate,
        ['--intake', INTAKE_PATH, '--blocked-summary', BLOCKED_SUMMARY_PATH, '--commit'],
        buildDependencies()
    );
    assert.equal(result.status, 1);
    const payload = JSON.parse(result.stdout);
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.90D/);
});

test('Makefile preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-real-parameter-intake-preview',
            'NETWORK_REAL_PARAMETER_INTAKE_NODE=node',
            `INTAKE=${INTAKE_PATH}`,
            `BLOCKED_SUMMARY=${BLOCKED_SUMMARY_PATH}`,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(result.status, 0, result.stderr);
    const payload = extractLastJsonObject(result.stdout);
    assert.equal(payload.ok, true);
    assert.equal(payload.intake_valid, true);
    assert.equal(payload.blocked_summary_valid, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-real-parameter-intake-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_INTAKE=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.90D/);
});

[
    ['不访问网络', 'would_access_network', false],
    ['不启动 browser', 'would_launch_browser', false],
    ['不执行 proxy runtime', 'would_use_proxy', false],
    ['不执行 engine', 'would_execute_engine', false],
    ['不执行 legacy titan_discovery', 'would_execute_legacy_titan_discovery', false],
    ['不写 staging', 'would_write_staging', false],
    ['不创建目录', 'would_create_staging_directory', false],
    ['不写 source manifest', 'would_write_source_manifest', false],
    ['不写 packet file', 'would_write_packet_file', false],
    ['不写 approval packet file', 'would_write_approval_packet_file', false],
    ['不写 blocked summary file', 'would_write_blocked_summary_file', false],
    ['不写 real parameter intake file', 'would_write_real_parameter_intake_file', false],
    ['不写 DB', 'would_write_db', false],
    ['不 spawn child process', 'would_spawn_child_process', false],
].forEach(([name, field, expected]) => {
    test(name, t => {
        installExecutionGuards(t);
        const gate = loadValidatorFresh();
        const payload = gate.runValidation(buildArgs(), buildDependencies());
        assert.equal(payload.ok, true);
        assert.equal(payload[field], expected);
    });
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
