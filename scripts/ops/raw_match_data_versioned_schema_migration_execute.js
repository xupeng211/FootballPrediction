#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2G_RAW_MATCH_DATA_VERSIONED_SCHEMA_MIGRATION_EXECUTION';
const EXPECTED = Object.freeze({
    source: 'fotmob',
    table: 'raw_match_data',
    currentUnique: 'match_id',
    targetUnique: 'match_id,data_version',
    currentConstraint: 'raw_match_data_match_id_key',
    targetConstraint: 'raw_match_data_match_id_data_version_key',
});
const REQUIRED_YES_FLAGS = Object.freeze([
    'final-schema-migration-confirmation',
    'allow-db-write',
    'allow-schema-migration',
    'allow-alter-table',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allow-raw-match-data-write',
    'allow-matches-write',
    'allow-parser-features',
    'allow-training',
    'allow-prediction',
]);
const BLOCKED_YES_FLAGS = Object.freeze([
    'execute-raw-write',
    'rewrite-existing',
    'drop-v1',
    'touch-fotmob',
    'live-request',
]);
const COUNT_TABLES = Object.freeze([
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function toKebabKey(key) {
    return normalizeText(key)
        .replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        .replace(/^--+/, '');
}

function parseArgs(argv = []) {
    const args = {};
    for (let index = 0; index < argv.length; index += 1) {
        const token = String(argv[index]);
        if (!token.startsWith('--')) continue;
        const raw = token.slice(2);
        const eqIndex = raw.indexOf('=');
        if (eqIndex >= 0) {
            args[toKebabKey(raw.slice(0, eqIndex))] = raw.slice(eqIndex + 1);
            continue;
        }

        const next = argv[index + 1];
        if (next && !String(next).startsWith('--')) {
            args[toKebabKey(raw)] = next;
            index += 1;
        } else {
            args[toKebabKey(raw)] = 'yes';
        }
    }
    return args;
}

function normalizeBooleanFlag(value) {
    const normalized = normalizeText(value).toLowerCase();
    if (['yes', 'true', '1', 'y', 'on'].includes(normalized)) return true;
    if (['no', 'false', '0', 'n', 'off'].includes(normalized)) return false;
    return null;
}

function normalizeList(value) {
    return normalizeText(value)
        .split(',')
        .map(part => part.trim())
        .filter(Boolean);
}

function listEquals(actual, expected) {
    return actual.length === expected.length && actual.every((value, index) => value === expected[index]);
}

function requireExact(input, key, expected, errors) {
    const actual = normalizeText(input[key]);
    if (!actual) {
        errors.push(`${key}=${expected} is required`);
    } else if (actual !== expected) {
        errors.push(`${key} must be ${expected}`);
    }
    return actual;
}

function requireExactList(input, key, expected, errors) {
    const raw = normalizeText(input[key]);
    const expectedList = normalizeList(expected);
    const actualList = normalizeList(raw);
    if (!raw) {
        errors.push(`${key}=${expected} is required`);
    } else if (!listEquals(actualList, expectedList)) {
        errors.push(`${key} must be ${expected}`);
    }
    return actualList;
}

function requireYes(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value !== true) {
        errors.push(`${key}=yes is required`);
    }
    return value;
}

function requireNo(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value !== false) {
        errors.push(`${key}=no is required`);
    }
    return value;
}

function blockYes(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value === true) {
        errors.push(`${key}=yes is blocked in Phase 5.21L2G`);
    }
    return value;
}

function validateExecutionInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    if (!source) {
        errors.push('source=fotmob is required');
    } else if (source !== EXPECTED.source) {
        errors.push('source must be fotmob');
    }

    const table = requireExact(input, 'table', EXPECTED.table, errors);
    const currentUnique = requireExactList(input, 'current-unique', EXPECTED.currentUnique, errors);
    const targetUnique = requireExactList(input, 'target-unique', EXPECTED.targetUnique, errors);
    const currentConstraint = requireExact(input, 'current-constraint', EXPECTED.currentConstraint, errors);
    const targetConstraint = requireExact(input, 'target-constraint', EXPECTED.targetConstraint, errors);

    const yesFlags = {};
    for (const flag of REQUIRED_YES_FLAGS) {
        yesFlags[flag] = requireYes(input, flag, errors);
    }

    const noFlags = {};
    for (const flag of REQUIRED_NO_FLAGS) {
        noFlags[flag] = requireNo(input, flag, errors);
    }

    for (const flag of BLOCKED_YES_FLAGS) {
        blockYes(input, flag, errors);
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source: EXPECTED.source,
            table,
            currentUnique,
            targetUnique,
            currentConstraint,
            targetConstraint,
            finalSchemaMigrationConfirmation: yesFlags['final-schema-migration-confirmation'],
            allowDbWrite: yesFlags['allow-db-write'],
            allowSchemaMigration: yesFlags['allow-schema-migration'],
            allowAlterTable: yesFlags['allow-alter-table'],
            allowRawMatchDataWrite: noFlags['allow-raw-match-data-write'],
            allowMatchesWrite: noFlags['allow-matches-write'],
            allowParserFeatures: noFlags['allow-parser-features'],
            allowTraining: noFlags['allow-training'],
            allowPrediction: noFlags['allow-prediction'],
        },
    };
}

function buildRowCountQuery() {
    return `
SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
UNION ALL
SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
UNION ALL
SELECT 'raw_match_data', COUNT(*)::int FROM raw_match_data
UNION ALL
SELECT 'l3_features', COUNT(*)::int FROM l3_features
UNION ALL
SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
UNION ALL
SELECT 'predictions', COUNT(*)::int FROM predictions;
`.trim();
}

function buildPreflightQueries() {
    return {
        constraintStatus: `
SELECT
  COUNT(*) FILTER (
    WHERE conname = '${EXPECTED.currentConstraint}'
      AND contype = 'u'
      AND pg_get_constraintdef(c.oid) = 'UNIQUE (match_id)'
  )::int AS current_constraint_rows,
  COUNT(*) FILTER (
    WHERE conname = '${EXPECTED.targetConstraint}'
      AND contype = 'u'
      AND pg_get_constraintdef(c.oid) = 'UNIQUE (match_id, data_version)'
  )::int AS target_constraint_rows
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = '${EXPECTED.table}';
`.trim(),
        rowCounts: buildRowCountQuery(),
        dataVersionNullRows: `
SELECT COUNT(*)::int AS data_version_null_rows
FROM raw_match_data
WHERE data_version IS NULL;
`.trim(),
        duplicateMatchIdDataVersionRows: `
SELECT COUNT(*)::int AS duplicate_match_id_data_version_rows
FROM (
  SELECT match_id, data_version
  FROM raw_match_data
  GROUP BY match_id, data_version
  HAVING COUNT(*) > 1
) duplicates;
`.trim(),
    };
}

function buildForwardMigrationStatements() {
    return [
        `ALTER TABLE raw_match_data DROP CONSTRAINT ${EXPECTED.currentConstraint};`,
        `ALTER TABLE raw_match_data ADD CONSTRAINT ${EXPECTED.targetConstraint} UNIQUE (match_id, data_version);`,
    ];
}

function buildPostcheckQueries() {
    return {
        constraintStatus: `
SELECT
  COUNT(*) FILTER (
    WHERE conname = '${EXPECTED.currentConstraint}'
      AND contype = 'u'
  )::int AS current_constraint_rows,
  COUNT(*) FILTER (
    WHERE conname = '${EXPECTED.targetConstraint}'
      AND contype = 'u'
      AND pg_get_constraintdef(c.oid) = 'UNIQUE (match_id, data_version)'
  )::int AS target_constraint_rows
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = '${EXPECTED.table}';
`.trim(),
        rowCounts: buildRowCountQuery(),
    };
}

function toInteger(value) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
}

function rowCountsFromRows(rows = []) {
    const counts = {};
    for (const row of rows) {
        counts[row.table_name] = toInteger(row.rows);
    }
    for (const tableName of COUNT_TABLES) {
        if (!Object.prototype.hasOwnProperty.call(counts, tableName)) {
            counts[tableName] = 0;
        }
    }
    return counts;
}

function rowCountsEqual(before = {}, after = {}) {
    return COUNT_TABLES.every(tableName => toInteger(before[tableName]) === toInteger(after[tableName]));
}

