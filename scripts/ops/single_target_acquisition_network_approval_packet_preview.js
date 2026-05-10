#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
    extractYamlBlock,
    buildNonExecutionConfirmations,
} = require('./single_target_acquisition_pre_network_runbook_validate');
const {
    runValidation: runExecutionPlanValidation,
} = require('./single_target_acquisition_network_execution_plan_validate');

const APPROVAL_PHASE = 'PHASE4.87D_SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_HUMAN_APPROVAL_PACKET';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: single-target acquisition network dry-run human approval packet execution is not wired in Phase 4.87D.';
const NEXT_REQUIRED_PHASE = 'Phase 4.88D or explicit user-authorized network dry-run preparation';
const MODE = 'single-target-acquisition-network-approval-packet-preview';

const FIELDS = {
    top: words(`
        phase approval_packet_status human_approval_packet_ready
        network_dry_run_authorized network_dry_run_execution_allowed
        staging_write_authorized db_write_authorized training_authorized
        prediction_authorized final_human_confirmation included_artifacts
        included_validators target human_required_inputs approval_sections
        blocking_reasons safety next_phase_requirements
    `),
    included_artifacts: words(`
        pre_network_runbook network_auth_form final_readiness_checklist
        execution_plan
    `),
    included_validators: words(`
        runbook_validator auth_form_validator readiness_validator
        execution_plan_validator
    `),
    target: words(`
        target_source target_engine_family target_scope_type target_match_id
        target_league target_season target_date max_targets bulk_scope_allowed
    `),
    human_required_inputs: words(`
        real_target_source_required real_single_target_scope_required
        source_terms_review_required license_review_required
        allowed_use_review_required network_dry_run_authorization_required
        proxy_browser_network_policy_review_required staging_policy_review_required
        no_db_write_confirmation_required no_training_confirmation_required
        no_prediction_confirmation_required
    `),
    approval_section: words(`
        required approved approved_by
    `),
    safety: words(`
        would_access_network would_launch_browser would_use_proxy
        would_execute_engine would_write_staging
        would_create_staging_directory would_write_source_manifest
        would_write_packet_file would_write_approval_packet_file
        would_write_db would_train would_predict would_bulk_harvest
    `),
};

const APPROVAL_SECTION_NAMES = words(`
    source_terms_approval network_dry_run_approval
    proxy_browser_network_policy_approval staging_policy_approval
    no_db_write_approval final_human_confirmation
`);

const REQUIRED_BLOCKING_REASONS = words(`
    approval_packet_preview_only real_target_source_missing
    real_single_target_scope_missing source_terms_not_approved
    network_dry_run_not_authorized proxy_browser_network_policy_not_approved
    staging_policy_not_approved final_human_confirmation_missing
    execution_plan_still_draft_only
`);

const REQUIRED_NEXT_PHASE = words(`
    explicit_user_supplied_real_source explicit_user_supplied_single_target
    explicit_source_terms_approval explicit_network_dry_run_authorization
    explicit_proxy_browser_network_policy_acceptance
    explicit_staging_policy_acceptance explicit_no_db_write_confirmation
    explicit_no_training_confirmation explicit_no_prediction_confirmation
    final_human_confirmation
`);

const EXPECTED_ARTIFACTS = {
    pre_network_runbook: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md',
    network_auth_form: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_AUTHORIZATION_FORM_TEMPLATE.md',
    final_readiness_checklist:
        'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_FINAL_READINESS_CHECKLIST_TEMPLATE.md',
    execution_plan: 'docs/runbooks/SINGLE_TARGET_ACQUISITION_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md',
};

const EXPECTED_VALIDATORS = {
    runbook_validator: 'scripts/ops/single_target_acquisition_pre_network_runbook_validate.js',
    auth_form_validator: 'scripts/ops/single_target_acquisition_network_auth_form_validate.js',
    readiness_validator: 'scripts/ops/single_target_acquisition_network_readiness_checklist_validate.js',
    execution_plan_validator: 'scripts/ops/single_target_acquisition_network_execution_plan_validate.js',
};

