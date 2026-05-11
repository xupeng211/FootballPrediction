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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_target_acquisition_network_authorization_decision.js');
const AD_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION_TEMPLATE.md'
);
const HC_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST_TEMPLATE.md'
);
const RR_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT_TEMPLATE.md'
);
const RP_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md'
);
const INTAKE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md'
);
const VC_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md'
);
const BS_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md'
);
const AD_TEXT = fs.readFileSync(AD_PATH, 'utf8');

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        authorization_decision: AD_PATH,
        handoff_checklist: HC_PATH,
        review_result: RR_PATH,
        review_plan: RP_PATH,
        intake: INTAKE_PATH,
        validation_closure: VC_PATH,
        blocked_summary: BS_PATH,
        ...overrides,
    };
}

function buildDeps(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: p => fs.existsSync(p),
        readFileSync: (p, encoding) => fs.readFileSync(p, encoding),
        ...overrides,
    };
}

function buildTextDeps(text, targetPath = AD_PATH) {
    return buildDeps({
        existsSync: p => p === targetPath || fs.existsSync(p),
        readFileSync: (p, encoding) => {
            if (p === targetPath) return text;
            return fs.readFileSync(p, encoding);
        },
    });
}

function installGuards(t) {
    const original = {
        http: http.request,
        https: https.request,
        fetch: global.fetch,
        spawn: childProcess.spawn,
        exec: childProcess.exec,
        execFile: childProcess.execFile,
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        createWriteStream: fs.createWriteStream,
        mkdir: fs.mkdir,
        mkdirSync: fs.mkdirSync,
        net: net.connect,
        load: Module._load,
    };
    const fail = name => () => {
        throw new Error(name + ' should not be called');
    };

    http.request = fail('http');
    https.request = fail('https');
    global.fetch = fail('fetch');
    childProcess.spawn = fail('spawn');
    childProcess.exec = fail('exec');
    childProcess.execFile = fail('execFile');
    fs.writeFile = fail('writeFile');
    fs.writeFileSync = fail('writeFileSync');
    fs.createWriteStream = fail('createWriteStream');
    fs.mkdir = fail('mkdir');
    fs.mkdirSync = fail('mkdirSync');
    net.connect = fail('net');
    Module._load = function guardedLoad(request, parent, isMain) {
        if (
            new Set([
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
            ]).has(request)
        ) {
            throw new Error('blocked: ' + request);
        }
        if (/titan_discovery|DiscoveryService|FixtureRepository/i.test(request)) {
            throw new Error('blocked: ' + request);
        }
        return original.load.call(this, request, parent, isMain);
    };

    t.after(() => {
        Object.assign(http, { request: original.http });
        Object.assign(https, { request: original.https });
        global.fetch = original.fetch;
        Object.assign(childProcess, { spawn: original.spawn, exec: original.exec, execFile: original.execFile });
        Object.assign(fs, {
            writeFile: original.writeFile,
            writeFileSync: original.writeFileSync,
            createWriteStream: original.createWriteStream,
            mkdir: original.mkdir,
            mkdirSync: original.mkdirSync,
        });
        net.connect = original.net;
        Module._load = original.load;
    });
}

function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function replaceInDecision(search, replacement) {
    assert.match(AD_TEXT, new RegExp(escapeRegExp(search)));
    return AD_TEXT.replace(search, replacement);
}

function removeLine(line) {
    return AD_TEXT.replace(line + '\n', '');
}

function replaceSectionField(sectionName, fieldName, replacementValue) {
    const regex = new RegExp('(' + escapeRegExp(sectionName) + ':[\\s\\S]*?' + escapeRegExp(fieldName) + ': )[^\\n]+');
    const modified = AD_TEXT.replace(regex, '$1' + replacementValue);
    assert.notEqual(modified, AD_TEXT, sectionName + '.' + fieldName + ' should be modified');
    return modified;
}

function runMain(gate, argv, deps = buildDeps()) {
    let stdout = '';
    const status = gate.main(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
        },
        deps
    );
    return { status, stdout };
}

function extractJson(stdout) {
    const text = String(stdout || '').trim();
    const index = text.lastIndexOf('\n{');
    return JSON.parse(index >= 0 ? text.slice(index + 1) : text);
}

[
    ['authorization_decision', 'authorization decision'],
    ['handoff_checklist', 'handoff checklist'],
    ['review_result', 'review result'],
    ['review_plan', 'review plan'],
    ['intake', 'intake'],
    ['validation_closure', 'validation closure'],
    ['blocked_summary', 'blocked summary'],
].forEach(([field, label]) => {
    test('缺 ' + label + ' 失败', () => {
        const gate = loadFresh();
        const args = buildArgs();
        delete args[field];
        const payload = gate.runValidation(args, buildDeps());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), new RegExp('missing ' + label, 'i'));
    });
});

