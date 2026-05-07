#!/usr/bin/env node
'use strict';

const { runDryRun, parseArgs: parseDryRunArgs } = require('./football_data_adapter_dry_run');

const PREFLIGHT_PHASE = 'PHASE4.64C_FOOTBALL_DATA_DB_WRITE_PREFLIGHT';

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_db_write_preflight.js --source-manifest <path> --local-csv <path> [--json]',
        '  node scripts/ops/football_data_db_write_preflight.js --source-manifest <path> --local-csv <path> --commit',
        '',
        'Safety:',
        '  Phase 4.64C is preflight/runbook preview only. No DB writes, no DB reads, no pg_dump execution.',
    ].join('\n');
}

function parseArgs(argv) {
    return parseDryRunArgs(argv);
}

function buildRequiredBeforeDbWrite() {
    return [
        'approval_status must be approved_for_db_write',
        'source manifest must include human approval note',
        'deterministic match_id strategy must be finalized',
        'duplicate detection against DB must be SELECT-only prechecked',
        'pg_dump backup must be created immediately before write',
        'max rows must be small and explicit',
        'target tables must be declared',
        'rollback/restore plan must be written',
        'post-write row counts must be validated',
        'training/prediction must remain blocked',
    ];
}

function buildFuturePgDumpRunbook() {
    return [
        'Stop before write and request explicit DB write authorization.',
        'Confirm source manifest is approved_for_db_write and includes license/provenance approval.',
        'Run SELECT-only duplicate/existing match precheck in a separate authorized phase.',
        'Create pg_dump backup immediately before any future write.',
        'Record backup path, sha256, timestamp, DB name, and operator in the write report.',
        'Write only an explicit small batch after backup verification.',
        'Validate post-write row counts and inserted match IDs.',
        'Keep training and prediction gates blocked until separately authorized.',
    ];
}

function buildFutureValidationChecklist() {
    return [
        'source manifest sha256 and row_count still match local CSV',
        'candidate rows reviewed and max row count explicitly approved',
        'target tables limited to matches and optional future odds history',
        'odds remain preview-only until odds write policy is separately approved',
        'rollback restore command documented but not executed by this preflight',
        'post-write SELECT-only counts compared against pre-write counts',
        'no training or prediction command is chained after write',
    ];
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'no_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_legacy_runtime',
        'no_pg_dump_execution',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_adapted_csv_writes',
        'no_staging_writes',
    ];
}

function buildSafetyFlags() {
    return {
        db_write_allowed: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_execute_pg_dump: false,
        would_access_network: false,
        would_write_files: false,
        would_execute_legacy_runtime: false,
        would_train_model: false,
        would_execute_prediction: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: PREFLIGHT_PHASE,
        mode: fields.mode || 'football-data-db-write-preflight',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        source_manifest_found: false,
        local_csv_found: false,
        dry_run_passed: false,
        sha256_match: false,
        row_count_match: false,
        commit_gate: 'blocked',
        required_before_db_write: buildRequiredBeforeDbWrite(),
        future_pg_dump_runbook: buildFuturePgDumpRunbook(),
        future_validation_checklist: buildFutureValidationChecklist(),
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
        blocked_reason: 'BLOCKED: football-data DB write commit is not wired in Phase 4.64C.',
        errors: ['BLOCKED: football-data DB write commit is not wired in Phase 4.64C.'],
    });
}

function buildPreflightPlan(dryRunPayload) {
    const rowClassification = dryRunPayload.row_classification || {};
    return {
        target_tables_preview: ['matches', 'bookmaker_odds_history_preview_only'],
        max_rows_preview: dryRunPayload.candidate_rows.length,
        candidate_rows: dryRunPayload.candidate_rows.length,
        trainable_label_rows: rowClassification.trainable_label_rows || 0,
        odds_preview_rows: rowClassification.odds_preview_rows || 0,
        match_write_policy: 'future_small_batch_only_after_backup_and_authorization',
        odds_write_policy: 'blocked_preview_only_in_phase_4_64c',
        deterministic_match_id_strategy: 'future_required_not_finalized_in_phase_4_64c',
        duplicate_detection_policy: 'future_select_only_precheck_required_not_executed_here',
        rollback_policy: 'future_pg_restore_runbook_required_not_executed_here',
    };
}

