#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.73C readiness checklist consolidation review in one audit-friendly file. */

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

const READINESS_REVIEW_PHASE = 'PHASE4.73C_FOOTBALL_DATA_PACKET_FILE_READINESS';
const READINESS_TEMPLATE_PHASE = 'PHASE4_PACKET_FILE_CREATION_READINESS';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --readiness-checklist=<path>, --auth-form=<path>, --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: football-data packet file readiness commit is not wired in Phase 4.73C.';

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

const MISSING_READINESS_ITEMS = [
    'readiness_status must be ready',
    'authorization_status must be authorized_for_packet_file_creation',
    'final_packet_creation_confirmation must be true',
    'operator must be filled',
    'reviewer must be filled',
    'human_approval_note must be present',
    'packet_creation_reason must be present',
    'packet_directory must be explicit',
    'packet_file must be explicit',
    'packet_manifest_file must be explicit',
    'approved_candidate_match_ids must be reviewed',
    'manual_review_candidate_match_ids must be excluded or resolved',
    'packet file creation must be separately authorized by human',
];

const PERMISSION_SEPARATION = [
    'readiness does not authorize packet file creation',
    'packet file creation does not authorize DB write',
    'packet file creation does not authorize pg_dump',
    'packet file creation does not authorize pg_restore',
    'packet file creation does not authorize training',
    'packet file creation does not authorize prediction',
];