test('authorization decision 缺 YAML block 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDeps('# no yaml\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing YAML block/i);
});

test('authorization decision invalid YAML 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDeps('```yaml\nnot yaml\n```\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /invalid YAML/i);
});

test('missing phase 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDeps(removeLine('phase: PHASE4_95D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing required fields: phase|phase must be/);
});

[
    [
        'authorization_decision_status 非 template_only 失败',
        'authorization_decision_status: template_only',
        'authorization_decision_status: ready',
        /authorization_decision_status not template_only/,
    ],
    [
        'network_authorization_decision_ready=true 失败',
        'network_authorization_decision_ready: false',
        'network_authorization_decision_ready: true',
        /network_authorization_decision_ready true/,
    ],
    [
        'network_authorization_decision_recorded=true 失败',
        'network_authorization_decision_recorded: false',
        'network_authorization_decision_recorded: true',
        /network_authorization_decision_recorded true/,
    ],
    [
        'authorization_decision 不是 not_authorized 失败',
        'authorization_decision: not_authorized',
        'authorization_decision: conditionally_authorized_for_future_preparation',
        /authorization_decision not not_authorized/,
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
        'authorization_decision_is_not_execution=false 失败',
        'authorization_decision_is_not_execution: true',
        'authorization_decision_is_not_execution: false',
        /authorization_decision_is_not_execution/,
    ],
    [
        'future_execution_preparation_phase_required=false 失败',
        'future_execution_preparation_phase_required: true',
        'future_execution_preparation_phase_required: false',
        /future_execution_preparation_phase_required/,
    ],
    [
        'future_final_confirmation_required=false 失败',
        'future_final_confirmation_required: true',
        'future_final_confirmation_required: false',
        /future_final_confirmation_required/,
    ],
    [
        'can_proceed_to_network_dry_run_preparation=true 失败',
        'can_proceed_to_network_dry_run_preparation: false',
        'can_proceed_to_network_dry_run_preparation: true',
        /can_proceed_to_network_dry_run_preparation true/,
    ],
].forEach(([name, search, replacement, pattern]) => {
    test(name, () => {
        const gate = loadFresh();
        const payload = gate.runValidation(buildArgs(), buildTextDeps(replaceInDecision(search, replacement)));
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

[
    [
        'decision_sections.scope_decision.reviewed=true 失败',
        'scope_decision',
        'reviewed',
        'true',
        /scope_decision.*reviewed/,
    ],
    [
        'decision_sections.scope_decision.decision 不是 not_authorized 失败',
        'scope_decision',
        'decision',
        'denied',
        /scope_decision.*decision not not_authorized/,
    ],
    [
        'decision_sections.source_terms_decision.reviewed=true 失败',
        'source_terms_decision',
        'reviewed',
        'true',
        /source_terms_decision.*reviewed/,
    ],
    [
        'decision_sections.source_terms_decision.decision 不是 not_authorized 失败',
        'source_terms_decision',
        'decision',
        'needs_revision',
        /source_terms_decision.*decision not not_authorized/,
    ],
    [
        'decision_sections.network_runtime_decision.reviewed=true 失败',
        'network_runtime_decision',
        'reviewed',
        'true',
        /network_runtime_decision.*reviewed/,
    ],
    [
        'decision_sections.network_runtime_decision.decision 不是 not_authorized 失败',
        'network_runtime_decision',
        'decision',
        'denied',
        /network_runtime_decision.*decision not not_authorized/,
    ],
    [
        'decision_sections.network_runtime_decision.external_network_allowed=true 失败',
        'network_runtime_decision',
        'external_network_allowed',
        'true',
        /external_network_allowed true/,
    ],
    [
        'decision_sections.network_runtime_decision.browser_runtime_allowed=true 失败',
        'network_runtime_decision',
        'browser_runtime_allowed',
        'true',
        /browser_runtime_allowed true/,
    ],
    [
        'decision_sections.network_runtime_decision.proxy_runtime_allowed=true 失败',
        'network_runtime_decision',
        'proxy_runtime_allowed',
        'true',
        /proxy_runtime_allowed true/,
    ],
    [
        'decision_sections.staging_decision.reviewed=true 失败',
        'staging_decision',
        'reviewed',
        'true',
        /staging_decision.*reviewed/,
    ],
    [
        'decision_sections.staging_decision.staging_write_allowed=true 失败',
        'staging_decision',
        'staging_write_allowed',
        'true',
        /staging_write_allowed true/,
    ],
    [
        'decision_sections.staging_decision.source_manifest_write_allowed=true 失败',
        'staging_decision',
        'source_manifest_write_allowed',
        'true',
        /source_manifest_write_allowed true/,
    ],
    [
        'decision_sections.db_training_prediction_decision.db_write_allowed=true 失败',
        'db_training_prediction_decision',
        'db_write_allowed',
        'true',
        /db_write_allowed true/,
    ],
    [
        'decision_sections.db_training_prediction_decision.training_allowed=true 失败',
        'db_training_prediction_decision',
        'training_allowed',
        'true',
        /training_allowed true/,
    ],
    [
        'decision_sections.db_training_prediction_decision.prediction_allowed=true 失败',
        'db_training_prediction_decision',
        'prediction_allowed',
        'true',
        /prediction_allowed true/,
    ],
    [
        'decision_sections.db_training_prediction_decision.model_artifact_loading_allowed=true 失败',
        'db_training_prediction_decision',
        'model_artifact_loading_allowed',
        'true',
        /model_artifact_loading_allowed true/,
    ],
    [
        'decision_sections.final_human_decision.final_confirmation=true 失败',
        'final_human_decision',
        'final_confirmation',
        'true',
        /final_confirmation true/,
    ],
    ['bulk_scope_allowed=true 失败', 'scope_decision', 'bulk_scope_allowed', 'true', /bulk_scope_allowed true/],
    ['max_targets > 1 失败', 'scope_decision', 'max_targets', '2', /max_targets > 1/],
].forEach(([name, sectionName, fieldName, replacementValue, pattern]) => {
    test(name, () => {
        const gate = loadFresh();
        const payload = gate.runValidation(
            buildArgs(),
            buildTextDeps(replaceSectionField(sectionName, fieldName, replacementValue))
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

[
    [
        'codex_may_not_authorize_network=false 失败',
        'codex_may_not_authorize_network: true',
        'codex_may_not_authorize_network: false',
        /codex_may_not_authorize_network/,
    ],
    [
        'codex_may_not_set_execution_allowed=false 失败',
        'codex_may_not_set_execution_allowed: true',
        'codex_may_not_set_execution_allowed: false',
        /codex_may_not_set_execution_allowed/,
    ],
    [
        'safety would_access_network=true 失败',
        'would_access_network: false',
        'would_access_network: true',
        /safety\.would_access_network/,
    ],
    ['safety would_write_db=true 失败', 'would_write_db: false', 'would_write_db: true', /safety\.would_write_db/],
    [
        'safety would_write_network_authorization_decision_file=true 失败',
        'would_write_network_authorization_decision_file: false',
        'would_write_network_authorization_decision_file: true',
        /safety\.would_write_network_authorization_decision_file/,
    ],
].forEach(([name, search, replacement, pattern]) => {
    test(name, () => {
        const gate = loadFresh();
        const payload = gate.runValidation(buildArgs(), buildTextDeps(replaceInDecision(search, replacement)));
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), pattern);
    });
});

test('decision_sections missing 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInDecision('decision_sections:', 'decision_sections_missing:'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing required fields.*decision_sections/);
});

test('decision_blocking_reasons missing 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInDecision('decision_blocking_reasons:', 'decision_blocking_reasons_missing:'))
    );
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing decision_blocking_reasons/);
});

test('valid network authorization decision preview 成功', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildDeps());
    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.95D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION');
    assert.equal(payload.network_authorization_decision_template_only, true);
    assert.equal(payload.authorization_decision_valid, true);
    assert.equal(payload.handoff_checklist_valid, true);
    assert.equal(payload.review_result_valid, true);
    assert.equal(payload.review_plan_valid, true);
    assert.equal(payload.real_parameter_intake_valid, true);
    assert.equal(payload.validation_closure_valid, true);
    assert.equal(payload.blocked_summary_valid, true);
    assert.equal(payload.network_authorization_decision_ready, false);
    assert.equal(payload.network_authorization_decision_recorded, false);
    assert.equal(payload.authorization_decision, 'not_authorized');
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.authorization_decision_is_not_execution, true);
    assert.equal(payload.future_execution_preparation_phase_required, true);
    assert.equal(payload.future_final_confirmation_required, true);
    assert.equal(payload.can_proceed_to_network_dry_run_preparation, false);
    assert.equal(payload.authorization_handoff_ready, false);
    assert.equal(payload.authorization_handoff_completed, false);
    assert.equal(payload.filled_intake_reviewed, false);
    assert.equal(payload.filled_intake_accepted, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.decision_sections_complete, true);
    assert.equal(payload.decision_sections_authorized, false);
    assert.deepEqual(payload.decision_blocking_reasons, [
        'authorization_decision_template_only',
        'authorization_handoff_not_completed',
        'filled_intake_review_result_not_accepted',
        'source_terms_not_authorized',
        'network_runtime_not_authorized',
        'staging_not_authorized',
        'db_training_prediction_not_authorized',
        'final_human_confirmation_missing',
        'future_execution_preparation_phase_required',
    ]);
    for (const field of [
        'would_access_network',
        'would_launch_browser',
        'would_use_proxy',
        'would_execute_engine',
        'would_execute_legacy_titan_discovery',
        'would_write_staging',
        'would_create_staging_directory',
        'would_write_source_manifest',
        'would_write_packet_file',
        'would_write_approval_packet_file',
        'would_write_user_input_closure_file',
        'would_write_blocked_summary_file',
        'would_write_real_parameter_intake_file',
        'would_write_real_parameter_validation_closure_file',
        'would_write_filled_intake_review_file',
        'would_write_filled_intake_review_result_file',
        'would_write_authorization_handoff_checklist_file',
        'would_write_network_authorization_decision_file',
        'would_write_db',
        'would_train',
        'would_predict',
        'would_spawn_child_process',
    ]) {
        assert.equal(payload[field], false, field);
    }
    assert.equal(payload.commit_gate, 'blocked');
});

