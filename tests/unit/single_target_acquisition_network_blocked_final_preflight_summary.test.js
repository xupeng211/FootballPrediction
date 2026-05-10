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
    'scripts/ops/single_target_acquisition_network_blocked_final_preflight_summary.js'
);
const BLOCKED_SUMMARY_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md'
);
const INPUT_CLOSURE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_USER_INPUT_REQUIREMENTS_CLOSURE_TEMPLATE.md'
);
const APPROVAL_PACKET_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_HUMAN_APPROVAL_PACKET_TEMPLATE.md'
);
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
const BLOCKED_SUMMARY_TEXT = fs.readFileSync(BLOCKED_SUMMARY_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        blocked_summary: BLOCKED_SUMMARY_PATH,
        input_closure: INPUT_CLOSURE_PATH,
        approval_packet: APPROVAL_PACKET_PATH,
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

function buildSummaryTextDependencies(markdownText) {
    const targetPath = BLOCKED_SUMMARY_PATH;
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
            `${name} should not be called by single_target_acquisition_network_blocked_final_preflight_summary`
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
    assert.match(BLOCKED_SUMMARY_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return BLOCKED_SUMMARY_TEXT.replace(searchValue, replaceValue);
}

function replaceInSection(sectionName, searchValue, replaceValue) {
    const sectionHeader = `${sectionName}:\n`;
    const startIndex = BLOCKED_SUMMARY_TEXT.indexOf(sectionHeader);
    assert.notEqual(startIndex, -1, `missing section ${sectionName}`);
    const nextSectionMatch = BLOCKED_SUMMARY_TEXT.slice(startIndex + sectionHeader.length).match(/\n[A-Za-z0-9_]+:\n/);
    const endIndex =
        nextSectionMatch && typeof nextSectionMatch.index === 'number'
            ? startIndex + sectionHeader.length + nextSectionMatch.index
            : BLOCKED_SUMMARY_TEXT.length;
    const sectionText = BLOCKED_SUMMARY_TEXT.slice(startIndex, endIndex);
    assert.match(sectionText, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return `${BLOCKED_SUMMARY_TEXT.slice(0, startIndex)}${sectionText.replace(searchValue, replaceValue)}${BLOCKED_SUMMARY_TEXT.slice(endIndex)}`;
}

function removeLineFromTemplate(line) {
    return BLOCKED_SUMMARY_TEXT.replace(`${line}\n`, '');
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

test('缺 blocked summary 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.blocked_summary;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing blocked summary/i);
});

test('缺 input closure 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.input_closure;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing input closure/i);
});

test('缺 approval packet 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.approval_packet;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing approval packet/i);
});

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

test('blocked summary 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildSummaryTextDependencies('# no yaml\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing YAML block/i);
});

test('blocked summary invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildSummaryTextDependencies('```yaml\nnot yaml\n```\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /invalid YAML/i);
});

test('missing phase 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            removeLineFromTemplate(
                'phase: PHASE4_89D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing required fields: phase|phase must be/);
});

test('summary_status 非 blocked_preview_only 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(replaceInTemplate('summary_status: blocked_preview_only', 'summary_status: ready'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /blocked_preview_only/);
});

test('network_dry_run_blocked=false 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            replaceInTemplate('network_dry_run_blocked: true', 'network_dry_run_blocked: false')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /network_dry_run_blocked false/);
});

[
    [
        'network_dry_run_ready=true 失败',
        'network_dry_run_ready: false',
        'network_dry_run_ready: true',
        /network_dry_run_ready true/,
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
        'human_approval_packet_ready=true 失败',
        'human_approval_packet_ready: false',
        'human_approval_packet_ready: true',
        /human_approval_packet_ready true/,
    ],
    [
        'user_inputs_complete=true 失败',
        'user_inputs_complete: false',
        'user_inputs_complete: true',
        /user_inputs_complete true/,
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
            buildSummaryTextDependencies(replaceInTemplate(searchValue, replaceValue))
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

test('missing_user_inputs missing 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(removeLineFromTemplate('    - real_target_source'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing_user_inputs missing required value|missing_user_inputs missing/);
});

test('blocking_summary missing 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(removeLineFromTemplate('blocking_summary:'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /blocking_summary/);
});

