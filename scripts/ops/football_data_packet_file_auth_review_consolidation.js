#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.75C auth review consolidation in one audit-friendly file. */

const fs = require('fs');
const path = require('path');

const { runValidation, extractYamlBlock, parseYamlBlock } = require('./football_data_packet_file_auth_validate');
const { runPacketFilePreflight } = require('./football_data_packet_file_preflight');
const { runPacketAssembly } = require('./football_data_small_write_packet_assembly');
const { runAuthorizationReview } = require('./football_data_packet_file_auth_review');
const { runReadinessReview } = require('./football_data_packet_file_readiness_review');
const { runDraftReview } = require('./football_data_packet_file_auth_packet_draft');
const { buildDbConfig, assertSelectOnlySql } = require('./football_data_duplicate_precheck');

const CONSOLIDATION_PHASE = 'PHASE4.75C_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION';
const CONSOLIDATION_TEMPLATE_PHASE = 'PHASE4_PACKET_FILE_CREATION_AUTH_REVIEW_CONSOLIDATION';
const MISSING_ARGS_MESSAGE =
    'ERROR: provide --consolidation-template=<path>, --draft-template=<path>, --readiness-checklist=<path>, --auth-form=<path>, --source-manifest=<path>, --local-csv=<path>, --approval-form=<path>, and --runbook-template=<path>';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: football-data packet file authorization review consolidation commit is not wired in Phase 4.75C.';

const CURRENT_DB_TABLES = [
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
];

const CURRENT_DB_COUNTS_SQL = `
SELECT table_name, rows FROM (
    SELECT 'matches' AS table_name, COUNT(*)::bigint AS rows, 1 AS sort_order FROM matches
    UNION ALL SELECT 'bookmaker_odds_history', COUNT(*)::bigint, 2 FROM bookmaker_odds_history
    UNION ALL SELECT 'raw_match_data', COUNT(*)::bigint, 3 FROM raw_match_data
    UNION ALL SELECT 'l3_features', COUNT(*)::bigint, 4 FROM l3_features
    UNION ALL SELECT 'match_features_training', COUNT(*)::bigint, 5 FROM match_features_training
    UNION ALL SELECT 'predictions', COUNT(*)::bigint, 6 FROM predictions
) counts ORDER BY sort_order
`;

const CONSOLIDATED_REVIEW_SECTIONS = [
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
    'missing_draft_requirements',
    'permission_separation',
    'final_human_decision_required',
];

const CONSOLIDATED_BLOCKING_REASONS = [
    'consolidation_status is draft_review_only',
    'draft_status is draft_only',
    'readiness_status is not_ready',
    'authorization_status is not_authorized',
    'ready_for_packet_file_creation is false',
    'authorized_for_packet_file_creation is false',
    'final_packet_creation_confirmation is false',
    'human-only fields remain empty',
    'packet path fields remain template-only',
    'packet file creation is not authorized in this phase',
];

const PERMISSION_SEPARATION = [
    'review consolidation does not authorize packet file creation',
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

const REQUIRED_CONSOLIDATION_FIELDS = [
    'phase',
    'consolidation_status',
    'draft_status',
    'readiness_status',
    'authorization_status',
    'ready_for_human_review',
    'ready_for_packet_file_creation',
    'authorized_for_packet_file_creation',
    'final_packet_creation_confirmation',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_auth_review_consolidation.js --consolidation-template <path> --draft-template <path> --readiness-checklist <path> --auth-form <path> --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path>',
        '',
        'Safety: Phase 4.75C review consolidation only. No writes, no pg_dump, no network.',
    ].join('\n');
}

