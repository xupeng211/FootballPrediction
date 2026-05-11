#!/usr/bin/env node
/**
 * Phase 4.98F: FotMob trusted single-target adapter preflight hardening.
 *
 * This command is preflight-only. It does not access the network, launch browser
 * or proxy runtime, execute legacy FotMob runtime, write staging, write DB,
 * spawn child processes, train, or predict.
 */

'use strict';

const PHASE = 'PHASE4_98F_FOTMOB_ADAPTER_PREFLIGHT_HARDENING';
const DEFAULT_PARSER_CONFIDENCE_THRESHOLD = 0.8;
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: FotMob adapter preflight hardening is not executable in Phase 4.98F.';

const ALLOWED_SCOPE_TYPES = ['match_id', 'league_season_date'];
const BOOLEAN_FIELDS = [
    'terms_approval',
    'network_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'allow_db_write',
    'allow_training',
    'allow_prediction',
    'final_human_confirmation',
];

const TRUE_VALUES = new Set(['yes', 'true']);
const FALSE_VALUES = new Set(['no', 'false']);

const OPTIONAL_POLICY_FIELDS = [
    'source_homepage_url',
    'terms_url',
    'license_url',
    'allowed_use_summary',
    'rate_limit_policy',
    'retry_policy',
    'user_agent_policy',
    'output_root',
    'expected_response_kind',
    'parser_confidence_threshold',
];

function assignArgValue(args, key, value) {
    if (args[key] === undefined) {
        args[key] = value;
    } else if (Array.isArray(args[key])) {
        args[key].push(value);
    } else {
        args[key] = [args[key], value];
    }
}

function parseArgs(argv) {
    const args = {};
    const positional = [];

    for (let i = 0; i < argv.length; i++) {
        const current = argv[i];
        if (current === '--commit') {
            args.commit = true;
        } else if (current.startsWith('--')) {
            const eq = current.indexOf('=');
            if (eq !== -1) {
                assignArgValue(args, current.slice(2, eq).replace(/-/g, '_'), current.slice(eq + 1));
            } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
                assignArgValue(args, current.slice(2).replace(/-/g, '_'), argv[i + 1]);
                i++;
            } else {
                assignArgValue(args, current.slice(2).replace(/-/g, '_'), 'true');
            }
        } else {
            positional.push(current);
        }
    }

    if (positional.length > 0) {
        args.positional = positional;
    }

    return args;
}

function singleValue(params, field) {
    const value = params[field];
    if (Array.isArray(value)) {
        return value.length === 1 ? value[0] : value;
    }
    return value;
}

function normalizeBooleanFlag(value) {
    if (Array.isArray(value)) {
        return undefined;
    }
    if (value === undefined || value === null || value === '') {
        return undefined;
    }
    const normalized = String(value).trim().toLowerCase();
    if (TRUE_VALUES.has(normalized)) {
        return true;
    }
    if (FALSE_VALUES.has(normalized)) {
        return false;
    }
    return undefined;
}

function hasMultipleTargets(params) {
    const matchId = params.target_match_id;
    if (Array.isArray(matchId) && matchId.length !== 1) {
        return true;
    }
    if (typeof matchId === 'string' && matchId.includes(',')) {
        return true;
    }
    if (params.target_match_ids !== undefined || params.target_ids !== undefined || params.targets !== undefined) {
        return true;
    }
    return false;
}

function normalizeInput(params) {
    const normalized = {
        target_source: singleValue(params, 'target_source'),
        target_scope_type: singleValue(params, 'target_scope_type'),
        target_match_id: singleValue(params, 'target_match_id'),
        target_league: singleValue(params, 'target_league'),
        target_season: singleValue(params, 'target_season'),
        target_date: singleValue(params, 'target_date'),
        target_count: 1,
        bulk_scope_allowed: false,
        max_targets: 1,
        ignored_yes_flags: [],
    };

    for (const field of OPTIONAL_POLICY_FIELDS) {
        normalized[field] = singleValue(params, field);
    }

    normalized.expected_response_kind = normalized.expected_response_kind || 'unknown';
    normalized.parser_confidence_threshold =
        normalized.parser_confidence_threshold === undefined
            ? DEFAULT_PARSER_CONFIDENCE_THRESHOLD
            : Number(normalized.parser_confidence_threshold);

    return normalized;
}

