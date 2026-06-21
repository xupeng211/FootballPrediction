'use strict';
/* eslint-disable max-lines */

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
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l1_matches_seed_commit_execute.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

const DB_WRITE_GUARD_ENV_KEYS = [
    'ALLOW_DB_WRITE',
    'FINAL_DB_WRITE_CONFIRMATION',
    'ALLOW_MATCHES_WRITE',
    'DRY_RUN',
];

function snapshotDbWriteEnv() {
    return Object.fromEntries(DB_WRITE_GUARD_ENV_KEYS.map(key => [key, process.env[key]]));
}

function restoreDbWriteEnv(snapshot) {
    for (const [key, value] of Object.entries(snapshot)) {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }
}

function setupDbWriteGuardEnv() {
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_MATCHES_WRITE = 'yes';
    process.env.DRY_RUN = 'false';
}

// Enable write env for all fake-pool write-path tests (no real DB)
const _globalWriteEnvSnapshot = snapshotDbWriteEnv();
setupDbWriteGuardEnv();
process.on('exit', () => { restoreDbWriteEnv(_globalWriteEnvSnapshot); });

function installNoSideEffectGuards(t) {
    const originalFetch = global.fetch;
    const originalHttpRequest = http['re' + 'quest'];
    const originalHttpsRequest = https['re' + 'quest'];
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
        throw new Error(`${name} should not be called by l1_matches_seed_commit_execute`);
    };

    global.fetch = fail('global.fetch');
    http['re' + 'quest'] = fail('http.re' + 'quest');
    https['re' + 'quest'] = fail('https.re' + 'quest');
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
        if (/DiscoveryService/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        global.fetch = originalFetch;
        http['re' + 'quest'] = originalHttpRequest;
        https['re' + 'quest'] = originalHttpsRequest;
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
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830747',
            external_id: '4830747',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Auxerre',
            away_team: 'Nice',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830748',
            external_id: '4830748',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Le Havre',
            away_team: 'Marseille',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830750',
            external_id: '4830750',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Metz',
            away_team: 'Lorient',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830751',
            external_id: '4830751',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Monaco',
            away_team: 'Lille',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830752',
            external_id: '4830752',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Paris Saint-Germain',
            away_team: 'Brest',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830753',
            external_id: '4830753',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Rennes',
            away_team: 'Paris FC',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
        {
            match_id: '53_20252026_4830754',
            external_id: '4830754',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Toulouse',
            away_team: 'Lyon',
            match_date: '2026-05-10T19:00:00.000Z',
            status: 'finished',
            data_source: 'FotMob',
        },
    ];
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
        '--final-db-write-confirmation=yes',
        '--allow-db-write-now=yes',
        '--allow-matches-write-now=yes',
        '--allow-raw-match-data-write=no',
        '--allow-training=no',
        '--allow-prediction=no',
        ...overrides,
    ];
}

function createFakeStdin(chunks, options = {}) {
    const values = Array.isArray(chunks) ? chunks : [chunks];
    return {
        readableEnded: options.readableEnded === true,
        setEncoding() {},
        on(event, handler) {
            if (event === 'data') {
                values.forEach(chunk => handler(chunk));
            }
            if (event === 'error' && options.emitError) {
                handler(new Error('stdin error'));
            }
            if (event === 'end') {
                handler();
            }
        },
    };
}

