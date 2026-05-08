#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- This packet preview keeps the full non-write contract in one file for auditability. */

const fs = require('fs');
const path = require('path');

const { runPreflight } = require('./football_data_db_write_preflight');
const { runDuplicatePrecheck, assertSelectOnlySql } = require('./football_data_duplicate_precheck');
const { runInsertPolicyPrecheck } = require('./football_data_insert_policy_precheck');
const {
    PG_DUMP_COMMAND_PREVIEW,
    PG_RESTORE_COMMAND_PREVIEW,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    buildManifestCompatibleDryRun,
    buildPostWriteValidationChecklist,
    buildRollbackRestorePreview,
    runSmallWriteAuthPreview,
} = require('./football_data_small_write_auth_preview');
const { extractYamlBlock, parseYamlBlock, runValidation } = require('./football_data_small_write_runbook_validate');

const PACKET_ASSEMBLY_PHASE = 'PHASE4.69C_FOOTBALL_DATA_SMALL_WRITE_PACKET_ASSEMBLY';
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: football-data small write packet commit is not wired in Phase 4.69C.';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const CURRENT_DB_TABLES = [
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
];
const PACKET_SECTIONS = [
    'source_manifest_summary',
    'local_csv_summary',
    'csv_dry_run_summary',
    'db_write_preflight_summary',
    'duplicate_precheck_summary',
    'insert_policy_summary',
    'small_write_auth_preview_summary',
    'runbook_template_summary',
    'approval_form_summary',
    'proposed_match_ids',
    'insert_candidate_table',
    'blocked_candidate_table',
    'manual_review_table',
    'pg_dump_command_preview',
    'post_write_validation_checklist',
    'rollback_restore_preview',
    'final_human_approval_required',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_small_write_packet_assembly.js --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> [--json]',
        '  node scripts/ops/football_data_small_write_packet_assembly.js --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> --commit',
        '',
        'Safety:',
        '  Phase 4.69C assembles a stdout-only dry-run packet preview.',
        '  No packet file writes, no DB writes, no pg_dump, no pg_restore, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOptions = new Map([
        ['--source-manifest', 'sourceManifest'],
        ['--local-csv', 'localCsv'],
        ['--approval-form', 'approvalForm'],
        ['--runbook-template', 'runbookTemplate'],
    ]);
    const flagOptions = new Map([
        ['--commit', 'commit'],
        ['--json', 'json'],
        ['--help', 'help'],
        ['-h', 'help'],
    ]);
    const args = {
        sourceManifest: '',
        localCsv: '',
        approvalForm: '',
        runbookTemplate: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        const matchedValueOption = [...valueOptions.keys()].find(
            option => token === option || token.startsWith(`${option}=`)
        );
        if (matchedValueOption) {
            const key = valueOptions.get(matchedValueOption);
            const usesSeparateValue = token === matchedValueOption;
            args[key] = usesSeparateValue
                ? String(argv[index + 1] || '')
                : token.slice(`${matchedValueOption}=`.length);
            if (usesSeparateValue) {
                index += 1;
            }
            continue;
        }
        if (flagOptions.has(token)) {
            args[flagOptions.get(token)] = true;
            continue;
        }
        throw new Error(`Unknown argument: ${token}`);
    }

    return args;
}

function resolveLocalPath(rawPath, cwd = process.cwd()) {
    if (!rawPath) {
        return '';
    }
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) {
        return '';
    }
    return path.relative(cwd, absolutePath) || '.';
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'select_only_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_packet_file_write',
        'no_legacy_runtime',
        'no_pg_dump_execution',
        'no_pg_restore_execution',
        'no_training',
        'no_prediction_execution',
    ];
}

