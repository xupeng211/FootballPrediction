/**
 * Phase 4.79D: Single-Target Acquisition Runtime Scaffold Unit Tests
 *
 * Validates parameter validation, output structure, and proves no runtime side effects.
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const child_process = require('child_process');
const path = require('path');
const fs = require('fs');

const SCRIPT = path.join(__dirname, '../../scripts/ops/single_target_acquisition_runtime_scaffold.js');

// ---------------------------------------------------------------------------
// Guard helpers: functions that must NOT be called by the scaffold.
// These are NOT installed globally to avoid breaking the test runner itself.
// Instead, we verify via source-code audit and subprocess execution.
// ---------------------------------------------------------------------------

/**
 * Verify the scaffold source does not import any forbidden module.
 */
function assertNoForbiddenImports(source) {
    const forbidden = [
        { pattern: /require\s*\(\s*['"](.*titan_discovery[^'"]*)['"]\s*\)/, name: 'titan_discovery' },
        { pattern: /require\s*\(\s*['"](.*DiscoveryService[^'"]*)['"]\s*\)/, name: 'DiscoveryService' },
        { pattern: /require\s*\(\s*['"](.*FixtureRepository[^'"]*)['"]\s*\)/, name: 'FixtureRepository' },
        { pattern: /require\s*\(\s*['"](.*playwright[^'"]*)['"]\s*\)/i, name: 'Playwright' },
        { pattern: /require\s*\(\s*['"]pg['"]\s*\)/, name: 'pg (node-postgres)' },
        { pattern: /require\s*\(\s*['"]redis[^'"]*['"]\s*\)/, name: 'Redis' },
        { pattern: /require\s*\(\s*['"]axios[^'"]*['"]\s*\)/, name: 'axios' },
        { pattern: /require\s*\(\s*['"]node-fetch[^'"]*['"]\s*\)/, name: 'node-fetch' },
    ];

    for (const { pattern, name } of forbidden) {
        assert.ok(!pattern.test(source), `scaffold must NOT import ${name}`);
    }
}

/**
 * Build CLI args array from an options object.
 */
function buildCliArgs(opts) {
    const args = [];
    for (const [key, val] of Object.entries(opts)) {
        if (key === 'commit' && val) {
            args.push('--commit');
        } else {
            args.push(`--${key.replace(/_/g, '-')}=${val}`);
        }
    }
    return args;
}

/**
 * Run scaffold as subprocess and return { stdout, stderr, exitCode }.
 */
function runScaffold(opts) {
    const args = buildCliArgs(opts);
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

// ---------------------------------------------------------------------------
// Unit tests: parseArgs
// ---------------------------------------------------------------------------

describe('parseArgs', () => {
    const { parseArgs } = require(SCRIPT);

    it('parses --key=value pairs', () => {
        const { args } = parseArgs(['--target-source=fotmob', '--terms-approval=yes']);
        assert.strictEqual(args.target_source, 'fotmob');
        assert.strictEqual(args.terms_approval, 'yes');
    });

    it('parses --key value form', () => {
        const { args } = parseArgs(['--target-source', 'fotmob', '--target-match-id', 'm123']);
        assert.strictEqual(args.target_source, 'fotmob');
        assert.strictEqual(args.target_match_id, 'm123');
    });

    it('captures --commit as boolean flag', () => {
        const { args } = parseArgs(['--commit', '--target-source=fotmob']);
        assert.strictEqual(args.commit, true);
    });

    it('converts hyphens to underscores in keys', () => {
        const { args } = parseArgs(['--target-source=fotmob']);
        assert.strictEqual(args.target_source, 'fotmob');
    });
});

// ---------------------------------------------------------------------------
// Unit tests: validate
// ---------------------------------------------------------------------------

describe('validate', () => {
    const { validate } = require(SCRIPT);

    // 1. missing target_source
    it('fails when target_source is missing', () => {
        const errors = validate({});
        const found = errors.some(e => e.includes('target-source is required'));
        assert.ok(found, 'should error on missing target_source');
    });

    // 2. missing target_engine_family
    it('fails when target_engine_family is missing', () => {
        const errors = validate({ target_source: 'fotmob' });
        const found = errors.some(e => e.includes('target-engine-family is required'));
        assert.ok(found, 'should error on missing target_engine_family');
    });

    // 3. non-titan_discovery engine family fails
    it('fails when engine family is not titan_discovery', () => {
        const errors = validate({ target_source: 'fotmob', target_engine_family: 'unknown_engine' });
        const found = errors.some(e => e.includes('unknown engine family'));
        assert.ok(found, 'should error on unknown engine family');
    });

    // 4. legacy engine run_production fails
    it('fails when engine family is run_production (legacy)', () => {
        const errors = validate({ target_source: 'fotmob', target_engine_family: 'run_production' });
        const found = errors.some(e => e.includes('forbidden legacy runtime'));
        assert.ok(found, 'should block run_production');
    });

    // 5. legacy engine recon_scanner fails
    it('fails when engine family is recon_scanner (legacy)', () => {
        const errors = validate({ target_source: 'fotmob', target_engine_family: 'recon_scanner' });
        const found = errors.some(e => e.includes('forbidden legacy runtime'));
        assert.ok(found, 'should block recon_scanner');
    });

    // 6. odds_harvest_pipeline fails
    it('fails when engine family is odds_harvest_pipeline (forbidden)', () => {
        const errors = validate({ target_source: 'fotmob', target_engine_family: 'odds_harvest_pipeline' });
        const found = errors.some(e => e.includes('forbidden legacy runtime'));
        assert.ok(found, 'should block odds_harvest_pipeline');
    });

    // 7. scope_type=all fails
    it('fails when target_scope_type is "all"', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'all',
        });
        const found = errors.some(e => e.includes('forbidden'));
        assert.ok(found, 'should block scope_type=all');
    });

    // 8. scope_type=bulk fails
    it('fails when target_scope_type is "bulk"', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'bulk',
        });
        const found = errors.some(e => e.includes('forbidden'));
        assert.ok(found, 'should block scope_type=bulk');
    });

    // 9. scope_type=production fails
    it('fails when target_scope_type is "production"', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'production',
        });
        const found = errors.some(e => e.includes('forbidden'));
        assert.ok(found, 'should block scope_type=production');
    });

    // 10. match_id scope missing target_match_id
    it('fails when scope_type=match_id but target_match_id is missing', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
        });
        const found = errors.some(e => e.includes('target-match-id is required'));
        assert.ok(found, 'should error on missing target_match_id');
    });

    // 11. league_season_date scope missing target_league
    it('fails when scope_type=league_season_date but target_league is missing', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'league_season_date',
            target_season: '2025-2026',
            target_date: '2026-05-09',
        });
        const found = errors.some(e => e.includes('target-league is required'));
        assert.ok(found, 'should error on missing target_league');
    });

    // 12. league_season_date scope missing target_season
    it('fails when scope_type=league_season_date but target_season is missing', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'league_season_date',
            target_league: 'EPL',
            target_date: '2026-05-09',
        });
        const found = errors.some(e => e.includes('target-season is required'));
        assert.ok(found, 'should error on missing target_season');
    });

    // 13. league_season_date scope missing target_date
    it('fails when scope_type=league_season_date but target_date is missing', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'league_season_date',
            target_league: 'EPL',
            target_season: '2025-2026',
        });
        const found = errors.some(e => e.includes('target-date is required'));
        assert.ok(found, 'should error on missing target_date');
    });

    // 14. confirm_single_target_scope=no fails
    it('fails when confirm_single_target_scope is "no"', () => {
        const errors = validate({
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
            confirm_single_target_scope: 'no',
        });
        const found = errors.some(e => e.includes('confirm-single-target-scope must be "yes"'));
        assert.ok(found, 'should error on confirm_single_target_scope=no');
    });

    // 15. invalid yes/no field
    it('fails when a yes/no field has an invalid value', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'sample-001',
            terms_approval: 'invalid',
        });
        const found = errors.some(e => e.includes('must be "yes" or "no"'));
        assert.ok(found, 'should error on invalid yes/no value');
    });

    // --commit blocked
    it('fails when --commit flag is present', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'sample-001',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
            commit: true,
        });
        const found = errors.some(e => e.includes('commit/execution is not wired'));
        assert.ok(found, 'should block --commit');
    });

    // 16. valid match_id scaffold succeeds
    it('returns no errors for a valid match_id scaffold', () => {
        const errors = validate({
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
        });
        assert.strictEqual(errors.length, 0, `unexpected errors: ${errors.join('; ')}`);
    });

    // 17. valid league_season_date scaffold succeeds
    it('returns no errors for a valid league_season_date scaffold', () => {
        const errors = validate({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'league_season_date',
            target_league: 'EPL',
            target_season: '2025-2026',
            target_date: '2026-05-09',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(errors.length, 0, `unexpected errors: ${errors.join('; ')}`);
    });
});