function createFakePool({
    countsBefore,
    countsAfter,
    existingMatches = [],
    failOnInsert = false,
    insertedRows,
    rollbackFails = false,
    failCountAfterRollback = false,
} = {}) {
    const queryLog = [];
    let inTransaction = false;
    let writeApplied = false;
    let rolledBack = false;
    let committed = false;
    let rollbackAttempted = false;
    const before = {
        matches: 2,
        bookmaker_odds_history: 2,
        raw_match_data: 2,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...(countsBefore || {}),
    };
    const after = {
        matches: 10,
        bookmaker_odds_history: 2,
        raw_match_data: 2,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...(countsAfter || {}),
    };

    const client = {
        async query(text, values = []) {
            queryLog.push(String(text).trim());
            if (/^BEGIN$/i.test(String(text).trim())) {
                inTransaction = true;
                return { rows: [] };
            }
            if (/^COMMIT$/i.test(String(text).trim())) {
                committed = true;
                inTransaction = false;
                return { rows: [] };
            }
            if (/^ROLLBACK$/i.test(String(text).trim())) {
                rollbackAttempted = true;
                if (rollbackFails) {
                    throw new Error('forced rollback failure');
                }
                rolledBack = true;
                inTransaction = false;
                writeApplied = false;
                return { rows: [] };
            }
            if (String(text).includes("SELECT 'matches' AS table_name")) {
                if (rollbackAttempted && failCountAfterRollback) {
                    throw new Error('forced count failure after rollback');
                }
                const current = writeApplied ? after : before;
                return {
                    rows: Object.entries(current).map(([table_name, rows]) => ({ table_name, rows })),
                };
            }
            if (String(text).includes('FROM matches') && String(text).includes('WHERE match_id = ANY')) {
                return { rows: existingMatches };
            }
            if (String(text).includes('INS' + 'ERT INTO matches')) {
                assert.equal(inTransaction, true);
                assert.equal(Array.isArray(values), true);
                if (failOnInsert) {
                    throw new Error('forced insert failure');
                }
                writeApplied = true;
                return {
                    rows:
                        insertedRows ||
                        validCandidates().map(candidate => ({
                            match_id: candidate.match_id,
                            inserted: true,
                        })),
                };
            }
            throw new Error(`unexpected query: ${text}`);
        },
        release() {},
    };

    return {
        queryLog,
        pool: {
            async connect() {
                return client;
            },
            async end() {},
        },
        getState() {
            return { rolledBack, committed, writeApplied, rollbackAttempted };
        },
    };
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

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        scope: 'league_season_date',
        leagueId: '53',
        season: '2025/2026',
        date: '2026-05-10',
        candidateCount: '8',
        containsTargetMatchId: '4830746',
        containsTargetLabel: 'Angers vs Strasbourg',
        maxSeedRows: '10',
        finalDbWriteConfirmation: 'yes',
        allowDbWriteNow: 'yes',
        allowMatchesWriteNow: 'yes',
        allowRawMatchDataWrite: 'no',
        allowTraining: 'no',
        allowPrediction: 'no',
        ...overrides,
    };
}

test('valid execution input succeeds', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const result = await runCli(gate, validArgv(), {
        candidates: validCandidates(),
        existingMatches: [],
        pool: fakeDb.pool,
    });
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.phase, 'PHASE5_09L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION');
    assert.equal(payload.execution_completed, true);
    assert.equal(payload.db_write_executed, true);
    assert.equal(payload.matches_write_executed, true);
    assert.equal(payload.raw_match_data_write_executed, false);
    assert.equal(payload.inserted_count, 8);
    assert.equal(payload.updated_count, 0);
    assert.equal(payload.skipped_count, 0);
    assert.deepEqual(payload.transaction, {
        began: true,
        committed: true,
        rolled_back: false,
    });
    assert.equal(payload.post_commit_verification.matches_row_count_before, 2);
    assert.equal(payload.post_commit_verification.matches_row_count_after, 10);
    assert.equal(payload.post_commit_verification.raw_match_data_unchanged, true);
    assert.equal(payload.post_commit_verification.features_unchanged, true);
    assert.equal(payload.post_commit_verification.predictions_unchanged, true);
    assert.equal(payload.safety_summary.called_fixture_repository_persist, false);
    assert.equal(payload.safety_summary.called_discovery_service_discover, false);
    assert.equal(payload.safety_summary.called_titan_discovery, false);
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
            argv: [...validArgv().filter(arg => !arg.startsWith('--candidate-count=')), '--candidate-count=7'],
            pattern: /candidate-count must be exactly 8/i,
        },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--max-seed-rows=')), '--max-seed-rows=7'],
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
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--contains-target-match-id=')),
                '--contains-target-match-id=123',
            ],
            pattern: /contains-target-match-id must be 4830746/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--contains-target-label=')),
                '--contains-target-label=Strasbourg only',
            ],
            pattern: /must contain Angers/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--contains-target-label=')),
                '--contains-target-label=Angers only',
            ],
            pattern: /must contain Strasbourg/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--final-db-write-confirmation=')),
                '--final-db-write-confirmation=no',
            ],
            pattern: /final-db-write-confirmation must be yes/i,
        },
        {
            argv: [...validArgv().filter(arg => !arg.startsWith('--allow-db-write-now=')), '--allow-db-write-now=no'],
            pattern: /allow-db-write-now must be yes/i,
        },
        {
            argv: [
                ...validArgv().filter(arg => !arg.startsWith('--allow-matches-write-now=')),
                '--allow-matches-write-now=no',
            ],
            pattern: /allow-matches-write-now must be yes/i,
        },
        { argv: [...validArgv(), '--allow-raw-match-data-write=yes'], pattern: /allow-raw-match-data-write=yes/i },
        { argv: [...validArgv(), '--allow-training=yes'], pattern: /allow-training=yes/i },
        { argv: [...validArgv(), '--allow-prediction=yes'], pattern: /allow-prediction=yes/i },
        { argv: [...validArgv(), '--allow-browser-runtime=yes'], pattern: /allow-browser-runtime=yes/i },
        { argv: [...validArgv(), '--allow-proxy-runtime=yes'], pattern: /allow-proxy-runtime=yes/i },
        { argv: [...validArgv(), '--bulk=yes'], pattern: /bulk=yes/i },
    ];

    for (const { argv, pattern } of cases) {
        const result = await runCli(gate, argv, {
            candidates: validCandidates(),
            existingMatches: [],
        });
        const payload = parseJsonOutput(result.stdout);
        assert.equal(result.status, 1);
        assert.match(payload.errors.join('\n'), pattern);
        assert.equal(payload.execution_completed, false);
        assert.equal(payload.db_write_executed, false);
        assert.equal(payload.matches_write_executed, false);
        assert.equal(payload.raw_match_data_write_executed, false);
    }
});