function buildFutureRealPacketRequirements() {
    return [
        'approval form must be copied from template into a real reviewed file',
        'approval_status must be changed only by human',
        'final_human_confirmation must be set only by human',
        'packet must list exact proposed_match_ids',
        'packet must exclude manual_review and invalid candidates',
        'pg_dump must be executed only in future authorized write phase',
        'backup file must be non-empty before write',
        'write must be small and auditable',
        'post-write validation must be recorded',
    ];
}

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        packet_write_allowed: false,
        db_write_allowed: false,
        small_write_authorized: false,
        would_write_packet_file: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        would_execute_legacy_runtime: false,
        would_spawn_child_process: false,
        would_train_model: false,
        would_execute_prediction: false,
        would_load_model_artifact: false,
        approval_form_is_template: true,
        approval_granted: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: PACKET_ASSEMBLY_PHASE,
        mode: fields.mode || 'football-data-small-write-packet-assembly',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        csv_dry_run_passed: false,
        db_write_preflight_passed: false,
        duplicate_precheck_passed: false,
        insert_policy_precheck_passed: false,
        small_write_auth_preview_passed: false,
        approval_form_validation_passed: false,
        approval_status: null,
        final_human_confirmation: null,
        commit_gate: 'blocked',
        packet_sections: PACKET_SECTIONS,
        pg_dump_command_preview: PG_DUMP_COMMAND_PREVIEW,
        pg_restore_command_preview: PG_RESTORE_COMMAND_PREVIEW,
        post_write_validation_checklist: buildPostWriteValidationChecklist(),
        rollback_restore_preview: buildRollbackRestorePreview(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        future_real_packet_requirements: buildFutureRealPacketRequirements(),
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
        select_only_db_reads: false,
        ...fields,
    };
}

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: BLOCKED_COMMIT_MESSAGE,
        errors: [BLOCKED_COMMIT_MESSAGE],
    });
}

function buildPathContext(args, cwd, existsSync) {
    const sourceManifestPath = resolveLocalPath(args.sourceManifest, cwd);
    const localCsvPath = resolveLocalPath(args.localCsv, cwd);
    const approvalFormPath = resolveLocalPath(args.approvalForm, cwd);
    const runbookTemplatePath = resolveLocalPath(args.runbookTemplate, cwd);
    return {
        sourceManifestPath,
        localCsvPath,
        approvalFormPath,
        runbookTemplatePath,
        sourceManifestFound: existsSync(sourceManifestPath),
        localCsvFound: existsSync(localCsvPath),
        approvalFormFound: existsSync(approvalFormPath),
        runbookTemplateFound: existsSync(runbookTemplatePath),
    };
}

function validateRequiredArgs(args) {
    return Boolean(args.sourceManifest && args.localCsv && args.approvalForm && args.runbookTemplate);
}

function buildMissingPathPayload(args, cwd, pathContext) {
    const baseFields = {
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,
    };

    if (!pathContext.sourceManifestFound) {
        return buildFailurePayload(args, {
            mode: 'manifest-error',
            ...baseFields,
            errors: [`source manifest not found: ${toRelativePath(pathContext.sourceManifestPath, cwd)}`],
        });
    }
    if (!pathContext.localCsvFound) {
        return buildFailurePayload(args, {
            mode: 'csv-error',
            ...baseFields,
            errors: [`local CSV not found: ${toRelativePath(pathContext.localCsvPath, cwd)}`],
        });
    }
    if (!pathContext.approvalFormFound) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            ...baseFields,
            errors: [`approval form not found: ${toRelativePath(pathContext.approvalFormPath, cwd)}`],
        });
    }
    if (!pathContext.runbookTemplateFound) {
        return buildFailurePayload(args, {
            mode: 'runbook-template-error',
            ...baseFields,
            errors: [`runbook template not found: ${toRelativePath(pathContext.runbookTemplatePath, cwd)}`],
        });
    }
    return null;
}

function readJsonSafely(readFileSync, filePath) {
    try {
        return JSON.parse(readFileSync(filePath, 'utf8'));
    } catch (error) {
        return {
            parse_error: error.message,
        };
    }
}

function parseApprovalTemplate(markdownText) {
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        return {};
    }
    try {
        return parseYamlBlock(yamlText);
    } catch (error) {
        return {
            parse_error: error.message,
        };
    }
}

