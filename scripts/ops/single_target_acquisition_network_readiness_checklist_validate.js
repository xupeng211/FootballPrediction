#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    parseYamlBlock,
    validateParsedYaml: validateRunbookParsedYaml,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    validateParsedYaml: validateAuthFormParsedYaml,
} = require('./single_target_acquisition_network_auth_form_validate');

const READINESS_PHASE = 'PHASE4.85D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FINAL_READINESS_CHECKLIST';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run final readiness execution is not wired in Phase 4.85D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.86D or explicit user-authorized network dry-run preparation';
const MODE = 'single-target-acquisition-network-readiness-checklist-validate';
const TEMPLATE_WARNING = [
    'Phase 4.85D remains template-only.',
    'CLI authorization yes values do not authorize execution in this phase.',
];

const FIELDS = {
    top: words(`
        phase checklist_status network_dry_run_ready network_dry_run_authorized
        staging_write_authorized db_write_authorized training_authorized
        prediction_authorized final_human_confirmation required_prior_artifacts
        required_validations target source_terms network_authorization
        proxy_browser_network_preflight staging_policy
        db_training_prediction_policy safety blocking_reasons
        next_phase_requirements
    `),
    required_prior_artifacts: words(`
        runtime_scaffold_present staging_schema_validator_present
        staging_writer_preflight_present staging_packet_preview_present
        pre_network_runbook_present network_auth_form_present
    `),
    required_validations: words(`
        runtime_scaffold_validated staging_schema_validated
        staging_writer_preflight_validated staging_packet_preview_validated
        pre_network_runbook_validated network_auth_form_validated
    `),
    target: words(`
        target_source target_engine_family target_scope_type target_match_id
        target_league target_season target_date max_targets bulk_scope_allowed
    `),
    source_terms: words(`
        source_url terms_url license_url allowed_use terms_approval
        terms_reviewed_by human_approval_note
    `),
    network_authorization: words(`
        network_dry_run_authorization allow_external_network
        allow_browser_runtime allow_proxy_runtime allow_staging_write
    `),
    proxy_browser_network_preflight: words(`
        proxy_required proxy_provider proxy_health_check_passed
        browser_required browser_provider network_policy_reviewed
        rate_limit_policy_reviewed retry_policy_reviewed
        user_agent_policy_reviewed no_login_paywall_bypass
        no_anti_bot_bypass no_bulk_expansion
    `),
    staging_policy: words(`
        output_root_reviewed output_root_allowed schema_validation_passed
        packet_preview_passed staging_write_authorized
    `),
    db_training_prediction_policy: words(`
        db_write_authorized training_authorized prediction_authorized
        model_artifact_loading_authorized
    `),
    safety: words(`
        would_access_network would_launch_browser would_use_proxy
        would_execute_engine would_write_staging
        would_create_staging_directory would_write_source_manifest
        would_write_packet_file would_write_db would_train
        would_predict would_bulk_harvest
    `),
};

const REQUIRED_ARRAYS = {
    blocking_reasons: words(`
        checklist_template_only network_dry_run_not_authorized
        staging_write_not_authorized db_write_not_authorized
        final_human_confirmation_missing
    `),
    next_phase_requirements: words(`
        real_target_source real_single_target_scope reviewed_source_terms
        explicit_network_dry_run_authorization
        accepted_proxy_browser_network_preflight
        accepted_staging_packet_preview confirmed_no_db_write
        confirmed_no_training confirmed_no_prediction
    `),
};

