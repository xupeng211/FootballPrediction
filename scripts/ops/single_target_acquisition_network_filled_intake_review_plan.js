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
const {
    runValidation: validateValidationClosure,
} = require('./single_target_acquisition_network_real_parameter_intake_validation_closure');

const OUTPUT_PHASE = 'PHASE4.92D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN';
const TEMPLATE_PHASE = 'PHASE4_92D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN';
const MODE = 'single-target-acquisition-network-filled-intake-review-plan-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition filled-intake review plan execution is not wired in Phase 4.92D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.93D or explicit user-filled real parameter intake';
const INTAKE_TEMPLATE = 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md';
const VALIDATION_CLOSURE_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';

const REVIEW_SEQUENCE_STEPS = [
    'review_real_target',
    'review_source_terms',
    'review_network_authorization',
    'review_proxy_browser_network_policy',
    'review_staging_policy',
    'review_no_db_training_prediction_policy',
    'review_final_human_confirmation',
];

const REVIEW_RULE_GROUPS = [
    'real_target_review',
    'source_terms_review',
    'network_authorization_review',
    'proxy_browser_network_policy_review',
    'staging_policy_review',
    'no_db_training_prediction_review',
    'final_human_confirmation_review',
];

const REVIEW_BLOCKING_REASONS = [
    'filled_intake_not_provided',
    'filled_intake_not_reviewed',
    'real_target_review_not_passed',
    'source_terms_review_not_passed',
    'network_authorization_review_not_passed',
    'proxy_browser_network_policy_review_not_passed',
    'staging_policy_review_not_passed',
    'no_db_training_prediction_review_not_passed',
    'final_human_confirmation_review_not_passed',
    'future_separate_phase_required',
];

const REQUIRED_TOP_FIELDS = words(`
    phase review_plan_status filled_intake_review_ready filled_intake_reviewed
    filled_intake_accepted real_parameters_provided real_parameter_intake_validated
    network_dry_run_authorized network_dry_run_execution_allowed
    staging_write_authorized db_write_authorized training_authorized
    prediction_authorized final_human_confirmation review_sequence
    review_rule_groups review_blocking_reasons included_artifacts
    codex_constraints safety next_phase_requirements
`);

const TOP_FALSE = {
    filled_intake_review_ready: 'filled_intake_review_ready true in template is not allowed',
    filled_intake_reviewed: 'filled_intake_reviewed true in template is not allowed',
    filled_intake_accepted: 'filled_intake_accepted true in template is not allowed',
    real_parameters_provided: 'real_parameters_provided true in template is not allowed',
    real_parameter_intake_validated: 'real_parameter_intake_validated true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

const REVIEW_SEQUENCE_FIELDS = words(`
    step_id name required review_complete review_passed stop_if_failed
`);

const RULE_GROUP_REQUIREMENTS = {
    real_target_review: words(`
        requires_target_source requires_engine_family_titan_discovery
        requires_single_target_scope allows_match_id_scope
        allows_league_season_date_scope max_targets bulk_scope_allowed
        review_passed
    `),
    source_terms_review: words(`
        requires_source_homepage_url requires_terms_url requires_license_url
        requires_allowed_use_summary requires_terms_reviewed_by
        requires_terms_approval_yes review_passed
    `),
    network_authorization_review: words(`
        requires_network_dry_run_authorization_yes requires_external_network_decision
        requires_browser_runtime_decision requires_proxy_runtime_decision
        requires_no_bulk_expansion_confirmation review_passed
    `),
    proxy_browser_network_policy_review: words(`
        requires_proxy_policy requires_browser_policy requires_rate_limit_policy
        requires_retry_policy requires_user_agent_policy
        requires_no_login_paywall_bypass_confirmation
        requires_no_anti_bot_bypass_confirmation review_passed
    `),
    staging_policy_review: words(`
        requires_output_root_policy requires_schema_validation_policy
        requires_source_manifest_policy
        requires_staging_write_authorization_decision review_passed
    `),
    no_db_training_prediction_review: words(`
        requires_no_db_write_confirmation requires_no_training_confirmation
        requires_no_prediction_confirmation
        requires_no_model_artifact_loading_confirmation review_passed
    `),
    final_human_confirmation_review: words(`
        requires_confirmed_by requires_final_confirmation_yes review_passed
    `),
};

const CODEX_CONSTRAINT_FIELDS = words(`
    codex_may_not_self_fill_real_parameters
    codex_may_not_mark_review_passed
    codex_may_not_accept_filled_intake
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
    would_write_filled_intake_review_file
    would_write_db would_train would_predict would_bulk_harvest
`);

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_filled_intake_review_plan.js --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path>',
        '  node scripts/ops/single_target_acquisition_network_filled_intake_review_plan.js --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path> --commit',
        '',
        'Safety:',
        '  Phase 4.92D previews a local filled-intake review plan template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        review_plan: '',
        intake: '',
        validation_closure: '',
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
        filled_intake_review_plan_template_only: true,
        review_plan_valid: false,
        real_parameter_intake_valid: false,
        validation_closure_valid: false,
        blocked_summary_valid: false,
        filled_intake_review_ready: false,
        filled_intake_reviewed: false,
        filled_intake_accepted: false,
        real_parameters_provided: false,
        real_parameter_intake_validated: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        review_sequence_complete: false,
        review_sequence_passed: false,
        review_rule_groups_complete: false,
        review_rule_groups_passed: false,
        review_blocking_reasons: REVIEW_BLOCKING_REASONS,
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
        would_write_filled_intake_review_file: false,
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
        review_plan: args.review_plan || null,
        intake: args.intake || null,
        validation_closure: args.validation_closure || null,
        blocked_summary: args.blocked_summary || null,
        review_plan_found: false,
        intake_found: false,
        validation_closure_found: false,
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
            'no_filled_intake_review_file_writes',
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
    if (!args.review_plan) errors.push('missing review plan');
    if (!args.intake) errors.push('missing intake');
    if (!args.validation_closure) errors.push('missing validation closure');
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
    addMissingNested(
        parsedYaml,
        'included_artifacts',
        words('real_parameter_intake validation_closure blocked_summary'),
        missingFields
    );
    addMissingNested(parsedYaml, 'codex_constraints', CODEX_CONSTRAINT_FIELDS, missingFields);
    addMissingNested(parsedYaml, 'safety', SAFETY_FIELDS, missingFields);
    return missingFields;
}

