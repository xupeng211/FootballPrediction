#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const { parseIntakeYaml } = require('./single_target_acquisition_network_real_parameter_intake');
const {
    runValidation: validateHandoffChecklist,
} = require('./single_target_acquisition_network_authorization_handoff_checklist');

const OUTPUT_PHASE = 'PHASE4.95D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION';
const TEMPLATE_PHASE = 'PHASE4_95D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_DECISION';
const MODE = 'single-target-acquisition-network-authorization-decision-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network authorization decision execution is not wired in Phase 4.95D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.96D or explicit user-filled real parameter intake';

const AUTHORIZATION_HANDOFF_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST_TEMPLATE.md';
const REVIEW_RESULT_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT_TEMPLATE.md';
const REVIEW_PLAN_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md';
const INTAKE_TEMPLATE = 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md';
const VALIDATION_CLOSURE_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';

const AUTHORIZATION_DECISION_ALLOWED_VALUES = [
    'not_authorized',
    'denied',
    'needs_revision',
    'conditionally_authorized_for_future_preparation',
];

const DECISION_BLOCKING_REASONS = [
    'authorization_decision_template_only',
    'authorization_handoff_not_completed',
    'filled_intake_review_result_not_accepted',
    'source_terms_not_authorized',
    'network_runtime_not_authorized',
    'staging_not_authorized',
    'db_training_prediction_not_authorized',
    'final_human_confirmation_missing',
    'future_execution_preparation_phase_required',
];

const DECISION_SECTION_FIELDS = {
    scope_decision: w('reviewed decision single_target_confirmed bulk_scope_allowed max_targets blocking_reason'),
    source_terms_decision: w('reviewed decision terms_approved allowed_use_approved blocking_reason'),
    network_runtime_decision: w(
        'reviewed decision external_network_allowed browser_runtime_allowed proxy_runtime_allowed blocking_reason'
    ),
    staging_decision: w('reviewed decision staging_write_allowed source_manifest_write_allowed blocking_reason'),
    db_training_prediction_decision: w(
        'reviewed decision db_write_allowed training_allowed prediction_allowed model_artifact_loading_allowed blocking_reason'
    ),
    final_human_decision: w('reviewed decision final_confirmation confirmed_by blocking_reason'),
};

const REQUIRED_TOP = w(
    'phase authorization_decision_status network_authorization_decision_ready network_authorization_decision_recorded network_dry_run_authorized network_dry_run_execution_allowed authorization_decision authorization_decision_allowed_values filled_intake_reviewed filled_intake_accepted authorization_handoff_ready authorization_handoff_completed can_proceed_to_network_dry_run_preparation staging_write_authorized db_write_authorized training_authorized prediction_authorized final_human_confirmation included_artifacts decision_metadata decision_sections authorization_boundaries decision_blocking_reasons codex_constraints safety next_phase_requirements'
);

const TOP_FALSE = {
    network_authorization_decision_ready: 'network_authorization_decision_ready true is not allowed',
    network_authorization_decision_recorded: 'network_authorization_decision_recorded true is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true is not allowed',
    filled_intake_reviewed: 'filled_intake_reviewed true is not allowed',
    filled_intake_accepted: 'filled_intake_accepted true is not allowed',
    authorization_handoff_ready: 'authorization_handoff_ready true is not allowed',
    authorization_handoff_completed: 'authorization_handoff_completed true is not allowed',
    can_proceed_to_network_dry_run_preparation: 'can_proceed_to_network_dry_run_preparation true is not allowed',
    staging_write_authorized: 'staging_write_authorized true is not allowed',
    db_write_authorized: 'db_write_authorized true is not allowed',
    training_authorized: 'training_authorized true is not allowed',
    prediction_authorized: 'prediction_authorized true is not allowed',
    final_human_confirmation: 'final_human_confirmation true is not allowed',
};

const INCLUDED_ARTIFACT_FIELDS = {
    authorization_handoff_checklist: AUTHORIZATION_HANDOFF_TEMPLATE,
    filled_intake_review_result: REVIEW_RESULT_TEMPLATE,
    filled_intake_review_plan: REVIEW_PLAN_TEMPLATE,
    real_parameter_intake: INTAKE_TEMPLATE,
    validation_closure: VALIDATION_CLOSURE_TEMPLATE,
    blocked_summary: BLOCKED_SUMMARY_TEMPLATE,
};

