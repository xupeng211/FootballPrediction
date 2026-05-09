#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.76C pre-authorization closure is kept in one audit-friendly gate file. */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const {
    runConsolidationReview,
    parseConsolidationTemplate,
    validateConsolidation,
    CURRENT_DB_COUNTS_SQL,
    mapDbCounts,
} = require('./football_data_packet_file_auth_review_consolidation');
const {
    runDraftReview,
    parseDraftTemplate,
    validateDraftTemplateStructure,
} = require('./football_data_packet_file_auth_packet_draft');
const {
    runReadinessReview,
    parseReadinessChecklist,
    validateReadinessChecklistStructure,
} = require('./football_data_packet_file_readiness_review');
const { runAuthorizationReview } = require('./football_data_packet_file_auth_review');
const { runValidation, extractYamlBlock, parseYamlBlock } = require('./football_data_packet_file_auth_validate');
const { runPacketFilePreflight } = require('./football_data_packet_file_preflight');
const { runPacketAssembly } = require('./football_data_small_write_packet_assembly');
const { buildDbConfig, assertSelectOnlySql } = require('./football_data_duplicate_precheck');

const CLOSURE_PHASE = 'PHASE4.76C_FOOTBALL_DATA_PACKET_FILE_PREAUTHORIZATION_CLOSURE';
const CLOSURE_TEMPLATE_PHASE = 'PHASE4_PACKET_FILE_PREAUTHORIZATION_CLOSURE';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --closure-template=<path>, --consolidation-template=<path>, --draft-template=<path>, --readiness-checklist=<path>, --auth-form=<path>, --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: football-data packet file pre-authorization closure commit is not wired in Phase 4.76C.';

const REQUIRED_CLOSURE_FIELDS = [
    'phase',
    'closure_status',
    'consolidation_status',
    'draft_status',
    'readiness_status',
    'authorization_status',
    'ready_for_human_review',
    'ready_for_packet_file_creation',
    'authorized_for_packet_file_creation',
    'packet_file_creation_ready',
    'packet_file_creation_authorized',
    'final_packet_creation_confirmation',
    'operator',
    'reviewer',
    'source_manifest',
    'local_csv',
    'approval_form',
    'runbook_template',
    'packet_auth_form',
    'readiness_checklist',
    'auth_packet_draft',
    'auth_review_consolidation',
    'packet_directory',
    'packet_file',
    'packet_manifest_file',
    'approved_output_root',
];

const PREAUTHORIZATION_CLOSURE_SECTIONS = [
    'chain_inventory',
    'gate_inventory',
    'template_inventory',
    'status_summary',
    'human_only_missing_fields',
    'unresolved_readiness_items',
    'consolidated_blocking_reasons',
    'permission_separation',
    'future_authorization_requirements',
    'final_non_authorization_decision',
];

const CLOSURE_BLOCKING_REASONS = [
    'closure_status is preauthorization_closed_not_authorized',
    'consolidation_status is draft_review_only',
    'draft_status is draft_only',
    'readiness_status is not_ready',
    'authorization_status is not_authorized',
    'ready_for_packet_file_creation is false',
    'authorized_for_packet_file_creation is false',
    'packet_file_creation_ready is false',
    'packet_file_creation_authorized is false',
    'final_packet_creation_confirmation is false',
    'human-only fields remain empty',
    'packet path fields remain template-only',
    'candidate approval fields remain template-only',
    'packet file creation is not authorized in this phase',
];

const PERMISSION_SEPARATION = [
    'pre-authorization closure does not authorize packet file creation',
    'packet file creation does not authorize DB write',
    'packet file creation does not authorize pg_dump',
    'packet file creation does not authorize pg_restore',
    'packet file creation does not authorize training',
    'packet file creation does not authorize prediction',
];

