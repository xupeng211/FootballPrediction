#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2F_RAW_MATCH_DATA_VERSIONED_SCHEMA_MIGRATION_PREFLIGHT';
const EXPECTED = Object.freeze({
    source: 'fotmob',
    table: 'raw_match_data',
    currentUnique: 'match_id',
    targetUnique: 'match_id,data_version',
    targetVersion: 'fotmob_pageprops_v2',
});
const DEFAULT_CURRENT_UNIQUE_CONSTRAINT = 'raw_match_data_match_id_key';
const DEFAULT_TARGET_UNIQUE_CONSTRAINT = 'raw_match_data_match_id_data_version_key';
const REQUIRED_NO_FLAGS = Object.freeze([
    'allow-db-write',
    'allow-migration',
    'allow-raw-match-data-write',
    'allow-parser-features',
    'allow-training',
    'allow-prediction',
]);
const BLOCKED_YES_FLAGS = Object.freeze([
    'execute',
    'commit',
    'alter-table',
    'drop-constraint',
    'add-constraint',
    'create-index',
    'drop-index',
]);
const DEFAULT_SCHEMA_PREFLIGHT = Object.freeze({
    currentUniqueMatchIdConstraint: DEFAULT_CURRENT_UNIQUE_CONSTRAINT,
    constraints: [{ conname: DEFAULT_CURRENT_UNIQUE_CONSTRAINT, definition: 'UNIQUE (match_id)' }],
    indexes: [
        {
            indexname: DEFAULT_CURRENT_UNIQUE_CONSTRAINT,
            indexdef: 'CREATE UNIQUE INDEX raw_match_data_match_id_key ON public.raw_match_data USING btree (match_id)',
        },
    ],
    dataVersionNullRows: 0,
    duplicateMatchIdRows: 0,
    duplicateMatchIdDataVersionRows: 0,
});

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
        const token = argv[index];
        if (!token.startsWith('--')) continue;
        const raw = token.slice(2);
        const eqIndex = raw.indexOf('=');
        if (eqIndex >= 0) {
            args[toKebabKey(raw.slice(0, eqIndex))] = raw.slice(eqIndex + 1);
            continue;
        }
        const next = argv[index + 1];
        if (next && !next.startsWith('--')) {
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
    if (['yes', 'true', '1', 'y'].includes(normalized)) return true;
    if (['no', 'false', '0', 'n'].includes(normalized)) return false;
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
        errors.push(`${key}=yes is blocked in Phase 5.21L2F`);
    }
    return value;
}

function validatePreflightInput(input = {}) {
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
    const targetVersion = requireExact(input, 'target-version', EXPECTED.targetVersion, errors);

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
            targetVersion,
            allowDbWrite: noFlags['allow-db-write'],
            allowMigration: noFlags['allow-migration'],
            allowRawMatchDataWrite: noFlags['allow-raw-match-data-write'],
            allowParserFeatures: noFlags['allow-parser-features'],
            allowTraining: noFlags['allow-training'],
            allowPrediction: noFlags['allow-prediction'],
        },
    };
}

function normalizeSchemaDefinitions(items = []) {
    if (!Array.isArray(items)) return [];
    return items
        .map(item => {
            if (typeof item === 'string') return item;
            return [item.conname, item.indexname, item.definition, item.indexdef].filter(Boolean).join(' ');
        })
        .map(value => normalizeText(value).replace(/\s+/g, ' ').toLowerCase())
        .filter(Boolean);
}

function hasUniqueForColumns(definitions = [], columns = []) {
    const compactColumns = columns.join(',');
    const compactColumnsReversed = [...columns].reverse().join(',');
    return definitions.some(definition => {
        const compact = definition.replace(/\s+/g, '');
        return (
            compact.includes(`unique(${compactColumns})`) ||
            compact.includes(`unique(${compactColumnsReversed})`) ||
            (compact.includes('uniqueindex') &&
                (compact.includes(`btree(${compactColumns})`) ||
                    compact.includes(`btree(${compactColumnsReversed})`))) ||
            (compact.includes('uniqueconstraint') &&
                (compact.includes(`btree(${compactColumns})`) || compact.includes(`btree(${compactColumnsReversed})`)))
        );
    });
}

function integerOrZero(value) {
    const numberValue = Number(value);
    return Number.isInteger(numberValue) && numberValue >= 0 ? numberValue : 0;
}

