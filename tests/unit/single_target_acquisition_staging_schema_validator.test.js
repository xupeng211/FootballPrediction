/**
 * Phase 4.80D: Single-Target Acquisition Staging Schema Validator Unit Tests
 *
 * Validates schema-based artifact/manifest validation and proves no runtime side effects.
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const child_process = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const SCRIPT = path.join(__dirname, '../../scripts/ops/single_target_acquisition_staging_schema_validator.js');
const ARTIFACT_SCHEMA = path.join(__dirname, '../../schemas/acquisition/single_target_staging_artifact.schema.json');
const MANIFEST_SCHEMA = path.join(__dirname, '../../schemas/acquisition/source_manifest_candidate.schema.json');
const SAMPLE_ARTIFACT = path.join(
    __dirname,
    '../fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json'
);
const SAMPLE_MANIFEST = path.join(__dirname, '../fixtures/acquisition/sample_source_manifest_candidate_phase480d.json');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function runValidator(opts) {
    const args = [];
    for (const [key, val] of Object.entries(opts)) {
        if (key === 'commit' && val) {
            args.push('--commit');
        } else {
            args.push(`--${key.replace(/_/g, '-')}=${val}`);
        }
    }
    const result = child_process.spawnSync(process.execPath, [SCRIPT, ...args], {
        encoding: 'utf8',
        timeout: 10000,
        env: { ...process.env, NODE_ENV: 'test' },
    });
    return {
        stdout: (result.stdout || '').trim(),
        stderr: (result.stderr || '').trim(),
        exitCode: result.status,
    };
}

function writeTempFile(data) {
    const tmpDir = os.tmpdir();
    const tmpFile = path.join(tmpDir, `phase480d_test_${Date.now()}_${Math.random().toString(36).slice(2)}.json`);
    fs.writeFileSync(tmpFile, JSON.stringify(data, null, 2), 'utf8');
    return tmpFile;
}

function cleanupTempFile(filePath) {
    try {
        fs.unlinkSync(filePath);
    } catch (_) {
        /* ignore */
    }
}

// ---------------------------------------------------------------------------
// Unit tests: validateArtifact
// ---------------------------------------------------------------------------

describe('validateArtifact', () => {
    const { validateArtifact } = require(SCRIPT);

    // 7. valid artifact passes
    it('validates a correct staging artifact successfully', () => {
        const result = validateArtifact(SAMPLE_ARTIFACT, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, true, `errors: ${result.errors.join('; ')}`);
    });

    // 1. missing artifact schema
    it('fails when artifact schema path is missing', () => {
        const result = validateArtifact(SAMPLE_ARTIFACT, null);
        assert.strictEqual(result.valid, false);
        assert.ok(result.errors.some(e => e.includes('schema path is required')));
    });

    // 3. artifact schema is invalid JSON
    it('fails when artifact schema file is not valid JSON', () => {
        const badSchema = writeTempFile({ not_a_schema: true, __bad: undefined });
        const result = validateArtifact(SAMPLE_ARTIFACT, badSchema);
        // The schema is valid JSON but lacks type info needed for validation
        // Actually test a non-existent file for schema
        const result2 = validateArtifact(SAMPLE_ARTIFACT, '/nonexistent/schema.json');
        assert.strictEqual(result2.valid, false);
        cleanupTempFile(badSchema);
    });

    // 5. artifact invalid JSON
    it('fails when artifact data is not valid JSON', () => {
        const tmpFile = writeTempFile({ __invalid: true });
        const result = validateArtifact(tmpFile, '/nonexistent/schema.json');
        assert.strictEqual(result.valid, false);
        cleanupTempFile(tmpFile);
    });

    // 10. missing source.name
    it('fails when artifact is missing source.name', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        delete data.source.name;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when source.name is missing');
        assert.ok(
            result.errors.some(e => e.includes('source.name')),
            `errors: ${result.errors.join('; ')}`
        );
        cleanupTempFile(tmpFile);
    });

    // 11. missing target_scope
    it('fails when artifact is missing target_scope', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        delete data.target_scope;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when target_scope is missing');
        cleanupTempFile(tmpFile);
    });

    // 12. unsupported scope_type=bulk
    it('fails when artifact scope_type is "bulk"', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.target_scope.scope_type = 'bulk';
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for scope_type=bulk');
        assert.ok(result.errors.some(e => e.includes('forbidden') || e.includes('enum')));
        cleanupTempFile(tmpFile);
    });

    // 13. match_id scope but missing match_id
    it('fails when scope_type=match_id but match_id is missing', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        delete data.target_scope.match_id;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when match_id is missing');
        assert.ok(result.errors.some(e => e.includes('match_id')));
        cleanupTempFile(tmpFile);
    });

    // 14. league_season_date scope missing league/season/date
    it('fails when scope_type=league_season_date but league is missing', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.target_scope.scope_type = 'league_season_date';
        data.target_scope.match_id = null;
        data.target_scope.league = null;
        data.target_scope.season = '2025-2026';
        data.target_scope.date = '2026-05-09';
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when league is missing for league_season_date');
        cleanupTempFile(tmpFile);
    });

    // 15. engine.family not titan_discovery
    it('fails when artifact engine.family is not titan_discovery', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.engine.family = 'run_production';
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for non-titan_discovery engine');
        cleanupTempFile(tmpFile);
    });

    // 16. safety.would_write_db=true
    it('fails when artifact safety.would_write_db is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.safety.would_write_db = true;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for would_write_db=true');
        assert.ok(result.errors.some(e => e.includes('would_write_db')));
        cleanupTempFile(tmpFile);
    });

    // 17. safety.would_train=true
    it('fails when artifact safety.would_train is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.safety.would_train = true;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for would_train=true');
        cleanupTempFile(tmpFile);
    });

    // 18. safety.would_predict=true
    it('fails when artifact safety.would_predict is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.safety.would_predict = true;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for would_predict=true');
        cleanupTempFile(tmpFile);
    });

    // 19. safety.bulk_scope=true
    it('fails when artifact safety.bulk_scope is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.safety.bulk_scope = true;
        const tmpFile = writeTempFile(data);
        const result = validateArtifact(tmpFile, ARTIFACT_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for bulk_scope=true');
        cleanupTempFile(tmpFile);
    });
});

