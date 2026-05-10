#!/usr/bin/env node
/**
 * Phase 4.82D: Single-Target Acquisition Staging Packet Preview
 *
 * Aggregates Phase 4.79D (scaffold), 4.80D (schema validation), and
 * 4.81D (writer preflight) into a single packet preview. Read-only,
 * local-only, no network, no DB, no file writes.
 */

'use strict';

const fs = require('fs');
const { validateArtifact, validateManifest } = require('./single_target_acquisition_staging_schema_validator');
const {
    checkOutputRoot,
    checkTargetConsistency,
    buildPathPreviews,
    safeSlug,
    checkAuthorization: checkWriterAuth,
} = require('./single_target_acquisition_staging_writer_preflight');

// ---------------------------------------------------------------------------
// Constants (aligned with 4.79D/4.81D)
// ---------------------------------------------------------------------------

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
const YES_NO_FIELDS_479D = [
    'terms_approval',
    'network_dry_run_authorization',
    'allow_browser_runtime',
    'allow_proxy_runtime',
    'allow_external_network',
    'allow_staging_write',
    'confirm_single_target_scope',
];

// ---------------------------------------------------------------------------
// 4.79D Scaffold validation (inlined, no child process)
// ---------------------------------------------------------------------------

function checkEngine(params) {
    const e = [];
    if (!params.target_engine_family) e.push('target_engine_family is required');
    else if (FORBIDDEN_ENGINES.includes(params.target_engine_family)) {
        e.push(`engine family "${params.target_engine_family}" is forbidden`);
    } else if (!ALLOWED_ENGINE_FAMILIES.includes(params.target_engine_family)) {
        e.push(`unknown engine family "${params.target_engine_family}"`);
    }
    return e;
}

function checkScope(params) {
    const e = [];
    if (!params.target_scope_type) e.push('target_scope_type is required');
    else if (FORBIDDEN_SCOPE_TYPES.includes(params.target_scope_type)) {
        e.push(`scope type "${params.target_scope_type}" is forbidden`);
    } else if (!ALLOWED_SCOPE_TYPES.includes(params.target_scope_type)) {
        e.push(`unknown scope type "${params.target_scope_type}"`);
    }
    return e;
}

function checkScopeDeps(params) {
    const e = [];
    if (params.target_scope_type === 'match_id' && !params.target_match_id) {
        e.push('target_match_id is required when scope_type=match_id');
    }
    if (params.target_scope_type === 'league_season_date') {
        if (!params.target_league) e.push('target_league is required for league_season_date');
        if (!params.target_season) e.push('target_season is required for league_season_date');
        if (!params.target_date) e.push('target_date is required for league_season_date');
    }
    return e;
}

function validateScaffold(params) {
    const errors = [];
    if (!params.target_source) errors.push('target_source is required');
    errors.push(...checkEngine(params));
    errors.push(...checkScope(params));
    errors.push(...checkScopeDeps(params));
    for (const f of YES_NO_FIELDS_479D) {
        if (params[f] !== 'yes' && params[f] !== 'no') errors.push(`${f} is required (yes/no)`);
    }
    if (params.confirm_single_target_scope !== 'yes') {
        errors.push('confirm_single_target_scope must be yes');
    }
    return errors;
}

// ---------------------------------------------------------------------------
// Packet build
// ---------------------------------------------------------------------------

function baseOutput(args, overrides) {
    return Object.assign(
        {
            phase: 'PHASE4.82D_SINGLE_TARGET_ACQUISITION_STAGING_PACKET_PREVIEW',
            packet_preview_only: true,
            runtime_scaffold_passed: false,
            artifact_schema_valid: false,
            manifest_schema_valid: false,
            artifact_valid: false,
            manifest_valid: false,
            writer_preflight_passed: false,
            target_consistency_valid: false,
            output_root_allowed: false,
            packet_sections: [
                'runtime_scaffold',
                'schema_validation',
                'writer_preflight',
                'future_paths',
                'authorization_summary',
                'guardrails',
                'next_phase_requirements',
            ],
            staging_write_authorization: args.staging_write_authorization || 'no',
            final_human_confirmation: args.final_human_confirmation || 'no',
            staging_write_authorized: false,
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
            next_required_phase: 'Phase 4.83D or explicit user-authorized network dry-run runbook',
        },
        overrides
    );
}

