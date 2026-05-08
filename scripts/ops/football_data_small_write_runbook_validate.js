#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const RUNBOOK_VALIDATE_PHASE = 'PHASE4.68C_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK_VALIDATE';
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: football-data small write runbook commit is not wired in Phase 4.68C.';
const REQUIRED_FIELDS = [
    'phase',
    'approval_status',
    'operator',
    'reviewer',
    'source_manifest',
    'local_csv',
    'source_name',
    'source_url',
    'license_url',
    'terms_url',
    'human_approval_note',
    'max_insert_rows',
    'target_tables',
    'allow_odds_insert',
    'allow_raw_insert',
    'allow_l3_insert',
    'allow_training_features_insert',
    'allow_predictions_insert',
    'allow_training',
    'allow_prediction',
    'require_pg_dump',
    'pg_dump_command_preview',
    'backup_path',
    'approved_candidate_match_ids',
    'excluded_candidate_match_ids',
    'manual_review_candidate_match_ids',
    'expected_before_counts',
    'expected_after_counts',
    'rollback_plan_reviewed',
    'post_write_validation_required',
    'final_human_confirmation',
];
const REQUIRED_COUNT_FIELDS = [
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
];
const REQUIRED_FALSE_FIELDS = [
    'allow_odds_insert',
    'allow_raw_insert',
    'allow_l3_insert',
    'allow_training_features_insert',
    'allow_predictions_insert',
    'allow_training',
    'allow_prediction',
    'final_human_confirmation',
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_small_write_runbook_validate.js --approval-form <path> [--json]',
        '  node scripts/ops/football_data_small_write_runbook_validate.js --approval-form <path> --commit',
        '',
        'Safety:',
        '  Phase 4.68C validates a local approval form template only.',
        '  No DB reads, no DB writes, no pg_dump, no pg_restore, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        approvalForm: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token.startsWith('--approval-form=')) {
            args.approvalForm = token.slice('--approval-form='.length);
        } else if (token === '--approval-form') {
            args.approvalForm = String(argv[index + 1] || '');
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

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'no_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_pg_dump_execution',
        'no_pg_restore_execution',
        'no_child_process_spawn',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
    ];
}

function buildSafetyFlags() {
    return {
        would_read_db: false,
        would_write_db: false,
        would_write_files: false,
        would_access_network: false,
        would_execute_pg_dump: false,
        would_execute_pg_restore: false,
        would_spawn_child_process: false,
        would_train_model: false,
        would_execute_prediction: false,
        would_load_model_artifact: false,
        approval_granted: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: RUNBOOK_VALIDATE_PHASE,
        mode: fields.mode || 'football-data-small-write-runbook-validate',
        ok: false,
        approval_form: args.approvalForm || null,
        approval_form_found: false,
        yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        approval_status: null,
        target_tables: null,
        commit_gate: 'blocked',
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
    const missingFields = REQUIRED_FIELDS.filter(field => !Object.prototype.hasOwnProperty.call(parsedYaml, field));

    for (const parent of ['expected_before_counts', 'expected_after_counts']) {
        if (!parsedYaml[parent] || typeof parsedYaml[parent] !== 'object' || Array.isArray(parsedYaml[parent])) {
            continue;
        }
        for (const field of REQUIRED_COUNT_FIELDS) {
            if (!Object.prototype.hasOwnProperty.call(parsedYaml[parent], field)) {
                missingFields.push(`${parent}.${field}`);
            }
        }
    }

    return missingFields;
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);

    if (missingFields.length > 0) {
        errors.push(`missing required fields: ${missingFields.join(',')}`);
    }
    if (parsedYaml.approval_status !== 'not_approved') {
        errors.push('approval_status must remain not_approved in the Phase 4.68C template');
    }
    if (
        !Array.isArray(parsedYaml.target_tables) ||
        parsedYaml.target_tables.length !== 1 ||
        parsedYaml.target_tables[0] !== 'matches'
    ) {
        errors.push('target_tables must contain only matches in Phase 4.68C');
    }
    for (const field of REQUIRED_FALSE_FIELDS) {
        if (parsedYaml[field] !== false) {
            errors.push(`${field} must be false in the Phase 4.68C template`);
        }
    }
    if (parsedYaml.require_pg_dump !== true) {
        errors.push('require_pg_dump must be true');
    }
    if (parsedYaml.post_write_validation_required !== true) {
        errors.push('post_write_validation_required must be true');
    }

    return {
        ok: errors.length === 0,
        missingFields,
        errors,
    };
}

function buildSuccessPayload(args, parsedYaml, approvalFormFound) {
    return {
        phase: RUNBOOK_VALIDATE_PHASE,
        mode: 'football-data-small-write-runbook-validate',
        ok: true,
        approval_form: args.approvalForm,
        approval_form_found: approvalFormFound,
        yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        approval_status: parsedYaml.approval_status,
        target_tables: parsedYaml.target_tables,
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
    const approvalFormPath = resolveLocalPath(args.approvalForm, cwd);

    if (!args.approvalForm) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            errors: ['ERROR: provide --approval-form=<path>'],
        });
    }

    if (!existsSync(approvalFormPath)) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            approval_form_found: false,
            errors: [`approval form not found: ${toRelativePath(approvalFormPath, cwd)}`],
        });
    }

    const markdownText = readFileSync(approvalFormPath, 'utf8');
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            approval_form_found: true,
            yaml_block_found: false,
            errors: ['YAML fenced block not found'],
        });
    }

    let parsedYaml;
    try {
        parsedYaml = parseYamlBlock(yamlText);
    } catch (error) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            approval_form_found: true,
            yaml_block_found: true,
            errors: [`unable to parse YAML block: ${error.message}`],
        });
    }

    const validation = validateParsedYaml(parsedYaml);
    if (!validation.ok) {
        return buildFailurePayload(args, {
            mode: 'approval-form-error',
            approval_form_found: true,
            yaml_block_found: true,
            required_fields_present: validation.missingFields.length === 0,
            missing_fields: validation.missingFields,
            approval_status: parsedYaml.approval_status || null,
            target_tables: parsedYaml.target_tables || null,
            errors: validation.errors,
        });
    }

    return buildSuccessPayload(args, parsedYaml, true);
}

function payloadToText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `approval_form_found=${payload.approval_form_found}`,
        `yaml_block_found=${payload.yaml_block_found}`,
        `required_fields_present=${payload.required_fields_present}`,
        `approval_status=${payload.approval_status}`,
        `target_tables=${JSON.stringify(payload.target_tables)}`,
        `commit_gate=${payload.commit_gate}`,
        `would_read_db=${payload.would_read_db}`,
        `would_write_db=${payload.would_write_db}`,
        `would_write_files=${payload.would_write_files}`,
        `would_access_network=${payload.would_access_network}`,
        `would_execute_pg_dump=${payload.would_execute_pg_dump}`,
        `would_execute_pg_restore=${payload.would_execute_pg_restore}`,
        `would_spawn_child_process=${payload.would_spawn_child_process}`,
        `approval_granted=${payload.approval_granted}`,
    ];

    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (Array.isArray(payload.missing_fields) && payload.missing_fields.length > 0) {
        lines.push(`missing_fields=${payload.missing_fields.join(',')}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
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
                approvalForm: '',
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
    RUNBOOK_VALIDATE_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    REQUIRED_FIELDS,
    REQUIRED_COUNT_FIELDS,
    parseArgs,
    extractYamlBlock,
    parseYamlBlock,
    validateParsedYaml,
    runValidation,
    buildNonExecutionConfirmations,
    main,
};
