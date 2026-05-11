'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fotmob_single_target_adapter_scaffold.js');
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

const BOOLEAN_FIELDS = [
    'terms_approval',
    'network_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'allow_db_write',
    'allow_training',
    'allow_prediction',
    'final_human_confirmation',
];

const WOULD_FALSE_FIELDS = [
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

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalConnect = net.connect;
    const originalCreateConnection = net.createConnection;
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
        throw new Error(`${name} should not be called by fotmob_single_target_adapter_scaffold`);
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
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
            'chromium',
            'http',
            'node:http',
            'https',
            'node:https',
            'net',
            'node:net',
            'child_process',
            'node:child_process',
        ]);
        const blockedFragments = [
            'titan_discovery',
            'run_production',
            'batch_historical_backfill',
            'backfill_historical_raw_match_data',
            'titan_seeder',
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
        net.connect = originalConnect;
        net.createConnection = originalCreateConnection;
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

function loadFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function baseInput(overrides = {}) {
    return {
        target_source: 'fotmob',
        target_scope_type: 'match_id',
        target_match_id: 'sample-match-001',
        terms_approval: 'no',
        network_authorization: 'no',
        allow_browser_runtime: 'no',
        allow_proxy_runtime: 'no',
        allow_external_network: 'no',
        allow_staging_write: 'no',
        allow_db_write: 'no',
        allow_training: 'no',
        allow_prediction: 'no',
        final_human_confirmation: 'no',
        ...overrides,
    };
}

function cliArgs(input) {
    const args = [];
    for (const [key, value] of Object.entries(input)) {
        if (key === 'commit' && value) {
            args.push('--commit');
        } else if (Array.isArray(value)) {
            for (const item of value) {
                args.push(`--${key.replace(/_/g, '-')}=${item}`);
            }
        } else {
            args.push(`--${key.replace(/_/g, '-')}=${value}`);
        }
    }
    return args;
}

function runCli(gate, input) {
    let stdout = '';
    let stderr = '';
    const status = gate.runCli(cliArgs(input), {
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });
    return {
        status,
        stdout,
        stderr,
        payload: stdout ? JSON.parse(stdout) : null,
    };
}

function assertSafePayload(payload) {
    assert.equal(payload.adapter_scaffold_only, true);
    assert.equal(payload.target_source, 'fotmob');
    assert.equal(payload.target_count, 1);
    assert.equal(payload.single_target, true);
    assert.equal(payload.bulk_scope_allowed, false);
    assert.equal(payload.max_targets, 1);
    assert.equal(payload.trusted_adapter_ready, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.network_dry_run_execution_allowed, false);
    assert.equal(payload.commit_gate, 'blocked');

    for (const field of WOULD_FALSE_FIELDS) {
        assert.equal(payload[field], false, `${field} must remain false`);
    }
}

test('valid match_id preflight succeeds and returns stdout-only safety JSON', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runCli(gate, baseInput());

    assert.equal(result.status, 0);
    assert.equal(result.stderr, '');
    assert.equal(result.payload.phase, gate.PHASE);
    assert.equal(result.payload.target_scope_type, 'match_id');
    assert.equal(result.payload.target_match_id, 'sample-match-001');
    assertSafePayload(result.payload);
});

test('valid league_season_date preflight succeeds', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runCli(
        gate,
        baseInput({
            target_scope_type: 'league_season_date',
            target_match_id: undefined,
            target_league: 'premier-league',
            target_season: '2025-2026',
            target_date: '2026-05-11',
        })
    );

    assert.equal(result.status, 0);
    assert.equal(result.payload.target_scope_type, 'league_season_date');
    assert.equal(result.payload.target_league, 'premier-league');
    assert.equal(result.payload.target_season, '2025-2026');
    assert.equal(result.payload.target_date, '2026-05-11');
    assertSafePayload(result.payload);
});

test('target-source must be fotmob', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const validation = gate.validateSingleTargetInput(baseInput({ target_source: 'other' }));

    assert.equal(validation.valid, false);
    assert.match(validation.errors.join('\n'), /target-source must be "fotmob"/);
});

test('target-scope-type is required and must be supported', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const missing = gate.validateSingleTargetInput(baseInput({ target_scope_type: undefined }));
    const unsupported = gate.validateSingleTargetInput(baseInput({ target_scope_type: 'bulk' }));

    assert.equal(missing.valid, false);
    assert.match(missing.errors.join('\n'), /target-scope-type is required/);
    assert.equal(unsupported.valid, false);
    assert.match(unsupported.errors.join('\n'), /unsupported --target-scope-type "bulk"/);
});

