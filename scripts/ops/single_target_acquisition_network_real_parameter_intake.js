#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    validateParsedYaml: validateBlockedSummaryYaml,
} = require('./single_target_acquisition_network_blocked_final_preflight_summary');

const OUTPUT_PHASE = 'PHASE4.90D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE';
const TEMPLATE_PHASE = 'PHASE4_90D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE';
const MODE = 'single-target-acquisition-network-real-parameter-intake-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition real-parameter intake execution is not wired in Phase 4.90D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.91D or explicit user-supplied real network dry-run parameters';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';
const PRIMARY_BLOCKING_REASON = 'missing_user_supplied_real_network_dry_run_inputs';

const MISSING_PARAMETER_GROUPS = [
    'real_target',
    'source_terms',
    'network_authorization',
    'proxy_browser_network_policy',
    'staging_policy',
    'no_db_training_prediction_policy',
    'final_human_confirmation',
];

const REQUIRED_TOP_FIELDS = words(`
    phase intake_status real_parameters_provided network_dry_run_authorized
    network_dry_run_execution_allowed staging_write_authorized
    db_write_authorized training_authorized prediction_authorized
    final_human_confirmation real_target source_terms network_authorization
    proxy_browser_network_policy staging_policy no_db_training_prediction_policy
    included_blocked_preflight safety
`);

