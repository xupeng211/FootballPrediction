#!/usr/bin/env node
'use strict';

const {
    RAW_MATCH_DATA_VERSIONS,
    selectCanonicalRawMatchData,
    isSyntheticOrUnknownVersion,
} = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

const PHASE = 'PHASE5_21L2H_RAW_MATCH_DATA_VERSION_AWARE_COMPATIBILITY_AUDIT';

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        table: null,
        preferredVersion: null,
        fallbackVersion: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowMigration: false,
        allowAlterTable: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        table: 'table',
        'preferred-version': 'preferredVersion',
        preferred_version: 'preferredVersion',
        'fallback-version': 'fallbackVersion',
        fallback_version: 'fallbackVersion',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        execute: 'execute',
        commit: 'commit',
        'touch-fotmob': 'touchFotmob',
        touch_fotmob: 'touchFotmob',
        'live-request': 'liveRequest',
        live_request: 'liveRequest',
        'allow-migration': 'allowMigration',
        allow_migration: 'allowMigration',
        'allow-alter-table': 'allowAlterTable',
        allow_alter_table: 'allowAlterTable',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowMigration',
        'allowAlterTable',
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        if (booleanKeys.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }
        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function normalizeAuditInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        table: normalizeText(input.table),
        preferredVersion: normalizeText(input.preferredVersion),
        fallbackVersion: normalizeText(input.fallbackVersion),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        execute: normalizeBooleanFlag(input.execute, false),
        commit: normalizeBooleanFlag(input.commit, false),
        touchFotmob: normalizeBooleanFlag(input.touchFotmob, false),
        liveRequest: normalizeBooleanFlag(input.liveRequest, false),
        allowMigration: normalizeBooleanFlag(input.allowMigration, false),
        allowAlterTable: normalizeBooleanFlag(input.allowAlterTable, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2H`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function validateAuditInput(input = {}) {
    const value = normalizeAuditInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    if (!value.source) errors.push('missing source=fotmob');
    else if (value.source !== 'fotmob') errors.push('source must be fotmob');
    if (!value.table) errors.push('missing table=raw_match_data');
    else if (value.table !== 'raw_match_data') errors.push('table must be raw_match_data');
    if (value.preferredVersion !== RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2) {
        errors.push('preferred-version must be fotmob_pageprops_v2');
    }
    if (value.fallbackVersion !== RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1) {
        errors.push('fallback-version must be fotmob_html_hyd_v1');
    }
    pushRequiredNo(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredNo(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredNo(errors, value.allowParserFeatures, 'allow-parser-features');
    pushRequiredNo(errors, value.allowTraining, 'allow-training');
    pushRequiredNo(errors, value.allowPrediction, 'allow-prediction');
    if (value.execute === true) errors.push('execute=yes is blocked in Phase 5.21L2H');
    if (value.commit === true) errors.push('commit=yes is blocked in Phase 5.21L2H');
    if (value.touchFotmob === true) errors.push('touch-fotmob=yes is blocked in Phase 5.21L2H');
    if (value.liveRequest === true) errors.push('live-request=yes is blocked in Phase 5.21L2H');
    if (value.allowMigration === true) errors.push('allow-migration=yes is blocked in Phase 5.21L2H');
    if (value.allowAlterTable === true) errors.push('allow-alter-table=yes is blocked in Phase 5.21L2H');
    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildSchemaConstraintSummary(constraints = []) {
    const rows = Array.isArray(constraints) ? constraints : [];
    const hasVersionedUnique = rows.some(
        row =>
            normalizeText(row.conname) === 'raw_match_data_match_id_data_version_key' ||
            /UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(normalizeText(row.definition))
    );
    const hasMatchIdUnique = rows.some(row => {
        const definition = normalizeText(row.definition);
        return (
            normalizeText(row.conname) === 'raw_match_data_match_id_key' ||
            (/UNIQUE\s*\(\s*match_id\s*\)/i.test(definition) &&
                !/UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(definition))
        );
    });
    return {
        unique_match_id_data_version_exists: hasVersionedUnique,
        unique_match_id_absent: !hasMatchIdUnique,
        unique_match_id_exists: hasMatchIdUnique,
    };
}

function buildDataVersionDistribution(rows = []) {
    return (Array.isArray(rows) ? rows : []).map(row => ({
        data_version: row.data_version ?? null,
        rows: Number(row.rows || 0),
    }));
}

function buildDuplicateSummary(rows = []) {
    const duplicates = (Array.isArray(rows) ? rows : []).map(row => ({
        match_id: row.match_id,
        data_version: row.data_version,
        rows: Number(row.rows || 0),
    }));
    return {
        duplicate_match_id_data_version_rows: duplicates.length,
        duplicates,
    };
}

function buildCanonicalSelectorDryRun(rows = [], { preferredVersion, fallbackVersion } = {}) {
    const grouped = new Map();
    for (const row of Array.isArray(rows) ? rows : []) {
        const key = normalizeText(row.match_id);
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(row);
    }

    return [...grouped.entries()]
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([matchId, matchRows]) => {
            let selected = null;
            let controlledError = null;
            try {
                selected = selectCanonicalRawMatchData({
                    rows: matchRows,
                    allowedVersions: [preferredVersion, fallbackVersion],
                    versionPriority: [preferredVersion, fallbackVersion],
                    excludeSyntheticUnknown: true,
                });
            } catch (error) {
                controlledError = String(error.message || error);
            }
            return {
                match_id: matchId,
                external_id: matchRows[0]?.external_id || null,
                available_versions: [...new Set(matchRows.map(row => row.data_version))].sort(),
                selected_canonical_version: selected?.data_version || null,
                selected_row_id: selected?.id ?? null,
                synthetic_unknown_excluded: matchRows.some(row => isSyntheticOrUnknownVersion(row.data_version)),
                controlled_error: controlledError,
            };
        });
}

function buildRiskInventory() {
    return {
        legacy_on_conflict_match_id_paths: [
            'src/infrastructure/harvesters/components/Persistence.js',
            'src/infrastructure/harvesters/TitanSlimHarvester.js',
            'src/infrastructure/services/MarathonService.js',
            'scripts/ops/backfill_historical_raw_match_data.js',
            'scripts/ops/seed_fotmob_sample.js',
            'scripts/ops/bulk_import_matches.js',
            'src/database/sql_store.py',
            'scripts/test/end_to_end_test.js',
        ],
        controlled_paths_updated: [
            'scripts/ops/l2_raw_match_data_ingest_preflight.js',
            'scripts/ops/l2_raw_match_data_write.js',
            'scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js',
            'scripts/ops/l2_remaining_raw_match_data_write.js',
        ],
        remaining_policy: 'legacy/admin ON CONFLICT(match_id) paths remain deprecated and agent-blocked until upgraded',
    };
}

function assertSelectOnly(sql) {
    const normalized = normalizeText(sql);
    if (!/^SELECT\b/i.test(normalized)) {
        throw new Error(`NON_SELECT_SQL_BLOCKED: ${normalized.slice(0, 80)}`);
    }
    if (/\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|MERGE|COPY|BEGIN|COMMIT|ROLLBACK)\b/i.test(normalized)) {
        throw new Error(`NON_SELECT_SQL_BLOCKED: ${normalized.slice(0, 80)}`);
    }
}

async function safeSelect(db, sql, values = []) {
    assertSelectOnly(sql);
    const result = await db.query(sql, values);
    return result.rows || [];
}

async function readAuditRows(db) {
    const constraints = await safeSelect(
        db,
        `
            SELECT
              conname,
              contype,
              pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'raw_match_data'
            ORDER BY conname
        `
    );
    const distribution = await safeSelect(
        db,
        `
            SELECT data_version, COUNT(*)::int AS rows
            FROM raw_match_data
            GROUP BY data_version
            ORDER BY data_version
        `
    );
    const duplicates = await safeSelect(
        db,
        `
            SELECT match_id, data_version, COUNT(*)::int AS rows
            FROM raw_match_data
            GROUP BY match_id, data_version
            HAVING COUNT(*) > 1
            ORDER BY match_id, data_version
        `
    );
    const rawRows = await safeSelect(
        db,
        `
            SELECT id, match_id, external_id, data_version, data_hash, collected_at
            FROM raw_match_data
            ORDER BY match_id, data_version, id
        `
    );
    return {
        constraints,
        distribution,
        duplicates,
        rawRows,
    };
}

function buildAuditResult(input, rows) {
    const value = normalizeAuditInput(input);
    return {
        phase: PHASE,
        audit_only: true,
        ok: true,
        source: value.source,
        table: value.table,
        preferred_version: value.preferredVersion,
        fallback_version: value.fallbackVersion,
        schema_constraint_check: buildSchemaConstraintSummary(rows.constraints),
        data_version_distribution: buildDataVersionDistribution(rows.distribution),
        duplicate_summary: buildDuplicateSummary(rows.duplicates),
        canonical_selector_dry_run: buildCanonicalSelectorDryRun(rows.rawRows, {
            preferredVersion: value.preferredVersion,
            fallbackVersion: value.fallbackVersion,
        }),
        risk_inventory: buildRiskInventory(),
        execution_flags: {
            db_write_executed: false,
            raw_match_data_write_executed: false,
            schema_migration_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
            fotmob_access_executed: false,
        },
    };
}

async function buildRawMatchDataVersionCompatibilityAudit(input = {}, dependencies = {}) {
    const validation = validateAuditInput(input);
    if (!validation.ok) {
        return {
            phase: PHASE,
            audit_only: true,
            ok: false,
            controlled_error: `INVALID_VERSION_COMPATIBILITY_AUDIT_INPUT:${validation.errors.join('; ')}`,
            errors: validation.errors,
            execution_flags: {
                db_write_executed: false,
                raw_match_data_write_executed: false,
                schema_migration_executed: false,
                parser_features_executed: false,
                training_executed: false,
                prediction_executed: false,
                fotmob_access_executed: false,
            },
        };
    }

    if (dependencies.auditRows) {
        return buildAuditResult(validation.value, dependencies.auditRows);
    }

    const pool = dependencies.pool || (dependencies.getPool ? dependencies.getPool() : createDefaultPool());
    const shouldClose = !dependencies.pool && !dependencies.getPool;
    try {
        const rows = await readAuditRows(pool);
        return buildAuditResult(validation.value, rows);
    } finally {
        if (shouldClose) {
            await closeDefaultPool();
        }
    }
}

function createDefaultPool() {
    return require('../../config/database').getPool();
}

async function closeDefaultPool() {
    await require('../../config/database').closePool();
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/raw_match_data_version_compatibility_audit.js --source=fotmob --table=raw_match_data --preferred-version=fotmob_pageprops_v2 --fallback-version=fotmob_html_hyd_v1 --allow-db-write=no --allow-raw-match-data-write=no --allow-parser-features=no --allow-training=no --allow-prediction=no',
        '',
        'Safety:',
        '  Phase 5.21L2H is SELECT-only: no DB write, raw_match_data write, schema migration, FotMob access, parser/features, training, or prediction.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const result = await buildRawMatchDataVersionCompatibilityAudit(args, dependencies);
    stdout(`${JSON.stringify(result, null, 2)}\n`);
    return result.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    {
                        phase: PHASE,
                        audit_only: true,
                        ok: false,
                        controlled_error: String(error.message || error),
                        execution_flags: {
                            db_write_executed: false,
                            raw_match_data_write_executed: false,
                            schema_migration_executed: false,
                            parser_features_executed: false,
                            training_executed: false,
                            prediction_executed: false,
                            fotmob_access_executed: false,
                        },
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validateAuditInput,
    buildSchemaConstraintSummary,
    buildDataVersionDistribution,
    buildDuplicateSummary,
    buildCanonicalSelectorDryRun,
    buildRiskInventory,
    buildRawMatchDataVersionCompatibilityAudit,
    runCli,
};