const DECISION_METADATA_FIELDS = w(
    'decision_maker decision_made_at decision_notes source_of_authorization authorization_decision_id template_only'
);
const AUTHORIZATION_BOUNDARY_FIELDS = w(
    'authorization_decision_is_not_execution future_execution_preparation_phase_required future_final_confirmation_required codex_may_not_authorize_network codex_may_not_enable_execution codex_may_not_self_approve_terms codex_may_not_self_accept_handoff codex_may_not_convert_decision_to_execution'
);
const CODEX_FIELDS = w(
    'codex_may_not_self_fill_real_parameters codex_may_not_mark_decision_recorded codex_may_not_authorize_network codex_may_not_set_execution_allowed codex_may_not_mark_reviewed codex_may_not_write_runtime_files'
);
const SAFETY_FIELDS = w(
    'would_access_network would_launch_browser would_use_proxy would_execute_engine would_execute_legacy_titan_discovery would_write_staging would_create_staging_directory would_write_source_manifest would_write_packet_file would_write_approval_packet_file would_write_user_input_closure_file would_write_blocked_summary_file would_write_real_parameter_intake_file would_write_real_parameter_validation_closure_file would_write_filled_intake_review_file would_write_filled_intake_review_result_file would_write_authorization_handoff_checklist_file would_write_network_authorization_decision_file would_write_db would_train would_predict would_bulk_harvest would_spawn_child_process'
);

function w(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_authorization_decision.js --authorization-decision <path> --handoff-checklist <path> --review-result <path> --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path>',
        '',
        'Safety: Phase 4.95D previews a local network authorization decision template only. No network, no writes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        authorization_decision: '',
        handoff_checklist: '',
        review_result: '',
        review_plan: '',
        intake: '',
        validation_closure: '',
        blocked_summary: '',
        commit: false,
        help: false,
    };
    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];
        if (token === '--commit') {
            args.commit = true;
            continue;
        }
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        if (!token.startsWith('--')) throw new Error('Unknown: ' + token);
        const eqIndex = token.indexOf('=');
        if (eqIndex !== -1) {
            args[token.slice(2, eqIndex).replace(/-/g, '_')] = token.slice(eqIndex + 1);
        } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
            args[token.slice(2).replace(/-/g, '_')] = String(argv[i + 1] || '');
            i += 1;
        } else {
            throw new Error('Unknown: ' + token);
        }
    }
    return args;
}

function buildSafetyFlags() {
    return {
        network_authorization_decision_template_only: true,
        authorization_decision_valid: false,
        handoff_checklist_valid: false,
        review_result_valid: false,
        review_plan_valid: false,
        real_parameter_intake_valid: false,
        validation_closure_valid: false,
        blocked_summary_valid: false,
        network_authorization_decision_ready: false,
        network_authorization_decision_recorded: false,
        authorization_decision: 'not_authorized',
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        authorization_decision_is_not_execution: true,
        future_execution_preparation_phase_required: true,
        future_final_confirmation_required: true,
        can_proceed_to_network_dry_run_preparation: false,
        authorization_handoff_ready: false,
        authorization_handoff_completed: false,
        filled_intake_reviewed: false,
        filled_intake_accepted: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        decision_sections_complete: false,
        decision_sections_authorized: false,
        decision_blocking_reasons: DECISION_BLOCKING_REASONS,
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
        would_write_filled_intake_review_result_file: false,
        would_write_authorization_handoff_checklist_file: false,
        would_write_network_authorization_decision_file: false,
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
        authorization_decision_path: args.authorization_decision || null,
        handoff_checklist: args.handoff_checklist || null,
        review_result: args.review_result || null,
        review_plan: args.review_plan || null,
        intake: args.intake || null,
        validation_closure: args.validation_closure || null,
        blocked_summary: args.blocked_summary || null,
        authorization_decision_found: false,
        handoff_checklist_found: false,
        review_result_found: false,
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
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
            'no_filled_intake_review_file_writes',
            'no_filled_intake_review_result_file_writes',
            'no_authorization_handoff_checklist_file_writes',
            'no_network_authorization_decision_file_writes',
            'no_legacy_titan_discovery_execution',
            'no_child_process_spawn',
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

function resolveLocalPath(rawPath, cwd) {
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function validateRequiredCliFields(args) {
    const errors = [];
    if (!args.authorization_decision) errors.push('missing authorization decision');
    if (!args.handoff_checklist) errors.push('missing handoff checklist');
    if (!args.review_result) errors.push('missing review result');
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

function loadYamlFile(args, deps, fieldName, missingLabel, mode) {
    const targetPath = resolveLocalPath(args[fieldName], deps.cwd);
    if (!deps.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: false,
                errors: ['missing ' + missingLabel + ': ' + toRelativePath(targetPath, deps.cwd)],
            }),
        };
    }

    const yamlText = extractYamlBlock(deps.readFileSync(targetPath, 'utf8'));
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
                errors: ['invalid YAML: ' + error.message],
            }),
        };
    }
}