const HUMAN_ONLY_FIELDS = [
    'readiness_status',
    'authorization_status',
    'final_packet_creation_confirmation',
    'operator',
    'reviewer',
    'human_approval_note',
    'packet_creation_reason',
    'approved_candidate_match_ids',
    'excluded_candidate_match_ids',
    'manual_review_candidate_match_ids',
    'packet_directory',
    'packet_file',
    'packet_manifest_file',
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

const REQUIRED_READINESS_FIELDS = [
    'phase',
    'readiness_status',
    'operator',
    'reviewer',
    'source_manifest',
    'local_csv',
    'approval_form',
    'runbook_template',
    'packet_auth_form',
    'packet_directory',
    'packet_file',
    'packet_manifest_file',
    'approved_output_root',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_readiness_review.js --readiness-checklist <path> --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path>',
        '  node scripts/ops/football_data_packet_file_readiness_review.js --readiness-checklist <path> --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> --commit',
        '',
        'Safety:',
        '  Phase 4.73C runs readiness checklist consolidation only.',
        '  No packet file writes, no packet directory creation, no DB writes, no pg_dump, no pg_restore, no child processes, no network.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOptions = new Map([
        ['--readiness-checklist', 'readinessChecklist'],
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
        readinessChecklist: '',
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

function readReviewedInputs(pathContext, readFileSync) {
    return {
        readinessChecklistMarkdown: readFileSync(pathContext.readinessChecklistPath, 'utf8'),
        authFormMarkdown: readFileSync(pathContext.authFormPath, 'utf8'),
        sourceManifestText: readFileSync(pathContext.sourceManifestPath, 'utf8'),
        localCsvText: readFileSync(pathContext.localCsvPath, 'utf8'),
        approvalFormMarkdown: readFileSync(pathContext.approvalFormPath, 'utf8'),
        runbookTemplateMarkdown: readFileSync(pathContext.runbookTemplatePath, 'utf8'),
    };
}

function parseReadinessChecklist(markdownText) {
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        throw new Error('YAML fenced block not found in packet file readiness checklist');
    }
    return parseYamlBlock(yamlText);
}

function validateRequiredArgs(args) {
    return Boolean(
        args.readinessChecklist &&
        args.authForm &&
        args.sourceManifest &&
        args.localCsv &&
        args.approvalForm &&
        args.runbookTemplate
    );
}

function buildPathContext(args, cwd, existsSync) {
    const readinessChecklistPath = resolveLocalPath(args.readinessChecklist, cwd);
    const authFormPath = resolveLocalPath(args.authForm, cwd);
    const sourceManifestPath = resolveLocalPath(args.sourceManifest, cwd);
    const localCsvPath = resolveLocalPath(args.localCsv, cwd);
    const approvalFormPath = resolveLocalPath(args.approvalForm, cwd);
    const runbookTemplatePath = resolveLocalPath(args.runbookTemplate, cwd);
    return {
        readinessChecklistPath,
        authFormPath,
        sourceManifestPath,
        localCsvPath,
        approvalFormPath,
        runbookTemplatePath,
        readinessChecklistFound: existsSync(readinessChecklistPath),
        authFormFound: existsSync(authFormPath),
        sourceManifestFound: existsSync(sourceManifestPath),
        localCsvFound: existsSync(localCsvPath),
        approvalFormFound: existsSync(approvalFormPath),
        runbookTemplateFound: existsSync(runbookTemplatePath),
        cwd,
    };
}

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        readiness_review_completed: true,
        readiness_status: 'not_ready',
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        db_write_authorized: false,
        pg_dump_authorized: false,
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
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: READINESS_REVIEW_PHASE,
        mode: fields.mode || 'football-data-packet-file-readiness-review',
        ok: false,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        readiness_checklist_found: false,
        auth_form_found: false,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        packet_file_auth_review_passed: false,
        packet_file_auth_validation_passed: false,
        packet_file_preflight_passed: false,
        packet_preview_passed: false,
        select_only_db_reads: false,
        readiness_review_completed: false,
        readiness_status: 'not_ready',
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        db_write_authorized: false,
        pg_dump_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
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
        commit_gate: 'blocked',
        missing_readiness_items: MISSING_READINESS_ITEMS,
        permission_separation: PERMISSION_SEPARATION,
        human_only_fields: HUMAN_ONLY_FIELDS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        errors: [],
        warnings: [],
        current_db_counts: null,
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

function buildMissingPathPayload(args, pathContext) {
    const baseFields = {
        readiness_checklist_found: pathContext.readinessChecklistFound,
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,
    };

    if (!pathContext.readinessChecklistFound) {
        return buildFailurePayload(args, {
            mode: 'readiness-checklist-error',
            ...baseFields,
            errors: [
                `readiness checklist not found: ${toRelativePath(pathContext.readinessChecklistPath, pathContext.cwd)}`,
            ],
        });
    }
    if (!pathContext.authFormFound) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            ...baseFields,
            errors: [`auth form not found: ${toRelativePath(pathContext.authFormPath, pathContext.cwd)}`],
        });
    }
    if (!pathContext.sourceManifestFound) {
        return buildFailurePayload(args, {
            mode: 'manifest-error',
            ...baseFields,
            errors: [`source manifest not found: ${toRelativePath(pathContext.sourceManifestPath, pathContext.cwd)}`],
        });
    }
    if (!pathContext.localCsvFound) {
        return buildFailurePayload(args, {
            mode: 'csv-error',
            ...baseFields,
            errors: [`local CSV not found: ${toRelativePath(pathContext.localCsvPath, pathContext.cwd)}`],
        });
    }
    if (!pathContext.approvalFormFound) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            ...baseFields,
            errors: [`approval form not found: ${toRelativePath(pathContext.approvalFormPath, pathContext.cwd)}`],
        });
    }
    if (!pathContext.runbookTemplateFound) {
        return buildFailurePayload(args, {
            mode: 'runbook-template-error',
            ...baseFields,
            errors: [`runbook template not found: ${toRelativePath(pathContext.runbookTemplatePath, pathContext.cwd)}`],
        });
    }
    return null;
}

function validateScalarFields(readinessData, errors) {
    if (readinessData.phase !== READINESS_TEMPLATE_PHASE) {
        errors.push(`readiness checklist phase must be ${READINESS_TEMPLATE_PHASE}, got: ${readinessData.phase}`);
    }
    if (readinessData.readiness_status !== 'not_ready') {
        errors.push(`readiness_status must be not_ready, got: ${readinessData.readiness_status}`);
    }
}

function validateFinalReadinessFalse(readinessData, errors) {
    const fields = [
        'packet_file_creation_ready',
        'packet_file_creation_authorized',
        'db_write_authorized',
        'pg_dump_authorized',
        'training_authorized',
        'prediction_authorized',
    ];
    for (const field of fields) {
        const value = (readinessData['final_readiness'] || {})[field];
        if (value !== false && value !== undefined) {
            errors.push(`final_readiness.${field} must be false, got: ${value}`);
        }
    }
}

