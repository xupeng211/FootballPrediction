#!/usr/bin/env node
/**
 * Phase 4.81D: Single-Target Acquisition Staging Writer Preflight
 *
 * Preflight-only command. Validates artifact/manifest schemas, checks target
 * consistency, validates output root policy, and previews future staging paths.
 * Does NOT create directories, write files, access network, or write DB.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { validateArtifact, validateManifest } = require('./single_target_acquisition_staging_schema_validator');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALLOWED_OUTPUT_ROOT = 'docs/_staging_preview/acquisition/single_target';

const FORBIDDEN_OUTPUT_ROOTS = ['docs/_packets', 'data/', '.'];

const ALLOWED_ENGINE_FAMILIES = ['titan_discovery'];

const ALLOWED_SCOPE_TYPES = ['match_id', 'league_season_date'];

const FORBIDDEN_SCOPE_TYPES = ['all', 'bulk', 'production', 'league', 'season', 'full_source'];

// ---------------------------------------------------------------------------
// Output root policy validation
// ---------------------------------------------------------------------------

function checkOutputRoot(outputRoot) {
    const errors = [];

    if (!outputRoot) {
        errors.push('output_root is required');
        return errors;
    }

    // must not be absolute
    if (path.isAbsolute(outputRoot)) {
        errors.push('output_root must not be an absolute path');
    }

    // must not contain ..
    if (outputRoot.includes('..')) {
        errors.push('output_root must not contain ".."');
    }

    // must not be a forbidden root
    const normalized = outputRoot.replace(/\/+$/, '');
    for (const forbidden of FORBIDDEN_OUTPUT_ROOTS) {
        if (normalized === forbidden.replace(/\/+$/, '') || normalized.startsWith(forbidden)) {
            errors.push(`output_root "${outputRoot}" is not allowed (forbidden prefix: ${forbidden})`);
        }
    }

    // must start with allowed root
    const allowedNorm = ALLOWED_OUTPUT_ROOT.replace(/\/+$/, '');
    if (!normalized.startsWith(allowedNorm)) {
        errors.push(`output_root must be under "${ALLOWED_OUTPUT_ROOT}", got "${outputRoot}"`);
    }

    return errors;
}

// ---------------------------------------------------------------------------
// Safe slug for filenames (no slashes, no spaces, no ..)
// ---------------------------------------------------------------------------

function safeSlug(text) {
    return (text || 'unknown')
        .replace(/\.\./g, '__')
        .replace(/[^a-zA-Z0-9._-]/g, '_')
        .replace(/_{2,}/g, '_')
        .replace(/^_|_$/g, '')
        .slice(0, 64);
}

// ---------------------------------------------------------------------------
// sha256 hash8 extraction
// ---------------------------------------------------------------------------

function extractHash8(artifactData) {
    const sha = artifactData && artifactData.capture && artifactData.capture.raw_payload_sha256;
    if (sha && typeof sha === 'string' && sha.length >= 8 && /^[0-9a-fA-F]+$/.test(sha)) {
        return sha.slice(0, 8);
    }
    return '00000000'; // safe fallback
}

// ---------------------------------------------------------------------------
// Target consistency helpers
// ---------------------------------------------------------------------------

function checkSourceMatch(args, artSource, manSource) {
    const errors = [];
    if (args.target_source && artSource && args.target_source !== artSource) {
        errors.push(`target_source "${args.target_source}" does not match artifact source "${artSource}"`);
    }
    if (args.target_source && manSource && args.target_source !== manSource) {
        errors.push(`target_source "${args.target_source}" does not match manifest source "${manSource}"`);
    }
    return errors;
}

function checkEngineMatch(args, artEngine, manEngine) {
    const errors = [];
    if (args.target_engine_family && artEngine && args.target_engine_family !== artEngine) {
        errors.push(
            `target_engine_family "${args.target_engine_family}" does not match artifact engine "${artEngine}"`
        );
    }
    if (args.target_engine_family && manEngine && args.target_engine_family !== manEngine) {
        errors.push(
            `target_engine_family "${args.target_engine_family}" does not match manifest engine "${manEngine}"`
        );
    }
    if (args.target_engine_family && !ALLOWED_ENGINE_FAMILIES.includes(args.target_engine_family)) {
        errors.push(`target_engine_family "${args.target_engine_family}" is not allowed`);
    }
    return errors;
}

function checkScopeMatch(args, artScope, manScope) {
    const errors = [];
    if (args.target_scope_type && artScope && args.target_scope_type !== artScope) {
        errors.push(`target_scope_type "${args.target_scope_type}" does not match artifact scope "${artScope}"`);
    }
    if (args.target_scope_type && manScope && args.target_scope_type !== manScope) {
        errors.push(`target_scope_type "${args.target_scope_type}" does not match manifest scope "${manScope}"`);
    }
    if (args.target_scope_type && FORBIDDEN_SCOPE_TYPES.includes(args.target_scope_type)) {
        errors.push(`target_scope_type "${args.target_scope_type}" is forbidden`);
    }
    return errors;
}

function checkMatchIdDeps(args, artifactData, manifestData) {
    const errors = [];
    if (!args.target_match_id) {
        errors.push('target_match_id is required when target_scope_type=match_id');
    }
    const artId = artifactData && artifactData.target_scope && artifactData.target_scope.match_id;
    const manId = manifestData && manifestData.target_scope && manifestData.target_scope.match_id;
    if (args.target_match_id && artId && args.target_match_id !== artId) {
        errors.push(`target_match_id "${args.target_match_id}" does not match artifact match_id "${artId}"`);
    }
    if (args.target_match_id && manId && args.target_match_id !== manId) {
        errors.push(`target_match_id "${args.target_match_id}" does not match manifest match_id "${manId}"`);
    }
    return errors;
}

function checkLeagueSeasonDateDeps(args) {
    const errors = [];
    if (!args.target_league) errors.push('target_league is required for league_season_date');
    if (!args.target_season) errors.push('target_season is required for league_season_date');
    if (!args.target_date) errors.push('target_date is required for league_season_date');
    return errors;
}

function checkScopeDepsMatch(args, artifactData, manifestData) {
    if (args.target_scope_type === 'match_id') {
        return checkMatchIdDeps(args, artifactData, manifestData);
    }
    if (args.target_scope_type === 'league_season_date') {
        return checkLeagueSeasonDateDeps(args);
    }
    return [];
}

// ---------------------------------------------------------------------------
// Target consistency validation (orchestrates helpers)
// ---------------------------------------------------------------------------

function checkTargetConsistency(args, artifactData, manifestData) {
    const artSource = artifactData && artifactData.source && artifactData.source.name;
    const manSource = manifestData && manifestData.source_name;
    const artEngine = artifactData && artifactData.engine && artifactData.engine.family;
    const manEngine = manifestData && manifestData.engine_family;
    const artScope = artifactData && artifactData.target_scope && artifactData.target_scope.scope_type;
    const manScope = manifestData && manifestData.target_scope && manifestData.target_scope.scope_type;

    return [
        ...checkSourceMatch(args, artSource, manSource),
        ...checkEngineMatch(args, artEngine, manEngine),
        ...checkScopeMatch(args, artScope, manScope),
        ...checkScopeDepsMatch(args, artifactData, manifestData),
    ];
}

// ---------------------------------------------------------------------------
// Path preview
// ---------------------------------------------------------------------------

function buildPathPreviews(args, artifactData) {
    const source = safeSlug(args.target_source || 'unknown');
    const engine = safeSlug(args.target_engine_family || 'unknown');
    const scopeType = safeSlug(args.target_scope_type || 'unknown');
    const scopeValue =
        args.target_scope_type === 'match_id'
            ? safeSlug(args.target_match_id || 'unknown')
            : safeSlug(args.target_league || args.target_date || 'unknown');
    const hash8 = extractHash8(artifactData);
    const safeTargetSlug = `${scopeType}_${scopeValue}`.slice(0, 128);

    const dirPreview = `${args.output_root || ALLOWED_OUTPUT_ROOT}/${source}/${engine}/${scopeType}/${safeTargetSlug}`;
    const artifactFile = `single_target_staging_artifact_${source}_${safeTargetSlug}_${hash8}.json`;
    const manifestFile = `source_manifest_candidate_${source}_${safeTargetSlug}_${hash8}.json`;

    return { dirPreview, artifactFile, manifestFile };
}

// ---------------------------------------------------------------------------
// Validate authorization fields
// ---------------------------------------------------------------------------

function checkAuthorization(args) {
    const errors = [];
    const yesNo = ['staging_write_authorization', 'final_human_confirmation'];
    for (const field of yesNo) {
        const val = args[field];
        if (val === undefined || val === '') {
            errors.push(`${field} is required (yes or no)`);
        } else if (val !== 'yes' && val !== 'no') {
            errors.push(`${field} must be "yes" or "no", got "${val}"`);
        }
    }
    return errors;
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
        if (!args[f]) {
            const cliName = '--' + f.replace(/_/g, '-');
            errors.push(`${cliName} is required`);
        }
    }
    return errors;
}

function baseOutput(args, overrides) {
    return Object.assign(
        {
            phase: 'PHASE4.81D_SINGLE_TARGET_ACQUISITION_STAGING_WRITER_PREFLIGHT',
            preflight_only: true,
            artifact_schema_valid: false,
            manifest_schema_valid: false,
            artifact_valid: false,
            manifest_valid: false,
            output_root_allowed: false,
            target_consistency_valid: false,
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
            would_write_db: false,
            would_train: false,
            would_predict: false,
            would_spawn_child_process: false,
            commit_gate: 'blocked',
        },
        overrides
    );
}

function exitWithOutput(args, output, errors) {
    for (const e of errors) {
        console.error('ERROR:', e);
    }
    console.log(JSON.stringify(baseOutput(args, output), null, 2));
    process.exit(1);
}

function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.commit) {
        console.error(
            'BLOCKED: single-target acquisition staging writer commit/execution is not wired in Phase 4.81D.'
        );
        process.exit(1);
    }

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
    const authErrors = checkAuthorization(args);
    const allPreErrors = [...fieldErrors, ...authErrors];
    if (allPreErrors.length > 0) {
        for (const e of allPreErrors) {
            console.error('ERROR:', e);
        }
        process.exit(1);
    }

    const rootErrors = checkOutputRoot(args.output_root);
    if (rootErrors.length > 0) exitWithOutput(args, {}, rootErrors);

    const artifactResult = validateArtifact(args.artifact, args.artifact_schema);
    const manifestResult = validateManifest(args.manifest, args.manifest_schema);

    if (!artifactResult.valid || !manifestResult.valid) {
        exitWithOutput(
            args,
            {
                artifact_schema_valid: artifactResult.valid,
                manifest_schema_valid: manifestResult.valid,
                artifact_valid: artifactResult.valid,
                manifest_valid: manifestResult.valid,
                output_root_allowed: true,
            },
            [...artifactResult.errors, ...manifestResult.errors]
        );
    }

    const artifactData = JSON.parse(fs.readFileSync(args.artifact, 'utf8'));
    const manifestData = JSON.parse(fs.readFileSync(args.manifest, 'utf8'));

    const consistencyErrors = checkTargetConsistency(args, artifactData, manifestData);
    if (consistencyErrors.length > 0) {
        exitWithOutput(
            args,
            {
                artifact_schema_valid: true,
                manifest_schema_valid: true,
                artifact_valid: true,
                manifest_valid: true,
                output_root_allowed: true,
            },
            consistencyErrors
        );
    }

    const previews = buildPathPreviews(args, artifactData);
    console.log(
        JSON.stringify(
            baseOutput(args, {
                artifact_schema_valid: true,
                manifest_schema_valid: true,
                artifact_valid: true,
                manifest_valid: true,
                output_root_allowed: true,
                target_consistency_valid: true,
                future_staging_directory_preview: previews.dirPreview,
                future_artifact_file_preview: previews.artifactFile,
                future_manifest_file_preview: previews.manifestFile,
            }),
            null,
            2
        )
    );
}

if (require.main === module) {
    main();
}

module.exports = {
    checkOutputRoot,
    checkTargetConsistency,
    checkSourceMatch,
    checkEngineMatch,
    checkScopeMatch,
    checkScopeDepsMatch,
    buildPathPreviews,
    safeSlug,
    extractHash8,
    checkAuthorization,
};