function validateCommitFlag(params, errors) {
    if (params.commit) {
        errors.push(BLOCKED_COMMIT_MESSAGE);
    }
}

function validateSource(normalized, errors) {
    if (normalized.target_source !== 'fotmob') {
        errors.push('ERROR: --target-source must be "fotmob".');
    }
}

function validateScopeType(normalized, errors) {
    if (!normalized.target_scope_type) {
        errors.push('ERROR: --target-scope-type is required. Allowed: match_id, league_season_date.');
    } else if (!ALLOWED_SCOPE_TYPES.includes(normalized.target_scope_type)) {
        errors.push(
            `ERROR: unsupported --target-scope-type "${normalized.target_scope_type}". Allowed: match_id, league_season_date.`
        );
    }
}

function validateScopeFields(params, normalized, errors) {
    if (hasMultipleTargets(params)) {
        errors.push('ERROR: FotMob adapter scaffold is single-target only; provide exactly one target-match-id.');
    }

    if (normalized.target_scope_type === 'match_id' && !normalized.target_match_id) {
        errors.push('ERROR: --target-match-id is required when --target-scope-type=match_id.');
    }

    if (normalized.target_scope_type === 'league_season_date') {
        if (!normalized.target_league) {
            errors.push('ERROR: --target-league is required when --target-scope-type=league_season_date.');
        }
        if (!normalized.target_season) {
            errors.push('ERROR: --target-season is required when --target-scope-type=league_season_date.');
        }
        if (!normalized.target_date) {
            errors.push('ERROR: --target-date is required when --target-scope-type=league_season_date.');
        }
    }
}

function validateTargetLimits(params, errors) {
    const targetCount = singleValue(params, 'target_count');
    if (targetCount !== undefined) {
        const parsedCount = Number(targetCount);
        if (!Number.isFinite(parsedCount) || parsedCount !== 1) {
            errors.push('ERROR: --target-count must be 1.');
        }
    }

    const maxTargets = singleValue(params, 'max_targets');
    if (maxTargets !== undefined) {
        const parsedMax = Number(maxTargets);
        if (!Number.isFinite(parsedMax) || parsedMax !== 1) {
            errors.push('ERROR: --max-targets must be 1.');
        }
    }

    const bulkScopeAllowed = normalizeBooleanFlag(singleValue(params, 'bulk_scope_allowed'));
    if (params.bulk_scope_allowed !== undefined && bulkScopeAllowed === undefined) {
        errors.push('ERROR: --bulk-scope-allowed must be yes/no or true/false.');
    } else if (bulkScopeAllowed === true) {
        errors.push('ERROR: --bulk-scope-allowed must remain false.');
    }
}

function validateBooleanFields(params, normalized, errors) {
    for (const field of BOOLEAN_FIELDS) {
        const value = singleValue(params, field);
        const parsed = normalizeBooleanFlag(value);
        if (value === undefined || value === '') {
            errors.push(`ERROR: --${field.replace(/_/g, '-')} is required (no/false in Phase 4.98F).`);
        } else if (parsed === undefined) {
            errors.push(`ERROR: --${field.replace(/_/g, '-')} must be yes/no or true/false.`);
        } else if (parsed === true) {
            normalized.ignored_yes_flags.push(field);
        }
        normalized[field] = false;
    }
}

function validatePolicyFlags(normalized, errors) {
    if (
        !Number.isFinite(normalized.parser_confidence_threshold) ||
        normalized.parser_confidence_threshold < 0 ||
        normalized.parser_confidence_threshold > 1
    ) {
        errors.push('ERROR: --parser-confidence-threshold must be a number between 0 and 1.');
    }
}

function validateSingleTargetInput(params) {
    const errors = [];
    const normalized = normalizeInput(params);

    validateCommitFlag(params, errors);
    validateSource(normalized, errors);
    validateScopeType(normalized, errors);
    validateScopeFields(params, normalized, errors);
    validateTargetLimits(params, errors);
    validateBooleanFields(params, normalized, errors);
    validatePolicyFlags(normalized, errors);

    return {
        valid: errors.length === 0,
        errors,
        normalized,
    };
}