function parseArgs(argv) {
    const valueOpts = [
        '--consolidation-template',
        '--draft-template',
        '--readiness-checklist',
        '--auth-form',
        '--source-manifest',
        '--local-csv',
        '--approval-form',
        '--runbook-template',
    ];
    const valueKeyMap = {
        '--consolidation-template': 'consolidationTemplate',
        '--draft-template': 'draftTemplate',
        '--readiness-checklist': 'readinessChecklist',
        '--auth-form': 'authForm',
        '--source-manifest': 'sourceManifest',
        '--local-csv': 'localCsv',
        '--approval-form': 'approvalForm',
        '--runbook-template': 'runbookTemplate',
    };
    const flags = ['--commit', '--json', '--help', '-h'];
    const flagKeyMap = { '--commit': 'commit', '--json': 'json', '--help': 'help', '-h': 'help' };
    const args = {};
    for (const k of Object.values(valueKeyMap)) args[k] = '';
    for (const k of Object.values(flagKeyMap)) args[k] = false;

    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];
        const matched = valueOpts.find(o => token === o || token.startsWith(`${o}=`));
        if (matched) {
            const key = valueKeyMap[matched];
            args[key] = token === matched ? String(argv[i + 1] || '') : token.slice(`${matched}=`.length);
            if (token === matched) i += 1;
            continue;
        }
        if (flags.includes(token)) {
            args[flagKeyMap[token]] = true;
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

function toRelativePath(absPath, cwd = process.cwd()) {
    if (!absPath) return '';
    return path.relative(cwd, absPath) || '.';
}

function validateRequiredArgs(args) {
    return Boolean(
        args.consolidationTemplate &&
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
    const paths = [
        'consolidationTemplate',
        'draftTemplate',
        'readinessChecklist',
        'authForm',
        'sourceManifest',
        'localCsv',
        'approvalForm',
        'runbookTemplate',
    ];
    const ctx = { cwd };
    for (const p of paths) {
        const key = p + 'Path';
        ctx[key] = resolveLocalPath(args[p], cwd);
        ctx[p + 'Found'] = existsSync(ctx[key]);
    }
    return ctx;
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: CONSOLIDATION_PHASE,
        mode: fields.mode || 'consolidation-review',
        ok: false,
        consolidation_template: args.consolidationTemplate || null,
        draft_template: args.draftTemplate || null,
        readiness_checklist: args.readinessChecklist || null,
        auth_form: args.authForm || null,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        consolidation_template_found: false,
        draft_template_found: false,
        readiness_checklist_found: false,
        auth_form_found: false,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        auth_packet_draft_review_passed: false,
        readiness_review_passed: false,
        auth_review_passed: false,
        auth_validation_passed: false,
        packet_file_preflight_passed: false,
        packet_preview_passed: false,
        select_only_db_reads: false,
        consolidation_review_completed: false,
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
        consolidated_review_sections: CONSOLIDATED_REVIEW_SECTIONS,
        consolidated_blocking_reasons: CONSOLIDATED_BLOCKING_REASONS,
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
        'consolidationTemplate',
        'draftTemplate',
        'readinessChecklist',
        'authForm',
        'sourceManifest',
        'localCsv',
        'approvalForm',
        'runbookTemplate',
    ];
    for (const f of fields) {
        if (!pathContext[f + 'Found']) {
            return buildFailurePayload(args, {
                mode: f + '-error',
                errors: [
                    `${f
                        .replace(/([A-Z])/g, ' $1')
                        .trim()
                        .toLowerCase()} not found: ${toRelativePath(pathContext[f + 'Path'], pathContext.cwd)}`,
                ],
            });
        }
    }
    return null;
}

function readAllInputs(pathContext, readFileSync) {
    return {
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

function parseConsolidationTemplate(markdown) {
    const yaml = extractYamlBlock(markdown);
    if (!yaml) throw new Error('YAML fenced block not found in consolidation template');
    return parseYamlBlock(yaml);
}

function validateConsolidation(data) {
    const errors = [];
    if (!data || typeof data !== 'object') {
        errors.push('not a valid object');
        return errors;
    }
    if (data.phase !== CONSOLIDATION_TEMPLATE_PHASE) {
        errors.push(`phase must be ${CONSOLIDATION_TEMPLATE_PHASE}, got: ${data.phase}`);
    }
    if (data.consolidation_status !== 'draft_review_only') {
        errors.push(`consolidation_status must be draft_review_only, got: ${data.consolidation_status}`);
    }
    if (data.draft_status !== 'draft_only') {
        errors.push(`draft_status must be draft_only, got: ${data.draft_status}`);
    }
    if (data.readiness_status !== 'not_ready') {
        errors.push(`readiness_status must be not_ready, got: ${data.readiness_status}`);
    }
    for (const k of [
        'consolidation_ready_for_human_review',
        'packet_file_creation_ready',
        'packet_file_creation_authorized',
    ]) {
        const v = (data.final_decision || {})[k];
        if (v !== false && v !== undefined) errors.push(`final_decision.${k} must be false`);
    }
    for (const field of REQUIRED_CONSOLIDATION_FIELDS) {
        if (data[field] === undefined) errors.push(`required field missing: ${field}`);
    }
    return errors;
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function withDbClient(dependencies, cb) {
    if (dependencies.dbClient) return cb(dependencies.dbClient);
    const pool = dependencies.pool || (dependencies.createPool || createPool)();
    const client = await pool.connect();
    try {
        return await cb(client);
    } finally {
        client.release();
        if (!dependencies.pool && typeof pool.end === 'function') await pool.end();
    }
}

async function querySelectOnly(client, sql) {
    assertSelectOnlySql(sql);
    return client.query(sql);
}

function mapDbCounts(rows) {
    const m = {};
    for (const t of CURRENT_DB_TABLES) m[t] = 0;
    for (const r of rows || []) m[r.table_name] = Number.parseInt(r.rows, 10);
    return m;
}

async function runAllGates(args, inputs, dependencies, sr) {
    const gates = {};
    // Draft review (Phase 4.74C)
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
    } catch (e) {
        /* continue */
    }
    // Auth validation
    try {
        gates.authVal = runValidation(inputs.authFormMarkdown, sr);
    } catch (e) {
        /* continue */
    }
    // Packet preview
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
    } catch (e) {
        /* continue */
    }
    // Preflight
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
    } catch (e) {
        /* continue */
    }
    // Auth review
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
    } catch (e) {
        /* continue */
    }
    // Readiness review
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
    } catch (e) {
        /* continue */
    }
    // DB counts
    try {
        gates.dbRows = await withDbClient(
            dependencies,
            async c => (await querySelectOnly(c, CURRENT_DB_COUNTS_SQL)).rows
        );
    } catch (e) {
        /* continue */
    }
    return gates;
}