const TOP_FALSE = {
    real_parameters_provided: 'real_parameters_provided true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

const SAFETY_FIELDS = words(`
    would_access_network would_launch_browser would_use_proxy
    would_execute_engine would_execute_legacy_titan_discovery
    would_write_staging would_create_staging_directory
    would_write_source_manifest would_write_packet_file
    would_write_approval_packet_file would_write_user_input_closure_file
    would_write_blocked_summary_file would_write_real_parameter_intake_file
    would_write_db would_train would_predict would_bulk_harvest
`);

const FIELD_OBJECT_REQUIREMENTS = {
    real_target: {
        target_source: words('required provided value'),
        target_engine_family: words('required provided value'),
        target_scope_type: words('required provided value allowed_values'),
        target_match_id: words('required_when_scope_type provided value'),
        target_league: words('required_when_scope_type provided value'),
        target_season: words('required_when_scope_type provided value'),
        target_date: words('required_when_scope_type provided value'),
    },
    source_terms: {
        source_homepage_url: words('required provided value'),
        terms_url: words('required provided value'),
        license_url: words('required provided value'),
        allowed_use_summary: words('required provided value'),
        terms_reviewed_by: words('required provided value'),
        terms_approval: words('required provided value'),
    },
    network_authorization: {
        network_dry_run_authorization: words('required provided value'),
        allow_external_network: words('required provided value'),
        allow_browser_runtime: words('required provided value'),
        allow_proxy_runtime: words('required provided value'),
        allow_staging_write: words('required provided value'),
    },
    proxy_browser_network_policy: {
        proxy_policy: words('required provided value'),
        browser_policy: words('required provided value'),
        rate_limit_policy: words('required provided value'),
        retry_policy: words('required provided value'),
        user_agent_policy: words('required provided value'),
        no_login_paywall_bypass_confirmation: words('required provided value'),
        no_anti_bot_bypass_confirmation: words('required provided value'),
        no_bulk_expansion_confirmation: words('required provided value'),
    },
    staging_policy: {
        output_root: words('required provided value allowed_prefix'),
        staging_write_authorized: words('required provided value'),
    },
    no_db_training_prediction_policy: {
        no_db_write_confirmation: words('required provided value'),
        no_training_confirmation: words('required provided value'),
        no_prediction_confirmation: words('required provided value'),
        no_model_artifact_loading_confirmation: words('required provided value'),
    },
};

const FINAL_CONFIRMATION_FIELDS = words('required provided confirmed_by value');

const DEFAULT_NO_VALUE_PATHS = words(`
    source_terms.terms_approval
    network_authorization.network_dry_run_authorization
    network_authorization.allow_external_network
    network_authorization.allow_browser_runtime
    network_authorization.allow_proxy_runtime
    network_authorization.allow_staging_write
    proxy_browser_network_policy.no_login_paywall_bypass_confirmation
    proxy_browser_network_policy.no_anti_bot_bypass_confirmation
    proxy_browser_network_policy.no_bulk_expansion_confirmation
    staging_policy.staging_write_authorized
    no_db_training_prediction_policy.no_db_write_confirmation
    no_db_training_prediction_policy.no_training_confirmation
    no_db_training_prediction_policy.no_prediction_confirmation
    no_db_training_prediction_policy.no_model_artifact_loading_confirmation
`);

const EMPTY_REAL_VALUE_PATHS = words(`
    real_target.target_source
    real_target.target_scope_type
    real_target.target_match_id
    real_target.target_league
    real_target.target_season
    real_target.target_date
    source_terms.source_homepage_url
    source_terms.terms_url
    source_terms.license_url
    source_terms.allowed_use_summary
    source_terms.terms_reviewed_by
    proxy_browser_network_policy.proxy_policy
    proxy_browser_network_policy.browser_policy
    proxy_browser_network_policy.rate_limit_policy
    proxy_browser_network_policy.retry_policy
    proxy_browser_network_policy.user_agent_policy
    staging_policy.output_root
`);

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_real_parameter_intake.js --intake <path> --blocked-summary <path>',
        '  node scripts/ops/single_target_acquisition_network_real_parameter_intake.js --intake <path> --blocked-summary <path> --commit',
        '',
        'Safety:',
        '  Phase 4.90D previews a local real-parameter intake template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        intake: '',
        blocked_summary: '',
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--commit') {
            args.commit = true;
            continue;
        }
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        if (!token.startsWith('--')) throw new Error(`Unknown argument: ${token}`);
        const eqIndex = token.indexOf('=');
        if (eqIndex !== -1) {
            args[token.slice(2, eqIndex).replace(/-/g, '_')] = token.slice(eqIndex + 1);
        } else if (index + 1 < argv.length && !argv[index + 1].startsWith('--')) {
            args[token.slice(2).replace(/-/g, '_')] = String(argv[index + 1] || '');
            index += 1;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function buildSafetyFlags() {
    return {
        real_parameter_intake_template_only: true,
        intake_valid: false,
        blocked_summary_valid: false,
        real_parameters_provided: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        missing_parameter_groups: MISSING_PARAMETER_GROUPS,
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_execute_engine: false,
        would_execute_legacy_titan_discovery: false,
        would_write_staging: false,
        would_create_staging_directory: false,
        would_write_source_manifest: false,
        would_write_packet_file: false,
        would_write_approval_packet_file: false,
        would_write_user_input_closure_file: false,
        would_write_blocked_summary_file: false,
        would_write_real_parameter_intake_file: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        would_spawn_child_process: false,
        commit_gate: 'blocked',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: OUTPUT_PHASE,
        mode: fields.mode || MODE,
        ok: false,
        intake: args.intake || null,
        blocked_summary: args.blocked_summary || null,
        intake_found: false,
        blocked_summary_found: false,
        yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
        ],
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

function resolveLocalPath(rawPath, cwd = process.cwd()) {
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function parseScalar(rawValue) {
    const value = String(rawValue || '').trim();
    if (value === '') return null;
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (/^-?\d+$/.test(value)) return Number(value);
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        return value.slice(1, -1);
    }
    return value;
}

function getNextContainerType(lines, currentIndex, currentIndent) {
    for (let index = currentIndex + 1; index < lines.length; index += 1) {
        const line = lines[index];
        if (!line.trim() || line.trim().startsWith('#')) continue;
        const indent = line.match(/^ */)[0].length;
        if (indent <= currentIndent) return false;
        return line.trim().startsWith('- ') ? 'list' : 'object';
    }
    return false;
}

function assignParsedValue(parent, key, value) {
    if (
        parent &&
        Object.prototype.hasOwnProperty.call(parent, key) &&
        key === 'final_human_confirmation' &&
        typeof parent[key] === 'boolean' &&
        value &&
        typeof value === 'object' &&
        !Array.isArray(value)
    ) {
        parent.final_human_confirmation_details = value;
        return;
    }
    parent[key] = value;
}

function parseIntakeYaml(yamlText) {
    const root = {};
    const stack = [{ indent: -1, value: root }];
    const lines = String(yamlText || '').split(/\r?\n/);

    lines.forEach((rawLine, lineIndex) => {
        if (!rawLine.trim() || rawLine.trim().startsWith('#')) return;
        const indent = rawLine.match(/^ */)[0].length;
        const trimmed = rawLine.trim();

        while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop();
        const parent = stack[stack.length - 1].value;

        if (trimmed.startsWith('- ')) {
            if (!Array.isArray(parent)) throw new Error(`unsupported YAML list line: ${trimmed}`);
            parent.push(parseScalar(trimmed.slice(2)));
            return;
        }

        const match = trimmed.match(/^([A-Za-z0-9_]+):(.*)$/);
        if (!match) throw new Error(`unsupported YAML line: ${trimmed}`);
        const key = match[1];
        const valueText = match[2].trim();

        if (valueText !== '') {
            assignParsedValue(parent, key, parseScalar(valueText));
            return;
        }

        const nextContainerType = getNextContainerType(lines, lineIndex, indent);
        if (!nextContainerType) {
            assignParsedValue(parent, key, null);
            return;
        }
        const container = nextContainerType === 'list' ? [] : {};
        assignParsedValue(parent, key, container);
        stack.push({ indent, value: container });
    });

    return root;
}

function validateRequiredCliFields(args) {
    const errors = [];
    if (!args.intake) errors.push('missing intake');
    if (!args.blocked_summary) errors.push('missing blocked summary');
    return errors;
}

function validateCliArgsOrPayload(args) {
    const errors = validateRequiredCliFields(args);
    return errors.length ? buildFailurePayload(args, { mode: 'argument-error', errors }) : null;
}

function loadYamlFile(args, dependencies, fieldName, missingLabel, mode) {
    const rawPath = args[fieldName];
    const targetPath = resolveLocalPath(rawPath, dependencies.cwd);
    if (!dependencies.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: false,
                errors: [`missing ${missingLabel}: ${toRelativePath(targetPath, dependencies.cwd)}`],
            }),
        };
    }

    const yamlText = extractYamlBlock(dependencies.readFileSync(targetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: true,
                yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return { parsedYaml: parseIntakeYaml(yamlText), yamlText };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: true,
                yaml_block_found: true,
                errors: [`invalid YAML: ${error.message}`],
            }),
        };
    }
}

