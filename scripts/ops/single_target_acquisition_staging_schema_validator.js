#!/usr/bin/env node
/**
 * Phase 4.80D: Single-Target Acquisition Staging Schema Validator
 *
 * Validates sample staging artifacts and source manifest candidates against
 * their respective JSON schemas. Read-only, local-only, no network, no DB,
 * no file writes, no child processes.
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Minimal JSON Schema validator helpers
// ---------------------------------------------------------------------------

function checkType(instance, schema, p) {
    const errors = [];
    if (!schema.type) return errors;

    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const instanceType = Array.isArray(instance) ? 'array' : typeof instance;
    const ok = types.some(t => {
        if (t === 'integer') return Number.isInteger(instance);
        if (t === 'null') return instance === null;
        return instanceType === t;
    });
    if (!ok) {
        errors.push(`${p}: expected type ${types.join('|')}, got ${instance === null ? 'null' : instanceType}`);
    }
    return errors;
}

function checkEnumConst(instance, schema, p) {
    const errors = [];
    if (schema.enum && !schema.enum.includes(instance)) {
        errors.push(`${p}: value "${instance}" not in enum [${schema.enum.join(', ')}]`);
    }
    if (schema.const !== undefined && instance !== schema.const) {
        errors.push(`${p}: must be ${JSON.stringify(schema.const)}, got ${JSON.stringify(instance)}`);
    }
    return errors;
}

function checkFormat(instance, schema, p) {
    const errors = [];
    if (typeof instance !== 'string') return errors;

    if (schema.format === 'date-time' && isNaN(Date.parse(instance))) {
        errors.push(`${p}: invalid date-time format "${instance}"`);
    }
    if (schema.format === 'uri' && !instance.includes('://') && !instance.startsWith('/')) {
        errors.push(`${p}: invalid uri format "${instance}"`);
    }
    return errors;
}

function checkAdditionalProps(instance, schema, p) {
    const errors = [];
    if (schema.additionalProperties === false && schema.properties) {
        for (const key of Object.keys(instance)) {
            if (!(key in schema.properties)) {
                errors.push(`${p}.${key}: additional property not allowed`);
            }
        }
    }
    return errors;
}

function checkRequired(instance, schema, p) {
    const errors = [];
    if (schema.required) {
        for (const req of schema.required) {
            if (!(req in instance)) {
                errors.push(`${p}.${req}: required field missing`);
            }
        }
    }
    return errors;
}

function checkProperties(instance, schema, p) {
    const errors = [];
    if (schema.properties) {
        for (const [key, propSchema] of Object.entries(schema.properties)) {
            if (key in instance) {
                errors.push(...validateAgainstSchema(instance[key], propSchema, `${p}.${key}`));
            }
        }
    }
    return errors;
}

function checkAllOf(instance, schema, p) {
    const errors = [];
    if (schema.allOf) {
        for (const sub of schema.allOf) {
            if (sub.if && sub.then) {
                const ifErrors = validateAgainstSchema(instance, sub.if, `${p}(if)`);
                if (ifErrors.length === 0) {
                    errors.push(...validateAgainstSchema(instance, sub.then, `${p}(then)`));
                }
            }
        }
    }
    return errors;
}

// ---------------------------------------------------------------------------
// Main schema validator entry point
// ---------------------------------------------------------------------------

function validateAgainstSchema(instance, schema, basePath) {
    const p = basePath || '$';
    if (!schema || typeof schema !== 'object') return [];

    const errors = [];
    errors.push(...checkType(instance, schema, p));
    if (instance === null || instance === undefined) return errors;

    errors.push(...checkEnumConst(instance, schema, p));
    errors.push(...checkFormat(instance, schema, p));

    if (schema.type === 'object' && typeof instance === 'object' && !Array.isArray(instance)) {
        errors.push(...checkAdditionalProps(instance, schema, p));
        errors.push(...checkRequired(instance, schema, p));
        errors.push(...checkProperties(instance, schema, p));
        errors.push(...checkAllOf(instance, schema, p));
    }

    return errors;
}

// ---------------------------------------------------------------------------
// File read helpers
// ---------------------------------------------------------------------------

function readJsonFile(filePath) {
    try {
        const raw = fs.readFileSync(filePath, 'utf8');
        return { data: JSON.parse(raw), error: null };
    } catch (e) {
        return { data: null, error: e.message };
    }
}

// ---------------------------------------------------------------------------
// Artifact-specific extra checks
// ---------------------------------------------------------------------------

function checkArtifactSafety(data, errors) {
    if (!data.safety) return;
    if (data.safety.would_write_db !== false) errors.push('artifact safety.would_write_db must be false');
    if (data.safety.would_train !== false) errors.push('artifact safety.would_train must be false');
    if (data.safety.would_predict !== false) errors.push('artifact safety.would_predict must be false');
    if (data.safety.bulk_scope !== false) errors.push('artifact safety.bulk_scope must be false');
}

function checkArtifactScopeType(data, errors) {
    if (!data.target_scope) return;
    const ts = data.target_scope;
    if (ts.scope_type === 'match_id' && !ts.match_id) {
        errors.push('artifact target_scope: match_id required when scope_type=match_id');
    }
    if (ts.scope_type === 'league_season_date') {
        if (!ts.league) errors.push('artifact target_scope: league required for league_season_date');
        if (!ts.season) errors.push('artifact target_scope: season required for league_season_date');
        if (!ts.date) errors.push('artifact target_scope: date required for league_season_date');
    }
    const forbidden = ['all', 'bulk', 'production', 'league', 'season', 'full_source'];
    if (forbidden.includes(ts.scope_type)) {
        errors.push(`artifact target_scope.scope_type "${ts.scope_type}" is forbidden`);
    }
}

function checkArtifactEngine(data, errors) {
    if (data.engine && data.engine.family && data.engine.family !== 'titan_discovery') {
        errors.push(`artifact engine.family "${data.engine.family}" is not titan_discovery`);
    }
}

// ---------------------------------------------------------------------------
// High-level validation: single staging artifact
// ---------------------------------------------------------------------------

function validateArtifact(artifactPath, schemaPath) {
    const result = { valid: false, errors: [] };

    if (!schemaPath) {
        result.errors.push('artifact schema path is required');
        return result;
    }
    if (!artifactPath) {
        result.errors.push('artifact file path is required');
        return result;
    }

    const schemaResult = readJsonFile(schemaPath);
    if (schemaResult.error) {
        result.errors.push(`artifact schema: ${schemaResult.error}`);
        return result;
    }

    const dataResult = readJsonFile(artifactPath);
    if (dataResult.error) {
        result.errors.push(`artifact data: ${dataResult.error}`);
        return result;
    }

    const data = dataResult.data;
    result.errors.push(...validateAgainstSchema(data, schemaResult.data));
    checkArtifactSafety(data, result.errors);
    checkArtifactScopeType(data, result.errors);
    checkArtifactEngine(data, result.errors);
    result.valid = result.errors.length === 0;
    return result;
}

// ---------------------------------------------------------------------------
// Manifest-specific extra checks
// ---------------------------------------------------------------------------

function checkManifestStatus(data, errors) {
    if (data.manifest_status && data.manifest_status !== 'candidate_not_approved') {
        errors.push('manifest manifest_status must be "candidate_not_approved"');
    }
    if (data.approval_status && data.approval_status !== 'not_approved') {
        errors.push('manifest approval_status must be "not_approved"');
    }
}

function checkManifestEngine(data, errors) {
    if (data.engine_family && data.engine_family !== 'titan_discovery') {
        errors.push(`manifest engine_family "${data.engine_family}" is not titan_discovery`);
    }
}

function checkManifestSafety(data, errors) {
    if (!data.safety) return;
    if (data.safety.approved_for_db_write !== false) {
        errors.push('manifest safety.approved_for_db_write must be false');
    }
    if (data.safety.approved_for_training !== false) {
        errors.push('manifest safety.approved_for_training must be false');
    }
    if (data.safety.approved_for_prediction !== false) {
        errors.push('manifest safety.approved_for_prediction must be false');
    }
}

// ---------------------------------------------------------------------------
// High-level validation: source manifest candidate
// ---------------------------------------------------------------------------

function validateManifest(manifestPath, schemaPath) {
    const result = { valid: false, errors: [] };

    if (!schemaPath) {
        result.errors.push('manifest schema path is required');
        return result;
    }
    if (!manifestPath) {
        result.errors.push('manifest file path is required');
        return result;
    }

    const schemaResult = readJsonFile(schemaPath);
    if (schemaResult.error) {
        result.errors.push(`manifest schema: ${schemaResult.error}`);
        return result;
    }

    const dataResult = readJsonFile(manifestPath);
    if (dataResult.error) {
        result.errors.push(`manifest data: ${dataResult.error}`);
        return result;
    }

    const data = dataResult.data;
    result.errors.push(...validateAgainstSchema(data, schemaResult.data));
    checkManifestStatus(data, result.errors);
    checkManifestEngine(data, result.errors);
    checkManifestSafety(data, result.errors);
    result.valid = result.errors.length === 0;
    return result;
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

function ensureRequiredPair(args, schemaKey, dataKey, label) {
    if (!args[schemaKey] && !args[dataKey]) return;
    if (!args[schemaKey]) {
        console.error(`ERROR: --${schemaKey.replace(/_/g, '-')} is required when validating ${label}`);
        process.exit(1);
    }
    if (!args[dataKey]) {
        console.error(`ERROR: --${dataKey.replace(/_/g, '-')} is required when validating ${label}`);
        process.exit(1);
    }
}

function buildOutput(artifactResult, manifestResult) {
    return {
        phase: 'PHASE4.80D_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA_VALIDATOR',
        validator_only: true,
        artifact_schema_valid: artifactResult ? artifactResult.valid : null,
        manifest_schema_valid: manifestResult ? manifestResult.valid : null,
        artifact_valid: artifactResult ? artifactResult.valid : null,
        manifest_valid: manifestResult ? manifestResult.valid : null,
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
    };
}

function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.commit) {
        console.error(
            'BLOCKED: single-target acquisition staging schema commit/execution is not wired in Phase 4.80D.'
        );
        process.exit(1);
    }

    const hasArtifact = args.artifact || args.artifact_schema;
    const hasManifest = args.manifest || args.manifest_schema;

    if (!hasArtifact && !hasManifest) {
        console.error('ERROR: provide at least --artifact-schema + --artifact or --manifest-schema + --manifest');
        process.exit(1);
    }

    ensureRequiredPair(args, 'artifact_schema', 'artifact', 'an artifact');
    ensureRequiredPair(args, 'manifest_schema', 'manifest', 'a manifest');

    let artifactResult = null;
    let manifestResult = null;

    if (args.artifact_schema && args.artifact) {
        artifactResult = validateArtifact(args.artifact, args.artifact_schema);
    }
    if (args.manifest_schema && args.manifest) {
        manifestResult = validateManifest(args.manifest, args.manifest_schema);
    }

    const output = buildOutput(artifactResult, manifestResult);
    const allErrors = [
        ...(artifactResult ? artifactResult.errors : []),
        ...(manifestResult ? manifestResult.errors : []),
    ];

    if (allErrors.length > 0) {
        for (const e of allErrors) {
            console.error('VALIDATION ERROR:', e);
        }
        console.log(JSON.stringify(output, null, 2));
        process.exit(1);
    }

    console.log(JSON.stringify(output, null, 2));
}

if (require.main === module) {
    main();
}

module.exports = { validateAgainstSchema, validateArtifact, validateManifest };
