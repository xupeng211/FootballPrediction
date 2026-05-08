#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines -- Phase 4.70C keeps the packet file preflight contract in one audit-focused script. */

const path = require('path');

const {
    PACKET_SECTIONS,
    MISSING_ARGS_MESSAGE,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    assertSelectOnlySql,
    parseArgs: parsePacketArgs,
    runPacketAssembly,
} = require('./football_data_small_write_packet_assembly');

const PACKET_FILE_PREFLIGHT_PHASE = 'PHASE4.70C_FOOTBALL_DATA_PACKET_FILE_PREFLIGHT';
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: football-data packet file generation is not wired in Phase 4.70C.';
const APPROVED_PACKET_ROOT = 'docs/_packets/football_data/small_write';
const FUTURE_PACKET_METADATA_FIELDS = [
    'packet_version',
    'source_manifest_path',
    'local_csv_path',
    'approval_form_path',
    'runbook_template_path',
    'source_sha256',
    'row_count',
    'proposed_match_ids',
    'insert_candidate_count',
    'blocked_candidate_count',
    'manual_review_count',
    'db_counts_before_preview',
    'pg_dump_command_preview',
    'post_write_validation_checklist',
    'rollback_restore_preview',
    'generated_at_preview_only',
    'generated_by_preview_only',
];
const REQUIRED_PACKET_SECTION_FIELDS = [
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
const DIRECTORY_TIMESTAMP_PREVIEW = '<timestamp>';
const GENERATED_AT_PREVIEW_ONLY = '<generated_at_preview_only>';
const GENERATED_BY_PREVIEW_ONLY = '<generated_by_preview_only>';

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_preflight.js --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> [--json]',
        '  node scripts/ops/football_data_packet_file_preflight.js --source-manifest <path> --local-csv <path> --approval-form <path> --runbook-template <path> --commit',
        '',
        'Safety:',
        '  Phase 4.70C previews future packet file generation only.',
        '  No packet directory creation, no packet file writes, no DB writes, no pg_dump, no pg_restore.',
    ].join('\n');
}

function parseArgs(argv) {
    return parsePacketArgs(argv);
}

function toRelativePath(rawPath, cwd = process.cwd()) {
    if (!rawPath) {
        return null;
    }
    const absolutePath = path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
    return path.relative(cwd, absolutePath) || '.';
}

function slugToken(value, fallback = 'source') {
    const normalized = String(value || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
    return normalized || fallback;
}

function hash8(value) {
    const compact = String(value || '')
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '');
    return `${compact}preview00`.slice(0, 8);
}

