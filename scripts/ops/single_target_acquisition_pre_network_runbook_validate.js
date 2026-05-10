#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { validateArtifact, validateManifest } = require('./single_target_acquisition_staging_schema_validator');
const { checkOutputRoot, checkTargetConsistency } = require('./single_target_acquisition_staging_writer_preflight');

const PRE_NETWORK_PHASE = 'PHASE4.83D_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK_DRAFT';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition pre-network runbook execution is not wired in Phase 4.83D.';
const REQUIRED_TOP_LEVEL_FIELDS = [
    'phase',
    'runbook_status',
    'network_dry_run_ready',
    'network_dry_run_authorized',
    'staging_write_authorized',
    'db_write_authorized',
    'training_authorized',
    'prediction_authorized',
    'final_human_confirmation',
    'target',
    'source_terms',
    'authorizations',
    'preflight_inputs',
    'proxy_browser_network',
    'safety',
    'stop_conditions',
    'next_phase_requirements',
];
const REQUIRED_TARGET_FIELDS = [
    'target_source',
    'target_engine_family',
    'target_scope_type',
    'target_match_id',
    'target_league',
    'target_season',
    'target_date',
];
const REQUIRED_SOURCE_TERMS_FIELDS = [
    'terms_url',
    'license_url',
    'allowed_use',
    'terms_approval',
    'human_approval_note',
];
const REQUIRED_AUTHORIZATION_FIELDS = [
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'staging_write_authorization',
    'final_human_confirmation',
];
const REQUIRED_PREFLIGHT_FIELDS = [
    'runtime_scaffold_required',
    'schema_validation_required',
    'writer_preflight_required',
    'staging_packet_preview_required',
    'source_manifest_candidate_required',
    'output_root_required',
];
const REQUIRED_PROXY_BROWSER_NETWORK_FIELDS = [
    'proxy_required',
    'proxy_provider',
    'proxy_health_check_required',
    'browser_required',
    'browser_provider',
    'network_policy',
    'rate_limit_policy',
    'retry_policy',
    'user_agent_policy',
    'no_login_paywall_bypass',
    'no_anti_bot_bypass',
    'no_bulk_expansion',
];
const REQUIRED_SAFETY_FIELDS = [
    'would_access_network',
    'would_launch_browser',
    'would_use_proxy',
    'would_execute_engine',
    'would_write_staging',
    'would_create_staging_directory',
    'would_write_source_manifest',
    'would_write_db',
    'would_train',
    'would_predict',
    'would_bulk_harvest',
];
const REQUIRED_STOP_CONDITIONS = [
    'missing_terms_approval',
    'missing_network_authorization',
    'target_scope_not_single_target',
    'output_root_invalid',
    'schema_validation_failed',
    'packet_preview_failed',
    'any_would_write_db_true',
    'any_bulk_scope_detected',
    'any_legacy_runtime_required',
];
const REQUIRED_NEXT_PHASE_REQUIREMENTS = [
    'explicit_target_source',
    'explicit_single_target_scope',
    'reviewed_source_terms',
    'explicit_network_dry_run_authorization',
    'accepted_proxy_browser_network_preflight',
    'accepted_staging_packet_preview',
    'confirmed_no_db_write',
    'confirmed_no_training',
    'confirmed_no_prediction',
];
const REQUIRED_CLI_FIELDS = [
    'runbook',
    'artifact_schema',
    'manifest_schema',
    'artifact',
    'manifest',
    'output_root',
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
    'confirm_single_target_scope',
    'staging_write_authorization',
    'final_human_confirmation',
];
const YES_NO_FIELDS = [
    'terms_approval',
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'confirm_single_target_scope',
    'staging_write_authorization',
    'final_human_confirmation',
];
const TOP_LEVEL_FALSE_FIELD_RULES = [
    ['network_dry_run_ready', 'network_dry_run_ready must remain false in the Phase 4.83D template'],
    ['network_dry_run_authorized', 'network_dry_run_authorized true in template is not allowed'],
    ['staging_write_authorized', 'staging_write_authorized true in template is not allowed'],
    ['db_write_authorized', 'db_write_authorized true in template is not allowed'],
    ['training_authorized', 'training_authorized true in template is not allowed'],
    ['prediction_authorized', 'prediction_authorized true in template is not allowed'],
    ['final_human_confirmation', 'final_human_confirmation true in template is not allowed'],
];
const PROXY_BROWSER_NETWORK_TRUE_RULES = [
    ['proxy_health_check_required', 'proxy_browser_network.proxy_health_check_required must be true'],
    ['no_login_paywall_bypass', 'proxy_browser_network.no_login_paywall_bypass must be true'],
    ['no_anti_bot_bypass', 'proxy_browser_network.no_anti_bot_bypass must be true'],
    ['no_bulk_expansion', 'proxy_browser_network.no_bulk_expansion must be true'],
];

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_pre_network_runbook_validate.js --runbook <path> --artifact-schema <path> --manifest-schema <path> --artifact <path> --manifest <path> --output-root <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --confirm-single-target-scope yes --staging-write-authorization no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_pre_network_runbook_validate.js --runbook <path> ... --commit',
        '',
        'Safety:',
        '  Phase 4.83D validates a local pre-network runbook draft only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        runbook: '',
        artifact_schema: '',
        manifest_schema: '',
        artifact: '',
        manifest: '',
        output_root: '',
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
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
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

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'no_browser_automation',
        'no_proxy_runtime_execution',
        'no_engine_execution',
        'no_db_writes',
        'no_file_writes',
        'no_staging_writes',
        'no_source_manifest_writes',
        'no_packet_file_writes',
        'no_training',
        'no_prediction_execution',
        'no_child_process_spawn',
    ];
}

