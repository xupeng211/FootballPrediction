#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.74C auth packet draft review in one audit-friendly file. */

const fs = require('fs');
const path = require('path');

const { runValidation, extractYamlBlock, parseYamlBlock } = require('./football_data_packet_file_auth_validate');
const { runPacketFilePreflight } = require('./football_data_packet_file_preflight');
const { runPacketAssembly } = require('./football_data_small_write_packet_assembly');
const { runAuthorizationReview } = require('./football_data_packet_file_auth_review');
const { runReadinessReview } = require('./football_data_packet_file_readiness_review');
const {
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    buildDbConfig,
    assertSelectOnlySql,
} = require('./football_data_duplicate_precheck');

const AUTH_PACKET_DRAFT_PHASE = 'PHASE4.74C_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT';
const DRAFT_TEMPLATE_PHASE = 'PHASE4_PACKET_FILE_CREATION_AUTH_PACKET_DRAFT';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --draft-template=<path>, --readiness-checklist=<path>, --auth-form=<path>, --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: football-data packet file authorization packet draft commit is not wired in Phase 4.74C.';

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

const AUTHORIZATION_PACKET_DRAFT_SECTIONS = [
    'packet_creation_scope',
    'source_inputs_summary',
    'gate_results_summary',
    'readiness_review_summary',
    'authorization_review_summary',
    'proposed_packet_paths',
    'proposed_packet_metadata',
    'proposed_candidate_match_ids',
    'blocked_candidate_summary',
    'manual_review_summary',
    'human_only_fields',
    'missing_readiness_items',
    'permission_separation',
    'final_human_decision_required',
];

const MISSING_DRAFT_REQUIREMENTS = [
    'draft_status must remain draft_only until human review',
    'readiness_status must be ready before creation',
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
];

