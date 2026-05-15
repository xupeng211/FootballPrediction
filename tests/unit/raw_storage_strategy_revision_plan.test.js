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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/raw_storage_strategy_revision_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        'current-version': 'fotmob_html_hyd_v1',
        'recommended-version': 'fotmob_pageprops_v2',
        'recommended-hash-strategy': 'stable_pageprops_payload_v1',
        'allow-network': 'no',
        'allow-db-write': 'no',
        'allow-migration': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    return Object.entries(validInput(overrides)).flatMap(([key, value]) => [`--${key}`, value]);
}

test('valid input succeeds', () => {
    const result = mod.validatePlanInput(validInput());
    assert.equal(result.ok, true);
});

test('source missing fails', () => {
    const result = mod.validatePlanInput(validInput({ source: '' }));
    assert.equal(result.ok, false);
});

test('source non-fotmob fails', () => {
    const result = mod.validatePlanInput(validInput({ source: 'other' }));
    assert.equal(result.ok, false);
});

test('current-version missing fails', () => {
    const result = mod.validatePlanInput(validInput({ 'current-version': '' }));
    assert.equal(result.ok, false);
});

test('current-version not fotmob_html_hyd_v1 fails', () => {
    const result = mod.validatePlanInput(validInput({ 'current-version': 'other_v1' }));
    assert.equal(result.ok, false);
});

test('recommended-version missing fails', () => {
    const result = mod.validatePlanInput(validInput({ 'recommended-version': '' }));
    assert.equal(result.ok, false);
});

test('recommended-version not fotmob_pageprops_v2 fails', () => {
    const result = mod.validatePlanInput(validInput({ 'recommended-version': 'fotmob_full_next_v2' }));
    assert.equal(result.ok, false);
});

test('recommended-hash-strategy missing fails', () => {
    const result = mod.validatePlanInput(validInput({ 'recommended-hash-strategy': '' }));
    assert.equal(result.ok, false);
});

test('recommended-hash-strategy not stable_pageprops_payload_v1 fails', () => {
    const result = mod.validatePlanInput(validInput({ 'recommended-hash-strategy': 'stable_raw_payload_v1' }));
    assert.equal(result.ok, false);
});

for (const [name, override] of [
    ['allow-network=yes blocked', { 'allow-network': 'yes' }],
    ['allow-db-write=yes blocked', { 'allow-db-write': 'yes' }],
    ['allow-migration=yes blocked', { 'allow-migration': 'yes' }],
    ['allow-parser-features=yes blocked', { 'allow-parser-features': 'yes' }],
    ['allow-training=yes blocked', { 'allow-training': 'yes' }],
    ['allow-prediction=yes blocked', { 'allow-prediction': 'yes' }],
    ['execute=yes blocked', { execute: 'yes' }],
    ['commit=yes blocked', { commit: 'yes' }],
    ['rewrite-existing=yes blocked', { 'rewrite-existing': 'yes' }],
    ['drop-v1=yes blocked', { 'drop-v1': 'yes' }],
]) {
    test(name, () => {
        const result = mod.validatePlanInput(validInput(override));
        assert.equal(result.ok, false);
    });
}

test('buildRawV2ShapePolicy recommends pageProps', () => {
    assert.equal(mod.buildRawV2ShapePolicy().raw_data, 'pageProps');
});

test('raw v2 policy does not default to full __NEXT_DATA__', () => {
    assert.ok(mod.buildRawV2ShapePolicy().not_default.includes('full __NEXT_DATA__'));
});

test('raw v2 policy does not store full HTML body', () => {
    assert.ok(mod.buildRawV2ShapePolicy().not_stored.includes('full HTML body'));
});

test('derived payload policy marks transformed payload non-canonical', () => {
    const policy = mod.buildDerivedPayloadPolicy();
    assert.equal(policy.transformed_payload, 'derived/helper');
    assert.equal(policy.not_canonical_raw, true);
});

test('existing v1 policy keeps rows and does not rewrite now', () => {
    const policy = mod.buildExistingV1Policy();
    assert.equal(policy.keep_existing_rows, true);
    assert.equal(policy.do_not_rewrite_now, true);
});

