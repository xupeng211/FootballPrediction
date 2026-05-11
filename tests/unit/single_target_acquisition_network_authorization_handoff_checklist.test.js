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
    'scripts/ops/single_target_acquisition_network_authorization_handoff_checklist.js'
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
const HC_TEXT = fs.readFileSync(HC_PATH, 'utf8');

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}
function buildArgs(o = {}) {
    return {
        handoff_checklist: HC_PATH,
        review_result: RR_PATH,
        review_plan: RP_PATH,
        intake: INTAKE_PATH,
        validation_closure: VC_PATH,
        blocked_summary: BS_PATH,
        ...o,
    };
}
function buildDeps(o = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: p => fs.existsSync(p),
        readFileSync: (p, e) => fs.readFileSync(p, e),
        ...o,
    };
}
function buildTextDeps(text, tp = HC_PATH) {
    return buildDeps({
        existsSync: p => p === tp || fs.existsSync(p),
        readFileSync: (p, e) => {
            if (p === tp) return text;
            return fs.readFileSync(p, e);
        },
    });
}

function installGuards(t) {
    const orig = {
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
    const fail = n => () => {
        throw new Error(n + ' should not be called');
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
    Module._load = function p(r, parent, isMain) {
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
            ]).has(r)
        ) {
            throw new Error('blocked: ' + r);
        }
        if (/titan_discovery|DiscoveryService|FixtureRepository/i.test(r)) throw new Error('blocked: ' + r);
        return orig.load.call(this, r, parent, isMain);
    };
    t.after(() => {
        Object.assign(http, { request: orig.http });
        Object.assign(https, { request: orig.https });
        global.fetch = orig.fetch;
        Object.assign(childProcess, { spawn: orig.spawn, exec: orig.exec, execFile: orig.execFile });
        Object.assign(fs, {
            writeFile: orig.writeFile,
            writeFileSync: orig.writeFileSync,
            createWriteStream: orig.createWriteStream,
            mkdir: orig.mkdir,
            mkdirSync: orig.mkdirSync,
        });
        net.connect = orig.net;
        Module._load = orig.load;
    });
}

function replaceInTemplate(s, r) {
    assert.match(HC_TEXT, new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return HC_TEXT.replace(s, r);
}
function removeLine(l) {
    return HC_TEXT.replace(l + '\n', '');
}
function runMain(gate, argv, deps = buildDeps()) {
    let stdout = '';
    const status = gate.main(
        argv,
        {
            stdout: t => {
                stdout += t;
            },
        },
        deps
    );
    return { status, stdout };
}
function extractJson(out) {
    const t = String(out || '').trim();
    const i = t.lastIndexOf('\n{');
    return JSON.parse(i >= 0 ? t.slice(i + 1) : t);
}

// 1-6: missing files
['handoff_checklist', 'review_result', 'review_plan', 'intake', 'validation_closure', 'blocked_summary'].forEach(f => {
    const label = f.replace(/_/g, ' ');
    test('缺 ' + label + ' 失败', () => {
        const gate = loadFresh();
        const args = buildArgs();
        delete args[f];
        const p = gate.runValidation(args, buildDeps());
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp('missing ' + label, 'i'));
    });
});

// 7-8: YAML
test('handoff checklist 缺 YAML block 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(buildArgs(), buildTextDeps('# no yaml\n'));
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing YAML block/i);
});
test('handoff checklist invalid YAML 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(buildArgs(), buildTextDeps('```yaml\nnot yaml\n```\n'));
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /invalid YAML/i);
});

// 9: missing phase
test('missing phase 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(
            removeLine('phase: PHASE4_94D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST')
        )
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing required fields: phase|phase must be/);
});

// 10: handoff_checklist_status
test('handoff_checklist_status 非 template_only 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('handoff_checklist_status: template_only', 'handoff_checklist_status: ready'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /handoff_checklist_status not template_only/);
});