function validateSafetyChecksFalse(readinessData, errors) {
    const fields = [
        'allow_packet_directory_creation',
        'allow_packet_file_write',
        'allow_packet_manifest_write',
        'allow_db_write',
        'allow_pg_dump',
        'allow_pg_restore',
        'allow_external_network',
        'allow_training',
        'allow_prediction',
    ];
    for (const field of fields) {
        const value = (readinessData['safety_checks'] || {})[field];
        if (value !== false && value !== undefined) {
            errors.push(`safety_checks.${field} must be false, got: ${value}`);
        }
    }
}

function validateRequiredFieldsPresent(readinessData, errors) {
    for (const field of REQUIRED_READINESS_FIELDS) {
        if (readinessData[field] === undefined) {
            errors.push(`required field missing from readiness checklist: ${field}`);
        }
    }
}

function validateReadinessChecklistStructure(readinessData) {
    const errors = [];
    if (!readinessData || typeof readinessData !== 'object') {
        errors.push('readiness checklist YAML is not a valid object');
        return errors;
    }
    validateScalarFields(readinessData, errors);
    validateFinalReadinessFalse(readinessData, errors);
    validateSafetyChecksFalse(readinessData, errors);
    validateRequiredFieldsPresent(readinessData, errors);
    return errors;
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

function validateAndParseReadiness(inputs) {
    const errors = [];
    let readinessData = null;
    try {
        readinessData = parseReadinessChecklist(inputs.readinessChecklistMarkdown);
    } catch (err) {
        errors.push(`readiness checklist parse failed: ${err.message}`);
    }
    if (readinessData) {
        const structureErrors = validateReadinessChecklistStructure(readinessData);
        errors.push(...structureErrors);
    } else {
        errors.push('readiness checklist could not be parsed');
    }
    return { readinessData, errors };
}

function runAuthValidationPass(inputs, readFileSync) {
    try {
        const authResult = runValidation(inputs.authFormMarkdown, readFileSync);
        return { passed: authResult && authResult.ok, error: null };
    } catch (err) {
        return { passed: false, error: err.message };
    }
}

async function runPacketPreviewGate(args, dependencies) {
    try {
        const packetArgs = {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
            commit: false,
            json: true,
        };
        const payload = await runPacketAssembly(packetArgs, dependencies);
        return { passed: payload && payload.ok, error: null };
    } catch (err) {
        return { passed: false, error: err.message };
    }
}

async function runPreflightGate(args, dependencies) {
    try {
        const preflightArgs = {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
            commit: false,
            json: true,
        };
        const result = await runPacketFilePreflight(preflightArgs, dependencies);
        return { passed: result && result.ok, error: null };
    } catch (err) {
        return { passed: false, error: err.message };
    }
}

async function runAuthReviewGate(args, dependencies) {
    try {
        const { runAuthorizationReview } = require('./football_data_packet_file_auth_review');
        const reviewArgs = {
            authForm: args.authForm,
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
            commit: false,
            json: true,
        };
        const result = await runAuthorizationReview(reviewArgs, dependencies);
        return { passed: result && result.ok, error: null };
    } catch (err) {
        return { passed: false, error: err.message };
    }
}

async function runDbCountsQuery(dependencies) {
    try {
        const result = await withDbClient(dependencies, async client => {
            const res = await querySelectOnly(client, CURRENT_DB_COUNTS_SQL);
            return res.rows;
        });
        return { dbCounts: mapCurrentDbCounts(result), ok: true };
    } catch (err) {
        return { dbCounts: null, ok: false, error: err.message };
    }
}

function resolveInputs(args, dependencies) {
    const {
        cwd = process.cwd(),
        existsSync: suppliedExistsSync = fs.existsSync.bind(fs),
        readFileSync: suppliedReadFileSync = fs.readFileSync.bind(fs),
    } = dependencies;

    if (!validateRequiredArgs(args)) {
        return { earlyPayload: buildFailurePayload(args, { errors: [MISSING_ARGS_MESSAGE] }) };
    }
    if (args.commit) {
        return { earlyPayload: buildBlockedCommitPayload(args) };
    }
    const pathContext = buildPathContext(args, cwd, suppliedExistsSync);
    const missingPayload = buildMissingPathPayload(args, pathContext);
    if (missingPayload) {
        return { earlyPayload: missingPayload };
    }
    try {
        const inputs = readReviewedInputs(pathContext, suppliedReadFileSync);
        return {
            pathContext,
            inputs,
            errors: validateAndParseReadiness(inputs).errors,
            readFileSync: suppliedReadFileSync,
        };
    } catch (err) {
        return {
            earlyPayload: buildFailurePayload(args, {
                readiness_checklist_found: pathContext.readinessChecklistFound,
                auth_form_found: pathContext.authFormFound,
                source_manifest_found: pathContext.sourceManifestFound,
                local_csv_found: pathContext.localCsvFound,
                approval_form_found: pathContext.approvalFormFound,
                runbook_template_found: pathContext.runbookTemplateFound,
                errors: [`failed to read input files: ${err.message}`],
            }),
        };
    }
}

async function runGateChecks(args, dependencies, inputs, readFileSync) {
    const warnings = [];
    const gates = {};

    gates.authVal = runAuthValidationPass(inputs, readFileSync);
    if (!gates.authVal.passed) {
        warnings.push('auth form validation did not pass');
    }

    gates.packetPreview = await runPacketPreviewGate(args, dependencies);
    if (!gates.packetPreview.passed) {
        warnings.push('packet preview did not pass');
    }

    gates.preflight = await runPreflightGate(args, dependencies);
    if (!gates.preflight.passed) {
        warnings.push('packet file preflight did not pass');
    }

    gates.authReview = await runAuthReviewGate(args, dependencies);
    if (!gates.authReview.passed) {
        warnings.push('packet file auth review did not pass');
    }

    gates.dbResult = await runDbCountsQuery(dependencies);
    if (!gates.dbResult.ok) {
        warnings.push('SELECT-only DB read failed');
    }

    return { gates, warnings };
}

function buildReviewPayload(args, pathContext, gates, errors, warnings) {
    return {
        phase: READINESS_REVIEW_PHASE,
        mode: 'football-data-packet-file-readiness-review',
        ok: errors.length === 0,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,

        readiness_checklist_found: pathContext.readinessChecklistFound,
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,

        packet_file_auth_review_passed: gates.authReview.passed,
        packet_file_auth_validation_passed: gates.authVal.passed,
        packet_file_preflight_passed: gates.preflight.passed,
        packet_preview_passed: gates.packetPreview.passed,
        select_only_db_reads: gates.dbResult.ok,

        readiness_review_completed: true,
        readiness_status: 'not_ready',
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        db_write_authorized: false,
        pg_dump_authorized: false,
        training_authorized: false,
        prediction_authorized: false,

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
        commit_gate: 'blocked',

        missing_readiness_items: MISSING_READINESS_ITEMS,
        permission_separation: PERMISSION_SEPARATION,
        human_only_fields: HUMAN_ONLY_FIELDS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,

        current_db_counts: gates.dbResult.dbCounts,
        errors,
        warnings,
    };
}

async function runReadinessReview(args, dependencies = {}) {
    const resolved = resolveInputs(args, dependencies);
    if (resolved.earlyPayload) {
        return resolved.earlyPayload;
    }

    const { pathContext, inputs, errors, readFileSync } = resolved;
    const { gates, warnings } = await runGateChecks(args, dependencies, inputs, readFileSync);
    return buildReviewPayload(args, pathContext, gates, errors, warnings);
}

async function main(argv = process.argv.slice(2)) {
    let args;
    try {
        args = parseArgs(argv);
    } catch (err) {
        console.error(`ERROR: ${err.message}`);
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    if (args.help) {
        console.error(usage());
        return;
    }

    const result = await runReadinessReview(args);

    if (result.errors && result.errors.length > 0) {
        console.error('ERROR:', result.errors.join('\n'));
    }
    if (result.warnings && result.warnings.length > 0) {
        console.error('WARN:', result.warnings.join('\n'));
    }

    if (args.json) {
        console.log(JSON.stringify(result, null, 2));
    } else {
        // Human-readable text output
        const lines = [
            `phase=${result.phase}`,
            `readiness_checklist_found=${result.readiness_checklist_found}`,
            `auth_form_found=${result.auth_form_found}`,
            `source_manifest_found=${result.source_manifest_found}`,
            `local_csv_found=${result.local_csv_found}`,
            `approval_form_found=${result.approval_form_found}`,
            `runbook_template_found=${result.runbook_template_found}`,
            '',
            `packet_file_auth_review_passed=${result.packet_file_auth_review_passed}`,
            `packet_file_auth_validation_passed=${result.packet_file_auth_validation_passed}`,
            `packet_file_preflight_passed=${result.packet_file_preflight_passed}`,
            `packet_preview_passed=${result.packet_preview_passed}`,
            `select_only_db_reads=${result.select_only_db_reads}`,
            '',
            `readiness_review_completed=${result.readiness_review_completed}`,
            `readiness_status=${result.readiness_status}`,
            `packet_file_creation_ready=${result.packet_file_creation_ready}`,
            `packet_file_creation_authorized=${result.packet_file_creation_authorized}`,
            `db_write_authorized=${result.db_write_authorized}`,
            `pg_dump_authorized=${result.pg_dump_authorized}`,
            `training_authorized=${result.training_authorized}`,
            `prediction_authorized=${result.prediction_authorized}`,
            '',
            `would_create_packet_directory=${result.would_create_packet_directory}`,
            `would_write_packet_file=${result.would_write_packet_file}`,
            `would_write_packet_manifest=${result.would_write_packet_manifest}`,
            `would_execute_pg_dump=${result.would_execute_pg_dump}`,
            `would_execute_pg_restore=${result.would_execute_pg_restore}`,
            `would_insert_matches=${result.would_insert_matches}`,
            `would_insert_odds=${result.would_insert_odds}`,
            `would_write_db=${result.would_write_db}`,
            `would_access_network=${result.would_access_network}`,
            `would_write_files=${result.would_write_files}`,
            `commit_gate=${result.commit_gate}`,
            '',
            'missing_readiness_items:',
            ...result.missing_readiness_items.map(item => `- ${item}`),
            '',
            'permission_separation:',
            ...result.permission_separation.map(item => `- ${item}`),
            '',
            'human_only_fields:',
            ...result.human_only_fields.map(item => `- ${item}`),
            '',
            'non_execution_confirmations:',
            ...result.non_execution_confirmations.map(item => `- ${item}`),
        ];
        if (result.current_db_counts) {
            lines.push('');
            lines.push('current_db_counts:');
            for (const [table, count] of Object.entries(result.current_db_counts)) {
                lines.push(`  ${table}=${count}`);
            }
        }
        console.log(lines.join('\n'));
    }

    if (!result.ok) {
        process.exitCode = 1;
    }
}

if (require.main === module) {
    main().catch(err => {
        console.error('FATAL:', err.message);
        process.exitCode = 1;
    });
}

module.exports = {
    runReadinessReview,
    parseReadinessChecklist,
    validateReadinessChecklistStructure,
    validateRequiredArgs,
    buildPathContext,
    parseArgs,
    buildSafetyFlags,
    buildFailurePayload,
    buildBlockedCommitPayload,
    buildMissingPathPayload,
    MISSING_ARGS_MESSAGE,
    BLOCKED_COMMIT_MESSAGE,
    READINESS_REVIEW_PHASE,
    READINESS_TEMPLATE_PHASE,
    MISSING_READINESS_ITEMS,
    PERMISSION_SEPARATION,
    HUMAN_ONLY_FIELDS,
    NON_EXECUTION_CONFIRMATIONS,
    REQUIRED_READINESS_FIELDS,
    CURRENT_DB_TABLES,
    CURRENT_DB_COUNTS_SQL,
    mapCurrentDbCounts,
};