function buildPreflightFromRows(results = {}) {
    const constraintRow = results.constraintStatus?.rows?.[0] || {};
    const nullRow = results.dataVersionNullRows?.rows?.[0] || {};
    const duplicateRow = results.duplicateMatchIdDataVersionRows?.rows?.[0] || {};
    return {
        data_version_null_rows: toInteger(nullRow.data_version_null_rows),
        duplicate_match_id_data_version_rows: toInteger(duplicateRow.duplicate_match_id_data_version_rows),
        current_constraint_exists: toInteger(constraintRow.current_constraint_rows) > 0,
        target_constraint_exists: toInteger(constraintRow.target_constraint_rows) > 0,
    };
}

function buildPostcheckFromRows(results = {}, rowCountsBefore = {}) {
    const constraintRow = results.constraintStatus?.rows?.[0] || {};
    const rowCountsAfter = rowCountsFromRows(results.rowCounts?.rows || []);
    return {
        current_constraint_exists: toInteger(constraintRow.current_constraint_rows) > 0,
        target_constraint_exists: toInteger(constraintRow.target_constraint_rows) > 0,
        row_counts_unchanged: rowCountsEqual(rowCountsBefore, rowCountsAfter),
    };
}

function verifyPreflight(preflight = {}) {
    const errors = [];
    if (preflight.current_constraint_exists !== true) {
        errors.push(`${EXPECTED.currentConstraint} must exist before migration`);
    }
    if (preflight.target_constraint_exists !== false) {
        errors.push(`${EXPECTED.targetConstraint} must be absent before migration`);
    }
    if (toInteger(preflight.data_version_null_rows) !== 0) {
        errors.push('data_version null rows must be 0 before migration');
    }
    if (toInteger(preflight.duplicate_match_id_data_version_rows) !== 0) {
        errors.push('duplicate match_id,data_version rows must be 0 before migration');
    }
    return {
        ok: errors.length === 0,
        errors,
    };
}

function verifyPostcheck(postcheck = {}) {
    const errors = [];
    if (postcheck.current_constraint_exists !== false) {
        errors.push(`${EXPECTED.currentConstraint} must be absent after migration`);
    }
    if (postcheck.target_constraint_exists !== true) {
        errors.push(`${EXPECTED.targetConstraint} must exist after migration`);
    }
    if (postcheck.row_counts_unchanged !== true) {
        errors.push('row counts must remain unchanged after schema migration');
    }
    return {
        ok: errors.length === 0,
        errors,
    };
}

function buildExecutionSummary({
    schemaMigrationExecuted = false,
    transaction = {},
    preflight = {},
    postcheck = {},
    rowCountsBefore = {},
    rowCountsAfter = {},
    error = null,
} = {}) {
    return {
        phase: PHASE,
        schema_migration_executed: schemaMigrationExecuted,
        table: EXPECTED.table,
        migration: {
            from: 'UNIQUE(match_id)',
            to: 'UNIQUE(match_id,data_version)',
            dropped_constraint: schemaMigrationExecuted ? EXPECTED.currentConstraint : null,
            added_constraint: schemaMigrationExecuted ? EXPECTED.targetConstraint : null,
        },
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        preflight,
        postcheck,
        row_counts_before: rowCountsBefore,
        row_counts_after: rowCountsAfter,
        raw_match_data_write_executed: false,
        matches_write_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
        fotmob_access_executed: false,
        ...(error ? { ok: false, error: normalizeText(error.message || error) } : { ok: true }),
    };
}

function assertAllowedSql(sql) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ');
    const statements = new Set([
        'BEGIN',
        'COMMIT',
        'ROLLBACK',
        ...buildForwardMigrationStatements().map(statement => statement.replace(/\s+/g, ' ').trim()),
    ]);

    if (normalized.startsWith('SELECT ') || statements.has(normalized)) {
        return;
    }

    throw new Error(`SQL is not allowed in Phase 5.21L2G: ${normalized.slice(0, 120)}`);
}

async function queryAllowed(client, sql) {
    assertAllowedSql(sql);
    return client.query(sql);
}

async function collectPreflight(client) {
    const queries = buildPreflightQueries();
    const constraintStatus = await queryAllowed(client, queries.constraintStatus);
    const rowCounts = await queryAllowed(client, queries.rowCounts);
    const dataVersionNullRows = await queryAllowed(client, queries.dataVersionNullRows);
    const duplicateMatchIdDataVersionRows = await queryAllowed(client, queries.duplicateMatchIdDataVersionRows);
    const rowCountsBefore = rowCountsFromRows(rowCounts.rows || []);
    const preflight = buildPreflightFromRows({
        constraintStatus,
        dataVersionNullRows,
        duplicateMatchIdDataVersionRows,
    });
    return {
        preflight,
        rowCountsBefore,
    };
}

