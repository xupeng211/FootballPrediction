#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    PRE_NETWORK_PHASE,
    extractYamlBlock,
    parseYamlBlock,
    validateParsedYaml: validateRunbookParsedYaml,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');

const AUTH_PHASE = 'PHASE4.84D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run authorization execution is not wired in Phase 4.84D.';
const REQUIRED_TOP_LEVEL_FIELDS = [
    'phase',
    'authorization_form_status',
    'network_dry_run_authorized',
    'staging_write_authorized',
    'db_write_authorized',
    'training_authorized',
    'prediction_authorized',
    'final_human_confirmation',
    'request',
    'source_terms',
    'network_authorization',
    'proxy_browser_network_preflight',
    'required_inputs',
    'safety',
    'approvals',
];
const REQUIRED_REQUEST_FIELDS = [
    'requested_by',
    'requested_at',
    'target_source',
    'target_engine_family',
    'target_scope_type',
    'target_match_id',
    'target_league',
    'target_season',
    'target_date',
];
const REQUIRED_SOURCE_TERMS_FIELDS = [
    'source_url',
    'terms_url',
    'license_url',
    'allowed_use',
    'terms_reviewed_by',
    'terms_approval',
    'human_approval_note',
];
const REQUIRED_NETWORK_AUTHORIZATION_FIELDS = [
    'network_dry_run_authorization',
    'allow_external_network',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_staging_write',
    'max_targets',
    'bulk_scope_allowed',
    'allowed_runtime',
    'allowed_engine_family',
    'forbidden_legacy_runtime',
];
const REQUIRED_PROXY_BROWSER_NETWORK_FIELDS = [
    'proxy_required',
    'proxy_provider',
    'proxy_health_check_required',
    'browser_required',
    'browser_provider',
    'rate_limit_policy',
    'retry_policy',
    'user_agent_policy',
    'no_login_paywall_bypass',
    'no_anti_bot_bypass',
    'no_bulk_expansion',
];
const REQUIRED_INPUT_FIELDS = [
    'pre_network_runbook_required',
    'staging_packet_preview_required',
    'artifact_schema_required',
    'manifest_schema_required',
    'output_root_policy_required',
    'stop_conditions_required',
];
const REQUIRED_SAFETY_FIELDS = [
    'would_access_network',
    'would_launch_browser',
    'would_use_proxy',
    'would_execute_engine',
    'would_write_staging',
    'would_create_staging_directory',
    'would_write_source_manifest',
    'would_write_packet_file',
    'would_write_db',
    'would_train',
    'would_predict',
    'would_bulk_harvest',
];
const REQUIRED_APPROVAL_FIELDS = [
    'source_terms_approved_by',
    'network_dry_run_approved_by',
    'staging_policy_approved_by',
    'final_human_confirmation_by',
];
const REQUIRED_CLI_FIELDS = [
    'auth_form',
    'runbook',
    'target_source',
    'target_engine_family',
    'target_scope_type',
    'target_match_id',
    'terms_approval',
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'final_human_confirmation',
];
const YES_NO_FIELDS = [
    'terms_approval',
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'final_human_confirmation',
];
const TOP_LEVEL_FALSE_FIELD_RULES = [
    ['network_dry_run_authorized', 'network_dry_run_authorized true in template is not allowed'],
    ['staging_write_authorized', 'staging_write_authorized true in template is not allowed'],
    ['db_write_authorized', 'db_write_authorized true in template is not allowed'],
    ['training_authorized', 'training_authorized true in template is not allowed'],
    ['prediction_authorized', 'prediction_authorized true in template is not allowed'],
    ['final_human_confirmation', 'final_human_confirmation true in template is not allowed'],
];
const SOURCE_TERMS_NO_FIELDS = ['terms_approval'];
const NETWORK_AUTHORIZATION_NO_FIELDS = [
    'network_dry_run_authorization',
    'allow_external_network',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_staging_write',
];
const REQUIRED_INPUT_TRUE_FIELDS = REQUIRED_INPUT_FIELDS;
const REQUIRED_SAFETY_FALSE_FIELDS = REQUIRED_SAFETY_FIELDS;
const PROXY_BROWSER_NETWORK_TRUE_FIELDS = ['no_login_paywall_bypass', 'no_anti_bot_bypass', 'no_bulk_expansion'];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_auth_form_validate.js --auth-form <path> --runbook <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_auth_form_validate.js --auth-form <path> --runbook <path> --commit',
        '',
        'Safety:',
        '  Phase 4.84D validates a local network dry-run authorization form template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        auth_form: '',
        runbook: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--commit') {
            args.commit = true;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else if (token.startsWith('--')) {
            const eqIndex = token.indexOf('=');
            if (eqIndex !== -1) {
                args[token.slice(2, eqIndex).replace(/-/g, '_')] = token.slice(eqIndex + 1);
            } else if (index + 1 < argv.length && !argv[index + 1].startsWith('--')) {
                args[token.slice(2).replace(/-/g, '_')] = String(argv[index + 1] || '');
                index += 1;
            } else {
                throw new Error(`Unknown argument: ${token}`);
            }
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

function buildSafetyFlags() {
    return {
        authorization_form_template_only: true,
        auth_form_valid: false,
        runbook_template_valid: false,
        network_dry_run_authorized: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_execute_engine: false,
        would_write_staging: false,
        would_create_staging_directory: false,
        would_write_source_manifest: false,
        would_write_packet_file: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        would_spawn_child_process: false,
        commit_gate: 'blocked',
        next_required_phase: 'Phase 4.85D or explicit user-authorized network dry-run preparation',
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: AUTH_PHASE,
        mode: fields.mode || 'single-target-acquisition-network-auth-form-validate',
        ok: false,
        auth_form: args.auth_form || null,
        runbook: args.runbook || null,
        auth_form_found: false,
        runbook_found: false,
        yaml_block_found: false,
        runbook_yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
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

function collectMissingFields(parsedYaml, parentKey, requiredKeys, missingFields) {
    const value = parsedYaml[parentKey];
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        for (const key of requiredKeys) {
            missingFields.push(`${parentKey}.${key}`);
        }
        return;
    }
    for (const key of requiredKeys) {
        if (!Object.prototype.hasOwnProperty.call(value, key)) {
            missingFields.push(`${parentKey}.${key}`);
        }
    }
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP_LEVEL_FIELDS.filter(
        field => !Object.prototype.hasOwnProperty.call(parsedYaml, field)
    );
    collectMissingFields(parsedYaml, 'request', REQUIRED_REQUEST_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'source_terms', REQUIRED_SOURCE_TERMS_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'network_authorization', REQUIRED_NETWORK_AUTHORIZATION_FIELDS, missingFields);
    collectMissingFields(
        parsedYaml,
        'proxy_browser_network_preflight',
        REQUIRED_PROXY_BROWSER_NETWORK_FIELDS,
        missingFields
    );
    collectMissingFields(parsedYaml, 'required_inputs', REQUIRED_INPUT_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'safety', REQUIRED_SAFETY_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'approvals', REQUIRED_APPROVAL_FIELDS, missingFields);
    return missingFields;
}

function ensureNestedNoFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== 'no') {
            errors.push(`${parentKey}.${fieldName} must remain no in the Phase 4.84D template`);
        }
    }
}

function ensureNestedTrueFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== true) {
            errors.push(`${parentKey}.${fieldName} must be true in the Phase 4.84D template`);
        }
    }
}

function ensureNestedFalseFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== false) {
            errors.push(`${parentKey}.${fieldName} must remain false in the Phase 4.84D template`);
        }
    }
}

function pushMissingFieldsError(missingFields, errors) {
    if (missingFields.length > 0) {
        errors.push(`missing required fields: ${missingFields.join(',')}`);
    }
}

function validateTopLevelTemplateFields(parsedYaml, errors) {
    if (parsedYaml.phase !== AUTH_PHASE) {
        errors.push(`phase must be ${AUTH_PHASE}`);
    }
    if (parsedYaml.authorization_form_status !== 'template_only') {
        errors.push('authorization_form_status must remain template_only in the Phase 4.84D template');
    }
    for (const [fieldName, message] of TOP_LEVEL_FALSE_FIELD_RULES) {
        if (parsedYaml[fieldName] !== false) {
            errors.push(message);
        }
    }
}

function validateRequestSection(parsedYaml, errors) {
    const request = parsedYaml.request || {};
    if (request.target_engine_family !== 'titan_discovery') {
        errors.push('unsupported engine family "template target_engine_family must remain titan_discovery"');
    }
    if (request.target_scope_type === 'bulk') {
        errors.push('unsupported scope type bulk');
    }
}