function buildSafetyFlags() {
    return {
        runbook_draft_only: true,
        runbook_valid: false,
        packet_preview_passed: false,
        network_dry_run_ready: false,
        network_dry_run_authorized: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
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
        next_required_phase: 'Phase 4.84D or explicit user-authorized network dry-run runbook',
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: PRE_NETWORK_PHASE,
        mode: fields.mode || 'single-target-acquisition-pre-network-runbook-validate',
        ok: false,
        runbook: args.runbook || null,
        runbook_found: false,
        yaml_block_found: false,
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
    collectMissingFields(parsedYaml, 'target', REQUIRED_TARGET_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'source_terms', REQUIRED_SOURCE_TERMS_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'authorizations', REQUIRED_AUTHORIZATION_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'preflight_inputs', REQUIRED_PREFLIGHT_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'proxy_browser_network', REQUIRED_PROXY_BROWSER_NETWORK_FIELDS, missingFields);
    collectMissingFields(parsedYaml, 'safety', REQUIRED_SAFETY_FIELDS, missingFields);
    return missingFields;
}

function ensureArrayContainsAll(parsedYaml, key, requiredValues, errors) {
    const value = parsedYaml[key];
    if (!Array.isArray(value)) {
        errors.push(`${key} must be an array`);
        return;
    }
    for (const requiredValue of requiredValues) {
        if (!value.includes(requiredValue)) {
            errors.push(`${key} missing required value "${requiredValue}"`);
        }
    }
}

function ensureNestedNoFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== 'no') {
            errors.push(`${parentKey}.${fieldName} must remain no in the Phase 4.83D template`);
        }
    }
}

function ensureNestedTrueFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== true) {
            errors.push(`${parentKey}.${fieldName} must be true in the Phase 4.83D template`);
        }
    }
}

function ensureNestedFalseFields(parsedYaml, parentKey, fieldNames, errors) {
    const parent = parsedYaml[parentKey] || {};
    for (const fieldName of fieldNames) {
        if (parent[fieldName] !== false) {
            errors.push(`${parentKey}.${fieldName} must remain false in the Phase 4.83D template`);
        }
    }
}

function pushMissingFieldsError(missingFields, errors) {
    if (missingFields.length > 0) {
        errors.push(`missing required fields: ${missingFields.join(',')}`);
    }
}

function validateTopLevelTemplateFields(parsedYaml, errors) {
    if (parsedYaml.phase !== PRE_NETWORK_PHASE) {
        errors.push(`phase must be ${PRE_NETWORK_PHASE}`);
    }
    if (parsedYaml.runbook_status !== 'draft_only') {
        errors.push('runbook_status must remain draft_only in the Phase 4.83D template');
    }
    for (const [fieldName, message] of TOP_LEVEL_FALSE_FIELD_RULES) {
        if (parsedYaml[fieldName] !== false) {
            errors.push(message);
        }
    }
}