function pickFields(source, mapping) {
    const picked = {};
    for (const [targetKey, sourceKey] of Object.entries(mapping)) {
        picked[targetKey] = source?.[sourceKey] ?? null;
    }
    return picked;
}

function summarizeSourceManifest(manifest, manifestPath, cwd) {
    return {
        path: toRelativePath(manifestPath, cwd),
        source_name: manifest.source_name || null,
        source_type: manifest.source_type || null,
        source_url: manifest.source_url || null,
        license_url: manifest.license_url || null,
        terms_url: manifest.terms_url || null,
        approval_status: manifest.approval_status || null,
        human_approval_note_present: Boolean(String(manifest.human_approval_note || '').trim()),
        local_csv_path: manifest.local_csv_path || null,
        sha256: manifest.sha256 || null,
        row_count: manifest.row_count ?? null,
        mapping_version: manifest.mapping_version || null,
        parser_version: manifest.parser_version || null,
    };
}

function summarizeLocalCsv(localCsvPath, dryRunPayload, cwd) {
    return {
        path: toRelativePath(localCsvPath, cwd),
        expected_sha256: dryRunPayload.expected_sha256 || null,
        actual_sha256: dryRunPayload.actual_sha256 || null,
        sha256_match: dryRunPayload.sha256_match,
        expected_row_count: dryRunPayload.expected_row_count ?? null,
        actual_row_count: dryRunPayload.actual_row_count ?? null,
        row_count_match: dryRunPayload.row_count_match,
        total_rows: dryRunPayload.total_rows ?? null,
        parsed_rows: dryRunPayload.parsed_rows ?? null,
        candidate_rows: (dryRunPayload.candidate_rows || []).length,
        trainable_label_rows: dryRunPayload.trainable_label_rows || 0,
        skipped_rows: dryRunPayload.skipped_rows || 0,
        odds_preview_rows: dryRunPayload.odds_preview_rows || 0,
    };
}