function validateSourceTermsSection(parsedYaml, errors) {
    ensureNestedNoFields(parsedYaml, 'source_terms', SOURCE_TERMS_NO_FIELDS, errors);
}

function validateNetworkAuthorizationSection(parsedYaml, errors) {
    const networkAuthorization = parsedYaml.network_authorization || {};
    ensureNestedNoFields(parsedYaml, 'network_authorization', NETWORK_AUTHORIZATION_NO_FIELDS, errors);

    if (networkAuthorization.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.84D template');
    }
    if (networkAuthorization.bulk_scope_allowed !== false) {
        errors.push('bulk scope allowed must remain false in the Phase 4.84D template');
    }
    if (networkAuthorization.allowed_runtime !== 'scaffolded_single_target_only') {
        errors.push('network_authorization.allowed_runtime must remain scaffolded_single_target_only');
    }
    if (networkAuthorization.allowed_engine_family !== 'titan_discovery') {
        errors.push(
            'unsupported engine family "network_authorization.allowed_engine_family must remain titan_discovery"'
        );
    }
    if (networkAuthorization.forbidden_legacy_runtime !== true) {
        errors.push('network_authorization.forbidden_legacy_runtime must be true in the Phase 4.84D template');
    }
}

function validateProxyBrowserNetworkSection(parsedYaml, errors) {
    ensureNestedTrueFields(parsedYaml, 'proxy_browser_network_preflight', PROXY_BROWSER_NETWORK_TRUE_FIELDS, errors);
}

function validateRequiredInputsSection(parsedYaml, errors) {
    ensureNestedTrueFields(parsedYaml, 'required_inputs', REQUIRED_INPUT_TRUE_FIELDS, errors);
}

function validateSafetySection(parsedYaml, errors) {
    ensureNestedFalseFields(parsedYaml, 'safety', REQUIRED_SAFETY_FALSE_FIELDS, errors);
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    pushMissingFieldsError(missingFields, errors);
    validateTopLevelTemplateFields(parsedYaml, errors);
    validateRequestSection(parsedYaml, errors);
    validateSourceTermsSection(parsedYaml, errors);
    validateNetworkAuthorizationSection(parsedYaml, errors);
    validateProxyBrowserNetworkSection(parsedYaml, errors);
    validateRequiredInputsSection(parsedYaml, errors);
    validateSafetySection(parsedYaml, errors);
    return {
        ok: errors.length === 0,
        missingFields,
        errors,
    };
}

function validateCliYesNoFields(args) {
    const errors = [];
    for (const field of YES_NO_FIELDS) {
        const value = args[field];
        if (value !== 'yes' && value !== 'no') {
            errors.push(`--${field.replace(/_/g, '-')} is required (yes/no)`);
        }
    }
    return errors;
}

function validateCliTargetFields(args) {
    const errors = [];
    if (args.target_engine_family !== 'titan_discovery') {
        errors.push(`unsupported engine family "${args.target_engine_family}"`);
    }
    if (args.target_scope_type !== 'match_id' && args.target_scope_type !== 'league_season_date') {
        errors.push(`unsupported scope type "${args.target_scope_type}"`);
    }
    if (args.target_scope_type === 'bulk') {
        errors.push('unsupported scope type bulk');
    }
    if (args.target_scope_type === 'match_id' && !args.target_match_id) {
        errors.push('--target-match-id is required when target_scope_type=match_id');
    }
    return errors;
}