async function collectPostcheck(client, rowCountsBefore) {
    const queries = buildPostcheckQueries();
    const constraintStatus = await queryAllowed(client, queries.constraintStatus);
    const rowCounts = await queryAllowed(client, queries.rowCounts);
    const rowCountsAfter = rowCountsFromRows(rowCounts.rows || []);
    const postcheck = buildPostcheckFromRows({ constraintStatus, rowCounts }, rowCountsBefore);
    return {
        postcheck,
        rowCountsAfter,
    };
}

function createDefaultPool() {
    const { getPool, closePool } = require('../../config/database');
    return {
        pool: getPool(),
        close: closePool,
    };
}

async function runMigrationExecution(input = {}, dependencies = {}) {
    const transaction = { began: false, committed: false, rolled_back: false };
    let client = dependencies.client || null;
    let releaseClient = false;
    let closePool = null;
    let preflight = {};
    let postcheck = {};
    let rowCountsBefore = {};
    let rowCountsAfter = {};

    if (!client) {
        const defaultPool = dependencies.pool ? { pool: dependencies.pool, close: null } : createDefaultPool();
        closePool = defaultPool.close;
        client = await defaultPool.pool.connect();
        releaseClient = true;
    }

    try {
        await queryAllowed(client, 'BEGIN');
        transaction.began = true;

        const collectedPreflight = await collectPreflight(client);
        preflight = collectedPreflight.preflight;
        rowCountsBefore = collectedPreflight.rowCountsBefore;
        const preflightVerification = verifyPreflight(preflight);
        if (!preflightVerification.ok) {
            throw new Error(`preflight failed: ${preflightVerification.errors.join('; ')}`);
        }

        for (const statement of buildForwardMigrationStatements()) {
            await queryAllowed(client, statement);
        }

        const collectedPostcheck = await collectPostcheck(client, rowCountsBefore);
        postcheck = collectedPostcheck.postcheck;
        rowCountsAfter = collectedPostcheck.rowCountsAfter;
        const postcheckVerification = verifyPostcheck(postcheck);
        if (!postcheckVerification.ok) {
            throw new Error(`postcheck failed: ${postcheckVerification.errors.join('; ')}`);
        }

        await queryAllowed(client, 'COMMIT');
        transaction.committed = true;
        return buildExecutionSummary({
            schemaMigrationExecuted: true,
            transaction,
            preflight,
            postcheck,
            rowCountsBefore,
            rowCountsAfter,
        });
    } catch (error) {
        if (transaction.began && !transaction.committed) {
            try {
                await queryAllowed(client, 'ROLLBACK');
                transaction.rolled_back = true;
            } catch (rollbackError) {
                error.rollback_error = rollbackError.message;
            }
        }
        const summary = buildExecutionSummary({
            schemaMigrationExecuted: false,
            transaction,
            preflight,
            postcheck,
            rowCountsBefore,
            rowCountsAfter,
            error,
        });
        error.controlledPayload = summary;
        throw error;
    } finally {
        if (releaseClient && client?.release) {
            client.release();
        }
        if (closePool) {
            await closePool();
        }
    }
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsedArgs = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateExecutionInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        const payload = {
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            schema_migration_executed: false,
            raw_match_data_write_executed: false,
            matches_write_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
            fotmob_access_executed: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    try {
        const payload = await runMigrationExecution(validation.value, dependencies);
        output(payload);
        return { status: 0, payload };
    } catch (error) {
        const payload =
            error.controlledPayload ||
            buildExecutionSummary({
                schemaMigrationExecuted: false,
                error,
            });
        output(payload);
        return { status: 1, payload };
    }
}

module.exports = {
    PHASE,
    EXPECTED,
    parseArgs,
    normalizeBooleanFlag,
    validateExecutionInput,
    buildPreflightQueries,
    buildForwardMigrationStatements,
    buildPostcheckQueries,
    verifyPreflight,
    verifyPostcheck,
    buildExecutionSummary,
    runMigrationExecution,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
