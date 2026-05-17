'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_league_small_batch_target_manifest_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        batchId: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        batchSizePolicy: '20-50',
        planningScope: 'single-league-small-batch-target-manifest',
        allowDbWrite: false,
        allowNetwork: false,
        allowRawAcquisition: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowOddsWrite: false,
        migrate: false,
        inventTargets: false,
        fabricateExternalIds: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        route: 'html_hydration',
        'raw-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'league-id': '53',
        'league-name': 'Ligue 1',
        season: '2025/2026',
        'batch-id': 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        'batch-size-policy': '20-50',
        'planning-scope': 'single-league-small-batch-target-manifest',
        'allow-db-write': 'no',
        'allow-network': 'no',
        'allow-raw-acquisition': 'no',
        'allow-schema-migration': 'no',
        'allow-parser-implementation': 'no',
        'allow-feature-extraction': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validatePlanningInput(validInput(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

function runPlan(argv = validArgv()) {
    const stdout = [];
    const stderr = [];
    const exitCode = mod.execute(argv, {
        stdout: { write: chunk => stdout.push(String(chunk)) },
        stderr: { write: chunk => stderr.push(String(chunk)) },
    });
    const stdoutText = stdout.join('');
    const stderrText = stderr.join('');
    return {
        exitCode,
        stdout: stdoutText,
        stderr: stderrText,
        json: stdoutText ? JSON.parse(stdoutText) : null,
        errorJson: stderrText ? JSON.parse(stderrText) : null,
    };
}

function fakeInventory() {
    return [
        {
            match_id: '53_20252026_4830746',
            external_id: '4830746',
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Angers',
            away_team: 'Strasbourg',
            match_date: '2026-05-10T19:00:00Z',
            status: 'finished',
            existing_versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        },
        {
            match_id: '53_20252026_9999001',
            external_id: '9999001',
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Local Home',
            away_team: 'Local Away',
            match_date: '2026-05-17T19:00:00Z',
            status: 'finished',
            existing_versions: ['fotmob_html_hyd_v1'],
        },
    ];
}

function installExecutionGuards(t) {
    const originalFetch = global.fetch;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by single_league_small_batch_target_manifest_plan`);
    };

    global.fetch = fail('global.fetch');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    http.request = fail('http.request');
    https.request = fail('https.request');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'playwright',
            'playwright-core',
            'puppeteer',
            'child_process',
            'node:child_process',
            'http',
            'node:http',
            'https',
            'node:https',
        ]);
        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (
            /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data|odds_harvest_pipeline|train|predict/i.test(
                request
            )
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        global.fetch = originalFetch;
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        fs.createWriteStream = originalCreateWriteStream;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        Module._load = originalLoad;
    });
}

function loadWithBlockedImportPattern(t, pattern) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (pattern.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
    return loadFreshModule();
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePlanningInput(validInput()).ok, true);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source=fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route=html_hydration/));
test('route not html_hydration fails', () =>
    assertInvalid({ route: 'api_match_details' }, /route must be html_hydration/));
test('raw-version missing fails', () => assertInvalid({ rawVersion: '' }, /missing raw-version=fotmob_pageprops_v2/));
test('raw-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid({ rawVersion: 'fotmob_html_hyd_v1' }, /raw-version must be fotmob_pageprops_v2/));
test('hash-strategy missing fails', () =>
    assertInvalid({ hashStrategy: '' }, /missing hash-strategy=stable_pageprops_payload_v1/));
test('hash-strategy not stable_pageprops_payload_v1 fails', () =>
    assertInvalid({ hashStrategy: 'other_hash' }, /hash-strategy must be stable_pageprops_payload_v1/));
test('league-id missing fails', () => assertInvalid({ leagueId: '' }, /missing league-id=53/));
test('league-id not 53 fails for this phase', () =>
    assertInvalid({ leagueId: 54 }, /league-id must be 53 for this phase/));
test('league-name missing fails', () => assertInvalid({ leagueName: '' }, /missing league-name=Ligue 1/));
test('league-name not Ligue 1 fails for this phase', () =>
    assertInvalid({ leagueName: 'Premier League' }, /league-name must be Ligue 1 for this phase/));
test('season missing fails', () => assertInvalid({ season: '' }, /missing season=2025\/2026/));
test('season not 2025/2026 fails for this phase', () =>
    assertInvalid({ season: '2024/2025' }, /season must be 2025\/2026 for this phase/));
test('batch-id missing fails', () =>
    assertInvalid({ batchId: '' }, /missing batch-id=fotmob-pageprops-v2-ligue1-2025-2026-profile-001/));
test('batch-id wrong fails', () => assertInvalid({ batchId: 'wrong' }, /batch-id must be/));
test('batch-size-policy missing fails', () =>
    assertInvalid({ batchSizePolicy: '' }, /missing batch-size-policy=20-50/));
test('batch-size-policy not 20-50 fails', () =>
    assertInvalid({ batchSizePolicy: '100' }, /batch-size-policy must be 20-50/));
test('planning-scope missing fails', () =>
    assertInvalid({ planningScope: '' }, /missing planning-scope=single-league-small-batch-target-manifest/));
test('wrong planning-scope fails', () =>
    assertInvalid({ planningScope: 'other' }, /planning-scope must be single-league-small-batch-target-manifest/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-network=yes blocked', () => assertInvalid({ allowNetwork: true }, /allow-network=yes is blocked/));
test('allow-raw-acquisition=yes blocked', () =>
    assertInvalid({ allowRawAcquisition: true }, /allow-raw-acquisition=yes is blocked/));
test('allow-schema-migration=yes blocked', () =>
    assertInvalid({ allowSchemaMigration: true }, /allow-schema-migration=yes is blocked/));
test('allow-parser-implementation=yes blocked', () =>
    assertInvalid({ allowParserImplementation: true }, /allow-parser-implementation=yes is blocked/));
test('allow-feature-extraction=yes blocked', () =>
    assertInvalid({ allowFeatureExtraction: true }, /allow-feature-extraction=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: true }, /execute=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('touch-fotmob=yes blocked', () => assertInvalid({ touchFotmob: true }, /touch-fotmob=yes is blocked/));
test('live-request=yes blocked', () => assertInvalid({ liveRequest: true }, /live-request=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-odds-write=yes blocked', () => assertInvalid({ allowOddsWrite: true }, /allow-odds-write=yes is blocked/));
test('migrate=yes blocked', () => assertInvalid({ migrate: true }, /migrate=yes is blocked/));
test('invent-targets=yes blocked', () => assertInvalid({ inventTargets: true }, /invent-targets=yes is blocked/));
test('fabricate-external-ids=yes blocked', () =>
    assertInvalid({ fabricateExternalIds: true }, /fabricate-external-ids=yes is blocked/));

test('fake DB known v2 targets are marked already_completed', () => {
    const completed = mod.buildKnownCompletedTargets(fakeInventory());
    assert.equal(completed.length, 1);
    assert.equal(completed[0].target_status, 'already_completed');
    assert.equal(completed[0].reason, 'already_has_fotmob_pageprops_v2');
});

test('fake DB known completed are excluded from candidate_targets', () => {
    const manifest = mod.buildManifestProposal(fakeInventory());
    assert.equal(manifest.known_completed_targets[0].exclude_from_new_profile_batch, true);
    assert.ok(!manifest.candidate_targets.some(target => target.match_id === '53_20252026_4830746'));
});

test('fake DB local matches without v2 become candidate_targets', () => {
    const manifest = mod.buildManifestProposal(fakeInventory());
    assert.equal(manifest.candidate_targets.length, 1);
    assert.equal(manifest.candidate_targets[0].match_id, '53_20252026_9999001');
    assert.equal(manifest.candidate_targets[0].target_status, 'planned');
});

test('if candidate target count < 20, target_population_status blocked_pending_authorized_target_discovery', () => {
    const manifest = mod.buildManifestProposal(fakeInventory());
    assert.equal(manifest.target_population_status, 'blocked_pending_authorized_target_discovery');
});

test('no fabricated targets when local candidates insufficient', () => {
    const manifest = mod.buildManifestProposal(fakeInventory());
    assert.equal(manifest.no_invented_targets, true);
    assert.equal(manifest.no_fabricated_external_ids, true);
    assert.equal(manifest.candidate_targets.length, 1);
});

test('manifest includes required fields', () => {
    const fields = runPlan().json.target_manifest_schema.map(entry => entry.field);
    assert.ok(fields.includes('target_id'));
    assert.ok(fields.includes('baseline_hash'));
    assert.ok(fields.includes('odds_alignment_ready'));
});

test('manifest includes readiness gates', () => {
    const gates = runPlan().json.readiness_gates;
    assert.ok(gates.includes('manifest reviewed'));
    assert.ok(gates.includes('no invented external_id'));
    assert.ok(gates.includes('explicit network authorization before target discovery/preflight'));
});

test('manifest includes odds_alignment_ready field', () => {
    const manifest = runPlan().json.manifest_proposal;
    assert.equal(manifest.known_completed_targets[0].odds_alignment_ready, true);
    assert.ok(manifest.target_manifest_schema.some(entry => entry.field === 'odds_alignment_ready'));
});

test('no DB write', () => {
    assert.equal(runPlan().json.db_write_executed, false);
});

test('no network', () => {
    assert.equal(runPlan().json.network_executed, false);
});

test('no raw acquisition', () => {
    assert.equal(runPlan().json.raw_acquisition_executed, false);
});

test('no schema migration', () => {
    assert.equal(runPlan().json.schema_migration_executed, false);
});

test('no parser/features/training', () => {
    const plan = runPlan().json;
    assert.equal(plan.parser_implementation_executed, false);
    assert.equal(plan.feature_extraction_executed, false);
    assert.equal(plan.training_executed, false);
    assert.equal(plan.prediction_executed, false);
});

test('no child_process spawn', t => {
    installExecutionGuards(t);
    const result = runPlan();
    assert.equal(result.exitCode, 0);
});

test('no ProductionHarvester/raw ingest import', t => {
    const freshModule = loadWithBlockedImportPattern(
        t,
        /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i
    );
    assert.equal(typeof freshModule.execute, 'function');
});

test('no odds_harvest_pipeline import', t => {
    const freshModule = loadWithBlockedImportPattern(t, /odds_harvest_pipeline/i);
    assert.equal(typeof freshModule.execute, 'function');
});