function summarizeRunbookTemplate(runbookTemplatePath, markdownText, cwd) {
    return {
        path: toRelativePath(runbookTemplatePath, cwd),
        template_only: true,
        preview_only: /PREVIEW ONLY/i.test(markdownText),
        do_not_run_marker_present: /DO NOT RUN/i.test(markdownText),
        headings: String(markdownText || '')
            .split(/\r?\n/)
            .filter(line => /^#{1,3} /.test(line))
            .map(line => line.replace(/^#+\s*/, '').trim()),
    };
}

function summarizeApprovalForm(approvalFormPath, parsedApproval, validationPayload, cwd) {
    return {
        path: toRelativePath(approvalFormPath, cwd),
        template_only: true,
        validation_passed: validationPayload.ok,
        approval_status: parsedApproval.approval_status || validationPayload.approval_status || null,
        final_human_confirmation: parsedApproval.final_human_confirmation ?? null,
        target_tables: parsedApproval.target_tables || validationPayload.target_tables || null,
        allow_odds_insert: parsedApproval.allow_odds_insert ?? null,
        allow_raw_insert: parsedApproval.allow_raw_insert ?? null,
        allow_l3_insert: parsedApproval.allow_l3_insert ?? null,
        allow_training: parsedApproval.allow_training ?? null,
        allow_prediction: parsedApproval.allow_prediction ?? null,
        require_pg_dump: parsedApproval.require_pg_dump ?? null,
    };
}

function summarizeCsvDryRun(dryRunPayload) {
    return {
        ...pickFields(dryRunPayload, {
            phase: 'dry_run_version',
            ok: 'ok',
            source_name: 'source_name',
            approval_status: 'approval_status',
            total_rows: 'total_rows',
            parsed_rows: 'parsed_rows',
        }),
        candidate_rows: (dryRunPayload.candidate_rows || []).length,
        row_classification: dryRunPayload.row_classification || null,
        warnings: dryRunPayload.warnings || [],
    };
}

function summarizePreflight(preflightPayload) {
    return {
        ...pickFields(preflightPayload, {
            phase: 'phase',
            ok: 'ok',
            commit_gate: 'commit_gate',
        }),
        target_tables_preview: preflightPayload.preflight_plan?.target_tables_preview || null,
        max_rows_preview: preflightPayload.preflight_plan?.max_rows_preview ?? null,
        match_write_policy: preflightPayload.preflight_plan?.match_write_policy || null,
        odds_write_policy: preflightPayload.preflight_plan?.odds_write_policy || null,
    };
}

function summarizeDuplicatePrecheck(duplicatePayload) {
    return {
        ...pickFields(duplicatePayload, {
            phase: 'phase',
            ok: 'ok',
            candidate_rows: 'candidate_rows',
            exact_existing_matches: 'exact_existing_matches',
            reversed_team_matches: 'reversed_team_matches',
            nearby_date_matches: 'nearby_date_matches',
            invalid_candidates: 'invalid_candidates',
            commit_gate: 'commit_gate',
        }),
        insert_risk_summary: duplicatePayload.insert_risk_summary || null,
    };
}

function summarizeInsertPolicy(insertPolicyPayload) {
    return {
        ...pickFields(insertPolicyPayload, {
            phase: 'phase',
            ok: 'ok',
            match_id_strategy: 'match_id_strategy',
            match_id_strategy_finalized: 'match_id_strategy_finalized',
            manifest_approval_status: 'manifest_approval_status',
            candidate_rows: 'candidate_rows',
            future_insert_candidates: 'future_insert_candidates',
            blocked_by_manifest_policy: 'blocked_by_manifest_policy',
            skip_existing_matches: 'skip_existing_matches',
            manual_review_required: 'manual_review_required',
            invalid_candidates: 'invalid_candidates',
            commit_gate: 'commit_gate',
        }),
    };
}

function summarizeAuthPreview(authPayload) {
    return {
        ...pickFields(authPayload, {
            phase: 'phase',
            ok: 'ok',
            current_db_counts: 'current_db_counts',
            current_db_schema_preview: 'current_db_schema_preview',
            max_rows_preview: 'max_rows_preview',
            target_tables_preview: 'target_tables_preview',
            small_write_authorized: 'small_write_authorized',
            db_write_allowed: 'db_write_allowed',
            commit_gate: 'commit_gate',
        }),
    };
}

function mapCandidatePreview(preview) {
    return {
        row_number: preview.row_number || null,
        proposed_match_id: preview.proposed_match_id || null,
        home_team: preview.home_team || null,
        away_team: preview.away_team || null,
        match_date: preview.match_date || null,
        insert_policy: preview.insert_policy || null,
        duplicate_risk: preview.duplicate_risk || null,
        policy_reason: preview.policy_reason || null,
        required_action: preview.review_reason || preview.skip_reason || preview.policy_reason || null,
    };
}

function buildCandidateTables(insertPolicyPayload) {
    const previews = insertPolicyPayload.candidate_previews || [];
    const insertCandidateTable = previews
        .filter(preview => preview.insert_policy === 'future_insert_candidate')
        .map(preview => ({
            ...mapCandidatePreview(preview),
            approved_to_insert: false,
        }));
    const manualReviewTable = previews
        .filter(preview => preview.insert_policy === 'manual_review_required')
        .map(mapCandidatePreview);
    const blockedCandidateTable = previews
        .filter(preview => preview.insert_policy !== 'future_insert_candidate')
        .filter(preview => preview.insert_policy !== 'manual_review_required')
        .map(mapCandidatePreview);

    return {
        proposed_match_ids: previews.map(preview => preview.proposed_match_id).filter(Boolean),
        insert_candidate_table: insertCandidateTable,
        blocked_candidate_table: blockedCandidateTable,
        manual_review_table: manualReviewTable,
    };
}

function mergeWarnings(...payloads) {
    return payloads.flatMap(payload => payload?.warnings || []);
}

function buildBaseDependencyArgs(args) {
    return {
        sourceManifest: args.sourceManifest,
        localCsv: args.localCsv,
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

function buildApprovalValidationDependencies(dependencies, pathContext, approvalMarkdown) {
    const cwd = dependencies.cwd || process.cwd();
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readFileSync = dependencies.readFileSync || fs.readFileSync;
    return {
        ...(dependencies.approvalValidationDependencies || {}),
        cwd,
        existsSync,
        readFileSync: filePath => {
            const resolved = resolveLocalPath(filePath, cwd);
            if (resolved === pathContext.approvalFormPath) {
                return approvalMarkdown;
            }
            return readFileSync(filePath, 'utf8');
        },
    };
}

function buildProgressState(pathContext, parsedApproval, fields = {}) {
    return {
        source_manifest_found: Boolean(pathContext.sourceManifestFound),
        local_csv_found: Boolean(pathContext.localCsvFound),
        approval_form_found: Boolean(pathContext.approvalFormFound),
        runbook_template_found: Boolean(pathContext.runbookTemplateFound),
        approval_status: parsedApproval.approval_status ?? null,
        final_human_confirmation: parsedApproval.final_human_confirmation ?? null,
        ...fields,
    };
}

function buildStageFailurePayload(args, progressState, mode, payload, fields = {}) {
    return buildFailurePayload(args, {
        mode,
        ...progressState,
        ...fields,
        errors: payload.errors || [`${mode} failed`],
        warnings: payload.warnings || [],
    });
}

function buildSuccessPacketPayload(args, context) {
    const candidateTables = buildCandidateTables(context.insertPolicyPayload);
    return {
        phase: PACKET_ASSEMBLY_PHASE,
        mode: 'football-data-small-write-packet-assembly',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        approval_form: args.approvalForm,
        runbook_template: args.runbookTemplate,
        ...buildProgressState(context.pathContext, context.parsedApproval, {
            csv_dry_run_passed: true,
            db_write_preflight_passed: true,
            duplicate_precheck_passed: true,
            insert_policy_precheck_passed: true,
            small_write_auth_preview_passed: true,
            approval_form_validation_passed: true,
        }),
        commit_gate: 'blocked',
        packet_sections: PACKET_SECTIONS,
        source_manifest_summary: summarizeSourceManifest(
            context.manifest,
            context.pathContext.sourceManifestPath,
            context.cwd
        ),
        local_csv_summary: summarizeLocalCsv(context.pathContext.localCsvPath, context.dryRunPayload, context.cwd),
        csv_dry_run_summary: summarizeCsvDryRun(context.dryRunPayload),
        db_write_preflight_summary: summarizePreflight(context.preflightPayload),
        duplicate_precheck_summary: summarizeDuplicatePrecheck(context.duplicatePayload),
        insert_policy_summary: summarizeInsertPolicy(context.insertPolicyPayload),
        small_write_auth_preview_summary: summarizeAuthPreview(context.authPayload),
        runbook_template_summary: summarizeRunbookTemplate(
            context.pathContext.runbookTemplatePath,
            context.runbookMarkdown,
            context.cwd
        ),
        approval_form_summary: summarizeApprovalForm(
            context.pathContext.approvalFormPath,
            context.parsedApproval,
            context.approvalValidationPayload,
            context.cwd
        ),
        ...candidateTables,
        pg_dump_command_preview: context.authPayload.pg_dump_command_preview || PG_DUMP_COMMAND_PREVIEW,
        pg_restore_command_preview: context.authPayload.pg_restore_command_preview || PG_RESTORE_COMMAND_PREVIEW,
        post_write_validation_checklist:
            context.authPayload.post_write_validation || buildPostWriteValidationChecklist(),
        rollback_restore_preview: context.authPayload.rollback_restore_preview || buildRollbackRestorePreview(),
        final_human_approval_required: {
            required: true,
            approval_granted: false,
            approval_status: context.parsedApproval.approval_status,
            final_human_confirmation: context.parsedApproval.final_human_confirmation,
        },
        future_real_packet_requirements: buildFutureRealPacketRequirements(),
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        current_db_counts: context.authPayload.current_db_counts || null,
        current_db_schema_preview: context.authPayload.current_db_schema_preview || null,
        warnings: mergeWarnings(
            context.dryRunPayload,
            context.preflightPayload,
            context.duplicatePayload,
            context.insertPolicyPayload,
            context.authPayload
        ),
        errors: [],
    };
}

function buildPacketContext(args, dependencies = {}) {
    const cwd = dependencies.cwd || process.cwd();
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readFileSync = dependencies.readFileSync || fs.readFileSync;

    if (!validateRequiredArgs(args)) {
        return {
            failurePayload: buildFailurePayload(args, { mode: 'argument-error', errors: [MISSING_ARGS_MESSAGE] }),
        };
    }

    const pathContext = buildPathContext(args, cwd, existsSync);
    const missingPathPayload = buildMissingPathPayload(args, cwd, pathContext);
    if (missingPathPayload) {
        return { failurePayload: missingPathPayload };
    }

    const approvalMarkdown = readFileSync(pathContext.approvalFormPath, 'utf8');
    const runbookMarkdown = readFileSync(pathContext.runbookTemplatePath, 'utf8');
    const parsedApproval = parseApprovalTemplate(approvalMarkdown);
    return {
        context: {
            cwd,
            readFileSync,
            pathContext,
            approvalMarkdown,
            runbookMarkdown,
            parsedApproval,
            baseProgress: buildProgressState(pathContext, parsedApproval),
            runArgs: buildBaseDependencyArgs(args),
        },
    };
}

function runApprovalValidationStage(args, context, dependencies) {
    const approvalValidationPayload = (dependencies.runApprovalValidation || runValidation)(
        { approvalForm: args.approvalForm },
        buildApprovalValidationDependencies(dependencies, context.pathContext, context.approvalMarkdown)
    );
    if (!approvalValidationPayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(
                args,
                context.baseProgress,
                'approval-form-validation-failed',
                approvalValidationPayload
            ),
        };
    }
    context.approvalValidationPayload = approvalValidationPayload;
    return {};
}

function runDryRunStage(args, context, dependencies) {
    context.manifest = readJsonSafely(context.readFileSync, context.pathContext.sourceManifestPath);
    const runArgs = buildBaseDependencyArgs(args);
    context.dryRunPreview = dependencies.runDryRun || buildManifestCompatibleDryRun(dependencies);
    const dryRunPayload = context.dryRunPreview(runArgs);
    const dryRunProgress = buildProgressState(context.pathContext, context.parsedApproval, {
        approval_form_validation_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
    });
    if (!dryRunPayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(args, dryRunProgress, 'csv-dry-run-failed', dryRunPayload),
        };
    }
    context.dryRunPayload = dryRunPayload;
    context.dryRunProgress = dryRunProgress;
    return {};
}

async function runPreflightStage(args, context, dependencies) {
    const preflightPayload = await Promise.resolve(
        (dependencies.runPreflight || runPreflight)(context.runArgs, {
            ...(dependencies.preflightDependencies || {}),
            runDryRun: context.dryRunPreview,
        })
    );
    const preflightProgress = { ...context.dryRunProgress, csv_dry_run_passed: true };
    if (!preflightPayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(
                args,
                preflightProgress,
                'db-write-preflight-failed',
                preflightPayload,
                { warnings: mergeWarnings(context.dryRunPayload, preflightPayload) }
            ),
        };
    }
    context.preflightPayload = preflightPayload;
    context.preflightProgress = preflightProgress;
    return {};
}

async function runDuplicateStage(args, context, dependencies) {
    const duplicatePayload = await (dependencies.runDuplicatePrecheck || runDuplicatePrecheck)(
        context.runArgs,
        buildDbReadDependencies(dependencies, context.dryRunPreview, 'duplicateDependencies')
    );
    const duplicateProgress = { ...context.preflightProgress, db_write_preflight_passed: true };
    if (!duplicatePayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(
                args,
                duplicateProgress,
                'duplicate-precheck-failed',
                duplicatePayload,
                { warnings: mergeWarnings(context.dryRunPayload, context.preflightPayload, duplicatePayload) }
            ),
        };
    }
    context.duplicatePayload = duplicatePayload;
    context.duplicateProgress = duplicateProgress;
    return {};
}

async function runInsertPolicyStage(args, context, dependencies) {
    const insertPolicyPayload = await (dependencies.runInsertPolicyPrecheck || runInsertPolicyPrecheck)(
        context.runArgs,
        buildDbReadDependencies(dependencies, context.dryRunPreview, 'insertPolicyDependencies')
    );
    const insertProgress = { ...context.duplicateProgress, duplicate_precheck_passed: true };
    if (!insertPolicyPayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(
                args,
                insertProgress,
                'insert-policy-precheck-failed',
                insertPolicyPayload,
                {
                    warnings: mergeWarnings(
                        context.dryRunPayload,
                        context.preflightPayload,
                        context.duplicatePayload,
                        insertPolicyPayload
                    ),
                }
            ),
        };
    }
    context.insertPolicyPayload = insertPolicyPayload;
    context.insertProgress = insertProgress;
    return {};
}

