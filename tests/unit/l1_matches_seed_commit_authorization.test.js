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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l1_matches_seed_commit_authorization.js');
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
        throw new Error(`${name} should not be called by l1_matches_seed_commit_authorization`);
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

async function runCli(gate, argv) {
    let stdout = '';
    let stderr = '';
    const status = await gate.runCli(argv, {
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });
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
        '--user-authorized-matches-seed-commit=yes',
        '--allow-matches-write-next-phase=yes',
        '--allow-db-write-now=no',
        '--allow-raw-match-data-write=no',
        '--allow-training=no',
        '--allow-prediction=no',
        '--final-human-confirmation=yes',
        ...overrides,
    ];
}

test('valid authorization input succeeds and emits authorization-only payload', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, validArgv());
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.phase, 'PHASE5_07L1_CONTROLLED_MATCHES_SEED_COMMIT_AUTHORIZATION');
    assert.equal(payload.authorization_only, true);
    assert.equal(payload.authorization_status, 'authorized_for_next_phase_only');
    assert.equal(payload.source, 'fotmob');
    assert.equal(payload.scope, 'league_season_date');
    assert.equal(payload.league_id, '53');
    assert.equal(payload.season, '2025/2026');
    assert.equal(payload.date, '2026-05-10');
    assert.equal(payload.candidate_count, 8);
    assert.equal(payload.max_seed_rows, 10);
    assert.equal(payload.contains_target_match_id, '4830746');
    assert.equal(payload.contains_target_label, 'Angers vs Strasbourg');
    assert.equal(payload.user_authorized_matches_seed_commit, true);
    assert.equal(payload.matches_seed_commit_authorization_recorded, true);
    assert.equal(payload.matches_seed_commit_ready_for_next_phase, true);
    assert.equal(payload.commit_allowed_this_phase, false);
    assert.equal(payload.db_write_allowed_this_phase, false);
    assert.equal(payload.matches_write_allowed_this_phase, false);
    assert.equal(payload.matches_write_allowed_next_phase, true);
    assert.equal(payload.raw_match_data_write_allowed, false);
    assert.equal(payload.training_allowed, false);
    assert.equal(payload.prediction_allowed, false);
    assert.equal(payload.final_human_confirmation, true);
    assert.deepEqual(payload.affected_scope, {
        source: 'fotmob',
        league_id: '53',
        season: '2025/2026',
        date: '2026-05-10',
        max_rows: 10,
    });
    assert.ok(payload.pre_commit_baseline_requirements.includes('main CI green'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('clean worktree'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('DB row counts baseline'));
    assert.ok(
        payload.pre_commit_baseline_requirements.includes('affected candidate set reloaded or explicitly supplied')
    );
    assert.ok(payload.pre_commit_baseline_requirements.includes('affected existing matches SELECT'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('rows <= 10'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('source=fotmob'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('league_id=53'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('season=2025/2026'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('date=2026-05-10'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('no raw_match_data write'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('no feature/prediction write'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('rollback plan acknowledged'));
    assert.ok(payload.pre_commit_baseline_requirements.includes('post-commit verification plan acknowledged'));
    assert.ok(payload.authorization_gates.includes('user_authorized_matches_seed_commit=true'));
    assert.ok(payload.authorization_gates.includes('final_human_confirmation=true'));
    assert.ok(payload.authorization_gates.includes('allow_db_write_now=false'));
    assert.ok(payload.authorization_gates.includes('allow_matches_write_next_phase=true'));
    assert.ok(payload.authorization_gates.includes('allow_raw_match_data_write=false'));
    assert.ok(payload.authorization_gates.includes('allow_training=false'));
    assert.ok(payload.authorization_gates.includes('allow_prediction=false'));
    assert.ok(payload.authorization_gates.includes('commit_this_phase=false'));
    assert.ok(payload.blocked_actions_this_phase.includes('write_matches'));
    assert.ok(payload.blocked_actions_this_phase.includes('execute_db_write'));
    assert.ok(payload.blocked_actions_this_phase.includes('write_raw_match_data'));
    assert.ok(payload.blocked_actions_this_phase.includes('call_fixture_repository_persist'));
    assert.ok(payload.blocked_actions_this_phase.includes('run_titan_discovery'));
    assert.ok(payload.blocked_actions_this_phase.includes('run_discovery_service_discover'));
    assert.ok(payload.blocked_actions_this_phase.includes('harvest'));
    assert.ok(payload.blocked_actions_this_phase.includes('ingest'));
    assert.ok(payload.blocked_actions_this_phase.includes('training'));
    assert.ok(payload.blocked_actions_this_phase.includes('prediction'));
    assert.ok(
        payload.next_phase_requirements.includes('regenerate exact candidate set or use captured candidate payload')
    );
    assert.ok(payload.next_phase_requirements.includes('SELECT existing affected match rows'));
    assert.ok(payload.next_phase_requirements.includes('show would_insert / would_update / would_skip'));
    assert.ok(payload.next_phase_requirements.includes('require user final execution confirmation'));
    assert.ok(payload.next_phase_requirements.includes('execute in transaction'));
    assert.ok(payload.next_phase_requirements.includes('verify matches row delta / affected rows'));
    assert.ok(payload.next_phase_requirements.includes('verify raw_match_data unchanged'));
    assert.ok(payload.next_phase_requirements.includes('verify features/predictions unchanged'));
    assert.equal(payload.would_write_matches, false);
    assert.equal(payload.would_write_raw_match_data, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_call_fixture_repository_persist, false);
    assert.equal(payload.would_call_discovery_service_discover, false);
    assert.equal(payload.would_run_titan_discovery, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.commit_gate, 'blocked_this_phase');
    assert.equal(payload.next_required_phase, 'Phase 5.08L1 controlled matches seed commit execution');
});

test('validation failures and blocked flags are rejected', async t => {
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
            argv: validArgv().filter(arg => !arg.startsWith('--contains-target-match-id=')),
            pattern: /missing contains-target-match-id/i,
        },
        {
            argv: validArgv().filter(arg => !arg.startsWith('--contains-target-label=')),
            pattern: /missing contains-target-label/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--user-authorized-matches-seed-commit=')),
                '--user-authorized-matches-seed-commit=no',
            ],
            pattern: /user-authorized-matches-seed-commit must be yes/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--final-human-confirmation=')),
                '--final-human-confirmation=no',
            ],
            pattern: /final-human-confirmation must be yes/i,
        },
        { argv: [...validArgv(), '--allow-db-write-now=yes'], pattern: /allow-db-write-now=yes/i },
        {
            argv: [...validArgv(), '--allow-raw-match-data-write=yes'],
            pattern: /allow-raw-match-data-write=yes/i,
        },
        { argv: [...validArgv(), '--allow-training=yes'], pattern: /allow-training=yes/i },
        { argv: [...validArgv(), '--allow-prediction=yes'], pattern: /allow-prediction=yes/i },
        { argv: [...validArgv(), '--commit=yes'], pattern: /authorization-only/i },
        { argv: [...validArgv(), '--execute=yes'], pattern: /execute=yes/i },
    ];

    for (const { argv, pattern } of cases) {
        const result = await runCli(gate, argv);
        const payload = parseJsonOutput(result.stdout);
        assert.equal(result.status, 1);
        assert.match(payload.errors.join('\n'), pattern);
        assert.equal(payload.authorization_only, true);
        assert.equal(payload.would_write_matches, false);
        assert.equal(payload.would_write_raw_match_data, false);
        assert.equal(payload.would_write_db, false);
        assert.equal(payload.would_call_fixture_repository_persist, false);
        assert.equal(payload.would_call_discovery_service_discover, false);
        assert.equal(payload.would_run_titan_discovery, false);
    }
});

test('helpers normalize inputs and build expected authorization metadata', () => {
    const gate = loadModuleFresh();
    const options = gate.parseArgs([
        '--source=fotmob',
        '--scope=controlled_candidates_preview',
        '--league-id',
        '53',
        '--candidate-count',
        '8',
        '--contains-target-match-id',
        '4830746',
        '--contains-target-label',
        'Angers vs Strasbourg',
        '--user-authorized-matches-seed-commit=yes',
        '--allow-matches-write-next-phase=yes',
        '--allow-db-write-now=no',
        '--allow-raw-match-data-write=no',
        '--allow-training=no',
        '--allow-prediction=no',
        '--final-human-confirmation=yes',
        '--commit=no',
        '--execute=no',
    ]);

    assert.equal(options.scope, 'controlled_candidates_preview');
    assert.equal(options.leagueId, '53');
    assert.equal(options.userAuthorizedMatchesSeedCommit, true);
    assert.equal(gate.normalizeBooleanFlag('yes'), true);
    assert.equal(gate.normalizeBooleanFlag('no'), false);

    const validation = gate.validateAuthorizationInput({
        ...options,
        season: '2025/2026',
        date: '2026-05-10',
        maxSeedRows: '10',
    });
    assert.equal(validation.ok, true);
    assert.deepEqual(gate.buildAffectedScope(validation.value), {
        source: 'fotmob',
        league_id: '53',
        season: '2025/2026',
        date: '2026-05-10',
        max_rows: 10,
    });
    assert.ok(gate.buildAuthorizationGates(validation.value).includes('commit_this_phase=false'));
    assert.ok(gate.buildBlockedActionsThisPhase().includes('write_matches'));
    assert.ok(gate.buildNextPhaseRequirements().includes('execute in transaction'));
    assert.ok(gate.buildNextPhaseRequirements().includes('verify raw_match_data unchanged'));
});

test('script stays side-effect free on success and failure paths', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();

    const success = await runCli(gate, validArgv());
    const blocked = await runCli(gate, [...validArgv(), '--execute=yes']);

    assert.equal(success.status, 0);
    assert.equal(blocked.status, 1);
});

test('Makefile authorization target is registered and commit target remains blocked', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');

    assert.match(makefile, /^data-l1-matches-seed-commit-authorization:/m);
    assert.match(makefile, /scripts\/ops\/l1_matches_seed_commit_authorization\.js/);
    assert.match(makefile, /^data-l1-matches-seed-commit:/m);
    assert.match(makefile, /authorization-only in Phase 5\.07L1/);
});