async function runConsolidationReview(args, dependencies = {}) {
    const {
        cwd = process.cwd(),
        existsSync: se = fs.existsSync.bind(fs),
        readFileSync: sr = fs.readFileSync.bind(fs),
    } = dependencies;

    if (!validateRequiredArgs(args)) return buildFailurePayload(args, { errors: [MISSING_ARGS_MESSAGE] });
    if (args.commit) return buildBlockedCommitPayload(args);

    const pathContext = buildPathContext(args, cwd, se);
    const missing = buildMissingPathPayload(args, pathContext);
    if (missing) return missing;

    let inputs;
    try {
        inputs = readAllInputs(pathContext, sr);
    } catch (err) {
        return buildFailurePayload(args, { errors: [`failed to read input files: ${err.message}`] });
    }

    const errors = [];
    try {
        const d = parseConsolidationTemplate(inputs.consolidationMarkdown);
        errors.push(...validateConsolidation(d));
    } catch (e) {
        errors.push(`consolidation template parse failed: ${e.message}`);
    }

    const gates = await runAllGates(args, inputs, dependencies, sr);

    return {
        phase: CONSOLIDATION_PHASE,
        mode: 'consolidation-review',
        ok: errors.length === 0,
        consolidation_template: args.consolidationTemplate,
        draft_template: args.draftTemplate,
        readiness_checklist: args.readinessChecklist,
        auth_form: args.authForm,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        approval_form: args.approvalForm,
        runbook_template: args.runbookTemplate,
        consolidation_template_found: pathContext.consolidationTemplateFound,
        draft_template_found: pathContext.draftTemplateFound,
        readiness_checklist_found: pathContext.readinessChecklistFound,
        auth_form_found: pathContext.authFormFound,
        source_manifest_found: pathContext.sourceManifestFound,
        local_csv_found: pathContext.localCsvFound,
        approval_form_found: pathContext.approvalFormFound,
        runbook_template_found: pathContext.runbookTemplateFound,
        auth_packet_draft_review_passed: gates.draft && gates.draft.draft_review_completed,
        readiness_review_passed: gates.readiness && gates.readiness.readiness_review_completed,
        auth_review_passed: gates.authReview && gates.authReview.ok,
        auth_validation_passed: gates.authVal && gates.authVal.ok,
        packet_file_preflight_passed: gates.preflight && gates.preflight.ok,
        packet_preview_passed: gates.preview && gates.preview.ok,
        select_only_db_reads: !!gates.dbRows,
        consolidation_review_completed: true,
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
        consolidated_review_sections: CONSOLIDATED_REVIEW_SECTIONS,
        consolidated_blocking_reasons: CONSOLIDATED_BLOCKING_REASONS,
        permission_separation: PERMISSION_SEPARATION,
        non_execution_confirmations: NON_EXECUTION_CONFIRMATIONS,
        current_db_counts: gates.dbRows ? mapDbCounts(gates.dbRows) : null,
        errors,
        warnings: [],
    };
}