function hasOwn(root, key) {
    return Object.prototype.hasOwnProperty.call(root, key);
}

function addMissingNested(root, parentPath, requiredKeys, missingFields) {
    const value = getPath(root, parentPath);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        requiredKeys.forEach(key => missingFields.push(`${parentPath}.${key}`));
        return;
    }
    requiredKeys.filter(key => !hasOwn(value, key)).forEach(key => missingFields.push(`${parentPath}.${key}`));
}

function getPath(root, dottedPath) {
    return dottedPath.split('.').reduce((current, key) => {
        if (!current || typeof current !== 'object') return undefined;
        return current[key];
    }, root);
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP_FIELDS.filter(key => !hasOwn(parsedYaml, key));
    if (!hasOwn(parsedYaml, 'final_human_confirmation_details')) {
        missingFields.push('final_human_confirmation.provided');
    }
    Object.entries(FIELD_OBJECT_REQUIREMENTS).forEach(([sectionName, fieldRequirements]) => {
        Object.entries(fieldRequirements).forEach(([fieldName, requiredKeys]) => {
            addMissingNested(parsedYaml, `${sectionName}.${fieldName}`, requiredKeys, missingFields);
        });
    });
    addMissingNested(parsedYaml, 'final_human_confirmation_details', FINAL_CONFIRMATION_FIELDS, missingFields);
    addMissingNested(
        parsedYaml,
        'included_blocked_preflight',
        words('blocked_summary primary_blocking_reason'),
        missingFields
    );
    addMissingNested(parsedYaml, 'safety', SAFETY_FIELDS, missingFields);
    ['max_targets', 'bulk_scope_allowed'].forEach(fieldName => {
        if (!hasOwn(parsedYaml.real_target || {}, fieldName)) missingFields.push(`real_target.${fieldName}`);
    });
    ['schema_validation_required', 'source_manifest_required'].forEach(fieldName => {
        if (!hasOwn(parsedYaml.staging_policy || {}, fieldName)) missingFields.push(`staging_policy.${fieldName}`);
    });
    return missingFields;
}