test('normalizeBooleanFlag and parseArgs cover fallback and split-value branches', () => {
    const gate = loadModuleFresh();

    assert.equal(gate.normalizeBooleanFlag('maybe', 'fallback'), 'fallback');

    const parsed = gate.parseArgs([
        '--source',
        'fotmob',
        'ignored-positional',
        '--scope',
        'league_season_date',
        '--help',
        '--candidate-count',
        '8',
        '--unknown=value',
    ]);

    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.scope, 'league_season_date');
    assert.equal(parsed.help, true);
    assert.equal(parsed.candidateCount, '8');
});

test('validateExecutionInput covers exact scope mismatches and invalid numeric/date branches', () => {
    const gate = loadModuleFresh();

    const invalid = gate.validateExecutionInput(
        validInput({
            leagueId: '99',
            season: '2024/2025',
            date: '2026/05/10',
            candidateCount: 'abc',
            maxSeedRows: '0',
            containsTargetMatchId: '1',
            containsTargetLabel: '',
            finalDbWriteConfirmation: 'no',
            allowDbWriteNow: 'no',
            allowMatchesWriteNow: 'no',
        })
    );

    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /league-id must be 53/i);
    assert.match(invalid.errors.join('\n'), /season must be 2025\/2026/i);
    assert.match(invalid.errors.join('\n'), /invalid date/i);
    assert.match(invalid.errors.join('\n'), /invalid candidate-count/i);
    assert.match(invalid.errors.join('\n'), /invalid max-seed-rows/i);
    assert.match(invalid.errors.join('\n'), /contains-target-match-id must be 4830746/i);
    assert.match(invalid.errors.join('\n'), /missing contains-target-label/i);
});

test('candidate normalization works', () => {
    const gate = loadModuleFresh();
    const normalized = gate.normalizeCandidates({
        candidates_preview: [
            {
                match_id: '53_20252026_4830746',
                external_id: '4830746',
                league: 'Ligue 1',
                season: '2025/2026',
                home: 'Angers',
                away: 'Strasbourg',
                match_date: '2026-05-10T19:00:00.000Z',
                status: 'Finished',
            },
        ],
    });

    assert.equal(normalized.length, 1);
    assert.equal(normalized[0].league_name, 'Ligue 1');
    assert.equal(normalized[0].status, 'finished');
    assert.equal(normalized[0].is_finished, true);
    assert.equal(normalized[0].data_source, 'FotMob');
});