function fail(args, overrides, errors) {
    for (const e of errors) console.error('ERROR:', e);
    console.log(JSON.stringify(baseOutput(args, overrides), null, 2));
    process.exit(1);
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(argv) {
    const args = {};
    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--commit') {
            args.commit = true;
        } else if (a.startsWith('--')) {
            const eq = a.indexOf('=');
            if (eq !== -1) {
                args[a.slice(2, eq).replace(/-/g, '_')] = a.slice(eq + 1);
            } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
                args[a.slice(2).replace(/-/g, '_')] = argv[i + 1];
                i++;
            }
        }
    }
    return args;
}

function ensureRequired(args, fields) {
    const errors = [];
    for (const f of fields) {
        if (!args[f]) errors.push(`--${f.replace(/_/g, '-')} is required`);
    }
    return errors;
}

function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.commit) {
        console.error(
            'BLOCKED: single-target acquisition staging packet commit/execution is not wired in Phase 4.82D.'
        );
        process.exit(1);
    }

    // Required fields
    const requiredFields = [
        'artifact_schema',
        'manifest_schema',
        'artifact',
        'manifest',
        'output_root',
        'target_source',
        'target_engine_family',
        'target_scope_type',
    ];
    const fieldErrors = ensureRequired(args, requiredFields);
    if (fieldErrors.length > 0) fail(args, {}, fieldErrors);

    // 4.79D scaffold validation
    const scaffoldErrors = validateScaffold(args);
    if (scaffoldErrors.length > 0) {
        fail(args, { runtime_scaffold_passed: false }, scaffoldErrors);
    }

    // 4.79D authorization
    const authErrors479d = [];
    for (const f of YES_NO_FIELDS_479D) {
        if (args[f] !== 'yes' && args[f] !== 'no') {
            authErrors479d.push(`${f} is required (yes/no)`);
        }
    }
    if (authErrors479d.length > 0) fail(args, { runtime_scaffold_passed: true }, authErrors479d);

    // 4.81D authorization
    const writerAuthErrors = checkWriterAuth(args);
    if (writerAuthErrors.length > 0) fail(args, { runtime_scaffold_passed: true }, writerAuthErrors);

    // Output root
    const rootErrors = checkOutputRoot(args.output_root);
    if (rootErrors.length > 0) fail(args, { runtime_scaffold_passed: true }, rootErrors);

    // 4.80D Schema validation
    const artifactResult = validateArtifact(args.artifact, args.artifact_schema);
    const manifestResult = validateManifest(args.manifest, args.manifest_schema);

    if (!artifactResult.valid || !manifestResult.valid) {
        fail(
            args,
            {
                runtime_scaffold_passed: true,
                artifact_schema_valid: artifactResult.valid,
                manifest_schema_valid: manifestResult.valid,
                artifact_valid: artifactResult.valid,
                manifest_valid: manifestResult.valid,
                output_root_allowed: true,
            },
            [...artifactResult.errors, ...manifestResult.errors]
        );
    }

    // Load data for consistency
    const artifactData = JSON.parse(fs.readFileSync(args.artifact, 'utf8'));
    const manifestData = JSON.parse(fs.readFileSync(args.manifest, 'utf8'));

    // Target consistency
    const consistencyErrors = checkTargetConsistency(args, artifactData, manifestData);
    if (consistencyErrors.length > 0) {
        fail(
            args,
            {
                runtime_scaffold_passed: true,
                artifact_schema_valid: true,
                manifest_schema_valid: true,
                artifact_valid: true,
                manifest_valid: true,
                output_root_allowed: true,
            },
            consistencyErrors
        );
    }

    // Path previews
    const previews = buildPathPreviews(args, artifactData);

    // Success
    console.log(
        JSON.stringify(
            baseOutput(args, {
                runtime_scaffold_passed: true,
                artifact_schema_valid: true,
                manifest_schema_valid: true,
                artifact_valid: true,
                manifest_valid: true,
                writer_preflight_passed: true,
                target_consistency_valid: true,
                output_root_allowed: true,
                future_staging_directory_preview: previews.dirPreview,
                future_artifact_file_preview: previews.artifactFile,
                future_manifest_file_preview: previews.manifestFile,
            }),
            null,
            2
        )
    );
}

if (require.main === module) main();

module.exports = { validateScaffold };
