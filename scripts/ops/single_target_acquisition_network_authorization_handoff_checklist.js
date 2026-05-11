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
const {
    runValidation: validateReviewResult,
} = require('./single_target_acquisition_network_filled_intake_review_result');

const OUTPUT_PHASE = 'PHASE4.94D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST';
const TEMPLATE_PHASE = 'PHASE4_94D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_HANDOFF_CHECKLIST';
const MODE = 'single-target-acquisition-network-authorization-handoff-checklist-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition authorization handoff checklist execution is not wired in Phase 4.94D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.95D or explicit user-filled real parameter intake';
const REVIEW_RESULT_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_RESULT_TEMPLATE.md';
const REVIEW_PLAN_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FILLED_INTAKE_REVIEW_PLAN_TEMPLATE.md';
const INTAKE_TEMPLATE = 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_TEMPLATE.md';
const VALIDATION_CLOSURE_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_REAL_PARAMETER_INTAKE_VALIDATION_CLOSURE_TEMPLATE.md';
const BLOCKED_SUMMARY_TEMPLATE =
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY_TEMPLATE.md';

const HANDOFF_SECTIONS = [
    'filled_intake_review_result_check',
    'real_parameter_integrity_check',
    'source_terms_and_allowed_use_check',
    'network_authorization_check',
    'proxy_browser_network_policy_check',
    'staging_policy_check',
    'no_db_training_prediction_check',
    'final_human_confirmation_check',
];

const HANDOFF_BLOCKING_REASONS = [
    'handoff_checklist_template_only',
    'filled_intake_review_result_not_accepted',
    'real_parameters_not_validated',
    'source_terms_not_approved',
    'network_dry_run_not_authorized',
    'proxy_browser_network_policy_not_approved',
    'staging_policy_not_approved',
    'no_db_training_prediction_policy_not_confirmed',
    'final_human_confirmation_missing',
    'future_separate_authorization_phase_required',
];

const SECTION_FIELDS = w('required checked passed blocking_reason');
const AUTH_BOUNDARY_FIELDS = w(
    'handoff_checklist_is_not_authorization future_authorization_phase_required codex_may_not_authorize_network codex_may_not_enable_execution codex_may_not_convert_handoff_to_runbook codex_may_not_self_approve_terms codex_may_not_self_accept_review_result'
);

const REQUIRED_TOP = w(
    'phase handoff_checklist_status authorization_handoff_ready authorization_handoff_completed filled_intake_review_result_ready filled_intake_reviewed filled_intake_accepted can_proceed_to_network_dry_run_preparation real_parameters_provided real_parameter_intake_validated network_dry_run_authorized network_dry_run_execution_allowed staging_write_authorized db_write_authorized training_authorized prediction_authorized final_human_confirmation handoff_sections handoff_blocking_reasons authorization_boundary included_artifacts codex_constraints safety next_phase_requirements'
);

const TOP_FALSE = {
    authorization_handoff_ready: 'authorization_handoff_ready true is not allowed',
    authorization_handoff_completed: 'authorization_handoff_completed true is not allowed',
    filled_intake_review_result_ready: 'filled_intake_review_result_ready true is not allowed',
    filled_intake_reviewed: 'filled_intake_reviewed true is not allowed',
    filled_intake_accepted: 'filled_intake_accepted true is not allowed',
    can_proceed_to_network_dry_run_preparation: 'can_proceed_to_network_dry_run_preparation true is not allowed',
    real_parameters_provided: 'real_parameters_provided true is not allowed',
    real_parameter_intake_validated: 'real_parameter_intake_validated true is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true is not allowed',
    staging_write_authorized: 'staging_write_authorized true is not allowed',
    db_write_authorized: 'db_write_authorized true is not allowed',
    training_authorized: 'training_authorized true is not allowed',
    prediction_authorized: 'prediction_authorized true is not allowed',
    final_human_confirmation: 'final_human_confirmation true is not allowed',
};

