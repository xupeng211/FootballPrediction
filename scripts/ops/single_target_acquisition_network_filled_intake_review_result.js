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
const { runValidation: validateReviewPlan } = require('./single_target_acquisition_network_filled_intake_review_plan');

const OUTPUT_PHASE = 'PHASE4.93D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT';
const TEMPLATE_PHASE = 'PHASE4_93D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT';
const MODE = 'single-target-acquisition-network-filled-intake-review-result-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition filled-intake review result execution is not wired in Phase 4.93D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.94D or explicit user-filled real parameter intake';
const REVIEW_PLAN_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md';
const INTAKE_TEMPLATE = 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md';
const VALIDATION_CLOSURE_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';

const REVIEW_SECTIONS = [
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
    'review_result_template_only',
    'future_separate_phase_required',
];

const SECTION_FIELDS = words(`
    reviewed passed result blocking_reason reviewer_notes
`);

const OVERALL_FIELDS = words(`
    status accepted rejected needs_revision
    can_proceed_to_network_dry_run_preparation
    requires_future_separate_phase blocking_reasons
`);

const REQUIRED_TOP_FIELDS = words(`
    phase review_result_status filled_intake_review_result_ready
    filled_intake_reviewed filled_intake_accepted filled_intake_rejected
    filled_intake_needs_revision real_parameters_provided
    real_parameter_intake_validated network_dry_run_authorized
    network_dry_run_execution_allowed staging_write_authorized
    db_write_authorized training_authorized prediction_authorized
    final_human_confirmation review_metadata review_sections
    overall_review_result included_artifacts codex_constraints safety
    next_phase_requirements
`);

const TOP_FALSE = {
    filled_intake_review_result_ready: 'filled_intake_review_result_ready true in template is not allowed',
    filled_intake_reviewed: 'filled_intake_reviewed true in template is not allowed',
    filled_intake_accepted: 'filled_intake_accepted true in template is not allowed',
    filled_intake_rejected: 'filled_intake_rejected true in template is not allowed',
    filled_intake_needs_revision: 'filled_intake_needs_revision true in template is not allowed',
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

const CODEX_CONSTRAINT_FIELDS = words(`
    codex_may_not_self_fill_real_parameters codex_may_not_mark_reviewed
    codex_may_not_mark_passed codex_may_not_accept_filled_intake
    codex_may_not_authorize_network codex_may_not_enable_execution
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
    would_write_filled_intake_review_result_file
    would_write_db would_train would_predict would_bulk_harvest
`);

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_filled_intake_review_result.js --review-result <path> --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path>',
        '  node scripts/ops/single_target_acquisition_network_filled_intake_review_result.js --review-result <path> --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path> --commit',
        '',
        'Safety: Phase 4.93D previews a local filled-intake review result template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        review_result: '',
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
        if (!token.startsWith('--')) throw new Error('Unknown argument: ' + token);
        const eqIndex = token.indexOf('=');
        if (eqIndex !== -1) {
            args[token.slice(2, eqIndex).replace(/-/g, '_')] = token.slice(eqIndex + 1);
        } else if (index + 1 < argv.length && !argv[index + 1].startsWith('--')) {
            args[token.slice(2).replace(/-/g, '_')] = String(argv[index + 1] || '');
            index += 1;
        } else {
            throw new Error('Unknown argument: ' + token);
        }
    }
    return args;
}

function buildSafetyFlags() {
    return {
        filled_intake_review_result_template_only: true,
        review_result_valid: false,
        review_plan_valid: false,
        real_parameter_intake_valid: false,
        validation_closure_valid: false,
        blocked_summary_valid: false,
        filled_intake_review_result_ready: false,
        filled_intake_reviewed: false,
        filled_intake_accepted: false,
        filled_intake_rejected: false,
        filled_intake_needs_revision: false,
        real_parameters_provided: false,
        real_parameter_intake_validated: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        review_sections_complete: false,
        review_sections_passed: false,
        overall_review_status: 'not_reviewed',
        can_proceed_to_network_dry_run_preparation: false,
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
        would_write_filled_intake_review_result_file: false,
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
        review_result: args.review_result || null,
        review_plan: args.review_plan || null,
        intake: args.intake || null,
        validation_closure: args.validation_closure || null,
        blocked_summary: args.blocked_summary || null,
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
            'no_legacy_titan_discovery_execution',
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
    if (!args.review_result) errors.push('missing review result');
    if (!args.review_plan) errors.push('missing review plan');
    if (!args.intake) errors.push('missing intake');
    if (!args.validation_closure) errors.push('missing validation closure');
    if (!args.blocked_summary) errors.push('missing blocked summary');
    return errors;
}

function validateCliArgsOrPayload(args) {
    const errs = validateRequiredCliFields(args);
    return errs.length ? buildFailurePayload(args, { mode: 'argument-error', errors: errs }) : null;
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
    } catch (e) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: true,
                yaml_block_found: true,
                errors: ['invalid YAML: ' + e.message],
            }),
        };
    }
}