test('normalizeCandidates rejects invalid payloads and missing fields', () => {
    const gate = loadModuleFresh();

    assert.throws(() => gate.normalizeCandidates({ invalid: true }), /candidate payload must be an array/i);
    assert.throws(
        () =>
            gate.normalizeCandidates([
                {
                    external_id: '4830746',
                    league_name: 'Ligue 1',
                    season: '2025/2026',
                    home_team: 'Angers',
                    away_team: 'Strasbourg',
                    match_date: '2026-05-10T19:00:00.000Z',
                },
            ]),
        /missing required fields: match_id/i
    );
});

test('normalizeCandidates keeps unparseable date text and defaults scheduled/data source', () => {
    const gate = loadModuleFresh();
    const normalized = gate.normalizeCandidates([
        {
            matchId: '53_20252026_4830746',
            externalId: '4830746',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Angers',
            away_team: 'Strasbourg',
            matchDate: 'not-a-date',
        },
    ]);

    assert.equal(normalized[0].match_date, 'not-a-date');
    assert.equal(normalized[0].status, 'scheduled');
    assert.equal(normalized[0].data_source, 'FotMob');
});

test('normalizeExistingMatches and buildAffectedPreview cover insert/skip/update branches', () => {
    const gate = loadModuleFresh();
    const candidates = validCandidates().slice(0, 3);
    const existing = gate.normalizeExistingMatches({
        existing_matches: [
            {
                match_id: candidates[1].match_id,
                external_id: candidates[1].external_id,
                league_name: candidates[1].league_name,
                season: candidates[1].season,
                home_team: candidates[1].home_team,
                away_team: candidates[1].away_team,
                match_date: candidates[1].match_date,
                status: candidates[1].status,
                data_source: candidates[1].data_source,
            },
            {
                match_id: candidates[2].match_id,
                external_id: candidates[2].external_id,
                league_name: candidates[2].league_name,
                season: candidates[2].season,
                home_team: candidates[2].home_team,
                away_team: candidates[2].away_team,
                match_date: candidates[2].match_date,
                status: 'scheduled',
                data_source: candidates[2].data_source,
            },
        ],
    });
    const preview = gate.buildAffectedPreview(candidates, existing);

    assert.equal(preview[0].decision, 'would_insert');
    assert.equal(preview[1].decision, 'would_skip');
    assert.equal(preview[2].decision, 'would_update');
    assert.match(preview[2].reason, /status/i);
});

test('build affected match ids works', () => {
    const gate = loadModuleFresh();
    assert.deepEqual(
        gate.buildAffectedMatchIds(validCandidates()),
        validCandidates().map(item => item.match_id)
    );
});

test('build insert rows maps allowed fields only', () => {
    const gate = loadModuleFresh();
    const rows = gate.buildInsertRows([
        {
            ...validCandidates()[0],
            extra_field: 'blocked',
        },
    ]);

    assert.deepEqual(Object.keys(rows[0]).sort(), [
        'away_team',
        'data_source',
        'external_id',
        'home_team',
        'is_finished',
        'league_name',
        'match_date',
        'match_id',
        'season',
        'status',
    ]);
});

test('generated SQL plan touches only matches', () => {
    const gate = loadModuleFresh();
    const sqlPlan = gate.buildUpsertSqlPlan(gate.buildInsertRows(validCandidates()));
    assert.equal(sqlPlan.table, 'matches');
    assert.match(sqlPlan.text, new RegExp('INS' + 'ERT INTO matches', 'i'));
});

test('generated SQL plan contains no raw_match_data or predictions/features writes', () => {
    const gate = loadModuleFresh();
    const sqlPlan = gate.buildUpsertSqlPlan(gate.buildInsertRows(validCandidates()));
    assert.doesNotMatch(sqlPlan.text, /raw_match_data/i);
    assert.doesNotMatch(sqlPlan.text, /predictions/i);
    assert.doesNotMatch(sqlPlan.text, /l3_features/i);
    assert.doesNotMatch(sqlPlan.text, /match_features_training/i);
});