function hasOwn(root, key) {
    return Object.prototype.hasOwnProperty.call(root, key);
}

function gp(root, dottedPath) {
    return dottedPath.split('.').reduce((current, key) => {
        if (!current || typeof current !== 'object') return undefined;
        return current[key];
    }, root);
}

function addMissing(root, parentPath, requiredKeys, missingFields) {
    const value = gp(root, parentPath);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        missingFields.push(parentPath);
        return;
    }
    requiredKeys.filter(key => !hasOwn(value, key)).forEach(key => missingFields.push(parentPath + '.' + key));
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP.filter(key => !hasOwn(parsedYaml, key));
    addMissing(parsedYaml, 'included_artifacts', Object.keys(INCLUDED_ARTIFACT_FIELDS), missingFields);
    addMissing(parsedYaml, 'decision_metadata', DECISION_METADATA_FIELDS, missingFields);
    Object.entries(DECISION_SECTION_FIELDS).forEach(([sectionName, fields]) => {
        addMissing(parsedYaml, 'decision_sections.' + sectionName, fields, missingFields);
    });
    addMissing(parsedYaml, 'authorization_boundaries', AUTHORIZATION_BOUNDARY_FIELDS, missingFields);
    addMissing(parsedYaml, 'codex_constraints', CODEX_FIELDS, missingFields);
    addMissing(parsedYaml, 'safety', SAFETY_FIELDS, missingFields);
    return missingFields;
}

function validateAllowedValues(parsedYaml, errors) {
    const values = parsedYaml.authorization_decision_allowed_values;
    if (!Array.isArray(values)) {
        errors.push('authorization_decision_allowed_values missing');
        return;
    }
    const missing = AUTHORIZATION_DECISION_ALLOWED_VALUES.filter(value => !values.includes(value));
    if (missing.length) errors.push('missing authorization_decision_allowed_values: ' + missing.join(','));
}

function validateTopLevelFalse(parsedYaml, errors) {
    Object.entries(TOP_FALSE).forEach(([key, message]) => {
        if (parsedYaml[key] !== false) errors.push(message);
    });
}

function validateIncludedArtifacts(parsedYaml, errors) {
    const included = parsedYaml.included_artifacts || {};
    Object.entries(INCLUDED_ARTIFACT_FIELDS).forEach(([field, expected]) => {
        if (included[field] !== expected) errors.push('included_artifacts.' + field + ' must be ' + expected);
    });
}

function validateDecisionMetadata(parsedYaml, errors) {
    const metadata = parsedYaml.decision_metadata || {};
    if (metadata.template_only !== true) errors.push('decision_metadata.template_only must be true');
}

function validateDecisionSectionCommon(sectionName, section, errors) {
    if (!section || typeof section !== 'object' || Array.isArray(section)) {
        errors.push('missing decision_sections.' + sectionName);
        return false;
    }
    if (section.reviewed !== false) {
        errors.push('decision_sections.' + sectionName + '.reviewed true is not allowed');
    }
    if (section.decision !== 'not_authorized') {
        errors.push('decision_sections.' + sectionName + '.decision not not_authorized');
    }
    return true;
}

function requireFalse(sectionName, section, field, errors) {
    if (section[field] !== false) {
        errors.push('decision_sections.' + sectionName + '.' + field + ' true is not allowed');
    }
}