const CODEX_FIELDS = w(
    'codex_may_not_self_fill_real_parameters codex_may_not_mark_checked codex_may_not_mark_passed codex_may_not_complete_handoff codex_may_not_authorize_network codex_may_not_enable_execution codex_may_not_write_runtime_files'
);

const SAFETY_FIELDS = w(
    'would_access_network would_launch_browser would_use_proxy would_execute_engine would_execute_legacy_titan_discovery would_write_staging would_create_staging_directory would_write_source_manifest would_write_packet_file would_write_approval_packet_file would_write_user_input_closure_file would_write_blocked_summary_file would_write_real_parameter_intake_file would_write_real_parameter_validation_closure_file would_write_filled_intake_review_file would_write_filled_intake_review_result_file would_write_authorization_handoff_checklist_file would_write_db would_train would_predict would_bulk_harvest'
);

function w(t) {
    return t.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_authorization_handoff_checklist.js --handoff-checklist <path> --review-result <path> --review-plan <path> --intake <path> --validation-closure <path> --blocked-summary <path>',
        '',
        'Safety: Phase 4.94D previews a local authorization handoff checklist template only. No network, no writes.',
    ].join('\n');
}

function parseArgs(argv) {
    const a = {
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
        const t = argv[i];
        if (t === '--commit') {
            a.commit = true;
            continue;
        }
        if (t === '--help' || t === '-h') {
            a.help = true;
            continue;
        }
        if (!t.startsWith('--')) throw new Error('Unknown: ' + t);
        const eq = t.indexOf('=');
        if (eq !== -1) {
            a[t.slice(2, eq).replace(/-/g, '_')] = t.slice(eq + 1);
        } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
            a[t.slice(2).replace(/-/g, '_')] = String(argv[i + 1] || '');
            i += 1;
        } else {
            throw new Error('Unknown: ' + t);
        }
    }
    return a;
}

