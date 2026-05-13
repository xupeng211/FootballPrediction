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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l1_matches_seed_commit_execution_preflight.js');
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
        throw new Error(`${name} should not be called by l1_matches_seed_commit_execution_preflight`);
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
        if (['redis', 'ioredis', 'playwright', 'playwright-core'].includes(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/FixtureRepository|titan_discovery/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (request === 'pg') {
            return {
                Pool: class FakePool {
                    async query(text) {
                        if (!/^\s*SELECT\b/i.test(String(text || ''))) {
                            throw new Error('pg write query is blocked in unit tests');
                        }
                        return { rows: [] };
                    }
                    async end() {}
                },
            };
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
        '--candidate-count=2',
        '--contains-target-match-id=4830746',
        '--contains-target-label=Angers vs Strasbourg',
        '--max-seed-rows=10',
        '--final-db-write-confirmation=no',
        '--allow-db-write-now=no',
        '--allow-matches-write-now=no',
        '--allow-raw-match-data-write=no',
        '--allow-training=no',
        '--allow-prediction=no',
        ...overrides,
    ];
}

function validCandidates() {
    return [
        {
            match_id: '53_20252026_4830746',
            external_id: '4830746',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Angers',
            away_team: 'Strasbourg',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Brest',
            away_team: 'Nice',
            match_date: '2026-05-10T21:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
    ];
}

test('valid execution preflight input succeeds', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, validArgv(), {
        candidates: validCandidates(),
        existingMatches: [],
    });
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.phase, 'PHASE5_08L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION_PREFLIGHT');
    assert.equal(payload.execution_preflight_only, true);
    assert.equal(payload.final_db_write_confirmation_required, true);
    assert.equal(payload.commit_allowed_this_phase, false);
    assert.equal(payload.db_write_allowed_this_phase, false);
    assert.equal(payload.matches_write_allowed_this_phase, false);
    assert.equal(payload.raw_match_data_write_allowed, false);
    assert.equal(payload.would_write_matches, false);
    assert.equal(payload.would_write_raw_match_data, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_call_fixture_repository_persist, false);
    assert.equal(payload.would_call_discovery_service_discover, false);
    assert.equal(payload.would_run_titan_discovery, false);
    assert.equal(payload.exact_candidate_set_captured, true);
    assert.equal(payload.affected_matches_selected, true);
    assert.equal(payload.would_insert_count, 2);
    assert.equal(payload.would_update_count, 0);
    assert.equal(payload.would_skip_count, 0);
    assert.equal(payload.affected_preview.length, 2);
    assert.equal(payload.affected_preview[0].decision, 'would_insert');
    assert.match(JSON.stringify(payload.transaction_plan), /BEGIN/);
    assert.match(JSON.stringify(payload.transaction_plan), /COMMIT only after final confirmation in next phase/);
    assert.match(JSON.stringify(payload.transaction_plan), /ROLLBACK on error/);
    assert.equal(payload.backup_plan.pg_dump_allowed_this_phase, false);
    assert.equal(payload.backup_plan.backup_file_write_allowed_this_phase, false);
    assert.equal(payload.rollback_plan.delete_allowed_this_phase, false);
    assert.equal(payload.rollback_plan.rollback_file_write_allowed_this_phase, false);
    assert.equal(payload.post_commit_verification_plan.raw_match_data_unchanged, true);
    assert.equal(payload.post_commit_verification_plan.l3_features_unchanged, true);
    assert.equal(payload.post_commit_verification_plan.match_features_training_unchanged, true);
    assert.equal(payload.post_commit_verification_plan.predictions_unchanged, true);
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
        { argv: [...validArgv(), '--final-db-write-confirmation=yes'], pattern: /final-db-write-confirmation=yes/i },
        { argv: [...validArgv(), '--allow-db-write-now=yes'], pattern: /allow-db-write-now=yes/i },
        {
            argv: [...validArgv(), '--allow-matches-write-now=yes'],
            pattern: /allow-matches-write-now=yes/i,
        },
        {
            argv: [...validArgv(), '--allow-raw-match-data-write=yes'],
            pattern: /allow-raw-match-data-write=yes/i,
        },
        { argv: [...validArgv(), '--allow-training=yes'], pattern: /allow-training=yes/i },
        { argv: [...validArgv(), '--allow-prediction=yes'], pattern: /allow-prediction=yes/i },
        { argv: [...validArgv(), '--commit=yes'], pattern: /preflight-only/i },
        { argv: [...validArgv(), '--execute=yes'], pattern: /execute=yes/i },
    ];

    for (const { argv, pattern } of cases) {
        const result = await runCli(gate, argv, {
            candidates: validCandidates(),
            existingMatches: [],
        });
        const payload = parseJsonOutput(result.stdout);
        assert.equal(result.status, 1);
        assert.match(payload.errors.join('\n'), pattern);
        assert.equal(payload.execution_preflight_only, true);
        assert.equal(payload.would_write_matches, false);
        assert.equal(payload.would_write_raw_match_data, false);
        assert.equal(payload.would_write_db, false);
        assert.equal(payload.would_call_fixture_repository_persist, false);
        assert.equal(payload.would_call_discovery_service_discover, false);
        assert.equal(payload.would_run_titan_discovery, false);
    }
});

