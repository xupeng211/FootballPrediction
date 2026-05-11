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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fotmob_stdout_network_dry_run_execution_plan.js');
const PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md'
);
const PACKET_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_AUTHORIZATION_PACKET_TEMPLATE.md'
);
const PLAN_TEXT = fs.readFileSync(PLAN_PATH, 'utf8');

const LEGACY_PATHS = [
    path.join(PROJECT_ROOT, 'scripts/ops/titan_discovery.js'),
    path.join(PROJECT_ROOT, 'scripts/ops/run_production.js'),
    path.join(PROJECT_ROOT, 'scripts/ops/batch_historical_backfill.js'),
    path.join(PROJECT_ROOT, 'scripts/ops/backfill_historical_raw_match_data.js'),
    path.join(PROJECT_ROOT, 'scripts/ops/titan_seeder.js'),
    path.join(PROJECT_ROOT, 'src/infrastructure/harvesters/ProductionHarvester.js'),
    path.join(PROJECT_ROOT, 'src/infrastructure/harvesters/strategies/FotMobStrategy.js'),
    path.join(PROJECT_ROOT, 'src/infrastructure/services/FixtureRepository.js'),
    path.join(PROJECT_ROOT, 'src/infrastructure/harvesters/components/Persistence.js'),
    path.join(PROJECT_ROOT, 'src/infrastructure/services/BrowserProvider.js'),
];

const SAFE_FALSE_FIELDS = [
    'would_access_network',
    'would_launch_browser',
    'would_use_proxy',
    'would_execute_legacy_runtime',
    'would_execute_engine',
    'would_write_staging',
    'would_create_staging_directory',
    'would_write_source_manifest',
    'would_write_packet_file',
    'would_write_execution_plan_file',
    'would_write_db',
    'would_train',
    'would_predict',
    'would_spawn_child_process',
];