function hasProvided(value) {
    return value !== undefined && value !== null && String(value).trim() !== '';
}

function buildTargetIdentifier(input) {
    if (input.target_scope_type === 'match_id') {
        return input.target_match_id;
    }
    if (input.target_scope_type === 'league_season_date') {
        return [input.target_league, input.target_season, input.target_date].join('|');
    }
    return null;
}

function buildSourceManifestCandidatePreview(input) {
    return {
        source: 'fotmob',
        target_scope_type: input.target_scope_type,
        target_identifier: buildTargetIdentifier(input),
        source_homepage_url_provided: hasProvided(input.source_homepage_url),
        terms_url_provided: hasProvided(input.terms_url),
        license_url_provided: hasProvided(input.license_url),
        allowed_use_summary_provided: hasProvided(input.allowed_use_summary),
        network_authorization: false,
        created_for_preview_only: true,
        would_write_source_manifest: false,
    };
}

function buildParserConfidenceStub(input) {
    return {
        parser_ready: false,
        real_response_available: false,
        parser_confidence: 0,
        parser_confidence_threshold: input.parser_confidence_threshold,
        parser_confidence_passed: false,
        would_parse_real_response: false,
    };
}

function buildResponsePreviewSchemaStub(input) {
    return {
        expected_response_kind: input.expected_response_kind || 'unknown',
        schema_ready: false,
        schema_validation_passed: false,
        would_validate_real_response: false,
    };
}

function stopGate(gate, reason) {
    return {
        gate,
        blocked: true,
        reason,
    };
}

function buildStopGates(input) {
    return [
        stopGate('missing_terms_approval', 'terms approval is not granted in Phase 4.98F'),
        stopGate('missing_network_authorization', 'network authorization is not granted in Phase 4.98F'),
        stopGate('no_real_target_authorization', 'real target authorization must be reviewed in a later phase'),
        stopGate('source_terms_not_verified', 'source terms and allowed-use evidence are not verified'),
        stopGate('browser_runtime_not_authorized', 'browser runtime remains blocked by default'),
        stopGate('proxy_runtime_not_authorized', 'proxy runtime remains blocked by default'),
        stopGate('external_network_not_authorized', 'external network access remains blocked in Phase 4.98F'),
        stopGate('staging_write_not_authorized', 'staging writes remain blocked in Phase 4.98F'),
        stopGate('db_write_not_authorized', 'DB writes remain blocked in Phase 4.98F'),
        stopGate('parser_not_ready', 'parser confidence is stub-only and no real response is available'),
        stopGate('source_manifest_not_approved', 'source manifest candidate preview is not an approved manifest'),
        stopGate('network_execution_blocked', 'network dry-run execution is blocked in Phase 4.98F'),
        stopGate('future_phase_required', 'a later authorization phase is required before any execution'),
        stopGate(
            'allowed_use_summary_missing',
            hasProvided(input.allowed_use_summary)
                ? 'allowed-use summary is provided but not approved in Phase 4.98F'
                : 'allowed-use summary is missing'
        ),
    ];
}

function buildReadinessSummary() {
    return {
        adapter_scaffold_ready: true,
        preflight_hardened: true,
        source_manifest_candidate_preview_ready: true,
        parser_confidence_stub_ready: true,
        network_dry_run_ready: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
        next_required_phase:
            'Phase 4.99F FotMob stdout-only network dry-run authorization packet or explicit user-supplied real target authorization',
    };
}

