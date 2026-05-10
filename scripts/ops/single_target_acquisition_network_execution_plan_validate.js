#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    validateParsedYaml: validateReadinessParsedYaml,
    runValidation: runReadinessValidation,
} = require('./single_target_acquisition_network_readiness_checklist_validate');

const EXECUTION_PHASE = 'PHASE4.86D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_DRAFT';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run execution is not wired in Phase 4.86D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.87D or explicit user-authorized network dry-run preparation';
const MODE = 'single-target-acquisition-network-execution-plan-validate';
const EXPECTED_STEPS = [
    'confirm_single_target_scope',
    'confirm_source_terms',
    'confirm_network_authorization',
    'confirm_proxy_browser_network_preflight',
    'confirm_staging_packet_preview',
    'future_network_dry_run',
    'future_staging_artifact_validation',
];

const FIELDS = {
    top: words(`
        phase execution_plan_status network_dry_run_execution_allowed
        network_dry_run_authorized staging_write_authorized
        db_write_authorized training_authorized prediction_authorized
        final_human_confirmation required_prior_artifacts
        required_prior_validations target execution_steps stop_gates
        network_runtime_policy staging_policy db_training_prediction_policy
        safety next_phase_requirements
    `),
    required_prior_artifacts: words(`
        runtime_scaffold_present staging_schema_validator_present
        staging_writer_preflight_present staging_packet_preview_present
        pre_network_runbook_present network_auth_form_present
        final_readiness_checklist_present
    `),
    required_prior_validations: words(`
        runtime_scaffold_validated staging_schema_validated
        staging_writer_preflight_validated staging_packet_preview_validated
        pre_network_runbook_validated network_auth_form_validated
        final_readiness_checklist_validated
    `),
    target: words(`
        target_source target_engine_family target_scope_type target_match_id
        target_league target_season target_date max_targets bulk_scope_allowed
    `),
    stop_gates: words(`
        terms_not_approved network_not_authorized target_not_single
        bulk_scope_detected legacy_runtime_required db_write_required
        training_or_prediction_required staging_write_not_authorized
        proxy_or_browser_policy_unreviewed source_manifest_policy_missing
    `),
    network_runtime_policy: words(`
        allow_external_network allow_browser_runtime allow_proxy_runtime
        allow_legacy_titan_discovery_runtime allow_bulk_harvest
    `),
    staging_policy: words(`
        allow_staging_directory_creation allow_staging_artifact_write
        allow_source_manifest_write output_root_policy_reviewed
        schema_validation_required
    `),
    db_training_prediction_policy: words(`
        allow_db_write allow_pg_dump allow_training allow_prediction
        allow_model_artifact_loading
    `),
    safety: words(`
        would_access_network would_launch_browser would_use_proxy
        would_execute_engine would_write_staging
        would_create_staging_directory would_write_source_manifest
        would_write_packet_file would_write_db would_train
        would_predict would_bulk_harvest
    `),
};

const REQUIRED_NEXT_PHASE = words(`
    real_user_authorized_source real_single_target_scope explicit_terms_approval
    explicit_network_dry_run_authorization
    accepted_proxy_browser_network_policy accepted_staging_policy
    accepted_stop_gates confirmed_no_db_write confirmed_no_training
    confirmed_no_prediction
`);