test('parser must branch by data_version', () => {
    assert.equal(mod.buildExistingV1Policy().parser_must_branch_by_data_version, true);
});

test('mixed provenance policy excludes synthetic/unknown from FotMob parser/training', () => {
    assert.equal(mod.buildMixedProvenancePolicy().synthetic_and_unknown_excluded_from_fotmob_parser_training, true);
});

test('league expansion policy requires completeness profile', () => {
    assert.equal(
        mod.buildLeagueExpansionCompletenessPolicy().requires_completeness_profile_before_parser_training,
        true
    );
});

test('profile modules include required coverage modules', () => {
    const modules = mod.buildLeagueExpansionCompletenessPolicy().profile_modules;
    for (const moduleName of [
        'content.lineup',
        'content.playerStats',
        'content.shotmap',
        'content.stats',
        'content.liveticker',
        'content.matchFacts',
        'content.momentum',
        'content.h2h',
        'content.table',
    ]) {
        assert.ok(modules.includes(moduleName), `${moduleName} should be profiled`);
    }
});

test('plan is planning_only=true', () => {
    const plan = mod.buildRawStorageStrategyRevisionPlan();
    assert.equal(plan.planning_only, true);
});

test('runCli emits successful planning payload', async () => {
    const outputs = [];
    const result = await mod.runCli(validArgv(), {
        output: payload => outputs.push(payload),
    });
    assert.equal(result.status, 0);
    assert.equal(outputs[0].recommended_canonical_raw_version, 'fotmob_pageprops_v2');
});

test('no fs write / mkdir', async () => {
    const originals = {
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        mkdir: fs.mkdir,
        createWriteStream: fs.createWriteStream,
    };
    let called = false;
    fs.writeFile = () => {
        called = true;
        throw new Error('fs.writeFile blocked');
    };
    fs.writeFileSync = () => {
        called = true;
        throw new Error('fs.writeFileSync blocked');
    };
    fs.mkdir = () => {
        called = true;
        throw new Error('fs.mkdir blocked');
    };
    fs.createWriteStream = () => {
        called = true;
        throw new Error('fs.createWriteStream blocked');
    };
    try {
        await loadFreshModule().runCli(validArgv(), { output: () => {} });
        assert.equal(called, false);
    } finally {
        fs.writeFile = originals.writeFile;
        fs.writeFileSync = originals.writeFileSync;
        fs.mkdir = originals.mkdir;
        fs.createWriteStream = originals.createWriteStream;
    }
});

test('no child_process spawn', () => {
    const originals = {
        spawn: childProcess.spawn,
        exec: childProcess.exec,
        execFile: childProcess.execFile,
    };
    let called = false;
    childProcess.spawn = () => {
        called = true;
        throw new Error('spawn blocked');
    };
    childProcess.exec = () => {
        called = true;
        throw new Error('exec blocked');
    };
    childProcess.execFile = () => {
        called = true;
        throw new Error('execFile blocked');
    };
    try {
        loadFreshModule();
        assert.equal(called, false);
    } finally {
        childProcess.spawn = originals.spawn;
        childProcess.exec = originals.exec;
        childProcess.execFile = originals.execFile;
    }
});

test('no network access', async () => {
    const originals = {
        fetch: global.fetch,
        httpRequest: http.request,
        httpsRequest: https.request,
    };
    let called = false;
    global.fetch = () => {
        called = true;
        throw new Error('fetch blocked');
    };
    http.request = () => {
        called = true;
        throw new Error('http.request blocked');
    };
    https.request = () => {
        called = true;
        throw new Error('https.request blocked');
    };
    try {
        await mod.runCli(validArgv(), { output: () => {} });
        assert.equal(called, false);
    } finally {
        global.fetch = originals.fetch;
        http.request = originals.httpRequest;
        https.request = originals.httpsRequest;
    }
});

test('no DB write', async () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (request === 'pg') throw new Error('pg import blocked');
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        const result = await loadFreshModule().runCli(validArgv(), { output: () => {} });
        assert.equal(result.payload.db_write_executed, false);
    } finally {
        Module._load = originalLoad;
    }
});

test('no ProductionHarvester/raw ingest import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/.test(request)) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});

test('no parser/features/training import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/NextDataParser|feature|train|predict/.test(request)) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});
