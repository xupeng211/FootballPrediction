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
    'scripts/ops/single_target_acquisition_network_filled_intake_review_result.js'
);
const REVIEW_RESULT_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT_TEMPLATE.md'
);
const REVIEW_PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md'
);
const INTAKE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md'
);
const VALIDATION_CLOSURE_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md'
);
const BLOCKED_SUMMARY_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md'
);
const REVIEW_RESULT_TEXT = fs.readFileSync(REVIEW_RESULT_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        review_result: REVIEW_RESULT_PATH,
        review_plan: REVIEW_PLAN_PATH,
        intake: INTAKE_PATH,
        validation_closure: VALIDATION_CLOSURE_PATH,
        blocked_summary: BLOCKED_SUMMARY_PATH,
        ...overrides,
    };
}

function buildDeps(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: p => fs.existsSync(p),
        readFileSync: (p, e) => fs.readFileSync(p, e),
        ...overrides,
    };
}

function buildTextDeps(markdownText, targetPath = REVIEW_RESULT_PATH) {
    return buildDeps({
        existsSync: p => p === targetPath || fs.existsSync(p),
        readFileSync: (p, e) => {
            if (p === targetPath) return markdownText;
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
    assert.match(REVIEW_RESULT_TEXT, new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return REVIEW_RESULT_TEXT.replace(s, r);
}
function removeLine(l) {
    return REVIEW_RESULT_TEXT.replace(l + '\n', '');
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

function extractLastJsonObject(stdout) {
    const t = String(stdout || '').trim();
    const i = t.lastIndexOf('\n{');
    return JSON.parse(i >= 0 ? t.slice(i + 1) : t);
}

// 1-5: missing files
['review_result', 'review_plan', 'intake', 'validation_closure', 'blocked_summary'].forEach(f => {
    const label = f.replace(/_/g, ' ');
    test('缺 ' + label + ' 失败', () => {
        const gate = loadValidatorFresh();
        const args = buildArgs();
        delete args[f];
        const p = gate.runValidation(args, buildDeps());
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp('missing ' + label, 'i'));
    });
});

// 6-7: YAML issues
test('review result 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(buildArgs(), buildTextDeps('# no yaml\n'));
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing YAML block/i);
});
test('review result invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(buildArgs(), buildTextDeps('```yaml\nnot yaml\n```\n'));
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /invalid YAML/i);
});

// 8: missing phase
test('missing phase 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(
            removeLine('phase: PHASE4_93D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT')
        )
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing required fields: phase|phase must be/);
});

// 9: review_result_status non-template_only
test('review_result_status 非 template_only 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('review_result_status: template_only', 'review_result_status: ready'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /review_result_status not template_only/);
});

// 10-16: top-level false fields
[
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
        'filled_intake_rejected=true',
        'filled_intake_rejected: false',
        'filled_intake_rejected: true',
        /filled_intake_rejected true/,
    ],
    [
        'filled_intake_needs_revision=true',
        'filled_intake_needs_revision: false',
        'filled_intake_needs_revision: true',
        /filled_intake_needs_revision true/,
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
        const gate = loadValidatorFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 17-30: review_sections.*.reviewed/passed=true
const SECTION_NAMES = [
    'real_target_review',
    'source_terms_review',
    'network_authorization_review',
    'proxy_browser_network_policy_review',
    'staging_policy_review',
    'no_db_training_prediction_review',
    'final_human_confirmation_review',
];
SECTION_NAMES.forEach(name => {
    test('review_sections.' + name + '.reviewed=true 失败', () => {
        const gate = loadValidatorFresh();
        const t = REVIEW_RESULT_TEXT.replace(
            new RegExp('(' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ':[\\s\\S]*?reviewed: )false'),
            '$1true'
        );
        assert.ok(t !== REVIEW_RESULT_TEXT, 'template should be modified');
        const p = gate.runValidation(buildArgs(), buildTextDeps(t));
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\.reviewed true'));
    });
    test('review_sections.' + name + '.passed=true 失败', () => {
        const gate = loadValidatorFresh();
        const t = REVIEW_RESULT_TEXT.replace(
            new RegExp('(' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ':[\\s\\S]*?passed: )false'),
            '$1true'
        );
        assert.ok(t !== REVIEW_RESULT_TEXT, 'template should be modified');
        const p = gate.runValidation(buildArgs(), buildTextDeps(t));
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\.passed true'));
    });
});

// 31-33: overall_review_result
test('overall_review_result.status 不是 not_reviewed 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('status: not_reviewed', 'status: accepted'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /overall_review_result\.status/);
});
test('overall_review_result.accepted=true 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('    accepted: false', '    accepted: true'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /overall_review_result\.accepted true/);
});
test('overall_review_result.can_proceed_to_network_dry_run_preparation=true 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(
            replaceInTemplate(
                'can_proceed_to_network_dry_run_preparation: false',
                'can_proceed_to_network_dry_run_preparation: true'
            )
        )
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /can_proceed_to_network_dry_run_preparation true/);
});

// 34-40: authorization flags
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
        const gate = loadValidatorFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 41-44: codex constraints