const CLI_REQUIRED = words(`
    execution_plan checklist runbook auth_form target_source target_engine_family
    target_scope_type target_match_id terms_approval
    network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const CLI_YES_NO = words(`
    terms_approval network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const TOP_FALSE = {
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    staging_write_authorized: 'staging_write_authorized true in template is not allowed',
    db_write_authorized: 'db_write_authorized true in template is not allowed',
    training_authorized: 'training_authorized true in template is not allowed',
    prediction_authorized: 'prediction_authorized true in template is not allowed',
    final_human_confirmation: 'final_human_confirmation true in template is not allowed',
};

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
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

function pushContainer(parent, key) {
    parent[key] = key === 'execution_steps' || key === 'next_phase_requirements' ? [] : {};
}

function parseExecutionPlanYaml(yamlText) {
    const root = {};
    let section = '';
    let currentItem = null;

    String(yamlText || '')
        .split(/\r?\n/)
        .forEach(rawLine => {
            if (!rawLine.trim() || rawLine.trim().startsWith('#')) return;
            const indent = rawLine.match(/^ */)[0].length;
            const trimmed = rawLine.trim();
            if (indent === 0) {
                const match = trimmed.match(/^([A-Za-z0-9_]+):(.*)$/);
                if (!match) throw new Error(`unsupported YAML line: ${trimmed}`);
                section = match[1];
                currentItem = null;
                root[section] = match[2].trim() === '' ? null : parseScalar(match[2]);
                if (match[2].trim() === '') pushContainer(root, section);
                return;
            }
            if (section === 'execution_steps') {
                currentItem = parseExecutionStepLine(root.execution_steps, currentItem, indent, trimmed);
                return;
            }
            if (Array.isArray(root[section])) {
                if (!trimmed.startsWith('- ')) throw new Error(`unsupported YAML list line: ${trimmed}`);
                root[section].push(parseScalar(trimmed.slice(2)));
                return;
            }
            parseNestedLine(root, section, trimmed);
        });

    return root;
}

function parseExecutionStepLine(steps, currentItem, indent, trimmed) {
    if (indent === 4 && trimmed.startsWith('- ')) {
        const item = {};
        steps.push(item);
        parseNestedAssignment(item, trimmed.slice(2));
        return item;
    }
    if (indent >= 6 && currentItem) {
        parseNestedAssignment(currentItem, trimmed);
        return currentItem;
    }
    throw new Error(`unsupported execution_steps line: ${trimmed}`);
}

function parseNestedLine(root, section, trimmed) {
    if (!root[section] || typeof root[section] !== 'object' || Array.isArray(root[section])) root[section] = {};
    parseNestedAssignment(root[section], trimmed);
}

function parseNestedAssignment(target, trimmed) {
    const match = trimmed.match(/^([A-Za-z0-9_]+):(.*)$/);
    if (!match) throw new Error(`unsupported YAML line: ${trimmed}`);
    target[match[1]] = match[2].trim() === '' ? null : parseScalar(match[2]);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_execution_plan_validate.js --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_execution_plan_validate.js --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --commit',
        '',
        'Safety:',
        '  Phase 4.86D validates a local execution plan draft only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = { execution_plan: '', checklist: '', runbook: '', auth_form: '', commit: false, help: false };
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
        execution_plan_draft_only: true,
        execution_plan_valid: false,
        readiness_checklist_valid: false,
        runbook_template_valid: false,
        auth_form_template_valid: false,
        network_dry_run_execution_allowed: false,
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
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: EXECUTION_PHASE,
        mode: fields.mode || MODE,
        ok: false,
        execution_plan: args.execution_plan || null,
        checklist: args.checklist || null,
        runbook: args.runbook || null,
        auth_form: args.auth_form || null,
        execution_plan_found: false,
        checklist_found: false,
        runbook_found: false,
        auth_form_found: false,
        yaml_block_found: false,
        checklist_yaml_block_found: false,
        runbook_yaml_block_found: false,
        auth_form_yaml_block_found: false,
        required_fields_present: false,
        missing_fields: [],
        errors: [],
        warnings: [],
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        ...fields,
    };
}

function validateRequiredCliFields(args) {
    return CLI_REQUIRED.flatMap(field => {
        if (args[field]) return [];
        if (field === 'execution_plan') return ['missing execution plan'];
        if (field === 'checklist') return ['missing checklist'];
        if (field === 'runbook') return ['missing runbook'];
        if (field === 'auth_form') return ['missing auth form'];
        return [`missing ${field.replace(/_/g, ' ')} path or value`];
    });
}