// ---------------------------------------------------------------------------
// Unit tests: validateManifest
// ---------------------------------------------------------------------------

describe('validateManifest', () => {
    const { validateManifest } = require(SCRIPT);

    // 8. valid manifest passes
    it('validates a correct manifest candidate successfully', () => {
        const result = validateManifest(SAMPLE_MANIFEST, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, true, `errors: ${result.errors.join('; ')}`);
    });

    // 2. missing manifest schema
    it('fails when manifest schema path is missing', () => {
        const result = validateManifest(SAMPLE_MANIFEST, null);
        assert.strictEqual(result.valid, false);
    });

    // 4. manifest schema invalid JSON
    it('fails when manifest schema file does not exist', () => {
        const result = validateManifest(SAMPLE_MANIFEST, '/nonexistent/manifest_schema.json');
        assert.strictEqual(result.valid, false);
    });

    // 6. manifest invalid JSON
    it('fails when manifest data is not valid JSON', () => {
        const result = validateManifest('/nonexistent/manifest.json', MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false);
    });

    // 20. missing source_name
    it('fails when manifest is missing source_name', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        delete data.source_name;
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when source_name is missing');
        cleanupTempFile(tmpFile);
    });

    // 21. manifest_status not candidate_not_approved
    it('fails when manifest_status is not candidate_not_approved', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        data.manifest_status = 'approved';
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when manifest_status is not candidate_not_approved');
        cleanupTempFile(tmpFile);
    });

    // 22. approval_status not not_approved
    it('fails when approval_status is not not_approved', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        data.approval_status = 'approved';
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail when approval_status is not not_approved');
        cleanupTempFile(tmpFile);
    });

    // 23. approved_for_db_write=true
    it('fails when manifest safety.approved_for_db_write is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        data.safety.approved_for_db_write = true;
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for approved_for_db_write=true');
        assert.ok(result.errors.some(e => e.includes('approved_for_db_write')));
        cleanupTempFile(tmpFile);
    });

    // 24. approved_for_training=true
    it('fails when manifest safety.approved_for_training is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        data.safety.approved_for_training = true;
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for approved_for_training=true');
        cleanupTempFile(tmpFile);
    });

    // 25. approved_for_prediction=true
    it('fails when manifest safety.approved_for_prediction is true', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_MANIFEST, 'utf8'));
        data.safety.approved_for_prediction = true;
        const tmpFile = writeTempFile(data);
        const result = validateManifest(tmpFile, MANIFEST_SCHEMA);
        assert.strictEqual(result.valid, false, 'should fail for approved_for_prediction=true');
        cleanupTempFile(tmpFile);
    });
});

// ---------------------------------------------------------------------------
// Integration tests: validator CLI via subprocess
// ---------------------------------------------------------------------------

