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
const SCRIPT_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/single_target_acquisition_network_real_parameter_intake_validation_closure.js'
);
const VALIDATION_CLOSURE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md'
);
const INTAKE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md'
);
const BLOCKED_SUMMARY_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md'
);
const VALIDATION_CLOSURE_TEXT = fs.readFileSync(VALIDATION_CLOSURE_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        validation_closure: VALIDATION_CLOSURE_PATH,
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

function buildTextDependencies(markdownText, targetPath = VALIDATION_CLOSURE_PATH) {
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
        throw new Error(
            `${name} should not be called by single_target_acquisition_network_real_parameter_intake_validation_closure`
        );
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
    assert.match(VALIDATION_CLOSURE_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return VALIDATION_CLOSURE_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return VALIDATION_CLOSURE_TEXT.replace(`${line}\n`, '');
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

test('缺 validation closure 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.validation_closure;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing validation closure/i);
});

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

test('validation closure 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDependencies('# no yaml\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing YAML block/i);
});

test('validation closure invalid YAML 失败', () => {
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
            removeLineFromTemplate(
                'phase: PHASE4_91D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing required fields: phase|phase must be/);
});

test('validation_closure_status 非 template_only 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate('validation_closure_status: template_only', 'validation_closure_status: ready')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /validation_closure_status not template_only|template_only/);
});

[
    [
        'real_parameter_intake_validation_ready=true 失败',
        'real_parameter_intake_validation_ready: false',
        'real_parameter_intake_validation_ready: true',
        /real_parameter_intake_validation_ready true/,
    ],
    [
        'real_parameter_intake_validated=true 失败',
        'real_parameter_intake_validated: false',
        'real_parameter_intake_validated: true',
        /real_parameter_intake_validated true/,
    ],
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
    'real_target_validation',
    'source_terms_validation',
    'network_authorization_validation',
    'staging_policy_validation',
    'no_db_training_prediction_validation',
    'final_human_confirmation_validation',
].forEach(groupName => {
    test(`validation_rule_groups.${groupName}.validation_passed=true 失败`, () => {
        const gate = loadValidatorFresh();
        const payload = gate.runValidation(
            buildArgs(),
            buildTextDependencies(
                replaceInTemplate(
                    `${groupName}:\n        required: true\n        rule_complete: true\n        validation_passed: false`,
                    `${groupName}:\n        required: true\n        rule_complete: true\n        validation_passed: true`
                )
            )
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), new RegExp(`${groupName}\\.validation_passed true`));
    });
});

test('codex_may_not_self_fill_real_parameters=false 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate(
                '    codex_may_not_self_fill_real_parameters: true',
                '    codex_may_not_self_fill_real_parameters: false'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /codex_may_not_self_fill_real_parameters false/);
});

test('codex_may_not_mark_validation_passed=false 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate(
                '    codex_may_not_mark_validation_passed: true',
                '    codex_may_not_mark_validation_passed: false'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /codex_may_not_mark_validation_passed false/);
});

test('validation_blocking_reasons missing 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('validation_blocking_reasons:', 'validation_blocking_reasons_missing:'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing validation_blocking_reasons|validation_blocking_reasons/);
});

test('validation rule group missing 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('    real_target_validation:', '    real_target_validation_missing:'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing validation rule group: real_target_validation/);
});

test('bulk_scope_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate('        bulk_scope_allowed: false', '        bulk_scope_allowed: true')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /bulk_scope_allowed true/);
});

test('max_targets > 1 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(replaceInTemplate('        max_targets: 1', '        max_targets: 2'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /max_targets > 1/);
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

test('safety would_write_real_parameter_validation_closure_file=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDependencies(
            replaceInTemplate(
                '    would_write_real_parameter_validation_closure_file: false',
                '    would_write_real_parameter_validation_closure_file: true'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /safety\.would_write_real_parameter_validation_closure_file/);
});

test('valid validation closure preview 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(
        payload.phase,
        'PHASE4.91D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE'
    );
    assert.equal(payload.validation_closure_template_only, true);
    assert.equal(payload.validation_closure_valid, true);
    assert.equal(payload.real_parameter_intake_valid, true);
    assert.equal(payload.blocked_summary_valid, true);
    assert.equal(payload.real_parameter_intake_validation_ready, false);
    assert.equal(payload.real_parameter_intake_validated, false);
    assert.equal(payload.real_parameters_provided, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.validation_rule_groups_complete, true);
    assert.equal(payload.validation_rule_groups_passed, false);
    assert.deepEqual(payload.validation_blocking_reasons, [
        'real_parameters_not_provided',
        'real_target_not_validated',
        'source_terms_not_validated',
        'network_authorization_not_validated',
        'staging_policy_not_validated',
        'no_db_training_prediction_policy_not_validated',
        'final_human_confirmation_not_validated',
        'future_separate_phase_required',
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
    assert.equal(payload.would_write_real_parameter_validation_closure_file, false);
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
        [
            '--validation-closure',
            VALIDATION_CLOSURE_PATH,
            '--intake',
            INTAKE_PATH,
            '--blocked-summary',
            BLOCKED_SUMMARY_PATH,
            '--commit',
        ],
        buildDependencies()
    );
    assert.equal(result.status, 1);
    const payload = JSON.parse(result.stdout);
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.91D/);
});

test('Makefile preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-real-parameter-validation-closure-preview',
            'NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE_NODE=node',
            `VALIDATION_CLOSURE=${VALIDATION_CLOSURE_PATH}`,
            `INTAKE=${INTAKE_PATH}`,
            `BLOCKED_SUMMARY=${BLOCKED_SUMMARY_PATH}`,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(result.status, 0, result.stderr);
    const payload = extractLastJsonObject(result.stdout);
    assert.equal(payload.ok, true);
    assert.equal(payload.validation_closure_valid, true);
    assert.equal(payload.real_parameter_intake_valid, true);
    assert.equal(payload.blocked_summary_valid, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-real-parameter-validation-closure-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.91D/);
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
    ['不写 validation closure file', 'would_write_real_parameter_validation_closure_file', false],
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
    assert.ok(!/require\s*\(\s*['"](?:node:)?child_process['"]/.test(source));
});
