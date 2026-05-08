#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const PACKET_FILE_AUTH_VALIDATE_PHASE = 'PHASE4.71C_FOOTBALL_DATA_PACKET_FILE_AUTH_VALIDATE';
const TEMPLATE_PHASE = 'PHASE4_PACKET_FILE_CREATION_AUTH';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: football-data packet file creation authorization commit is not wired in Phase 4.71C.';
const APPROVED_OUTPUT_ROOT = 'docs/_packets/football_data/small_write';
const REQUIRED_PACKET_SECTIONS = [
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
const REQUIRED_FIELDS = [
    'phase',
    'authorization_status',
    'operator',
    'reviewer',
    'source_manifest',
    'local_csv',
    'approval_form',
    'runbook_template',
    'packet_directory',
    'packet_file',
    'packet_manifest_file',
    'packet_version',
    'source_name',
    'source_sha256',
    'row_count',
    'allow_packet_directory_creation',
    'allow_packet_file_write',
    'allow_packet_manifest_write',
    'allow_db_write',
    'allow_pg_dump',
    'allow_pg_restore',
    'allow_external_network',
    'allow_training',
    'allow_prediction',
    'approved_packet_sections',
    'approved_output_root',
    'approved_candidate_match_ids',
    'excluded_candidate_match_ids',
    'manual_review_candidate_match_ids',
    'packet_creation_reason',
    'human_approval_note',
    'final_packet_creation_confirmation',
];
const REQUIRED_FALSE_FIELDS = [
    'allow_packet_directory_creation',
    'allow_packet_file_write',
    'allow_packet_manifest_write',
    'allow_db_write',
    'allow_pg_dump',
    'allow_pg_restore',
    'allow_external_network',
    'allow_training',
    'allow_prediction',
    'final_packet_creation_confirmation',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_packet_file_auth_validate.js --auth-form <path> [--json]',
        '  node scripts/ops/football_data_packet_file_auth_validate.js --auth-form <path> --commit',
        '',
        'Safety:',
        '  Phase 4.71C validates a local packet file creation authorization template only.',
        '  No DB reads, no DB writes, no file writes, no directory creation, no pg_dump, no pg_restore.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        authForm: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token.startsWith('--auth-form=')) {
            args.authForm = token.slice('--auth-form='.length);
        } else if (token === '--auth-form') {
            args.authForm = String(argv[index + 1] || '');
            index += 1;
        } else if (token === '--commit') {
            args.commit = true;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
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

function normalizeRelativePath(value) {
    return String(value || '')
        .replace(/\\/g, '/')
        .replace(/\/+$/g, '');
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'no_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_packet_directory_create',
        'no_packet_file_write',
        'no_packet_manifest_write',
        'no_pg_dump_execution',
        'no_pg_restore_execution',
        'no_child_process_spawn',
        'no_training',
        'no_prediction_execution',
    ];
}

function buildSafetyFlags() {
    return {
        would_read_db: false,
        would_write_db: false,
        would_write_files: false,
        would_create_packet_directory: false,
        would_write_packet_file: false,
        would_write_packet_manifest: false,
        would_access_network: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_spawn_child_process: false,
        would_train_model: false,
        would_execute_prediction: false,
        authorization_granted: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: PACKET_FILE_AUTH_VALIDATE_PHASE,
        mode: fields.mode || 'football-data-packet-file-auth-validate',
        ok: false,
        auth_form: args.authForm || null,
        auth_form_found: false,
        yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        authorization_status: null,
        final_packet_creation_confirmation: null,
        approved_output_root: null,
        approved_output_root_valid: false,
        approved_packet_sections: [],
        approved_packet_sections_complete: false,
        approved_packet_sections_missing: REQUIRED_PACKET_SECTIONS,
        commit_gate: 'blocked',
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
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

function extractYamlBlock(markdownText) {
    const match = String(markdownText || '').match(/```ya?ml\s*\n([\s\S]*?)\n```/i);
    return match ? match[1] : '';
}

function stripInlineComment(value) {
    const hashIndex = value.indexOf(' #');
    if (hashIndex === -1) {
        return value;
    }
    return value.slice(0, hashIndex);
}

function parseScalar(rawValue) {
    const value = stripInlineComment(String(rawValue || '')).trim();
    if (value === '') {
        return null;
    }
    if (value === 'true') {
        return true;
    }
    if (value === 'false') {
        return false;
    }
    if (value === '[]') {
        return [];
    }
    if (value.startsWith('[') && value.endsWith(']')) {
        const inner = value.slice(1, -1).trim();
        if (!inner) {
            return [];
        }
        return inner.split(',').map(item => parseScalar(item.trim()));
    }
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        return value.slice(1, -1);
    }
    if (/^-?\d+$/.test(value)) {
        return Number(value);
    }
    return value;
}

function parseTopLevelYamlLine(root, trimmed) {
    const match = trimmed.match(/^([A-Za-z0-9_]+):(.*)$/);
    if (!match) {
        throw new Error(`unsupported YAML line: ${trimmed}`);
    }

    const key = match[1];
    const value = match[2].trim();
    root[key] = value === '' ? null : parseScalar(value);
    return key;
}

function parseNestedYamlLine(root, currentKey, trimmed) {
    if (trimmed.startsWith('- ')) {
        if (!Array.isArray(root[currentKey])) {
            root[currentKey] = [];
        }
        root[currentKey].push(parseScalar(trimmed.slice(2)));
        return;
    }

    const nestedMatch = trimmed.match(/^([A-Za-z0-9_]+):(.*)$/);
    if (!nestedMatch) {
        throw new Error(`unsupported YAML line: ${trimmed}`);
    }
    if (!root[currentKey] || Array.isArray(root[currentKey]) || typeof root[currentKey] !== 'object') {
        root[currentKey] = {};
    }
    root[currentKey][nestedMatch[1]] = nestedMatch[2].trim() === '' ? null : parseScalar(nestedMatch[2]);
}

function parseYamlBlock(yamlText) {
    const root = {};
    let currentKey = '';

    for (const rawLine of String(yamlText || '').split(/\r?\n/)) {
        if (!rawLine.trim() || rawLine.trim().startsWith('#')) {
            continue;
        }

        const indent = rawLine.match(/^ */)[0].length;
        const trimmed = rawLine.trim();

        if (indent === 0) {
            currentKey = parseTopLevelYamlLine(root, trimmed);
            continue;
        }

        if (indent >= 2 && currentKey) {
            parseNestedYamlLine(root, currentKey, trimmed);
            continue;
        }

        throw new Error(`unsupported YAML indentation: ${trimmed}`);
    }

    return root;
}

function findMissingFields(parsedYaml) {
    return REQUIRED_FIELDS.filter(field => !Object.prototype.hasOwnProperty.call(parsedYaml, field));
}

function validateApprovedOutputRoot(value) {
    const normalized = normalizeRelativePath(value);
    const normalizedRoot = normalizeRelativePath(APPROVED_OUTPUT_ROOT);
    return normalized === normalizedRoot;
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    const approvedPacketSections = Array.isArray(parsedYaml.approved_packet_sections)
        ? parsedYaml.approved_packet_sections
        : [];
    const missingPacketSections = REQUIRED_PACKET_SECTIONS.filter(section => !approvedPacketSections.includes(section));

    if (missingFields.length > 0) {
        errors.push(`missing required fields: ${missingFields.join(',')}`);
    }
    if (parsedYaml.phase !== TEMPLATE_PHASE) {
        errors.push(`phase must remain ${TEMPLATE_PHASE} in the Phase 4.71C template`);
    }
    if (parsedYaml.authorization_status !== 'not_authorized') {
        errors.push('authorization_status must remain not_authorized in the Phase 4.71C template');
    }
    for (const field of REQUIRED_FALSE_FIELDS) {
        if (parsedYaml[field] !== false) {
            errors.push(`${field} must be false in the Phase 4.71C template`);
        }
    }
    if (!Array.isArray(parsedYaml.approved_packet_sections)) {
        errors.push('approved_packet_sections must be an array');
    }
    if (missingPacketSections.length > 0) {
        errors.push(`approved_packet_sections is missing required sections: ${missingPacketSections.join(', ')}`);
    }
    if (!validateApprovedOutputRoot(parsedYaml.approved_output_root)) {
        errors.push(`approved_output_root must stay inside ${APPROVED_OUTPUT_ROOT}`);
    }

    return {
        ok: errors.length === 0,
        missingFields,
        missingPacketSections,
        errors,
    };
}

function buildSuccessPayload(args, parsedYaml, authFormFound) {
    const validation = validateParsedYaml(parsedYaml);

    return {
        phase: PACKET_FILE_AUTH_VALIDATE_PHASE,
        mode: 'football-data-packet-file-auth-validate',
        ok: true,
        auth_form: args.authForm,
        auth_form_found: authFormFound,
        yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        authorization_status: parsedYaml.authorization_status,
        final_packet_creation_confirmation: parsedYaml.final_packet_creation_confirmation,
        approved_output_root: parsedYaml.approved_output_root,
        approved_output_root_valid: true,
        approved_packet_sections: parsedYaml.approved_packet_sections,
        approved_packet_sections_complete: validation.missingPacketSections.length === 0,
        approved_packet_sections_missing: validation.missingPacketSections,
        allow_packet_directory_creation: parsedYaml.allow_packet_directory_creation,
        allow_packet_file_write: parsedYaml.allow_packet_file_write,
        allow_packet_manifest_write: parsedYaml.allow_packet_manifest_write,
        allow_db_write: parsedYaml.allow_db_write,
        allow_pg_dump: parsedYaml.allow_pg_dump,
        allow_pg_restore: parsedYaml.allow_pg_restore,
        allow_external_network: parsedYaml.allow_external_network,
        allow_training: parsedYaml.allow_training,
        allow_prediction: parsedYaml.allow_prediction,
        commit_gate: 'blocked',
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: [],
        warnings: [],
    };
}

function runValidation(args, dependencies = {}) {
    const cwd = dependencies.cwd || process.cwd();
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readFileSync = dependencies.readFileSync || fs.readFileSync;
    const authFormPath = resolveLocalPath(args.authForm, cwd);

    if (!args.authForm) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            errors: ['ERROR: provide --auth-form=<path>'],
        });
    }

    if (!existsSync(authFormPath)) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            auth_form_found: false,
            errors: [`auth form not found: ${toRelativePath(authFormPath, cwd)}`],
        });
    }

    const markdownText = readFileSync(authFormPath, 'utf8');
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            auth_form_found: true,
            yaml_block_found: false,
            errors: ['YAML fenced block not found'],
        });
    }

    let parsedYaml;
    try {
        parsedYaml = parseYamlBlock(yamlText);
    } catch (error) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            auth_form_found: true,
            yaml_block_found: true,
            errors: [`unable to parse YAML block: ${error.message}`],
        });
    }

    const validation = validateParsedYaml(parsedYaml);
    if (!validation.ok) {
        return buildFailurePayload(args, {
            mode: 'auth-form-error',
            auth_form_found: true,
            yaml_block_found: true,
            required_fields_present: validation.missingFields.length === 0,
            missing_fields: validation.missingFields,
            authorization_status: parsedYaml.authorization_status || null,
            final_packet_creation_confirmation: parsedYaml.final_packet_creation_confirmation ?? null,
            approved_output_root: parsedYaml.approved_output_root || null,
            approved_output_root_valid: validateApprovedOutputRoot(parsedYaml.approved_output_root),
            approved_packet_sections: Array.isArray(parsedYaml.approved_packet_sections)
                ? parsedYaml.approved_packet_sections
                : [],
            approved_packet_sections_complete: validation.missingPacketSections.length === 0,
            approved_packet_sections_missing: validation.missingPacketSections,
            allow_packet_directory_creation: parsedYaml.allow_packet_directory_creation,
            allow_packet_file_write: parsedYaml.allow_packet_file_write,
            allow_packet_manifest_write: parsedYaml.allow_packet_manifest_write,
            allow_db_write: parsedYaml.allow_db_write,
            allow_pg_dump: parsedYaml.allow_pg_dump,
            allow_pg_restore: parsedYaml.allow_pg_restore,
            allow_external_network: parsedYaml.allow_external_network,
            allow_training: parsedYaml.allow_training,
            allow_prediction: parsedYaml.allow_prediction,
            errors: validation.errors,
        });
    }

    return buildSuccessPayload(args, parsedYaml, true);
}