function validateTopLevelFalse(parsedYaml, errors) {
    Object.entries(TOP_FALSE).forEach(([fieldName, message]) => {
        if (parsedYaml[fieldName] !== false) errors.push(message);
    });
}

function validateReviewSequence(parsedYaml, errors) {
    const sequence = parsedYaml.review_sequence;
    if (!sequence || typeof sequence !== 'object' || Array.isArray(sequence)) {
        errors.push('missing review_sequence');
        return;
    }
    REVIEW_SEQUENCE_STEPS.forEach((stepName, index) => {
        const step = sequence[stepName];
        if (!step || typeof step !== 'object') {
            errors.push('missing review_sequence step: ' + stepName);
            return;
        }
        if (step.step_id !== index + 1) {
            errors.push('review_sequence.' + stepName + '.step_id must be ' + (index + 1));
        }
        if (step.required !== true) {
            errors.push('review_sequence.' + stepName + '.required must be true');
        }
        if (step.stop_if_failed !== true) {
            errors.push('review_sequence.' + stepName + '.stop_if_failed must be true');
        }
        if (step.review_complete !== false) {
            errors.push('review_sequence.' + stepName + '.review_complete true in template is not allowed');
        }
        if (step.review_passed !== false) {
            errors.push('review_sequence.' + stepName + '.review_passed true in template is not allowed');
        }
    });
}

function validateRuleGroups(parsedYaml, errors) {
    const groups = parsedYaml.review_rule_groups || {};
    REVIEW_RULE_GROUPS.forEach(groupName => {
        const group = groups[groupName];
        if (!group || typeof group !== 'object' || Array.isArray(group)) {
            errors.push('missing review rule group: ' + groupName);
            return;
        }
        if (group.review_passed !== false) {
            errors.push('review_rule_groups.' + groupName + '.review_passed true in template is not allowed');
        }
        RULE_GROUP_REQUIREMENTS[groupName]
            .filter(fieldName => fieldName !== 'review_passed')
            .forEach(fieldName => {
                if (fieldName === 'max_targets' && group.max_targets !== 1) {
                    errors.push('max_targets > 1 is not allowed in the Phase 4.92D review plan template');
                    return;
                }
                if (fieldName === 'bulk_scope_allowed' && group.bulk_scope_allowed !== false) {
                    errors.push('bulk_scope_allowed true is not allowed in the Phase 4.92D review plan template');
                    return;
                }
                if (!['max_targets', 'bulk_scope_allowed'].includes(fieldName) && group[fieldName] !== true) {
                    errors.push('review_rule_groups.' + groupName + '.' + fieldName + ' must be true');
                }
            });
    });
}

function validateBlockingReasons(parsedYaml, errors) {
    const reasons = parsedYaml.review_blocking_reasons;
    if (!Array.isArray(reasons)) {
        errors.push('missing review_blocking_reasons');
        return;
    }
    const missing = REVIEW_BLOCKING_REASONS.filter(reason => !reasons.includes(reason));
    if (missing.length) errors.push('missing review_blocking_reasons: ' + missing.join(','));
}