function validateDecisionSections(parsedYaml, errors) {
    const sections = parsedYaml.decision_sections || {};

    const scope = sections.scope_decision;
    if (validateDecisionSectionCommon('scope_decision', scope, errors)) {
        requireFalse('scope_decision', scope, 'single_target_confirmed', errors);
        requireFalse('scope_decision', scope, 'bulk_scope_allowed', errors);
        if (typeof scope.max_targets !== 'number') {
            errors.push('decision_sections.scope_decision.max_targets must be 1');
        } else if (scope.max_targets > 1) {
            errors.push('decision_sections.scope_decision.max_targets > 1 is not allowed');
        } else if (scope.max_targets !== 1) {
            errors.push('decision_sections.scope_decision.max_targets must be 1');
        }
    }

    const sourceTerms = sections.source_terms_decision;
    if (validateDecisionSectionCommon('source_terms_decision', sourceTerms, errors)) {
        requireFalse('source_terms_decision', sourceTerms, 'terms_approved', errors);
        requireFalse('source_terms_decision', sourceTerms, 'allowed_use_approved', errors);
    }

    const runtime = sections.network_runtime_decision;
    if (validateDecisionSectionCommon('network_runtime_decision', runtime, errors)) {
        requireFalse('network_runtime_decision', runtime, 'external_network_allowed', errors);
        requireFalse('network_runtime_decision', runtime, 'browser_runtime_allowed', errors);
        requireFalse('network_runtime_decision', runtime, 'proxy_runtime_allowed', errors);
    }

    const staging = sections.staging_decision;
    if (validateDecisionSectionCommon('staging_decision', staging, errors)) {
        requireFalse('staging_decision', staging, 'staging_write_allowed', errors);
        requireFalse('staging_decision', staging, 'source_manifest_write_allowed', errors);
    }

    const dbTrainingPrediction = sections.db_training_prediction_decision;
    if (validateDecisionSectionCommon('db_training_prediction_decision', dbTrainingPrediction, errors)) {
        requireFalse('db_training_prediction_decision', dbTrainingPrediction, 'db_write_allowed', errors);
        requireFalse('db_training_prediction_decision', dbTrainingPrediction, 'training_allowed', errors);
        requireFalse('db_training_prediction_decision', dbTrainingPrediction, 'prediction_allowed', errors);
        requireFalse('db_training_prediction_decision', dbTrainingPrediction, 'model_artifact_loading_allowed', errors);
    }

    const finalHuman = sections.final_human_decision;
    if (validateDecisionSectionCommon('final_human_decision', finalHuman, errors)) {
        requireFalse('final_human_decision', finalHuman, 'final_confirmation', errors);
    }
}

function validateAuthorizationBoundaries(parsedYaml, errors) {
    const boundaries = parsedYaml.authorization_boundaries || {};
    AUTHORIZATION_BOUNDARY_FIELDS.forEach(field => {
        if (boundaries[field] !== true) errors.push('authorization_boundaries.' + field + ' must be true');
    });
}

function validateBlockingReasons(parsedYaml, errors) {
    const reasons = parsedYaml.decision_blocking_reasons;
    if (!Array.isArray(reasons)) {
        errors.push('missing decision_blocking_reasons');
        return;
    }
    const missing = DECISION_BLOCKING_REASONS.filter(reason => !reasons.includes(reason));
    if (missing.length) errors.push('missing decision_blocking_reasons: ' + missing.join(','));
}

function validateCodexConstraints(parsedYaml, errors) {
    const constraints = parsedYaml.codex_constraints || {};
    CODEX_FIELDS.forEach(field => {
        if (constraints[field] !== true) errors.push('codex_constraints.' + field + ' false is not allowed');
    });
}