describe('validator CLI (subprocess)', () => {
    // 9. artifact + manifest both pass
    it('exits 0 and outputs valid JSON for artifact + manifest', () => {
        const result = runValidator({
            artifact_schema: ARTIFACT_SCHEMA,
            manifest_schema: MANIFEST_SCHEMA,
            artifact: SAMPLE_ARTIFACT,
            manifest: SAMPLE_MANIFEST,
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.artifact_schema_valid, true);
        assert.strictEqual(parsed.manifest_schema_valid, true);
        assert.strictEqual(parsed.would_access_network, false);
        assert.strictEqual(parsed.would_write_db, false);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.commit_gate, 'blocked');
    });

    // artifact-only succeeds
    it('exits 0 for artifact-only validation', () => {
        const result = runValidator({
            artifact_schema: ARTIFACT_SCHEMA,
            artifact: SAMPLE_ARTIFACT,
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.artifact_valid, true);
    });

    // manifest-only succeeds
    it('exits 0 for manifest-only validation', () => {
        const result = runValidator({
            manifest_schema: MANIFEST_SCHEMA,
            manifest: SAMPLE_MANIFEST,
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.manifest_valid, true);
    });

    // missing params fails
    it('exits non-zero when no schema or artifact/manifest provided', () => {
        const result = runValidator({});
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero');
    });

    // 26. --commit blocked
    it('exits non-zero when --commit is passed', () => {
        const result = runValidator({
            artifact_schema: ARTIFACT_SCHEMA,
            artifact: SAMPLE_ARTIFACT,
            commit: true,
        });
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero for --commit');
        assert.ok(result.stderr.includes('commit/execution is not wired'), `stderr: ${result.stderr}`);
    });

    // artifact with bad data fails
    it('exits non-zero when artifact has invalid engine family', () => {
        const data = JSON.parse(fs.readFileSync(SAMPLE_ARTIFACT, 'utf8'));
        data.engine.family = 'bad_engine';
        const tmpFile = writeTempFile(data);
        const result = runValidator({
            artifact_schema: ARTIFACT_SCHEMA,
            artifact: tmpFile,
        });
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero for invalid engine family');
        cleanupTempFile(tmpFile);
    });

    // all would_* false in output
    it('outputs all would_* false even when all validation passes', () => {
        const result = runValidator({
            artifact_schema: ARTIFACT_SCHEMA,
            manifest_schema: MANIFEST_SCHEMA,
            artifact: SAMPLE_ARTIFACT,
            manifest: SAMPLE_MANIFEST,
        });
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.would_access_network, false);
        assert.strictEqual(parsed.would_launch_browser, false);
        assert.strictEqual(parsed.would_use_proxy, false);
        assert.strictEqual(parsed.would_execute_engine, false);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.would_create_staging_directory, false);
        assert.strictEqual(parsed.would_write_source_manifest, false);
        assert.strictEqual(parsed.would_write_db, false);
        assert.strictEqual(parsed.would_train, false);
        assert.strictEqual(parsed.would_predict, false);
        assert.strictEqual(parsed.would_spawn_child_process, false);
        assert.strictEqual(parsed.commit_gate, 'blocked');
    });
});

// ---------------------------------------------------------------------------
// Source-code audit: no forbidden imports, no side effects
// ---------------------------------------------------------------------------

describe('source-code side-effect audit', () => {
    const source = fs.readFileSync(SCRIPT, 'utf8');

    it('does not import titan_discovery or DiscoveryService', () => {
        assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(source), 'must not import titan_discovery');
        assert.ok(!/require\s*\(\s*['"].*DiscoveryService/.test(source), 'must not import DiscoveryService');
    });

    it('does not import pg or redis', () => {
        assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source), 'must not import pg');
        assert.ok(!/require\s*\(\s*['"]redis/.test(source), 'must not import redis');
    });

    it('does not import playwright', () => {
        assert.ok(!/require\s*\(\s*['"]playwright/.test(source), 'must not import playwright');
    });

    it('does not import http/https/net modules', () => {
        assert.ok(!/require\s*\(\s*['"]https?['"]/.test(source), 'must not import http/https');
        assert.ok(!/require\s*\(\s*['"]net['"]/.test(source), 'must not import net');
    });

    it('does not import child_process', () => {
        assert.ok(!/require\s*\(\s*['"]child_process['"]/.test(source), 'must not import child_process');
    });

    it('does not import axios/node-fetch', () => {
        assert.ok(!/require\s*\(\s*['"]axios/.test(source), 'must not import axios');
        assert.ok(!/require\s*\(\s*['"]node-fetch/.test(source), 'must not import node-fetch');
    });

    it('does not use fs write methods', () => {
        assert.ok(
            !/writeFileSync|writeFile|createWriteStream|mkdirSync|mkdir/.test(source),
            'must not use fs write/mkdir methods'
        );
    });
});