function isEmptyValue(value) {
    return value === null || typeof value === 'undefined' || value === '';
}

function validateProvidedFields(parsedYaml, errors) {
    Object.entries(FIELD_OBJECT_REQUIREMENTS).forEach(([sectionName, fieldRequirements]) => {
        Object.keys(fieldRequirements).forEach(fieldName => {
            const fieldPath = `${sectionName}.${fieldName}`;
            const field = getPath(parsedYaml, fieldPath);
            if (!field || typeof field !== 'object' || Array.isArray(field)) return;
            if (field.provided !== false) {
                errors.push(`${fieldPath}.provided true in template is not allowed`);
            }
        });
    });
    const finalConfirmation = parsedYaml.final_human_confirmation_details || {};
    if (finalConfirmation.provided !== false) {
        errors.push('final_human_confirmation.provided true in template is not allowed');
    }
}

function validateDefaultValues(parsedYaml, errors) {
    EMPTY_REAL_VALUE_PATHS.forEach(fieldPath => {
        const value = getPath(parsedYaml, `${fieldPath}.value`);
        if (!isEmptyValue(value)) {
            errors.push(`Codex self-filled real parameter: ${fieldPath}.value must remain empty`);
        }
    });

    DEFAULT_NO_VALUE_PATHS.forEach(fieldPath => {
        const value = getPath(parsedYaml, `${fieldPath}.value`);
        if (value !== 'no') errors.push(`${fieldPath}.value must remain no`);
    });

    const engine = getPath(parsedYaml, 'real_target.target_engine_family');
    if (!engine || engine.value !== 'titan_discovery') {
        errors.push(`target_engine_family not titan_discovery: ${engine ? engine.value : 'missing'}`);
    }
    if (engine && engine.provided !== false) {
        errors.push('real_target.target_engine_family.provided true in template is not allowed');
    }

    const allowedValues = getPath(parsedYaml, 'real_target.target_scope_type.allowed_values');
    if (
        !Array.isArray(allowedValues) ||
        !allowedValues.includes('match_id') ||
        !allowedValues.includes('league_season_date')
    ) {
        errors.push('real_target.target_scope_type.allowed_values must include match_id and league_season_date');
    }

    const finalConfirmation = parsedYaml.final_human_confirmation_details || {};
    if (!isEmptyValue(finalConfirmation.confirmed_by)) {
        errors.push('Codex self-filled real parameter: final_human_confirmation.confirmed_by must remain empty');
    }
    if (finalConfirmation.value !== 'no') {
        errors.push('final_human_confirmation.value must remain no');
    }
}