function loadFresh() {
    delete require.cache[require.resolve(SCRIPT_PATH)];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        plan: PLAN_PATH,
        packet: PACKET_PATH,
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

function buildTextDependencies(planMarkdownText, targetPath = PLAN_PATH) {
    const resolvedPlan = path.resolve(targetPath);
    return buildDependencies({
        existsSync: candidate => path.resolve(candidate) === resolvedPlan || fs.existsSync(candidate),
        readFileSync: (candidate, encoding) => {
            if (path.resolve(candidate) === resolvedPlan) return planMarkdownText;
            return fs.readFileSync(candidate, encoding);
        },
    });
}

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalNetConnect = net.connect;
    const originalNetCreateConnection = net.createConnection;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by fotmob_stdout_network_dry_run_execution_plan`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    net.connect = fail('net.connect');
    net.createConnection = fail('net.createConnection');
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
            'net',
            'node:net',
            'child_process',
            'node:child_process',
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
            'chromium',
        ]);
        const blockedFragments = [
            'titan_discovery',
            'run_production',
            'batch_historical_backfill',
            'backfill_historical_raw_match_data',
            'titan_seeder',
            'DiscoveryService',
            'ProductionHarvester',
            'FotMobStrategy',
            'FixtureRepository',
            'Persistence',
            'BrowserProvider',
            'ProxyProvider',
        ];

        if (blockedImports.has(request) || blockedFragments.some(fragment => String(request).includes(fragment))) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        global.fetch = originalFetch;
        net.connect = originalNetConnect;
        net.createConnection = originalNetCreateConnection;
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

function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function replaceInTemplate(searchValue, replaceValue) {
    assert.match(PLAN_TEXT, new RegExp(escapeRegExp(searchValue)));
    return PLAN_TEXT.replace(searchValue, replaceValue);
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

function extractJson(stdout) {
    return JSON.parse(String(stdout || '').trim());
}

function assertSafePayload(payload) {
    assert.equal(payload.phase, 'PHASE5_00F_FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_EXECUTION_PLAN');
    assert.equal(payload.execution_plan_template_only, true);
    assert.equal(payload.execution_plan_valid, true);
    assert.equal(payload.authorization_packet_valid, true);
    assert.equal(payload.execution_plan_ready, false);
    assert.equal(payload.execution_plan_reviewed, false);
    assert.equal(payload.execution_plan_accepted, false);
    assert.equal(payload.execution_allowed, false);
    assert.equal(payload.user_filled_packet_provided, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.target_source, 'fotmob');
    assert.equal(payload.target_count, 0);
    assert.equal(payload.max_targets, 1);
    assert.equal(payload.single_target_only, true);
    assert.equal(payload.bulk_scope_allowed, false);
    assert.equal(payload.stdout_only, true);
    assert.equal(payload.external_network_allowed, false);
    assert.equal(payload.browser_runtime_allowed, false);
    assert.equal(payload.proxy_runtime_allowed, false);
    assert.equal(payload.legacy_runtime_allowed, false);
    assert.equal(payload.acquisition_engine_allowed, false);
    assert.equal(payload.stdout_preview_allowed, false);
    assert.equal(payload.staging_write_allowed, false);
    assert.equal(payload.source_manifest_write_allowed, false);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.training_allowed, false);
    assert.equal(payload.prediction_allowed, false);
    assert.equal(payload.pre_execution_checks_complete, true);
    assert.equal(payload.pre_execution_checks_passed, false);
    assert.equal(payload.abort_conditions_active, true);
    assert.equal(payload.continue_template_phases, false);
    assert.equal(payload.requires_user_real_input, true);
    assert.equal(payload.commit_gate, 'blocked');
    assert.equal(
        payload.next_required_action,
        'user_must_fill_real_fotmob_target_terms_allowed_use_and_network_authorization'
    );
    for (const field of SAFE_FALSE_FIELDS) {
        assert.equal(payload[field], false, `${field} must remain false`);
    }
}

test('缺 plan 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs({ plan: '' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing plan/i);
});

test('缺 packet 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs({ packet: '' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing packet/i);
});

test('plan 缺 YAML block 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDependencies('# no yaml\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing YAML block/i);
});

test('invalid YAML 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildTextDependencies('```yaml\nnot yaml\n```\n'));
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /invalid YAML/i);
});

[
    [
        'execution_plan_status 非 template_only 失败',
        'execution_plan_status: template_only',
        'execution_plan_status: approved',
        /execution_plan_status not template_only/,
    ],
    [
        'execution_plan_ready=true 失败',
        'execution_plan_ready: false',
        'execution_plan_ready: true',
        /execution_plan_ready true/,
    ],
    [
        'execution_plan_accepted=true 失败',
        'execution_plan_accepted: false',
        'execution_plan_accepted: true',
        /execution_plan_accepted true/,
    ],
    ['execution_allowed=true 失败', 'execution_allowed: false', 'execution_allowed: true', /execution_allowed true/],
    [
        'user_filled_packet_provided=true 失败',
        'user_filled_packet_provided: false',
        'user_filled_packet_provided: true',
        /user_filled_packet_provided true/,
    ],
    [
        'network_dry_run_authorized=true 失败',
        'network_dry_run_authorized: false',
        'network_dry_run_authorized: true',
        /network_dry_run_authorized true/,
    ],
    [
        'final_human_confirmation=true 失败',
        'final_human_confirmation: false',
        'final_human_confirmation: true',
        /final_human_confirmation true/,
    ],
    ['target_source 不是 fotmob 失败', 'target_source: fotmob', 'target_source: other', /target_source not fotmob/],
    ['target_count > 1 失败', 'target_count: 0', 'target_count: 2', /target_count > 1/],
    ['max_targets > 1 失败', 'max_targets: 1', 'max_targets: 2', /max_targets > 1/],
    [
        'bulk_scope_allowed=true 失败',
        'bulk_scope_allowed: false',
        'bulk_scope_allowed: true',
        /bulk_scope_allowed true/,
    ],
    ['stdout_only=false 失败', 'stdout_only: true', 'stdout_only: false', /stdout_only false/],
    [
        'external_network_allowed=true 失败',
        'external_network_allowed: false',
        'external_network_allowed: true',
        /external_network_allowed true/,
    ],
    [
        'browser_runtime_allowed=true 失败',
        'browser_runtime_allowed: false',
        'browser_runtime_allowed: true',
        /browser_runtime_allowed true/,
    ],
    [
        'proxy_runtime_allowed=true 失败',
        'proxy_runtime_allowed: false',
        'proxy_runtime_allowed: true',
        /proxy_runtime_allowed true/,
    ],
    [
        'legacy_runtime_allowed=true 失败',
        'legacy_runtime_allowed: false',
        'legacy_runtime_allowed: true',
        /legacy_runtime_allowed true/,
    ],
    [
        'acquisition_engine_allowed=true 失败',
        'acquisition_engine_allowed: false',
        'acquisition_engine_allowed: true',
        /acquisition_engine_allowed true/,
    ],
    [
        'staging_write_allowed=true 失败',
        'staging_write_allowed: false',
        'staging_write_allowed: true',
        /staging_write_allowed true/,
    ],
    [
        'source_manifest_write_allowed=true 失败',
        'source_manifest_write_allowed: false',
        'source_manifest_write_allowed: true',
        /source_manifest_write_allowed true/,
    ],
    ['db_write_allowed=true 失败', 'db_write_allowed: false', 'db_write_allowed: true', /db_write_allowed true/],
    ['training_allowed=true 失败', 'training_allowed: false', 'training_allowed: true', /training_allowed true/],
    [
        'prediction_allowed=true 失败',
        'prediction_allowed: false',
        'prediction_allowed: true',
        /prediction_allowed true/,
    ],
    [
        'pre_execution_checks 任一 checked=true 失败',
        'checked: false',
        'checked: true',
        /pre_execution_checks\.user_filled_authorization_packet_check\.checked true/,
    ],
    [
        'pre_execution_checks 任一 passed=true 失败',
        'passed: false',
        'passed: true',
        /pre_execution_checks\.user_filled_authorization_packet_check\.passed true/,
    ],
    [
        'continue_template_phases=true 失败',
        'continue_template_phases: false',
        'continue_template_phases: true',
        /continue_template_phases true/,
    ],
    [
        'requires_user_real_input=false 失败',
        'requires_user_real_input: true',
        'requires_user_real_input: false',
        /requires_user_real_input false/,
    ],
    [
        'codex_may_not_execute_network_dry_run=false 失败',
        'codex_may_not_execute_network_dry_run: true',
        'codex_may_not_execute_network_dry_run: false',
        /codex_may_not_execute_network_dry_run false/,
    ],
    [
        'safety would_access_network=true 失败',
        'would_access_network: false',
        'would_access_network: true',
        /safety would_access_network not false/,
    ],
    [
        'safety would_write_db=true 失败',
        'would_write_db: false',
        'would_write_db: true',
        /safety would_write_db not false/,
    ],
    [
        'safety would_write_execution_plan_file=true 失败',
        'would_write_execution_plan_file: false',
        'would_write_execution_plan_file: true',
        /safety would_write_execution_plan_file not false/,
    ],
].forEach(([name, searchValue, replaceValue, expectedError]) => {
    test(name, () => {
        const gate = loadFresh();
        const payload = gate.runValidation(
            buildArgs(),
            buildTextDependencies(replaceInTemplate(searchValue, replaceValue))
        );
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), expectedError);
    });
});

test('valid execution plan preview 成功', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runMain(gate, [`--plan=${PLAN_PATH}`, `--packet=${PACKET_PATH}`], buildDependencies());
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr, '');
    assertSafePayload(extractJson(result.stdout));
});

test('--commit blocked', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runMain(gate, [`--plan=${PLAN_PATH}`, `--packet=${PACKET_PATH}`, '--commit'], buildDependencies());
    assert.equal(result.status, 1);
    assert.equal(result.stdout, '');
    assert.match(result.stderr, /BLOCKED: FotMob stdout-only network dry-run execution plan is not executable/);
});

test('Makefile preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-fotmob-stdout-network-dry-run-execution-plan-preview',
            'FOTMOB_STDOUT_NETWORK_EXECUTION_PLAN_NODE=node',
            `PLAN=${PLAN_PATH}`,
            `PACKET=${PACKET_PATH}`,
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.equal(result.status, 0, result.stderr);
    assertSafePayload(extractJson(result.stdout));
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-fotmob-stdout-network-dry-run-execution-plan-commit',
            `PLAN=${PLAN_PATH}`,
            `PACKET=${PACKET_PATH}`,
            'CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_EXECUTION_PLAN=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not executable in Phase 5\.00F/);
});

[
    ['不访问网络', 'would_access_network'],
    ['不启动 browser', 'would_launch_browser'],
    ['不执行 proxy runtime', 'would_use_proxy'],
    ['不执行 legacy runtime', 'would_execute_legacy_runtime'],
    ['不写 staging', 'would_write_staging'],
    ['不创建目录', 'would_create_staging_directory'],
    ['不写 source manifest', 'would_write_source_manifest'],
    ['不写 packet file', 'would_write_packet_file'],
    ['不写 execution plan file', 'would_write_execution_plan_file'],
    ['不写 DB', 'would_write_db'],
    ['不 spawn child process', 'would_spawn_child_process'],
].forEach(([name, field]) => {
    test(name, t => {
        installExecutionGuards(t);
        const gate = loadFresh();
        const payload = gate.runValidation(buildArgs(), buildDependencies());
        assert.equal(payload.ok, true);
        assert.equal(payload[field], false);
    });
});

test('execution plan validation does not import legacy runtime, browser, proxy, DB, or child process paths', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    for (const legacyPath of LEGACY_PATHS) {
        assert.equal(require.cache[legacyPath], undefined, `${legacyPath} must not be loaded`);
    }
});

test('source audit: 不 import forbidden modules', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"](?:node:)?http['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"](?:node:)?https['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"](?:node:)?net['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"](?:node:)?child_process['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]redis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]ioredis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]playwright/.test(source));
    assert.ok(!/titan_discovery|DiscoveryService|ProductionHarvester|FotMobStrategy/.test(source));
    assert.ok(!/FixtureRepository|Persistence|BrowserProvider|ProxyProvider/.test(source));
});
