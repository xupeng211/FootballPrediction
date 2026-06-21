'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/raw_match_data_versioned_schema_migration_execute.js');
const execute = require(MODULE_PATH);

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        table: 'raw_match_data',
        'current-unique': 'match_id',
        'target-unique': 'match_id,data_version',
        'current-constraint': 'raw_match_data_match_id_key',
        'target-constraint': 'raw_match_data_match_id_data_version_key',
        'final-schema-migration-confirmation': 'yes',
        'allow-db-write': 'yes',
        'allow-schema-migration': 'yes',
        'allow-alter-table': 'yes',
        'allow-raw-match-data-write': 'no',
        'allow-matches-write': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
}

function assertInvalid(overrides, pattern) {
    const result = execute.validateExecutionInput(validArgs(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

function defaultRowCounts(overrides = {}) {
    return {
        matches: 10,
        bookmaker_odds_history: 2,
        raw_match_data: 10,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...overrides,
    };
}

function rowsFromCounts(counts) {
    return Object.entries(counts).map(([table_name, rows]) => ({ table_name, rows }));
}

function handleTransactionSql(text) {
    if (text === 'BEGIN' || text === 'COMMIT' || text === 'ROLLBACK') {
        return { handled: true, result: { rows: [] } };
    }
    return { handled: false };
}

function handleAlterSql(text, state) {
    if (text.includes('ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_key')) {
        if (state.failOnAlter) throw new Error('ALTER failed');
        state.currentConstraintExists = false;
        return { handled: true, result: { rows: [] } };
    }
    if (
        text.includes(
            'ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_data_version_key UNIQUE (match_id, data_version)'
        )
    ) {
        if (state.failOnAlter) throw new Error('ALTER failed');
        state.targetConstraintExists = state.keepTargetAbsentAfterAlter ? false : true;
        return { handled: true, result: { rows: [] } };
    }
    return { handled: false };
}

function handleSelectSql(text, state) {
    if (text.includes('current_constraint_rows') && text.includes('FROM pg_constraint')) {
        return {
            handled: true,
            result: {
                rows: [
                    {
                        current_constraint_rows: state.currentConstraintExists ? 1 : 0,
                        target_constraint_rows: state.targetConstraintExists ? 1 : 0,
                    },
                ],
            },
        };
    }
    if (text.includes('data_version_null_rows')) {
        return { handled: true, result: { rows: [{ data_version_null_rows: state.dataVersionNullRows }] } };
    }
    if (text.includes('duplicate_match_id_data_version_rows')) {
        return {
            handled: true,
            result: {
                rows: [{ duplicate_match_id_data_version_rows: state.duplicateMatchIdDataVersionRows }],
            },
        };
    }
    if (text.includes("SELECT 'matches' AS table_name")) {
        state.rowCountCallCount += 1;
        return {
            handled: true,
            result: {
                rows: rowsFromCounts(state.rowCountCallCount === 1 ? state.rowCountsBefore : state.rowCountsAfter),
            },
        };
    }
    return { handled: false };
}

function createFakeClient(options = {}) {
    const state = {
        currentConstraintExists: options.currentConstraintExists ?? true,
        targetConstraintExists: options.targetConstraintExists ?? false,
        dataVersionNullRows: options.dataVersionNullRows ?? 0,
        duplicateMatchIdDataVersionRows: options.duplicateMatchIdDataVersionRows ?? 0,
        rowCountsBefore: options.rowCountsBefore || defaultRowCounts(),
        rowCountsAfter: options.rowCountsAfter || options.rowCountsBefore || defaultRowCounts(),
        failOnAlter: options.failOnAlter || false,
        keepTargetAbsentAfterAlter: options.keepTargetAbsentAfterAlter || false,
        calls: [],
        rowCountCallCount: 0,
        released: false,
    };

    return {
        state,
        async query(sql) {
            const text = String(sql).trim();
            state.calls.push(text);
            const transaction = handleTransactionSql(text);
            if (transaction.handled) return transaction.result;
            const alter = handleAlterSql(text, state);
            if (alter.handled) return alter.result;
            const select = handleSelectSql(text, state);
            if (select.handled) return select.result;
            throw new Error(`unexpected SQL: ${text}`);
        },
        release() {
            state.released = true;
        },
    };
}

function withPatched(object, property, replacement, callback) {
    const hadProperty = Object.prototype.hasOwnProperty.call(object, property);
    const original = object[property];
    object[property] = replacement;
    return Promise.resolve()
        .then(callback)
        .finally(() => {
            if (hadProperty) {
                object[property] = original;
            } else {
                delete object[property];
            }
        });
}

// ── DB Write Guard env helpers ──────────────────────────────────────────────

const DB_WRITE_GUARD_ENV_KEYS = [
    'ALLOW_DB_WRITE',
    'FINAL_DB_WRITE_CONFIRMATION',
    'ALLOW_RAW_MATCH_DATA_WRITE',
    'ALLOW_SCHEMA_WRITE',
    'DRY_RUN',
];

function snapshotEnv(keys = DB_WRITE_GUARD_ENV_KEYS) {
    return Object.fromEntries(keys.map(key => [key, process.env[key]]));
}

function restoreEnv(snapshot) {
    for (const [key, value] of Object.entries(snapshot)) {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }
}

function applySchemaMigrationGuardEnv(overrides = {}) {
    const saved = snapshotEnv(DB_WRITE_GUARD_ENV_KEYS);
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.ALLOW_RAW_MATCH_DATA_WRITE = 'yes';
    process.env.ALLOW_SCHEMA_WRITE = 'yes';
    process.env.DRY_RUN = 'false';
    for (const [key, value] of Object.entries(overrides)) {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }
    return saved;
}

async function withSchemaMigrationGuardEnv(callback, overrides = {}) {
    const saved = applySchemaMigrationGuardEnv(overrides);
    try {
        return await callback();
    } finally {
        restoreEnv(saved);
    }
}

function runCliWithGuardEnv(argv, dependencies, envOverrides) {
    return withSchemaMigrationGuardEnv(() => execute.runCli(argv, dependencies), envOverrides);
}

test('valid input succeeds', () => {
    const result = execute.validateExecutionInput(validArgs());
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

test('current-constraint wrong fails', () => {
    assertInvalid({ 'current-constraint': 'wrong_key' }, /current-constraint must be raw_match_data_match_id_key/);
});

test('target-constraint wrong fails', () => {
    assertInvalid(
        { 'target-constraint': 'wrong_key' },
        /target-constraint must be raw_match_data_match_id_data_version_key/
    );
});

test('final-schema-migration-confirmation missing blocked', () => {
    assertInvalid({ 'final-schema-migration-confirmation': '' }, /final-schema-migration-confirmation=yes is required/);
});

test('final-schema-migration-confirmation=no blocked', () => {
    assertInvalid(
        { 'final-schema-migration-confirmation': 'no' },
        /final-schema-migration-confirmation=yes is required/
    );
});

test('allow-db-write=no blocked', () => {
    assertInvalid({ 'allow-db-write': 'no' }, /allow-db-write=yes is required/);
});

test('allow-schema-migration=no blocked', () => {
    assertInvalid({ 'allow-schema-migration': 'no' }, /allow-schema-migration=yes is required/);
});

test('allow-alter-table=no blocked', () => {
    assertInvalid({ 'allow-alter-table': 'no' }, /allow-alter-table=yes is required/);
});

test('allow-raw-match-data-write=yes blocked', () => {
    assertInvalid({ 'allow-raw-match-data-write': 'yes' }, /allow-raw-match-data-write=no is required/);
});

test('allow-matches-write=yes blocked', () => {
    assertInvalid({ 'allow-matches-write': 'yes' }, /allow-matches-write=no is required/);
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

test('execute-raw-write=yes blocked', () => {
    assertInvalid({ 'execute-raw-write': 'yes' }, /execute-raw-write=yes is blocked/);
});

test('rewrite-existing=yes blocked', () => {
    assertInvalid({ 'rewrite-existing': 'yes' }, /rewrite-existing=yes is blocked/);
});

test('drop-v1=yes blocked', () => {
    assertInvalid({ 'drop-v1': 'yes' }, /drop-v1=yes is blocked/);
});

test('touch-fotmob=yes blocked', () => {
    assertInvalid({ 'touch-fotmob': 'yes' }, /touch-fotmob=yes is blocked/);
});

test('live-request=yes blocked', () => {
    assertInvalid({ 'live-request': 'yes' }, /live-request=yes is blocked/);
});

test('buildForwardMigrationStatements includes exact DROP CONSTRAINT', () => {
    assert.equal(
        execute.buildForwardMigrationStatements()[0],
        'ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_key;'
    );
});

test('buildForwardMigrationStatements includes exact ADD CONSTRAINT', () => {
    assert.equal(
        execute.buildForwardMigrationStatements()[1],
        'ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_data_version_key UNIQUE (match_id, data_version);'
    );
});

test('verifyPreflight passes when current exists / target absent / no null / no duplicates', () => {
    const result = execute.verifyPreflight({
        current_constraint_exists: true,
        target_constraint_exists: false,
        data_version_null_rows: 0,
        duplicate_match_id_data_version_rows: 0,
    });
    assert.equal(result.ok, true);
});

test('verifyPreflight fails when current constraint absent', () => {
    const result = execute.verifyPreflight({
        current_constraint_exists: false,
        target_constraint_exists: false,
        data_version_null_rows: 0,
        duplicate_match_id_data_version_rows: 0,
    });
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /must exist/);
});

test('verifyPreflight fails when target constraint already exists', () => {
    const result = execute.verifyPreflight({
        current_constraint_exists: true,
        target_constraint_exists: true,
        data_version_null_rows: 0,
        duplicate_match_id_data_version_rows: 0,
    });
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /must be absent/);
});

test('verifyPreflight fails when data_version null rows > 0', () => {
    const result = execute.verifyPreflight({
        current_constraint_exists: true,
        target_constraint_exists: false,
        data_version_null_rows: 1,
        duplicate_match_id_data_version_rows: 0,
    });
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /null rows must be 0/);
});

test('verifyPreflight fails when duplicate match_id,data_version rows > 0', () => {
    const result = execute.verifyPreflight({
        current_constraint_exists: true,
        target_constraint_exists: false,
        data_version_null_rows: 0,
        duplicate_match_id_data_version_rows: 1,
    });
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /duplicate match_id,data_version/);
});

test('verifyPostcheck passes when current absent / target exists / row counts unchanged', () => {
    const result = execute.verifyPostcheck({
        current_constraint_exists: false,
        target_constraint_exists: true,
        row_counts_unchanged: true,
    });
    assert.equal(result.ok, true);
});

test('verifyPostcheck fails when row counts changed', () => {
    const result = execute.verifyPostcheck({
        current_constraint_exists: false,
        target_constraint_exists: true,
        row_counts_unchanged: false,
    });
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /row counts/);
});

test('fake DB transaction commits on success', async () => {
    const client = createFakeClient();
    const summary = await execute.runMigrationExecution(validArgs(), { client });
    assert.equal(summary.schema_migration_executed, true);
    assert.deepEqual(summary.transaction, { began: true, committed: true, rolled_back: false });
    assert.equal(client.state.calls.includes('COMMIT'), true);
});

test('fake DB transaction rolls back on ALTER failure', async () => {
    const client = createFakeClient({ failOnAlter: true });
    await assert.rejects(() => execute.runMigrationExecution(validArgs(), { client }), /ALTER failed/);
    assert.equal(client.state.calls.includes('ROLLBACK'), true);
    assert.equal(client.state.calls.includes('COMMIT'), false);
});

test('fake DB transaction rolls back on postcheck failure', async () => {
    const client = createFakeClient({ keepTargetAbsentAfterAlter: true });
    await assert.rejects(() => execute.runMigrationExecution(validArgs(), { client }), /postcheck failed/);
    assert.equal(client.state.calls.includes('ROLLBACK'), true);
    assert.equal(client.state.calls.includes('COMMIT'), false);
});

test('summary raw_match_data_write_executed=false', () => {
    const summary = execute.buildExecutionSummary();
    assert.equal(summary.raw_match_data_write_executed, false);
});

test('summary fotmob_access_executed=false', () => {
    const summary = execute.buildExecutionSummary();
    assert.equal(summary.fotmob_access_executed, false);
});

test('no INSERT/UPDATE/DELETE SQL generated', async () => {
    const client = createFakeClient();
    await execute.runMigrationExecution(validArgs(), { client });
    const sql = client.state.calls.join('\n');
    assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP TABLE)\b/i);
    assert.match(sql, /ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_key/);
    assert.match(sql, /ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_data_version_key/);
});

test('guard blocks schema migration write path when DRY_RUN is not false', async () => {
    await assert.rejects(
        () => runCliWithGuardEnv(
            validArgs(),
            { client: createFakeClient(), output() {} },
            { DRY_RUN: undefined }
        ),
        /DRY_RUN is enabled/
    );
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
                                    const result = await runCliWithGuardEnv(validArgs(), {
                                        client: createFakeClient(),
                                        output() {},
                                    });
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
                            const result = await runCliWithGuardEnv(validArgs(), {
                                client: createFakeClient(),
                                output() {},
                            });
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
                    throw new Error(`${['http', 'request'].join('.')} should not be called`);
                },
                async () => {
                    await withPatched(
                        https,
                        'request',
                        () => {
                            throw new Error(`${['https', 'request'].join('.')} should not be called`);
                        },
                        async () => {
                            const result = await runCliWithGuardEnv(validArgs(), {
                                client: createFakeClient(),
                                output() {},
                            });
                            assert.equal(result.status, 0);
                            assert.equal(result.payload.fotmob_access_executed, false);
                        }
                    );
                }
            );
        }
    );
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no parser/features/training import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /require\([^)]*(parser|feature|train|predict)/i);
});
