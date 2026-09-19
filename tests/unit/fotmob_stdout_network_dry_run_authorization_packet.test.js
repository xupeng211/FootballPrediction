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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fotmob_stdout_network_dry_run_authorization_packet.js');
const PACKET_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_AUTHORIZATION_PACKET_TEMPLATE.md'
);
const PACKET_TEXT = fs.readFileSync(PACKET_PATH, 'utf8');

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

function buildTextDependencies(markdownText, targetPath = PACKET_PATH) {
    const resolvedTarget = path.resolve(targetPath);
    return buildDependencies({
        existsSync: candidate => path.resolve(candidate) === resolvedTarget || fs.existsSync(candidate),
        readFileSync: (candidate, encoding) => {
            if (path.resolve(candidate) === resolvedTarget) return markdownText;
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
        throw new Error(`${name} should not be called by fotmob_stdout_network_dry_run_authorization_packet`);
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
    assert.match(PACKET_TEXT, new RegExp(escapeRegExp(searchValue)));
    return PACKET_TEXT.replace(searchValue, replaceValue);
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
    assert.equal(payload.phase, 'PHASE4_99F_FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_AUTHORIZATION_PACKET');
    assert.equal(payload.authorization_packet_template_only, true);
    assert.equal(payload.authorization_packet_valid, true);
    assert.equal(payload.authorization_packet_ready, false);
    assert.equal(payload.authorization_packet_reviewed, false);
    assert.equal(payload.authorization_packet_accepted, false);
    assert.equal(payload.target_source, 'fotmob');
    assert.equal(payload.target_count, 0);
    assert.equal(payload.max_targets, 1);
    assert.equal(payload.single_target_only, true);
    assert.equal(payload.bulk_scope_allowed, false);
    assert.equal(payload.terms_approval, false);
    assert.equal(payload.allowed_use_approved, false);
    assert.equal(payload.external_network_authorized, false);
    assert.equal(payload.stdout_only_network_dry_run_authorized, false);
    assert.equal(payload.browser_runtime_authorized, false);
    assert.equal(payload.proxy_runtime_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.source_manifest_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.authorization_decision, 'not_authorized');
    assert.equal(payload.final_human_confirmation, false);
    assert.equal(payload.commit_gate, 'blocked');
    for (const field of SAFE_FALSE_FIELDS) {
        assert.equal(payload[field], false, `${field} must remain false`);
    }
}

test('缺 packet 失败', () => {
    const gate = loadFresh();
    const payload = gate.runValidation({}, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing packet/i);
});

test('缺 YAML block 失败', () => {
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
        'authorization_packet_status 非 template_only 失败',
        'authorization_packet_status: template_only',
        'authorization_packet_status: approved',
        /authorization_packet_status not template_only/,
    ],
    [
        'authorization_packet_ready=true 失败',
        'authorization_packet_ready: false',
        'authorization_packet_ready: true',
        /authorization_packet_ready true/,
    ],
    [
        'authorization_packet_accepted=true 失败',
        'authorization_packet_accepted: false',
        'authorization_packet_accepted: true',
        /authorization_packet_accepted true/,
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
    ['terms_approval=true 失败', 'terms_approval: false', 'terms_approval: true', /terms_approval true/],
    [
        'allowed_use_approved=true 失败',
        'allowed_use_approved: false',
        'allowed_use_approved: true',
        /allowed_use_approved true/,
    ],
    [
        'external_network_authorized=true 失败',
        'external_network_authorized: false',
        'external_network_authorized: true',
        /external_network_authorized true/,
    ],
    [
        'stdout_only_network_dry_run_authorized=true 失败',
        'stdout_only_network_dry_run_authorized: false',
        'stdout_only_network_dry_run_authorized: true',
        /stdout_only_network_dry_run_authorized true/,
    ],
    [
        'browser_runtime_authorized=true 失败',
        'browser_runtime_authorized: false',
        'browser_runtime_authorized: true',
        /browser_runtime_authorized true/,
    ],
    [
        'proxy_runtime_authorized=true 失败',
        'proxy_runtime_authorized: false',
        'proxy_runtime_authorized: true',
        /proxy_runtime_authorized true/,
    ],
    [
        'staging_write_authorized=true 失败',
        'staging_write_authorized: false',
        'staging_write_authorized: true',
        /staging_write_authorized true/,
    ],
    [
        'source_manifest_write_authorized=true 失败',
        'source_manifest_write_authorized: false',
        'source_manifest_write_authorized: true',
        /source_manifest_write_authorized true/,
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
        'authorization_decision 不是 not_authorized 失败',
        'authorization_decision: not_authorized',
        'authorization_decision: authorized',
        /authorization_decision not not_authorized/,
    ],
    [
        'final_human_confirmation=true 失败',
        'final_human_confirmation: false',
        'final_human_confirmation: true',
        /final_human_confirmation true/,
    ],
    [
        'codex_may_not_self_fill_target=false 失败',
        'codex_may_not_self_fill_target: true',
        'codex_may_not_self_fill_target: false',
        /codex_may_not_self_fill_target false/,
    ],
    [
        'codex_may_not_self_authorize_network=false 失败',
        'codex_may_not_self_authorize_network: true',
        'codex_may_not_self_authorize_network: false',
        /codex_may_not_self_authorize_network false/,
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
        'safety would_write_packet_file=true 失败',
        'would_write_packet_file: false',
        'would_write_packet_file: true',
        /safety would_write_packet_file not false/,
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

test('valid template preview 成功', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runMain(gate, [`--packet=${PACKET_PATH}`], buildDependencies());
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr, '');
    const payload = extractJson(result.stdout);
    assert.equal(payload.ok, true);
    assert.deepEqual(payload.authorization_blocking_reasons, gate.EXPECTED_BLOCKING_REASONS);
    assertSafePayload(payload);
});

test('--commit blocked', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runMain(gate, [`--packet=${PACKET_PATH}`, '--commit'], buildDependencies());
    assert.equal(result.status, 1);
    assert.equal(result.stdout, '');
    assert.match(result.stderr, /BLOCKED: FotMob stdout-only network dry-run authorization packet is not executable/);
});

test('Makefile preview 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-fotmob-stdout-network-dry-run-authorization-packet-preview',
            'FOTMOB_STDOUT_NETWORK_AUTH_PACKET_NODE=node',
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
            'data-fotmob-stdout-network-dry-run-authorization-packet-commit',
            `PACKET=${PACKET_PATH}`,
            'CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_AUTHORIZATION_PACKET=1',
        ],
        { cwd: PROJECT_ROOT, encoding: 'utf8', shell: false }
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not executable in Phase 4\.99F/);
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

test('adapter import and validation do not import legacy runtime, browser, proxy, DB, or child process paths', t => {
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
