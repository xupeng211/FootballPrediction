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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/large_scale_target_inventory_schema_readiness_audit.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        rawVersion: 'fotmob_pageprops_v2',
        planningScope: 'target-inventory-schema-readiness',
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
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        'raw-version': 'fotmob_pageprops_v2',
        'planning-scope': 'target-inventory-schema-readiness',
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
        throw new Error(`${name} should not be called by large_scale_target_inventory_schema_readiness_audit`);
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
    assertInvalid({ planningScope: '' }, /missing planning-scope=target-inventory-schema-readiness/));
test('wrong planning-scope fails', () =>
    assertInvalid({ planningScope: 'other-scope' }, /planning-scope must be target-inventory-schema-readiness/));
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

test('plan says matches is canonical identity, not workflow queue', () => {
    const judgments = runPlan().json.current_schema_readiness_summary.judgments;
    assert.equal(judgments.matches_is_canonical_match_identity, true);
    assert.equal(judgments.matches_is_not_acquisition_workflow_queue, true);
});

test('plan says raw_match_data is versioned raw store', () => {
    const judgments = runPlan().json.current_schema_readiness_summary.judgments;
    assert.equal(judgments.raw_match_data_is_versioned_raw_store, true);
    assert.equal(judgments.future_acquisition_state_must_not_be_mixed_into_raw_match_data, true);
});

test('plan includes four target representation options', () => {
    const options = runPlan().json.target_inventory_representation_options.map(option => option.option);
    assert.equal(options.length, 4);
    assert.ok(options.includes('A_REUSE_MATCHES_ONLY'));
    assert.ok(options.includes('B_DOCS_ONLY_MANIFEST'));
    assert.ok(options.includes('C_SOURCE_CONTROLLED_JSON_YAML_MANIFEST'));
    assert.ok(options.includes('D_DEDICATED_ACQUISITION_TARGETS_TABLE_OR_STAGING_TABLE'));
});

test('plan recommends short-term docs/manifest', () => {
    const strategy = runPlan().json.recommended_representation_strategy;
    assert.match(strategy.short_term_strategy, /manifest|docs/i);
});

test('plan recommends medium-term acquisition_targets/staging table', () => {
    const strategy = runPlan().json.recommended_representation_strategy;
    assert.match(strategy.medium_term_strategy, /acquisition_targets|acquisition_batches/i);
});

test('plan includes proposed target fields', () => {
    const fields = runPlan().json.proposed_future_acquisition_target_fields;
    assert.ok(fields.includes('target_id'));
    assert.ok(fields.includes('batch_id'));
    assert.ok(fields.includes('baseline_hash'));
    assert.ok(fields.includes('odds_alignment_ready'));
});

test('plan includes target state machine', () => {
    const stateMachine = runPlan().json.target_state_machine;
    assert.ok(stateMachine.states.includes('planned'));
    assert.ok(stateMachine.states.includes('hash_baseline_ready'));
    assert.ok(stateMachine.states.includes('blocked'));
    assert.match(stateMachine.hard_gate, /preflight_passed .* hash_baseline_ready .* explicit authorization/i);
});

test('plan includes schema gap severities', () => {
    const gaps = runPlan().json.schema_gaps_readiness_findings;
    const severities = gaps.map(gap => gap.severity);
    assert.ok(severities.includes('high'));
    assert.ok(severities.includes('medium'));
    assert.ok(severities.includes('low'));
    assert.ok(severities.includes('acceptable_for_short_term_manifest'));
});

test('plan includes example manifest shape', () => {
    const manifest = runPlan().json.example_manifest_shape;
    assert.equal(manifest.batch_id, 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001');
    assert.equal(manifest.source, 'fotmob');
    assert.equal(manifest.route, 'html_hydration');
    assert.equal(manifest.targets[0].match_id, '53_20252026_4830746');
});

test('plan includes readiness gates before real acquisition', () => {
    const gates = runPlan().json.readiness_gates_before_real_acquisition;
    assert.ok(gates.includes('target inventory reviewed'));
    assert.ok(gates.includes('duplicate detection passed'));
    assert.ok(gates.includes('baseline hashes captured'));
});

test('plan includes odds alignment readiness', () => {
    const readiness = runPlan().json.odds_alignment_readiness;
    assert.equal(readiness.odds_ingestion_this_phase, false);
    assert.equal(readiness.kickoff_time_must_be_preserved, true);
    assert.equal(readiness.target_inventory_must_not_store_odds_values, true);
});

test('plan recommends L2S manifest planning', () => {
    const phases = runPlan().json.recommended_next_phases.map(entry => entry.phase);
    assert.ok(phases.includes('Phase 5.21L2S'));
});

test('plan recommends L2T no-write preflight', () => {
    const phases = runPlan().json.recommended_next_phases.map(entry => entry.phase);
    assert.ok(phases.includes('Phase 5.21L2T'));
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
