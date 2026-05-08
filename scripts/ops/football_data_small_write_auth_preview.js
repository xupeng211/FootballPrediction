#!/usr/bin/env node
'use strict';

const fs = require('fs');

const { parseArgs: parseDryRunArgs, runDryRun } = require('./football_data_adapter_dry_run');
const { runPreflight } = require('./football_data_db_write_preflight');
const {
    runDuplicatePrecheck,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    buildDbConfig,
    assertSelectOnlySql,
} = require('./football_data_duplicate_precheck');
const { runInsertPolicyPrecheck } = require('./football_data_insert_policy_precheck');

const SMALL_WRITE_AUTH_PHASE = 'PHASE4.67C_FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW';
const APPROVED_FOR_DB_WRITE = 'approved_for_db_write';
const APPROVED_FOR_DRY_RUN = 'approved_for_dry_run';
const PG_DUMP_COMMAND_PREVIEW =
    'docker compose -f docker-compose.dev.yml exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > data/backups/<timestamp>_pre_football_data_small_write.dump';
const PG_RESTORE_COMMAND_PREVIEW =
    'docker compose -f docker-compose.dev.yml exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists <backup_path>';
const CURRENT_DB_TABLES = [
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
];

const CURRENT_DB_COUNTS_SQL = `
SELECT table_name, rows
FROM (
    SELECT 'matches' AS table_name, COUNT(*)::bigint AS rows, 1 AS sort_order FROM matches
    UNION ALL
    SELECT 'bookmaker_odds_history', COUNT(*)::bigint, 2 FROM bookmaker_odds_history
    UNION ALL
    SELECT 'raw_match_data', COUNT(*)::bigint, 3 FROM raw_match_data
    UNION ALL
    SELECT 'l3_features', COUNT(*)::bigint, 4 FROM l3_features
    UNION ALL
    SELECT 'match_features_training', COUNT(*)::bigint, 5 FROM match_features_training
    UNION ALL
    SELECT 'predictions', COUNT(*)::bigint, 6 FROM predictions
) counts
ORDER BY sort_order
`;

const REQUIRED_TABLES_SQL = `
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'matches',
      'bookmaker_odds_history',
      'raw_match_data',
      'l3_features',
      'match_features_training',
      'predictions'
  )
ORDER BY table_name
`;