function validateCliArgsOrPayload(args) {
    const errors = validateRequiredCliFields(args);
    CLI_YES_NO.forEach(field => {
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

function resolveLocalPath(rawPath, cwd = process.cwd()) {
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function loadMarkdownYaml(args, fieldName, modePrefix, missingLabel, yamlFlagField, dependencies) {
    const targetPath = resolveLocalPath(args[fieldName], dependencies.cwd);
    if (!dependencies.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: false,
                errors: [`${missingLabel}: ${toRelativePath(targetPath, dependencies.cwd)}`],
            }),
        };
    }
    const yamlText = extractYamlBlock(dependencies.readFileSync(targetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: true,
                [yamlFlagField]: false,
                errors: ['missing YAML block'],
            }),
        };
    }
    try {
        return { parsedYaml: fieldName === 'execution_plan' ? parseExecutionPlanYaml(yamlText) : null, yamlText };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: true,
                [yamlFlagField]: true,
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
    const missingFields = FIELDS.top.filter(key => !Object.prototype.hasOwnProperty.call(parsedYaml, key));
    Object.entries(FIELDS)
        .filter(([key]) => key !== 'top')
        .forEach(([key, requiredKeys]) => addMissingNested(parsedYaml, key, requiredKeys, missingFields));
    return missingFields;
}

function ensureNestedValues(root, parentKey, fieldNames, expectedValue, errors, label) {
    const parent = root[parentKey] || {};
    fieldNames.forEach(fieldName => {
        if (parent[fieldName] !== expectedValue) {
            errors.push(`${parentKey}.${fieldName} must ${label} in the Phase 4.86D template`);
        }
    });
}

function validateExecutionSteps(parsedYaml, errors) {
    const steps = parsedYaml.execution_steps;
    if (!Array.isArray(steps)) {
        errors.push('execution_steps missing');
        return;
    }
    EXPECTED_STEPS.forEach((expectedName, index) => {
        const step = steps[index];
        if (!step || step.name !== expectedName) {
            errors.push(`execution step missing: ${expectedName}`);
        }
        if (step && step.execution_allowed !== false) {
            errors.push('execution step allowed true in template is not allowed');
        }
        if (step && step.stop_if_failed !== true) {
            errors.push(`execution step stop_if_failed must be true: ${expectedName}`);
        }
    });
}

function validateStopGates(parsedYaml, errors) {
    const stopGates = parsedYaml.stop_gates || {};
    FIELDS.stop_gates.forEach(fieldName => {
        if (!Object.prototype.hasOwnProperty.call(stopGates, fieldName)) {
            errors.push(`stop gate missing: ${fieldName}`);
        } else if (stopGates[fieldName] !== true) {
            errors.push(`stop gate disabled: ${fieldName}`);
        }
    });
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) errors.push(`missing required fields: ${missingFields.join(',')}`);
    if (parsedYaml.phase !== EXECUTION_PHASE) errors.push(`phase must be ${EXECUTION_PHASE}`);
    if (parsedYaml.execution_plan_status !== 'draft_only') {
        errors.push('execution_plan_status must remain draft_only in the Phase 4.86D template');
    }
    Object.entries(TOP_FALSE).forEach(([field, message]) => {
        if (parsedYaml[field] !== false) errors.push(message);
    });

    ensureNestedValues(
        parsedYaml,
        'required_prior_artifacts',
        FIELDS.required_prior_artifacts,
        true,
        errors,
        'be true'
    );
    ensureNestedValues(
        parsedYaml,
        'required_prior_validations',
        FIELDS.required_prior_validations,
        false,
        errors,
        'remain false'
    );
    ensureNestedValues(
        parsedYaml,
        'network_runtime_policy',
        FIELDS.network_runtime_policy,
        false,
        errors,
        'remain false'
    );
    ensureNestedValues(
        parsedYaml,
        'db_training_prediction_policy',
        FIELDS.db_training_prediction_policy,
        false,
        errors,
        'remain false'
    );
    ensureNestedValues(parsedYaml, 'safety', FIELDS.safety, false, errors, 'remain false');
    ensureNestedValues(
        parsedYaml,
        'staging_policy',
        FIELDS.staging_policy.filter(field => field !== 'schema_validation_required'),
        false,
        errors,
        'remain false'
    );
    ensureNestedValues(parsedYaml, 'staging_policy', ['schema_validation_required'], true, errors, 'be true');
    validateTargetSection(parsedYaml, errors);
    validateExecutionSteps(parsedYaml, errors);
    validateStopGates(parsedYaml, errors);
    ensureArrayContainsAll(parsedYaml, 'next_phase_requirements', REQUIRED_NEXT_PHASE, errors);
    return { ok: errors.length === 0, missingFields, errors };
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
        errors.push('bulk scope allowed must remain false in the Phase 4.86D template');
    }
    if (target.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.86D template');
    }
}