function validateTemplatePolicySections(parsedYaml, errors) {
    if ((parsedYaml.target || {}).target_engine_family !== 'titan_discovery') {
        errors.push('target.target_engine_family must remain titan_discovery in the Phase 4.83D template');
    }
    if ((parsedYaml.source_terms || {}).terms_approval !== 'no') {
        errors.push('source_terms.terms_approval must remain no in the Phase 4.83D template');
    }

    ensureNestedNoFields(parsedYaml, 'authorizations', REQUIRED_AUTHORIZATION_FIELDS, errors);
    ensureNestedTrueFields(parsedYaml, 'preflight_inputs', REQUIRED_PREFLIGHT_FIELDS, errors);
    ensureNestedFalseFields(parsedYaml, 'safety', REQUIRED_SAFETY_FIELDS, errors);
}

function validateProxyBrowserNetworkSection(parsedYaml, errors) {
    const proxyBrowserNetwork = parsedYaml.proxy_browser_network || {};
    for (const [fieldName, message] of PROXY_BROWSER_NETWORK_TRUE_RULES) {
        if (proxyBrowserNetwork[fieldName] !== true) {
            errors.push(message);
        }
    }
}

function validateRequiredArrays(parsedYaml, errors) {
    ensureArrayContainsAll(parsedYaml, 'stop_conditions', REQUIRED_STOP_CONDITIONS, errors);
    ensureArrayContainsAll(parsedYaml, 'next_phase_requirements', REQUIRED_NEXT_PHASE_REQUIREMENTS, errors);
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    pushMissingFieldsError(missingFields, errors);
    validateTopLevelTemplateFields(parsedYaml, errors);
    validateTemplatePolicySections(parsedYaml, errors);
    validateProxyBrowserNetworkSection(parsedYaml, errors);
    validateRequiredArrays(parsedYaml, errors);
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
    if (args.confirm_single_target_scope !== 'yes') {
        errors.push('confirm_single_target_scope must be yes');
    }
    return errors;
}

function validateRequiredCliFields(args) {
    const errors = [];
    for (const field of REQUIRED_CLI_FIELDS) {
        if (!args[field]) {
            errors.push(`missing ${field.replace(/_/g, ' ')} path or value`);
        }
    }
    return errors;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: PRE_NETWORK_PHASE,
        mode: 'single-target-acquisition-pre-network-runbook-validate',
        ok: true,
        runbook: args.runbook,
        runbook_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        runbook_valid: true,
        packet_preview_passed: true,
        errors: [],
        warnings: [
            'Phase 4.83D remains draft-only.',
            'CLI authorization yes values do not authorize execution in this phase.',
        ],
        non_execution_confirmations: buildNonExecutionConfirmations(),
    };
}

function buildArgumentErrorPayload(args, errors) {
    return buildFailurePayload(args, {
        mode: 'argument-error',
        errors,
    });
}

function validateCliArgsOrPayload(args) {
    const missingCliFields = validateRequiredCliFields(args);
    if (missingCliFields.length > 0) {
        return buildArgumentErrorPayload(args, [
            `missing runbook path or required CLI values: ${missingCliFields.join(', ')}`,
        ]);
    }

    const cliYesNoErrors = validateCliYesNoFields(args);
    const cliTargetErrors = validateCliTargetFields(args);
    if (cliYesNoErrors.length > 0 || cliTargetErrors.length > 0) {
        return buildArgumentErrorPayload(args, [...cliYesNoErrors, ...cliTargetErrors]);
    }
    return null;
}

function loadRunbookDraft(args, cwd, existsSync, readFileSync) {
    const runbookPath = resolveLocalPath(args.runbook, cwd);
    if (!existsSync(runbookPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'runbook-error',
                runbook_found: false,
                errors: [`missing runbook path: ${toRelativePath(runbookPath, cwd)}`],
            }),
        };
    }

    const markdownText = readFileSync(runbookPath, 'utf8');
    const yamlText = extractYamlBlock(markdownText);
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'runbook-error',
                runbook_found: true,
                yaml_block_found: false,
                errors: ['invalid runbook markdown / missing YAML block'],
            }),
        };
    }

    try {
        return { parsedYaml: parseYamlBlock(yamlText) };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'runbook-error',
                runbook_found: true,
                yaml_block_found: true,
                errors: [`invalid runbook markdown / missing YAML block: ${error.message}`],
            }),
        };
    }
}

function validateRunbookDraftOrPayload(args, parsedYaml) {
    const parsedValidation = validateParsedYaml(parsedYaml);
    if (!parsedValidation.ok) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'runbook-error',
                runbook_found: true,
                yaml_block_found: true,
                required_fields_present: parsedValidation.missingFields.length === 0,
                missing_fields: parsedValidation.missingFields,
                errors: parsedValidation.errors,
            }),
        };
    }
    return null;
}