const NEXT_PHASE_REQUIREMENTS = [
    'explicit user authorization for packet file creation',
    'real reviewed auth form',
    'real reviewed readiness checklist',
    'explicit packet output directory',
    'explicit packet file path',
    'explicit packet manifest path',
    'reviewed proposed_match_ids',
    'manual_review candidates excluded or resolved',
    'human approval note',
    'final_packet_creation_confirmation=true set only by human',
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

const PATH_FIELDS = [
    'closureTemplate',
    'consolidationTemplate',
    'draftTemplate',
    'readinessChecklist',
    'authForm',
    'sourceManifest',
    'localCsv',
    'approvalForm',
    'runbookTemplate',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_preauthorization_closure.js --closure-template <path> --consolidation-template <path> --draft-template <path> --readiness-checklist <path> --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path>',
        '  node scripts/ops/football_data_packet_file_preauthorization_closure.js ... --commit',
        '',
        'Safety: Phase 4.76C pre-authorization closure only. No writes, no packet directory creation, no pg_dump, no pg_restore, no network, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOptions = new Map([
        ['--closure-template', 'closureTemplate'],
        ['--consolidation-template', 'consolidationTemplate'],
        ['--draft-template', 'draftTemplate'],
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
    const args = Object.fromEntries(PATH_FIELDS.map(field => [field, '']));
    args.commit = false;
    args.json = false;
    args.help = false;

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
            if (usesSeparateValue) index += 1;
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
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function optionName(field) {
    return field.replace(/([A-Z])/g, '-$1').toLowerCase();
}

function validateRequiredArgs(args) {
    return PATH_FIELDS.every(field => Boolean(args[field]));
}

function buildPathContext(args, cwd, existsSync) {
    const context = { cwd };
    for (const field of PATH_FIELDS) {
        const resolved = resolveLocalPath(args[field], cwd);
        context[`${field}Path`] = resolved;
        context[`${field}Found`] = existsSync(resolved);
    }
    return context;
}

function buildBasePayload(args, fields = {}) {
    return {
        phase: CLOSURE_PHASE,
        mode: fields.mode || 'preauthorization-closure',
        ok: false,
        closure_template: args.closureTemplate || null,
        consolidation_template: args.consolidationTemplate || null,
        draft_template: args.draftTemplate || null,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        closure_template_found: false,
        consolidation_template_found: false,
        draft_template_found: false,
        readiness_checklist_found: false,
        auth_form_found: false,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        auth_review_consolidation_passed: false,
        auth_packet_draft_review_passed: false,
        readiness_review_passed: false,
        auth_review_passed: false,
        auth_validation_passed: false,
        packet_file_preflight_passed: false,
        packet_preview_passed: false,
        select_only_db_reads: false,
        closure_review_completed: false,
        closure_status: 'preauthorization_closed_not_authorized',
        consolidation_status: 'draft_review_only',
        draft_status: 'draft_only',
        readiness_status: 'not_ready',
        authorization_status: 'not_authorized',
        ready_for_human_review: false,
        ready_for_packet_file_creation: false,
        authorized_for_packet_file_creation: false,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        final_packet_creation_confirmation: false,
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
        preauthorization_closure_sections: PREAUTHORIZATION_CLOSURE_SECTIONS,
        closure_blocking_reasons: CLOSURE_BLOCKING_REASONS,
        permission_separation: PERMISSION_SEPARATION,
        next_phase_requirements: NEXT_PHASE_REQUIREMENTS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        errors: [],
        warnings: [],
        current_db_counts: null,
        ...fields,
    };
}

function buildBlockedCommitPayload(args) {
    return buildBasePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: BLOCKED_COMMIT_MESSAGE,
        errors: [BLOCKED_COMMIT_MESSAGE],
    });
}

function buildMissingPathPayload(args, pathContext) {
    const foundFields = {};
    for (const field of PATH_FIELDS) {
        foundFields[`${optionName(field).replace(/-/g, '_')}_found`] = pathContext[`${field}Found`];
    }

    for (const field of PATH_FIELDS) {
        if (!pathContext[`${field}Found`]) {
            return buildBasePayload(args, {
                mode: `${optionName(field)}-error`,
                ...foundFields,
                errors: [
                    `${optionName(field).replace(/-/g, ' ')} not found: ${toRelativePath(
                        pathContext[`${field}Path`],
                        pathContext.cwd
                    )}`,
                ],
            });
        }
    }
    return null;
}

function readAllInputs(pathContext, readFileSync) {
    return {
        closureMarkdown: readFileSync(pathContext.closureTemplatePath, 'utf8'),
        consolidationMarkdown: readFileSync(pathContext.consolidationTemplatePath, 'utf8'),
        draftMarkdown: readFileSync(pathContext.draftTemplatePath, 'utf8'),
        readinessMarkdown: readFileSync(pathContext.readinessChecklistPath, 'utf8'),
        authFormMarkdown: readFileSync(pathContext.authFormPath, 'utf8'),
        sourceManifestText: readFileSync(pathContext.sourceManifestPath, 'utf8'),
        localCsvText: readFileSync(pathContext.localCsvPath, 'utf8'),
        approvalFormMarkdown: readFileSync(pathContext.approvalFormPath, 'utf8'),
        runbookTemplateMarkdown: readFileSync(pathContext.runbookTemplatePath, 'utf8'),
    };
}

