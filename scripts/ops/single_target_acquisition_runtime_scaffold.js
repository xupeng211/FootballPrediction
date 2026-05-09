#!/usr/bin/env node
/**
 * Phase 4.79D: Single-Target Acquisition Runtime Scaffold
 *
 * Scaffold-only command. Validates parameters and outputs a runtime plan preview.
 * Does NOT access network, launch browser, use proxy, write DB, write staging,
 * execute any acquisition engine, or spawn child processes.
 */

'use strict';

const ALLOWED_ENGINE_FAMILIES = ['titan_discovery'];

const FORBIDDEN_ENGINES = [
    'run_production',
    'recon_scanner',
    'odds_harvest_pipeline',
    'total_war_pipeline',
    'titan_marathon',
    'batch_historical_backfill',
    'fetch_and_adapt_euro_leagues',
];

const ALLOWED_SCOPE_TYPES = ['match_id', 'league_season_date'];

const FORBIDDEN_SCOPE_TYPES = ['all', 'bulk', 'production', 'league', 'season', 'full_source'];

const YES_NO_FIELDS = [
    'terms_approval',
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'confirm_single_target_scope',
];

/**
 * Parse CLI arguments into a key/value map.
 * Recognizes --key=value and --key value forms.
 * --commit is captured as a boolean flag.
 */
function parseArgs(argv) {
    const args = {};
    const positional = [];

    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--commit') {
            args.commit = true;
        } else if (a.startsWith('--')) {
            const eq = a.indexOf('=');
            if (eq !== -1) {
                const key = a.slice(2, eq);
                const val = a.slice(eq + 1);
                args[key.replace(/-/g, '_')] = val;
            } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
                args[a.slice(2).replace(/-/g, '_')] = argv[i + 1];
                i++;
            } else {
                args[a.slice(2).replace(/-/g, '_')] = 'true';
            }
        } else {
            positional.push(a);
        }
    }

    return { args, positional };
}

function validateCommit(params, errors) {
    if (params.commit) {
        errors.push('BLOCKED: single-target acquisition runtime commit/execution is not wired in Phase 4.79D.');
    }
}

function validateRequired(params, errors) {
    if (!params.target_source) {
        errors.push('ERROR: --target-source is required (e.g. fotmob).');
    }
    if (!params.target_engine_family) {
        errors.push('ERROR: --target-engine-family is required. Allowed: titan_discovery.');
    }
    if (!params.target_scope_type) {
        errors.push('ERROR: --target-scope-type is required. Allowed: match_id, league_season_date.');
    }
}

function validateEngineFamily(params, errors) {
    const f = params.target_engine_family;
    if (!f) return;
    if (FORBIDDEN_ENGINES.includes(f)) {
        errors.push(`BLOCKED: engine family "${f}" is a forbidden legacy runtime. Allowed: titan_discovery.`);
    }
    if (!ALLOWED_ENGINE_FAMILIES.includes(f)) {
        errors.push(`ERROR: unknown engine family "${f}". Allowed: titan_discovery.`);
    }
}

function validateScopeType(params, errors) {
    const s = params.target_scope_type;
    if (!s) return;
    if (FORBIDDEN_SCOPE_TYPES.includes(s)) {
        errors.push(`BLOCKED: scope type "${s}" is forbidden. Allowed: match_id, league_season_date.`);
    }
    if (!ALLOWED_SCOPE_TYPES.includes(s)) {
        errors.push(`ERROR: unknown scope type "${s}". Allowed: match_id, league_season_date.`);
    }
}

function validateScopeDependent(params, errors) {
    if (params.target_scope_type === 'match_id' && !params.target_match_id) {
        errors.push('ERROR: --target-match-id is required when target_scope_type=match_id.');
    }
    if (params.target_scope_type === 'league_season_date') {
        if (!params.target_league) {
            errors.push('ERROR: --target-league is required when target_scope_type=league_season_date.');
        }
        if (!params.target_season) {
            errors.push('ERROR: --target-season is required when target_scope_type=league_season_date.');
        }
        if (!params.target_date) {
            errors.push('ERROR: --target-date is required when target_scope_type=league_season_date.');
        }
    }
}

function validateYesNoFields(params, errors) {
    for (const field of YES_NO_FIELDS) {
        const val = params[field];
        if (val === undefined || val === '') {
            errors.push(`ERROR: --${field.replace(/_/g, '-')} is required (yes or no).`);
        } else if (val !== 'yes' && val !== 'no') {
            errors.push(`ERROR: --${field.replace(/_/g, '-')} must be "yes" or "no", got "${val}".`);
        }
    }
}

function validateConfirmScope(params, errors) {
    if (
        params.confirm_single_target_scope === 'no' &&
        !errors.some(e => e.includes('confirm-single-target-scope must be'))
    ) {
        errors.push('ERROR: --confirm-single-target-scope must be "yes" for a valid scaffold plan.');
    }
}

/**
 * Collect all validation errors. Returns an array of error message strings.
 */
function validate(params) {
    const errors = [];
    validateCommit(params, errors);
    validateRequired(params, errors);
    validateEngineFamily(params, errors);
    validateScopeType(params, errors);
    validateScopeDependent(params, errors);
    validateYesNoFields(params, errors);
    validateConfirmScope(params, errors);
    return errors;
}

/**
 * Build the scaffold output JSON.
 */
function buildOutput(params) {
    return {
        phase: 'PHASE4.79D_SINGLE_TARGET_ACQUISITION_RUNTIME_SCAFFOLD',
        scaffold_only: true,
        runtime_plan_created: true,
        target_source: params.target_source || null,
        target_engine_family: params.target_engine_family || null,
        target_scope_type: params.target_scope_type || null,
        single_target_scope_confirmed: params.confirm_single_target_scope === 'yes',
        legacy_runtime_blocked: true,
        would_execute_legacy_titan_discovery: false,
        would_execute_engine: false,
        would_access_network: false,
        would_launch_browser: false,
        would_use_proxy: false,
        would_write_staging: false,
        would_create_staging_directory: false,
        would_write_source_manifest: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        would_bulk_harvest: false,
        would_spawn_child_process: false,
        commit_gate: 'blocked',
        next_required_phase: 'Phase 4.80D or explicit user-authorized network dry-run runbook',
        guardrails: [
            'no_external_network',
            'no_browser_automation',
            'no_proxy_runtime_execution',
            'no_db_writes',
            'no_staging_writes',
            'no_legacy_runtime',
            'no_training',
            'no_prediction',
        ],
    };
}

/**
 * Main entry point.
 */
function main() {
    const { args } = parseArgs(process.argv.slice(2));

    const errors = validate(args);
    if (errors.length > 0) {
        for (const e of errors) {
            console.error(e);
        }
        process.exit(1);
    }

    const output = buildOutput(args);
    console.log(JSON.stringify(output, null, 2));
}

// Only run when executed directly, not when required for testing.
if (require.main === module) {
    main();
}

// Export for unit test parity checks (no side effects).
module.exports = {
    parseArgs,
    validate,
    buildOutput,
    ALLOWED_ENGINE_FAMILIES,
    FORBIDDEN_ENGINES,
    ALLOWED_SCOPE_TYPES,
    FORBIDDEN_SCOPE_TYPES,
};