const CLI_REQUIRED = words(`
    checklist runbook auth_form target_source target_engine_family
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

const CHECKS = {
    topFalse: {
        network_dry_run_ready: 'network_dry_run_ready true in template is not allowed',
        network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
        staging_write_authorized: 'staging_write_authorized true in template is not allowed',
        db_write_authorized: 'db_write_authorized true in template is not allowed',
        training_authorized: 'training_authorized true in template is not allowed',
        prediction_authorized: 'prediction_authorized true in template is not allowed',
        final_human_confirmation: 'final_human_confirmation true in template is not allowed',
    },
    nestedNo: {
        source_terms: ['terms_approval'],
        network_authorization: words(`
            network_dry_run_authorization allow_external_network
            allow_browser_runtime allow_proxy_runtime allow_staging_write
        `),
    },
    nestedFalse: {
        required_validations: FIELDS.required_validations,
        staging_policy: FIELDS.staging_policy,
        db_training_prediction_policy: FIELDS.db_training_prediction_policy,
        safety: FIELDS.safety,
        proxy_browser_network_preflight: words(`
            proxy_health_check_passed network_policy_reviewed
            rate_limit_policy_reviewed retry_policy_reviewed
            user_agent_policy_reviewed
        `),
    },
    nestedTrue: {
        required_prior_artifacts: FIELDS.required_prior_artifacts,
        proxy_browser_network_preflight: words(`
            no_login_paywall_bypass no_anti_bot_bypass no_bulk_expansion
        `),
    },
};

function words(text) {
    return text.trim().split(/\s+/).filter(Boolean);
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_readiness_checklist_validate.js --checklist <path> --runbook <path> --auth-form <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_readiness_checklist_validate.js --checklist <path> --runbook <path> --auth-form <path> --commit',
        '',
        'Safety:',
        '  Phase 4.85D validates a local network readiness checklist template only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        checklist: '',
        runbook: '',
        auth_form: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--commit') {
            args.commit = true;
            continue;
        }
        if (token === '--json') {
            args.json = true;
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
            continue;
        }
        if (index + 1 < argv.length && !argv[index + 1].startsWith('--')) {
            args[token.slice(2).replace(/-/g, '_')] = String(argv[index + 1] || '');
            index += 1;
            continue;
        }
        throw new Error(`Unknown argument: ${token}`);
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

function buildSafetyFlags() {
    return {
        readiness_checklist_template_only: true,
        checklist_valid: false,
        runbook_template_valid: false,
        auth_form_template_valid: false,
        network_dry_run_ready: false,
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
        phase: READINESS_PHASE,
        mode: fields.mode || MODE,
        ok: false,
        checklist: args.checklist || null,
        runbook: args.runbook || null,
        auth_form: args.auth_form || null,
        checklist_found: false,
        runbook_found: false,
        auth_form_found: false,
        yaml_block_found: false,
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

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: BLOCKED_COMMIT_MESSAGE,
        errors: [BLOCKED_COMMIT_MESSAGE],
    });
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
            errors.push(`${parentKey}.${fieldName} must ${label} in the Phase 4.85D template`);
        }
    });
}

function ensureArrayContainsAll(root, key, requiredValues, errors, label) {
    const value = root[key];
    if (!Array.isArray(value)) {
        errors.push(`${label || key} missing`);
        return;
    }
    requiredValues
        .filter(requiredValue => !value.includes(requiredValue))
        .forEach(requiredValue => errors.push(`${label || key} missing required value "${requiredValue}"`));
}

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);

    if (missingFields.length) {
        errors.push(`missing required fields: ${missingFields.join(',')}`);
    }
    if (parsedYaml.phase !== READINESS_PHASE) {
        errors.push(`phase must be ${READINESS_PHASE}`);
    }
    if (parsedYaml.checklist_status !== 'template_only') {
        errors.push('checklist_status must remain template_only in the Phase 4.85D template');
    }

    Object.entries(CHECKS.topFalse).forEach(([field, message]) => {
        if (parsedYaml[field] !== false) {
            errors.push(message);
        }
    });
    Object.entries(CHECKS.nestedNo).forEach(([parentKey, fieldNames]) =>
        ensureNestedValues(parsedYaml, parentKey, fieldNames, 'no', errors, 'remain no')
    );
    Object.entries(CHECKS.nestedFalse).forEach(([parentKey, fieldNames]) =>
        ensureNestedValues(parsedYaml, parentKey, fieldNames, false, errors, 'remain false')
    );
    ensureNestedValues(
        parsedYaml,
        'proxy_browser_network_preflight',
        CHECKS.nestedTrue.proxy_browser_network_preflight,
        true,
        errors,
        'be true'
    );

    const target = parsedYaml.target || {};
    const priorArtifacts = parsedYaml.required_prior_artifacts || {};
    FIELDS.required_prior_artifacts.forEach(fieldName => {
        if (priorArtifacts[fieldName] !== true) {
            errors.push(`required prior artifact missing: ${fieldName}`);
        }
    });
    if (target.target_engine_family !== 'titan_discovery') {
        errors.push(`unsupported engine family "${target.target_engine_family}"`);
    }
    if (target.target_scope_type === 'bulk') {
        errors.push('unsupported scope type bulk');
    }
    if (target.bulk_scope_allowed !== false) {
        errors.push('bulk scope allowed must remain false in the Phase 4.85D template');
    }
    if (target.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.85D template');
    }

    ensureArrayContainsAll(
        parsedYaml,
        'blocking_reasons',
        REQUIRED_ARRAYS.blocking_reasons,
        errors,
        'blocking reasons'
    );
    ensureArrayContainsAll(
        parsedYaml,
        'next_phase_requirements',
        REQUIRED_ARRAYS.next_phase_requirements,
        errors,
        'next_phase_requirements'
    );

    return { ok: errors.length === 0, missingFields, errors };
}

function validateRequiredCliFields(args) {
    return CLI_REQUIRED.flatMap(field => {
        if (args[field]) {
            return [];
        }
        if (field === 'checklist') return ['missing checklist'];
        if (field === 'runbook') return ['missing runbook'];
        if (field === 'auth_form') return ['missing auth form'];
        return [`missing ${field.replace(/_/g, ' ')} path or value`];
    });
}

function validateCliYesNoFields(args) {
    return CLI_YES_NO.flatMap(field => {
        const value = args[field];
        return value === 'yes' || value === 'no' ? [] : [`--${field.replace(/_/g, '-')} is required (yes/no)`];
    });
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
    return errors;
}

function validateCliArgsOrPayload(args) {
    const errors = [
        ...validateRequiredCliFields(args),
        ...validateCliYesNoFields(args),
        ...validateCliTargetFields(args),
    ];
    return errors.length ? buildFailurePayload(args, { mode: 'argument-error', errors }) : null;
}

function loadMarkdownYaml(args, fieldName, modePrefix, missingLabel, yamlFlagField, dependencies) {
    const { cwd, existsSync, readFileSync } = dependencies;
    const targetPath = resolveLocalPath(args[fieldName], cwd);
    if (!existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: `${modePrefix}-error`,
                [`${fieldName}_found`]: false,
                errors: [`${missingLabel}: ${toRelativePath(targetPath, cwd)}`],
            }),
        };
    }

    const markdownText = readFileSync(targetPath, 'utf8');
    const yamlText = extractYamlBlock(markdownText);
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
        return { parsedYaml: parseYamlBlock(yamlText) };
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

function buildValidatedContext(args, fields = {}) {
    return buildFailurePayload(args, {
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        runbook_yaml_block_found: true,
        auth_form_yaml_block_found: true,
        required_fields_present: true,
        checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        ...fields,
    });
}

function validateChecklistOrPayload(args, parsedYaml) {
    const parsedValidation = validateParsedYaml(parsedYaml);
    if (parsedValidation.ok) return null;
    return {
        payload: buildFailurePayload(args, {
            mode: 'checklist-error',
            checklist_found: true,
            yaml_block_found: true,
            required_fields_present: parsedValidation.missingFields.length === 0,
            missing_fields: parsedValidation.missingFields,
            errors: parsedValidation.errors,
        }),
    };
}

function validateTemplateOrPayload(args, parsedYaml, validator, mode, message, fields) {
    const parsedValidation = validator(parsedYaml);
    if (parsedValidation.ok) return null;
    return {
        payload: buildFailurePayload(args, {
            mode,
            ...fields,
            errors: [`${message}: ${parsedValidation.errors.join('; ')}`],
        }),
    };
}

function validateTargetConsistency(args, checklistYaml, runbookYaml, authFormYaml) {
    const checklistTarget = checklistYaml.target || {};
    const runbookTarget = runbookYaml.target || {};
    const authRequest = authFormYaml.request || {};
    const errors = [
        ['checklist.target.target_source', checklistTarget.target_source, args.target_source],
        ['checklist.target.target_engine_family', checklistTarget.target_engine_family, args.target_engine_family],
        ['checklist.target.target_scope_type', checklistTarget.target_scope_type, args.target_scope_type],
        ['checklist.target.target_match_id', checklistTarget.target_match_id, args.target_match_id],
        ['runbook.target.target_source', runbookTarget.target_source, args.target_source],
        ['runbook.target.target_engine_family', runbookTarget.target_engine_family, args.target_engine_family],
        ['runbook.target.target_scope_type', runbookTarget.target_scope_type, args.target_scope_type],
        ['runbook.target.target_match_id', runbookTarget.target_match_id, args.target_match_id],
        ['auth_form.request.target_source', authRequest.target_source, args.target_source],
        ['auth_form.request.target_engine_family', authRequest.target_engine_family, args.target_engine_family],
        ['auth_form.request.target_scope_type', authRequest.target_scope_type, args.target_scope_type],
        ['auth_form.request.target_match_id', authRequest.target_match_id, args.target_match_id],
    ]
        .filter(([, templateValue, cliValue]) => templateValue && templateValue !== cliValue)
        .map(
            ([label, templateValue, cliValue]) =>
                `target mismatch: ${label} "${templateValue}" does not match CLI value "${cliValue}"`
        );

    return errors.length ? buildValidatedContext(args, { mode: 'target-error', errors }) : null;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: READINESS_PHASE,
        mode: MODE,
        ok: true,
        checklist: args.checklist,
        runbook: args.runbook,
        auth_form: args.auth_form,
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        runbook_yaml_block_found: true,
        auth_form_yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        errors: [],
        warnings: TEMPLATE_WARNING,
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

    const checklistLoad = loadMarkdownYaml(
        args,
        'checklist',
        'checklist',
        'missing checklist',
        'yaml_block_found',
        localDeps
    );
    if (checklistLoad.payload) return checklistLoad.payload;

    const checklistValidation = validateChecklistOrPayload(args, checklistLoad.parsedYaml);
    if (checklistValidation) return checklistValidation.payload;

    const runbookLoad = loadMarkdownYaml(
        args,
        'runbook',
        'runbook',
        'missing runbook',
        'runbook_yaml_block_found',
        localDeps
    );
    if (runbookLoad.payload) return runbookLoad.payload;

    const runbookValidation = validateTemplateOrPayload(
        args,
        runbookLoad.parsedYaml,
        validateRunbookParsedYaml,
        'runbook-error',
        'runbook template validation failed',
        {
            checklist_found: true,
            runbook_found: true,
            yaml_block_found: true,
            runbook_yaml_block_found: true,
            checklist_valid: true,
        }
    );
    if (runbookValidation) return runbookValidation.payload;

    const authFormLoad = loadMarkdownYaml(
        args,
        'auth_form',
        'auth-form',
        'missing auth form',
        'auth_form_yaml_block_found',
        localDeps
    );
    if (authFormLoad.payload) return authFormLoad.payload;

    const authFormValidation = validateTemplateOrPayload(
        args,
        authFormLoad.parsedYaml,
        validateAuthFormParsedYaml,
        'auth-form-error',
        'auth form template validation failed',
        {
            checklist_found: true,
            runbook_found: true,
            auth_form_found: true,
            yaml_block_found: true,
            runbook_yaml_block_found: true,
            auth_form_yaml_block_found: true,
            checklist_valid: true,
            runbook_template_valid: true,
        }
    );
    if (authFormValidation) return authFormValidation.payload;

    const targetConsistencyPayload = validateTargetConsistency(
        args,
        checklistLoad.parsedYaml,
        runbookLoad.parsedYaml,
        authFormLoad.parsedYaml
    );
    if (targetConsistencyPayload) return targetConsistencyPayload;

    return buildSuccessPayload(args);
}

function writePayload(payload, io) {
    io.stdout(`${JSON.stringify(payload, null, 2)}\n`);
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
            writePayload(buildBlockedCommitPayload(args), output);
            return 1;
        }
        const payload = runValidation(args, dependencies);
        writePayload(payload, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        writePayload(
            buildFailurePayload(
                { checklist: '', runbook: '', auth_form: '' },
                { mode: 'argument-error', errors: [error.message] }
            ),
            output
        );
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    READINESS_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    validateParsedYaml,
    runValidation,
    main,
};
