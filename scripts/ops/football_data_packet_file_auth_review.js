#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.72C keeps the dry-run authorization review contract in one file for auditability. */

const fs = require('fs');
const path = require('path');

const { runValidation, extractYamlBlock, parseYamlBlock } = require('./football_data_packet_file_auth_validate');
const { runPacketFilePreflight } = require('./football_data_packet_file_preflight');
const { runPacketAssembly } = require('./football_data_small_write_packet_assembly');
const {
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    buildDbConfig,
    assertSelectOnlySql,
} = require('./football_data_duplicate_precheck');

const PACKET_FILE_AUTH_REVIEW_PHASE = 'PHASE4.72C_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --auth-form=<path>, --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: football-data packet file authorization review commit is not wired in Phase 4.72C.';
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
const PERMISSION_SEPARATION = [
    'packet file creation does not authorize DB write',
    'packet file creation does not authorize pg_dump',
    'packet file creation does not authorize pg_restore',
    'packet file creation does not authorize training',
    'packet file creation does not authorize prediction',
];
const HUMAN_ONLY_FIELDS = [
    'authorization_status',
    'final_packet_creation_confirmation',
    'operator',
    'reviewer',
    'human_approval_note',
    'approved_candidate_match_ids',
    'excluded_candidate_match_ids',
    'manual_review_candidate_match_ids',
    'packet_creation_reason',
];
const NON_EXECUTION_CONFIRMATIONS = [
    'no_external_network',
    'select_only_db_reads',
    'no_db_writes',
    'no_file_writes',
    'no_packet_file_write',
    'no_packet_directory_create',
    'no_legacy_runtime',
    'no_pg_dump_execution',
    'no_pg_restore_execution',
    'no_training',
    'no_prediction_execution',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_auth_review.js --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> [--json]',
        '  node scripts/ops/football_data_packet_file_auth_review.js --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> --commit',
        '',
        'Safety:',
        '  Phase 4.72C runs a dry-run authorization review only.',
        '  No packet file writes, no packet directory creation, no DB writes, no pg_dump, no pg_restore, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOptions = new Map([
        ['--auth-form', 'authForm'],
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
        authForm: '',
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

function normalizePathLike(value) {
    return String(value || '')
        .replace(/\\/g, '/')
        .replace(/\/+$/g, '')
        .trim();
}

function compareReviewedPath(authValue, reviewedAbsolutePath, cwd = process.cwd()) {
    if (!authValue) {
        return false;
    }
    const normalizedAuth = normalizePathLike(authValue);
    const reviewedRelative = normalizePathLike(toRelativePath(reviewedAbsolutePath, cwd));
    const reviewedAbsolute = normalizePathLike(path.resolve(reviewedAbsolutePath));
    const authAbsolute = normalizePathLike(path.resolve(cwd, String(authValue)));
    return (
        normalizedAuth === reviewedRelative || normalizedAuth === reviewedAbsolute || authAbsolute === reviewedAbsolute
    );
}

function trimToEmpty(value) {
    return String(value || '').trim();
}

function toStringArray(value) {
    return Array.isArray(value) ? value.map(item => String(item || '').trim()).filter(Boolean) : [];
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function withDbClient(dependencies, callback) {
    if (dependencies.dbClient) {
        return callback(dependencies.dbClient);
    }

    const pool = dependencies.pool || (dependencies.createPool || createPool)();
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

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        authorization_review_completed: true,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        approval_granted: false,
        would_create_packet_directory: false,
        would_write_packet_file: false,
        would_write_packet_manifest: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        would_spawn_child_process: false,
        would_train_model: false,
        would_execute_prediction: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: PACKET_FILE_AUTH_REVIEW_PHASE,
        mode: fields.mode || 'football-data-packet-file-auth-review',
        ok: false,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        auth_form_found: false,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        auth_form_validation_passed: false,
        packet_file_preflight_passed: false,
        packet_preview_passed: false,
        select_only_db_reads: false,
        authorization_review_completed: false,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        authorization_status: null,
        final_packet_creation_confirmation: null,
        approval_granted: false,
        commit_gate: 'blocked',
        current_db_counts: null,
        missing_authorization_requirements: [],
        permission_separation: PERMISSION_SEPARATION,
        human_only_fields: HUMAN_ONLY_FIELDS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        errors: [],
        warnings: [],
        would_create_packet_directory: false,
        would_write_packet_file: false,
        would_write_packet_manifest: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        would_spawn_child_process: false,
        would_train_model: false,
        would_execute_prediction: false,
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

function validateRequiredArgs(args) {
    return Boolean(args.authForm && args.sourceManifest && args.localCsv && args.approvalForm && args.runbookTemplate);
}

function buildPathContext(args, cwd, existsSync) {
    const authFormPath = resolveLocalPath(args.authForm, cwd);
    const sourceManifestPath = resolveLocalPath(args.sourceManifest, cwd);
    const localCsvPath = resolveLocalPath(args.localCsv, cwd);
    const approvalFormPath = resolveLocalPath(args.approvalForm, cwd);
    const runbookTemplatePath = resolveLocalPath(args.runbookTemplate, cwd);
    return {
        authFormPath,
        sourceManifestPath,
        localCsvPath,
        approvalFormPath,
        runbookTemplatePath,
        authFormFound: existsSync(authFormPath),
        sourceManifestFound: existsSync(sourceManifestPath),
        localCsvFound: existsSync(localCsvPath),
        approvalFormFound: existsSync(approvalFormPath),
        runbookTemplateFound: existsSync(runbookTemplatePath),
    };
}

function buildMissingPathPayload(args, pathContext, cwd) {
    const baseFields = {
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,
    };

    if (!pathContext.authFormFound) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            ...baseFields,
            errors: [`auth form not found: ${toRelativePath(pathContext.authFormPath, cwd)}`],
        });
    }
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

function readReviewedInputs(pathContext, readFileSync) {
    return {
        authFormMarkdown: readFileSync(pathContext.authFormPath, 'utf8'),
        sourceManifestText: readFileSync(pathContext.sourceManifestPath, 'utf8'),
        localCsvText: readFileSync(pathContext.localCsvPath, 'utf8'),
        approvalFormMarkdown: readFileSync(pathContext.approvalFormPath, 'utf8'),
        runbookTemplateMarkdown: readFileSync(pathContext.runbookTemplatePath, 'utf8'),
    };
}

function parseAuthFormMarkdown(markdownText) {
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        throw new Error('YAML fenced block not found in packet file authorization form');
    }
    return parseYamlBlock(yamlText);
}