function hasOwn(root, key) {
    return Object.prototype.hasOwnProperty.call(root, key);
}

function getPath(root, dottedPath) {
    return dottedPath.split('.').reduce((c, k) => {
        if (!c || typeof c !== 'object') return undefined;
        return c[k];
    }, root);
}

function addMissingNested(root, parentPath, requiredKeys, missingFields) {
    const value = getPath(root, parentPath);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        missingFields.push(parentPath);
        return;
    }
    requiredKeys.filter(k => !hasOwn(value, k)).forEach(k => missingFields.push(parentPath + '.' + k));
}

function findMissingFields(parsedYaml) {
    const mf = REQUIRED_TOP_FIELDS.filter(k => !hasOwn(parsedYaml, k));
    REVIEW_SECTIONS.forEach(s => addMissingNested(parsedYaml, 'review_sections.' + s, SECTION_FIELDS, mf));
    addMissingNested(
        parsedYaml,
        'review_metadata',
        words('reviewer reviewed_at review_notes source_of_filled_intake review_result_id template_only'),
        mf
    );
    addMissingNested(parsedYaml, 'overall_review_result', OVERALL_FIELDS, mf);
    addMissingNested(
        parsedYaml,
        'included_artifacts',
        words('filled_intake_review_plan real_parameter_intake validation_closure blocked_summary'),
        mf
    );
    addMissingNested(parsedYaml, 'codex_constraints', CODEX_CONSTRAINT_FIELDS, mf);
    addMissingNested(parsedYaml, 'safety', SAFETY_FIELDS, mf);
    return mf;
}

function validateTopLevelFalse(parsedYaml, errors) {
    Object.entries(TOP_FALSE).forEach(([k, msg]) => {
        if (parsedYaml[k] !== false) errors.push(msg);
    });
}

function validateReviewSections(parsedYaml, errors) {
    const sections = parsedYaml.review_sections || {};
    REVIEW_SECTIONS.forEach(name => {
        const s = sections[name];
        if (!s || typeof s !== 'object' || Array.isArray(s)) {
            errors.push('missing review_sections.' + name);
            return;
        }
        if (s.reviewed !== false) errors.push('review_sections.' + name + '.reviewed true in template is not allowed');
        if (s.passed !== false) errors.push('review_sections.' + name + '.passed true in template is not allowed');
        if (s.result !== 'not_reviewed') {
            errors.push('review_sections.' + name + '.result must be not_reviewed in template');
        }
    });
}

function validateOverallResult(parsedYaml, errors) {
    const overall = parsedYaml.overall_review_result || {};
    if (overall.status !== 'not_reviewed') errors.push('overall_review_result.status must be not_reviewed in template');
    if (overall.accepted !== false) errors.push('overall_review_result.accepted true in template is not allowed');
    if (overall.can_proceed_to_network_dry_run_preparation !== false) {
        errors.push('overall_review_result.can_proceed_to_network_dry_run_preparation true in template is not allowed');
    }
    if (overall.requires_future_separate_phase !== true) {
        errors.push('overall_review_result.requires_future_separate_phase must be true in template');
    }
    if (!Array.isArray(overall.blocking_reasons)) {
        errors.push('missing overall_review_result.blocking_reasons');
        return;
    }
    const missing = REVIEW_BLOCKING_REASONS.filter(r => !overall.blocking_reasons.includes(r));
    if (missing.length) errors.push('missing overall_review_result.blocking_reasons: ' + missing.join(','));
}

function validateIncludedArtifacts(parsedYaml, errors) {
    const inc = parsedYaml.included_artifacts || {};
    if (inc.filled_intake_review_plan !== REVIEW_PLAN_TEMPLATE) {
        errors.push('included_artifacts.filled_intake_review_plan must be ' + REVIEW_PLAN_TEMPLATE);
    }
    if (inc.real_parameter_intake !== INTAKE_TEMPLATE) {
        errors.push('included_artifacts.real_parameter_intake must be ' + INTAKE_TEMPLATE);
    }
    if (inc.validation_closure !== VALIDATION_CLOSURE_TEMPLATE) {
        errors.push('included_artifacts.validation_closure must be ' + VALIDATION_CLOSURE_TEMPLATE);
    }
    if (inc.blocked_summary !== BLOCKED_SUMMARY_TEMPLATE) {
        errors.push('included_artifacts.blocked_summary must be ' + BLOCKED_SUMMARY_TEMPLATE);
    }
}

function validateCodexConstraints(parsedYaml, errors) {
    const cc = parsedYaml.codex_constraints || {};
    CODEX_CONSTRAINT_FIELDS.forEach(f => {
        if (cc[f] !== true) errors.push('codex_constraints.' + f + ' false is not allowed');
    });
}

function validateSafety(parsedYaml, errors) {
    const s = parsedYaml.safety || {};
    SAFETY_FIELDS.forEach(f => {
        if (s[f] !== false) errors.push('safety.' + f + ' must remain false');
    });
}