// ---------------------------------------------------------------------------
// Unit tests: buildOutput — all would_* are false regardless of yes fields
// ---------------------------------------------------------------------------

describe('buildOutput', () => {
    const { buildOutput } = require(SCRIPT);

    function assertAllWouldFalse(output) {
        const falseFields = [
            'would_execute_legacy_titan_discovery',
            'would_execute_engine',
            'would_access_network',
            'would_launch_browser',
            'would_use_proxy',
            'would_write_staging',
            'would_create_staging_directory',
            'would_write_source_manifest',
            'would_write_db',
            'would_train',
            'would_predict',
            'would_bulk_harvest',
            'would_spawn_child_process',
        ];
        for (const field of falseFields) {
            assert.strictEqual(output[field], false, `${field} must be false in scaffold output`);
        }
    }

    // 18. even with terms_approval=yes, would_access_network stays false
    it('outputs would_access_network=false even when terms_approval=yes', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'yes',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assertAllWouldFalse(output);
        assert.strictEqual(output.would_access_network, false);
        assert.strictEqual(output.commit_gate, 'blocked');
    });

    // 19. even with network_dry_run_authorization=yes, no network
    it('outputs would_access_network=false even when network_dry_run_authorization=yes', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'yes',
            network_dry_run_authorization: 'yes',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assertAllWouldFalse(output);
        assert.strictEqual(output.would_access_network, false);
    });

    // 20. even with allow_browser_runtime=yes, no browser
    it('outputs would_launch_browser=false even when allow_browser_runtime=yes', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'yes',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assertAllWouldFalse(output);
        assert.strictEqual(output.would_launch_browser, false);
    });

    // 21. even with allow_proxy_runtime=yes, no proxy
    it('outputs would_use_proxy=false even when allow_proxy_runtime=yes', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'yes',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assertAllWouldFalse(output);
        assert.strictEqual(output.would_use_proxy, false);
    });

    // 22. even with allow_staging_write=yes, no staging write
    it('outputs would_write_staging=false even when allow_staging_write=yes', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'yes',
            confirm_single_target_scope: 'yes',
        });
        assertAllWouldFalse(output);
        assert.strictEqual(output.would_write_staging, false);
    });

    // 23-28: explicit would_* false checks
    it('outputs would_execute_legacy_titan_discovery=false', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.would_execute_legacy_titan_discovery, false);
    });

    it('outputs would_write_db=false', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.would_write_db, false);
    });

    it('outputs would_write_staging=false', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.would_write_staging, false);
    });

    it('outputs would_execute_engine=false', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.would_execute_engine, false);
    });

    it('outputs commit_gate=blocked', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.commit_gate, 'blocked');
    });

    it('outputs scaffold_only=true and runtime_plan_created=true', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.scaffold_only, true);
        assert.strictEqual(output.runtime_plan_created, true);
    });

    it('includes all 8 guardrails', () => {
        const output = buildOutput({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'm1',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(output.guardrails.length, 8);
        assert.ok(output.guardrails.includes('no_external_network'));
        assert.ok(output.guardrails.includes('no_browser_automation'));
        assert.ok(output.guardrails.includes('no_proxy_runtime_execution'));
        assert.ok(output.guardrails.includes('no_db_writes'));
        assert.ok(output.guardrails.includes('no_staging_writes'));
        assert.ok(output.guardrails.includes('no_legacy_runtime'));
        assert.ok(output.guardrails.includes('no_training'));
        assert.ok(output.guardrails.includes('no_prediction'));
    });
});

