/**
 * Phase 4.81D: Single-Target Acquisition Staging Writer Preflight Unit Tests
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const child_process = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const SCRIPT = path.join(__dirname, '../../scripts/ops/single_target_acquisition_staging_writer_preflight.js');
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

function runPreflight(opts) {
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
        timeout: 15000,
        env: { ...process.env, NODE_ENV: 'test' },
    });
    return {
        stdout: (result.stdout || '').trim(),
        stderr: (result.stderr || '').trim(),
        exitCode: result.status,
    };
}

function makeTempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'phase481d-'));
}

function writeTempJson(dir, name, data) {
    const p = path.join(dir, name);
    fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf8');
    return p;
}

function baseOpts() {
    return {
        artifact_schema: ARTIFACT_SCHEMA,
        manifest_schema: MANIFEST_SCHEMA,
        artifact: SAMPLE_ARTIFACT,
        manifest: SAMPLE_MANIFEST,
        output_root: 'docs/_staging_preview/acquisition/single_target',
        target_source: 'fotmob',
        target_engine_family: 'titan_discovery',
        target_scope_type: 'match_id',
        target_match_id: 'sample-match-001',
        staging_write_authorization: 'no',
        final_human_confirmation: 'no',
    };
}

// ---------------------------------------------------------------------------
// Unit tests: checkOutputRoot
// ---------------------------------------------------------------------------

describe('checkOutputRoot', () => {
    const { checkOutputRoot } = require(SCRIPT);

    it('rejects empty output_root', () => {
        const errors = checkOutputRoot('');
        assert.ok(
            errors.some(e => e.includes('required')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('rejects absolute path', () => {
        const errors = checkOutputRoot('/absolute/path');
        assert.ok(
            errors.some(e => e.includes('absolute')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('rejects path with ..', () => {
        const errors = checkOutputRoot('docs/../escape');
        assert.ok(
            errors.some(e => e.includes('..')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('rejects docs/_packets', () => {
        const errors = checkOutputRoot('docs/_packets/something');
        assert.ok(
            errors.some(e => e.includes('forbidden')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('rejects data/ root', () => {
        const errors = checkOutputRoot('data/staging');
        assert.ok(
            errors.some(e => e.includes('forbidden')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('rejects output_root outside allowed root', () => {
        const errors = checkOutputRoot('docs/other_dir');
        assert.ok(
            errors.some(e => e.includes('must be under')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('accepts valid output root', () => {
        const errors = checkOutputRoot('docs/_staging_preview/acquisition/single_target');
        assert.strictEqual(errors.length, 0, `unexpected errors: ${errors.join('; ')}`);
    });

    it('accepts valid subdirectory', () => {
        const errors = checkOutputRoot('docs/_staging_preview/acquisition/single_target/fotmob/titan_discovery');
        assert.strictEqual(errors.length, 0, `unexpected errors: ${errors.join('; ')}`);
    });
});

// ---------------------------------------------------------------------------
// Unit tests: safeSlug, extractHash8
// ---------------------------------------------------------------------------

describe('safeSlug', () => {
    const { safeSlug } = require(SCRIPT);

    it('replaces spaces with underscores', () => {
        assert.strictEqual(safeSlug('hello world'), 'hello_world');
    });

    it('removes slashes', () => {
        assert.ok(!safeSlug('a/b').includes('/'));
    });

    it('removes dot-dot', () => {
        assert.ok(!safeSlug('a..b').includes('..'));
    });
});

describe('extractHash8', () => {
    const { extractHash8 } = require(SCRIPT);

    it('extracts first 8 hex chars from sha256', () => {
        const hash8 = extractHash8({
            capture: { raw_payload_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
        });
        assert.strictEqual(hash8, 'e3b0c442');
    });

    it('returns fallback for non-hex', () => {
        const hash8 = extractHash8({ capture: { raw_payload_sha256: 'nothex!!' } });
        assert.strictEqual(hash8, '00000000');
    });

    it('returns fallback for missing capture', () => {
        const hash8 = extractHash8({});
        assert.strictEqual(hash8, '00000000');
    });
});

// ---------------------------------------------------------------------------
// Unit tests: checkTargetConsistency
// ---------------------------------------------------------------------------

describe('checkTargetConsistency', () => {
    const { checkTargetConsistency } = require(SCRIPT);
    const art = {
        source: { name: 'fotmob' },
        engine: { family: 'titan_discovery' },
        target_scope: { scope_type: 'match_id', match_id: 'sample-match-001' },
    };
    const man = {
        source_name: 'fotmob',
        engine_family: 'titan_discovery',
        target_scope: { scope_type: 'match_id', match_id: 'sample-match-001' },
    };

    it('passes when all targets match', () => {
        const errors = checkTargetConsistency(
            {
                target_source: 'fotmob',
                target_engine_family: 'titan_discovery',
                target_scope_type: 'match_id',
                target_match_id: 'sample-match-001',
            },
            art,
            man
        );
        assert.strictEqual(errors.length, 0, `unexpected: ${errors.join('; ')}`);
    });

    it('fails when target_source mismatches artifact', () => {
        const errors = checkTargetConsistency({ target_source: 'other' }, art, man);
        assert.ok(
            errors.some(e => e.includes('source')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('fails when engine family mismatches', () => {
        const errors = checkTargetConsistency({ target_engine_family: 'other' }, art, man);
        assert.ok(
            errors.some(e => e.includes('engine')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('fails when scope_type mismatches', () => {
        const errors = checkTargetConsistency({ target_scope_type: 'league_season_date' }, art, man);
        assert.ok(
            errors.some(e => e.includes('scope')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('fails when match_id mismatches', () => {
        const errors = checkTargetConsistency(
            {
                target_scope_type: 'match_id',
                target_match_id: 'wrong-id',
            },
            art,
            man
        );
        assert.ok(
            errors.some(e => e.includes('match_id')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('fails for unsupported engine family', () => {
        const errors = checkTargetConsistency({ target_engine_family: 'run_production' }, art, man);
        assert.ok(
            errors.some(e => e.includes('not allowed')),
            `errors: ${errors.join('; ')}`
        );
    });

    it('fails for forbidden scope type bulk', () => {
        const errors = checkTargetConsistency({ target_scope_type: 'bulk' }, art, man);
        assert.ok(
            errors.some(e => e.includes('forbidden')),
            `errors: ${errors.join('; ')}`
        );
    });
});

// ---------------------------------------------------------------------------
// Integration tests: CLI via subprocess
// ---------------------------------------------------------------------------

describe('preflight CLI (subprocess)', () => {
    // 24. valid match_id preflight success
    it('exits 0 for valid match_id preflight', () => {
        const result = runPreflight(baseOpts());
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.preflight_only, true);
        assert.strictEqual(parsed.artifact_schema_valid, true);
        assert.strictEqual(parsed.manifest_schema_valid, true);
        assert.strictEqual(parsed.output_root_allowed, true);
        assert.strictEqual(parsed.target_consistency_valid, true);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.would_create_staging_directory, false);
        assert.strictEqual(parsed.would_write_source_manifest, false);
        assert.strictEqual(parsed.commit_gate, 'blocked');
        // path previews present
        assert.ok(parsed.future_staging_directory_preview);
        assert.ok(parsed.future_artifact_file_preview);
        assert.ok(parsed.future_manifest_file_preview);
    });

    // 26-27: authorization yes still blocks
    it('outputs would_write_staging=false even when authorization fields are yes', () => {
        const opts = baseOpts();
        opts.staging_write_authorization = 'yes';
        opts.final_human_confirmation = 'yes';
        const result = runPreflight(opts);
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.would_create_staging_directory, false);
        assert.strictEqual(parsed.staging_write_authorized, false);
    });

    // 1. missing artifact schema
    it('fails when artifact_schema is missing', () => {
        const opts = baseOpts();
        delete opts.artifact_schema;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 2. missing manifest schema
    it('fails when manifest_schema is missing', () => {
        const opts = baseOpts();
        delete opts.manifest_schema;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 3. missing artifact
    it('fails when artifact is missing', () => {
        const opts = baseOpts();
        delete opts.artifact;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 4. missing manifest
    it('fails when manifest is missing', () => {
        const opts = baseOpts();
        delete opts.manifest;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 5. missing output_root
    it('fails when output_root is missing', () => {
        const opts = baseOpts();
        delete opts.output_root;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 6. missing target_source
    it('fails when target_source is missing', () => {
        const opts = baseOpts();
        delete opts.target_source;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 7. missing target_engine_family
    it('fails when target_engine_family is missing', () => {
        const opts = baseOpts();
        delete opts.target_engine_family;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 8. missing target_scope_type
    it('fails when target_scope_type is missing', () => {
        const opts = baseOpts();
        delete opts.target_scope_type;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 9. missing staging_write_authorization
    it('fails when staging_write_authorization is missing', () => {
        const opts = baseOpts();
        delete opts.staging_write_authorization;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 10. missing final_human_confirmation
    it('fails when final_human_confirmation is missing', () => {
        const opts = baseOpts();
        delete opts.final_human_confirmation;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 11-15. output_root policy tests
    it('fails for absolute output_root', () => {
        const opts = baseOpts();
        opts.output_root = '/absolute/path';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    it('fails for output_root with ..', () => {
        const opts = baseOpts();
        opts.output_root = 'docs/../escape';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    it('fails for output_root=data', () => {
        const opts = baseOpts();
        opts.output_root = 'data/staging';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    it('fails for output_root=docs/_packets', () => {
        const opts = baseOpts();
        opts.output_root = 'docs/_packets/something';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 16-17. schema validation failure
    it('fails when artifact schema is invalid', () => {
        const tmpDir = makeTempDir();
        const badArtifact = writeTempJson(tmpDir, 'bad_artifact.json', { not_valid: true });
        const opts = baseOpts();
        opts.artifact = badArtifact;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0, 'should fail for invalid artifact');
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    // 18-20. target mismatch
    it('fails when target_source mismatches', () => {
        const opts = baseOpts();
        opts.target_source = 'other_source';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    it('fails when target_engine_family mismatches', () => {
        const opts = baseOpts();
        opts.target_engine_family = 'bad_engine';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    it('fails when target_match_id mismatches', () => {
        const opts = baseOpts();
        opts.target_match_id = 'wrong-match';
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0);
    });

    // 31. --commit blocked
    it('exits non-zero when --commit is passed', () => {
        const opts = baseOpts();
        opts.commit = true;
        const result = runPreflight(opts);
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero for --commit');
        assert.ok(result.stderr.includes('commit/execution is not wired'), `stderr: ${result.stderr}`);
    });

    // all would_* false
    it('outputs all would_* false', () => {
        const result = runPreflight(baseOpts());
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
        assert.strictEqual(parsed.staging_write_authorized, false);
    });

    // path preview correctness
    it('generates correct future directory preview', () => {
        const result = runPreflight(baseOpts());
        const parsed = JSON.parse(result.stdout);
        assert.ok(parsed.future_staging_directory_preview.includes('docs/_staging_preview/acquisition/single_target'));
        assert.ok(parsed.future_staging_directory_preview.includes('fotmob'));
        assert.ok(parsed.future_staging_directory_preview.includes('titan_discovery'));
        assert.ok(parsed.future_staging_directory_preview.includes('match_id'));
        assert.ok(parsed.future_staging_directory_preview.includes('sample-match-001'));
        assert.ok(parsed.future_artifact_file_preview.endsWith('.json'));
        assert.ok(parsed.future_manifest_file_preview.endsWith('.json'));
    });
});

// ---------------------------------------------------------------------------
// Source-code audit: no side effects
// ---------------------------------------------------------------------------

describe('source-code side-effect audit', () => {
    const source = fs.readFileSync(SCRIPT, 'utf8');

    it('does not import titan_discovery or DiscoveryService', () => {
        assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(source), 'must not import titan_discovery');
        assert.ok(!/require\s*\(\s*['"].*DiscoveryService/.test(source), 'must not import DiscoveryService');
    });

    it('does not import pg/redis', () => {
        assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source), 'must not import pg');
        assert.ok(!/require\s*\(\s*['"]redis/.test(source), 'must not import redis');
    });

    it('does not import playwright', () => {
        assert.ok(!/require\s*\(\s*['"]playwright/.test(source), 'must not import playwright');
    });

    it('does not import http/https/net', () => {
        assert.ok(!/require\s*\(\s*['"]https?['"]/.test(source), 'must not import http/https');
        assert.ok(!/require\s*\(\s*['"]net['"]/.test(source), 'must not import net');
    });

    it('does not import child_process', () => {
        assert.ok(!/require\s*\(\s*['"]child_process['"]/.test(source), 'must not import child_process');
    });

    it('does not use fs write/mkdir methods', () => {
        assert.ok(
            !/writeFileSync|writeFile|createWriteStream|mkdirSync|mkdir/.test(source),
            'must not use fs write/mkdir'
        );
    });
});