function mapManualReviewIds(packetPreviewPayload) {
    return (packetPreviewPayload.manual_review_table || []).map(row => row.proposed_match_id).filter(Boolean);
}

function mapInsertCandidateIds(packetPreviewPayload) {
    const directIds = (packetPreviewPayload.insert_candidate_table || [])
        .map(row => row.proposed_match_id)
        .filter(Boolean);
    if (directIds.length > 0) {
        return directIds;
    }
    return (packetPreviewPayload.proposed_match_ids || []).filter(Boolean);
}

function includesAllValues(actualValues, expectedValues) {
    const actualSet = new Set(toStringArray(actualValues));
    return toStringArray(expectedValues).every(value => actualSet.has(value));
}

function collectRequiredLiteralRequirementMessages(authFormData) {
    const missing = [];
    if (authFormData.authorization_status !== 'authorized_for_packet_file_creation') {
        missing.push('authorization_status must be authorized_for_packet_file_creation');
    }
    if (authFormData.final_packet_creation_confirmation !== true) {
        missing.push('final_packet_creation_confirmation must be true');
    }
    if (!trimToEmpty(authFormData.operator)) {
        missing.push('operator must be filled');
    }
    if (!trimToEmpty(authFormData.reviewer)) {
        missing.push('reviewer must be filled');
    }
    if (!trimToEmpty(authFormData.packet_directory)) {
        missing.push('packet_directory must be explicit');
    }
    if (!trimToEmpty(authFormData.packet_file)) {
        missing.push('packet_file must be explicit');
    }
    if (!trimToEmpty(authFormData.packet_manifest_file)) {
        missing.push('packet_manifest_file must be explicit');
    }
    return missing;
}

function collectReviewedPathRequirementMessages(authFormData, context) {
    const missing = [];
    if (!compareReviewedPath(authFormData.source_manifest, context.pathContext.sourceManifestPath, context.cwd)) {
        missing.push('source_manifest must match reviewed source');
    }
    if (!compareReviewedPath(authFormData.local_csv, context.pathContext.localCsvPath, context.cwd)) {
        missing.push('local_csv must match reviewed CSV');
    }
    return missing;
}

function collectCandidateRequirementMessages(authFormData, context) {
    const missing = [];
    const approvedCandidateIds = toStringArray(authFormData.approved_candidate_match_ids);
    const reviewedInsertCandidateIds = mapInsertCandidateIds(context.packetPreviewPayload);

    if (
        reviewedInsertCandidateIds.length > 0 &&
        (!includesAllValues(approvedCandidateIds, reviewedInsertCandidateIds) || approvedCandidateIds.length === 0)
    ) {
        missing.push('approved_candidate_match_ids must be reviewed');
    }

    return missing;
}

