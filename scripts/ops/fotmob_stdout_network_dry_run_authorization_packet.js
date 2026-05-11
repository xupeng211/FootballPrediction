#!/usr/bin/env node
/**
 * Phase 4.99F: FotMob stdout-only network dry-run authorization packet preview.
 *
 * This command reads a local packet template and prints a JSON summary to stdout.
 * It does not access the network, launch browser or proxy runtime, execute legacy
 * FotMob runtime, write files, connect to DB, spawn child processes, train, or predict.
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PHASE = 'PHASE4_99F_FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_AUTHORIZATION_PACKET';
const BLOCKED_COMMIT_MESSAGE =
    'BLOCKED: FotMob stdout-only network dry-run authorization packet is not executable in Phase 4.99F.';
const NEXT_REQUIRED_PHASE =
    'Phase 5.00F FotMob stdout-only network dry-run execution plan or explicit user-filled authorization packet review';

const EXPECTED_BLOCKING_REASONS = [
    'authorization_packet_template_only',
    'real_target_not_provided',
    'source_terms_not_approved',
    'allowed_use_not_approved',
    'external_network_not_authorized',
    'stdout_only_network_dry_run_not_authorized',
    'final_human_confirmation_missing',
    'future_execution_phase_required',
];

const REQUIRED_TOP_LEVEL_FIELDS = [
    'phase',
    'authorization_packet_status',
    'authorization_packet_ready',
    'authorization_packet_reviewed',
    'authorization_packet_accepted',
    'target',
    'source_terms',
    'network_policy',
    'output_policy',
    'data_safety_policy',
    'authorization_decision',
    'included_artifacts',
    'authorization_blocking_reasons',
    'codex_constraints',
    'safety',
    'next_phase_requirements',
];

const REQUIRED_NESTED_FIELDS = {
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
    source_terms: [
        'source_homepage_url',
        'terms_url',
        'license_url',
        'allowed_use_summary',
        'terms_reviewed_by',
        'terms_reviewed_at',
        'terms_approval',
        'allowed_use_approved',
    ],
    network_policy: [
        'external_network_authorized',
        'stdout_only_network_dry_run_authorized',
        'browser_runtime_authorized',
        'proxy_runtime_authorized',
        'login_required',
        'paywall_bypass_allowed',
        'anti_bot_bypass_allowed',
        'rate_limit_policy',
        'retry_policy',
        'user_agent_policy',
    ],
    output_policy: [
        'stdout_only',
        'staging_write_authorized',
        'source_manifest_write_authorized',
        'packet_write_authorized',
        'output_root',
        'bounded_preview_required',
    ],
    data_safety_policy: [
        'db_write_authorized',
        'training_authorized',
        'prediction_authorized',
        'model_artifact_loading_authorized',
        'no_db_write_confirmation',
        'no_training_confirmation',
        'no_prediction_confirmation',
    ],
    authorization_decision: [
        'network_dry_run_authorized',
        'network_dry_run_execution_allowed',
        'authorization_decision',
        'final_human_confirmation',
        'confirmed_by',
        'confirmed_at',
        'reviewer_notes',
    ],
    included_artifacts: [
        'adapter_scaffold',
        'preflight_hardening_report',
        'adapter_scaffold_report',
        'readiness_gap_report',
        'runbook_draft',
    ],
    codex_constraints: [
        'codex_may_not_self_fill_target',
        'codex_may_not_self_approve_terms',
        'codex_may_not_self_authorize_network',
        'codex_may_not_enable_execution',
        'codex_may_not_write_runtime_packet',
        'codex_may_not_execute_network_dry_run',
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
        'would_write_db',
        'would_train',
        'would_predict',
        'would_spawn_child_process',
    ],
};

const SAFETY_FALSE_FIELDS = REQUIRED_NESTED_FIELDS.safety;
const CODEX_TRUE_FIELDS = REQUIRED_NESTED_FIELDS.codex_constraints;

function parseArgs(argv = []) {
    const args = {
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
        '  node scripts/ops/fotmob_stdout_network_dry_run_authorization_packet.js --packet <path>',
        '  node scripts/ops/fotmob_stdout_network_dry_run_authorization_packet.js --packet <path> --commit',
        '',
        'Safety:',
        '  Phase 4.99F validates a local authorization packet template only.',
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
    const match = String(markdownText || '').match(/```yaml\s*\r?\n([\s\S]*?)```/i);
    return match ? match[1] : '';
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

function parsePacketYaml(yamlText) {
    const root = {};
    const stack = [{ indent: -1, value: root }];
    const lines = String(yamlText || '').split(/\r?\n/);

    lines.forEach((rawLine, lineIndex) => {
        if (!rawLine.trim() || rawLine.trim().startsWith('#')) return;
        if (/^\t+/.test(rawLine)) throw new Error(`unsupported YAML indentation: ${rawLine.trim()}`);

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
    return missingFields;
}

function expectValue(parsedYaml, dottedPath, expectedValue, errors, message) {
    if (getPath(parsedYaml, dottedPath) !== expectedValue) {
        errors.push(message || `${dottedPath} must be ${expectedValue}`);
    }
}

function validatePacketValues(parsedYaml) {
    const errors = [];
    const missingFields = findMissingFields(parsedYaml);
    if (missingFields.length) {
        errors.push(`missing required fields: ${missingFields.join(', ')}`);
    }

    expectValue(parsedYaml, 'phase', PHASE, errors, `phase must be ${PHASE}`);
    expectValue(
        parsedYaml,
        'authorization_packet_status',
        'template_only',
        errors,
        'authorization_packet_status not template_only'
    );
    expectValue(parsedYaml, 'authorization_packet_ready', false, errors, 'authorization_packet_ready true');
    expectValue(parsedYaml, 'authorization_packet_reviewed', false, errors, 'authorization_packet_reviewed true');
    expectValue(parsedYaml, 'authorization_packet_accepted', false, errors, 'authorization_packet_accepted true');

    expectValue(parsedYaml, 'target.target_source', 'fotmob', errors, 'target_source not fotmob');
    const targetCount = getPath(parsedYaml, 'target.target_count');
    if (targetCount > 1) errors.push('target_count > 1');
    if (targetCount !== 0) errors.push('target_count must remain 0 in Phase 4.99F template');
    const maxTargets = getPath(parsedYaml, 'target.max_targets');
    if (maxTargets > 1) errors.push('max_targets > 1');
    if (maxTargets !== 1) errors.push('max_targets must be 1');
    expectValue(parsedYaml, 'target.single_target_only', true, errors, 'single_target_only not true');
    expectValue(parsedYaml, 'target.bulk_scope_allowed', false, errors, 'bulk_scope_allowed true');

    expectValue(parsedYaml, 'source_terms.terms_approval', false, errors, 'terms_approval true');
    expectValue(parsedYaml, 'source_terms.allowed_use_approved', false, errors, 'allowed_use_approved true');

    expectValue(
        parsedYaml,
        'network_policy.external_network_authorized',
        false,
        errors,
        'external_network_authorized true'
    );
    expectValue(
        parsedYaml,
        'network_policy.stdout_only_network_dry_run_authorized',
        false,
        errors,
        'stdout_only_network_dry_run_authorized true'
    );
    expectValue(
        parsedYaml,
        'network_policy.browser_runtime_authorized',
        false,
        errors,
        'browser_runtime_authorized true'
    );
    expectValue(parsedYaml, 'network_policy.proxy_runtime_authorized', false, errors, 'proxy_runtime_authorized true');
    expectValue(parsedYaml, 'network_policy.login_required', false, errors, 'login_required true');
    expectValue(parsedYaml, 'network_policy.paywall_bypass_allowed', false, errors, 'paywall_bypass_allowed true');
    expectValue(parsedYaml, 'network_policy.anti_bot_bypass_allowed', false, errors, 'anti_bot_bypass_allowed true');

    expectValue(parsedYaml, 'output_policy.stdout_only', true, errors, 'stdout_only not true');
    expectValue(parsedYaml, 'output_policy.staging_write_authorized', false, errors, 'staging_write_authorized true');
    expectValue(
        parsedYaml,
        'output_policy.source_manifest_write_authorized',
        false,
        errors,
        'source_manifest_write_authorized true'
    );
    expectValue(parsedYaml, 'output_policy.packet_write_authorized', false, errors, 'packet_write_authorized true');
    expectValue(
        parsedYaml,
        'output_policy.bounded_preview_required',
        true,
        errors,
        'bounded_preview_required not true'
    );

    expectValue(parsedYaml, 'data_safety_policy.db_write_authorized', false, errors, 'db_write_authorized true');
    expectValue(parsedYaml, 'data_safety_policy.training_authorized', false, errors, 'training_authorized true');
    expectValue(parsedYaml, 'data_safety_policy.prediction_authorized', false, errors, 'prediction_authorized true');
    expectValue(
        parsedYaml,
        'data_safety_policy.model_artifact_loading_authorized',
        false,
        errors,
        'model_artifact_loading_authorized true'
    );

    expectValue(
        parsedYaml,
        'authorization_decision.network_dry_run_authorized',
        false,
        errors,
        'network_dry_run_authorized true'
    );
    expectValue(
        parsedYaml,
        'authorization_decision.network_dry_run_execution_allowed',
        false,
        errors,
        'network_dry_run_execution_allowed true'
    );
    expectValue(
        parsedYaml,
        'authorization_decision.authorization_decision',
        'not_authorized',
        errors,
        'authorization_decision not not_authorized'
    );
    expectValue(
        parsedYaml,
        'authorization_decision.final_human_confirmation',
        false,
        errors,
        'final_human_confirmation true'
    );

    const blockingReasons = parsedYaml.authorization_blocking_reasons;
    if (!Array.isArray(blockingReasons)) {
        errors.push('authorization_blocking_reasons missing or not list');
    } else {
        const missingReasons = EXPECTED_BLOCKING_REASONS.filter(reason => !blockingReasons.includes(reason));
        if (missingReasons.length) {
            errors.push(`missing authorization_blocking_reasons: ${missingReasons.join(', ')}`);
        }
    }

    CODEX_TRUE_FIELDS.forEach(field => {
        expectValue(parsedYaml, `codex_constraints.${field}`, true, errors, `${field} false`);
    });

    SAFETY_FALSE_FIELDS.forEach(field => {
        expectValue(parsedYaml, `safety.${field}`, false, errors, `safety ${field} not false`);
    });

    return errors;
}

function buildBasePayload(args, fields = {}) {
    return {
        phase: PHASE,
        ok: false,
        packet: args.packet || null,
        packet_found: false,
        yaml_block_found: false,
        authorization_packet_template_only: true,
        authorization_packet_valid: false,
        authorization_packet_ready: false,
        authorization_packet_reviewed: false,
        authorization_packet_accepted: false,
        target_source: null,
        target_count: null,
        max_targets: null,
        single_target_only: false,
        bulk_scope_allowed: false,
        terms_approval: false,
        allowed_use_approved: false,
        external_network_authorized: false,
        stdout_only_network_dry_run_authorized: false,
        browser_runtime_authorized: false,
        proxy_runtime_authorized: false,
        staging_write_authorized: false,
        source_manifest_write_authorized: false,
        db_write_authorized: false,
        training_authorized: false,
        prediction_authorized: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        authorization_decision: 'not_authorized',
        final_human_confirmation: false,
        authorization_blocking_reasons: [],
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_execute_legacy_runtime: false,
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
        errors: [],
        ...fields,
    };
}

function buildSuccessPayload(args, parsedYaml) {
    return buildBasePayload(args, {
        ok: true,
        packet_found: true,
        yaml_block_found: true,
        authorization_packet_valid: true,
        authorization_packet_ready: parsedYaml.authorization_packet_ready,
        authorization_packet_reviewed: parsedYaml.authorization_packet_reviewed,
        authorization_packet_accepted: parsedYaml.authorization_packet_accepted,
        target_source: parsedYaml.target.target_source,
        target_count: parsedYaml.target.target_count,
        max_targets: parsedYaml.target.max_targets,
        single_target_only: parsedYaml.target.single_target_only,
        bulk_scope_allowed: parsedYaml.target.bulk_scope_allowed,
        terms_approval: parsedYaml.source_terms.terms_approval,
        allowed_use_approved: parsedYaml.source_terms.allowed_use_approved,
        external_network_authorized: parsedYaml.network_policy.external_network_authorized,
        stdout_only_network_dry_run_authorized: parsedYaml.network_policy.stdout_only_network_dry_run_authorized,
        browser_runtime_authorized: parsedYaml.network_policy.browser_runtime_authorized,
        proxy_runtime_authorized: parsedYaml.network_policy.proxy_runtime_authorized,
        staging_write_authorized: parsedYaml.output_policy.staging_write_authorized,
        source_manifest_write_authorized: parsedYaml.output_policy.source_manifest_write_authorized,
        db_write_authorized: parsedYaml.data_safety_policy.db_write_authorized,
        training_authorized: parsedYaml.data_safety_policy.training_authorized,
        prediction_authorized: parsedYaml.data_safety_policy.prediction_authorized,
        network_dry_run_authorized: parsedYaml.authorization_decision.network_dry_run_authorized,
        network_dry_run_execution_allowed: parsedYaml.authorization_decision.network_dry_run_execution_allowed,
        authorization_decision: parsedYaml.authorization_decision.authorization_decision,
        final_human_confirmation: parsedYaml.authorization_decision.final_human_confirmation,
        authorization_blocking_reasons: parsedYaml.authorization_blocking_reasons,
        would_access_network: parsedYaml.safety.would_access_network,
        would_launch_browser: parsedYaml.safety.would_launch_browser,
        would_use_proxy: parsedYaml.safety.would_use_proxy,
        would_execute_legacy_runtime: parsedYaml.safety.would_execute_legacy_runtime,
        would_execute_engine: parsedYaml.safety.would_execute_engine,
        would_write_staging: parsedYaml.safety.would_write_staging,
        would_create_staging_directory: parsedYaml.safety.would_create_staging_directory,
        would_write_source_manifest: parsedYaml.safety.would_write_source_manifest,
        would_write_packet_file: parsedYaml.safety.would_write_packet_file,
        would_write_db: parsedYaml.safety.would_write_db,
        would_train: parsedYaml.safety.would_train,
        would_predict: parsedYaml.safety.would_predict,
        would_spawn_child_process: parsedYaml.safety.would_spawn_child_process,
    });
}

function loadPacketYaml(args, dependencies) {
    if (!args.packet) {
        return {
            payload: buildBasePayload(args, {
                mode: 'argument-error',
                errors: ['missing packet'],
            }),
        };
    }

    const packetPath = resolveLocalPath(args.packet, dependencies.cwd);
    if (!dependencies.existsSync(packetPath)) {
        return {
            payload: buildBasePayload(args, {
                mode: 'packet-error',
                packet: args.packet,
                packet_found: false,
                errors: [`missing packet: ${toRelativePath(packetPath, dependencies.cwd)}`],
            }),
        };
    }

    const yamlText = extractYamlBlock(dependencies.readFileSync(packetPath, 'utf8'));
    if (!yamlText) {
        return {
            payload: buildBasePayload(args, {
                mode: 'packet-error',
                packet_found: true,
                yaml_block_found: false,
                errors: ['missing YAML block'],
            }),
        };
    }

    try {
        return {
            parsedYaml: parsePacketYaml(yamlText),
            yamlText,
        };
    } catch (error) {
        return {
            payload: buildBasePayload(args, {
                mode: 'packet-error',
                packet_found: true,
                yaml_block_found: true,
                errors: [`invalid YAML: ${error.message}`],
            }),
        };
    }
}

function runValidation(args, dependencies = defaultDependencies()) {
    const loaded = loadPacketYaml(args, dependencies);
    if (loaded.payload) return loaded.payload;

    const errors = validatePacketValues(loaded.parsedYaml);
    if (errors.length) {
        return buildBasePayload(args, {
            mode: 'validation-error',
            packet_found: true,
            yaml_block_found: true,
            errors,
        });
    }

    return buildSuccessPayload(args, loaded.parsedYaml);
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
    NEXT_REQUIRED_PHASE,
    EXPECTED_BLOCKING_REASONS,
    REQUIRED_TOP_LEVEL_FIELDS,
    REQUIRED_NESTED_FIELDS,
    SAFETY_FALSE_FIELDS,
    CODEX_TRUE_FIELDS,
    parseArgs,
    usage,
    extractYamlBlock,
    parseScalar,
    parsePacketYaml,
    findMissingFields,
    validatePacketValues,
    buildBasePayload,
    buildSuccessPayload,
    loadPacketYaml,
    runValidation,
    main,
};