async function main(argv = process.argv.slice(2)) {
    let args;
    try {
        args = parseArgs(argv);
    } catch (e) {
        console.error(`ERROR: ${e.message}`);
        console.error(usage());
        process.exitCode = 1;
        return;
    }
    if (args.help) {
        console.error(usage());
        return;
    }

    const result = await runConsolidationReview(args);

    if (result.errors.length) console.error('ERROR:', result.errors.join('\n'));
    if (result.warnings.length) console.error('WARN:', result.warnings.join('\n'));

    if (args.json) {
        console.log(JSON.stringify(result, null, 2));
    } else {
        const lines = [
            `phase=${result.phase}`,
            `consolidation_template_found=${result.consolidation_template_found}`,
            `draft_template_found=${result.draft_template_found}`,
            `readiness_checklist_found=${result.readiness_checklist_found}`,
            `auth_form_found=${result.auth_form_found}`,
            `source_manifest_found=${result.source_manifest_found}`,
            `local_csv_found=${result.local_csv_found}`,
            `approval_form_found=${result.approval_form_found}`,
            `runbook_template_found=${result.runbook_template_found}`,
            '',
            `auth_packet_draft_review_passed=${result.auth_packet_draft_review_passed}`,
            `readiness_review_passed=${result.readiness_review_passed}`,
            `auth_review_passed=${result.auth_review_passed}`,
            `auth_validation_passed=${result.auth_validation_passed}`,
            `packet_file_preflight_passed=${result.packet_file_preflight_passed}`,
            `packet_preview_passed=${result.packet_preview_passed}`,
            `select_only_db_reads=${result.select_only_db_reads}`,
            '',
            `consolidation_review_completed=${result.consolidation_review_completed}`,
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
            `would_write_db=${result.would_write_db}`,
            `commit_gate=${result.commit_gate}`,
            '',
            'consolidated_review_sections:',
            ...result.consolidated_review_sections.map(s => `- ${s}`),
            '',
            'consolidated_blocking_reasons:',
            ...result.consolidated_blocking_reasons.map(s => `- ${s}`),
            '',
            'permission_separation:',
            ...result.permission_separation.map(s => `- ${s}`),
            '',
            'non_execution_confirmations:',
            ...result.non_execution_confirmations.map(s => `- ${s}`),
        ];
        if (result.current_db_counts) {
            lines.push('', 'current_db_counts:');
            for (const [t, c] of Object.entries(result.current_db_counts)) lines.push(`  ${t}=${c}`);
        }
        console.log(lines.join('\n'));
    }
    if (!result.ok) process.exitCode = 1;
}

if (require.main === module) {
    main().catch(e => {
        console.error('FATAL:', e.message);
        process.exitCode = 1;
    });
}

module.exports = {
    runConsolidationReview,
    parseConsolidationTemplate,
    validateConsolidation,
    validateRequiredArgs,
    buildPathContext,
    parseArgs,
    buildFailurePayload,
    buildBlockedCommitPayload,
    MISSING_ARGS_MESSAGE,
    BLOCKED_COMMIT_MESSAGE,
    CONSOLIDATION_PHASE,
    CONSOLIDATION_TEMPLATE_PHASE,
    CONSOLIDATED_REVIEW_SECTIONS,
    CONSOLIDATED_BLOCKING_REASONS,
    PERMISSION_SEPARATION,
    NON_EXECUTION_CONFIRMATIONS,
    CURRENT_DB_TABLES,
    CURRENT_DB_COUNTS_SQL,
    mapDbCounts,
};