async function runAuthStage(args, context, dependencies) {
    const authPayload = await (dependencies.runSmallWriteAuthPreview || runSmallWriteAuthPreview)(context.runArgs, {
        ...(dependencies.authPreviewDependencies || {}),
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
        runDryRun: () => context.dryRunPayload,
        runPreflight: () => context.preflightPayload,
        runDuplicatePrecheck: async () => context.duplicatePayload,
        runInsertPolicyPrecheck: async () => context.insertPolicyPayload,
        inspectCurrentDbState: dependencies.inspectCurrentDbState,
    });
    if (!authPayload.ok) {
        return {
            failurePayload: buildStageFailurePayload(
                args,
                { ...context.insertProgress, insert_policy_precheck_passed: true },
                'small-write-auth-preview-failed',
                authPayload,
                {
                    warnings: mergeWarnings(
                        context.dryRunPayload,
                        context.preflightPayload,
                        context.duplicatePayload,
                        context.insertPolicyPayload,
                        authPayload
                    ),
                }
            ),
        };
    }
    context.authPayload = authPayload;
    return {};
}

async function runPacketStages(args, context, dependencies) {
    const stageRunners = [
        runApprovalValidationStage,
        runDryRunStage,
        runPreflightStage,
        runDuplicateStage,
        runInsertPolicyStage,
        runAuthStage,
    ];

    for (const runStage of stageRunners) {
        const stageResult = await runStage(args, context, dependencies);
        if (stageResult.failurePayload) {
            return stageResult;
        }
    }
    return {};
}

