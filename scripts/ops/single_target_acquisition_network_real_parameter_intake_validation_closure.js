#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    parseIntakeYaml,
    runValidation: validateRealParameterIntake,
} = require('./single_target_acquisition_network_real_parameter_intake');

const OUTPUT_PHASE = 'PHASE4.91D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE';
const TEMPLATE_PHASE = 'PHASE4_91D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE';
const MODE = 'single-target-acquisition-network-real-parameter-validation-closure-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition real-parameter intake validation closure execution is not wired in Phase 4.91D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.92D or explicit user-filled real parameter intake';
const REAL_PARAMETER_INTAKE_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';

const VALIDATION_RULE_GROUPS = [
    'real_target_validation',
    'source_terms_validation',
    'network_authorization_validation',
    'staging_policy_validation',
    'no_db_training_prediction_validation',
    'final_human_confirmation_validation',
];

const VALIDATION_BLOCKING_REASONS = [
    'real_parameters_not_provided',
    'real_target_not_validated',
    'source_terms_not_validated',
    'network_authorization_not_validated',
    'staging_policy_not_validated',
    'no_db_training_prediction_policy_not_validated',
    'final_human_confirmation_not_validated',
    'future_separate_phase_required',
];

const REQUIRED_TOP_FIELDS = words(`
    phase validation_closure_status real_parameter_intake_validation_ready
    real_parameter_intake_validated real_parameters_provided
    network_dry_run_authorized network_dry_run_execution_allowed
    staging_write_authorized db_write_authorized training_authorized
    prediction_authorized final_human_confirmation validation_rule_groups
    validation_blocking_reasons included_artifacts codex_constraints safety
    next_phase_requirements
`);

