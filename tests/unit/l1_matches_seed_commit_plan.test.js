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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l1_matches_seed_commit_plan.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function installNoSideEffectGuards(t) {
    const originalFetch = global.fetch;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalNetConnect = net.connect;
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
        throw new Error(`${name} should not be called by l1_matches_seed_commit_plan`);
    };

    global.fetch = fail('global.fetch');
    http.request = fail('http.request');
    https.request = fail('https.request');
    net.connect = fail('net.connect');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');

    Module._load = function patchedLoad(request, parent, isMain) {
        if (['pg', 'redis', 'ioredis', 'playwright', 'playwright-core'].includes(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/FixtureRepository|titan_discovery|DiscoveryService/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        global.fetch = originalFetch;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        net.connect = originalNetConnect;
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

async function runCli(gate, argv, dependencies = {}) {
    let stdout = '';
    let stderr = '';
    const status = await gate.runCli(
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

function parseJsonOutput(stdout) {
    const payload = String(stdout || '').trim();
    assert.notEqual(payload, '', 'expected JSON payload');
    return JSON.parse(payload);
}

function validArgv(overrides = []) {
    return [
        '--source=fotmob',
        '--scope=league_season_date',
        '--league-id=53',
        '--season=2025/2026',
        '--date=2026-05-10',
        '--candidate-count=8',
        '--contains-target-match-id=4830746',
        '--contains-target-label=Angers vs Strasbourg',
        '--max-seed-rows=10',
        '--commit=no',
        ...overrides,
    ];
}

function assertNoWriteFlags(payload) {
    assert.equal(payload.planning_only, true);
    assert.equal(payload.matches_seed_commit_ready, false);
    assert.equal(payload.matches_seed_commit_authorized, false);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.matches_write_allowed, false);
    assert.equal(payload.raw_match_data_write_allowed, false);
    assert.equal(payload.training_allowed, false);
    assert.equal(payload.prediction_allowed, false);
    assert.equal(payload.would_write_matches, false);
    assert.equal(payload.would_write_raw_match_data, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_call_fixture_repository_persist, false);
    assert.equal(payload.would_call_discovery_service_discover, false);
    assert.equal(payload.would_run_titan_discovery, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.commit_gate, 'blocked');
}

test('valid planning input succeeds and emits no-write plan', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, validArgv(), { env: {} });
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.phase, 'PHASE5_06L1_CONTROLLED_MATCHES_SEED_COMMIT_PLANNING');
    assert.equal(payload.source, 'fotmob');
    assert.equal(payload.scope, 'league_season_date');
    assert.equal(payload.league_id, '53');
    assert.equal(payload.season, '2025/2026');
    assert.equal(payload.date, '2026-05-10');
    assert.equal(payload.candidate_count_from_previous_preview, 8);
    assert.equal(payload.max_seed_rows, 10);
    assert.equal(payload.contains_target_match_id, '4830746');
    assert.equal(payload.contains_target_label, 'Angers vs Strasbourg');
    assertNoWriteFlags(payload);
});

test('validation failures are blocked', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const cases = [
        { argv: validArgv().filter(arg => !arg.startsWith('--source=')), pattern: /missing source/i },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--source=')), '--source=other'],
            pattern: /unsupported source/i,
        },
        { argv: validArgv().filter(arg => !arg.startsWith('--scope=')), pattern: /missing scope/i },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--scope=')), '--scope=bulk'],
            pattern: /unsupported scope/i,
        },
        { argv: validArgv().filter(arg => !arg.startsWith('--league-id=')), pattern: /missing league-id/i },
        { argv: validArgv().filter(arg => !arg.startsWith('--season=')), pattern: /missing season/i },
        { argv: validArgv().filter(arg => !arg.startsWith('--date=')), pattern: /missing date/i },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--candidate-count=')), '--candidate-count=11'],
            pattern: /candidate-count must be <= max-seed-rows/i,
        },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--max-seed-rows=')), '--max-seed-rows=11'],
            pattern: /max-seed-rows > 10/i,
        },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--commit=')), '--commit=yes'],
            pattern: /not executable/i,
        },
        { argv: [...validArgv(), '--allow-db-write=yes'], pattern: /allow-db-write=yes/i },
        { argv: [...validArgv(), '--allow-matches-write=yes'], pattern: /allow-matches-write=yes/i },
        {
            argv: [...validArgv(), '--allow-raw-match-data-write=yes'],
            pattern: /allow-raw-match-data-write=yes/i,
        },
        { argv: [...validArgv(), '--training=yes'], pattern: /training=yes/i },
        { argv: [...validArgv(), '--prediction=yes'], pattern: /prediction=yes/i },
    ];

    for (const { argv, pattern } of cases) {
        const result = await runCli(gate, argv, { env: {} });
        const payload = parseJsonOutput(result.stdout);
        assert.equal(result.status, 1);
        assert.match(payload.errors.join('\n'), pattern);
        assert.equal(payload.would_write_db, false);
        assert.equal(payload.would_write_matches, false);
        assert.equal(payload.would_write_raw_match_data, false);
    }
});