const CLI_REQUIRED = words(`
    approval_packet execution_plan checklist runbook auth_form target_source
    target_engine_family target_scope_type target_match_id terms_approval
    network_dry_run_authorization allow_browser_runtime allow_proxy_runtime
    allow_external_network allow_staging_write final_human_confirmation
`);

const CLI_YES_NO = words(`
    terms_approval network_dry_run_authorization allow_browser_runtime
    allow_proxy_runtime allow_external_network allow_staging_write
    final_human_confirmation
`);

const TOP_FALSE = {
    human_approval_packet_ready: 'human_approval_packet_ready true in template is not allowed',
    network_dry_run_authorized: 'network_dry_run_authorized true in template is not allowed',
    network_dry_run_execution_allowed: 'network_dry_run_execution_allowed true in template is not allowed',
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

function parseApprovalPacketYaml(yamlText) {
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
            parent[key] = parseScalar(valueText);
            return;
        }

        const nextContainerType = getNextContainerType(lines, lineIndex, indent);
        if (!nextContainerType) {
            parent[key] = null;
            return;
        }
        const container = nextContainerType === 'list' ? [] : {};
        parent[key] = container;
        stack.push({ indent, value: container });
    });

    return root;
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

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_target_acquisition_network_approval_packet_preview.js --approval-packet <path> --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --target-source <src> --target-engine-family titan_discovery --target-scope-type match_id --target-match-id <id> --terms-approval no --network-dry-run-authorization no --allow-browser-runtime no --allow-proxy-runtime no --allow-external-network no --allow-staging-write no --final-human-confirmation no',
        '  node scripts/ops/single_target_acquisition_network_approval_packet_preview.js --approval-packet <path> --execution-plan <path> --checklist <path> --runbook <path> --auth-form <path> --commit',
        '',
        'Safety:',
        '  Phase 4.87D previews a local human approval packet only.',
        '  No network, no browser, no proxy runtime, no engine execution, no DB, no file writes, no child processes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
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
        approval_packet_preview_only: true,
        approval_packet_valid: false,
        execution_plan_valid: false,
        readiness_checklist_valid: false,
        runbook_template_valid: false,
        auth_form_template_valid: false,
        human_approval_packet_ready: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
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
        would_write_approval_packet_file: false,
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
        phase: APPROVAL_PHASE,
        mode: fields.mode || MODE,
        ok: false,
        approval_packet: args.approval_packet || null,
        execution_plan: args.execution_plan || null,
        checklist: args.checklist || null,
        runbook: args.runbook || null,
        auth_form: args.auth_form || null,
        approval_packet_found: false,
        execution_plan_found: false,
        checklist_found: false,
        runbook_found: false,
        auth_form_found: false,
        yaml_block_found: false,
        execution_plan_yaml_block_found: false,
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