// ---------------------------------------------------------------------------
// Integration tests: scaffold as subprocess
// ---------------------------------------------------------------------------

describe('scaffold CLI (subprocess)', () => {
    // 16. valid match_id scaffold success
    it('exits 0 and outputs valid JSON for match_id scaffold', () => {
        const result = runScaffold({
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
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.scaffold_only, true);
        assert.strictEqual(parsed.would_access_network, false);
        assert.strictEqual(parsed.would_write_db, false);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.commit_gate, 'blocked');
    });

    // 17. valid league_season_date scaffold success
    it('exits 0 and outputs valid JSON for league_season_date scaffold', () => {
        const result = runScaffold({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'league_season_date',
            target_league: 'EPL',
            target_season: '2025-2026',
            target_date: '2026-05-09',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.target_scope_type, 'league_season_date');
        assert.strictEqual(parsed.would_access_network, false);
    });

    // --commit blocked in CLI
    it('exits non-zero when --commit is passed', () => {
        const result = runScaffold({
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
            commit: true,
        });
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero for --commit');
        assert.ok(
            result.stderr.includes('commit/execution is not wired'),
            `stderr should mention blocked commit: ${result.stderr}`
        );
    });

    // missing required field fails
    it('exits non-zero when target_source is missing', () => {
        const result = runScaffold({});
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero');
        assert.ok(result.stderr.includes('target-source'), `stderr: ${result.stderr}`);
    });

    // Invalid scope type fails
    it('exits non-zero when scope_type is "all"', () => {
        const result = runScaffold({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'all',
            target_match_id: 'sample-match-001',
            terms_approval: 'no',
            network_dry_run_authorization: 'no',
            allow_browser_runtime: 'no',
            allow_proxy_runtime: 'no',
            allow_external_network: 'no',
            allow_staging_write: 'no',
            confirm_single_target_scope: 'yes',
        });
        assert.notStrictEqual(result.exitCode, 0, 'should exit non-zero for scope=all');
    });

    // all yes fields still produce would_* false
    it('outputs all would_* false even when all yes/no fields are yes', () => {
        const result = runScaffold({
            target_source: 'fotmob',
            target_engine_family: 'titan_discovery',
            target_scope_type: 'match_id',
            target_match_id: 'sample-match-001',
            terms_approval: 'yes',
            network_dry_run_authorization: 'yes',
            allow_browser_runtime: 'yes',
            allow_proxy_runtime: 'yes',
            allow_external_network: 'yes',
            allow_staging_write: 'yes',
            confirm_single_target_scope: 'yes',
        });
        assert.strictEqual(result.exitCode, 0, `stderr: ${result.stderr}`);
        const parsed = JSON.parse(result.stdout);
        assert.strictEqual(parsed.would_access_network, false);
        assert.strictEqual(parsed.would_launch_browser, false);
        assert.strictEqual(parsed.would_use_proxy, false);
        assert.strictEqual(parsed.would_write_staging, false);
        assert.strictEqual(parsed.would_write_db, false);
        assert.strictEqual(parsed.would_execute_engine, false);
    });
});

// ---------------------------------------------------------------------------
// Source-code audit: no forbidden imports, no side effects
// ---------------------------------------------------------------------------

describe('source-code side-effect audit', () => {
    const source = fs.readFileSync(SCRIPT, 'utf8');

    // 29. no titan_discovery import
    it('does not import or reference titan_discovery module', () => {
        assertNoForbiddenImports(source);
    });

    // 30. no child_process
    it('does not import child_process', () => {
        assert.ok(!/require\s*\(\s*['"]child_process['"]\s*\)/.test(source), 'must not import child_process');
    });

    // 31-34: no fs writes, no mkdir, no network, no DB
    it('does not import fs write methods', () => {
        assert.ok(
            !/fs\.writeFileSync|fs\.writeFile|fs\.createWriteStream/.test(source),
            'must not import fs write methods'
        );
        assert.ok(!/fs\.mkdirSync|fs\.mkdir/.test(source), 'must not import fs mkdir methods');
    });

    it('does not import http/https modules', () => {
        assert.ok(!/require\s*\(\s*['"]https?['"]\s*\)/.test(source), 'must not import http or https');
    });

    it('does not import net module', () => {
        assert.ok(!/require\s*\(\s*['"]net['"]\s*\)/.test(source), 'must not import net module');
    });

    it('does not import pg module', () => {
        assert.ok(!/require\s*\(\s*['"]pg['"]\s*\)/.test(source), 'must not import pg');
    });

    it('does not import redis module', () => {
        assert.ok(!/require\s*\(\s*['"]redis/.test(source), 'must not import redis');
    });

    it('does not import playwright', () => {
        assert.ok(!/require\s*\(\s*['"]playwright/.test(source), 'must not import playwright');
    });

    it('does not import fetch/axios', () => {
        assert.ok(!/require\s*\(\s*['"]axios/.test(source), 'must not import axios');
        assert.ok(!/require\s*\(\s*['"]node-fetch/.test(source), 'must not import node-fetch');
    });
});
