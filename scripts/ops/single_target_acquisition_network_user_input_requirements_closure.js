#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    runValidation: runApprovalPacketValidation,
    parseApprovalPacketYaml: parseClosureYaml,
} = require('./single_target_acquisition_network_approval_packet_preview');

const OUTPUT_PHASE = 'PHASE4.88D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_USER_INPUT_REQUIREMENTS_CLOSURE';
const TEMPLATE_PHASE = 'PHASE4_88D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_USER_INPUT_REQUIREMENTS_CLOSURE';
const MODE = 'single-target-acquisition-network-user-input-requirements-closure-preview';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run user input requirements closure execution is not wired in Phase 4.88D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.89D or explicit user-supplied network dry-run parameters';

const REQUIRED_CLI_FIELDS = words(`
    input_closure approval_packet execution_plan checklist runbook auth_form
    target_source target_engine_family target_scope_type target_match_id
    terms_approval network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const YES_NO_FIELDS = words(`
    terms_approval network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const REQUIRED_TOP_FIELDS = words(`
    phase closure_status user_inputs_complete network_dry_run_authorized
    network_dry_run_execution_allowed human_approval_packet_ready
    staging_write_authorized db_write_authorized training_authorized
    prediction_authorized final_human_confirmation required_user_inputs
    input_blocking_reasons included_artifacts safety next_phase_requirements
`);

const REQUIRED_INPUT_SECTIONS = {
    real_target_source: words('required provided value'),
    real_target_scope: words(`
        required provided scope_type target_match_id target_league target_season
        target_date max_targets bulk_scope_allowed
    `),
    source_terms: words(`
        terms_url_required license_url_required allowed_use_required
        terms_review_required terms_approval_required provided
    `),
    network_authorization: words(`
        network_dry_run_authorization_required allow_external_network_required
        allow_browser_runtime_required allow_proxy_runtime_required provided
    `),
    proxy_browser_network_policy: words(`
        proxy_policy_required browser_policy_required rate_limit_policy_required
        retry_policy_required user_agent_policy_required
        no_login_paywall_bypass_confirmation_required
        no_anti_bot_bypass_confirmation_required
        no_bulk_expansion_confirmation_required provided
    `),
    staging_policy: words(`
        allow_staging_write_required output_root_policy_required
        schema_validation_required source_manifest_policy_required provided
    `),
    no_db_training_prediction_policy: words(`
        no_db_write_confirmation_required no_training_confirmation_required
        no_prediction_confirmation_required
        no_model_artifact_loading_confirmation_required provided
    `),
    final_human_confirmation: words('required provided confirmed_by'),
};

const INPUT_GROUP_NAMES = Object.keys(REQUIRED_INPUT_SECTIONS);

const REQUIRED_BOOLEAN_TRUE_FIELDS = {
    real_target_source: words('required'),
    real_target_scope: words('required'),
    source_terms: words(`
        terms_url_required license_url_required allowed_use_required
        terms_review_required terms_approval_required
    `),
    network_authorization: words(`
        network_dry_run_authorization_required allow_external_network_required
        allow_browser_runtime_required allow_proxy_runtime_required
    `),
    proxy_browser_network_policy: words(`
        proxy_policy_required browser_policy_required rate_limit_policy_required
        retry_policy_required user_agent_policy_required
        no_login_paywall_bypass_confirmation_required
        no_anti_bot_bypass_confirmation_required
        no_bulk_expansion_confirmation_required
    `),
    staging_policy: words(`
        allow_staging_write_required output_root_policy_required
        schema_validation_required source_manifest_policy_required
    `),
    no_db_training_prediction_policy: words(`
        no_db_write_confirmation_required no_training_confirmation_required
        no_prediction_confirmation_required
        no_model_artifact_loading_confirmation_required
    `),
    final_human_confirmation: words('required'),
};

const TOP_FALSE = {
    user_inputs_complete: 'user_inputs_complete true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    human_approval_packet_ready: 'human_approval_packet_ready true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

const SAFETY_FIELDS = words(`
    would_access_network would_launch_browser would_use_proxy would_execute_engine
    would_write_staging would_create_staging_directory would_write_source_manifest
    would_write_packet_file would_write_approval_packet_file
    would_write_user_input_closure_file would_write_db would_train would_predict
    would_bulk_harvest
`);

const EXPECTED_ARTIFACTS = {
    approval_packet: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_HUMAN_APPROVAL_PACKET_TEMPLATE.md',
    execution_plan: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md',
    readiness_checklist:
        'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FINAL_READINESS_CHECKLIST_TEMPLATE.md',
    pre_network_runbook: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md',
    network_auth_form: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md',
};

const REQUIRED_BLOCKING_REASONS = words(`
    real_target_source_missing real_single_target_scope_missing
    source_terms_missing network_authorization_missing
    proxy_browser_network_policy_missing staging_policy_missing
    no_db_training_prediction_confirmation_missing final_human_confirmation_missing
`);

const REQUIRED_NEXT_PHASE_REQUIREMENTS = words(`
    user_supplied_real_target_source user_supplied_real_single_target_scope
    user_supplied_terms_url user_supplied_license_url user_confirmed_allowed_use
    user_confirmed_network_dry_run_authorization
    user_confirmed_external_network_policy user_confirmed_browser_proxy_policy
    user_confirmed_staging_policy user_confirmed_no_db_write
    user_confirmed_no_training user_confirmed_no_prediction
    user_final_human_confirmation
`);

const MISSING_USER_INPUTS = [
    'real_target_source',
    'real_single_target_scope',
    'source_terms',
    'network_authorization',
    'proxy_browser_network_policy',
    'staging_policy',
    'no_db_training_prediction_policy',
    'final_human_confirmation',
];

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_user_input_requirements_closure.js --input-closure <path> --approval-packet <path> --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_user_input_requirements_closure.js --input-closure <path> ... --commit',
        '',
        'Safety:',
        '  Phase 4.88D previews local user input requirements only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
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
        if (!token.startsWith('--')) {
            throw new Error(`Unknown argument: ${token}`);
        }
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
        input_requirements_closure_preview_only: true,
        input_closure_valid: false,
        approval_packet_valid: false,
        execution_plan_valid: false,
        readiness_checklist_valid: false,
        runbook_template_valid: false,
        auth_form_template_valid: false,
        user_inputs_complete: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        human_approval_packet_ready: false,
        staging_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        final_human_confirmation: false,
        missing_user_inputs: MISSING_USER_INPUTS,
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_execute_engine: false,
        would_write_staging: false,
        would_create_staging_directory: false,
        would_write_source_manifest: false,
        would_write_packet_file: false,
        would_write_approval_packet_file: false,
        would_write_user_input_closure_file: false,
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
        input_closure: args.input_closure || null,
        approval_packet: args.approval_packet || null,
        execution_plan: args.execution_plan || null,
        checklist: args.checklist || null,
        runbook: args.runbook || null,
        auth_form: args.auth_form || null,
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
            'no_approval_packet_file_writes',
            'no_user_input_closure_file_writes',
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

function loadClosureYaml(args, dependencies) {
    const targetPath = resolveLocalPath(args.input_closure, dependencies.cwd);
    if (!dependencies.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'input-closure-error',
                input_closure_found: false,
                errors: [`missing input closure: ${toRelativePath(targetPath, dependencies.cwd)}`],
            }),
        };
    }

    const yamlText = extractYamlBlock(dependencies.readFileSync(targetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'input-closure-error',
                input_closure_found: true,
                yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return { parsedYaml: parseClosureYaml(yamlText), yamlText };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'input-closure-error',
                input_closure_found: true,
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
    const inputs = parsedYaml.required_user_inputs || {};
    Object.entries(REQUIRED_INPUT_SECTIONS).forEach(([sectionName, requiredKeys]) => {
        addMissingNested(inputs, sectionName, requiredKeys, missingFields);
    });
    addMissingNested(parsedYaml, 'included_artifacts', Object.keys(EXPECTED_ARTIFACTS), missingFields);
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

function validateRequiredInputSections(parsedYaml, errors) {
    const inputs = parsedYaml.required_user_inputs || {};
    INPUT_GROUP_NAMES.forEach(sectionName => {
        const section = inputs[sectionName];
        if (!section || typeof section !== 'object' || Array.isArray(section)) {
            errors.push(`required_user_inputs.${sectionName} missing`);
            return;
        }
        if (section.provided !== false) {
            errors.push(`required_user_inputs.${sectionName}.provided true in template is not allowed`);
        }
        (REQUIRED_BOOLEAN_TRUE_FIELDS[sectionName] || []).forEach(fieldName => {
            if (section[fieldName] !== true) {
                errors.push(`required_user_inputs.${sectionName}.${fieldName} must be true`);
            }
        });
    });

    const targetScope = inputs.real_target_scope || {};
    if (targetScope.bulk_scope_allowed !== false) {
        errors.push('bulk scope allowed must remain false in the Phase 4.88D template');
    }
    if (targetScope.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.88D template');
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
    if (parsedYaml.closure_status !== 'closure_preview_only') {
        errors.push('closure_status must remain closure_preview_only in the Phase 4.88D template');
    }
    Object.entries(TOP_FALSE).forEach(([fieldName, message]) => {
        if (parsedYaml[fieldName] !== false) errors.push(message);
    });
    validateRequiredInputSections(parsedYaml, errors);
    ensureObjectValues(parsedYaml, 'included_artifacts', EXPECTED_ARTIFACTS, errors);
    validateSafety(parsedYaml, errors);
    ensureArrayContainsAll(
        parsedYaml,
        'input_blocking_reasons',
        REQUIRED_BLOCKING_REASONS,
        errors,
        'input_blocking_reasons missing'
    );
    ensureArrayContainsAll(parsedYaml, 'next_phase_requirements', REQUIRED_NEXT_PHASE_REQUIREMENTS, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function validateTargetConsistency(args, closureYaml, approvalPacketPayload) {
    const inputs = closureYaml.required_user_inputs || {};
    const source = inputs.real_target_source || {};
    const scope = inputs.real_target_scope || {};
    const candidates = [
        ['required_user_inputs.real_target_source.value', source.value, args.target_source],
        ['required_user_inputs.real_target_scope.scope_type', scope.scope_type, args.target_scope_type],
        ['required_user_inputs.real_target_scope.target_match_id', scope.target_match_id, args.target_match_id],
        ['required_user_inputs.real_target_scope.target_league', scope.target_league, args.target_league],
        ['required_user_inputs.real_target_scope.target_season', scope.target_season, args.target_season],
        ['required_user_inputs.real_target_scope.target_date', scope.target_date, args.target_date],
    ];
    const errors = candidates
        .filter(([, templateValue, cliValue]) => templateValue && templateValue !== cliValue)
        .map(
            ([label, templateValue, cliValue]) =>
                `target mismatch: input closure ${label} "${templateValue}" does not match CLI value "${cliValue}"`
        );
    if (approvalPacketPayload.errors && approvalPacketPayload.errors.some(error => /target mismatch/i.test(error))) {
        errors.push(...approvalPacketPayload.errors);
    }
    return errors;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: OUTPUT_PHASE,
        mode: MODE,
        ok: true,
        input_closure: args.input_closure,
        approval_packet: args.approval_packet,
        execution_plan: args.execution_plan,
        checklist: args.checklist,
        runbook: args.runbook,
        auth_form: args.auth_form,
        input_closure_found: true,
        approval_packet_found: true,
        execution_plan_found: true,
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        required_fields_present: true,
        input_closure_valid: true,
        approval_packet_valid: true,
        execution_plan_valid: true,
        readiness_checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        errors: [],
        warnings: [
            'Phase 4.88D remains closure-preview-only.',
            'CLI authorization yes values do not complete user inputs or authorize execution in this phase.',
        ],
        non_execution_confirmations: [
            ...buildNonExecutionConfirmations(),
            'no_approval_packet_file_writes',
            'no_user_input_closure_file_writes',
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

    const closureLoad = loadClosureYaml(args, localDeps);
    if (closureLoad.payload) return closureLoad.payload;

    const closureValidation = validateParsedYaml(closureLoad.parsedYaml);
    if (!closureValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'input-closure-error',
            input_closure_found: true,
            yaml_block_found: true,
            required_fields_present: closureValidation.missingFields.length === 0,
            missing_fields: closureValidation.missingFields,
            errors: closureValidation.errors,
        });
    }

    const approvalPacketPayload = runApprovalPacketValidation(args, localDeps);
    if (!approvalPacketPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'approval-packet-error',
            input_closure_found: true,
            yaml_block_found: true,
            input_closure_valid: true,
            errors: approvalPacketPayload.errors,
        });
    }

    const targetErrors = validateTargetConsistency(args, closureLoad.parsedYaml, approvalPacketPayload);
    if (targetErrors.length) {
        return buildFailurePayload(args, {
            mode: 'target-error',
            input_closure_found: true,
            approval_packet_found: true,
            execution_plan_found: true,
            checklist_found: true,
            runbook_found: true,
            auth_form_found: true,
            yaml_block_found: true,
            required_fields_present: true,
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
