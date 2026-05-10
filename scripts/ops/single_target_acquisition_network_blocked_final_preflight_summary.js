#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    parseApprovalPacketYaml: parseBlockedSummaryYaml,
} = require('./single_target_acquisition_network_approval_packet_preview');
const {
    runValidation: runUserInputClosureValidation,
} = require('./single_target_acquisition_network_user_input_requirements_closure');

const OUTPUT_PHASE = 'PHASE4.89D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY';
const TEMPLATE_PHASE = 'PHASE4_89D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_BLOCKED_FINAL_PREFLIGHT_SUMMARY';
const MODE = 'single-target-acquisition-network-blocked-final-preflight-summary';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run blocked final preflight summary execution is not wired in Phase 4.89D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.90D or explicit user-supplied network dry-run parameters';
const PRIMARY_BLOCKING_REASON = 'missing_user_supplied_real_network_dry_run_inputs';

const REQUIRED_CLI_FIELDS = words(`
    blocked_summary input_closure approval_packet execution_plan checklist
    runbook auth_form target_source target_engine_family target_scope_type
    target_match_id terms_approval network_dry_run_authorization
    allow_browser_runtime allow_proxy_runtime allow_external_network
    allow_staging_write final_human_confirmation
`);

const YES_NO_FIELDS = words(`
    terms_approval network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const REQUIRED_TOP_FIELDS = words(`
    phase summary_status network_dry_run_blocked network_dry_run_ready
    network_dry_run_authorized network_dry_run_execution_allowed
    human_approval_packet_ready user_inputs_complete staging_write_authorized
    db_write_authorized training_authorized prediction_authorized
    final_human_confirmation blocking_summary target missing_user_inputs
    included_chain gate_statuses safety allowed_next_steps forbidden_next_steps
`);

const BLOCKING_SUMMARY_FIELDS = words(`
    primary_reason cannot_continue_without_user_inputs
    codex_may_not_self_fill_inputs codex_may_not_escalate_authorization
    requires_future_separate_phase
`);

const TARGET_FIELDS = words(`
    target_source target_engine_family target_scope_type target_match_id
    target_league target_season target_date max_targets bulk_scope_allowed
`);

const SAFETY_FIELDS = words(`
    would_access_network would_launch_browser would_use_proxy
    would_execute_engine would_execute_legacy_titan_discovery
    would_write_staging would_create_staging_directory
    would_write_source_manifest would_write_packet_file
    would_write_approval_packet_file would_write_user_input_closure_file
    would_write_blocked_summary_file would_write_db would_train
    would_predict would_bulk_harvest
`);

const TOP_FALSE = {
    network_dry_run_ready: 'network_dry_run_ready true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    human_approval_packet_ready: 'human_approval_packet_ready true in template is not allowed',
    user_inputs_complete: 'user_inputs_complete true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

const REQUIRED_MISSING_USER_INPUTS = [
    'real_target_source',
    'real_single_target_scope',
    'source_terms',
    'license_review',
    'allowed_use_review',
    'network_authorization',
    'external_network_policy',
    'browser_runtime_policy',
    'proxy_runtime_policy',
    'staging_policy',
    'no_db_write_confirmation',
    'no_training_confirmation',
    'no_prediction_confirmation',
    'final_human_confirmation',
];

const EXPECTED_INCLUDED_CHAIN = {
    runtime_scaffold: 'scripts/ops/single_target_acquisition_runtime_scaffold.js',
    staging_schema_validator: 'scripts/ops/single_target_acquisition_staging_schema_validator.js',
    staging_writer_preflight: 'scripts/ops/single_target_acquisition_staging_writer_preflight.js',
    staging_packet_preview: 'scripts/ops/single_target_acquisition_staging_packet_preview.js',
    pre_network_runbook: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md',
    network_auth_form: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md',
    final_readiness_checklist:
        'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FINAL_READINESS_CHECKLIST_TEMPLATE.md',
    execution_plan: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md',
    human_approval_packet: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_HUMAN_APPROVAL_PACKET_TEMPLATE.md',
    user_input_closure:
        'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_USER_INPUT_REQUIREMENTS_CLOSURE_TEMPLATE.md',
};

const GATE_STATUS_FIELDS = words(`
    runtime_scaffold_available staging_schema_validator_available
    staging_writer_preflight_available staging_packet_preview_available
    pre_network_runbook_available network_auth_form_available
    final_readiness_checklist_available execution_plan_available
    human_approval_packet_available user_input_closure_available
    all_runtime_execution_gates_blocked all_write_gates_blocked
    all_authorization_gates_false
`);

const REQUIRED_ALLOWED_NEXT_STEPS = words(`
    remain_blocked user_provides_real_single_target_network_dry_run_inputs
    future_separate_phase_validates_user_inputs
    future_separate_phase_reviews_terms_and_authorization
`);

const REQUIRED_FORBIDDEN_NEXT_STEPS = words(`
    codex_self_fills_real_source codex_self_fills_real_target
    codex_self_approves_terms codex_self_authorizes_network
    codex_executes_network_dry_run codex_writes_staging
    codex_writes_db codex_trains_or_predicts
`);

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_blocked_final_preflight_summary.js --blocked-summary <path> --input-closure <path> --approval-packet <path> --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_blocked_final_preflight_summary.js --blocked-summary <path> ... --commit',
        '',
        'Safety:',
        '  Phase 4.89D previews a local blocked final preflight summary only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        blocked_summary: '',
        input_closure: '',
        approval_packet: '',
        execution_plan: '',
        checklist: '',
        runbook: '',
        auth_form: '',
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
        blocked_final_preflight_summary_preview_only: true,
        blocked_summary_valid: false,
        input_closure_valid: false,
        approval_packet_valid: false,
        execution_plan_valid: false,
        readiness_checklist_valid: false,
        runbook_template_valid: false,
        auth_form_template_valid: false,
        network_dry_run_blocked: true,
        network_dry_run_ready: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        human_approval_packet_ready: false,
        user_inputs_complete: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        primary_blocking_reason: PRIMARY_BLOCKING_REASON,
        missing_user_inputs: REQUIRED_MISSING_USER_INPUTS,
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
        blocked_summary: args.blocked_summary || null,
        input_closure: args.input_closure || null,
        approval_packet: args.approval_packet || null,
        execution_plan: args.execution_plan || null,
        checklist: args.checklist || null,
        runbook: args.runbook || null,
        auth_form: args.auth_form || null,
        blocked_summary_found: false,
        input_closure_found: false,
        approval_packet_found: false,
        execution_plan_found: false,
        checklist_found: false,
        runbook_found: false,
        auth_form_found: false,
        yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_approval_packet_file_writes',
            'no_user_input_closure_file_writes',
            'no_blocked_summary_file_writes',
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
    return REQUIRED_CLI_FIELDS.flatMap(field => {
        if (args[field]) return [];
        if (field === 'blocked_summary') return ['missing blocked summary'];
        if (field === 'input_closure') return ['missing input closure'];
        if (field === 'approval_packet') return ['missing approval packet'];
        if (field === 'execution_plan') return ['missing execution plan'];
        if (field === 'checklist') return ['missing checklist'];
        if (field === 'runbook') return ['missing runbook'];
        if (field === 'auth_form') return ['missing auth form'];
        return [`missing ${field.replace(/_/g, ' ')} path or value`];
    });
}

function validateCliArgsOrPayload(args) {
    const errors = validateRequiredCliFields(args);
    YES_NO_FIELDS.forEach(field => {
        if (args[field] !== 'yes' && args[field] !== 'no') {
            errors.push(`--${field.replace(/_/g, '-')} is required (yes/no)`);
        }
    });
    if (args.target_engine_family && args.target_engine_family !== 'titan_discovery') {
        errors.push(`unsupported engine family "${args.target_engine_family}"`);
    }
    if (
        args.target_scope_type &&
        args.target_scope_type !== 'match_id' &&
        args.target_scope_type !== 'league_season_date'
    ) {
        errors.push(`unsupported scope type "${args.target_scope_type}"`);
    }
    if (args.target_scope_type === 'bulk') errors.push('unsupported scope type bulk');
    return errors.length ? buildFailurePayload(args, { mode: 'argument-error', errors }) : null;
}

function loadBlockedSummaryYaml(args, dependencies) {
    const targetPath = resolveLocalPath(args.blocked_summary, dependencies.cwd);
    if (!dependencies.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'blocked-summary-error',
                blocked_summary_found: false,
                errors: [`missing blocked summary: ${toRelativePath(targetPath, dependencies.cwd)}`],
            }),
        };
    }

    const yamlText = extractYamlBlock(dependencies.readFileSync(targetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'blocked-summary-error',
                blocked_summary_found: true,
                yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return { parsedYaml: parseBlockedSummaryYaml(yamlText), yamlText };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'blocked-summary-error',
                blocked_summary_found: true,
                yaml_block_found: true,
                errors: [`invalid YAML: ${error.message}`],
            }),
        };
    }
}

function addMissingNested(root, parentKey, requiredKeys, missingFields) {
    const value = root[parentKey];
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        requiredKeys.forEach(key => missingFields.push(`${parentKey}.${key}`));
        return;
    }
    requiredKeys
        .filter(key => !Object.prototype.hasOwnProperty.call(value, key))
        .forEach(key => missingFields.push(`${parentKey}.${key}`));
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP_FIELDS.filter(key => !Object.prototype.hasOwnProperty.call(parsedYaml, key));
    addMissingNested(parsedYaml, 'blocking_summary', BLOCKING_SUMMARY_FIELDS, missingFields);
    addMissingNested(parsedYaml, 'target', TARGET_FIELDS, missingFields);
    addMissingNested(parsedYaml, 'included_chain', Object.keys(EXPECTED_INCLUDED_CHAIN), missingFields);
    addMissingNested(parsedYaml, 'gate_statuses', GATE_STATUS_FIELDS, missingFields);
    addMissingNested(parsedYaml, 'safety', SAFETY_FIELDS, missingFields);
    return missingFields;
}

function ensureArrayContainsAll(root, key, requiredValues, errors, missingMessage) {
    const value = root[key];
    if (!Array.isArray(value)) {
        errors.push(missingMessage || `${key} missing`);
        return;
    }
    requiredValues
        .filter(requiredValue => !value.includes(requiredValue))
        .forEach(requiredValue => errors.push(`${key} missing required value "${requiredValue}"`));
}

function ensureObjectValues(root, parentKey, expectedValues, errors) {
    const parent = root[parentKey] || {};
    Object.entries(expectedValues).forEach(([fieldName, expectedValue]) => {
        if (parent[fieldName] !== expectedValue) {
            errors.push(`${parentKey}.${fieldName} must be ${expectedValue}`);
        }
    });
}

function validateBlockingSummary(parsedYaml, errors) {
    const summary = parsedYaml.blocking_summary || {};
    if (summary.primary_reason !== PRIMARY_BLOCKING_REASON) {
        errors.push(`primary_reason must be ${PRIMARY_BLOCKING_REASON}`);
    }
    words(`
        cannot_continue_without_user_inputs codex_may_not_self_fill_inputs
        codex_may_not_escalate_authorization requires_future_separate_phase
    `).forEach(fieldName => {
        if (summary[fieldName] !== true) {
            errors.push(`blocking_summary.${fieldName} must be true`);
        }
    });
}

function validateTargetSection(parsedYaml, errors) {
    const target = parsedYaml.target || {};
    if (target.target_engine_family !== 'titan_discovery') {
        errors.push(`unsupported engine family "${target.target_engine_family}"`);
    }
    if (target.target_scope_type === 'bulk') {
        errors.push('unsupported scope type bulk');
    }
    if (target.bulk_scope_allowed !== false) {
        errors.push('bulk scope allowed must remain false in the Phase 4.89D template');
    }
    if (target.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.89D template');
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
    if (parsedYaml.summary_status !== 'blocked_preview_only') {
        errors.push('summary_status must remain blocked_preview_only in the Phase 4.89D template');
    }
    if (parsedYaml.network_dry_run_blocked !== true) {
        errors.push('network_dry_run_blocked false in template is not allowed');
    }
    Object.entries(TOP_FALSE).forEach(([fieldName, message]) => {
        if (parsedYaml[fieldName] !== false) errors.push(message);
    });
    validateBlockingSummary(parsedYaml, errors);
    validateTargetSection(parsedYaml, errors);
    ensureArrayContainsAll(
        parsedYaml,
        'missing_user_inputs',
        REQUIRED_MISSING_USER_INPUTS,
        errors,
        'missing_user_inputs missing'
    );
    ensureObjectValues(parsedYaml, 'included_chain', EXPECTED_INCLUDED_CHAIN, errors);
    GATE_STATUS_FIELDS.forEach(fieldName => {
        if ((parsedYaml.gate_statuses || {})[fieldName] !== true) {
            errors.push(`gate_statuses.${fieldName} must be true`);
        }
    });
    validateSafety(parsedYaml, errors);
    ensureArrayContainsAll(parsedYaml, 'allowed_next_steps', REQUIRED_ALLOWED_NEXT_STEPS, errors);
    ensureArrayContainsAll(parsedYaml, 'forbidden_next_steps', REQUIRED_FORBIDDEN_NEXT_STEPS, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function validateTargetConsistency(args, parsedYaml, inputClosurePayload) {
    const target = parsedYaml.target || {};
    const candidates = [
        ['blocked_summary.target.target_source', target.target_source, args.target_source],
        ['blocked_summary.target.target_engine_family', target.target_engine_family, args.target_engine_family],
        ['blocked_summary.target.target_scope_type', target.target_scope_type, args.target_scope_type],
        ['blocked_summary.target.target_match_id', target.target_match_id, args.target_match_id],
        ['blocked_summary.target.target_league', target.target_league, args.target_league],
        ['blocked_summary.target.target_season', target.target_season, args.target_season],
        ['blocked_summary.target.target_date', target.target_date, args.target_date],
    ];
    const errors = candidates
        .filter(([, templateValue, cliValue]) => templateValue && templateValue !== cliValue)
        .map(
            ([label, templateValue, cliValue]) =>
                `target mismatch: ${label} "${templateValue}" does not match CLI value "${cliValue}"`
        );
    if (inputClosurePayload.errors && inputClosurePayload.errors.some(error => /target mismatch/i.test(error))) {
        errors.push(...inputClosurePayload.errors);
    }
    return errors;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        blocked_summary: args.blocked_summary,
        input_closure: args.input_closure,
        approval_packet: args.approval_packet,
        execution_plan: args.execution_plan,
        checklist: args.checklist,
        runbook: args.runbook,
        auth_form: args.auth_form,
        blocked_summary_found: true,
        input_closure_found: true,
        approval_packet_found: true,
        execution_plan_found: true,
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        blocked_summary_valid: true,
        input_closure_valid: true,
        approval_packet_valid: true,
        execution_plan_valid: true,
        readiness_checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        errors: [],
        warnings: [
            'Phase 4.89D remains blocked-preview-only.',
            'CLI authorization yes values do not unblock execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_legacy_titan_discovery_execution',
            'no_approval_packet_file_writes',
            'no_user_input_closure_file_writes',
            'no_blocked_summary_file_writes',
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

    const summaryLoad = loadBlockedSummaryYaml(args, localDeps);
    if (summaryLoad.payload) return summaryLoad.payload;

    const summaryValidation = validateParsedYaml(summaryLoad.parsedYaml);
    if (!summaryValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'blocked-summary-error',
            blocked_summary_found: true,
            yaml_block_found: true,
            required_fields_present: summaryValidation.missingFields.length === 0,
            missing_fields: summaryValidation.missingFields,
            errors: summaryValidation.errors,
        });
    }

    const inputClosurePayload = runUserInputClosureValidation(args, localDeps);
    if (!inputClosurePayload.ok) {
        return buildFailurePayload(args, {
            mode: 'input-closure-error',
            blocked_summary_found: true,
            yaml_block_found: true,
            blocked_summary_valid: true,
            errors: inputClosurePayload.errors,
        });
    }

    const targetErrors = validateTargetConsistency(args, summaryLoad.parsedYaml, inputClosurePayload);
    if (targetErrors.length) {
        return buildFailurePayload(args, {
            mode: 'target-error',
            blocked_summary_found: true,
            input_closure_found: true,
            approval_packet_found: true,
            execution_plan_found: true,
            checklist_found: true,
            runbook_found: true,
            auth_form_found: true,
            yaml_block_found: true,
            required_fields_present: true,
            blocked_summary_valid: true,
            input_closure_valid: true,
            approval_packet_valid: true,
            execution_plan_valid: true,
            readiness_checklist_valid: true,
            runbook_template_valid: true,
            auth_form_template_valid: true,
            errors: targetErrors,
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
    validateParsedYaml,
    runValidation,
    main,
};