function buildSafetyFlags() {
    return {
        authorization_handoff_checklist_template_only: true,
        handoff_checklist_valid: false,
        review_result_valid: false,
        review_plan_valid: false,
        real_parameter_intake_valid: false,
        validation_closure_valid: false,
        blocked_summary_valid: false,
        authorization_handoff_ready: false,
        authorization_handoff_completed: false,
        filled_intake_review_result_ready: false,
        filled_intake_reviewed: false,
        filled_intake_accepted: false,
        can_proceed_to_network_dry_run_preparation: false,
        real_parameters_provided: false,
        real_parameter_intake_validated: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        handoff_sections_complete: false,
        handoff_sections_passed: false,
        handoff_checklist_is_not_authorization: true,
        future_authorization_phase_required: true,
        handoff_blocking_reasons: HANDOFF_BLOCKING_REASONS,
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
        handoff_checklist: args.handoff_checklist || null,
        review_result: args.review_result || null,
        review_plan: args.review_plan || null,
        intake: args.intake || null,
        validation_closure: args.validation_closure || null,
        blocked_summary: args.blocked_summary || null,
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

function resolveLocalPath(r, cwd) {
    if (!r) return '';
    return path.isAbsolute(r) ? path.resolve(r) : path.resolve(cwd, r);
}
function toRelativePath(a, cwd) {
    if (!a) return '';
    return path.relative(cwd, a) || '.';
}

function validateRequiredCliFields(args) {
    const e = [];
    if (!args.handoff_checklist) e.push('missing handoff checklist');
    if (!args.review_result) e.push('missing review result');
    if (!args.review_plan) e.push('missing review plan');
    if (!args.intake) e.push('missing intake');
    if (!args.validation_closure) e.push('missing validation closure');
    if (!args.blocked_summary) e.push('missing blocked summary');
    return e;
}
function validateCliArgsOrPayload(args) {
    const e = validateRequiredCliFields(args);
    return e.length ? buildFailurePayload(args, { mode: 'argument-error', errors: e }) : null;
}

function loadYamlFile(args, deps, fieldName, missingLabel, mode) {
    const tp = resolveLocalPath(args[fieldName], deps.cwd);
    if (!deps.existsSync(tp)) {
        return {
            payload: buildFailurePayload(args, {
                mode,
                [`${fieldName}_found`]: false,
                errors: ['missing ' + missingLabel + ': ' + toRelativePath(tp, deps.cwd)],
            }),
        };
    }
    const yt = extractYamlBlock(deps.readFileSync(tp, 'utf8'));
    if (!yt) {
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
        return { parsedYaml: parseIntakeYaml(yt), yamlText: yt };
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
function gp(root, dp) {
    return dp.split('.').reduce((c, k) => {
        if (!c || typeof c !== 'object') return undefined;
        return c[k];
    }, root);
}
function addMissing(root, pp, rk, mf) {
    const v = gp(root, pp);
    if (!v || typeof v !== 'object' || Array.isArray(v)) {
        mf.push(pp);
        return;
    }
    rk.filter(k => !hasOwn(v, k)).forEach(k => mf.push(pp + '.' + k));
}

function findMissingFields(py) {
    const mf = REQUIRED_TOP.filter(k => !hasOwn(py, k));
    HANDOFF_SECTIONS.forEach(s => addMissing(py, 'handoff_sections.' + s, SECTION_FIELDS, mf));
    addMissing(py, 'authorization_boundary', AUTH_BOUNDARY_FIELDS, mf);
    addMissing(
        py,
        'included_artifacts',
        w(
            'filled_intake_review_result filled_intake_review_plan real_parameter_intake validation_closure blocked_summary'
        ),
        mf
    );
    addMissing(py, 'codex_constraints', CODEX_FIELDS, mf);
    addMissing(py, 'safety', SAFETY_FIELDS, mf);
    return mf;
}

function validateTopLevelFalse(py, errors) {
    Object.entries(TOP_FALSE).forEach(([k, msg]) => {
        if (py[k] !== false) errors.push(msg);
    });
}

function validateHandoffSections(py, errors) {
    const sec = py.handoff_sections || {};
    HANDOFF_SECTIONS.forEach(name => {
        const s = sec[name];
        if (!s || typeof s !== 'object' || Array.isArray(s)) {
            errors.push('missing handoff_sections.' + name);
            return;
        }
        if (s.checked !== false) errors.push('handoff_sections.' + name + '.checked true in template is not allowed');
        if (s.passed !== false) errors.push('handoff_sections.' + name + '.passed true in template is not allowed');
        if (s.required !== true) errors.push('handoff_sections.' + name + '.required must be true');
    });
}

function validateAuthorizationBoundary(py, errors) {
    const ab = py.authorization_boundary || {};
    AUTH_BOUNDARY_FIELDS.forEach(f => {
        if (ab[f] !== true) errors.push('authorization_boundary.' + f + ' must be true');
    });
}

function validateBlockingReasons(py, errors) {
    const br = py.handoff_blocking_reasons;
    if (!Array.isArray(br)) {
        errors.push('missing handoff_blocking_reasons');
        return;
    }
    const m = HANDOFF_BLOCKING_REASONS.filter(r => !br.includes(r));
    if (m.length) errors.push('missing handoff_blocking_reasons: ' + m.join(','));
}

function validateIncludedArtifacts(py, errors) {
    const inc = py.included_artifacts || {};
    if (inc.filled_intake_review_result !== REVIEW_RESULT_TEMPLATE) {
        errors.push('included_artifacts.filled_intake_review_result must be ' + REVIEW_RESULT_TEMPLATE);
    }
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

function validateCodexConstraints(py, errors) {
    const cc = py.codex_constraints || {};
    CODEX_FIELDS.forEach(f => {
        if (cc[f] !== true) errors.push('codex_constraints.' + f + ' false is not allowed');
    });
}
function validateSafety(py, errors) {
    const s = py.safety || {};
    SAFETY_FIELDS.forEach(f => {
        if (s[f] !== false) errors.push('safety.' + f + ' must remain false');
    });
}

function validateParsedYaml(py) {
    const errors = [];
    const mf = findMissingFields(py);
    if (mf.length) errors.push('missing required fields: ' + mf.join(','));
    if (py.phase !== TEMPLATE_PHASE) errors.push('phase must be ' + TEMPLATE_PHASE);
    if (py.handoff_checklist_status !== 'template_only') errors.push('handoff_checklist_status not template_only');
    validateTopLevelFalse(py, errors);
    validateHandoffSections(py, errors);
    validateAuthorizationBoundary(py, errors);
    validateBlockingReasons(py, errors);
    validateIncludedArtifacts(py, errors);
    validateCodexConstraints(py, errors);
    validateSafety(py, errors);
    return { ok: errors.length === 0, missingFields: mf, errors };
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        handoff_checklist: args.handoff_checklist,
        review_result: args.review_result,
        review_plan: args.review_plan,
        intake: args.intake,
        validation_closure: args.validation_closure,
        blocked_summary: args.blocked_summary,
        handoff_checklist_found: true,
        review_result_found: true,
        review_plan_found: true,
        intake_found: true,
        validation_closure_found: true,
        blocked_summary_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        handoff_checklist_valid: true,
        review_result_valid: true,
        review_plan_valid: true,
        real_parameter_intake_valid: true,
        validation_closure_valid: true,
        blocked_summary_valid: true,
        handoff_sections_complete: true,
        handoff_sections_passed: false,
        handoff_checklist_is_not_authorization: true,
        future_authorization_phase_required: true,
        errors: [],
        warnings: ['Phase 4.94D remains template-only.', 'Handoff checklist does not constitute authorization.'],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_blocked_summary_file_writes',
            'no_real_parameter_intake_file_writes',
            'no_real_parameter_validation_closure_file_writes',
            'no_filled_intake_review_file_writes',
            'no_filled_intake_review_result_file_writes',
            'no_authorization_handoff_checklist_file_writes',
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

    const hcLoad = loadYamlFile(args, deps, 'handoff_checklist', 'handoff checklist', 'handoff-checklist-error');
    if (hcLoad.payload) return hcLoad.payload;

    const hcValidation = validateParsedYaml(hcLoad.parsedYaml);
    if (!hcValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'handoff-checklist-error',
            handoff_checklist_found: true,
            yaml_block_found: true,
            required_fields_present: hcValidation.missingFields.length === 0,
            missing_fields: hcValidation.missingFields,
            errors: hcValidation.errors,
        });
    }

    const intakeP = validateRealParameterIntake({ intake: args.intake, blocked_summary: args.blocked_summary }, deps);
    if (!intakeP.ok) {
        return buildFailurePayload(args, {
            mode: 'intake-error',
            handoff_checklist_found: true,
            handoff_checklist_valid: true,
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
            handoff_checklist_found: true,
            handoff_checklist_valid: true,
            real_parameter_intake_valid: true,
            yaml_block_found: true,
            errors: closureP.errors || ['closure failed'],
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
            handoff_checklist_found: true,
            handoff_checklist_valid: true,
            real_parameter_intake_valid: true,
            validation_closure_valid: true,
            yaml_block_found: true,
            errors: planP.errors || ['plan failed'],
        });
    }

    const resultP = validateReviewResult(
        {
            review_result: args.review_result,
            review_plan: args.review_plan,
            intake: args.intake,
            validation_closure: args.validation_closure,
            blocked_summary: args.blocked_summary,
        },
        deps
    );
    if (!resultP.ok) {
        return buildFailurePayload(args, {
            mode: 'result-error',
            handoff_checklist_found: true,
            handoff_checklist_valid: true,
            real_parameter_intake_valid: true,
            validation_closure_valid: true,
            review_plan_valid: true,
            yaml_block_found: true,
            errors: resultP.errors || ['result failed'],
        });
    }

    return buildSuccessPayload(args);
}

function writePayload(p, io) {
    io.stdout(JSON.stringify(p, null, 2) + '\n');
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
    HANDOFF_SECTIONS,
    HANDOFF_BLOCKING_REASONS,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