test('--commit blocked', () => {
    const gate = loadFresh();
    const result = runMain(
        gate,
        [
            '--authorization-decision',
            AD_PATH,
            '--handoff-checklist',
            HC_PATH,
            '--review-result',
            RR_PATH,
            '--review-plan',
            RP_PATH,
            '--intake',
            INTAKE_PATH,
            '--validation-closure',
            VC_PATH,
            '--blocked-summary',
            BS_PATH,
            '--commit',
        ],
        buildDeps()
    );
    assert.equal(result.status, 1);
    assert.match(JSON.parse(result.stdout).errors.join('\n'), /not wired in Phase 4.95D/);
});

test('Makefile preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-authorization-decision-preview',
            'NETWORK_AUTHORIZATION_DECISION_NODE=node',
            'AUTHORIZATION_DECISION=' + AD_PATH,
            'HANDOFF_CHECKLIST=' + HC_PATH,
            'REVIEW_RESULT=' + RR_PATH,
            'REVIEW_PLAN=' + RP_PATH,
            'INTAKE=' + INTAKE_PATH,
            'VALIDATION_CLOSURE=' + VC_PATH,
            'BLOCKED_SUMMARY=' + BS_PATH,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(result.status, 0, result.stderr);
    assert.equal(extractJson(result.stdout).ok, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-authorization-decision-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_DECISION=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.95D/);
});