function parseClosureTemplate(markdownText) {
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) throw new Error('YAML fenced block not found in pre-authorization closure template');
    return parseYamlBlock(yamlText);
}

function requireBoolean(object, key, expected, errors, prefix = '') {
    const value = object ? object[key] : undefined;
    if (value !== expected) errors.push(`${prefix}${key} must be ${expected}, got: ${value}`);
}

function validateClosureScalarFields(closureData, errors) {
    if (closureData.phase !== CLOSURE_TEMPLATE_PHASE) {
        errors.push(`closure template phase must be ${CLOSURE_TEMPLATE_PHASE}, got: ${closureData.phase}`);
    }
    if (closureData.closure_status !== 'preauthorization_closed_not_authorized') {
        errors.push(
            `closure_status must be preauthorization_closed_not_authorized, got: ${closureData.closure_status}`
        );
    }
    if (closureData.consolidation_status !== 'draft_review_only') {
        errors.push(`consolidation_status must be draft_review_only, got: ${closureData.consolidation_status}`);
    }
    if (closureData.draft_status !== 'draft_only') {
        errors.push(`draft_status must be draft_only, got: ${closureData.draft_status}`);
    }
    if (closureData.readiness_status !== 'not_ready') {
        errors.push(`readiness_status must be not_ready, got: ${closureData.readiness_status}`);
    }
    if (closureData.authorization_status !== 'not_authorized') {
        errors.push(`authorization_status must be not_authorized, got: ${closureData.authorization_status}`);
    }
}

function validateClosureFalseFields(closureData, errors) {
    for (const field of [
        'ready_for_human_review',
        'ready_for_packet_file_creation',
        'authorized_for_packet_file_creation',
        'packet_file_creation_ready',
        'packet_file_creation_authorized',
        'final_packet_creation_confirmation',
    ]) {
        requireBoolean(closureData, field, false, errors);
    }
}

function validateClosureRequiredFields(closureData, errors) {
    for (const field of REQUIRED_CLOSURE_FIELDS) {
        if (closureData[field] === undefined) errors.push(`required field missing from closure template: ${field}`);
    }
}

function validateClosureBlockingStatus(closureData, errors) {
    for (const field of [
        'blocks_packet_directory_creation',
        'blocks_packet_file_write',
        'blocks_packet_manifest_write',
        'blocks_db_write',
        'blocks_pg_dump',
        'blocks_pg_restore',
        'blocks_external_network',
        'blocks_training',
        'blocks_prediction',
    ]) {
        requireBoolean(closureData.blocking_status || {}, field, true, errors, 'blocking_status.');
    }
}

function validateClosurePermissionSeparation(closureData, errors) {
    for (const field of [
        'preauthorization_closure_authorizes_packet_file_creation',
        'packet_file_creation_authorizes_db_write',
        'packet_file_creation_authorizes_pg_dump',
        'packet_file_creation_authorizes_pg_restore',
        'packet_file_creation_authorizes_training',
        'packet_file_creation_authorizes_prediction',
    ]) {
        requireBoolean(closureData.permission_separation || {}, field, false, errors, 'permission_separation.');
    }
}

function validateClosureFinalDecision(closureData, errors) {
    requireBoolean(
        closureData.final_decision || {},
        'closure_ready_for_human_review',
        false,
        errors,
        'final_decision.'
    );
    requireBoolean(closureData.final_decision || {}, 'packet_file_creation_ready', false, errors, 'final_decision.');
    requireBoolean(
        closureData.final_decision || {},
        'packet_file_creation_authorized',
        false,
        errors,
        'final_decision.'
    );
    requireBoolean(
        closureData.final_decision || {},
        'next_phase_requires_explicit_human_authorization',
        true,
        errors,
        'final_decision.'
    );
}

function validateClosureTemplateStructure(closureData) {
    const errors = [];
    if (!closureData || typeof closureData !== 'object') {
        errors.push('closure template YAML is not a valid object');
        return errors;
    }
    validateClosureScalarFields(closureData, errors);
    validateClosureFalseFields(closureData, errors);
    validateClosureRequiredFields(closureData, errors);
    validateClosureBlockingStatus(closureData, errors);
    validateClosurePermissionSeparation(closureData, errors);
    validateClosureFinalDecision(closureData, errors);
    return errors;
}