function buildSuccessPayload(args, dryRunPayload) {
    const rowClassification = dryRunPayload.row_classification || {};
    const preflightPlan = buildPreflightPlan(dryRunPayload);
    return {
        phase: PREFLIGHT_PHASE,
        mode: 'football-data-db-write-preflight',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        dry_run_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        approval_status: dryRunPayload.approval_status,
        source_name: dryRunPayload.source_name,
        parser_version: dryRunPayload.parser_version,
        dry_run_version: dryRunPayload.dry_run_version,
        total_rows: dryRunPayload.total_rows,
        candidate_rows: dryRunPayload.candidate_rows.length,
        trainable_label_rows: rowClassification.trainable_label_rows || 0,
        odds_preview_rows: rowClassification.odds_preview_rows || 0,
        skipped_rows: rowClassification.skipped_rows || 0,
        row_classification: rowClassification,
        candidate_preview: dryRunPayload.candidate_preview,
        db_write_allowed_reason:
            'Phase 4.64C only previews future DB write requirements; approval_status=dry_run_only is not DB write approval.',
        commit_gate: 'blocked',
        preflight_plan: preflightPlan,
        required_before_db_write: buildRequiredBeforeDbWrite(),
        future_pg_dump_runbook: buildFuturePgDumpRunbook(),
        future_validation_checklist: buildFutureValidationChecklist(),
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        dry_run_non_execution_confirmations: dryRunPayload.non_execution_confirmations,
        warnings: dryRunPayload.warnings || [],
        errors: [],
    };
}

function runPreflight(args, dependencies = {}) {
    if (!args.sourceManifest || !args.localCsv) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            errors: ['ERROR: provide --source-manifest=<path> and --local-csv=<path>'],
        });
    }

    const dryRun = dependencies.runDryRun || runDryRun;
    const dryRunPayload = dryRun(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
        },
        dependencies.dryRunDependencies || {}
    );

    if (!dryRunPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'dry-run-failed',
            source_manifest_found: dryRunPayload.source_manifest_found,
            local_csv_found: dryRunPayload.local_csv_found,
            sha256_match: dryRunPayload.sha256_match,
            row_count_match: dryRunPayload.row_count_match,
            dry_run_passed: false,
            dry_run_failure_mode: dryRunPayload.mode,
            errors: dryRunPayload.errors || ['football-data CSV dry-run failed'],
            warnings: dryRunPayload.warnings || [],
        });
    }

    return buildSuccessPayload(args, dryRunPayload);
}

function appendOptionalTextFields(lines, payload) {
    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
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

function payloadToText(payload) {
    const lines = [
        `phase=${payload.phase}`,
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `dry_run_passed=${payload.dry_run_passed}`,
        `sha256_match=${payload.sha256_match}`,
        `row_count_match=${payload.row_count_match}`,
        `candidate_rows=${payload.candidate_rows || 0}`,
        `trainable_label_rows=${payload.trainable_label_rows || 0}`,
        `odds_preview_rows=${payload.odds_preview_rows || 0}`,
        `db_write_allowed=${payload.db_write_allowed}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    appendOptionalTextFields(lines, payload);
    appendListSection(lines, 'required_before_db_write', payload.required_before_db_write);
    appendListSection(lines, 'future_pg_dump_runbook', payload.future_pg_dump_runbook);
    appendListSection(lines, 'future_validation_checklist', payload.future_validation_checklist);
    appendListSection(lines, 'non_execution_confirmations', payload.non_execution_confirmations);

    return lines.join('\n');
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function main(argv = process.argv.slice(2), io = {}) {
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

        const payload = runPreflight(args);
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
                mode: 'argument-error',
                errors: [error.message],
            }
        );
        writePayload(payload, json, output);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    PREFLIGHT_PHASE,
    parseArgs,
    runPreflight,
    buildRequiredBeforeDbWrite,
    buildFuturePgDumpRunbook,
    buildFutureValidationChecklist,
    buildNonExecutionConfirmations,
    main,
};
