/**
 * Phase 4.82D: Staging Packet Preview Unit Tests
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const child_process = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const SCRIPT = path.join(__dirname, '../../scripts/ops/single_target_acquisition_staging_packet_preview.js');
const ARTIFACT_SCHEMA = path.join(__dirname, '../../schemas/acquisition/single_target_staging_artifact.schema.json');
const MANIFEST_SCHEMA = path.join(__dirname, '../../schemas/acquisition/source_manifest_candidate.schema.json');
const SAMPLE_ARTIFACT = path.join(
    __dirname,
    '../fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json'
);
const SAMPLE_MANIFEST = path.join(__dirname, '../fixtures/acquisition/sample_source_manifest_candidate_phase480d.json');

function runPacket(opts) {
    const args = [];
    for (const [key, val] of Object.entries(opts)) {
        if (key === 'commit' && val) {
            args.push('--commit');
        } else {
            args.push(`--${key.replace(/_/g, '-')}=${val}`);
        }
    }
    const r = child_process.spawnSync(process.execPath, [SCRIPT, ...args], {
        encoding: 'utf8',
        timeout: 15000,
        env: { ...process.env, NODE_ENV: 'test' },
    });
    return { stdout: (r.stdout || '').trim(), stderr: (r.stderr || '').trim(), exitCode: r.status };
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
        terms_approval: 'no',
        network_dry_run_authorization: 'no',
        allow_browser_runtime: 'no',
        allow_proxy_runtime: 'no',
        allow_external_network: 'no',
        allow_staging_write: 'no',
        confirm_single_target_scope: 'yes',
        staging_write_authorization: 'no',
        final_human_confirmation: 'no',
    };
}

function makeTempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'phase482d-'));
}

describe('validateScaffold', () => {
    const { validateScaffold } = require(SCRIPT);

    it('accepts valid match_id scaffold params', () => {
        const errors = validateScaffold(baseOpts());
        assert.strictEqual(errors.length, 0, `unexpected: ${errors.join('; ')}`);
    });

    it('rejects missing target_source', () => {
        const o = baseOpts();
        delete o.target_source;
        assert.ok(validateScaffold(o).some(e => e.includes('target_source')));
    });

    it('rejects forbidden engine', () => {
        const o = baseOpts();
        o.target_engine_family = 'run_production';
        assert.ok(validateScaffold(o).some(e => e.includes('forbidden')));
    });

    it('rejects scope_type=bulk', () => {
        const o = baseOpts();
        o.target_scope_type = 'bulk';
        assert.ok(validateScaffold(o).some(e => e.includes('forbidden')));
    });

    it('rejects confirm_single_target_scope=no', () => {
        const o = baseOpts();
        o.confirm_single_target_scope = 'no';
        assert.ok(validateScaffold(o).some(e => e.includes('must be yes')));
    });
});

describe('packet CLI (subprocess)', () => {
    // 31. valid match_id preview
    it('exits 0 for valid match_id packet preview', () => {
        const r = runPacket(baseOpts());
        assert.strictEqual(r.exitCode, 0, r.stderr);
        const p = JSON.parse(r.stdout);
        assert.strictEqual(p.packet_preview_only, true);
        assert.strictEqual(p.runtime_scaffold_passed, true);
        assert.strictEqual(p.artifact_schema_valid, true);
        assert.strictEqual(p.manifest_schema_valid, true);
        assert.strictEqual(p.writer_preflight_passed, true);
        assert.strictEqual(p.target_consistency_valid, true);
        assert.strictEqual(p.output_root_allowed, true);
        assert.ok(p.packet_sections.length >= 7);
        assert.ok(p.future_staging_directory_preview);
        assert.ok(p.future_artifact_file_preview);
        assert.ok(p.future_manifest_file_preview);
    });

    // 33. all-yes still no-op
    it('outputs all would_* false even when all authorization fields are yes', () => {
        const o = baseOpts();
        o.terms_approval = 'yes';
        o.network_dry_run_authorization = 'yes';
        o.allow_browser_runtime = 'yes';
        o.allow_proxy_runtime = 'yes';
        o.allow_external_network = 'yes';
        o.allow_staging_write = 'yes';
        o.staging_write_authorization = 'yes';
        o.final_human_confirmation = 'yes';
        const r = runPacket(o);
        assert.strictEqual(r.exitCode, 0, r.stderr);
        const p = JSON.parse(r.stdout);
        assert.strictEqual(p.would_access_network, false);
        assert.strictEqual(p.would_write_staging, false);
        assert.strictEqual(p.would_write_db, false);
        assert.strictEqual(p.would_write_packet_file, false);
        assert.strictEqual(p.staging_write_authorized, false);
    });

    // 1-5 missing params
    it('fails when artifact_schema missing', () => {
        const o = baseOpts();
        delete o.artifact_schema;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when manifest_schema missing', () => {
        const o = baseOpts();
        delete o.manifest_schema;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when artifact missing', () => {
        const o = baseOpts();
        delete o.artifact;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when manifest missing', () => {
        const o = baseOpts();
        delete o.manifest;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when output_root missing', () => {
        const o = baseOpts();
        delete o.output_root;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });

    // 6-17 authorization missing
    it('fails when target_source missing', () => {
        const o = baseOpts();
        delete o.target_source;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when target_engine_family missing', () => {
        const o = baseOpts();
        delete o.target_engine_family;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when target_scope_type missing', () => {
        const o = baseOpts();
        delete o.target_scope_type;
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails when terms_approval invalid', () => {
        const o = baseOpts();
        o.terms_approval = 'bad';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });

    // 18-22 output root policy
    it('fails for absolute output_root', () => {
        const o = baseOpts();
        o.output_root = '/abs';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails for output_root with ..', () => {
        const o = baseOpts();
        o.output_root = 'docs/../esc';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails for output_root=data', () => {
        const o = baseOpts();
        o.output_root = 'data/staging';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails for output_root=docs/_packets', () => {
        const o = baseOpts();
        o.output_root = 'docs/_packets/x';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });

    // 24-29 consistency
    it('fails for target_source mismatch', () => {
        const o = baseOpts();
        o.target_source = 'other';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails for engine mismatch', () => {
        const o = baseOpts();
        o.target_engine_family = 'bad';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });
    it('fails for match_id mismatch', () => {
        const o = baseOpts();
        o.target_match_id = 'wrong';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });

    // 30 confirm=no
    it('fails when confirm_single_target_scope=no', () => {
        const o = baseOpts();
        o.confirm_single_target_scope = 'no';
        assert.notStrictEqual(runPacket(o).exitCode, 0);
    });

    // 38 --commit blocked
    it('exits non-zero for --commit', () => {
        const o = baseOpts();
        o.commit = true;
        const r = runPacket(o);
        assert.notStrictEqual(r.exitCode, 0);
        assert.ok(r.stderr.includes('commit/execution is not wired'));
    });
});

// Source audit
describe('source-code side-effect audit', () => {
    const source = fs.readFileSync(SCRIPT, 'utf8');
    it('does not import forbidden modules', () => {
        assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(source));
        assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source));
        assert.ok(!/require\s*\(\s*['"]redis/.test(source));
        assert.ok(!/require\s*\(\s*['"]playwright/.test(source));
        assert.ok(!/require\s*\(\s*['"]https?['"]/.test(source));
        assert.ok(!/require\s*\(\s*['"]child_process['"]/.test(source));
        assert.ok(!/writeFileSync|writeFile|createWriteStream|mkdirSync|mkdir/.test(source));
    });
});