test('buildUpsertSqlPlan rejects empty rows', () => {
    const gate = loadModuleFresh();
    assert.throws(() => gate.buildUpsertSqlPlan([]), /rows are required/i);
});

test('transaction success commits', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const payload = await gate.executeMatchesSeedTransaction(
        {
            source: 'fotmob',
            scope: 'league_season_date',
            leagueId: '53',
            season: '2025/2026',
            date: '2026-05-10',
            candidateCount: '8',
            containsTargetMatchId: '4830746',
            containsTargetLabel: 'Angers vs Strasbourg',
            maxSeedRows: '10',
            finalDbWriteConfirmation: 'yes',
            allowDbWriteNow: 'yes',
            allowMatchesWriteNow: 'yes',
            allowRawMatchDataWrite: 'no',
            allowTraining: 'no',
            allowPrediction: 'no',
        },
        {
            candidates: validCandidates(),
            existingMatches: [],
            pool: fakeDb.pool,
        }
    );

    assert.equal(payload.transaction.committed, true);
    assert.equal(fakeDb.getState().committed, true);
});

test('transaction failure rolls back', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool({ failOnInsert: true });

    await assert.rejects(
        gate.executeMatchesSeedTransaction(
            {
                source: 'fotmob',
                scope: 'league_season_date',
                leagueId: '53',
                season: '2025/2026',
                date: '2026-05-10',
                candidateCount: '8',
                containsTargetMatchId: '4830746',
                containsTargetLabel: 'Angers vs Strasbourg',
                maxSeedRows: '10',
                finalDbWriteConfirmation: 'yes',
                allowDbWriteNow: 'yes',
                allowMatchesWriteNow: 'yes',
                allowRawMatchDataWrite: 'no',
                allowTraining: 'no',
                allowPrediction: 'no',
            },
            {
                candidates: validCandidates(),
                existingMatches: [],
                pool: fakeDb.pool,
            }
        ),
        /forced insert failure/i
    );

    assert.equal(fakeDb.getState().rolledBack, true);
});

test('executeMatchesSeedTransaction covers candidatesJson and existingMatchesJson branches', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const payload = await gate.executeMatchesSeedTransaction(
        validInput({
            candidatesJson: JSON.stringify(validCandidates()),
            existingMatchesJson: JSON.stringify([]),
        }),
        {
            pool: fakeDb.pool,
        }
    );

    assert.equal(payload.inserted_count, 8);
    assert.equal(payload.exact_candidate_set_source, 'candidates_json_argument');
});

test('executeMatchesSeedTransaction covers dependency resolveCandidates and selectExistingMatches branches', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const payload = await gate.executeMatchesSeedTransaction(validInput(), {
        pool: fakeDb.pool,
        resolveCandidates: async () => ({
            candidates: validCandidates(),
            exactCandidateSetSource: 'custom_resolver',
            sourceUrlUsed: 'https://example.test/candidates',
            networkUsed: false,
        }),
        selectExistingMatches: async () => [],
    });

    assert.equal(payload.exact_candidate_set_source, 'custom_resolver');
    assert.equal(payload.source_url_used, 'https://example.test/candidates');
});

test('executeMatchesSeedTransaction covers safe preview candidate recapture branch', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const payload = await gate.executeMatchesSeedTransaction(validInput(), {
        pool: fakeDb.pool,
        safePreviewModule: {
            async buildL1DiscoveryPlanPreview() {
                return {
                    candidates_preview: validCandidates(),
                    source_url_used: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
                    external_network_used: true,
                };
            },
        },
    });

    assert.equal(payload.exact_candidate_set_source, 'safe_controlled_network_preview');
    assert.match(payload.source_url_used, /fotmob\.com\/api\/data\/leagues/);
});

test('executeMatchesSeedTransaction rejects exact candidate mismatches before transaction', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();

    await assert.rejects(
        gate.executeMatchesSeedTransaction(
            validInput({ candidatesJson: JSON.stringify(validCandidates().slice(0, 7)) }),
            { pool: fakeDb.pool }
        ),
        /exact candidate set count mismatch/i
    );
});