function validateAuthFormTemplate(markdownText) {
    const result = runValidation(
        { authForm: '__inline_auth_form__' },
        {
            existsSync: () => true,
            readFileSync: () => markdownText,
        }
    );
    return result.ok ? [] : result.errors.map(error => `auth form template invalid: ${error}`);
}

function countCsvDataRows(csvText) {
    const lines = String(csvText || '')
        .replace(/^\uFEFF/, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean);
    return Math.max(0, lines.length - 1);
}

function sha256Text(text) {
    return crypto.createHash('sha256').update(text).digest('hex');
}

function validateSourceManifestAndCsv(sourceManifestText, localCsvText) {
    const errors = [];
    let manifest = null;
    try {
        manifest = JSON.parse(sourceManifestText);
    } catch (error) {
        return { errors: [`source manifest parse failed: ${error.message}`], manifest: null };
    }
    const actualSha256 = sha256Text(localCsvText);
    const actualRowCount = countCsvDataRows(localCsvText);
    if (manifest.sha256 !== actualSha256) {
        errors.push('sha256 mismatch; closure review stopped before DB reads');
    }
    if (manifest.row_count !== actualRowCount) {
        errors.push('row_count mismatch; closure review stopped before DB reads');
    }
    return { errors, manifest, actualSha256, actualRowCount };
}

