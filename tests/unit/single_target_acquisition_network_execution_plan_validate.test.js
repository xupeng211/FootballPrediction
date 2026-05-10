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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_target_acquisition_network_execution_plan_validate.js');
const EXECUTION_PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md'
);
const CHECKLIST_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FINAL_READINESS_CHECKLIST_TEMPLATE.md'
);
const RUNBOOK_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md'
);
const AUTH_FORM_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md'
);
const EXECUTION_PLAN_TEXT = fs.readFileSync(EXECUTION_PLAN_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        execution_plan: EXECUTION_PLAN_PATH,
        checklist: CHECKLIST_PATH,
        runbook: RUNBOOK_PATH,
        auth_form: AUTH_FORM_PATH,
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
        throw new Error(`${name} should not be called by single_target_acquisition_network_execution_plan_validate`);
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
    assert.match(EXECUTION_PLAN_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return EXECUTION_PLAN_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return EXECUTION_PLAN_TEXT.replace(`${line}\n`, '');
}

function withTempExecutionPlan(markdownText, callback) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phase486d-'));
    const executionPlanPath = path.join(tempDir, 'execution-plan.md');
    fs.writeFileSync(executionPlanPath, markdownText, 'utf8');
    try {
        callback(executionPlanPath);
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }
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

test('缺 execution plan 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.execution_plan;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing execution plan/i);
});

test('缺 checklist 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.checklist;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing checklist/i);
});

test('缺 runbook 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.runbook;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing runbook/i);
});

test('缺 auth form 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.auth_form;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing auth form/i);
});

test('execution plan 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan('# no yaml\n', executionPlanPath => {
        const payload = gate.runValidation({ ...buildArgs(), execution_plan: executionPlanPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /missing YAML block/i);
    });
});

test('execution plan invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan('```yaml\nnot yaml\n```\n', executionPlanPath => {
        const payload = gate.runValidation({ ...buildArgs(), execution_plan: executionPlanPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /invalid YAML/i);
    });
});

test('missing phase 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(
        removeLineFromTemplate('phase: PHASE4.86D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_DRAFT'),
        executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /missing required fields: phase/);
        }
    );
});

test('execution_plan_status 非 draft_only 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(
        replaceInTemplate('execution_plan_status: draft_only', 'execution_plan_status: approved'),
        executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /draft_only/);
        }
    );
});

[
    [
        'network_dry_run_execution_allowed=true 失败',
        'network_dry_run_execution_allowed: false',
        'network_dry_run_execution_allowed: true',
        /network_dry_run_execution_allowed true/,
    ],
    [
        'network_dry_run_authorized=true 失败',
        'network_dry_run_authorized: false',
        'network_dry_run_authorized: true',
        /network_dry_run_authorized true/,
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
        withTempExecutionPlan(replaceInTemplate(searchValue, replaceValue), executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), pattern);
        });
    });
});

test('任一 execution_steps.execution_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(
        replaceInTemplate('      execution_allowed: false', '      execution_allowed: true'),
        executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /execution step allowed true/);
        }
    );
});

test('stop gate missing 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(removeLineFromTemplate('    terms_not_approved: true'), executionPlanPath => {
        const payload = gate.runValidation({ ...buildArgs(), execution_plan: executionPlanPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /stop gate missing|stop_gates\.terms_not_approved/);
    });
});

test('stop gate disabled 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(
        replaceInTemplate('    network_not_authorized: true', '    network_not_authorized: false'),
        executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /stop gate disabled/);
        }
    );
});

test('bulk_scope_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(
        replaceInTemplate('    bulk_scope_allowed: false', '    bulk_scope_allowed: true'),
        executionPlanPath => {
            const payload = gate.runValidation(
                { ...buildArgs(), execution_plan: executionPlanPath },
                buildDependencies()
            );
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /bulk scope allowed/i);
        }
    );
});

test('max_targets > 1 失败', () => {
    const gate = loadValidatorFresh();
    withTempExecutionPlan(replaceInTemplate('    max_targets: 1', '    max_targets: 2'), executionPlanPath => {
        const payload = gate.runValidation({ ...buildArgs(), execution_plan: executionPlanPath }, buildDependencies());
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
    withTempExecutionPlan(replaceInTemplate('    target_source:', '    target_source: other'), executionPlanPath => {
        const payload = gate.runValidation({ ...buildArgs(), execution_plan: executionPlanPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /target mismatch/i);
    });
});

test('valid execution plan validate 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.86D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_DRAFT');
    assert.equal(payload.execution_plan_draft_only, true);
    assert.equal(payload.execution_plan_valid, true);
    assert.equal(payload.readiness_checklist_valid, true);
    assert.equal(payload.runbook_template_valid, true);
    assert.equal(payload.auth_form_template_valid, true);
    assert.equal(payload.network_dry_run_execution_allowed, false);
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

test('all CLI yes 仍 no-op / execution not allowed', () => {
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
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_db, false);
});

test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(
        gate,
        [
            '--execution-plan',
            EXECUTION_PLAN_PATH,
            '--checklist',
            CHECKLIST_PATH,
            '--runbook',
            RUNBOOK_PATH,
            '--auth-form',
            AUTH_FORM_PATH,
            '--commit',
        ],
        buildDependencies()
    );
    assert.equal(result.status, 1);
    const payload = JSON.parse(result.stdout);
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.86D/);
});

test('Makefile validate 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-execution-plan-validate',
            'NETWORK_EXECUTION_PLAN_NODE=node',
            `EXECUTION_PLAN=${EXECUTION_PLAN_PATH}`,
            `CHECKLIST=${CHECKLIST_PATH}`,
            `RUNBOOK=${RUNBOOK_PATH}`,
            `AUTH_FORM=${AUTH_FORM_PATH}`,
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
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(result.status, 0, result.stderr);
    const payload = extractLastJsonObject(result.stdout);
    assert.equal(payload.ok, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-execution-plan-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_EXECUTION_PLAN=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.86D/);
});

[
    ['不访问网络', 'would_access_network', false],
    ['不启动 browser', 'would_launch_browser', false],
    ['不执行 proxy runtime', 'would_use_proxy', false],
    ['不执行 engine', 'would_execute_engine', false],
    ['不写 staging', 'would_write_staging', false],
    ['不创建目录', 'would_create_staging_directory', false],
    ['不写 source manifest', 'would_write_source_manifest', false],
    ['不写 packet file', 'would_write_packet_file', false],
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