function collectManualReviewRequirementMessages(authFormData, context) {
    const missing = [];
    const excludedCandidateIds = new Set(toStringArray(authFormData.excluded_candidate_match_ids));
    const manualReviewCandidateIds = new Set(toStringArray(authFormData.manual_review_candidate_match_ids));
    const reviewedManualReviewIds = mapManualReviewIds(context.packetPreviewPayload);

    if (
        manualReviewCandidateIds.size === 0 ||
        reviewedManualReviewIds.some(
            matchId => !manualReviewCandidateIds.has(matchId) && !excludedCandidateIds.has(matchId)
        )
    ) {
        missing.push('manual_review_candidate_match_ids must be excluded or resolved');
    }

    return missing;
}

function collectHumanApprovalRequirementMessages(authFormData) {
    return trimToEmpty(authFormData.human_approval_note) ? [] : ['human_approval_note must be present'];
}

function buildMissingAuthorizationRequirements(authFormData, context) {
    const missing = [
        ...collectRequiredLiteralRequirementMessages(authFormData),
        ...collectReviewedPathRequirementMessages(authFormData, context),
        ...collectCandidateRequirementMessages(authFormData, context),
        ...collectManualReviewRequirementMessages(authFormData, context),
        ...collectHumanApprovalRequirementMessages(authFormData),
    ];
    return [...new Set(missing)];
}

function createAuthorizationReviewRuntime(args, dependencies = {}) {
    const cwd = dependencies.cwd || process.cwd();
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readFileSync = dependencies.readFileSync || fs.readFileSync;

    if (!validateRequiredArgs(args)) {
        return {
            failurePayload: buildFailurePayload(args, {
                mode: 'argument-error',
                errors: [MISSING_ARGS_MESSAGE],
            }),
        };
    }

    const pathContext = buildPathContext(args, cwd, existsSync);
    const missingPathPayload = buildMissingPathPayload(args, pathContext, cwd);
    if (missingPathPayload) {
        return {
            failurePayload: missingPathPayload,
        };
    }

    return {
        cwd,
        existsSync,
        readFileSync,
        pathContext,
        reviewedInputs: readReviewedInputs(pathContext, readFileSync),
        authFormData: null,
        packetPreviewPayload: null,
        packetFilePreflightPayload: null,
        dbReview: {},
    };
}

function buildAuthValidationStageDependencies(runtime, dependencies = {}) {
    return {
        cwd: dependencies.cwd || runtime.cwd,
        existsSync: dependencies.existsSync || runtime.existsSync || fs.existsSync,
        readFileSync: dependencies.readFileSync || runtime.readFileSync || fs.readFileSync,
        runAuthValidation: dependencies.runAuthValidation,
        ...(dependencies.authValidationDependencies || {}),
    };
}

function buildPacketPreviewStageDependencies(runtime, dependencies = {}) {
    return {
        cwd: dependencies.cwd || runtime.cwd,
        existsSync: dependencies.existsSync || runtime.existsSync || fs.existsSync,
        readFileSync: dependencies.readFileSync || runtime.readFileSync || fs.readFileSync,
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
        runPacketAssembly: dependencies.runPacketAssembly,
        ...(dependencies.packetPreviewDependencies || {}),
    };
}

function buildPacketFilePreflightStageDependencies(runtime, dependencies = {}) {
    return {
        cwd: dependencies.cwd || runtime.cwd,
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
        runPacketFilePreflight: dependencies.runPacketFilePreflight,
        ...(dependencies.packetFilePreflightDependencies || {}),
    };
}

async function runAuthorizationReviewStages(args, runtime, dependencies = {}) {
    const authValidationPayload = await (dependencies.runAuthValidationStage || runAuthValidationStage)(
        args,
        runtime,
        buildAuthValidationStageDependencies(runtime, dependencies)
    );
    if (!authValidationPayload.ok) {
        return buildStageFailurePayload(args, runtime, 'auth-form-validation-failed', authValidationPayload, {
            auth_form_validation_passed: false,
            errors: authValidationPayload.errors || ['football-data packet file auth validation failed'],
        });
    }

    runtime.authFormData = parseAuthFormMarkdown(runtime.reviewedInputs.authFormMarkdown);

    const packetPreviewPayload = await (dependencies.runPacketPreviewStage || runPacketPreviewStage)(
        args,
        runtime,
        buildPacketPreviewStageDependencies(runtime, dependencies)
    );
    runtime.packetPreviewPayload = packetPreviewPayload;
    if (!packetPreviewPayload.ok) {
        return buildStageFailurePayload(args, runtime, 'packet-preview-failed', packetPreviewPayload, {
            auth_form_validation_passed: true,
            packet_preview_passed: false,
            errors: packetPreviewPayload.errors || ['football-data packet preview failed'],
        });
    }

    const packetFilePreflightPayload = await (dependencies.runPacketFilePreflightStage || runPacketFilePreflightStage)(
        args,
        runtime,
        buildPacketFilePreflightStageDependencies(runtime, dependencies)
    );
    runtime.packetFilePreflightPayload = packetFilePreflightPayload;
    if (!packetFilePreflightPayload.ok) {
        return buildStageFailurePayload(args, runtime, 'packet-file-preflight-failed', packetFilePreflightPayload, {
            auth_form_validation_passed: true,
            packet_preview_passed: true,
            packet_file_preflight_passed: false,
            errors: packetFilePreflightPayload.errors || ['football-data packet file preflight failed'],
        });
    }

    return null;
}

