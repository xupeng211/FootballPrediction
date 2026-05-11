#!/usr/bin/env node
/**
 * Phase 5.00F: FotMob stdout-only network dry-run execution plan preview.
 *
 * This command reads a local execution plan template and authorization packet
 * template, then prints a JSON summary to stdout. It does not access the
 * network, launch browser or proxy runtime, execute legacy FotMob runtime,
 * write files, connect to DB, spawn child processes, train, or predict.
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const authorizationPacketGate = require('./fotmob_stdout_network_dry_run_authorization_packet.js');

const PHASE = 'PHASE5_00F_FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_EXECUTION_PLAN';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: FotMob stdout-only network dry-run execution plan is not executable in Phase 5.00F.';
const NEXT_REQUIRED_ACTION = 'user_must_fill_real_fotmob_target_terms_allowed_use_and_network_authorization';

const EXPECTED_ABORT_CONDITIONS = [
    'missing_user_filled_authorization_packet',
    'real_target_not_provided',
    'source_terms_not_approved',
    'allowed_use_not_approved',
    'external_network_not_authorized',
    'target_scope_not_single_target',
    'target_count_not_one',
    'browser_required_without_authorization',
    'proxy_required_without_authorization',
    'login_required',
    'paywall_bypass_required',
    'anti_bot_bypass_required',
    'staging_write_requested',
    'source_manifest_write_requested',
    'db_write_requested',
    'training_requested',
    'prediction_requested',
    'legacy_runtime_requested',
    'final_human_confirmation_missing',
];

const EXPECTED_BLOCKING_REASONS = [
    'execution_plan_template_only',
    'user_filled_authorization_packet_missing',
    'real_target_not_provided',
    'source_terms_not_approved',
    'allowed_use_not_approved',
    'external_network_not_authorized',
    'final_human_confirmation_missing',
    'future_explicit_execution_confirmation_required',
];

const EXPECTED_STDOUT_FIELDS = [
    'phase',
    'target',
    'request_summary',
    'response_status_summary',
    'parser_preview',
    'parser_confidence',
    'safety_summary',
    'stop_gates',
];

const EXPECTED_REQUIRED_USER_INPUTS = [
    'real_fotmob_target',
    'source_homepage_url',
    'terms_url',
    'license_url_if_any',
    'allowed_use_summary',
    'explicit_stdout_only_network_authorization',
    'browser_policy',
    'proxy_policy',
    'staging_policy',
    'no_db_write_confirmation',
    'no_training_confirmation',
    'no_prediction_confirmation',
    'final_human_confirmation',
];

const PRE_EXECUTION_CHECKS = [
    'user_filled_authorization_packet_check',
    'real_target_check',
    'source_terms_check',
    'allowed_use_check',
    'explicit_network_authorization_check',
    'single_target_scope_check',
    'no_browser_proxy_by_default_check',
    'no_staging_write_by_default_check',
    'no_db_training_prediction_check',
    'final_human_confirmation_check',
];

const REQUIRED_TOP_LEVEL_FIELDS = [
    'phase',
    'execution_plan_status',
    'execution_plan_ready',
    'execution_plan_reviewed',
    'execution_plan_accepted',
    'execution_allowed',
    'authorization_packet',
    'target',
    'runtime_policy',
    'output_policy',
    'data_safety_policy',
    'pre_execution_checks',
    'abort_conditions',
    'stdout_preview_expected_shape',
    'post_run_review',
    'codex_constraints',
    'safety',
    'execution_blocking_reasons',
    'next_step_after_phase_5_00f',
];

const REQUIRED_NESTED_FIELDS = {
    authorization_packet: [
        'required',
        'user_filled_packet_provided',
        'authorization_packet_reviewed',
        'authorization_packet_accepted',
        'network_dry_run_authorized',
        'final_human_confirmation',
    ],
    target: [
        'target_source',
        'target_scope_type',
        'target_match_id',
        'target_league',
        'target_season',
        'target_date',
        'target_url',
        'target_count',
        'max_targets',
        'single_target_only',
        'bulk_scope_allowed',
    ],
    runtime_policy: [
        'stdout_only',
        'external_network_allowed',
        'browser_runtime_allowed',
        'proxy_runtime_allowed',
        'legacy_runtime_allowed',
        'acquisition_engine_allowed',
        'rate_limit_policy',
        'retry_policy',
        'user_agent_policy',
    ],
    output_policy: [
        'stdout_preview_allowed',
        'staging_write_allowed',
        'source_manifest_write_allowed',
        'packet_write_allowed',
        'output_root',
    ],
    data_safety_policy: [
        'db_write_allowed',
        'training_allowed',
        'prediction_allowed',
        'model_artifact_loading_allowed',
    ],
    stdout_preview_expected_shape: [
        'expected_top_level_fields',
        'bounded_preview_required',
        'include_raw_html',
        'include_large_payload',
        'include_personal_data',
        'max_preview_bytes',
    ],
    post_run_review: [
        'required_after_future_execution',
        'review_stdout_preview',
        'review_response_status',
        'review_parser_confidence',
        'review_schema_drift',
        'review_stop_gates',
        'decide_whether_to_allow_staging_preview_later',
        'db_write_still_forbidden',
    ],
    codex_constraints: [
        'codex_may_not_self_fill_target',
        'codex_may_not_self_approve_terms',
        'codex_may_not_self_authorize_network',
        'codex_may_not_enable_execution',
        'codex_may_not_execute_network_dry_run',
        'codex_may_not_write_runtime_files',
    ],
    safety: [
        'would_access_network',
        'would_launch_browser',
        'would_use_proxy',
        'would_execute_legacy_runtime',
        'would_execute_engine',
        'would_write_staging',
        'would_create_staging_directory',
        'would_write_source_manifest',
        'would_write_packet_file',
        'would_write_execution_plan_file',
        'would_write_db',
        'would_train',
        'would_predict',
        'would_spawn_child_process',
    ],
    next_step_after_phase_5_00f: ['continue_template_phases', 'requires_user_real_input', 'required_user_inputs'],
};

const SAFETY_FALSE_FIELDS = REQUIRED_NESTED_FIELDS.safety;
const CODEX_TRUE_FIELDS = REQUIRED_NESTED_FIELDS.codex_constraints;

function parseArgs(argv = []) {
    const args = {
        plan: '',
        packet: '',
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

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/fotmob_stdout_network_dry_run_execution_plan.js --plan <path> --packet <path>',
        '  node scripts/ops/fotmob_stdout_network_dry_run_execution_plan.js --plan <path> --packet <path> --commit',
        '',
        'Safety:',
        '  Phase 5.00F validates a local execution plan template only.',
        '  No network, browser, proxy, legacy runtime, DB, file writes, child processes, training, or prediction.',
    ].join('\n');
}

function defaultDependencies() {
    return {
        cwd: process.cwd(),
        existsSync: targetPath => fs.existsSync(targetPath),
        readFileSync: (targetPath, encoding) => fs.readFileSync(targetPath, encoding),
    };
}

function resolveLocalPath(rawPath, cwd = process.cwd()) {
    if (!rawPath) return '';
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) return '';
    return path.relative(cwd, absolutePath) || '.';
}

function extractYamlBlock(markdownText) {
    return authorizationPacketGate.extractYamlBlock(markdownText);
}

function parsePlanYaml(yamlText) {
    return authorizationPacketGate.parsePacketYaml(yamlText);
}

function getPath(root, dottedPath) {
    return dottedPath.split('.').reduce((current, key) => {
        if (!current || typeof current !== 'object') return undefined;
        return current[key];
    }, root);
}

function hasOwn(root, key) {
    return Object.prototype.hasOwnProperty.call(root, key);
}

function findMissingFields(parsedYaml) {
    const missingFields = REQUIRED_TOP_LEVEL_FIELDS.filter(key => !hasOwn(parsedYaml, key));
    Object.entries(REQUIRED_NESTED_FIELDS).forEach(([sectionName, fields]) => {
        const section = parsedYaml[sectionName];
        if (!section || typeof section !== 'object' || Array.isArray(section)) {
            fields.forEach(field => missingFields.push(`${sectionName}.${field}`));
            return;
        }
        fields.filter(field => !hasOwn(section, field)).forEach(field => missingFields.push(`${sectionName}.${field}`));
    });

    PRE_EXECUTION_CHECKS.forEach(checkName => {
        const check = getPath(parsedYaml, `pre_execution_checks.${checkName}`);
        if (!check || typeof check !== 'object' || Array.isArray(check)) {
            missingFields.push(`pre_execution_checks.${checkName}`);
            ['required', 'checked', 'passed'].forEach(field =>
                missingFields.push(`pre_execution_checks.${checkName}.${field}`)
            );
            return;
        }
        ['required', 'checked', 'passed']
            .filter(field => !hasOwn(check, field))
            .forEach(field => missingFields.push(`pre_execution_checks.${checkName}.${field}`));
    });

    return missingFields;
}

function expectValue(parsedYaml, dottedPath, expectedValue, errors, message) {
    if (getPath(parsedYaml, dottedPath) !== expectedValue) {
        errors.push(message || `${dottedPath} must be ${expectedValue}`);
    }
}

function expectListIncludes(parsedYaml, dottedPath, expectedItems, errors, messagePrefix) {
    const value = getPath(parsedYaml, dottedPath);
    if (!Array.isArray(value)) {
        errors.push(`${dottedPath} missing or not list`);
        return;
    }

    const missingItems = expectedItems.filter(item => !value.includes(item));
    if (missingItems.length) {
        errors.push(`${messagePrefix}: ${missingItems.join(', ')}`);
    }
}

function validatePreExecutionChecks(parsedYaml, errors) {
    PRE_EXECUTION_CHECKS.forEach(checkName => {
        expectValue(
            parsedYaml,
            `pre_execution_checks.${checkName}.required`,
            true,
            errors,
            `pre_execution_checks.${checkName}.required not true`
        );
        expectValue(
            parsedYaml,
            `pre_execution_checks.${checkName}.checked`,
            false,
            errors,
            `pre_execution_checks.${checkName}.checked true`
        );
        expectValue(
            parsedYaml,
            `pre_execution_checks.${checkName}.passed`,
            false,
            errors,
            `pre_execution_checks.${checkName}.passed true`
        );
    });
}

function validatePlanValues(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) {
        errors.push(`missing required fields: ${missingFields.join(', ')}`);
    }

    expectValue(parsedYaml, 'phase', PHASE, errors, `phase must be ${PHASE}`);
    expectValue(
        parsedYaml,
        'execution_plan_status',
        'template_only',
        errors,
        'execution_plan_status not template_only'
    );
    expectValue(parsedYaml, 'execution_plan_ready', false, errors, 'execution_plan_ready true');
    expectValue(parsedYaml, 'execution_plan_reviewed', false, errors, 'execution_plan_reviewed true');
    expectValue(parsedYaml, 'execution_plan_accepted', false, errors, 'execution_plan_accepted true');
    expectValue(parsedYaml, 'execution_allowed', false, errors, 'execution_allowed true');

    expectValue(parsedYaml, 'authorization_packet.required', true, errors, 'authorization_packet.required not true');
    expectValue(
        parsedYaml,
        'authorization_packet.user_filled_packet_provided',
        false,
        errors,
        'user_filled_packet_provided true'
    );
    expectValue(
        parsedYaml,
        'authorization_packet.authorization_packet_reviewed',
        false,
        errors,
        'authorization_packet_reviewed true'
    );
    expectValue(
        parsedYaml,
        'authorization_packet.authorization_packet_accepted',
        false,
        errors,
        'authorization_packet_accepted true'
    );
    expectValue(
        parsedYaml,
        'authorization_packet.network_dry_run_authorized',
        false,
        errors,
        'network_dry_run_authorized true'
    );
    expectValue(
        parsedYaml,
        'authorization_packet.final_human_confirmation',
        false,
        errors,
        'final_human_confirmation true'
    );

    expectValue(parsedYaml, 'target.target_source', 'fotmob', errors, 'target_source not fotmob');
    const targetCount = getPath(parsedYaml, 'target.target_count');
    if (targetCount > 1) errors.push('target_count > 1');
    if (targetCount !== 0) errors.push('target_count must remain 0 in Phase 5.00F template');
    const maxTargets = getPath(parsedYaml, 'target.max_targets');
    if (maxTargets > 1) errors.push('max_targets > 1');
    if (maxTargets !== 1) errors.push('max_targets must be 1');
    expectValue(parsedYaml, 'target.single_target_only', true, errors, 'single_target_only not true');
    expectValue(parsedYaml, 'target.bulk_scope_allowed', false, errors, 'bulk_scope_allowed true');

    expectValue(parsedYaml, 'runtime_policy.stdout_only', true, errors, 'stdout_only false');
    expectValue(parsedYaml, 'runtime_policy.external_network_allowed', false, errors, 'external_network_allowed true');
    expectValue(parsedYaml, 'runtime_policy.browser_runtime_allowed', false, errors, 'browser_runtime_allowed true');
    expectValue(parsedYaml, 'runtime_policy.proxy_runtime_allowed', false, errors, 'proxy_runtime_allowed true');
    expectValue(parsedYaml, 'runtime_policy.legacy_runtime_allowed', false, errors, 'legacy_runtime_allowed true');
    expectValue(
        parsedYaml,
        'runtime_policy.acquisition_engine_allowed',
        false,
        errors,
        'acquisition_engine_allowed true'
    );

    expectValue(parsedYaml, 'output_policy.stdout_preview_allowed', false, errors, 'stdout_preview_allowed true');
    expectValue(parsedYaml, 'output_policy.staging_write_allowed', false, errors, 'staging_write_allowed true');
    expectValue(
        parsedYaml,
        'output_policy.source_manifest_write_allowed',
        false,
        errors,
        'source_manifest_write_allowed true'
    );
    expectValue(parsedYaml, 'output_policy.packet_write_allowed', false, errors, 'packet_write_allowed true');

    expectValue(parsedYaml, 'data_safety_policy.db_write_allowed', false, errors, 'db_write_allowed true');
    expectValue(parsedYaml, 'data_safety_policy.training_allowed', false, errors, 'training_allowed true');
    expectValue(parsedYaml, 'data_safety_policy.prediction_allowed', false, errors, 'prediction_allowed true');
    expectValue(
        parsedYaml,
        'data_safety_policy.model_artifact_loading_allowed',
        false,
        errors,
        'model_artifact_loading_allowed true'
    );

    validatePreExecutionChecks(parsedYaml, errors);

    expectListIncludes(parsedYaml, 'abort_conditions', EXPECTED_ABORT_CONDITIONS, errors, 'missing abort_conditions');
    expectListIncludes(
        parsedYaml,
        'stdout_preview_expected_shape.expected_top_level_fields',
        EXPECTED_STDOUT_FIELDS,
        errors,
        'missing stdout_preview_expected_shape.expected_top_level_fields'
    );
    expectValue(
        parsedYaml,
        'stdout_preview_expected_shape.bounded_preview_required',
        true,
        errors,
        'bounded_preview_required not true'
    );
    expectValue(parsedYaml, 'stdout_preview_expected_shape.include_raw_html', false, errors, 'include_raw_html true');
    expectValue(
        parsedYaml,
        'stdout_preview_expected_shape.include_large_payload',
        false,
        errors,
        'include_large_payload true'
    );
    expectValue(
        parsedYaml,
        'stdout_preview_expected_shape.include_personal_data',
        false,
        errors,
        'include_personal_data true'
    );

    Object.entries(parsedYaml.post_run_review || {}).forEach(([key, value]) => {
        if (value !== true) errors.push(`post_run_review.${key} not true`);
    });

    CODEX_TRUE_FIELDS.forEach(field => {
        expectValue(parsedYaml, `codex_constraints.${field}`, true, errors, `${field} false`);
    });

    SAFETY_FALSE_FIELDS.forEach(field => {
        expectValue(parsedYaml, `safety.${field}`, false, errors, `safety ${field} not false`);
    });

    expectListIncludes(
        parsedYaml,
        'execution_blocking_reasons',
        EXPECTED_BLOCKING_REASONS,
        errors,
        'missing execution_blocking_reasons'
    );
    expectValue(
        parsedYaml,
        'next_step_after_phase_5_00f.continue_template_phases',
        false,
        errors,
        'continue_template_phases true'
    );
    expectValue(
        parsedYaml,
        'next_step_after_phase_5_00f.requires_user_real_input',
        true,
        errors,
        'requires_user_real_input false'
    );
    expectListIncludes(
        parsedYaml,
        'next_step_after_phase_5_00f.required_user_inputs',
        EXPECTED_REQUIRED_USER_INPUTS,
        errors,
        'missing next_step_after_phase_5_00f.required_user_inputs'
    );

    return errors;
}

function buildBasePayload(args, fields = {}) {
    return {
        phase: PHASE,
        ok: false,
        plan: args.plan || null,
        packet: args.packet || null,
        plan_found: false,
        packet_found: false,
        plan_yaml_block_found: false,
        packet_yaml_block_found: false,
        execution_plan_template_only: true,
        execution_plan_valid: false,
        authorization_packet_valid: false,
        execution_plan_ready: false,
        execution_plan_reviewed: false,
        execution_plan_accepted: false,
        execution_allowed: false,
        user_filled_packet_provided: false,
        network_dry_run_authorized: false,
        final_human_confirmation: false,
        target_source: null,
        target_count: null,
        max_targets: null,
        single_target_only: false,
        bulk_scope_allowed: false,
        stdout_only: false,
        external_network_allowed: false,
        browser_runtime_allowed: false,
        proxy_runtime_allowed: false,
        legacy_runtime_allowed: false,
        acquisition_engine_allowed: false,
        stdout_preview_allowed: false,
        staging_write_allowed: false,
        source_manifest_write_allowed: false,
        db_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        pre_execution_checks_complete: false,
        pre_execution_checks_passed: false,
        abort_conditions_active: true,
        continue_template_phases: false,
        requires_user_real_input: true,
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_execute_legacy_runtime: false,
        would_execute_engine: false,
        would_write_staging: false,
        would_create_staging_directory: false,
        would_write_source_manifest: false,
        would_write_packet_file: false,
        would_write_execution_plan_file: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        would_spawn_child_process: false,
        commit_gate: 'blocked',
        next_required_action: NEXT_REQUIRED_ACTION,
        errors: [],
        ...fields,
    };
}

function preExecutionChecksComplete(parsedYaml) {
    return PRE_EXECUTION_CHECKS.every(checkName => {
        const check = getPath(parsedYaml, `pre_execution_checks.${checkName}`);
        return check && check.required === true && check.checked === false && check.passed === false;
    });
}

function buildSuccessPayload(args, parsedYaml) {
    return buildBasePayload(args, {
        ok: true,
        plan_found: true,
        packet_found: true,
        plan_yaml_block_found: true,
        packet_yaml_block_found: true,
        execution_plan_valid: true,
        authorization_packet_valid: true,
        execution_plan_ready: parsedYaml.execution_plan_ready,
        execution_plan_reviewed: parsedYaml.execution_plan_reviewed,
        execution_plan_accepted: parsedYaml.execution_plan_accepted,
        execution_allowed: parsedYaml.execution_allowed,
        user_filled_packet_provided: parsedYaml.authorization_packet.user_filled_packet_provided,
        network_dry_run_authorized: parsedYaml.authorization_packet.network_dry_run_authorized,
        final_human_confirmation: parsedYaml.authorization_packet.final_human_confirmation,
        target_source: parsedYaml.target.target_source,
        target_count: parsedYaml.target.target_count,
        max_targets: parsedYaml.target.max_targets,
        single_target_only: parsedYaml.target.single_target_only,
        bulk_scope_allowed: parsedYaml.target.bulk_scope_allowed,
        stdout_only: parsedYaml.runtime_policy.stdout_only,
        external_network_allowed: parsedYaml.runtime_policy.external_network_allowed,
        browser_runtime_allowed: parsedYaml.runtime_policy.browser_runtime_allowed,
        proxy_runtime_allowed: parsedYaml.runtime_policy.proxy_runtime_allowed,
        legacy_runtime_allowed: parsedYaml.runtime_policy.legacy_runtime_allowed,
        acquisition_engine_allowed: parsedYaml.runtime_policy.acquisition_engine_allowed,
        stdout_preview_allowed: parsedYaml.output_policy.stdout_preview_allowed,
        staging_write_allowed: parsedYaml.output_policy.staging_write_allowed,
        source_manifest_write_allowed: parsedYaml.output_policy.source_manifest_write_allowed,
        db_write_allowed: parsedYaml.data_safety_policy.db_write_allowed,
        training_allowed: parsedYaml.data_safety_policy.training_allowed,
        prediction_allowed: parsedYaml.data_safety_policy.prediction_allowed,
        pre_execution_checks_complete: preExecutionChecksComplete(parsedYaml),
        pre_execution_checks_passed: false,
        abort_conditions_active: true,
        continue_template_phases: parsedYaml.next_step_after_phase_5_00f.continue_template_phases,
        requires_user_real_input: parsedYaml.next_step_after_phase_5_00f.requires_user_real_input,
        would_access_network: parsedYaml.safety.would_access_network,
        would_launch_browser: parsedYaml.safety.would_launch_browser,
        would_use_proxy: parsedYaml.safety.would_use_proxy,
        would_execute_legacy_runtime: parsedYaml.safety.would_execute_legacy_runtime,
        would_execute_engine: parsedYaml.safety.would_execute_engine,
        would_write_staging: parsedYaml.safety.would_write_staging,
        would_create_staging_directory: parsedYaml.safety.would_create_staging_directory,
        would_write_source_manifest: parsedYaml.safety.would_write_source_manifest,
        would_write_packet_file: parsedYaml.safety.would_write_packet_file,
        would_write_execution_plan_file: parsedYaml.safety.would_write_execution_plan_file,
        would_write_db: parsedYaml.safety.would_write_db,
        would_train: parsedYaml.safety.would_train,
        would_predict: parsedYaml.safety.would_predict,
        would_spawn_child_process: parsedYaml.safety.would_spawn_child_process,
    });
}

function loadPlanYaml(args, dependencies) {
    if (!args.plan) {
        return {
            payload: buildBasePayload(args, {
                mode: 'argument-error',
                errors: ['missing plan'],
            }),
        };
    }

    const planPath = resolveLocalPath(args.plan, dependencies.cwd);
    if (!dependencies.existsSync(planPath)) {
        return {
            payload: buildBasePayload(args, {
                mode: 'plan-error',
                plan: args.plan,
                plan_found: false,
                errors: [`missing plan: ${toRelativePath(planPath, dependencies.cwd)}`],
            }),
        };
    }

    const yamlText = extractYamlBlock(dependencies.readFileSync(planPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildBasePayload(args, {
                mode: 'plan-error',
                plan_found: true,
                plan_yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return {
            parsedYaml: parsePlanYaml(yamlText),
            yamlText,
        };
    } catch (error) {
        return {
            payload: buildBasePayload(args, {
                mode: 'plan-error',
                plan_found: true,
                plan_yaml_block_found: true,
                errors: [`invalid YAML: ${error.message}`],
            }),
        };
    }
}

function validateAuthorizationPacket(args, dependencies) {
    if (!args.packet) {
        return buildBasePayload(args, {
            mode: 'argument-error',
            errors: ['missing packet'],
        });
    }

    const packetPayload = authorizationPacketGate.runValidation({ packet: args.packet }, dependencies);
    if (!packetPayload.ok) {
        return buildBasePayload(args, {
            mode: 'packet-error',
            packet_found: packetPayload.packet_found,
            packet_yaml_block_found: packetPayload.yaml_block_found,
            errors: packetPayload.errors,
        });
    }

    return null;
}

function runValidation(args, dependencies = defaultDependencies()) {
    const loadedPlan = loadPlanYaml(args, dependencies);
    if (loadedPlan.payload) return loadedPlan.payload;

    const packetErrorPayload = validateAuthorizationPacket(args, dependencies);
    if (packetErrorPayload) return packetErrorPayload;

    const errors = validatePlanValues(loadedPlan.parsedYaml);
    if (errors.length) {
        return buildBasePayload(args, {
            mode: 'validation-error',
            plan_found: true,
            packet_found: true,
            plan_yaml_block_found: true,
            packet_yaml_block_found: true,
            errors,
        });
    }

    return buildSuccessPayload(args, loadedPlan.parsedYaml);
}

function main(argv = process.argv.slice(2), io = {}, dependencies = defaultDependencies()) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));

    let args;
    try {
        args = parseArgs(argv);
    } catch (error) {
        stderr(`${error.message}\n`);
        return 1;
    }

    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    if (args.commit) {
        stderr(`${BLOCKED_COMMIT_MESSAGE}\n`);
        return 1;
    }

    const payload = runValidation(args, dependencies);
    if (!payload.ok) {
        stderr(`${payload.errors.join('\n')}\n`);
        return 1;
    }

    stdout(`${JSON.stringify(payload, null, 2)}\n`);
    return 0;
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    PHASE,
    BLOCKED_COMMIT_MESSAGE,
    NEXT_REQUIRED_ACTION,
    EXPECTED_ABORT_CONDITIONS,
    EXPECTED_BLOCKING_REASONS,
    EXPECTED_STDOUT_FIELDS,
    EXPECTED_REQUIRED_USER_INPUTS,
    PRE_EXECUTION_CHECKS,
    REQUIRED_TOP_LEVEL_FIELDS,
    REQUIRED_NESTED_FIELDS,
    SAFETY_FALSE_FIELDS,
    CODEX_TRUE_FIELDS,
    parseArgs,
    usage,
    extractYamlBlock,
    parsePlanYaml,
    findMissingFields,
    validatePlanValues,
    buildBasePayload,
    buildSuccessPayload,
    loadPlanYaml,
    validateAuthorizationPacket,
    runValidation,
    main,
};