function validateIncludedArtifacts(parsedYaml, errors) {
    const included = parsedYaml.included_artifacts || {};
    if (included.real_parameter_intake !== INTAKE_TEMPLATE) {
        errors.push('included_artifacts.real_parameter_intake must be ' + INTAKE_TEMPLATE);
    }
    if (included.validation_closure !== VALIDATION_CLOSURE_TEMPLATE) {
        errors.push('included_artifacts.validation_closure must be ' + VALIDATION_CLOSURE_TEMPLATE);
    }
    if (included.blocked_summary !== BLOCKED_SUMMARY_TEMPLATE) {
        errors.push('included_artifacts.blocked_summary must be ' + BLOCKED_SUMMARY_TEMPLATE);
    }
}

function validateCodexConstraints(parsedYaml, errors) {
    const constraints = parsedYaml.codex_constraints || {};
    CODEX_CONSTRAINT_FIELDS.forEach(fieldName => {
        if (constraints[fieldName] !== true) {
            errors.push('codex_constraints.' + fieldName + ' false is not allowed');
        }
    });
}

function validateSafety(parsedYaml, errors) {
    const safety = parsedYaml.safety || {};
    SAFETY_FIELDS.forEach(fieldName => {
        if (safety[fieldName] !== false) {
            errors.push('safety.' + fieldName + ' must remain false');
        }
    });
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) errors.push('missing required fields: ' + missingFields.join(','));
    if (parsedYaml.phase !== TEMPLATE_PHASE) errors.push('phase must be ' + TEMPLATE_PHASE);
    if (parsedYaml.review_plan_status !== 'template_only') {
        errors.push('review_plan_status not template_only');
    }
    validateTopLevelFalse(parsedYaml, errors);
    validateReviewSequence(parsedYaml, errors);
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
        review_plan: args.review_plan,
        intake: args.intake,
        validation_closure: args.validation_closure,
        blocked_summary: args.blocked_summary,
        review_plan_found: true,
        intake_found: true,
        validation_closure_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        review_plan_valid: true,
        real_parameter_intake_valid: true,
        validation_closure_valid: true,
        blocked_summary_valid: true,
        review_sequence_complete: true,
        review_sequence_passed: false,
        review_rule_groups_complete: true,
        review_rule_groups_passed: false,
        errors: [],
        warnings: [
            'Phase 4.92D remains template-only.',
            'Filled-intake review plan does not authorize network execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
            'no_filled_intake_review_file_writes',
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

    const planLoad = loadYamlFile(args, localDeps, 'review_plan', 'review plan', 'review-plan-error');
    if (planLoad.payload) return planLoad.payload;

    const planValidation = validateParsedYaml(planLoad.parsedYaml);
    if (!planValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'review-plan-error',
            review_plan_found: true,
            yaml_block_found: true,
            required_fields_present: planValidation.missingFields.length === 0,
            missing_fields: planValidation.missingFields,
            errors: planValidation.errors,
        });
    }

    const intakePayload = validateRealParameterIntake(
        { intake: args.intake, blocked_summary: args.blocked_summary },
        localDeps
    );
    if (!intakePayload.ok) {
        return buildFailurePayload(args, {
            mode: 'intake-error',
            review_plan_found: true,
            review_plan_valid: true,
            yaml_block_found: true,
            real_parameter_intake_valid: false,
            errors: intakePayload.errors || ['real parameter intake validation failed'],
        });
    }

    const closurePayload = validateValidationClosure(
        { validation_closure: args.validation_closure, intake: args.intake, blocked_summary: args.blocked_summary },
        localDeps
    );
    if (!closurePayload.ok) {
        return buildFailurePayload(args, {
            mode: 'validation-closure-error',
            review_plan_found: true,
            review_plan_valid: true,
            real_parameter_intake_valid: true,
            validation_closure_valid: false,
            yaml_block_found: true,
            errors: closurePayload.errors || ['validation closure validation failed'],
        });
    }

    return buildSuccessPayload(args);
}

function writePayload(payload, io) {
    io.stdout(JSON.stringify(payload, null, 2) + '\n');
}

function main(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const output = { stdout: io.stdout || (text => process.stdout.write(text)) };
    try {
        const args = parseArgs(argv);
        if (args.help) {
            output.stdout(usage() + '\n');
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
    REVIEW_SEQUENCE_STEPS,
    REVIEW_RULE_GROUPS,
    REVIEW_BLOCKING_REASONS,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