function buildNonExecutionConfirmations() {
    return [
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
}

function buildFutureRealPacketFileRequirements() {
    return [
        'user must explicitly authorize packet file creation',
        'output directory must be explicit',
        'packet path must be inside approved docs/_packets/football_data/small_write',
        'packet file must include source manifest hash',
        'packet file must include proposed_match_ids',
        'packet file must exclude manual_review and invalid candidates',
        'approval form must be copied from template into real reviewed file',
        'approval_status must be changed only by human',
        'final_human_confirmation must be set only by human',
        'packet file creation does not authorize DB write',
        'pg_dump and DB write require later separate authorization',
    ];
}

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        packet_file_generation_allowed: false,
        packet_write_allowed: false,
        db_write_allowed: false,
        small_write_authorized: false,
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
        phase: PACKET_FILE_PREFLIGHT_PHASE,
        mode: fields.mode || 'football-data-packet-file-preflight',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        approval_form: args.approvalForm || null,
        runbook_template: args.runbookTemplate || null,
        source_manifest_found: false,
        local_csv_found: false,
        approval_form_found: false,
        runbook_template_found: false,
        packet_preview_passed: false,
        approval_form_validation_passed: false,
        approval_status: null,
        final_human_confirmation: null,
        packet_sections: PACKET_SECTIONS,
        packet_sections_complete: false,
        packet_sections_missing: PACKET_SECTIONS,
        future_packet_directory_preview: null,
        future_packet_file_preview: null,
        future_packet_manifest_preview: null,
        future_packet_metadata: null,
        commit_gate: 'blocked',
        pg_dump_command_preview: null,
        pg_restore_command_preview: null,
        post_write_validation_checklist: [],
        rollback_restore_preview: [],
        non_execution_confirmations: buildNonExecutionConfirmations(),
        future_real_packet_file_requirements: buildFutureRealPacketFileRequirements(),
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

function resolveSourceSha(packetPayload) {
    return (
        packetPayload.source_manifest_summary?.sha256 ||
        packetPayload.local_csv_summary?.actual_sha256 ||
        packetPayload.local_csv_summary?.expected_sha256 ||
        ''
    );
}

function resolveSourceSlug(args, packetPayload) {
    const sourceName =
        packetPayload.source_manifest_summary?.source_name ||
        packetPayload.csv_dry_run_summary?.source_name ||
        packetPayload.source_manifest_summary?.source_type ||
        path.basename(String(args.sourceManifest || ''), path.extname(String(args.sourceManifest || '')));
    return slugToken(sourceName, 'source');
}

function validatePacketSections(packetPayload) {
    const packetSections = Array.isArray(packetPayload.packet_sections) ? packetPayload.packet_sections : [];
    const missingNamedSections = PACKET_SECTIONS.filter(section => !packetSections.includes(section));
    const missingMaterializedFields = REQUIRED_PACKET_SECTION_FIELDS.filter(
        fieldName => !Object.prototype.hasOwnProperty.call(packetPayload, fieldName)
    );
    return [...new Set([...missingNamedSections, ...missingMaterializedFields])];
}

function buildFuturePacketPreviews(args, packetPayload) {
    const sourceSlug = resolveSourceSlug(args, packetPayload);
    const sourceHash8 = hash8(resolveSourceSha(packetPayload));

    return {
        sourceSlug,
        sourceHash8,
        future_packet_directory_preview: `${APPROVED_PACKET_ROOT}/${DIRECTORY_TIMESTAMP_PREVIEW}_${sourceSlug}/`,
        future_packet_file_preview: `football_data_small_write_packet_${sourceSlug}_${sourceHash8}.json`,
        future_packet_manifest_preview: `football_data_small_write_packet_manifest_${sourceSlug}_${sourceHash8}.json`,
    };
}

function buildFuturePacketMetadata(args, packetPayload, previewInfo, cwd = process.cwd()) {
    return {
        packet_version: PACKET_FILE_PREFLIGHT_PHASE,
        source_manifest_path: toRelativePath(args.sourceManifest, cwd),
        local_csv_path: toRelativePath(args.localCsv, cwd),
        approval_form_path: toRelativePath(args.approvalForm, cwd),
        runbook_template_path: toRelativePath(args.runbookTemplate, cwd),
        source_sha256: resolveSourceSha(packetPayload) || null,
        row_count:
            packetPayload.local_csv_summary?.actual_row_count ??
            packetPayload.local_csv_summary?.expected_row_count ??
            packetPayload.source_manifest_summary?.row_count ??
            null,
        proposed_match_ids: packetPayload.proposed_match_ids || [],
        insert_candidate_count: (packetPayload.insert_candidate_table || []).length,
        blocked_candidate_count: (packetPayload.blocked_candidate_table || []).length,
        manual_review_count: (packetPayload.manual_review_table || []).length,
        db_counts_before_preview: packetPayload.current_db_counts || null,
        pg_dump_command_preview: packetPayload.pg_dump_command_preview || null,
        post_write_validation_checklist: packetPayload.post_write_validation_checklist || [],
        rollback_restore_preview: packetPayload.rollback_restore_preview || [],
        generated_at_preview_only: GENERATED_AT_PREVIEW_ONLY,
        generated_by_preview_only: GENERATED_BY_PREVIEW_ONLY,
    };
}

function buildSuccessPayload(args, packetPayload, cwd = process.cwd()) {
    const previewInfo = buildFuturePacketPreviews(args, packetPayload);
    const missingSections = validatePacketSections(packetPayload);
    const futurePacketMetadata = buildFuturePacketMetadata(args, packetPayload, previewInfo, cwd);

    return {
        phase: PACKET_FILE_PREFLIGHT_PHASE,
        mode: 'football-data-packet-file-preflight',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        approval_form: args.approvalForm,
        runbook_template: args.runbookTemplate,
        source_manifest_found: packetPayload.source_manifest_found,
        local_csv_found: packetPayload.local_csv_found,
        approval_form_found: packetPayload.approval_form_found,
        runbook_template_found: packetPayload.runbook_template_found,
        packet_preview_passed: true,
        approval_form_validation_passed: packetPayload.approval_form_validation_passed,
        approval_status: packetPayload.approval_status,
        final_human_confirmation: packetPayload.final_human_confirmation,
        packet_sections: packetPayload.packet_sections,
        packet_sections_complete: missingSections.length === 0,
        packet_sections_missing: missingSections,
        future_packet_directory_preview: previewInfo.future_packet_directory_preview,
        future_packet_file_preview: previewInfo.future_packet_file_preview,
        future_packet_manifest_preview: previewInfo.future_packet_manifest_preview,
        future_packet_metadata: futurePacketMetadata,
        commit_gate: 'blocked',
        pg_dump_command_preview: packetPayload.pg_dump_command_preview || null,
        pg_restore_command_preview: packetPayload.pg_restore_command_preview || null,
        post_write_validation_checklist: packetPayload.post_write_validation_checklist || [],
        rollback_restore_preview: packetPayload.rollback_restore_preview || [],
        current_db_counts: packetPayload.current_db_counts || null,
        packet_preview_phase: packetPayload.phase,
        packet_preview_mode: packetPayload.mode,
        proposed_match_ids: packetPayload.proposed_match_ids || [],
        insert_candidate_count: (packetPayload.insert_candidate_table || []).length,
        blocked_candidate_count: (packetPayload.blocked_candidate_table || []).length,
        manual_review_count: (packetPayload.manual_review_table || []).length,
        ...buildSafetyFlags(),
        approval_form_is_template: packetPayload.approval_form_is_template,
        approval_granted: false,
        non_execution_confirmations: buildNonExecutionConfirmations(),
        future_real_packet_file_requirements: buildFutureRealPacketFileRequirements(),
        warnings: packetPayload.warnings || [],
        errors: [],
    };
}

function buildPacketPreviewFailure(args, packetPayload) {
    return buildFailurePayload(args, {
        mode: 'packet-preview-failed',
        source_manifest_found: packetPayload.source_manifest_found,
        local_csv_found: packetPayload.local_csv_found,
        approval_form_found: packetPayload.approval_form_found,
        runbook_template_found: packetPayload.runbook_template_found,
        approval_form_validation_passed: packetPayload.approval_form_validation_passed || false,
        approval_status: packetPayload.approval_status ?? null,
        final_human_confirmation: packetPayload.final_human_confirmation ?? null,
        packet_preview_failure_mode: packetPayload.mode || null,
        select_only_db_reads: Boolean(packetPayload.select_only_db_reads),
        warnings: packetPayload.warnings || [],
        errors: packetPayload.errors || ['football-data packet preview failed'],
    });
}

async function runPacketFilePreflight(args, dependencies = {}) {
    if (!args.sourceManifest || !args.localCsv || !args.approvalForm || !args.runbookTemplate) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            errors: [MISSING_ARGS_MESSAGE],
        });
    }

    const packetPayload = await (dependencies.runPacketAssembly || runPacketAssembly)(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
            approvalForm: args.approvalForm,
            runbookTemplate: args.runbookTemplate,
        },
        dependencies.packetPreviewDependencies || {}
    );

    if (!packetPayload.ok) {
        return buildPacketPreviewFailure(args, packetPayload);
    }

    const payload = buildSuccessPayload(args, packetPayload, dependencies.cwd || process.cwd());
    if (!payload.packet_sections_complete) {
        return buildFailurePayload(args, {
            mode: 'packet-section-validation-failed',
            source_manifest_found: packetPayload.source_manifest_found,
            local_csv_found: packetPayload.local_csv_found,
            approval_form_found: packetPayload.approval_form_found,
            runbook_template_found: packetPayload.runbook_template_found,
            packet_preview_passed: true,
            approval_form_validation_passed: packetPayload.approval_form_validation_passed,
            approval_status: packetPayload.approval_status,
            final_human_confirmation: packetPayload.final_human_confirmation,
            select_only_db_reads: Boolean(packetPayload.select_only_db_reads),
            packet_sections: packetPayload.packet_sections,
            packet_sections_complete: false,
            packet_sections_missing: payload.packet_sections_missing,
            future_packet_directory_preview: payload.future_packet_directory_preview,
            future_packet_file_preview: payload.future_packet_file_preview,
            future_packet_manifest_preview: payload.future_packet_manifest_preview,
            future_packet_metadata: payload.future_packet_metadata,
            warnings: packetPayload.warnings || [],
            errors: [
                `packet preview is missing required packet sections: ${payload.packet_sections_missing.join(', ')}`,
            ],
        });
    }

    return payload;
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
    for (const [tableName, rows] of Object.entries(counts)) {
        lines.push(`- ${tableName}=${rows}`);
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
        `packet_preview_passed=${payload.packet_preview_passed}`,
        `approval_form_validation_passed=${payload.approval_form_validation_passed}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        `packet_file_generation_allowed=${payload.packet_file_generation_allowed}`,
        `packet_write_allowed=${payload.packet_write_allowed}`,
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
        `future_packet_directory_preview=${payload.future_packet_directory_preview}`,
        `future_packet_file_preview=${payload.future_packet_file_preview}`,
        `future_packet_manifest_preview=${payload.future_packet_manifest_preview}`,
        `approval_status=${payload.approval_status}`,
        `final_human_confirmation=${payload.final_human_confirmation}`,
        `approval_form_is_template=${payload.approval_form_is_template}`,
        `approval_granted=${payload.approval_granted}`,
        `packet_sections_complete=${payload.packet_sections_complete}`,
    ];

    appendOptionalTextFields(lines, payload);
    appendCurrentDbCounts(lines, payload.current_db_counts);
    appendListSection(lines, 'packet_sections', payload.packet_sections);
    appendListSection(lines, 'packet_sections_missing', payload.packet_sections_missing);
    appendListSection(lines, 'future_packet_metadata', Object.keys(payload.future_packet_metadata || {}));
    appendListSection(lines, 'non_execution_confirmations', payload.non_execution_confirmations);
    appendListSection(lines, 'future_real_packet_file_requirements', payload.future_real_packet_file_requirements);

    if (payload.future_packet_metadata) {
        lines.push(`future_packet_metadata_preview=${JSON.stringify(payload.future_packet_metadata)}`);
    }
    if (payload.pg_dump_command_preview) {
        lines.push(`pg_dump_command_preview=${JSON.stringify(payload.pg_dump_command_preview)}`);
    }
    if (payload.pg_restore_command_preview) {
        lines.push(`pg_restore_command_preview=${JSON.stringify(payload.pg_restore_command_preview)}`);
    }
    if (payload.post_write_validation_checklist) {
        lines.push(`post_write_validation_checklist=${JSON.stringify(payload.post_write_validation_checklist)}`);
    }
    if (payload.rollback_restore_preview) {
        lines.push(`rollback_restore_preview=${JSON.stringify(payload.rollback_restore_preview)}`);
    }
    if (payload.proposed_match_ids) {
        lines.push(`proposed_match_ids=${JSON.stringify(payload.proposed_match_ids)}`);
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

        const payload = await runPacketFilePreflight(args, dependencies);
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
    PACKET_FILE_PREFLIGHT_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    APPROVED_PACKET_ROOT,
    FUTURE_PACKET_METADATA_FIELDS,
    DIRECTORY_TIMESTAMP_PREVIEW,
    GENERATED_AT_PREVIEW_ONLY,
    GENERATED_BY_PREVIEW_ONLY,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    assertSelectOnlySql,
    buildNonExecutionConfirmations,
    buildFutureRealPacketFileRequirements,
    buildFuturePacketPreviews,
    buildFuturePacketMetadata,
    runPacketFilePreflight,
    payloadToText,
    main,
};
