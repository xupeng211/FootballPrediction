'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/raw_match_data_versioned_schema_migration_preflight.js');
const preflight = require(MODULE_PATH);

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        'current-unique': 'match_id',
        'target-unique': 'match_id,data_version',
        'target-version': 'fotmob_pageprops_v2',
        'allow-db-write': 'no',
        'allow-migration': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
}

function schema(overrides = {}) {
    return {
        currentUniqueMatchIdConstraint: 'raw_match_data_match_id_key',
        constraints: [{ conname: 'raw_match_data_match_id_key', definition: 'UNIQUE (match_id)' }],
        indexes: [],
        dataVersionNullRows: 0,
        duplicateMatchIdRows: 0,
        duplicateMatchIdDataVersionRows: 0,
        ...overrides,
    };
}

function assertInvalid(overrides, pattern) {
    const result = preflight.validatePreflightInput(validArgs(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

function withPatched(object, property, replacement, callback) {
    const original = object[property];
    object[property] = replacement;
    return Promise.resolve()
        .then(callback)
        .finally(() => {
            object[property] = original;
        });
}

test('valid input succeeds', () => {
    const result = preflight.validatePreflightInput(validArgs());
    assert.equal(result.ok, true);
    assert.deepEqual(result.value.currentUnique, ['match_id']);
    assert.deepEqual(result.value.targetUnique, ['match_id', 'data_version']);
});

test('source missing fails', () => {
    assertInvalid({ source: '' }, /source=fotmob is required/);
});

test('source non-fotmob fails', () => {
    assertInvalid({ source: 'other' }, /source must be fotmob/);
});

test('table missing fails', () => {
    assertInvalid({ table: '' }, /table=raw_match_data is required/);
});

test('table not raw_match_data fails', () => {
    assertInvalid({ table: 'matches' }, /table must be raw_match_data/);
});

test('current-unique missing fails', () => {
    assertInvalid({ 'current-unique': '' }, /current-unique=match_id is required/);
});

test('current-unique not match_id fails', () => {
    assertInvalid({ 'current-unique': 'external_id' }, /current-unique must be match_id/);
});

test('target-unique missing fails', () => {
    assertInvalid({ 'target-unique': '' }, /target-unique=match_id,data_version is required/);
});

test('target-unique not match_id,data_version fails', () => {
    assertInvalid({ 'target-unique': 'match_id,external_id' }, /target-unique must be match_id,data_version/);
});

test('target-version missing fails', () => {
    assertInvalid({ 'target-version': '' }, /target-version=fotmob_pageprops_v2 is required/);
});

test('target-version not fotmob_pageprops_v2 fails', () => {
    assertInvalid({ 'target-version': 'fotmob_html_hyd_v1' }, /target-version must be fotmob_pageprops_v2/);
});

test('allow-db-write=yes blocked', () => {
    assertInvalid({ 'allow-db-write': 'yes' }, /allow-db-write=no is required/);
});

test('allow-migration=yes blocked', () => {
    assertInvalid({ 'allow-migration': 'yes' }, /allow-migration=no is required/);
});

test('allow-raw-match-data-write=yes blocked', () => {
    assertInvalid({ 'allow-raw-match-data-write': 'yes' }, /allow-raw-match-data-write=no is required/);
});

test('allow-parser-features=yes blocked', () => {
    assertInvalid({ 'allow-parser-features': 'yes' }, /allow-parser-features=no is required/);
});

test('allow-training=yes blocked', () => {
    assertInvalid({ 'allow-training': 'yes' }, /allow-training=no is required/);
});

test('allow-prediction=yes blocked', () => {
    assertInvalid({ 'allow-prediction': 'yes' }, /allow-prediction=no is required/);
});

test('execute=yes blocked', () => {
    assertInvalid({ execute: 'yes' }, /execute=yes is blocked/);
});

test('commit=yes blocked', () => {
    assertInvalid({ commit: 'yes' }, /commit=yes is blocked/);
});

test('alter-table=yes blocked', () => {
    assertInvalid({ 'alter-table': 'yes' }, /alter-table=yes is blocked/);
});

test('drop-constraint=yes blocked', () => {
    assertInvalid({ 'drop-constraint': 'yes' }, /drop-constraint=yes is blocked/);
});

test('add-constraint=yes blocked', () => {
    assertInvalid({ 'add-constraint': 'yes' }, /add-constraint=yes is blocked/);
});

test('create-index=yes blocked', () => {
    assertInvalid({ 'create-index': 'yes' }, /create-index=yes is blocked/);
});

test('drop-index=yes blocked', () => {
    assertInvalid({ 'drop-index': 'yes' }, /drop-index=yes is blocked/);
});

test('buildSchemaPreflight detects current unique(match_id)', () => {
    const findings = preflight.buildSchemaPreflight(schema());
    assert.equal(findings.current_unique_match_id_exists, true);
    assert.equal(findings.current_unique_match_id_constraint, 'raw_match_data_match_id_key');
});

test('buildSchemaPreflight detects target unique absent', () => {
    const findings = preflight.buildSchemaPreflight(schema());
    assert.equal(findings.target_unique_match_id_data_version_exists, false);
    assert.equal(findings.safe_to_plan_migration, true);
});

test('buildSchemaPreflight blocks if data_version null rows > 0', () => {
    const findings = preflight.buildSchemaPreflight(schema({ dataVersionNullRows: 1 }));
    assert.equal(findings.data_version_null_rows, 1);
    assert.equal(findings.safe_to_plan_migration, false);
});

test('buildSchemaPreflight blocks if duplicate match_id,data_version rows > 0', () => {
    const findings = preflight.buildSchemaPreflight(schema({ duplicateMatchIdDataVersionRows: 1 }));
    assert.equal(findings.duplicate_match_id_data_version_rows, 1);
    assert.equal(findings.safe_to_plan_migration, false);
});

test('buildSchemaPreflight records duplicate match_id rows', () => {
    const findings = preflight.buildSchemaPreflight(schema({ duplicateMatchIdRows: 2 }));
    assert.equal(findings.duplicate_match_id_rows, 2);
});

test('forward migration plan drops raw_match_data_match_id_key', () => {
    assert.match(preflight.buildForwardMigrationPlan()[0], /DROP CONSTRAINT raw_match_data_match_id_key/);
});

test('forward migration plan adds raw_match_data_match_id_data_version_key', () => {
    assert.match(
        preflight.buildForwardMigrationPlan()[1],
        /ADD CONSTRAINT raw_match_data_match_id_data_version_key UNIQUE \(match_id, data_version\)/
    );
});

test('rollback plan requires duplicate match_id precondition', () => {
    assert.match(preflight.buildRollbackPlan()[0], /HAVING COUNT\(\*\) > 1 returns 0 rows/);
});

test('rollback plan restores raw_match_data_match_id_key', () => {
    const rollback = preflight.buildRollbackPlan();
    assert.match(rollback[1], /DROP CONSTRAINT raw_match_data_match_id_data_version_key/);
    assert.match(rollback[2], /ADD CONSTRAINT raw_match_data_match_id_key UNIQUE \(match_id\)/);
});

test('code impact summary requires writer conflict target change', () => {
    const summary = preflight.buildCodeImpactSummary();
    assert.equal(summary.writers_must_change_conflict_target, true);
    assert.ok(summary.controlled_writers_to_update.includes('future pageProps v2 writer'));
});

test('code impact summary requires reader data_version filtering', () => {
    const summary = preflight.buildCodeImpactSummary();
    assert.equal(summary.readers_must_filter_data_version, true);
    assert.equal(summary.canonical_selector_recommended, true);
});

test('plan is planning_only=true', () => {
    const payload = preflight.buildRawMatchDataVersionedSchemaMigrationPreflight();
    assert.equal(payload.planning_only, true);
    assert.equal(payload.phase, 'PHASE5_21L2F_RAW_MATCH_DATA_VERSIONED_SCHEMA_MIGRATION_PREFLIGHT');
});

test('execution flags all false', () => {
    const payload = preflight.buildRawMatchDataVersionedSchemaMigrationPreflight();
    assert.equal(payload.execution_this_phase.db_write_executed, false);
    assert.equal(payload.execution_this_phase.migration_executed, false);
    assert.equal(payload.execution_this_phase.alter_table_executed, false);
    assert.equal(payload.execution_this_phase.create_index_executed, false);
    assert.equal(payload.execution_this_phase.drop_index_executed, false);
});

test('no fs write / mkdir', async () => {
    await withPatched(
        fs,
        'writeFileSync',
        () => {
            throw new Error('writeFileSync should not be called');
        },
        async () => {
            await withPatched(
                fs,
                'writeFile',
                () => {
                    throw new Error('writeFile should not be called');
                },
                async () => {
                    await withPatched(
                        fs,
                        'mkdir',
                        () => {
                            throw new Error('mkdir should not be called');
                        },
                        async () => {
                            await withPatched(
                                fs,
                                'createWriteStream',
                                () => {
                                    throw new Error('createWriteStream should not be called');
                                },
                                async () => {
                                    const result = await preflight.runCli(validArgs(), { output() {} });
                                    assert.equal(result.status, 0);
                                }
                            );
                        }
                    );
                }
            );
        }
    );
});

test('no child_process spawn', async () => {
    await withPatched(
        childProcess,
        'spawn',
        () => {
            throw new Error('spawn should not be called');
        },
        async () => {
            await withPatched(
                childProcess,
                'exec',
                () => {
                    throw new Error('exec should not be called');
                },
                async () => {
                    await withPatched(
                        childProcess,
                        'execFile',
                        () => {
                            throw new Error('execFile should not be called');
                        },
                        async () => {
                            const result = await preflight.runCli(validArgs(), { output() {} });
                            assert.equal(result.status, 0);
                        }
                    );
                }
            );
        }
    );
});

test('no network access', async () => {
    await withPatched(
        globalThis,
        'fetch',
        () => {
            throw new Error('fetch should not be called');
        },
        async () => {
            await withPatched(
                http,
                'request',
                () => {
                    throw new Error('http.request should not be called');
                },
                async () => {
                    await withPatched(
                        https,
                        'request',
                        () => {
                            throw new Error('https.request should not be called');
                        },
                        async () => {
                            const result = await preflight.runCli(validArgs(), { output() {} });
                            assert.equal(result.status, 0);
                            assert.equal(result.payload.network_access_executed, false);
                        }
                    );
                }
            );
        }
    );
});

test('no DB write', () => {
    const payload = preflight.buildRawMatchDataVersionedSchemaMigrationPreflight();
    assert.equal(payload.db_write_executed, false);
    assert.equal(payload.raw_match_data_write_executed, false);
});

test('no migration execution', () => {
    const payload = preflight.buildRawMatchDataVersionedSchemaMigrationPreflight();
    assert.equal(payload.migration_executed, false);
    assert.equal(payload.execution_this_phase.migration_executed, false);
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /query\s*\(/);
    assert.doesNotMatch(source, /CREATE INDEX/);
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no parser/features/training import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /require\([^)]*(parser|feature|train|predict)/i);
});
