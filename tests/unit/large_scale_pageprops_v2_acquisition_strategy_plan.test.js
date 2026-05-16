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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        rawVersion: 'fotmob_pageprops_v2',
        planningScope: 'large-scale-acquisition-strategy',
        allowDbWrite: false,
        allowNetwork: false,
        allowRawAcquisition: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        allowOddsWrite: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        'raw-version': 'fotmob_pageprops_v2',
        'planning-scope': 'large-scale-acquisition-strategy',
        'allow-db-write': 'no',
        'allow-network': 'no',
        'allow-raw-acquisition': 'no',
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
        throw new Error(`${name} should not be called by large_scale_pageprops_v2_acquisition_strategy_plan`);
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
test('raw-version missing fails', () => assertInvalid({ rawVersion: '' }, /missing raw-version=fotmob_pageprops_v2/));
test('raw-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid({ rawVersion: 'fotmob_html_hyd_v1' }, /raw-version must be fotmob_pageprops_v2/));
test('planning-scope missing fails', () =>
    assertInvalid({ planningScope: '' }, /missing planning-scope=large-scale-acquisition-strategy/));
test('wrong planning-scope fails', () =>
    assertInvalid({ planningScope: 'other-scope' }, /planning-scope must be large-scale-acquisition-strategy/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-network=yes blocked', () => assertInvalid({ allowNetwork: true }, /allow-network=yes is blocked/));
test('allow-raw-acquisition=yes blocked', () =>
    assertInvalid({ allowRawAcquisition: true }, /allow-raw-acquisition=yes is blocked/));
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
test('allow-schema-migration=yes blocked', () =>
    assertInvalid({ allowSchemaMigration: true }, /allow-schema-migration=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));
test('allow-odds-write=yes blocked', () => assertInvalid({ allowOddsWrite: true }, /allow-odds-write=yes is blocked/));

test('plan says current 8 matches are samples, not training data', () => {
    const summary = runPlan().json.current_state_summary;
    assert.equal(summary.current_8_seeded_matches_are_validation_samples_not_training_data, true);
    assert.match(summary.limitation_statement, /not .*training/i);
});

test('plan includes tier 0 current seeded validation', () => {
    const tiers = runPlan().json.target_expansion_tiers.map(entry => entry.tier);
    assert.ok(tiers.includes('TIER_0_CURRENT_SEEDED_VALIDATION'));
});

test('plan includes tier 1 single-league single-season', () => {
    const tiers = runPlan().json.target_expansion_tiers.map(entry => entry.tier);
    assert.ok(tiers.includes('TIER_1_SINGLE_LEAGUE_SINGLE_SEASON'));
});

test('plan includes tier 2 top European multi-season', () => {
    const tiers = runPlan().json.target_expansion_tiers.map(entry => entry.tier);
    assert.ok(tiers.includes('TIER_2_TOP_EUROPEAN_MULTI_SEASON'));
});

test('plan includes tier 3 broader UEFA / second-tier', () => {
    const tiers = runPlan().json.target_expansion_tiers.map(entry => entry.tier);
    assert.ok(tiers.includes('TIER_3_BROADER_UEFA_SECOND_TIER'));
});

test('plan includes tier 4 low-tier / obscure league risk', () => {
    const tiers = runPlan().json.target_expansion_tiers.map(entry => entry.tier);
    assert.ok(tiers.includes('TIER_4_LOW_TIER_OBSCURE_LEAGUES'));
});

test('plan includes batch lifecycle', () => {
    const lifecycle = runPlan().json.batch_acquisition_lifecycle;
    assert.equal(lifecycle.length, 9);
    assert.equal(lifecycle[0].key, 'target_inventory_planning');
    assert.equal(lifecycle[8].key, 'parser_eligibility_decision');
});

test('plan includes target inventory design', () => {
    const design = runPlan().json.target_inventory_design;
    const fieldNames = design.inventory_fields.map(field => field.name);
    assert.ok(fieldNames.includes('match_id'));
    assert.ok(fieldNames.includes('external_id'));
    assert.ok(fieldNames.includes('league_id'));
    assert.ok(fieldNames.includes('kickoff_time'));
    assert.ok(fieldNames.includes('existing_versions'));
    assert.ok(fieldNames.includes('expected_coverage_tier'));
    assert.ok(fieldNames.includes('acquisition_state'));
});

test('plan includes batch sizing policy', () => {
    const policy = runPlan().json.batch_sizing_and_safety_policy;
    assert.equal(policy.first_batch_should_be_small, true);
    assert.equal(policy.suggested_batch_sizes.profile_batch, '20-50 matches');
    assert.equal(policy.suggested_batch_sizes.controlled_write_batch, '20-100 matches');
});

test('plan includes coverage profile strategy', () => {
    const strategy = runPlan().json.coverage_profile_strategy;
    const modulePaths = strategy.module_output_schema.map(moduleEntry => moduleEntry.module_path);
    assert.ok(modulePaths.includes('content'));
    assert.ok(modulePaths.includes('content.shotmap'));
    assert.ok(modulePaths.includes('header'));
    assert.ok(modulePaths.includes('fetchingLeagueData'));
});

test('plan includes low-tier missing module risk', () => {
    const policy = runPlan().json.low_tier_obscure_league_risk_policy;
    assert.equal(policy.low_tier_leagues_may_not_have_full_module_coverage, true);
    assert.equal(policy.do_not_assume_lineup_playerStats_shotmap_momentum_stats_exist, true);
    assert.equal(policy.missing_advanced_modules_should_not_fail_ingestion, true);
});

test('plan includes data version/source fidelity policy', () => {
    const policy = runPlan().json.data_version_source_fidelity_policy;
    assert.equal(policy.canonical_raw_version, 'fotmob_pageprops_v2');
    assert.equal(policy.legacy_fallback_version, 'fotmob_html_hyd_v1');
    assert.equal(policy.data_hash_strategy, 'stable_pageprops_payload_v1');
});

test('plan includes odds alignment readiness', () => {
    const readiness = runPlan().json.match_identity_and_odds_alignment_readiness;
    assert.equal(readiness.odds_ingestion_this_phase, false);
    assert.equal(readiness.stable_match_id_is_critical, true);
    assert.match(readiness.future_odds_join_strategy, /match_id/i);
});

test('plan recommends L2R target inventory planning', () => {
    const phases = runPlan().json.recommended_next_phases.map(entry => entry.phase);
    assert.ok(phases.includes('Phase 5.21L2R'));
});

test('plan recommends L2S small-batch preflight', () => {
    const phases = runPlan().json.recommended_next_phases.map(entry => entry.phase);
    assert.ok(phases.includes('Phase 5.21L2S'));
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

test('no parser implementation', () => {
    assert.equal(runPlan().json.parser_implementation_executed, false);
});

test('no feature extraction', () => {
    assert.equal(runPlan().json.feature_extraction_executed, false);
});

test('no training/prediction', () => {
    const plan = runPlan().json;
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