function buildSchemaPreflight(schema = {}) {
    const source = { ...DEFAULT_SCHEMA_PREFLIGHT, ...schema };
    const definitions = normalizeSchemaDefinitions([...(source.constraints || []), ...(source.indexes || [])]);
    const currentUniqueExists = hasUniqueForColumns(definitions, ['match_id']);
    const targetUniqueExists = hasUniqueForColumns(definitions, ['match_id', 'data_version']);
    const dataVersionNullRows = integerOrZero(source.dataVersionNullRows);
    const duplicateMatchIdRows = integerOrZero(source.duplicateMatchIdRows);
    const duplicateMatchIdDataVersionRows = integerOrZero(source.duplicateMatchIdDataVersionRows);
    const safeToPlanMigration =
        currentUniqueExists === true &&
        targetUniqueExists === false &&
        dataVersionNullRows === 0 &&
        duplicateMatchIdDataVersionRows === 0;

    return {
        current_unique_match_id_constraint: source.currentUniqueMatchIdConstraint || DEFAULT_CURRENT_UNIQUE_CONSTRAINT,
        current_unique_match_id_exists: currentUniqueExists,
        target_unique_match_id_data_version_exists: targetUniqueExists,
        data_version_null_rows: dataVersionNullRows,
        duplicate_match_id_rows: duplicateMatchIdRows,
        duplicate_match_id_data_version_rows: duplicateMatchIdDataVersionRows,
        safe_to_plan_migration: safeToPlanMigration,
    };
}

function buildForwardMigrationPlan() {
    return [
        `ALTER TABLE raw_match_data DROP CONSTRAINT ${DEFAULT_CURRENT_UNIQUE_CONSTRAINT};`,
        `ALTER TABLE raw_match_data ADD CONSTRAINT ${DEFAULT_TARGET_UNIQUE_CONSTRAINT} UNIQUE (match_id, data_version);`,
    ];
}

function buildRollbackPlan() {
    return [
        'Precondition: SELECT match_id FROM raw_match_data GROUP BY match_id HAVING COUNT(*) > 1 returns 0 rows',
        `ALTER TABLE raw_match_data DROP CONSTRAINT ${DEFAULT_TARGET_UNIQUE_CONSTRAINT};`,
        `ALTER TABLE raw_match_data ADD CONSTRAINT ${DEFAULT_CURRENT_UNIQUE_CONSTRAINT} UNIQUE (match_id);`,
    ];
}

function buildCodeImpactSummary() {
    return {
        writers_must_change_conflict_target: true,
        readers_must_filter_data_version: true,
        canonical_selector_recommended: true,
        controlled_writers_to_update: [
            'scripts/ops/l2_raw_match_data_write.js',
            'scripts/ops/l2_remaining_raw_match_data_write.js',
            'future pageProps v2 writer',
        ],
        reader_categories_to_audit: [
            'feature smelter raw joins',
            'ML dataset/inference raw queries',
            'ops reports using raw_match_data joins',
        ],
    };
}

function buildRawMatchDataVersionedSchemaMigrationPreflight(input = {}, schema = {}) {
    const currentUnique = Array.isArray(input.currentUnique)
        ? input.currentUnique
        : normalizeList(EXPECTED.currentUnique);
    const targetUnique = Array.isArray(input.targetUnique) ? input.targetUnique : normalizeList(EXPECTED.targetUnique);

    return {
        phase: PHASE,
        planning_only: true,
        source: input.source || EXPECTED.source,
        table: input.table || EXPECTED.table,
        current_unique: currentUnique,
        target_unique: targetUnique,
        target_version: input.targetVersion || EXPECTED.targetVersion,
        schema_preflight: buildSchemaPreflight(schema),
        exact_forward_migration_plan: buildForwardMigrationPlan(),
        exact_rollback_plan: buildRollbackPlan(),
        execution_this_phase: {
            db_write_executed: false,
            migration_executed: false,
            alter_table_executed: false,
            create_index_executed: false,
            drop_index_executed: false,
        },
        code_impact_summary: buildCodeImpactSummary(),
        next_phases: [
            'Phase 5.21L2G: controlled schema migration execution',
            'Phase 5.21L2H: pageProps v2 single-target write preflight',
            'Phase 5.21L2I: pageProps v2 single-target controlled write',
        ],
        network_access_executed: false,
        db_write_executed: false,
        migration_executed: false,
        raw_match_data_write_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsedArgs = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePreflightInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        const payload = {
            phase: PHASE,
            planning_only: true,
            ok: false,
            blocked: true,
            errors: validation.errors,
            network_access_executed: false,
            db_write_executed: false,
            migration_executed: false,
            raw_match_data_write_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    const payload = {
        ok: true,
        ...buildRawMatchDataVersionedSchemaMigrationPreflight(validation.value, dependencies.schema || {}),
    };
    output(payload);
    return { status: 0, payload };
}

module.exports = {
    PHASE,
    EXPECTED,
    parseArgs,
    normalizeBooleanFlag,
    validatePreflightInput,
    buildSchemaPreflight,
    buildForwardMigrationPlan,
    buildRollbackPlan,
    buildCodeImpactSummary,
    buildRawMatchDataVersionedSchemaMigrationPreflight,
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