async function reviewCurrentDbCounts(dependencies = {}) {
    return withDbClient(dependencies, async client => {
        await querySelectOnly(client, READ_ONLY_BEGIN_SQL);
        try {
            const countsResult = await querySelectOnly(client, CURRENT_DB_COUNTS_SQL);
            return {
                current_db_counts: mapCurrentDbCounts(countsResult.rows || []),
            };
        } finally {
            await querySelectOnly(client, READ_ONLY_ROLLBACK_SQL);
        }
    });
}

function buildSuccessPayload(args, context) {
    const missingAuthorizationRequirements = buildMissingAuthorizationRequirements(context.authFormData, context);

    return {
        phase: PACKET_FILE_AUTH_REVIEW_PHASE,
        mode: 'football-data-packet-file-auth-review',
        ok: true,
        auth_form: args.authForm,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        approval_form: args.approvalForm,
        runbook_template: args.runbookTemplate,
        auth_form_found: true,
        source_manifest_found: true,
        local_csv_found: true,
        approval_form_found: true,
        runbook_template_found: true,
        auth_form_validation_passed: true,
        packet_file_preflight_passed: true,
        packet_preview_passed: true,
        authorization_status: context.authFormData.authorization_status ?? null,
        final_packet_creation_confirmation: context.authFormData.final_packet_creation_confirmation ?? null,
        commit_gate: 'blocked',
        current_db_counts:
            context.dbReview.current_db_counts ||
            context.packetPreviewPayload.current_db_counts ||
            context.packetFilePreflightPayload.current_db_counts ||
            null,
        missing_authorization_requirements: missingAuthorizationRequirements,
        permission_separation: PERMISSION_SEPARATION,
        human_only_fields: HUMAN_ONLY_FIELDS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        auth_form_reviewed_path: toRelativePath(context.pathContext.authFormPath, context.cwd),
        reviewed_source_manifest_path: toRelativePath(context.pathContext.sourceManifestPath, context.cwd),
        reviewed_local_csv_path: toRelativePath(context.pathContext.localCsvPath, context.cwd),
        reviewed_approval_form_path: toRelativePath(context.pathContext.approvalFormPath, context.cwd),
        reviewed_runbook_template_path: toRelativePath(context.pathContext.runbookTemplatePath, context.cwd),
        packet_preview_phase: context.packetPreviewPayload.phase || null,
        packet_file_preflight_phase: context.packetFilePreflightPayload.phase || null,
        approved_output_root: context.authFormData.approved_output_root || null,
        approved_packet_sections: context.authFormData.approved_packet_sections || [],
        reviewed_proposed_match_ids: context.packetPreviewPayload.proposed_match_ids || [],
        reviewed_manual_review_match_ids: mapManualReviewIds(context.packetPreviewPayload),
        warnings: [
            ...(context.packetPreviewPayload.warnings || []),
            ...(context.packetFilePreflightPayload.warnings || []),
        ],
        errors: [],
        ...buildSafetyFlags(),
    };
}

function buildStageFailurePayload(args, context, mode, payload, fields = {}) {
    return buildFailurePayload(args, {
        mode,
        auth_form_found: Boolean(context.pathContext?.authFormFound),
        source_manifest_found: Boolean(context.pathContext?.sourceManifestFound),
        local_csv_found: Boolean(context.pathContext?.localCsvFound),
        approval_form_found: Boolean(context.pathContext?.approvalFormFound),
        runbook_template_found: Boolean(context.pathContext?.runbookTemplateFound),
        auth_form_validation_passed: fields.auth_form_validation_passed || false,
        packet_preview_passed: fields.packet_preview_passed || false,
        packet_file_preflight_passed: fields.packet_file_preflight_passed || false,
        authorization_status: context.authFormData?.authorization_status ?? null,
        final_packet_creation_confirmation: context.authFormData?.final_packet_creation_confirmation ?? null,
        errors: payload.errors || [`${mode} failed`],
        warnings: payload.warnings || [],
        ...fields,
    });
}