function validateSafety(parsedYaml, errors) {
    const safety = parsedYaml.safety || {};
    SAFETY_FIELDS.forEach(field => {
        if (safety[field] !== false) errors.push('safety.' + field + ' must remain false');
    });
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) errors.push('missing required fields: ' + missingFields.join(','));
    if (parsedYaml.phase !== TEMPLATE_PHASE) errors.push('phase must be ' + TEMPLATE_PHASE);
    if (parsedYaml.authorization_decision_status !== 'template_only') {
        errors.push('authorization_decision_status not template_only');
    }
    if (parsedYaml.authorization_decision !== 'not_authorized') {
        errors.push('authorization_decision not not_authorized');
    }
    validateAllowedValues(parsedYaml, errors);
    validateTopLevelFalse(parsedYaml, errors);
    validateIncludedArtifacts(parsedYaml, errors);
    validateDecisionMetadata(parsedYaml, errors);
    validateDecisionSections(parsedYaml, errors);
    validateAuthorizationBoundaries(parsedYaml, errors);
    validateBlockingReasons(parsedYaml, errors);
    validateCodexConstraints(parsedYaml, errors);
    validateSafety(parsedYaml, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function pickHandoffFlags(payload) {
    return {
        handoff_checklist_found: payload.handoff_checklist_found || false,
        review_result_found: payload.review_result_found || false,
        review_plan_found: payload.review_plan_found || false,
        intake_found: payload.intake_found || false,
        validation_closure_found: payload.validation_closure_found || false,
        blocked_summary_found: payload.blocked_summary_found || false,
        handoff_checklist_valid: payload.handoff_checklist_valid || false,
        review_result_valid: payload.review_result_valid || false,
        review_plan_valid: payload.review_plan_valid || false,
        real_parameter_intake_valid: payload.real_parameter_intake_valid || false,
        validation_closure_valid: payload.validation_closure_valid || false,
        blocked_summary_valid: payload.blocked_summary_valid || false,
    };
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        authorization_decision_path: args.authorization_decision,
        handoff_checklist: args.handoff_checklist,
        review_result: args.review_result,
        review_plan: args.review_plan,
        intake: args.intake,
        validation_closure: args.validation_closure,
        blocked_summary: args.blocked_summary,
        authorization_decision_found: true,
        handoff_checklist_found: true,
        review_result_found: true,
        review_plan_found: true,
        intake_found: true,
        validation_closure_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        authorization_decision_valid: true,
        handoff_checklist_valid: true,
        review_result_valid: true,
        review_plan_valid: true,
        real_parameter_intake_valid: true,
        validation_closure_valid: true,
        blocked_summary_valid: true,
        decision_sections_complete: true,
        decision_sections_authorized: false,
        errors: [],
        warnings: [
            'Phase 4.95D remains template-only.',
            'Authorization decision template does not constitute authorization or execution.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
            'no_filled_intake_review_file_writes',
            'no_filled_intake_review_result_file_writes',
            'no_authorization_handoff_checklist_file_writes',
            'no_network_authorization_decision_file_writes',
            'no_legacy_titan_discovery_execution',
            'no_child_process_spawn',
        ],
    };
}

function runValidation(args, dependencies = {}) {
    const deps = {
        cwd: dependencies.cwd || process.cwd(),
        existsSync: dependencies.existsSync || fs.existsSync,
        readFileSync: dependencies.readFileSync || fs.readFileSync,
    };

    const cliPayload = validateCliArgsOrPayload(args);
    if (cliPayload) return cliPayload;

    const decisionLoad = loadYamlFile(
        args,
        deps,
        'authorization_decision',
        'authorization decision',
        'authorization-decision-error'
    );
    if (decisionLoad.payload) return decisionLoad.payload;

    const decisionValidation = validateParsedYaml(decisionLoad.parsedYaml);
    if (!decisionValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'authorization-decision-error',
            authorization_decision_found: true,
            yaml_block_found: true,
            required_fields_present: decisionValidation.missingFields.length === 0,
            missing_fields: decisionValidation.missingFields,
            errors: decisionValidation.errors,
        });
    }

    const handoffPayload = validateHandoffChecklist(
        {
            handoff_checklist: args.handoff_checklist,
            review_result: args.review_result,
            review_plan: args.review_plan,
            intake: args.intake,
            validation_closure: args.validation_closure,
            blocked_summary: args.blocked_summary,
        },
        deps
    );
    if (!handoffPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'handoff-chain-error',
            authorization_decision_found: true,
            yaml_block_found: true,
            required_fields_present: true,
            authorization_decision_valid: true,
            ...pickHandoffFlags(handoffPayload),
            errors: handoffPayload.errors || ['handoff checklist chain validation failed'],
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
    AUTHORIZATION_DECISION_ALLOWED_VALUES,
    DECISION_BLOCKING_REASONS,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