test('match_id scope requires exactly one target-match-id', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const missing = gate.validateSingleTargetInput(baseInput({ target_match_id: undefined }));
    const duplicate = gate.validateSingleTargetInput(baseInput({ target_match_id: ['a', 'b'] }));
    const commaSeparated = gate.validateSingleTargetInput(baseInput({ target_match_id: 'a,b' }));

    assert.equal(missing.valid, false);
    assert.match(missing.errors.join('\n'), /target-match-id is required/);
    assert.equal(duplicate.valid, false);
    assert.match(duplicate.errors.join('\n'), /single-target only/);
    assert.equal(commaSeparated.valid, false);
    assert.match(commaSeparated.errors.join('\n'), /single-target only/);
});

test('league_season_date requires league, season, and date', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const base = {
        target_scope_type: 'league_season_date',
        target_match_id: undefined,
        target_league: 'premier-league',
        target_season: '2025-2026',
        target_date: '2026-05-11',
    };
    const missingLeague = gate.validateSingleTargetInput(baseInput({ ...base, target_league: undefined }));
    const missingSeason = gate.validateSingleTargetInput(baseInput({ ...base, target_season: undefined }));
    const missingDate = gate.validateSingleTargetInput(baseInput({ ...base, target_date: undefined }));

    assert.equal(missingLeague.valid, false);
    assert.match(missingLeague.errors.join('\n'), /target-league is required/);
    assert.equal(missingSeason.valid, false);
    assert.match(missingSeason.errors.join('\n'), /target-season is required/);
    assert.equal(missingDate.valid, false);
    assert.match(missingDate.errors.join('\n'), /target-date is required/);
});

test('bulk scope and max_targets greater than one fail closed', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const targetCount = gate.validateSingleTargetInput(baseInput({ target_count: '2' }));
    const bulkScope = gate.validateSingleTargetInput(baseInput({ bulk_scope_allowed: 'yes' }));
    const maxTargets = gate.validateSingleTargetInput(baseInput({ max_targets: '2' }));

    assert.equal(targetCount.valid, false);
    assert.match(targetCount.errors.join('\n'), /target-count must be 1/);
    assert.equal(bulkScope.valid, false);
    assert.match(bulkScope.errors.join('\n'), /bulk-scope-allowed must remain false/);
    assert.equal(maxTargets.valid, false);
    assert.match(maxTargets.errors.join('\n'), /max-targets must be 1/);
});

test('yes authorization flags are accepted as input but ignored by Phase 4.97F policy', t => {
    installExecutionGuards(t);
    const gate = loadFresh();

    for (const field of BOOLEAN_FIELDS) {
        const payload = gate.buildPreflightSummary(baseInput({ [field]: 'yes' }));
        assertSafePayload(payload);
        assert.equal(payload.ignored_yes_flags.includes(field), true);
        assert.equal(payload.network_dry_run_ready, false);
    }
});

test('all-yes CLI remains blocked no-op and does not authorize execution', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const allYes = {};
    for (const field of BOOLEAN_FIELDS) {
        allYes[field] = 'yes';
    }
    const result = runCli(gate, baseInput(allYes));

    assert.equal(result.status, 0);
    assert.equal(result.payload.adapter_scaffold_only, true);
    assert.equal(result.payload.ignored_yes_flags.length, BOOLEAN_FIELDS.length);
    assertSafePayload(result.payload);
});

test('--commit is blocked and exits non-zero', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    let stdout = '';
    let stderr = '';
    const status = gate.runCli(['--commit'], {
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });

    assert.equal(status, 1);
    assert.equal(stdout, '');
    assert.match(stderr, /BLOCKED: FotMob trusted single-target adapter scaffold is not executable/);
});

test('default networkClient.fetch and dryRunFetchSingleTarget are disabled', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const adapter = gate.createFotMobSingleTargetAdapter();

    assert.throws(
        () => adapter.dependencies.networkClient.fetch('https://example.invalid'),
        /Network access is disabled/
    );
    assert.throws(() => adapter.dryRunFetchSingleTarget(), /Network dry-run execution is disabled/);
    assert.deepEqual(adapter.parsePreview({}), {
        parser_stub_only: true,
        parsed_remote_response: false,
    });
});

test('adapter import and preflight do not import or execute legacy runtime, browser, proxy, DB, files, or child process paths', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const result = runCli(gate, baseInput());

    assert.equal(result.status, 0);
    assertSafePayload(result.payload);
    for (const legacyPath of LEGACY_PATHS) {
        assert.equal(require.cache[legacyPath], undefined, `${legacyPath} must not be loaded`);
    }
});

test('parseArgs supports equals and space forms while preserving duplicate target detection', t => {
    installExecutionGuards(t);
    const gate = loadFresh();
    const parsed = gate.parseArgs([
        '--target-source=fotmob',
        '--target-scope-type',
        'match_id',
        '--target-match-id=a',
        '--target-match-id=b',
    ]);

    assert.equal(parsed.target_source, 'fotmob');
    assert.equal(parsed.target_scope_type, 'match_id');
    assert.deepEqual(parsed.target_match_id, ['a', 'b']);
    assert.equal(gate.validateSingleTargetInput(baseInput(parsed)).valid, false);
});