function validateSafety(parsedYaml, errors) {
    const safety = parsedYaml.safety || {};
    SAFETY_FIELDS.forEach(fieldName => {
        if (safety[fieldName] !== false) {
            errors.push(`safety.${fieldName} must remain false`);
        }
    });
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) errors.push(`missing required fields: ${missingFields.join(',')}`);
    if (parsedYaml.phase !== TEMPLATE_PHASE) errors.push(`phase must be ${TEMPLATE_PHASE}`);
    if (parsedYaml.intake_status !== 'template_only') {
        errors.push('intake_status must remain template_only in the Phase 4.90D template');
    }
    Object.entries(TOP_FALSE).forEach(([fieldName, message]) => {
        if (parsedYaml[fieldName] !== false) errors.push(message);
    });
    validateProvidedFields(parsedYaml, errors);
    validateDefaultValues(parsedYaml, errors);
    if ((parsedYaml.real_target || {}).bulk_scope_allowed !== false) {
        errors.push('bulk_scope_allowed true is not allowed in the Phase 4.90D template');
    }
    if ((parsedYaml.real_target || {}).max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.90D template');
    }
    if ((parsedYaml.staging_policy || {}).schema_validation_required !== true) {
        errors.push('staging_policy.schema_validation_required must be true');
    }
    if ((parsedYaml.staging_policy || {}).source_manifest_required !== true) {
        errors.push('staging_policy.source_manifest_required must be true');
    }
    const included = parsedYaml.included_blocked_preflight || {};
    if (included.blocked_summary !== BLOCKED_SUMMARY_TEMPLATE) {
        errors.push(`included_blocked_preflight.blocked_summary must be ${BLOCKED_SUMMARY_TEMPLATE}`);
    }
    if (included.primary_blocking_reason !== PRIMARY_BLOCKING_REASON) {
        errors.push(`included_blocked_preflight.primary_blocking_reason must be ${PRIMARY_BLOCKING_REASON}`);
    }
    validateSafety(parsedYaml, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        intake: args.intake,
        blocked_summary: args.blocked_summary,
        intake_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        intake_valid: true,
        blocked_summary_valid: true,
        errors: [],
        warnings: [
            'Phase 4.90D remains template-only.',
            'Real parameters remain unprovided and do not authorize network execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
        ],
    };
}

function runValidation(args, dependencies = {}) {
    const localDeps = {
        cwd: dependencies.cwd || process.cwd(),
        existsSync: dependencies.existsSync || fs.existsSync,
        readFileSync: dependencies.readFileSync || fs.readFileSync,
    };

    const cliPayload = validateCliArgsOrPayload(args);
    if (cliPayload) return cliPayload;

    const intakeLoad = loadYamlFile(args, localDeps, 'intake', 'intake', 'intake-error');
    if (intakeLoad.payload) return intakeLoad.payload;

    const intakeValidation = validateParsedYaml(intakeLoad.parsedYaml);
    if (!intakeValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'intake-error',
            intake_found: true,
            yaml_block_found: true,
            required_fields_present: intakeValidation.missingFields.length === 0,
            missing_fields: intakeValidation.missingFields,
            errors: intakeValidation.errors,
        });
    }

    const blockedLoad = loadYamlFile(args, localDeps, 'blocked_summary', 'blocked summary', 'blocked-summary-error');
    if (blockedLoad.payload) {
        return {
            ...blockedLoad.payload,
            intake_found: true,
            intake_valid: true,
        };
    }

    const blockedValidation = validateBlockedSummaryYaml(blockedLoad.parsedYaml);
    if (!blockedValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'blocked-summary-error',
            intake_found: true,
            blocked_summary_found: true,
            yaml_block_found: true,
            intake_valid: true,
            errors: blockedValidation.errors,
            missing_fields: blockedValidation.missingFields || [],
        });
    }

    return buildSuccessPayload(args);
}

function writePayload(payload, io) {
    io.stdout(`${JSON.stringify(payload, null, 2)}\n`);
}

function main(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const output = { stdout: io.stdout || (text => process.stdout.write(text)) };
    try {
        const args = parseArgs(argv);
        if (args.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }
        if (args.commit) {
            writePayload(buildBlockedCommitPayload(args), output);
            return 1;
        }
        const payload = runValidation(args, dependencies);
        writePayload(payload, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        writePayload(buildFailurePayload({}, { mode: 'argument-error', errors: [error.message] }), output);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    OUTPUT_PHASE,
    TEMPLATE_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    parseIntakeYaml,
    validateParsedYaml,
    runValidation,
    main,
};