async function runPacketAssembly(args, dependencies = {}) {
    const prepared = buildPacketContext(args, dependencies);
    if (prepared.failurePayload) {
        return prepared.failurePayload;
    }

    const context = prepared.context;
    const stageResult = await runPacketStages(args, context, dependencies);
    if (stageResult.failurePayload) {
        return stageResult.failurePayload;
    }
    return buildSuccessPacketPayload(args, context);
}

function appendListSection(lines, title, values) {
    lines.push(`${title}:`);
    for (const value of values || []) {
        lines.push(`- ${value}`);
    }
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

function appendCurrentDbCounts(lines, counts) {
    if (!counts) {
        return;
    }
    lines.push('current_db_counts:');
    for (const tableName of CURRENT_DB_TABLES) {
        lines.push(`- ${tableName}=${counts[tableName] ?? 'unknown'}`);
    }
}

function payloadToText(payload) {
    const lines = [
        `phase=${payload.phase}`,
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `approval_form_found=${payload.approval_form_found}`,
        `runbook_template_found=${payload.runbook_template_found}`,
        `csv_dry_run_passed=${payload.csv_dry_run_passed}`,
        `db_write_preflight_passed=${payload.db_write_preflight_passed}`,
        `duplicate_precheck_passed=${payload.duplicate_precheck_passed}`,
        `insert_policy_precheck_passed=${payload.insert_policy_precheck_passed}`,
        `small_write_auth_preview_passed=${payload.small_write_auth_preview_passed}`,
        `approval_form_validation_passed=${payload.approval_form_validation_passed}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        `packet_write_allowed=${payload.packet_write_allowed}`,
        `db_write_allowed=${payload.db_write_allowed}`,
        `small_write_authorized=${payload.small_write_authorized}`,
        `would_write_packet_file=${payload.would_write_packet_file}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_execute_pg_restore=${payload.would_execute_pg_restore}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `commit_gate=${payload.commit_gate}`,
        `approval_status=${payload.approval_status}`,
        `final_human_confirmation=${payload.final_human_confirmation}`,
        `approval_form_is_template=${payload.approval_form_is_template}`,
        `approval_granted=${payload.approval_granted}`,
        `pg_dump_command_preview=${JSON.stringify(payload.pg_dump_command_preview)}`,
        `pg_restore_command_preview=${JSON.stringify(payload.pg_restore_command_preview)}`,
    ];

    appendOptionalTextFields(lines, payload);
    appendCurrentDbCounts(lines, payload.current_db_counts);
    appendListSection(lines, 'packet_sections', payload.packet_sections);
    appendListSection(lines, 'non_execution_confirmations', payload.non_execution_confirmations);
    appendListSection(lines, 'future_real_packet_requirements', payload.future_real_packet_requirements);

    if (payload.source_manifest_summary) {
        lines.push(`source_manifest_summary=${JSON.stringify(payload.source_manifest_summary)}`);
    }
    if (payload.local_csv_summary) {
        lines.push(`local_csv_summary=${JSON.stringify(payload.local_csv_summary)}`);
    }
    if (payload.csv_dry_run_summary) {
        lines.push(`csv_dry_run_summary=${JSON.stringify(payload.csv_dry_run_summary)}`);
    }
    if (payload.db_write_preflight_summary) {
        lines.push(`db_write_preflight_summary=${JSON.stringify(payload.db_write_preflight_summary)}`);
    }
    if (payload.duplicate_precheck_summary) {
        lines.push(`duplicate_precheck_summary=${JSON.stringify(payload.duplicate_precheck_summary)}`);
    }
    if (payload.insert_policy_summary) {
        lines.push(`insert_policy_summary=${JSON.stringify(payload.insert_policy_summary)}`);
    }
    if (payload.small_write_auth_preview_summary) {
        lines.push(`small_write_auth_preview_summary=${JSON.stringify(payload.small_write_auth_preview_summary)}`);
    }
    if (payload.runbook_template_summary) {
        lines.push(`runbook_template_summary=${JSON.stringify(payload.runbook_template_summary)}`);
    }
    if (payload.approval_form_summary) {
        lines.push(`approval_form_summary=${JSON.stringify(payload.approval_form_summary)}`);
    }
    if (payload.proposed_match_ids) {
        lines.push(`proposed_match_ids=${JSON.stringify(payload.proposed_match_ids)}`);
    }
    if (payload.insert_candidate_table) {
        lines.push(`insert_candidate_table=${JSON.stringify(payload.insert_candidate_table)}`);
    }
    if (payload.blocked_candidate_table) {
        lines.push(`blocked_candidate_table=${JSON.stringify(payload.blocked_candidate_table)}`);
    }
    if (payload.manual_review_table) {
        lines.push(`manual_review_table=${JSON.stringify(payload.manual_review_table)}`);
    }
    if (payload.final_human_approval_required) {
        lines.push(`final_human_approval_required=${JSON.stringify(payload.final_human_approval_required)}`);
    }

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

        const payload = await runPacketAssembly(args, dependencies);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const payload = buildFailurePayload(
            {
                sourceManifest: '',
                localCsv: '',
                approvalForm: '',
                runbookTemplate: '',
            },
            {
                mode: 'runtime-error',
                errors: [error.message],
            }
        );
        writePayload(payload, argv.includes('--json'), output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => {
        process.exitCode = status;
    });
}

module.exports = {
    PACKET_ASSEMBLY_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    MISSING_ARGS_MESSAGE,
    PACKET_SECTIONS,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    runPacketAssembly,
    buildNonExecutionConfirmations,
    buildFutureRealPacketRequirements,
    buildCandidateTables,
    assertSelectOnlySql,
    payloadToText,
    main,
};