function validateReviewMetadata(parsedYaml, errors) {
    const meta = parsedYaml.review_metadata || {};
    if (meta.template_only !== true) errors.push('review_metadata.template_only must be true in template');
    if (meta.reviewer) errors.push('review_metadata.reviewer must be empty in template');
    if (meta.reviewed_at) errors.push('review_metadata.reviewed_at must be empty in template');
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const mf = findMissingFields(parsedYaml);
    if (mf.length) errors.push('missing required fields: ' + mf.join(','));
    if (parsedYaml.phase !== TEMPLATE_PHASE) errors.push('phase must be ' + TEMPLATE_PHASE);
    if (parsedYaml.review_result_status !== 'template_only') errors.push('review_result_status not template_only');
    validateTopLevelFalse(parsedYaml, errors);
    validateReviewMetadata(parsedYaml, errors);
    validateReviewSections(parsedYaml, errors);
    validateOverallResult(parsedYaml, errors);
    validateIncludedArtifacts(parsedYaml, errors);
    validateCodexConstraints(parsedYaml, errors);
    validateSafety(parsedYaml, errors);
    return { ok: errors.length === 0, missingFields: mf, errors };
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        review_result: args.review_result,
        review_plan: args.review_plan,
        intake: args.intake,
        validation_closure: args.validation_closure,
        blocked_summary: args.blocked_summary,
        review_result_found: true,
        review_plan_found: true,
        intake_found: true,
        validation_closure_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        review_result_valid: true,
        review_plan_valid: true,
        real_parameter_intake_valid: true,
        validation_closure_valid: true,
        blocked_summary_valid: true,
        review_sections_complete: true,
        review_sections_passed: false,
        overall_review_status: 'not_reviewed',
        can_proceed_to_network_dry_run_preparation: false,
        errors: [],
        warnings: [
            'Phase 4.93D remains template-only.',
            'Filled-intake review result does not authorize network execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
            'no_filled_intake_review_file_writes',
            'no_filled_intake_review_result_file_writes',
            'no_legacy_titan_discovery_execution',
        ],
    };
}

function runValidation(args, dependencies = {}) {
    const deps = {
        cwd: dependencies.cwd || process.cwd(),
        existsSync: dependencies.existsSync || fs.existsSync,
        readFileSync: dependencies.readFileSync || fs.readFileSync,
    };

    const cliP = validateCliArgsOrPayload(args);
    if (cliP) return cliP;

    const rrLoad = loadYamlFile(args, deps, 'review_result', 'review result', 'review-result-error');
    if (rrLoad.payload) return rrLoad.payload;

    const rrValidation = validateParsedYaml(rrLoad.parsedYaml);
    if (!rrValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'review-result-error',
            review_result_found: true,
            yaml_block_found: true,
            required_fields_present: rrValidation.missingFields.length === 0,
            missing_fields: rrValidation.missingFields,
            errors: rrValidation.errors,
        });
    }

    const intakeP = validateRealParameterIntake({ intake: args.intake, blocked_summary: args.blocked_summary }, deps);
    if (!intakeP.ok) {
        return buildFailurePayload(args, {
            mode: 'intake-error',
            review_result_found: true,
            review_result_valid: true,
            yaml_block_found: true,
            errors: intakeP.errors || ['intake validation failed'],
        });
    }

    const closureP = validateValidationClosure(
        { validation_closure: args.validation_closure, intake: args.intake, blocked_summary: args.blocked_summary },
        deps
    );
    if (!closureP.ok) {
        return buildFailurePayload(args, {
            mode: 'closure-error',
            review_result_found: true,
            review_result_valid: true,
            real_parameter_intake_valid: true,
            yaml_block_found: true,
            errors: closureP.errors || ['closure validation failed'],
        });
    }

    const planP = validateReviewPlan(
        {
            review_plan: args.review_plan,
            intake: args.intake,
            validation_closure: args.validation_closure,
            blocked_summary: args.blocked_summary,
        },
        deps
    );
    if (!planP.ok) {
        return buildFailurePayload(args, {
            mode: 'plan-error',
            review_result_found: true,
            review_result_valid: true,
            real_parameter_intake_valid: true,
            validation_closure_valid: true,
            yaml_block_found: true,
            errors: planP.errors || ['review plan validation failed'],
        });
    }

    return buildSuccessPayload(args);
}

function writePayload(payload, io) {
    io.stdout(JSON.stringify(payload, null, 2) + '\n');
}

function main(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const output = { stdout: io.stdout || (t => process.stdout.write(t)) };
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
        const p = runValidation(args, dependencies);
        writePayload(p, output);
        return p.ok ? 0 : 1;
    } catch (e) {
        writePayload(buildFailurePayload({}, { mode: 'argument-error', errors: [e.message] }), output);
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
    REVIEW_SECTIONS,
    REVIEW_BLOCKING_REASONS,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