function payloadToText(payload) {
    const lines = [
        `phase=${payload.phase}`,
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `validation_summary=${payload.ok ? 'passed' : 'failed'}`,
        `auth_form_found=${payload.auth_form_found}`,
        `yaml_block_found=${payload.yaml_block_found}`,
        `required_fields_present=${payload.required_fields_present}`,
        `authorization_status=${payload.authorization_status}`,
        `approved_output_root=${payload.approved_output_root}`,
        `approved_output_root_valid=${payload.approved_output_root_valid}`,
        `approved_packet_sections_complete=${payload.approved_packet_sections_complete}`,
        `final_packet_creation_confirmation=${payload.final_packet_creation_confirmation}`,
        `allow_packet_directory_creation=${payload.allow_packet_directory_creation}`,
        `allow_packet_file_write=${payload.allow_packet_file_write}`,
        `allow_packet_manifest_write=${payload.allow_packet_manifest_write}`,
        `allow_db_write=${payload.allow_db_write}`,
        `allow_pg_dump=${payload.allow_pg_dump}`,
        `allow_pg_restore=${payload.allow_pg_restore}`,
        `allow_external_network=${payload.allow_external_network}`,
        `allow_training=${payload.allow_training}`,
        `allow_prediction=${payload.allow_prediction}`,
        `would_read_db=${payload.would_read_db}`,
        `would_write_db=${payload.would_write_db}`,
        `would_write_files=${payload.would_write_files}`,
        `would_create_packet_directory=${payload.would_create_packet_directory}`,
        `would_write_packet_file=${payload.would_write_packet_file}`,
        `would_write_packet_manifest=${payload.would_write_packet_manifest}`,
        `would_access_network=${payload.would_access_network}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_execute_pg_restore=${payload.would_execute_pg_restore}`,
        `would_spawn_child_process=${payload.would_spawn_child_process}`,
        `authorization_granted=${payload.authorization_granted}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (Array.isArray(payload.missing_fields) && payload.missing_fields.length > 0) {
        lines.push(`missing_fields=${payload.missing_fields.join(',')}`);
    }
    if (
        Array.isArray(payload.approved_packet_sections_missing) &&
        payload.approved_packet_sections_missing.length > 0
    ) {
        lines.push(`approved_packet_sections_missing=${payload.approved_packet_sections_missing.join(',')}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
    }
    lines.push('approved_packet_sections=');
    for (const section of payload.approved_packet_sections || []) {
        lines.push(`  ${section}`);
    }
    lines.push('non_execution_confirmations=');
    for (const confirmation of payload.non_execution_confirmations || []) {
        lines.push(`  ${confirmation}`);
    }

    return lines.join('\n');
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function main(argv = process.argv.slice(2), io = {}, dependencies = {}) {
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

        const payload = runValidation(args, dependencies);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const payload = buildFailurePayload(
            {
                authForm: '',
            },
            {
                mode: 'argument-error',
                errors: [error.message],
            }
        );
        writePayload(payload, argv.includes('--json'), output);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    PACKET_FILE_AUTH_VALIDATE_PHASE,
    TEMPLATE_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    APPROVED_OUTPUT_ROOT,
    REQUIRED_FIELDS,
    REQUIRED_FALSE_FIELDS,
    REQUIRED_PACKET_SECTIONS,
    parseArgs,
    extractYamlBlock,
    parseYamlBlock,
    validateParsedYaml,
    runValidation,
    buildNonExecutionConfirmations,
    main,
};