const MATCH_ID_SCHEMA_SQL = `
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'matches'
  AND column_name = 'match_id'
LIMIT 1
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_small_write_auth_preview.js --source-manifest <path> --local-csv <path> [--json]',
        '  node scripts/ops/football_data_small_write_auth_preview.js --source-manifest <path> --local-csv <path> --commit',
        '',
        'Safety:',
        '  Phase 4.67C is authorization preview only. No DB writes, no pg_dump execution, no pg_restore execution.',
    ].join('\n');
}

function parseArgs(argv) {
    return parseDryRunArgs(argv);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function withDbClient(dependencies, callback) {
    if (dependencies.dbClient) {
        return callback(dependencies.dbClient);
    }

    const pool = dependencies.pool || createPool();
    const client = await pool.connect();
    try {
        return await callback(client);
    } finally {
        client.release();
        if (!dependencies.pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function buildRequiredBeforeSmallDbWrite() {
    return [
        'source manifest approval_status must be approved_for_db_write',
        'human approval note must identify exact source and exact CSV file',
        'operator must provide CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1 in future phase',
        'deterministic match_id strategy must be accepted',
        'duplicate policy must be accepted',
        'exact existing matches must not be inserted',
        'manual review candidates must not be inserted',
        'max insert rows must be explicit',
        'target tables must be explicit',
        'pg_dump backup must run immediately before write',
        'backup file must be non-empty',
        'write transaction must be small and auditable',
        'post-write row counts must be validated',
        'target inserted match_ids must be listed',
        'downstream training/prediction must remain blocked',
    ];
}

function buildPostWriteValidationChecklist() {
    return [
        'compare before/after row counts',
        'verify inserted match_ids only',
        'verify no odds insert unless explicitly authorized',
        'verify no raw/l3/training/prediction writes',
        'rerun dataset status',
        'rerun duplicate precheck',
        'record backup path',
        'record commit hash / report path',
    ];
}

function buildRollbackRestorePreview() {
    return [
        'restore is not executed automatically',
        'backup path must be reviewed by human',
        'restore would require explicit restore authorization',
        'restore command must be documented but not executed',
    ];
}

function buildApprovalRequirements() {
    return [
        'approved_for_db_write source manifest',
        'exact source + CSV human approval note',
        'future CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1 authorization',
        'explicit max_rows and target_tables decision',
    ];
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'select_only_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_legacy_runtime',
        'no_pg_dump_execution',
        'no_pg_restore_execution',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
    ];
}

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        db_write_allowed: false,
        small_write_authorized: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        would_execute_legacy_runtime: false,
        would_train_model: false,
        would_execute_prediction: false,
        would_load_model_artifact: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: SMALL_WRITE_AUTH_PHASE,
        mode: fields.mode || 'football-data-small-write-auth-preview',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        source_manifest_found: false,
        local_csv_found: false,
        csv_dry_run_passed: false,
        db_write_preflight_passed: false,
        duplicate_precheck_passed: false,
        insert_policy_precheck_passed: false,
        manifest_approval_status: null,
        sha256_match: false,
        row_count_match: false,
        commit_gate: 'blocked',
        current_db_counts: null,
        current_db_schema_preview: null,
        max_rows_preview: null,
        target_tables_preview: ['matches', 'bookmaker_odds_history'],
        approval_requirements: buildApprovalRequirements(),
        pg_dump_command_preview: PG_DUMP_COMMAND_PREVIEW,
        pg_restore_command_preview: PG_RESTORE_COMMAND_PREVIEW,
        required_before_small_db_write: buildRequiredBeforeSmallDbWrite(),
        post_write_validation: buildPostWriteValidationChecklist(),
        rollback_restore_preview: buildRollbackRestorePreview(),
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: [],
        warnings: [],
        ...fields,
    };
}

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: 'BLOCKED: football-data small DB write commit is not wired in Phase 4.67C.',
        errors: ['BLOCKED: football-data small DB write commit is not wired in Phase 4.67C.'],
    });
}

function buildManifestCompatibleDryRun(dependencies = {}) {
    if (dependencies.runDryRun) {
        return args => dependencies.runDryRun(args);
    }

    const dryRunDependencies = {
        ...(dependencies.dryRunDependencies || {}),
    };
    const readManifest = dryRunDependencies.readManifest || readJsonFile;
    let manifestApprovalStatus = null;

    dryRunDependencies.readManifest = manifestPath => {
        const manifest = readManifest(manifestPath);
        manifestApprovalStatus = manifest.approval_status || null;
        if (manifest.approval_status === APPROVED_FOR_DB_WRITE) {
            return {
                ...manifest,
                approval_status: APPROVED_FOR_DRY_RUN,
            };
        }
        return manifest;
    };

    return args => {
        const payload = runDryRun(args, dryRunDependencies);
        if (payload.ok && manifestApprovalStatus) {
            return {
                ...payload,
                approval_status: manifestApprovalStatus,
            };
        }
        return payload;
    };
}

function mapCurrentDbCounts(rows) {
    const mapped = {};
    for (const tableName of CURRENT_DB_TABLES) {
        mapped[tableName] = 0;
    }
    for (const row of rows || []) {
        mapped[row.table_name] = Number.parseInt(row.rows, 10);
    }
    return mapped;
}

function buildSchemaPreview(requiredTables, matchIdRow) {
    return {
        required_tables_found: requiredTables,
        required_tables_expected: CURRENT_DB_TABLES,
        matches_match_id: matchIdRow
            ? {
                  column_name: matchIdRow.column_name,
                  data_type: matchIdRow.data_type,
                  character_maximum_length: matchIdRow.character_maximum_length,
                  is_nullable: matchIdRow.is_nullable,
              }
            : null,
    };
}

function valueOrNull(value) {
    return value === undefined ? null : value;
}

function countOrZero(value) {
    return value || 0;
}

function buildIdentityFields(dryRunPayload, insertPolicyPayload) {
    return {
        manifest_approval_status: insertPolicyPayload.manifest_approval_status || dryRunPayload.approval_status || null,
        source_name: valueOrNull(dryRunPayload.source_name),
        parser_version: valueOrNull(dryRunPayload.parser_version),
        csv_dry_run_version: valueOrNull(dryRunPayload.dry_run_version),
    };
}

function buildPhaseFields(preflightPayload, duplicatePayload, insertPolicyPayload) {
    return {
        db_write_preflight_phase: valueOrNull(preflightPayload.phase),
        duplicate_precheck_phase: valueOrNull(duplicatePayload.phase),
        insert_policy_precheck_phase: valueOrNull(insertPolicyPayload.phase),
    };
}

function buildCandidateFields(dryRunPayload, duplicatePayload, insertPolicyPayload) {
    return {
        candidate_rows: dryRunPayload.candidate_rows.length,
        trainable_label_rows: countOrZero((dryRunPayload.row_classification || {}).trainable_label_rows),
        exact_existing_matches: countOrZero(duplicatePayload.exact_existing_matches),
        reversed_team_matches: countOrZero(duplicatePayload.reversed_team_matches),
        nearby_date_matches: countOrZero(duplicatePayload.nearby_date_matches),
        invalid_candidates: countOrZero(insertPolicyPayload.invalid_candidates),
        future_insert_candidates: countOrZero(insertPolicyPayload.future_insert_candidates),
        blocked_by_manifest_policy: countOrZero(insertPolicyPayload.blocked_by_manifest_policy),
        skip_existing_matches: countOrZero(insertPolicyPayload.skip_existing_matches),
        manual_review_required: countOrZero(insertPolicyPayload.manual_review_required),
        max_rows_preview: dryRunPayload.candidate_rows.length,
    };
}

function buildNonExecutionEchoFields(dryRunPayload, duplicatePayload, insertPolicyPayload) {
    return {
        dry_run_non_execution_confirmations: dryRunPayload.non_execution_confirmations || [],
        duplicate_precheck_non_execution_confirmations: duplicatePayload.non_execution_confirmations || [],
        insert_policy_non_execution_confirmations: insertPolicyPayload.non_execution_confirmations || [],
    };
}

function mergeWarnings(dryRunPayload, preflightPayload, duplicatePayload, insertPolicyPayload) {
    return [
        ...(dryRunPayload.warnings || []),
        ...(preflightPayload.warnings || []),
        ...(duplicatePayload.warnings || []),
        ...(insertPolicyPayload.warnings || []),
    ];
}

async function inspectCurrentDbState(dependencies = {}) {
    if (dependencies.inspectCurrentDbState) {
        return dependencies.inspectCurrentDbState();
    }

    return withDbClient(dependencies, async client => {
        await querySelectOnly(client, READ_ONLY_BEGIN_SQL);
        try {
            const countsResult = await querySelectOnly(client, CURRENT_DB_COUNTS_SQL);
            const requiredTablesResult = await querySelectOnly(client, REQUIRED_TABLES_SQL);
            const matchIdSchemaResult = await querySelectOnly(client, MATCH_ID_SCHEMA_SQL);
            return {
                current_db_counts: mapCurrentDbCounts(countsResult.rows || []),
                current_db_schema_preview: buildSchemaPreview(
                    (requiredTablesResult.rows || []).map(row => row.table_name),
                    (matchIdSchemaResult.rows || [])[0] || null
                ),
            };
        } finally {
            await querySelectOnly(client, READ_ONLY_ROLLBACK_SQL);
        }
    });
}

function buildSuccessPayload(args, dryRunPayload, preflightPayload, duplicatePayload, insertPolicyPayload, dbState) {
    const identityFields = buildIdentityFields(dryRunPayload, insertPolicyPayload);
    const phaseFields = buildPhaseFields(preflightPayload, duplicatePayload, insertPolicyPayload);
    const candidateFields = buildCandidateFields(dryRunPayload, duplicatePayload, insertPolicyPayload);
    const nonExecutionEchoFields = buildNonExecutionEchoFields(dryRunPayload, duplicatePayload, insertPolicyPayload);
    return {
        phase: SMALL_WRITE_AUTH_PHASE,
        mode: 'football-data-small-write-auth-preview',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        csv_dry_run_passed: true,
        db_write_preflight_passed: true,
        duplicate_precheck_passed: true,
        insert_policy_precheck_passed: true,
        ...identityFields,
        ...phaseFields,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        ...candidateFields,
        commit_gate: 'blocked',
        current_db_counts: dbState.current_db_counts,
        current_db_schema_preview: dbState.current_db_schema_preview,
        target_tables_preview: ['matches', 'bookmaker_odds_history'],
        approval_requirements: buildApprovalRequirements(),
        pg_dump_command_preview: PG_DUMP_COMMAND_PREVIEW,
        pg_restore_command_preview: PG_RESTORE_COMMAND_PREVIEW,
        required_before_small_db_write: buildRequiredBeforeSmallDbWrite(),
        post_write_validation: buildPostWriteValidationChecklist(),
        rollback_restore_preview: buildRollbackRestorePreview(),
        small_write_authorized_reason:
            'Phase 4.67C only previews future small DB write authorization requirements; real DB write remains blocked.',
        db_write_allowed_reason:
            'Phase 4.67C does not execute small DB writes, pg_dump, or pg_restore even when manifest approval_status is approved_for_db_write.',
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        ...nonExecutionEchoFields,
        warnings: mergeWarnings(dryRunPayload, preflightPayload, duplicatePayload, insertPolicyPayload),
        errors: [],
    };
}

function buildDryRunFailurePayload(args, dryRunPayload) {
    return buildFailurePayload(args, {
        mode: 'csv-dry-run-failed',
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        manifest_approval_status: dryRunPayload.approval_status || null,
        select_only_db_reads: false,
        errors: dryRunPayload.errors || ['football-data CSV dry-run failed'],
        warnings: dryRunPayload.warnings || [],
    });
}

function buildPreflightFailurePayload(args, dryRunPayload, preflightPayload) {
    return buildFailurePayload(args, {
        mode: 'db-write-preflight-failed',
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        csv_dry_run_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        manifest_approval_status: dryRunPayload.approval_status || null,
        select_only_db_reads: false,
        errors: preflightPayload.errors || ['football-data DB write preflight failed'],
        warnings: preflightPayload.warnings || [],
    });
}

function buildDuplicateFailurePayload(args, dryRunPayload, duplicatePayload) {
    return buildFailurePayload(args, {
        mode: 'duplicate-precheck-failed',
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        csv_dry_run_passed: true,
        db_write_preflight_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        manifest_approval_status: dryRunPayload.approval_status || null,
        select_only_db_reads: false,
        errors: duplicatePayload.errors || ['football-data duplicate precheck failed'],
        warnings: duplicatePayload.warnings || [],
    });
}

function buildInsertPolicyFailurePayload(args, dryRunPayload, insertPolicyPayload) {
    return buildFailurePayload(args, {
        mode: 'insert-policy-precheck-failed',
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        csv_dry_run_passed: true,
        db_write_preflight_passed: true,
        duplicate_precheck_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        manifest_approval_status: dryRunPayload.approval_status || null,
        select_only_db_reads: false,
        errors: insertPolicyPayload.errors || ['football-data insert policy precheck failed'],
        warnings: insertPolicyPayload.warnings || [],
    });
}

function buildDependencyRunArgs(args) {
    return {
        sourceManifest: args.sourceManifest,
        localCsv: args.localCsv,
    };
}

function buildPreflightDependencies(dependencies, dryRunPreview) {
    return {
        ...(dependencies.preflightDependencies || {}),
        runDryRun: dryRunPreview,
    };
}

function buildDbReadDependencies(dependencies, dryRunPreview, key) {
    return {
        ...(dependencies[key] || {}),
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
        runDryRun: dryRunPreview,
    };
}

async function runSmallWriteAuthPreview(args, dependencies = {}) {
    if (!args.sourceManifest || !args.localCsv) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            select_only_db_reads: false,
            errors: ['ERROR: provide --source-manifest=<path> and --local-csv=<path>'],
        });
    }

    const dryRunPreview = buildManifestCompatibleDryRun(dependencies);
    const dryRunArgs = buildDependencyRunArgs(args);

    const dryRunPayload = dryRunPreview(dryRunArgs);
    if (!dryRunPayload.ok) {
        return buildDryRunFailurePayload(args, dryRunPayload);
    }

    const preflightRunner = dependencies.runPreflight || runPreflight;
    const preflightPayload = await Promise.resolve(
        preflightRunner(dryRunArgs, buildPreflightDependencies(dependencies, dryRunPreview))
    );
    if (!preflightPayload.ok) {
        return buildPreflightFailurePayload(args, dryRunPayload, preflightPayload);
    }

    const duplicateRunner = dependencies.runDuplicatePrecheck || runDuplicatePrecheck;
    const duplicatePayload = await duplicateRunner(
        dryRunArgs,
        buildDbReadDependencies(dependencies, dryRunPreview, 'duplicateDependencies')
    );
    if (!duplicatePayload.ok) {
        return buildDuplicateFailurePayload(args, dryRunPayload, duplicatePayload);
    }

    const insertPolicyRunner = dependencies.runInsertPolicyPrecheck || runInsertPolicyPrecheck;
    const insertPolicyPayload = await insertPolicyRunner(
        dryRunArgs,
        buildDbReadDependencies(dependencies, dryRunPreview, 'insertPolicyDependencies')
    );
    if (!insertPolicyPayload.ok) {
        return buildInsertPolicyFailurePayload(args, dryRunPayload, insertPolicyPayload);
    }

    const dbState = await inspectCurrentDbState({
        ...dependencies,
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
    });

    return buildSuccessPayload(args, dryRunPayload, preflightPayload, duplicatePayload, insertPolicyPayload, dbState);
}

function appendOptionalTextFields(lines, payload) {
    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (payload.small_write_authorized_reason) {
        lines.push(`small_write_authorized_reason=${payload.small_write_authorized_reason}`);
    }
    if (payload.db_write_allowed_reason) {
        lines.push(`db_write_allowed_reason=${payload.db_write_allowed_reason}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
    }
}