function validateAllTemplates(inputs) {
    const errors = [];
    try {
        errors.push(...validateClosureTemplateStructure(parseClosureTemplate(inputs.closureMarkdown)));
    } catch (error) {
        errors.push(`closure template parse failed: ${error.message}`);
    }
    try {
        errors.push(...validateConsolidation(parseConsolidationTemplate(inputs.consolidationMarkdown)));
    } catch (error) {
        errors.push(`consolidation template parse failed: ${error.message}`);
    }
    try {
        errors.push(...validateDraftTemplateStructure(parseDraftTemplate(inputs.draftMarkdown)));
    } catch (error) {
        errors.push(`draft template parse failed: ${error.message}`);
    }
    try {
        errors.push(...validateReadinessChecklistStructure(parseReadinessChecklist(inputs.readinessMarkdown)));
    } catch (error) {
        errors.push(`readiness checklist parse failed: ${error.message}`);
    }
    errors.push(...validateAuthFormTemplate(inputs.authFormMarkdown));
    return errors;
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function withDbClient(dependencies, callback) {
    if (dependencies.dbClient) return callback(dependencies.dbClient);
    const pool = dependencies.pool || (dependencies.createPool || createPool)();
    const client = await pool.connect();
    try {
        return await callback(client);
    } finally {
        client.release();
        if (!dependencies.pool && typeof pool.end === 'function') await pool.end();
    }
}

async function querySelectOnly(client, sql) {
    assertSelectOnlySql(sql);
    return client.query(sql);
}

async function runAllGates(args, dependencies) {
    const gates = {};
    try {
        gates.consolidation = await runConsolidationReview(
            {
                consolidationTemplate: args.consolidationTemplate,
                draftTemplate: args.draftTemplate,
                readinessChecklist: args.readinessChecklist,
                authForm: args.authForm,
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.consolidationError = error.message;
    }
    try {
        gates.draft = await runDraftReview(
            {
                draftTemplate: args.draftTemplate,
                readinessChecklist: args.readinessChecklist,
                authForm: args.authForm,
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.draftError = error.message;
    }
    try {
        gates.readiness = await runReadinessReview(
            {
                readinessChecklist: args.readinessChecklist,
                authForm: args.authForm,
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.readinessError = error.message;
    }
    try {
        gates.authReview = await runAuthorizationReview(
            {
                authForm: args.authForm,
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.authReviewError = error.message;
    }
    try {
        gates.authValidation = runValidation({ authForm: args.authForm, commit: false, json: true }, dependencies);
    } catch (error) {
        gates.authValidationError = error.message;
    }
    try {
        gates.preflight = await runPacketFilePreflight(
            {
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.preflightError = error.message;
    }
    try {
        gates.preview = await runPacketAssembly(
            {
                sourceManifest: args.sourceManifest,
                localCsv: args.localCsv,
                approvalForm: args.approvalForm,
                runbookTemplate: args.runbookTemplate,
                commit: false,
                json: true,
            },
            dependencies
        );
    } catch (error) {
        gates.previewError = error.message;
    }
    try {
        gates.dbRows = await withDbClient(
            dependencies,
            async client => (await querySelectOnly(client, CURRENT_DB_COUNTS_SQL)).rows
        );
    } catch (error) {
        gates.dbRowsError = error.message;
    }
    return gates;
}

async function runPreauthorizationClosure(args, dependencies = {}) {
    const {
        cwd = process.cwd(),
        existsSync = fs.existsSync.bind(fs),
        readFileSync = fs.readFileSync.bind(fs),
    } = dependencies;

    if (!validateRequiredArgs(args)) return buildBasePayload(args, { errors: [MISSING_ARGS_MESSAGE] });
    if (args.commit) return buildBlockedCommitPayload(args);

    const pathContext = buildPathContext(args, cwd, existsSync);
    const missingPayload = buildMissingPathPayload(args, pathContext);
    if (missingPayload) return missingPayload;

    let inputs;
    try {
        inputs = readAllInputs(pathContext, readFileSync);
    } catch (error) {
        return buildBasePayload(args, { errors: [`failed to read input files: ${error.message}`] });
    }

    const templateErrors = validateAllTemplates(inputs);
    const integrity = validateSourceManifestAndCsv(inputs.sourceManifestText, inputs.localCsvText);
    const earlyErrors = [...templateErrors, ...integrity.errors];
    if (earlyErrors.length > 0) {
        return buildBasePayload(args, {
            mode: 'preauthorization-closure-error',
            closure_template_found: pathContext.closureTemplateFound,
            consolidation_template_found: pathContext.consolidationTemplateFound,
            draft_template_found: pathContext.draftTemplateFound,
            readiness_checklist_found: pathContext.readinessChecklistFound,
            auth_form_found: pathContext.authFormFound,
            source_manifest_found: pathContext.sourceManifestFound,
            local_csv_found: pathContext.localCsvFound,
            approval_form_found: pathContext.approvalFormFound,
            runbook_template_found: pathContext.runbookTemplateFound,
            errors: earlyErrors,
        });
    }

    const gates = await runAllGates(args, dependencies);

    return {
        phase: CLOSURE_PHASE,
        mode: 'preauthorization-closure',
        ok: true,
        closure_template: args.closureTemplate,
        consolidation_template: args.consolidationTemplate,
        draft_template: args.draftTemplate,
        readiness_checklist: args.readinessChecklist,
        auth_form: args.authForm,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        approval_form: args.approvalForm,
        runbook_template: args.runbookTemplate,
        closure_template_found: pathContext.closureTemplateFound,
        consolidation_template_found: pathContext.consolidationTemplateFound,
        draft_template_found: pathContext.draftTemplateFound,
        readiness_checklist_found: pathContext.readinessChecklistFound,
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,
        auth_review_consolidation_passed:
            gates.consolidation && gates.consolidation.consolidation_review_completed === true,
        auth_packet_draft_review_passed: gates.draft && gates.draft.draft_review_completed === true,
        readiness_review_passed: gates.readiness && gates.readiness.readiness_review_completed === true,
        auth_review_passed: gates.authReview && gates.authReview.ok === true,
        auth_validation_passed: gates.authValidation && gates.authValidation.ok === true,
        packet_file_preflight_passed: gates.preflight && gates.preflight.ok === true,
        packet_preview_passed: gates.preview && gates.preview.ok === true,
        select_only_db_reads: Array.isArray(gates.dbRows),
        closure_review_completed: true,
        closure_status: 'preauthorization_closed_not_authorized',
        consolidation_status: 'draft_review_only',
        draft_status: 'draft_only',
        readiness_status: 'not_ready',
        authorization_status: 'not_authorized',
        ready_for_human_review: false,
        ready_for_packet_file_creation: false,
        authorized_for_packet_file_creation: false,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        final_packet_creation_confirmation: false,
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
        preauthorization_closure_sections: PREAUTHORIZATION_CLOSURE_SECTIONS,
        closure_blocking_reasons: CLOSURE_BLOCKING_REASONS,
        permission_separation: PERMISSION_SEPARATION,
        next_phase_requirements: NEXT_PHASE_REQUIREMENTS,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        current_db_counts: gates.dbRows ? mapDbCounts(gates.dbRows) : null,
        errors: [],
        warnings: Object.entries(gates)
            .filter(([key]) => key.endsWith('Error'))
            .map(([key, value]) => `${key}: ${value}`),
    };
}

function payloadToText(result) {
    const lines = [
        `phase=${result.phase}`,
        `closure_template_found=${result.closure_template_found}`,
        `consolidation_template_found=${result.consolidation_template_found}`,
        `draft_template_found=${result.draft_template_found}`,
        `readiness_checklist_found=${result.readiness_checklist_found}`,
        `auth_form_found=${result.auth_form_found}`,
        `source_manifest_found=${result.source_manifest_found}`,
        `local_csv_found=${result.local_csv_found}`,
        `approval_form_found=${result.approval_form_found}`,
        `runbook_template_found=${result.runbook_template_found}`,
        '',
        `auth_review_consolidation_passed=${result.auth_review_consolidation_passed}`,
        `auth_packet_draft_review_passed=${result.auth_packet_draft_review_passed}`,
        `readiness_review_passed=${result.readiness_review_passed}`,
        `auth_review_passed=${result.auth_review_passed}`,
        `auth_validation_passed=${result.auth_validation_passed}`,
        `packet_file_preflight_passed=${result.packet_file_preflight_passed}`,
        `packet_preview_passed=${result.packet_preview_passed}`,
        `select_only_db_reads=${result.select_only_db_reads}`,
        '',
        `closure_review_completed=${result.closure_review_completed}`,
        `closure_status=${result.closure_status}`,
        `consolidation_status=${result.consolidation_status}`,
        `draft_status=${result.draft_status}`,
        `readiness_status=${result.readiness_status}`,
        `authorization_status=${result.authorization_status}`,
        `ready_for_human_review=${result.ready_for_human_review}`,
        `ready_for_packet_file_creation=${result.ready_for_packet_file_creation}`,
        `authorized_for_packet_file_creation=${result.authorized_for_packet_file_creation}`,
        `packet_file_creation_ready=${result.packet_file_creation_ready}`,
        `packet_file_creation_authorized=${result.packet_file_creation_authorized}`,
        `final_packet_creation_confirmation=${result.final_packet_creation_confirmation}`,
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
        'preauthorization_closure_sections:',
        ...result.preauthorization_closure_sections.map(section => `- ${section}`),
        '',
        'closure_blocking_reasons:',
        ...result.closure_blocking_reasons.map(reason => `- ${reason}`),
        '',
        'permission_separation:',
        ...result.permission_separation.map(item => `- ${item}`),
        '',
        'next_phase_requirements:',
        ...result.next_phase_requirements.map(item => `- ${item}`),
        '',
        'non_execution_confirmations:',
        ...result.non_execution_confirmations.map(item => `- ${item}`),
    ];
    if (result.current_db_counts) {
        lines.push('', 'current_db_counts:');
        for (const [tableName, count] of Object.entries(result.current_db_counts)) {
            lines.push(`  ${tableName}=${count}`);
        }
    }
    if (result.errors.length > 0) lines.push('', `errors=${result.errors.join('; ')}`);
    if (result.warnings.length > 0) lines.push('', `warnings=${result.warnings.join('; ')}`);
    return lines.join('\n');
}

async function main(argv = process.argv.slice(2)) {
    let args;
    try {
        args = parseArgs(argv);
    } catch (error) {
        console.error(`ERROR: ${error.message}`);
        console.error(usage());
        process.exitCode = 1;
        return;
    }
    if (args.help) {
        console.log(usage());
        return;
    }

    const result = await runPreauthorizationClosure(args);
    if (result.errors.length > 0) console.error('ERROR:', result.errors.join('\n'));
    if (result.warnings.length > 0) console.error('WARN:', result.warnings.join('\n'));
    console.log(args.json ? JSON.stringify(result, null, 2) : payloadToText(result));
    if (!result.ok) process.exitCode = 1;
}

if (require.main === module) {
    main().catch(error => {
        console.error('FATAL:', error.message);
        process.exitCode = 1;
    });
}

module.exports = {
    runPreauthorizationClosure,
    parseArgs,
    validateRequiredArgs,
    buildPathContext,
    parseClosureTemplate,
    validateClosureTemplateStructure,
    validateSourceManifestAndCsv,
    payloadToText,
    CLOSURE_PHASE,
    CLOSURE_TEMPLATE_PHASE,
    MISSING_ARGS_MESSAGE,
    BLOCKED_COMMIT_MESSAGE,
    REQUIRED_CLOSURE_FIELDS,
    PREAUTHORIZATION_CLOSURE_SECTIONS,
    CLOSURE_BLOCKING_REASONS,
    PERMISSION_SEPARATION,
    NEXT_PHASE_REQUIREMENTS,
    NON_EXECUTION_CONFIRMATIONS,
};