[
    [
        'codex_may_not_self_fill_real_parameters=false',
        'codex_may_not_self_fill_real_parameters: true',
        'codex_may_not_self_fill_real_parameters: false',
        /codex_may_not_self_fill_real_parameters false/,
    ],
    [
        'codex_may_not_mark_reviewed=false',
        'codex_may_not_mark_reviewed: true',
        'codex_may_not_mark_reviewed: false',
        /codex_may_not_mark_reviewed false/,
    ],
    [
        'codex_may_not_mark_passed=false',
        'codex_may_not_mark_passed: true',
        'codex_may_not_mark_passed: false',
        /codex_may_not_mark_passed false/,
    ],
    [
        'codex_may_not_accept_filled_intake=false',
        'codex_may_not_accept_filled_intake: true',
        'codex_may_not_accept_filled_intake: false',
        /codex_may_not_accept_filled_intake false/,
    ],
].forEach(([n, s, r, p]) => {
    test(n + ' 失败', () => {
        const gate = loadValidatorFresh();
        const pl = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(s, r)));
        assert.equal(pl.ok, false);
        assert.match(pl.errors.join('\n'), p);
    });
});

// 45: missing review_sections
test('review_sections missing 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('review_sections:', 'review_sections_missing:'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing required fields.*review_sections/);
});

// 46: missing blocking_reasons
test('overall_review_result.blocking_reasons missing 失败', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(
        buildArgs(),
        buildTextDeps(replaceInTemplate('blocking_reasons:', 'blocking_reasons_missing:'))
    );
    assert.equal(p.ok, false);
    assert.match(p.errors.join('\n'), /missing overall_review_result\.blocking_reasons/);
});

// 49-51: safety would_*
['would_access_network', 'would_write_db', 'would_write_filled_intake_review_result_file'].forEach(f => {
    test('safety ' + f + '=true 失败', () => {
        const gate = loadValidatorFresh();
        const p = gate.runValidation(buildArgs(), buildTextDeps(replaceInTemplate(f + ': false', f + ': true')));
        assert.equal(p.ok, false);
        assert.match(p.errors.join('\n'), new RegExp('safety\\.' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    });
});

// 52: valid preview
test('valid filled-intake review result preview 成功', () => {
    const gate = loadValidatorFresh();
    const p = gate.runValidation(buildArgs(), buildDeps());
    assert.equal(p.ok, true);
    assert.equal(p.phase, 'PHASE4.93D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT');
    assert.equal(p.filled_intake_review_result_template_only, true);
    assert.equal(p.review_result_valid, true);
    assert.equal(p.review_plan_valid, true);
    assert.equal(p.real_parameter_intake_valid, true);
    assert.equal(p.validation_closure_valid, true);
    assert.equal(p.blocked_summary_valid, true);
    assert.equal(p.filled_intake_review_result_ready, false);
    assert.equal(p.filled_intake_reviewed, false);
    assert.equal(p.filled_intake_accepted, false);
    assert.equal(p.filled_intake_rejected, false);
    assert.equal(p.filled_intake_needs_revision, false);
    assert.equal(p.real_parameters_provided, false);
    assert.equal(p.real_parameter_intake_validated, false);
    assert.equal(p.network_dry_run_authorized, false);
    assert.equal(p.network_dry_run_execution_allowed, false);
    assert.equal(p.review_sections_complete, true);
    assert.equal(p.review_sections_passed, false);
    assert.equal(p.overall_review_status, 'not_reviewed');
    assert.equal(p.can_proceed_to_network_dry_run_preparation, false);
    assert.deepEqual(p.review_blocking_reasons, [
        'filled_intake_not_provided',
        'filled_intake_not_reviewed',
        'review_result_template_only',
        'future_separate_phase_required',
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
        'would_write_db',
        'would_train',
        'would_predict',
        'would_spawn_child_process',
    ]) {
        assert.equal(p[f], false, f + ' should be false');
    }
    assert.equal(p.commit_gate, 'blocked');
});

// 53: --commit blocked
test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const r = runMain(
        gate,
        [
            '--review-result',
            REVIEW_RESULT_PATH,
            '--review-plan',
            REVIEW_PLAN_PATH,
            '--intake',
            INTAKE_PATH,
            '--validation-closure',
            VALIDATION_CLOSURE_PATH,
            '--blocked-summary',
            BLOCKED_SUMMARY_PATH,
            '--commit',
        ],
        buildDeps()
    );
    assert.equal(r.status, 1);
    assert.match(JSON.parse(r.stdout).errors.join('\n'), /not wired in Phase 4.93D/);
});

// 54-55: Makefile
test('Makefile preview 成功', () => {
    const r = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-filled-intake-review-result-preview',
            'NETWORK_FILLED_INTAKE_REVIEW_RESULT_NODE=node',
            'REVIEW_RESULT=' + REVIEW_RESULT_PATH,
            'REVIEW_PLAN=' + REVIEW_PLAN_PATH,
            'INTAKE=' + INTAKE_PATH,
            'VALIDATION_CLOSURE=' + VALIDATION_CLOSURE_PATH,
            'BLOCKED_SUMMARY=' + BLOCKED_SUMMARY_PATH,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(r.status, 0, r.stderr);
    const p = extractLastJsonObject(r.stdout);
    assert.equal(p.ok, true);
    assert.equal(p.review_result_valid, true);
});
test('Makefile commit blocked', () => {
    const r = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-network-filled-intake-review-result-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_RESULT=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(r.status, 0);
    assert.match(r.stdout, /not wired in Phase 4.93D/);
});

// 56-72: safety guard tests
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
    ['不写 DB', 'would_write_db'],
    ['不 spawn child process', 'would_spawn_child_process'],
].forEach(([n, f]) => {
    test(n, t => {
        installGuards(t);
        const gate = loadValidatorFresh();
        const p = gate.runValidation(buildArgs(), buildDeps());
        assert.equal(p.ok, true);
        assert.equal(p[f], false);
    });
});

// source audit
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