const TOP_FALSE = {
    real_parameter_intake_validation_ready: 'real_parameter_intake_validation_ready true in template is not allowed',
    real_parameter_intake_validated: 'real_parameter_intake_validated true in template is not allowed',
    real_parameters_provided: 'real_parameters_provided true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

const RULE_GROUP_REQUIREMENTS = {
    real_target_validation: words(`
        required rule_complete validation_passed requires_target_source
        requires_engine_family_titan_discovery requires_single_target_scope
        allows_match_id_scope allows_league_season_date_scope max_targets
        bulk_scope_allowed
    `),
    source_terms_validation: words(`
        required rule_complete validation_passed requires_source_homepage_url
        requires_terms_url requires_license_url requires_allowed_use_summary
        requires_terms_reviewed_by requires_terms_approval_yes
    `),
    network_authorization_validation: words(`
        required rule_complete validation_passed
        requires_network_dry_run_authorization_yes
        requires_allow_external_network_yes_or_explicit_no
        requires_browser_runtime_policy requires_proxy_runtime_policy
        requires_no_bulk_expansion_confirmation
    `),
    staging_policy_validation: words(`
        required rule_complete validation_passed requires_output_root_policy
        requires_schema_validation requires_source_manifest_policy
        requires_staging_write_authorization_decision
    `),
    no_db_training_prediction_validation: words(`
        required rule_complete validation_passed requires_no_db_write_confirmation
        requires_no_training_confirmation requires_no_prediction_confirmation
        requires_no_model_artifact_loading_confirmation
    `),
    final_human_confirmation_validation: words(`
        required rule_complete validation_passed requires_confirmed_by
        requires_final_confirmation_yes
    `),
};

const CODEX_CONSTRAINT_FIELDS = words(`
    codex_may_not_self_fill_real_parameters
    codex_may_not_mark_validation_passed
    codex_may_not_authorize_network
    codex_may_not_enable_execution
    codex_may_not_write_runtime_files
`);

const SAFETY_FIELDS = words(`
    would_access_network would_launch_browser would_use_proxy
    would_execute_engine would_execute_legacy_titan_discovery
    would_write_staging would_create_staging_directory
    would_write_source_manifest would_write_packet_file
    would_write_approval_packet_file would_write_user_input_closure_file
    would_write_blocked_summary_file would_write_real_parameter_intake_file
    would_write_real_parameter_validation_closure_file
    would_write_db would_train would_predict would_bulk_harvest
`);

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_real_parameter_intake_validation_closure.js --validation-closure <path> --intake <path> --blocked-summary <path>',
        '  node scripts/ops/single_target_acquisition_network_real_parameter_intake_validation_closure.js --validation-closure <path> --intake <path> --blocked-summary <path> --commit',
        '',
        'Safety:',
        '  Phase 4.91D previews a local real-parameter intake validation closure template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        validation_closure: '',
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
        validation_closure_template_only: true,
        validation_closure_valid: false,
        real_parameter_intake_valid: false,
        blocked_summary_valid: false,
        real_parameter_intake_validation_ready: false,
        real_parameter_intake_validated: false,
        real_parameters_provided: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        validation_rule_groups_complete: false,
        validation_rule_groups_passed: false,
        validation_blocking_reasons: VALIDATION_BLOCKING_REASONS,
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
        would_write_real_parameter_validation_closure_file: false,
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
        validation_closure: args.validation_closure || null,
        intake: args.intake || null,
        blocked_summary: args.blocked_summary || null,
        validation_closure_found: false,
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
            'no_real_parameter_validation_closure_file_writes',
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

function validateRequiredCliFields(args) {
    const errors = [];
    if (!args.validation_closure) errors.push('missing validation closure');
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

function getPath(root, dottedPath) {
    return dottedPath.split('.').reduce((current, key) => {
        if (!current || typeof current !== 'object') return undefined;
        return current[key];
    }, root);
}

function addMissingNested(root, parentPath, requiredKeys, missingFields) {
    const value = getPath(root, parentPath);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        missingFields.push(parentPath);
        return;
    }
    requiredKeys.filter(key => !hasOwn(value, key)).forEach(key => missingFields.push(`${parentPath}.${key}`));
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP_FIELDS.filter(key => !hasOwn(parsedYaml, key));
    VALIDATION_RULE_GROUPS.forEach(groupName => {
        addMissingNested(
            parsedYaml,
            `validation_rule_groups.${groupName}`,
            RULE_GROUP_REQUIREMENTS[groupName],
            missingFields
        );
    });
    addMissingNested(parsedYaml, 'included_artifacts', words('real_parameter_intake blocked_summary'), missingFields);
    addMissingNested(parsedYaml, 'codex_constraints', CODEX_CONSTRAINT_FIELDS, missingFields);
    addMissingNested(parsedYaml, 'safety', SAFETY_FIELDS, missingFields);
    return missingFields;
}

function validateTopLevelFalse(parsedYaml, errors) {
    Object.entries(TOP_FALSE).forEach(([fieldName, message]) => {
        if (parsedYaml[fieldName] !== false) errors.push(message);
    });
}

function validateRuleGroups(parsedYaml, errors) {
    const groups = parsedYaml.validation_rule_groups || {};
    VALIDATION_RULE_GROUPS.forEach(groupName => {
        const group = groups[groupName];
        if (!group || typeof group !== 'object' || Array.isArray(group)) {
            errors.push(`missing validation rule group: ${groupName}`);
            return;
        }
        if (group.required !== true) errors.push(`validation_rule_groups.${groupName}.required must be true`);
        if (group.rule_complete !== true) {
            errors.push(`validation_rule_groups.${groupName}.rule_complete must be true`);
        }
        if (group.validation_passed !== false) {
            errors.push(`validation_rule_groups.${groupName}.validation_passed true in template is not allowed`);
        }
        RULE_GROUP_REQUIREMENTS[groupName]
            .filter(fieldName => !['required', 'rule_complete', 'validation_passed'].includes(fieldName))
            .forEach(fieldName => {
                if (fieldName === 'max_targets' && group.max_targets !== 1) {
                    errors.push('max_targets > 1 is not allowed in the Phase 4.91D validation closure template');
                    return;
                }
                if (fieldName === 'bulk_scope_allowed' && group.bulk_scope_allowed !== false) {
                    errors.push(
                        'bulk_scope_allowed true is not allowed in the Phase 4.91D validation closure template'
                    );
                    return;
                }
                if (!['max_targets', 'bulk_scope_allowed'].includes(fieldName) && group[fieldName] !== true) {
                    errors.push(`validation_rule_groups.${groupName}.${fieldName} must be true`);
                }
            });
    });
}

function validateBlockingReasons(parsedYaml, errors) {
    const reasons = parsedYaml.validation_blocking_reasons;
    if (!Array.isArray(reasons)) {
        errors.push('missing validation_blocking_reasons');
        return;
    }
    const missing = VALIDATION_BLOCKING_REASONS.filter(reason => !reasons.includes(reason));
    if (missing.length) errors.push(`missing validation_blocking_reasons: ${missing.join(',')}`);
}

function validateIncludedArtifacts(parsedYaml, errors) {
    const included = parsedYaml.included_artifacts || {};
    if (included.real_parameter_intake !== REAL_PARAMETER_INTAKE_TEMPLATE) {
        errors.push(`included_artifacts.real_parameter_intake must be ${REAL_PARAMETER_INTAKE_TEMPLATE}`);
    }
    if (included.blocked_summary !== BLOCKED_SUMMARY_TEMPLATE) {
        errors.push(`included_artifacts.blocked_summary must be ${BLOCKED_SUMMARY_TEMPLATE}`);
    }
}

function validateCodexConstraints(parsedYaml, errors) {
    const constraints = parsedYaml.codex_constraints || {};
    CODEX_CONSTRAINT_FIELDS.forEach(fieldName => {
        if (constraints[fieldName] !== true) {
            errors.push(`codex_constraints.${fieldName} false is not allowed`);
        }
    });
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
    if (parsedYaml.validation_closure_status !== 'template_only') {
        errors.push('validation_closure_status not template_only');
    }
    validateTopLevelFalse(parsedYaml, errors);
    validateRuleGroups(parsedYaml, errors);
    validateBlockingReasons(parsedYaml, errors);
    validateIncludedArtifacts(parsedYaml, errors);
    validateCodexConstraints(parsedYaml, errors);
    validateSafety(parsedYaml, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        validation_closure: args.validation_closure,
        intake: args.intake,
        blocked_summary: args.blocked_summary,
        validation_closure_found: true,
        intake_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        validation_closure_valid: true,
        real_parameter_intake_valid: true,
        blocked_summary_valid: true,
        validation_rule_groups_complete: true,
        validation_rule_groups_passed: false,
        errors: [],
        warnings: [
            'Phase 4.91D remains template-only.',
            'Validation closure rules do not authorize network execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
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

    const closureLoad = loadYamlFile(
        args,
        localDeps,
        'validation_closure',
        'validation closure',
        'validation-closure-error'
    );
    if (closureLoad.payload) return closureLoad.payload;

    const closureValidation = validateParsedYaml(closureLoad.parsedYaml);
    if (!closureValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'validation-closure-error',
            validation_closure_found: true,
            yaml_block_found: true,
            required_fields_present: closureValidation.missingFields.length === 0,
            missing_fields: closureValidation.missingFields,
            errors: closureValidation.errors,
        });
    }

    const intakePayload = validateRealParameterIntake(
        { intake: args.intake, blocked_summary: args.blocked_summary },
        localDeps
    );
    if (!intakePayload.ok) {
        return buildFailurePayload(args, {
            mode: 'intake-or-blocked-summary-error',
            validation_closure_found: true,
            validation_closure_valid: true,
            validation_rule_groups_complete: true,
            yaml_block_found: true,
            real_parameter_intake_valid: intakePayload.intake_valid === true,
            blocked_summary_valid: intakePayload.blocked_summary_valid === true,
            intake_found: intakePayload.intake_found === true,
            blocked_summary_found: intakePayload.blocked_summary_found === true,
            errors: intakePayload.errors || ['real parameter intake validation failed'],
            missing_fields: intakePayload.missing_fields || [],
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
    VALIDATION_RULE_GROUPS,
    VALIDATION_BLOCKING_REASONS,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