function ensureArrayContainsAll(root, key, requiredValues, errors) {
    const value = root[key];
    if (!Array.isArray(value)) {
        errors.push(`${key} missing`);
        return;
    }
    requiredValues
        .filter(requiredValue => !value.includes(requiredValue))
        .forEach(requiredValue => errors.push(`${key} missing required value "${requiredValue}"`));
}

function validateTargetConsistency(args, executionPlanYaml, readinessArgs) {
    const planTarget = executionPlanYaml.target || {};
    const errors = [
        ['execution_plan.target.target_source', planTarget.target_source, args.target_source],
        ['execution_plan.target.target_engine_family', planTarget.target_engine_family, args.target_engine_family],
        ['execution_plan.target.target_scope_type', planTarget.target_scope_type, args.target_scope_type],
        ['execution_plan.target.target_match_id', planTarget.target_match_id, args.target_match_id],
    ]
        .filter(([, templateValue, cliValue]) => templateValue && templateValue !== cliValue)
        .map(
            ([label, templateValue, cliValue]) =>
                `target mismatch: ${label} "${templateValue}" does not match CLI value "${cliValue}"`
        );
    if (readinessArgs.errors && readinessArgs.errors.some(error => /target mismatch/i.test(error))) {
        errors.push(...readinessArgs.errors);
    }
    return errors;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: EXECUTION_PHASE,
        mode: MODE,
        ok: true,
        execution_plan: args.execution_plan,
        checklist: args.checklist,
        runbook: args.runbook,
        auth_form: args.auth_form,
        execution_plan_found: true,
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        checklist_yaml_block_found: true,
        runbook_yaml_block_found: true,
        auth_form_yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        execution_plan_valid: true,
        readiness_checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        errors: [],
        warnings: [
            'Phase 4.86D remains draft-only.',
            'CLI authorization yes values do not authorize execution in this phase.',
        ],
        non_execution_confirmations: buildNonExecutionConfirmations(),
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

    const planLoad = loadMarkdownYaml(
        args,
        'execution_plan',
        'execution-plan',
        'missing execution plan',
        'yaml_block_found',
        localDeps
    );
    if (planLoad.payload) return planLoad.payload;
    const planValidation = validateParsedYaml(planLoad.parsedYaml);
    if (!planValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'execution-plan-error',
            execution_plan_found: true,
            yaml_block_found: true,
            required_fields_present: planValidation.missingFields.length === 0,
            missing_fields: planValidation.missingFields,
            errors: planValidation.errors,
        });
    }

    const readinessPayload = runReadinessValidation(args, localDeps);
    if (!readinessPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'readiness-error',
            execution_plan_found: true,
            yaml_block_found: true,
            execution_plan_valid: true,
            errors: readinessPayload.errors,
        });
    }

    const targetErrors = validateTargetConsistency(args, planLoad.parsedYaml, readinessPayload);
    if (targetErrors.length) {
        return buildFailurePayload(args, {
            mode: 'target-error',
            execution_plan_found: true,
            checklist_found: true,
            runbook_found: true,
            auth_form_found: true,
            yaml_block_found: true,
            checklist_yaml_block_found: true,
            runbook_yaml_block_found: true,
            auth_form_yaml_block_found: true,
            required_fields_present: true,
            execution_plan_valid: true,
            readiness_checklist_valid: true,
            runbook_template_valid: true,
            auth_form_template_valid: true,
            errors: targetErrors,
        });
    }
    return buildSuccessPayload(args);
}

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: BLOCKED_COMMIT_MESSAGE,
        errors: [BLOCKED_COMMIT_MESSAGE],
    });
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
    EXECUTION_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    parseExecutionPlanYaml,
    validateParsedYaml,
    runValidation,
    main,
};