function loadApprovalPacketYaml(args, dependencies) {
    const targetPath = resolveLocalPath(args.approval_packet, dependencies.cwd);
    if (!dependencies.existsSync(targetPath)) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'approval-packet-error',
                approval_packet_found: false,
                errors: [`missing approval packet: ${toRelativePath(targetPath, dependencies.cwd)}`],
            }),
        };
    }
    const yamlText = extractYamlBlock(dependencies.readFileSync(targetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'approval-packet-error',
                approval_packet_found: true,
                yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }
    try {
        return { parsedYaml: parseApprovalPacketYaml(yamlText), yamlText };
    } catch (error) {
        return {
            payload: buildFailurePayload(args, {
                mode: 'approval-packet-error',
                approval_packet_found: true,
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
    const missingFields = FIELDS.top.filter(key => !Object.prototype.hasOwnProperty.call(parsedYaml, key));
    addMissingNested(parsedYaml, 'included_artifacts', FIELDS.included_artifacts, missingFields);
    addMissingNested(parsedYaml, 'included_validators', FIELDS.included_validators, missingFields);
    addMissingNested(parsedYaml, 'target', FIELDS.target, missingFields);
    addMissingNested(parsedYaml, 'human_required_inputs', FIELDS.human_required_inputs, missingFields);
    addMissingNested(parsedYaml, 'safety', FIELDS.safety, missingFields);
    const approvalSections = parsedYaml.approval_sections;
    if (!approvalSections || typeof approvalSections !== 'object' || Array.isArray(approvalSections)) {
        APPROVAL_SECTION_NAMES.forEach(sectionName => {
            FIELDS.approval_section.forEach(field => missingFields.push(`approval_sections.${sectionName}.${field}`));
        });
    } else {
        APPROVAL_SECTION_NAMES.forEach(sectionName => {
            addMissingNested(approvalSections, sectionName, FIELDS.approval_section, missingFields);
        });
    }
    return missingFields;
}

function ensureNestedValues(root, parentKey, fieldNames, expectedValue, errors, label) {
    const parent = root[parentKey] || {};
    fieldNames.forEach(fieldName => {
        if (parent[fieldName] !== expectedValue) {
            errors.push(`${parentKey}.${fieldName} must ${label} in the Phase 4.87D template`);
        }
    });
}

function ensureObjectValues(root, parentKey, expectedValues, errors) {
    const parent = root[parentKey] || {};
    Object.entries(expectedValues).forEach(([fieldName, expectedValue]) => {
        if (parent[fieldName] !== expectedValue) {
            errors.push(`${parentKey}.${fieldName} must be ${expectedValue}`);
        }
    });
}

function validateApprovalSections(parsedYaml, errors) {
    const sections = parsedYaml.approval_sections || {};
    APPROVAL_SECTION_NAMES.forEach(sectionName => {
        const section = sections[sectionName];
        if (!section || typeof section !== 'object' || Array.isArray(section)) {
            errors.push(`approval section missing: ${sectionName}`);
            return;
        }
        if (section.required !== true) errors.push(`approval section required must be true: ${sectionName}`);
        if (section.approved !== false) errors.push('approval section approved true in template is not allowed');
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
        errors.push('bulk scope allowed must remain false in the Phase 4.87D template');
    }
    if (target.max_targets !== 1) {
        errors.push('max_targets > 1 is not allowed in the Phase 4.87D template');
    }
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

function validateParsedYaml(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) errors.push(`missing required fields: ${missingFields.join(',')}`);
    if (parsedYaml.phase !== APPROVAL_PHASE) errors.push(`phase must be ${APPROVAL_PHASE}`);
    if (parsedYaml.approval_packet_status !== 'preview_only') {
        errors.push('approval_packet_status must remain preview_only in the Phase 4.87D template');
    }
    Object.entries(TOP_FALSE).forEach(([field, message]) => {
        if (parsedYaml[field] !== false) errors.push(message);
    });

    ensureObjectValues(parsedYaml, 'included_artifacts', EXPECTED_ARTIFACTS, errors);
    ensureObjectValues(parsedYaml, 'included_validators', EXPECTED_VALIDATORS, errors);
    ensureNestedValues(parsedYaml, 'human_required_inputs', FIELDS.human_required_inputs, true, errors, 'be true');
    ensureNestedValues(parsedYaml, 'safety', FIELDS.safety, false, errors, 'remain false');
    validateApprovalSections(parsedYaml, errors);
    validateTargetSection(parsedYaml, errors);
    ensureArrayContainsAll(
        parsedYaml,
        'blocking_reasons',
        REQUIRED_BLOCKING_REASONS,
        errors,
        'blocking reasons missing'
    );
    ensureArrayContainsAll(parsedYaml, 'next_phase_requirements', REQUIRED_NEXT_PHASE, errors);
    return { ok: errors.length === 0, missingFields, errors };
}

function validateTargetConsistency(args, approvalPacketYaml, executionPlanPayload) {
    const target = approvalPacketYaml.target || {};
    const errors = [
        ['approval_packet.target.target_source', target.target_source, args.target_source],
        ['approval_packet.target.target_engine_family', target.target_engine_family, args.target_engine_family],
        ['approval_packet.target.target_scope_type', target.target_scope_type, args.target_scope_type],
        ['approval_packet.target.target_match_id', target.target_match_id, args.target_match_id],
    ]
        .filter(([, templateValue, cliValue]) => templateValue && templateValue !== cliValue)
        .map(
            ([label, templateValue, cliValue]) =>
                `target mismatch: ${label} "${templateValue}" does not match CLI value "${cliValue}"`
        );
    if (executionPlanPayload.errors && executionPlanPayload.errors.some(error => /target mismatch/i.test(error))) {
        errors.push(...executionPlanPayload.errors);
    }
    return errors;
}

function buildSuccessPayload(args) {
    return {
        ...buildSafetyFlags(),
        phase: APPROVAL_PHASE,
        mode: MODE,
        ok: true,
        approval_packet: args.approval_packet,
        execution_plan: args.execution_plan,
        checklist: args.checklist,
        runbook: args.runbook,
        auth_form: args.auth_form,
        approval_packet_found: true,
        execution_plan_found: true,
        checklist_found: true,
        runbook_found: true,
        auth_form_found: true,
        yaml_block_found: true,
        execution_plan_yaml_block_found: true,
        checklist_yaml_block_found: true,
        runbook_yaml_block_found: true,
        auth_form_yaml_block_found: true,
        required_fields_present: true,
        missing_fields: [],
        approval_packet_valid: true,
        execution_plan_valid: true,
        readiness_checklist_valid: true,
        runbook_template_valid: true,
        auth_form_template_valid: true,
        errors: [],
        warnings: [
            'Phase 4.87D remains preview-only.',
            'CLI authorization yes values do not authorize execution in this phase.',
        ],
        non_execution_confirmations: [...buildNonExecutionConfirmations(), 'no_approval_packet_file_writes'],
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

    const approvalPacketLoad = loadApprovalPacketYaml(args, localDeps);
    if (approvalPacketLoad.payload) return approvalPacketLoad.payload;

    const approvalPacketValidation = validateParsedYaml(approvalPacketLoad.parsedYaml);
    if (!approvalPacketValidation.ok) {
        return buildFailurePayload(args, {
            mode: 'approval-packet-error',
            approval_packet_found: true,
            yaml_block_found: true,
            required_fields_present: approvalPacketValidation.missingFields.length === 0,
            missing_fields: approvalPacketValidation.missingFields,
            errors: approvalPacketValidation.errors,
        });
    }

    const executionPlanPayload = runExecutionPlanValidation(args, localDeps);
    if (!executionPlanPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'execution-plan-error',
            approval_packet_found: true,
            yaml_block_found: true,
            approval_packet_valid: true,
            errors: executionPlanPayload.errors,
        });
    }

    const targetErrors = validateTargetConsistency(args, approvalPacketLoad.parsedYaml, executionPlanPayload);
    if (targetErrors.length) {
        return buildFailurePayload(args, {
            mode: 'target-error',
            approval_packet_found: true,
            execution_plan_found: true,
            checklist_found: true,
            runbook_found: true,
            auth_form_found: true,
            yaml_block_found: true,
            execution_plan_yaml_block_found: true,
            checklist_yaml_block_found: true,
            runbook_yaml_block_found: true,
            auth_form_yaml_block_found: true,
            required_fields_present: true,
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
    APPROVAL_PHASE,
    BLOCKED_COMMIT_MESSAGE,
    parseArgs,
    parseApprovalPacketYaml,
    validateParsedYaml,
    runValidation,
    main,
};