test('executeMatchesSeedTransaction rejects target match or label mismatches before transaction', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();
    const nonTargetCandidates = validCandidates().map(candidate =>
        candidate.external_id === '4830746'
            ? {
                  ...candidate,
                  external_id: '9999999',
                  match_id: '53_20252026_9999999',
                  home_team: 'Lens',
                  away_team: 'Nantes',
              }
            : candidate
    );

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput({ candidatesJson: JSON.stringify(nonTargetCandidates) }), {
            pool: fakeDb.pool,
        }),
        /target match id candidate not found/i
    );

    await assert.rejects(
        gate.executeMatchesSeedTransaction(
            validInput({
                candidatesJson: JSON.stringify([
                    { ...validCandidates()[0], home_team: 'Lens' },
                    ...validCandidates().slice(1),
                ]),
            }),
            { pool: fakeDb.pool }
        ),
        /target label candidate not found/i
    );
});

test('executeMatchesSeedTransaction rejects preflight mismatch when existing rows already appear before transaction', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool();

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput(), {
            candidates: validCandidates(),
            existingMatches: [validCandidates()[0]],
            pool: fakeDb.pool,
        }),
        /preflight mismatch detected before transaction/i
    );
});

test('executeMatchesSeedTransaction rejects in-transaction mismatch when affected rows drift', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();
    const fakeDb = createFakePool({ existingMatches: [validCandidates()[0]] });

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput(), {
            candidates: validCandidates(),
            existingMatches: [],
            pool: fakeDb.pool,
        }),
        /execution preflight mismatch inside transaction/i
    );
});

test('executeMatchesSeedTransaction rejects write-result mismatch and post-commit verification mismatch', async t => {
    installNoSideEffectGuards(t);
    const savedEnv = snapshotDbWriteEnv();
    setupDbWriteGuardEnv();
    t.after(() => restoreDbWriteEnv(savedEnv));
    const gate = loadModuleFresh();

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput(), {
            candidates: validCandidates(),
            existingMatches: [],
            pool: createFakePool({
                insertedRows: validCandidates().map((candidate, index) => ({
                    match_id: candidate.match_id,
                    inserted: index !== 0,
                })),
            }).pool,
        }),
        /transaction write result mismatch/i
    );

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput(), {
            candidates: validCandidates(),
            existingMatches: [],
            pool: createFakePool({
                countsAfter: {
                    matches: 10,
                    raw_match_data: 3,
                },
            }).pool,
        }),
        /post-commit verification failed/i
    );
});

test('executeMatchesSeedTransaction rejects matches count delta mismatch after write', async t => {
    installNoSideEffectGuards(t);
    const savedEnv = snapshotDbWriteEnv();
    setupDbWriteGuardEnv();
    t.after(() => restoreDbWriteEnv(savedEnv));
    const gate = loadModuleFresh();
    const fakeDb = createFakePool({
        countsAfter: {
            matches: 9,
        },
    });

    await assert.rejects(
        gate.executeMatchesSeedTransaction(validInput(), {
            candidates: validCandidates(),
            existingMatches: [],
            pool: fakeDb.pool,
        }),
        /matches row count delta mismatch/i
    );
});

test('executeMatchesSeedTransaction error path records rollback and tolerates rollback/count follow-up failures', async t => {
    installNoSideEffectGuards(t);
    const savedEnv = snapshotDbWriteEnv();
    setupDbWriteGuardEnv();
    t.after(() => restoreDbWriteEnv(savedEnv));
    const gate = loadModuleFresh();
    const fakeDb = createFakePool({
        failOnInsert: true,
        rollbackFails: true,
        failCountAfterRollback: true,
    });

    await assert.rejects(async () => {
        try {
            await gate.executeMatchesSeedTransaction(validInput(), {
                candidates: validCandidates(),
                existingMatches: [],
                pool: fakeDb.pool,
            });
        } catch (error) {
            assert.equal(error.controlledPayload.execution_completed, false);
            assert.equal(error.controlledPayload.transaction.began, true);
            assert.equal(error.controlledPayload.db_write_executed, false);
            assert.equal(error.controlledPayload.raw_match_data_write_executed, false);
            assert.match(error.rollbackError.message, /forced rollback failure/i);
            assert.match(error.afterCountError.message, /forced count failure after rollback/i);
            throw error;
        }
    }, /forced insert failure/i);
});