function validateRequiredCliFields(args) {
    const errors = [];
    for (const field of REQUIRED_CLI_FIELDS) {
        if (!args[field]) {
            if (field === 'auth_form') {
                errors.push('missing auth form');
            } else if (field === 'runbook') {
                errors.push('missing runbook');
            } else {
                errors.push(`missing ${field.replace(/_/g, ' ')} path or value`);
            }
        }
    }
    return errors;
}

function buildArgumentErrorPayload(args, errors) {
    return buildFailurePayload(args, {
        mode: 'argument-error',
        errors,
    });
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: AUTH_PHASE,
        mode: 'single-target-acquisition-network-auth-form-validate',
        ok: true,
        auth_form: args.auth_form,
        runbook: args.runbook,
        auth_form_found: true,
        runbook_found: true,
        yaml_block_found: true,
        runbook_yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        auth_form_valid: true,
        runbook_template_valid: true,
        errors: [],
        warnings: [
            'Phase 4.84D remains template-only.',
            'CLI authorization yes values do not authorize execution in this phase.',
        ],
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function validateCliArgsOrPayload(args) {
    const missingCliFields = validateRequiredCliFields(args);
    if (missingCliFields.length > 0) {
        return buildArgumentErrorPayload(args, missingCliFields);
    }

    const cliYesNoErrors = validateCliYesNoFields(args);
    const cliTargetErrors = validateCliTargetFields(args);
    if (cliYesNoErrors.length > 0 || cliTargetErrors.length > 0) {
        return buildArgumentErrorPayload(args, [...cliYesNoErrors, ...cliTargetErrors]);
    }
    return null;
}

function loadMarkdownYaml(args, cwd, existsSync, readFileSync, fieldName, modePrefix, missingLabel) {
    const targetPath = resolveLocalPath(args[fieldName], cwd);
    if (!existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: false,
                errors: [`${missingLabel}: ${toRelativePath(targetPath, cwd)}`],
            }),
        };
    }

    const markdownText = readFileSync(targetPath, 'utf8');
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: true,
                [fieldName === 'auth_form' ? 'yaml_block_found' : 'runbook_yaml_block_found']: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return { parsedYaml: parseYamlBlock(yamlText) };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: true,
                [fieldName === 'auth_form' ? 'yaml_block_found' : 'runbook_yaml_block_found']: true,
                errors: [`invalid YAML: ${error.message}`],
            }),
        };
    }
}

function validateAuthFormOrPayload(args, parsedYaml) {
    const parsedValidation = validateParsedYaml(parsedYaml);
    if (!parsedValidation.ok) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'auth-form-error',
                auth_form_found: true,
                yaml_block_found: true,
                required_fields_present: parsedValidation.missingFields.length === 0,
                missing_fields: parsedValidation.missingFields,
                errors: parsedValidation.errors,
            }),
        };
    }
    return null;
}

function validateRunbookTemplateOrPayload(args, parsedYaml) {
    const parsedValidation = validateRunbookParsedYaml(parsedYaml);
    if (!parsedValidation.ok) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'runbook-error',
                auth_form_found: true,
                runbook_found: true,
                yaml_block_found: true,
                runbook_yaml_block_found: true,
                auth_form_valid: true,
                errors: [`runbook template validation failed: ${parsedValidation.errors.join('; ')}`],
            }),
        };
    }
    return null;
}

function validateTargetConsistency(args, authFormYaml, runbookYaml) {
    const request = authFormYaml.request || {};
    const runbookTarget = runbookYaml.target || {};
    const errors = [];

    const comparisons = [
        ['request.target_source', request.target_source, args.target_source],
        ['request.target_engine_family', request.target_engine_family, args.target_engine_family],
        ['request.target_scope_type', request.target_scope_type, args.target_scope_type],
        ['request.target_match_id', request.target_match_id, args.target_match_id],
        ['runbook.target.target_source', runbookTarget.target_source, args.target_source],
        ['runbook.target.target_engine_family', runbookTarget.target_engine_family, args.target_engine_family],
        ['runbook.target.target_scope_type', runbookTarget.target_scope_type, args.target_scope_type],
        ['runbook.target.target_match_id', runbookTarget.target_match_id, args.target_match_id],
    ];

    for (const [label, templateValue, cliValue] of comparisons) {
        if (templateValue && templateValue !== cliValue) {
            errors.push(`target mismatch: ${label} "${templateValue}" does not match CLI value "${cliValue}"`);
        }
    }

    if (errors.length > 0) {
        return buildFailurePayload(args, {
            mode: 'target-error',
            auth_form_found: true,
            runbook_found: true,
            yaml_block_found: true,
            runbook_yaml_block_found: true,
            required_fields_present: true,
            auth_form_valid: true,
            runbook_template_valid: true,
            errors,
        });
    }
    return null;
}