test('candidate normalization, existing matches normalization and affected preview decisions work', () => {
    const gate = loadModuleFresh();
    const candidates = gate.normalizeCandidates([
        {
            match_id: '53_20252026_4830746',
            external_id: '4830746',
            league: 'Ligue 1',
            season: '2025/2026',
            home: 'Angers',
            away: 'Strasbourg',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'Scheduled',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Brest',
            away_team: 'Nice',
            match_date: '2026-05-10T21:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830748',
            external_id: '4830748',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Lille',
            away_team: 'Monaco',
            match_date: '2026-05-10T22:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
    ]);
    const existingMatches = gate.normalizeExistingMatches([
        {
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Brest',
            away_team: 'Nice',
            match_date: '2026-05-10T21:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830748',
            external_id: '4830748',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Lille',
            away_team: 'Monaco',
            match_date: '2026-05-10T22:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
    ]);
    const preview = gate.buildAffectedPreview(candidates, existingMatches);

    assert.equal(candidates[0].status, 'scheduled');
    assert.equal(existingMatches[0].match_id, '53_20252026_4830747');
    assert.equal(preview[0].decision, 'would_insert');
    assert.equal(preview[0].existing_row_found, false);
    assert.equal(preview[1].decision, 'would_skip');
    assert.equal(preview[1].existing_row_found, true);
    assert.equal(preview[2].decision, 'would_update');
    assert.match(preview[2].reason, /status/);
});

test('counts and policy builders expose expected values', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const result = await gate.buildMatchesSeedExecutionPreflight(
        {
            source: 'fotmob',
            scope: 'league_season_date',
            leagueId: '53',
            season: '2025/2026',
            date: '2026-05-10',
            candidateCount: '2',
            containsTargetMatchId: '4830746',
            containsTargetLabel: 'Angers vs Strasbourg',
            maxSeedRows: '10',
            finalDbWriteConfirmation: 'no',
            allowDbWriteNow: 'no',
            allowMatchesWriteNow: 'no',
            allowRawMatchDataWrite: 'no',
            allowTraining: 'no',
            allowPrediction: 'no',
        },
        {
            candidates: validCandidates(),
            existingMatches: [
                {
                    match_id: '53_20252026_4830747',
                    external_id: '4830747',
                    league_name: 'Ligue 1',
                    season: '2025/2026',
                    home_team: 'Brest',
                    away_team: 'Nice',
                    match_date: '2026-05-10T21:00:00.000Z',
                    status: 'finished',
                    data_source: 'FotMob',
                },
            ],
        }
    );

    assert.equal(result.would_insert_count, 1);
    assert.equal(result.would_update_count, 1);
    assert.equal(result.would_skip_count, 0);
    assert.equal(result.execution_preflight_only, true);
    assert.equal(result.final_db_write_confirmation_required, true);
    assert.equal(result.commit_allowed_this_phase, false);
    assert.equal(result.db_write_allowed_this_phase, false);
    assert.equal(result.matches_write_allowed_this_phase, false);
    assert.equal(result.raw_match_data_write_allowed, false);
    assert.equal(result.would_write_matches, false);
    assert.equal(result.would_write_raw_match_data, false);
    assert.equal(result.would_write_db, false);
    assert.equal(result.would_call_fixture_repository_persist, false);
    assert.equal(result.would_call_discovery_service_discover, false);
    assert.equal(result.would_run_titan_discovery, false);
    assert.match(JSON.stringify(gate.buildTransactionPlan({ maxSeedRows: 10 })), /BEGIN/);
    assert.match(
        JSON.stringify(gate.buildTransactionPlan({ maxSeedRows: 10 })),
        /COMMIT only after final confirmation in next phase/
    );
    assert.match(JSON.stringify(gate.buildBackupPlan()), /pg_dump_allowed_this_phase/);
    assert.match(JSON.stringify(gate.buildRollbackPlan()), /delete_allowed_this_phase/);
    assert.match(JSON.stringify(gate.buildPostCommitVerificationPlan()), /raw_match_data_unchanged/);
});

test('Makefile preflight target is registered and commit target remains blocked', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l1-matches-seed-commit-execution-preflight:/m);
    assert.match(makefile, /scripts\/ops\/l1_matches_seed_commit_execution_preflight\.js/);
    assert.match(makefile, /^data-l1-matches-seed-commit:/m);
    assert.match(makefile, /authorization-only in Phase 5\.07L1|execution preflight/i);
});