test('post commit verification checks protected tables', () => {
    const gate = loadModuleFresh();
    const verification = gate.buildPostCommitVerification(
        {
            matches: 2,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        {
            matches: 10,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        }
    );

    assert.equal(verification.raw_match_data_unchanged, true);
    assert.equal(verification.features_unchanged, true);
    assert.equal(verification.predictions_unchanged, true);
});

test('output builder keeps required flags on fake success', () => {
    const gate = loadModuleFresh();
    const payload = gate.buildControlledExecutionResult({
        input: {
            source: 'fotmob',
            scope: 'league_season_date',
            leagueId: '53',
            season: '2025/2026',
            date: '2026-05-10',
            candidateCount: 8,
            maxSeedRows: 10,
            containsTargetMatchId: '4830746',
            containsTargetLabel: 'Angers vs Strasbourg',
        },
        exactCandidateSetSource: 'dependency_candidates',
        sourceUrlUsed: null,
        existingAffectedMatchesCount: 0,
        affectedPreview: [],
        insertedCount: 8,
        updatedCount: 0,
        skippedCount: 0,
        affectedMatchIds: validCandidates().map(item => item.match_id),
        transaction: {
            began: true,
            committed: true,
            rolled_back: false,
        },
        beforeCounts: {
            matches: 2,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        afterCounts: {
            matches: 10,
            bookmaker_odds_history: 2,
            raw_match_data: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
    });

    assert.equal(payload.execution_completed, true);
    assert.equal(payload.inserted_count, 8);
    assert.equal(payload.raw_match_data_write_executed, false);
    assert.equal(payload.safety_summary.called_fixture_repository_persist, false);
});

test('runCli handles stdin candidates, explicit stdinText, and invalid JSON errors', async t => {
    installNoSideEffectGuards(t);
    const gate = loadModuleFresh();

    const helpResult = await runCli(gate, ['--help']);
    assert.equal(helpResult.status, 0);
    assert.match(helpResult.stdout, /Usage:/);

    let stdout = '';
    const stdinStatus = await gate.runCli(
        validArgv(),
        {
            stdin: createFakeStdin(JSON.stringify(validCandidates())),
            stdout: text => {
                stdout += text;
            },
            stderr: () => {},
        },
        {
            pool: createFakePool().pool,
            existingMatches: [],
        }
    );
    assert.equal(stdinStatus, 0);
    assert.equal(parseJsonOutput(stdout).inserted_count, 8);

    const explicitStdin = await runCli(gate, validArgv(), {
        stdinText: JSON.stringify(validCandidates()),
        pool: createFakePool().pool,
        existingMatches: [],
    });
    assert.equal(explicitStdin.status, 0);
    assert.equal(parseJsonOutput(explicitStdin.stdout).inserted_count, 8);

    const invalidCandidatesJson = await runCli(gate, [...validArgv(), '--candidates-json={invalid'], {
        pool: createFakePool().pool,
        existingMatches: [],
    });
    assert.equal(invalidCandidatesJson.status, 1);
    assert.match(invalidCandidatesJson.stderr, /candidates-json is not valid JSON/i);

    const invalidExistingJson = await runCli(
        gate,
        [...validArgv(), '--candidates-json=' + JSON.stringify(validCandidates()), '--existing-matches-json={invalid'],
        { pool: createFakePool().pool }
    );
    assert.equal(invalidExistingJson.status, 1);
    assert.match(invalidExistingJson.stderr, /existing-matches-json is not valid JSON/i);

    const stdinErrorResult = await gate.runCli(
        validArgv(),
        {
            stdin: createFakeStdin('', { emitError: true }),
            stdout: () => {},
            stderr: () => {},
        },
        {
            candidates: validCandidates(),
            existingMatches: [],
            pool: createFakePool().pool,
        }
    );
    assert.equal(stdinErrorResult, 0);
});

test('Makefile execute target is registered and points to controlled script', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l1-matches-seed-commit-execute:/m);
    assert.match(makefile, /scripts\/ops\/l1_matches_seed_commit_execute\.js/);
    assert.match(makefile, /FINAL_DB_WRITE_CONFIRMATION=yes/);
});