function runValidation(args, dependencies = {}) {
    const cwd = dependencies.cwd || process.cwd();
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readFileSync = dependencies.readFileSync || fs.readFileSync;

    const cliPayload = validateCliArgsOrPayload(args);
    if (cliPayload) {
        return cliPayload;
    }

    const authFormLoad = loadMarkdownYaml(
        args,
        cwd,
        existsSync,
        readFileSync,
        'auth_form',
        'auth-form',
        'missing auth form'
    );
    if (authFormLoad.payload) {
        return authFormLoad.payload;
    }

    const authFormValidation = validateAuthFormOrPayload(args, authFormLoad.parsedYaml);
    if (authFormValidation && authFormValidation.payload) {
        return authFormValidation.payload;
    }

    const runbookLoad = loadMarkdownYaml(args, cwd, existsSync, readFileSync, 'runbook', 'runbook', 'missing runbook');
    if (runbookLoad.payload) {
        return runbookLoad.payload;
    }

    const runbookValidation = validateRunbookTemplateOrPayload(args, runbookLoad.parsedYaml);
    if (runbookValidation && runbookValidation.payload) {
        return runbookValidation.payload;
    }

    const targetConsistencyPayload = validateTargetConsistency(args, authFormLoad.parsedYaml, runbookLoad.parsedYaml);
    if (targetConsistencyPayload) {
        return targetConsistencyPayload;
    }

    return buildSuccessPayload(args);
}

function payloadToText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `auth_form_found=${payload.auth_form_found}`,
        `runbook_found=${payload.runbook_found}`,
        `yaml_block_found=${payload.yaml_block_found}`,
        `runbook_yaml_block_found=${payload.runbook_yaml_block_found}`,
        `required_fields_present=${payload.required_fields_present}`,
        `authorization_form_template_only=${payload.authorization_form_template_only}`,
        `auth_form_valid=${payload.auth_form_valid}`,
        `runbook_template_valid=${payload.runbook_template_valid}`,
        `network_dry_run_authorized=${payload.network_dry_run_authorized}`,
        `staging_write_authorized=${payload.staging_write_authorized}`,
        `db_write_authorized=${payload.db_write_authorized}`,
        `training_authorized=${payload.training_authorized}`,
        `prediction_authorized=${payload.prediction_authorized}`,
        `final_human_confirmation=${payload.final_human_confirmation}`,
        `would_access_network=${payload.would_access_network}`,
        `would_launch_browser=${payload.would_launch_browser}`,
        `would_use_proxy=${payload.would_use_proxy}`,
        `would_execute_engine=${payload.would_execute_engine}`,
        `would_write_staging=${payload.would_write_staging}`,
        `would_create_staging_directory=${payload.would_create_staging_directory}`,
        `would_write_source_manifest=${payload.would_write_source_manifest}`,
        `would_write_packet_file=${payload.would_write_packet_file}`,
        `would_write_db=${payload.would_write_db}`,
        `would_train=${payload.would_train}`,
        `would_predict=${payload.would_predict}`,
        `would_spawn_child_process=${payload.would_spawn_child_process}`,
        `commit_gate=${payload.commit_gate}`,
        `next_required_phase=${payload.next_required_phase}`,
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
        lines.push(`warnings=${payload.warnings.join('; ')}`);
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
            writePayload(payload, true, output);
            return 1;
        }

        const payload = runValidation(args, dependencies);
        writePayload(payload, true, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const payload = buildFailurePayload(
            { auth_form: '', runbook: '' },
            {
                mode: 'argument-error',
                errors: [error.message],
            }
        );
        writePayload(payload, true, output);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    AUTH_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