async function runAuthorizationReview(args, dependencies = {}) {
    const runtime = createAuthorizationReviewRuntime(args, dependencies);
    if (runtime.failurePayload) {
        return runtime.failurePayload;
    }

    const stageFailurePayload = await runAuthorizationReviewStages(args, runtime, dependencies);
    if (stageFailurePayload) {
        return stageFailurePayload;
    }

    runtime.dbReview = await reviewCurrentDbCounts({
        dbClient: dependencies.dbClient,
        pool: dependencies.pool,
        createPool: dependencies.createPool,
    });

    return buildSuccessPayload(args, runtime);
}

async function runAuthValidationStage(args, context, dependencies) {
    return (dependencies.runAuthValidation || runValidation)(
        { authForm: args.authForm },
        {
            cwd: dependencies.cwd || context.cwd,
            existsSync: dependencies.existsSync || fs.existsSync,
            readFileSync: dependencies.readFileSync || fs.readFileSync,
            ...(dependencies.authValidationDependencies || {}),
        }
    );
}

async function runPacketPreviewStage(args, context, dependencies) {
    return (dependencies.runPacketAssembly || runPacketAssembly)(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
        },
        {
            cwd: dependencies.cwd || context.cwd,
            existsSync: dependencies.existsSync || fs.existsSync,
            readFileSync: dependencies.readFileSync || fs.readFileSync,
            dbClient: dependencies.dbClient,
            pool: dependencies.pool,
            ...(dependencies.packetPreviewDependencies || {}),
        }
    );
}

async function runPacketFilePreflightStage(args, context, dependencies) {
    return (dependencies.runPacketFilePreflight || runPacketFilePreflight)(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
        },
        {
            cwd: dependencies.cwd || context.cwd,
            runPacketAssembly: async () => context.packetPreviewPayload,
            dbClient: dependencies.dbClient,
            pool: dependencies.pool,
            ...(dependencies.packetFilePreflightDependencies || {}),
        }
    );
}

function appendListSection(lines, title, values) {
    lines.push(`${title}:`);
    for (const value of values || []) {
        lines.push(`- ${value}`);
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
        `auth_form_found=${payload.auth_form_found}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `approval_form_found=${payload.approval_form_found}`,
        `runbook_template_found=${payload.runbook_template_found}`,
        `auth_form_validation_passed=${payload.auth_form_validation_passed}`,
        `packet_file_preflight_passed=${payload.packet_file_preflight_passed}`,
        `packet_preview_passed=${payload.packet_preview_passed}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        '',
        `authorization_review_completed=${payload.authorization_review_completed}`,
        `packet_file_creation_ready=${payload.packet_file_creation_ready}`,
        `packet_file_creation_authorized=${payload.packet_file_creation_authorized}`,
        `authorization_status=${payload.authorization_status}`,
        `final_packet_creation_confirmation=${payload.final_packet_creation_confirmation}`,
        `approval_granted=${payload.approval_granted}`,
        '',
        `would_create_packet_directory=${payload.would_create_packet_directory}`,
        `would_write_packet_file=${payload.would_write_packet_file}`,
        `would_write_packet_manifest=${payload.would_write_packet_manifest}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_execute_pg_restore=${payload.would_execute_pg_restore}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
    }

    appendCurrentDbCounts(lines, payload.current_db_counts);
    appendListSection(lines, 'missing_authorization_requirements', payload.missing_authorization_requirements);
    appendListSection(lines, 'permission_separation', payload.permission_separation);
    appendListSection(lines, 'human_only_fields', payload.human_only_fields);
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

        const payload = await runAuthorizationReview(args, dependencies);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const payload = buildFailurePayload(
            {
                authForm: '',
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
    PACKET_FILE_AUTH_REVIEW_PHASE,
    MISSING_ARGS_MESSAGE,
    BLOCKED_COMMIT_MESSAGE,
    CURRENT_DB_TABLES,
    CURRENT_DB_COUNTS_SQL,
    PERMISSION_SEPARATION,
    HUMAN_ONLY_FIELDS,
    NON_EXECUTION_CONFIRMATIONS,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    resolveLocalPath,
    toRelativePath,
    querySelectOnly,
    buildMissingAuthorizationRequirements,
    reviewCurrentDbCounts,
    runAuthorizationReview,
    payloadToText,
    main,
};
