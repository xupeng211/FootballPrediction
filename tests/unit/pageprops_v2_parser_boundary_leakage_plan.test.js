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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_parser_boundary_leakage_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        rawVersion: 'fotmob_pageprops_v2',
        planningScope: 'parser-boundary-leakage-acquisition-odds-roadmap',
        allowDbWrite: false,
        allowNetwork: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowOddsWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        'raw-version': 'fotmob_pageprops_v2',
        'planning-scope': 'parser-boundary-leakage-acquisition-odds-roadmap',
        'allow-db-write': 'no',
        'allow-network': 'no',
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
        throw new Error(`${name} should not be called by pageprops_v2_parser_boundary_leakage_plan`);
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

function getModule(plan, parserKey) {
    return plan.parser_module_plan.find(modulePlan => modulePlan.parser_key === parserKey);
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
    assertInvalid({ planningScope: '' }, /missing planning-scope=parser-boundary-leakage-acquisition-odds-roadmap/));
test('wrong planning-scope fails', () =>
    assertInvalid(
        { planningScope: 'other-scope' },
        /planning-scope must be parser-boundary-leakage-acquisition-odds-roadmap/
    ));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-network=yes blocked', () => assertInvalid({ allowNetwork: true }, /allow-network=yes is blocked/));
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
test('allow-odds-write=yes blocked', () => assertInvalid({ allowOddsWrite: true }, /allow-odds-write=yes is blocked/));
test('allow-schema-migration=yes blocked', () =>
    assertInvalid({ allowSchemaMigration: true }, /allow-schema-migration=yes is blocked/));
test('allow-matches-write=yes blocked', () =>
    assertInvalid({ allowMatchesWrite: true }, /allow-matches-write=yes is blocked/));

test('plan contains identity_metadata_parser', () => {
    assert.ok(getModule(runPlan().json, 'identity_metadata_parser'));
});

test('plan contains team_context_parser', () => {
    assert.ok(getModule(runPlan().json, 'team_context_parser'));
});

test('plan contains h2h_parser', () => {
    assert.ok(getModule(runPlan().json, 'h2h_parser'));
});

test('plan contains lineup_parser with conditional timestamp policy', () => {
    const lineupParser = getModule(runPlan().json, 'lineup_parser');
    assert.ok(lineupParser);
    assert.equal(lineupParser.leakage_tier, 'conditional_pre_match_if_timestamped');
    assert.match(lineupParser.timestamp_rule, /lineup_timestamp <= prediction_cutoff_time/);
});

test('plan marks shotmap as live/post_match only', () => {
    const shotmapParser = getModule(runPlan().json, 'shotmap_parser');
    assert.equal(shotmapParser.leakage_tier, 'post_match_only');
    assert.ok(shotmapParser.field_categories.live_only.length > 0);
});

test('plan marks playerStats as live/post_match only', () => {
    const playerStatsParser = getModule(runPlan().json, 'player_stats_parser');
    assert.equal(playerStatsParser.leakage_tier, 'post_match_only');
    assert.ok(playerStatsParser.field_categories.live_only.length > 0);
});

test('plan marks momentum as live/post_match only', () => {
    const momentumParser = getModule(runPlan().json, 'momentum_parser');
    assert.equal(momentumParser.leakage_tier, 'live_only');
    assert.ok(momentumParser.field_categories.post_match_only.length > 0);
});

test('plan includes prediction horizons T-24h/T-6h/T-1h/closing', () => {
    const horizons = runPlan()
        .json.leakage_safe_feature_policy.prediction_horizons.map(entry => entry.horizon)
        .sort();
    assert.deepEqual(horizons, [...mod.PREDICTION_HORIZONS].sort());
});

test('plan includes odds raw roadmap', () => {
    assert.ok(runPlan().json.odds_raw_roadmap);
});

test('plan says odds raw early, odds features later', () => {
    const oddsRoadmap = runPlan().json.odds_raw_roadmap;
    assert.equal(oddsRoadmap.odds_raw_should_be_ingested_early, true);
    assert.equal(oddsRoadmap.odds_features_must_wait_for_cutoff_policy, true);
});

test('plan includes odds_timestamp <= prediction_cutoff_time rule', () => {
    const policy = runPlan().json.leakage_safe_feature_policy;
    assert.equal(policy.odds_timestamp_rule, 'odds_timestamp <= prediction_cutoff_time');
});

test('plan says current 8 matches are samples, not training set', () => {
    const notice = runPlan().json.current_sample_notice;
    assert.equal(notice.training_dataset, false);
    assert.match(notice.statement, /not training data/);
});

test('plan includes large-scale acquisition roadmap', () => {
    assert.ok(runPlan().json.large_scale_pageprops_v2_acquisition_roadmap);
});

test('plan includes low-tier league missing module risk', () => {
    const risks = runPlan().json.large_scale_pageprops_v2_acquisition_roadmap.low_tier_league_risks;
    assert.ok(risks.includes('missing lineup'));
    assert.ok(risks.includes('missing playerStats'));
});

test('no DB write', () => {
    assert.equal(runPlan().json.db_write_executed, false);
});

test('no network', () => {
    assert.equal(runPlan().json.network_executed, false);
});

test('no parser implementation', () => {
    assert.equal(runPlan().json.parser_implementation_executed, false);
});

test('no feature extraction', () => {
    assert.equal(runPlan().json.feature_extraction_executed, false);
});

test('no fs write / mkdir except repo edits', t => {
    installExecutionGuards(t);
    const result = runPlan();
    assert.equal(result.exitCode, 0);
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

test('no training/prediction import', t => {
    const freshModule = loadWithBlockedImportPattern(t, /train|predict/i);
    assert.equal(typeof freshModule.execute, 'function');
});