const PERMISSION_SEPARATION = [
    'authorization packet draft does not authorize packet file creation',
    'packet file creation does not authorize DB write',
    'packet file creation does not authorize pg_dump',
    'packet file creation does not authorize pg_restore',
    'packet file creation does not authorize training',
    'packet file creation does not authorize prediction',
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

const REQUIRED_DRAFT_FIELDS = [
    'phase',
    'draft_status',
    'packet_file_creation_authorized',
    'packet_file_creation_ready',
    'readiness_status',
    'authorization_status',
    'final_packet_creation_confirmation',
    'operator',
    'reviewer',
    'source_manifest',
    'local_csv',
    'approval_form',
    'runbook_template',
    'packet_auth_form',
    'readiness_checklist',
    'packet_directory',
    'packet_file',
    'packet_manifest_file',
    'approved_output_root',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_auth_packet_draft.js --draft-template <path> --readiness-checklist <path> --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path>',
        '  node scripts/ops/football_data_packet_file_auth_packet_draft.js ... --commit',
        '',
        'Safety:',
        '  Phase 4.74C generates authorization packet draft review only.',
        '  No packet file writes, no packet directory creation, no DB writes, no pg_dump, no pg_restore, no child processes, no network.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOptions = new Map([
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
    const args = {
        draftTemplate: '',
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
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function validateRequiredArgs(args) {
    return Boolean(
        args.draftTemplate &&
        args.readinessChecklist &&
        args.authForm &&
        args.sourceManifest &&
        args.localCsv &&
        args.approvalForm &&
        args.runbookTemplate
    );
}

function buildPathContext(args, cwd, existsSync) {
    const paths = {
        draftTemplatePath: resolveLocalPath(args.draftTemplate, cwd),
        readinessChecklistPath: resolveLocalPath(args.readinessChecklist, cwd),
        authFormPath: resolveLocalPath(args.authForm, cwd),
        sourceManifestPath: resolveLocalPath(args.sourceManifest, cwd),
        localCsvPath: resolveLocalPath(args.localCsv, cwd),
        approvalFormPath: resolveLocalPath(args.approvalForm, cwd),
        runbookTemplatePath: resolveLocalPath(args.runbookTemplate, cwd),
    };
    return {
        ...paths,
        draftTemplateFound: existsSync(paths.draftTemplatePath),
        readinessChecklistFound: existsSync(paths.readinessChecklistPath),
        authFormFound: existsSync(paths.authFormPath),
        sourceManifestFound: existsSync(paths.sourceManifestPath),
        localCsvFound: existsSync(paths.localCsvPath),
        approvalFormFound: existsSync(paths.approvalFormPath),
        runbookTemplateFound: existsSync(paths.runbookTemplatePath),
        cwd,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: AUTH_PACKET_DRAFT_PHASE,
        mode: fields.mode || 'football-data-packet-file-auth-packet-draft',
        ok: false,
        draft_template: args.draftTemplate || null,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        draft_template_found: false,
        readiness_checklist_found: false,
        auth_form_found: false,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        readiness_review_passed: false,
        auth_review_passed: false,
        auth_validation_passed: false,
        packet_file_preflight_passed: false,
        packet_preview_passed: false,
        select_only_db_reads: false,
        draft_review_completed: false,
        draft_status: 'draft_only',
        ready_for_human_review: false,
        ready_for_packet_file_creation: false,
        authorized_for_packet_file_creation: false,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        readiness_status: 'not_ready',
        authorization_status: 'not_authorized',
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
        authorization_packet_draft_sections: AUTHORIZATION_PACKET_DRAFT_SECTIONS,
        missing_draft_requirements: MISSING_DRAFT_REQUIREMENTS,
        permission_separation: PERMISSION_SEPARATION,
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
    const fields = [
        'draftTemplate',
        'readinessChecklist',
        'authForm',
        'sourceManifest',
        'localCsv',
        'approvalForm',
        'runbookTemplate',
    ];
    const foundKeys = {
        draftTemplate: 'draft_template_found',
        readinessChecklist: 'readiness_checklist_found',
        authForm: 'auth_form_found',
        sourceManifest: 'source_manifest_found',
        localCsv: 'local_csv_found',
        approvalForm: 'approval_form_found',
        runbookTemplate: 'runbook_template_found',
    };
    for (const field of fields) {
        const found = pathContext[`${field}Found`];
        if (!found) {
            return buildFailurePayload(args, {
                mode: `${field}-error`,
                ...Object.fromEntries(Object.entries(foundKeys).map(([k, v]) => [v, pathContext[`${k}Found`]])),
                errors: [
                    `${field
                        .replace(/([A-Z])/g, ' $1')
                        .toLowerCase()
                        .trim()} not found: ${toRelativePath(pathContext[`${field}Path`], pathContext.cwd)}`,
                ],
            });
        }
    }
    return null;
}

function readAllInputs(pathContext, readFileSync) {
    return {
        draftTemplateMarkdown: readFileSync(pathContext.draftTemplatePath, 'utf8'),
        readinessChecklistMarkdown: readFileSync(pathContext.readinessChecklistPath, 'utf8'),
        authFormMarkdown: readFileSync(pathContext.authFormPath, 'utf8'),
        sourceManifestText: readFileSync(pathContext.sourceManifestPath, 'utf8'),
        localCsvText: readFileSync(pathContext.localCsvPath, 'utf8'),
        approvalFormMarkdown: readFileSync(pathContext.approvalFormPath, 'utf8'),
        runbookTemplateMarkdown: readFileSync(pathContext.runbookTemplatePath, 'utf8'),
    };
}

function parseDraftTemplate(markdownText) {
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        throw new Error('YAML fenced block not found in auth packet draft template');
    }
    return parseYamlBlock(yamlText);
}

function validateDraftTemplateStructure(draftData) {
    const errors = [];
    if (!draftData || typeof draftData !== 'object') {
        errors.push('draft template YAML is not a valid object');
        return errors;
    }
    if (draftData.phase !== DRAFT_TEMPLATE_PHASE) {
        errors.push(`draft template phase must be ${DRAFT_TEMPLATE_PHASE}, got: ${draftData.phase}`);
    }
    if (draftData.draft_status !== 'draft_only') {
        errors.push(`draft_status must be draft_only, got: ${draftData.draft_status}`);
    }
    if (
        draftData.packet_file_creation_authorized !== false &&
        draftData.packet_file_creation_authorized !== undefined
    ) {
        errors.push(`packet_file_creation_authorized must be false, got: ${draftData.packet_file_creation_authorized}`);
    }
    if (draftData.readiness_status !== 'not_ready') {
        errors.push(`readiness_status must be not_ready, got: ${draftData.readiness_status}`);
    }
    for (const key of [
        'ready_for_human_review',
        'ready_for_packet_file_creation',
        'authorized_for_packet_file_creation',
    ]) {
        const val = (draftData.final_decision || {})[key];
        if (val !== false && val !== undefined) {
            errors.push(`final_decision.${key} must be false, got: ${val}`);
        }
    }
    for (const field of REQUIRED_DRAFT_FIELDS) {
        if (draftData[field] === undefined) {
            errors.push(`required field missing from draft template: ${field}`);
        }
    }
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

async function querySelectOnly(client, sql) {
    assertSelectOnlySql(sql);
    return client.query(sql);
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

function validateAndParseDraft(inputs) {
    const errors = [];
    let draftData = null;
    try {
        draftData = parseDraftTemplate(inputs.draftTemplateMarkdown);
    } catch (err) {
        errors.push(`draft template parse failed: ${err.message}`);
    }
    if (draftData) {
        errors.push(...validateDraftTemplateStructure(draftData));
    } else {
        errors.push('draft template could not be parsed');
    }
    return { draftData, errors };
}

function resolveDraftInputs(args, dependencies) {
    const {
        cwd = process.cwd(),
        existsSync: se = fs.existsSync.bind(fs),
        readFileSync: sr = fs.readFileSync.bind(fs),
    } = dependencies;
    if (!validateRequiredArgs(args)) {
        return { earlyPayload: buildFailurePayload(args, { errors: [MISSING_ARGS_MESSAGE] }) };
    }
    if (args.commit) {
        return { earlyPayload: buildBlockedCommitPayload(args) };
    }
    const pathContext = buildPathContext(args, cwd, se);
    const missingPayload = buildMissingPathPayload(args, pathContext);
    if (missingPayload) {
        return { earlyPayload: missingPayload };
    }
    try {
        const inputs = readAllInputs(pathContext, sr);
        return { pathContext, inputs, errors: validateAndParseDraft(inputs).errors, sr };
    } catch (err) {
        return {
            earlyPayload: buildFailurePayload(args, {
                draft_template_found: pathContext.draftTemplateFound,
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

async function runAllGates(args, inputs, dependencies, sr) {
    const warnings = [];
    const gates = {
        authValidationPassed: false,
        packetPreviewPassed: false,
        preflightPassed: false,
        authReviewPassed: false,
        readinessReviewPassed: false,
        dbReadOk: false,
        dbCounts: null,
    };

    try {
        const r = runValidation(inputs.authFormMarkdown, sr);
        gates.authValidationPassed = r && r.ok;
    } catch (e) {
        warnings.push(`auth validation threw: ${e.message}`);
    }
    try {
        const r = await runPacketAssembly(
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
        gates.packetPreviewPassed = r && r.ok;
    } catch (e) {
        warnings.push(`packet preview threw: ${e.message}`);
    }
    try {
        const r = await runPacketFilePreflight(
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
        gates.preflightPassed = r && r.ok;
    } catch (e) {
        warnings.push(`preflight threw: ${e.message}`);
    }
    try {
        const r = await runAuthorizationReview(
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
        gates.authReviewPassed = r && r.ok;
    } catch (e) {
        warnings.push(`auth review threw: ${e.message}`);
    }
    try {
        const r = await runReadinessReview(
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
        gates.readinessReviewPassed = r && r.readiness_review_completed;
    } catch (e) {
        warnings.push(`readiness review threw: ${e.message}`);
    }
    try {
        const r = await withDbClient(dependencies, async c => (await querySelectOnly(c, CURRENT_DB_COUNTS_SQL)).rows);
        gates.dbCounts = mapCurrentDbCounts(r);
        gates.dbReadOk = true;
    } catch (e) {
        warnings.push(`SELECT-only DB read failed: ${e.message}`);
    }

    return { gates, warnings };
}

function buildDraftPayload(args, pathContext, gates, errors, warnings) {
    return {
        phase: AUTH_PACKET_DRAFT_PHASE,
        mode: 'football-data-packet-file-auth-packet-draft',
        ok: errors.length === 0,
        draft_template: args.draftTemplate || null,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,

        draft_template_found: pathContext.draftTemplateFound,
        readiness_checklist_found: pathContext.readinessChecklistFound,
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,

        readiness_review_passed: gates.readinessReviewPassed,
        auth_review_passed: gates.authReviewPassed,
        auth_validation_passed: gates.authValidationPassed,
        packet_file_preflight_passed: gates.preflightPassed,
        packet_preview_passed: gates.packetPreviewPassed,
        select_only_db_reads: gates.dbReadOk,

        draft_review_completed: true,
        draft_status: 'draft_only',
        ready_for_human_review: false,
        ready_for_packet_file_creation: false,
        authorized_for_packet_file_creation: false,
        packet_file_creation_ready: false,
        packet_file_creation_authorized: false,
        readiness_status: 'not_ready',
        authorization_status: 'not_authorized',
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

        authorization_packet_draft_sections: AUTHORIZATION_PACKET_DRAFT_SECTIONS,
        missing_draft_requirements: MISSING_DRAFT_REQUIREMENTS,
        permission_separation: PERMISSION_SEPARATION,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,

        current_db_counts: gates.dbCounts,
        errors,
        warnings,
    };
}

async function runDraftReview(args, dependencies = {}) {
    const resolved = resolveDraftInputs(args, dependencies);
    if (resolved.earlyPayload) return resolved.earlyPayload;

    const { pathContext, inputs, errors, sr } = resolved;
    const { gates, warnings } = await runAllGates(args, inputs, dependencies, sr);
    return buildDraftPayload(args, pathContext, gates, errors, warnings);
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

    const result = await runDraftReview(args);

    if (result.errors && result.errors.length > 0) {
        console.error('ERROR:', result.errors.join('\n'));
    }
    if (result.warnings && result.warnings.length > 0) {
        console.error('WARN:', result.warnings.join('\n'));
    }

    if (args.json) {
        console.log(JSON.stringify(result, null, 2));
    } else {
        const lines = [
            `phase=${result.phase}`,
            `draft_template_found=${result.draft_template_found}`,
            `readiness_checklist_found=${result.readiness_checklist_found}`,
            `auth_form_found=${result.auth_form_found}`,
            `source_manifest_found=${result.source_manifest_found}`,
            `local_csv_found=${result.local_csv_found}`,
            `approval_form_found=${result.approval_form_found}`,
            `runbook_template_found=${result.runbook_template_found}`,
            '',
            `readiness_review_passed=${result.readiness_review_passed}`,
            `auth_review_passed=${result.auth_review_passed}`,
            `auth_validation_passed=${result.auth_validation_passed}`,
            `packet_file_preflight_passed=${result.packet_file_preflight_passed}`,
            `packet_preview_passed=${result.packet_preview_passed}`,
            `select_only_db_reads=${result.select_only_db_reads}`,
            '',
            `draft_review_completed=${result.draft_review_completed}`,
            `draft_status=${result.draft_status}`,
            `ready_for_human_review=${result.ready_for_human_review}`,
            `ready_for_packet_file_creation=${result.ready_for_packet_file_creation}`,
            `authorized_for_packet_file_creation=${result.authorized_for_packet_file_creation}`,
            `packet_file_creation_ready=${result.packet_file_creation_ready}`,
            `packet_file_creation_authorized=${result.packet_file_creation_authorized}`,
            `readiness_status=${result.readiness_status}`,
            `authorization_status=${result.authorization_status}`,
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
            'authorization_packet_draft_sections:',
            ...result.authorization_packet_draft_sections.map(s => `- ${s}`),
            '',
            'missing_draft_requirements:',
            ...result.missing_draft_requirements.map(s => `- ${s}`),
            '',
            'permission_separation:',
            ...result.permission_separation.map(s => `- ${s}`),
            '',
            'non_execution_confirmations:',
            ...result.non_execution_confirmations.map(s => `- ${s}`),
        ];
        if (result.current_db_counts) {
            lines.push('', 'current_db_counts:');
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
    runDraftReview,
    parseDraftTemplate,
    validateDraftTemplateStructure,
    validateRequiredArgs,
    buildPathContext,
    parseArgs,
    buildFailurePayload,
    buildBlockedCommitPayload,
    MISSING_ARGS_MESSAGE,
    BLOCKED_COMMIT_MESSAGE,
    AUTH_PACKET_DRAFT_PHASE,
    DRAFT_TEMPLATE_PHASE,
    AUTHORIZATION_PACKET_DRAFT_SECTIONS,
    MISSING_DRAFT_REQUIREMENTS,
    PERMISSION_SEPARATION,
    NON_EXECUTION_CONFIRMATIONS,
    REQUIRED_DRAFT_FIELDS,
    CURRENT_DB_TABLES,
    CURRENT_DB_COUNTS_SQL,
    mapCurrentDbCounts,
};