function buildTargetMismatchPayload(args, message) {
    return buildFailurePayload(args, {
        mode: 'runbook-error',
        runbook_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        errors: [message],
    });
}

function validateRunbookTargetConsistency(args, parsedYaml) {
    const templateTarget = parsedYaml.target || {};
    if (templateTarget.target_source && templateTarget.target_source !== args.target_source) {
        return buildTargetMismatchPayload(
            args,
            `target mismatch: runbook target.target_source "${templateTarget.target_source}" does not match CLI target_source "${args.target_source}"`
        );
    }
    if (templateTarget.target_scope_type && templateTarget.target_scope_type !== args.target_scope_type) {
        return buildTargetMismatchPayload(
            args,
            `target mismatch: runbook target.target_scope_type "${templateTarget.target_scope_type}" does not match CLI target_scope_type "${args.target_scope_type}"`
        );
    }
    if (templateTarget.target_match_id && templateTarget.target_match_id !== args.target_match_id) {
        return buildTargetMismatchPayload(
            args,
            `target mismatch: runbook target.target_match_id "${templateTarget.target_match_id}" does not match CLI target_match_id "${args.target_match_id}"`
        );
    }
    return null;
}

function buildPacketPreviewFailurePayload(args, errors) {
    return buildFailurePayload(args, {
        mode: 'packet-preview-error',
        runbook_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        runbook_valid: true,
        errors,
    });
}

function validatePacketPreviewOrPayload(args, cwd, readFileSync) {
    const outputRootErrors = checkOutputRoot(args.output_root);
    if (outputRootErrors.length > 0) {
        return buildPacketPreviewFailurePayload(args, outputRootErrors);
    }

    const artifactResult = validateArtifact(args.artifact, args.artifact_schema);
    const manifestResult = validateManifest(args.manifest, args.manifest_schema);
    if (!artifactResult.valid || !manifestResult.valid) {
        return buildPacketPreviewFailurePayload(args, [
            'schema validation failed',
            ...artifactResult.errors,
            ...manifestResult.errors,
        ]);
    }

    const artifactData = JSON.parse(readFileSync(resolveLocalPath(args.artifact, cwd), 'utf8'));
    const manifestData = JSON.parse(readFileSync(resolveLocalPath(args.manifest, cwd), 'utf8'));
    const consistencyErrors = checkTargetConsistency(args, artifactData, manifestData);
    if (consistencyErrors.length > 0) {
        return buildPacketPreviewFailurePayload(args, ['packet preview failed', ...consistencyErrors]);
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

    const runbookLoad = loadRunbookDraft(args, cwd, existsSync, readFileSync);
    if (runbookLoad.payload) {
        return runbookLoad.payload;
    }

    const runbookValidation = validateRunbookDraftOrPayload(args, runbookLoad.parsedYaml);
    if (runbookValidation && runbookValidation.payload) {
        return runbookValidation.payload;
    }

    const targetConsistencyPayload = validateRunbookTargetConsistency(args, runbookLoad.parsedYaml);
    if (targetConsistencyPayload) {
        return targetConsistencyPayload;
    }

    const packetPreviewPayload = validatePacketPreviewOrPayload(args, cwd, readFileSync);
    if (packetPreviewPayload) {
        return packetPreviewPayload;
    }

    return buildSuccessPayload(args);
}

function payloadToText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `runbook_found=${payload.runbook_found}`,
        `yaml_block_found=${payload.yaml_block_found}`,
        `required_fields_present=${payload.required_fields_present}`,
        `runbook_draft_only=${payload.runbook_draft_only}`,
        `runbook_valid=${payload.runbook_valid}`,
        `packet_preview_passed=${payload.packet_preview_passed}`,
        `network_dry_run_ready=${payload.network_dry_run_ready}`,
        `network_dry_run_authorized=${payload.network_dry_run_authorized}`,
        `staging_write_authorized=${payload.staging_write_authorized}`,
        `db_write_authorized=${payload.db_write_authorized}`,
        `training_authorized=${payload.training_authorized}`,
        `prediction_authorized=${payload.prediction_authorized}`,
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
            { runbook: '' },
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
    PRE_NETWORK_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    extractYamlBlock,
    parseYamlBlock,
    validateParsedYaml,
    runValidation,
    buildNonExecutionConfirmations,
    main,
};