function buildPreflightSummary(params) {
    const validation = validateSingleTargetInput(params);
    if (!validation.valid) {
        const error = new Error(validation.errors.join('\n'));
        error.errors = validation.errors;
        throw error;
    }

    const input = validation.normalized;
    return {
        phase: PHASE,
        adapter_scaffold_only: true,
        adapter_scaffold_ready: true,
        preflight_hardened: true,
        target_source: 'fotmob',
        target_scope_type: input.target_scope_type,
        target_match_id: input.target_scope_type === 'match_id' ? input.target_match_id : null,
        target_league: input.target_scope_type === 'league_season_date' ? input.target_league : null,
        target_season: input.target_scope_type === 'league_season_date' ? input.target_season : null,
        target_date: input.target_scope_type === 'league_season_date' ? input.target_date : null,
        target_count: 1,
        single_target: true,
        bulk_scope_allowed: false,
        max_targets: 1,
        policy_inputs: {
            source_homepage_url_provided: hasProvided(input.source_homepage_url),
            terms_url_provided: hasProvided(input.terms_url),
            license_url_provided: hasProvided(input.license_url),
            allowed_use_summary_provided: hasProvided(input.allowed_use_summary),
            rate_limit_policy: input.rate_limit_policy || null,
            retry_policy: input.retry_policy || null,
            user_agent_policy: input.user_agent_policy || null,
            output_root_provided: hasProvided(input.output_root),
            expected_response_kind: input.expected_response_kind,
            parser_confidence_threshold: input.parser_confidence_threshold,
        },
        terms_approval: false,
        network_authorization: false,
        browser_runtime_allowed: false,
        proxy_runtime_allowed: false,
        external_network_allowed: false,
        staging_write_allowed: false,
        db_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: false,
        trusted_adapter_ready: false,
        network_dry_run_ready: false,
        network_dry_run_authorized: false,
        network_dry_run_execution_allowed: false,
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
        source_manifest_candidate_preview: buildSourceManifestCandidatePreview(input),
        parser_confidence_stub: buildParserConfidenceStub(input),
        response_preview_schema_stub: buildResponsePreviewSchemaStub(input),
        stop_gates: buildStopGates(input),
        readiness_summary: buildReadinessSummary(),
        commit_gate: 'blocked',
        ignored_yes_flags: input.ignored_yes_flags,
        next_required_phase:
            'Phase 4.99F FotMob stdout-only network dry-run authorization packet or explicit user-supplied real target authorization',
    };
}

function createDisabledNetworkClient() {
    return {
        fetch() {
            throw new Error('Network access is disabled in Phase 4.98F.');
        },
    };
}

function createNoopParser() {
    return {
        parsePreview() {
            return {
                parser_stub_only: true,
                parsed_remote_response: false,
            };
        },
    };
}

function createNoopLogger() {
    return {
        debug() {},
        info() {},
        warn() {},
        error() {},
    };
}

function createFotMobSingleTargetAdapter(dependencies = {}) {
    const networkClient = dependencies.networkClient || createDisabledNetworkClient();
    const parser = dependencies.parser || createNoopParser();
    const clock = dependencies.clock || (() => new Date().toISOString());
    const logger = dependencies.logger || createNoopLogger();

    return {
        dependencies: {
            networkClient,
            parser,
            clock,
            logger,
        },
        validateInputs: validateSingleTargetInput,
        preflight(input) {
            logger.debug('FotMob adapter scaffold preflight only; no network, DB, staging, browser, or proxy.');
            return buildPreflightSummary(input);
        },
        dryRunFetchSingleTarget() {
            throw new Error('Network dry-run execution is disabled in Phase 4.98F.');
        },
        parsePreview(payload) {
            return parser.parsePreview(payload);
        },
        summarizeToStdout(input) {
            return `${JSON.stringify(this.preflight(input), null, 2)}\n`;
        },
    };
}

function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));
    const args = parseArgs(argv);

    if (args.commit) {
        stderr(`${BLOCKED_COMMIT_MESSAGE}\n`);
        return 1;
    }

    try {
        const adapter = createFotMobSingleTargetAdapter();
        stdout(adapter.summarizeToStdout(args));
        return 0;
    } catch (error) {
        stderr(`${error.message}\n`);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = runCli();
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validateSingleTargetInput,
    validatePolicyFlags,
    createFotMobSingleTargetAdapter,
    buildPreflightSummary,
    buildStopGates,
    buildSourceManifestCandidatePreview,
    buildParserConfidenceStub,
    buildResponsePreviewSchemaStub,
    buildReadinessSummary,
    runCli,
    PHASE,
    BLOCKED_COMMIT_MESSAGE,
    DEFAULT_PARSER_CONFIDENCE_THRESHOLD,
};