test('primary_reason 非 missing_user_supplied_real_network_dry_run_inputs 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            replaceInTemplate(
                'primary_reason: missing_user_supplied_real_network_dry_run_inputs',
                'primary_reason: ready'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /primary_reason/);
});

test('codex_may_not_self_fill_inputs=false 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            replaceInTemplate('codex_may_not_self_fill_inputs: true', 'codex_may_not_self_fill_inputs: false')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /codex_may_not_self_fill_inputs/);
});

test('codex_may_not_escalate_authorization=false 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            replaceInTemplate(
                'codex_may_not_escalate_authorization: true',
                'codex_may_not_escalate_authorization: false'
            )
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /codex_may_not_escalate_authorization/);
});

test('bulk_scope_allowed=true 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(
            replaceInSection('target', '    bulk_scope_allowed: false', '    bulk_scope_allowed: true')
        )
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /bulk scope allowed/i);
});

test('max_targets > 1 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(replaceInSection('target', '    max_targets: 1', '    max_targets: 2'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /max_targets > 1/i);
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
    const payload = gate.runValidation(
        buildArgs(),
        buildSummaryTextDependencies(replaceInSection('target', '    target_source:', '    target_source: other'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /target mismatch/i);
});

test('valid blocked final preflight summary 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.89D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY');
    assert.equal(payload.blocked_final_preflight_summary_preview_only, true);
    assert.equal(payload.blocked_summary_valid, true);
    assert.equal(payload.input_closure_valid, true);
    assert.equal(payload.approval_packet_valid, true);
    assert.equal(payload.execution_plan_valid, true);
    assert.equal(payload.readiness_checklist_valid, true);
    assert.equal(payload.runbook_template_valid, true);
    assert.equal(payload.auth_form_template_valid, true);
    assert.equal(payload.network_dry_run_blocked, true);
    assert.equal(payload.network_dry_run_ready, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.human_approval_packet_ready, false);
    assert.equal(payload.user_inputs_complete, false);
    assert.equal(payload.primary_blocking_reason, 'missing_user_supplied_real_network_dry_run_inputs');
    assert.deepEqual(payload.missing_user_inputs, [
        'real_target_source',
        'real_single_target_scope',
        'source_terms',
        'license_review',
        'allowed_use_review',
        'network_authorization',
        'external_network_policy',
        'browser_runtime_policy',
        'proxy_runtime_policy',
        'staging_policy',
        'no_db_write_confirmation',
        'no_training_confirmation',
        'no_prediction_confirmation',
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
    assert.equal(payload.would_write_user_input_closure_file, false);
    assert.equal(payload.would_write_blocked_summary_file, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.would_spawn_child_process, false);
    assert.equal(payload.commit_gate, 'blocked');
});

test('all CLI yes 仍 blocked / inputs incomplete / not authorized', () => {
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
    assert.equal(payload.network_dry_run_blocked, true);
    assert.equal(payload.user_inputs_complete, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_write_blocked_summary_file, false);
});

test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(
        gate,
        [
            '--blocked-summary',
            BLOCKED_SUMMARY_PATH,
            '--input-closure',
            INPUT_CLOSURE_PATH,
            '--approval-packet',
            APPROVAL_PACKET_PATH,
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
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.89D/);
});

test('Makefile summary preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-blocked-final-preflight-summary',
            'NETWORK_BLOCKED_PREFLIGHT_NODE=node',
            `BLOCKED_SUMMARY=${BLOCKED_SUMMARY_PATH}`,
            `INPUT_CLOSURE=${INPUT_CLOSURE_PATH}`,
            `APPROVAL_PACKET=${APPROVAL_PACKET_PATH}`,
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
    assert.equal(payload.blocked_summary_valid, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-blocked-final-preflight-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_BLOCKED_FINAL_PREFLIGHT=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.89D/);
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
    ['不写 user input closure file', 'would_write_user_input_closure_file', false],
    ['不写 blocked summary file', 'would_write_blocked_summary_file', false],
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