// 11-18: top-level false fields
[
    [
        'authorization_handoff_ready=true',
        'authorization_handoff_ready: false',
        'authorization_handoff_ready: true',
        /authorization_handoff_ready true/,
    ],
    [
        'authorization_handoff_completed=true',
        'authorization_handoff_completed: false',
        'authorization_handoff_completed: true',
        /authorization_handoff_completed true/,
    ],
    [
        'filled_intake_review_result_ready=true',
        'filled_intake_review_result_ready: false',
        'filled_intake_review_result_ready: true',
        /filled_intake_review_result_ready true/,
    ],
    [
        'filled_intake_reviewed=true',
        'filled_intake_reviewed: false',
        'filled_intake_reviewed: true',
        /filled_intake_reviewed true/,
    ],
    [
        'filled_intake_accepted=true',
        'filled_intake_accepted: false',
        'filled_intake_accepted: true',
        /filled_intake_accepted true/,
    ],
    [
        'can_proceed_to_network_dry_run_preparation=true',
        'can_proceed_to_network_dry_run_preparation: false',
        'can_proceed_to_network_dry_run_preparation: true',
        /can_proceed_to_network_dry_run_preparation true/,
    ],
    [
        'real_parameters_provided=true',
        'real_parameters_provided: false',
        'real_parameters_provided: true',
        /real_parameters_provided true/,
    ],
    [
        'real_parameter_intake_validated=true',
        'real_parameter_intake_validated: false',
        'real_parameter_intake_validated: true',
        /real_parameter_intake_validated true/,
    ],
].forEach(([n, s, r, p]) => {
    test(n + ' 失败', () => {
        const gate = loadFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 19-34: handoff_sections.*.checked/passed=true
const SEC_NAMES = [
    'filled_intake_review_result_check',
    'real_parameter_integrity_check',
    'source_terms_and_allowed_use_check',
    'network_authorization_check',
    'proxy_browser_network_policy_check',
    'staging_policy_check',
    'no_db_training_prediction_check',
    'final_human_confirmation_check',
];
SEC_NAMES.forEach(name => {
    ['checked', 'passed'].forEach(field => {
        test('handoff_sections.' + name + '.' + field + '=true 失败', () => {
            const gate = loadFresh();
            const t = HC_TEXT.replace(
                new RegExp('(' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ':[\\s\\S]*?' + field + ': )false'),
                '$1true'
            );
            assert.ok(t !== HC_TEXT, 'template should be modified');
            const p = gate.runValidation(buildArgs(), buildTextDeps(t));
            assert.equal(p.ok, false);
            assert.match(
                p.errors.join('\n'),
                new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\.' + field + ' true')
            );
        });
    });
});

// 35-41: authorization flags
[
    [
        'network_dry_run_authorized=true',
        'network_dry_run_authorized: false',
        'network_dry_run_authorized: true',
        /network_dry_run_authorized true/,
    ],
    [
        'network_dry_run_execution_allowed=true',
        'network_dry_run_execution_allowed: false',
        'network_dry_run_execution_allowed: true',
        /network_dry_run_execution_allowed true/,
    ],
    [
        'staging_write_authorized=true',
        'staging_write_authorized: false',
        'staging_write_authorized: true',
        /staging_write_authorized true/,
    ],
    ['db_write_authorized=true', 'db_write_authorized: false', 'db_write_authorized: true', /db_write_authorized true/],
    ['training_authorized=true', 'training_authorized: false', 'training_authorized: true', /training_authorized true/],
    [
        'prediction_authorized=true',
        'prediction_authorized: false',
        'prediction_authorized: true',
        /prediction_authorized true/,
    ],
    [
        'final_human_confirmation=true',
        'final_human_confirmation: false',
        'final_human_confirmation: true',
        /final_human_confirmation true/,
    ],
].forEach(([n, s, r, p]) => {
    test(n + ' 失败', () => {
        const gate = loadFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 42-43: authorization_boundary flags
test('handoff_checklist_is_not_authorization=false 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(
            replaceInTemplate(
                'handoff_checklist_is_not_authorization: true',
                'handoff_checklist_is_not_authorization: false'
            )
        )
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /handoff_checklist_is_not_authorization/);
});
test('future_authorization_phase_required=false 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(
            replaceInTemplate('future_authorization_phase_required: true', 'future_authorization_phase_required: false')
        )
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /future_authorization_phase_required/);
});

// 44-47: codex constraints
[
    [
        'codex_may_not_mark_checked=false',
        'codex_may_not_mark_checked: true',
        'codex_may_not_mark_checked: false',
        /codex_may_not_mark_checked false/,
    ],
    [
        'codex_may_not_mark_passed=false',
        'codex_may_not_mark_passed: true',
        'codex_may_not_mark_passed: false',
        /codex_may_not_mark_passed false/,
    ],
    [
        'codex_may_not_complete_handoff=false',
        'codex_may_not_complete_handoff: true',
        'codex_may_not_complete_handoff: false',
        /codex_may_not_complete_handoff false/,
    ],
    [
        'codex_may_not_authorize_network=false',
        'codex_may_not_authorize_network: true',
        'codex_may_not_authorize_network: false',
        /codex_may_not_authorize_network/,
    ],
].forEach(([n, s, r, p]) => {
    test(n + ' 失败', () => {
        const gate = loadFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 48-49: missing sections
test('handoff_sections missing 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('handoff_sections:', 'handoff_sections_missing:'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing required fields.*handoff_sections/);
});
test('handoff_blocking_reasons missing 失败', () => {
    const gate = loadFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('handoff_blocking_reasons:', 'handoff_blocking_reasons_missing:'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing handoff_blocking_reasons/);
});

// 52-54: safety would_*
['would_access_network', 'would_write_db', 'would_write_authorization_handoff_checklist_file'].forEach(f => {
    test('safety ' + f + '=true 失败', () => {
        const gate = loadFresh();
        const p = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(f + ': false', f + ': true')));
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp('safety\\.' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    });
});

// 55: valid preview
test('valid authorization handoff checklist preview 成功', () => {
    const gate = loadFresh();
    const p = gate.runValidation(buildArgs(), buildDeps());
    assert.equal(p.ok, true);
    assert.equal(p.phase, 'PHASE4.94D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST');
    assert.equal(p.authorization_handoff_checklist_template_only, true);
    assert.equal(p.handoff_checklist_valid, true);
    assert.equal(p.review_result_valid, true);
    assert.equal(p.review_plan_valid, true);
    assert.equal(p.real_parameter_intake_valid, true);
    assert.equal(p.validation_closure_valid, true);
    assert.equal(p.blocked_summary_valid, true);
    assert.equal(p.authorization_handoff_ready, false);
    assert.equal(p.authorization_handoff_completed, false);
    assert.equal(p.filled_intake_accepted, false);
    assert.equal(p.can_proceed_to_network_dry_run_preparation, false);
    assert.equal(p.network_dry_run_authorized, false);
    assert.equal(p.network_dry_run_execution_allowed, false);
    assert.equal(p.handoff_sections_complete, true);
    assert.equal(p.handoff_sections_passed, false);
    assert.equal(p.handoff_checklist_is_not_authorization, true);
    assert.equal(p.future_authorization_phase_required, true);
    assert.deepEqual(p.handoff_blocking_reasons, [
        'handoff_checklist_template_only',
        'filled_intake_review_result_not_accepted',
        'real_parameters_not_validated',
        'source_terms_not_approved',
        'network_dry_run_not_authorized',
        'proxy_browser_network_policy_not_approved',
        'staging_policy_not_approved',
        'no_db_training_prediction_policy_not_confirmed',
        'final_human_confirmation_missing',
        'future_separate_authorization_phase_required',
    ]);
    for (const f of [
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
        'would_write_blocked_summary_file',
        'would_write_real_parameter_intake_file',
        'would_write_real_parameter_validation_closure_file',
        'would_write_filled_intake_review_file',
        'would_write_filled_intake_review_result_file',
        'would_write_authorization_handoff_checklist_file',
        'would_write_db',
        'would_train',
        'would_predict',
        'would_spawn_child_process',
    ]) {
        assert.equal(p[f], false, f);
    }
    assert.equal(p.commit_gate, 'blocked');
});

// 56: --commit blocked
test('--commit blocked', () => {
    const gate = loadFresh();
    const r = runMain(
        gate,
        [
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
    assert.equal(r.status, 1);
    assert.match(JSON.parse(r.stdout).errors.join('\n'), /not wired in Phase 4.94D/);
});

// 57-58: Makefile
test('Makefile preview 成功', () => {
    const r = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-authorization-handoff-checklist-preview',
            'NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST_NODE=node',
            'HANDOFF_CHECKLIST=' + HC_PATH,
            'REVIEW_RESULT=' + RR_PATH,
            'REVIEW_PLAN=' + RP_PATH,
            'INTAKE=' + INTAKE_PATH,
            'VALIDATION_CLOSURE=' + VC_PATH,
            'BLOCKED_SUMMARY=' + BS_PATH,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(r.status, 0, r.stderr);
    assert.equal(extractJson(r.stdout).ok, true);
});
test('Makefile commit blocked', () => {
    const r = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-authorization-handoff-checklist-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(r.status, 0);
    assert.match(r.stdout, /not wired in Phase 4.94D/);
});

// 59-76: safety guard tests
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
    ['不写 DB', 'would_write_db'],
    ['不 spawn child process', 'would_spawn_child_process'],
].forEach(([n, f]) => {
    test(n, t => {
        installGuards(t);
        const gate = loadFresh();
        const p = gate.runValidation(buildArgs(), buildDeps());
        assert.equal(p.ok, true);
        assert.equal(p[f], false);
    });
});

test('source audit: 不 import forbidden modules', () => {
    const src = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(src));
    assert.ok(!/require\s*\(\s*['"].*DiscoveryService/.test(src));
    assert.ok(!/require\s*\(\s*['"].*FixtureRepository/.test(src));
    assert.ok(!/require\s*\(\s*['"]pg['"]/.test(src));
    assert.ok(!/require\s*\(\s*['"]redis['"]/.test(src));
    assert.ok(!/require\s*\(\s*['"]ioredis['"]/.test(src));
    assert.ok(!/require\s*\(\s*['"]playwright/.test(src));
    assert.ok(!/require\s*\(\s*['"](?:node:)?child_process['"]/.test(src));
});