[
    ['不访问网络', 'would_access_network'],
    ['不启动 browser', 'would_launch_browser'],
    ['不执行 proxy runtime', 'would_use_proxy'],
    ['不执行 engine', 'would_execute_engine'],
    ['不执行 legacy titan_discovery', 'would_execute_legacy_titan_discovery'],
    ['不写 staging', 'would_write_staging'],
    ['不创建目录', 'would_create_staging_directory'],
    ['不写 source manifest', 'would_write_source_manifest'],
    ['不写 packet file', 'would_write_packet_file'],
    ['不写 approval packet file', 'would_write_approval_packet_file'],
    ['不写 blocked summary file', 'would_write_blocked_summary_file'],
    ['不写 real parameter intake file', 'would_write_real_parameter_intake_file'],
    ['不写 validation closure file', 'would_write_real_parameter_validation_closure_file'],
    ['不写 filled-intake review plan file', 'would_write_filled_intake_review_file'],
    ['不写 filled-intake review result file', 'would_write_filled_intake_review_result_file'],
    ['不写 authorization handoff checklist file', 'would_write_authorization_handoff_checklist_file'],
    ['不写 network authorization decision file', 'would_write_network_authorization_decision_file'],
    ['不写 DB', 'would_write_db'],
    ['不 spawn child process', 'would_spawn_child_process'],
].forEach(([name, field]) => {
    test(name, t => {
        installGuards(t);
        const gate = loadFresh();
        const payload = gate.runValidation(buildArgs(), buildDeps());
        assert.equal(payload.ok, true);
        assert.equal(payload[field], false);
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