test('environment write and model flags are blocked', () => {
    const gate = loadModuleFresh();
    for (const [envKey, pattern] of [
        ['DB_WRITE', /allow-db-write=yes/i],
        ['RAW_MATCH_DATA_WRITE', /allow-raw-match-data-write=yes/i],
        ['TRAINING', /training=yes/i],
        ['PREDICTION', /prediction=yes/i],
    ]) {
        const result = gate.validatePlanningInput(gate.parseArgs(validArgv()), { [envKey]: 'yes' });
        assert.equal(result.ok, false);
        assert.match(result.errors.join('\n'), pattern);
    }
});

test('mapping, upsert, backup, rollback and checks contain required controls', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const payload = gate.buildMatchesSeedCommitPlan(gate.parseArgs(validArgv()), {});
    const mappingText = JSON.stringify(payload.candidate_to_matches_mapping_policy);

    for (const field of ['match_id', 'external_id', 'home_team', 'away_team', 'match_date', 'status', 'data_source']) {
        assert.match(mappingText, new RegExp(field));
    }
    assert.ok(payload.candidate_to_matches_mapping_policy.forbidden_tables.includes('raw_match_data'));
    assert.ok(payload.candidate_to_matches_mapping_policy.forbidden_tables.includes('predictions'));
    assert.equal(payload.upsert_policy.identity_key, 'matches.match_id');
    assert.equal(payload.upsert_policy.transaction_required_for_future_commit, true);
    assert.equal(payload.upsert_policy.delete_allowed, false);
    assert.equal(payload.backup_policy.pg_dump_allowed_this_phase, false);
    assert.equal(payload.backup_policy.backup_file_write_allowed_this_phase, false);
    assert.equal(payload.rollback_policy.delete_execution_allowed_this_phase, false);
    assert.equal(payload.rollback_policy.runtime_rollback_file_write_allowed_this_phase, false);
    assert.ok(payload.pre_commit_checks.includes('user explicit authorization required'));
    assert.ok(payload.post_commit_checks.includes('raw_match_data unchanged'));
});

test('parseArgs and boolean normalization support expected flags', () => {
    const gate = loadModuleFresh();
    const options = gate.parseArgs([
        '--source=fotmob',
        '--scope=controlled_candidates_preview',
        '--league-id',
        '53',
        '--commit=no',
        '--training=false',
    ]);

    assert.equal(options.source, 'fotmob');
    assert.equal(options.scope, 'controlled_candidates_preview');
    assert.equal(options.leagueId, '53');
    assert.equal(options.commit, false);
    assert.equal(options.training, false);
    assert.equal(gate.normalizeBooleanFlag('yes'), true);
    assert.equal(gate.normalizeBooleanFlag('no'), false);
});

test('Makefile plan and blocked commit targets are registered', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l1-matches-seed-commit-plan:/m);
    assert.match(makefile, /scripts\/ops\/l1_matches_seed_commit_plan\.js/);
    assert.match(makefile, /^data-l1-matches-seed-commit:/m);
    assert.match(makefile, /L1 matches seed commit is not executable in Phase 5\.06L1/);
});