function appendListSection(lines, title, values) {
    lines.push(`${title}:`);
    for (const value of values || []) {
        lines.push(`- ${value}`);
    }
}

function appendCurrentDbCounts(lines, counts) {
    lines.push('current_db_counts:');
    const values = counts || {};
    for (const tableName of CURRENT_DB_TABLES) {
        lines.push(`- ${tableName}=${values[tableName] ?? 'unknown'}`);
    }
}

function payloadToText(payload) {
    const lines = [
        `phase=${payload.phase}`,
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `csv_dry_run_passed=${payload.csv_dry_run_passed}`,
        `db_write_preflight_passed=${payload.db_write_preflight_passed}`,
        `duplicate_precheck_passed=${payload.duplicate_precheck_passed}`,
        `insert_policy_precheck_passed=${payload.insert_policy_precheck_passed}`,
        `sha256_match=${payload.sha256_match}`,
        `row_count_match=${payload.row_count_match}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        `manifest_approval_status=${payload.manifest_approval_status}`,
        `db_write_allowed=${payload.db_write_allowed}`,
        `small_write_authorized=${payload.small_write_authorized}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_execute_pg_restore=${payload.would_execute_pg_restore}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `max_rows_preview=${payload.max_rows_preview}`,
        `target_tables_preview=${JSON.stringify(payload.target_tables_preview || [])}`,
        `pg_dump_command_preview=${JSON.stringify(payload.pg_dump_command_preview)}`,
        `pg_restore_command_preview=${JSON.stringify(payload.pg_restore_command_preview)}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    if (payload.current_db_schema_preview) {
        lines.push(`current_db_schema_preview=${JSON.stringify(payload.current_db_schema_preview)}`);
    }

    appendOptionalTextFields(lines, payload);
    appendCurrentDbCounts(lines, payload.current_db_counts);
    appendListSection(lines, 'approval_requirements', payload.approval_requirements);
    appendListSection(lines, 'required_before_small_db_write', payload.required_before_small_db_write);
    appendListSection(lines, 'post_write_validation', payload.post_write_validation);
    appendListSection(lines, 'rollback_restore_preview', payload.rollback_restore_preview);
    appendListSection(lines, 'non_execution_confirmations', payload.non_execution_confirmations);

    return lines.join('\n');
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

async function main(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    try {
        const args = parseArgs(argv);
        if (args.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }
        if (args.commit) {
            const payload = buildBlockedCommitPayload(args);
            writePayload(payload, args.json, output);
            return 1;
        }

        const payload = await runSmallWriteAuthPreview(args, dependencies);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const json = argv.includes('--json');
        const payload = buildFailurePayload(
            {
                sourceManifest: '',
                localCsv: '',
            },
            {
                mode: 'runtime-error',
                select_only_db_reads: false,
                errors: [error.message],
            }
        );
        writePayload(payload, json, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => {
        process.exitCode = status;
    });
}

module.exports = {
    SMALL_WRITE_AUTH_PHASE,
    CURRENT_DB_COUNTS_SQL,
    REQUIRED_TABLES_SQL,
    MATCH_ID_SCHEMA_SQL,
    PG_DUMP_COMMAND_PREVIEW,
    PG_RESTORE_COMMAND_PREVIEW,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    runSmallWriteAuthPreview,
    inspectCurrentDbState,
    buildRequiredBeforeSmallDbWrite,
    buildPostWriteValidationChecklist,
    buildRollbackRestorePreview,
    buildNonExecutionConfirmations,
    buildManifestCompatibleDryRun,
    payloadToText,
    assertSelectOnlySql,
    main,
};
