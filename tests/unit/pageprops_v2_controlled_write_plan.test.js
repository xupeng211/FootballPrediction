'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_controlled_write_plan.js');
const plan = require(MODULE_PATH);

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        'current-version': 'fotmob_html_hyd_v1',
        'target-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'target-match-id': '53_20252026_4830747',
        'target-external-id': '4830747',
        'allow-network': 'no',
        'allow-db-write': 'no',
        'allow-migration': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-parser-features': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
}

function assertInvalid(overrides, pattern) {
    const result = plan.validatePlanInput(validArgs(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

function withPatched(object, property, replacement, callback) {
    const original = object[property];
    object[property] = replacement;
    return Promise.resolve()
        .then(callback)
        .finally(() => {
            object[property] = original;
        });
}

test('valid input succeeds', () => {
    const result = plan.validatePlanInput(validArgs());
    assert.equal(result.ok, true);
    assert.equal(result.value.source, 'fotmob');
});

test('source missing fails', () => {
    assertInvalid({ source: '' }, /source=fotmob is required/);
});

test('source non-fotmob fails', () => {
    assertInvalid({ source: 'other' }, /source must be fotmob/);
});

test('current-version missing fails', () => {
    assertInvalid({ 'current-version': '' }, /current-version=fotmob_html_hyd_v1 is required/);
});

test('current-version not fotmob_html_hyd_v1 fails', () => {
    assertInvalid({ 'current-version': 'wrong' }, /current-version must be fotmob_html_hyd_v1/);
});

test('target-version missing fails', () => {
    assertInvalid({ 'target-version': '' }, /target-version=fotmob_pageprops_v2 is required/);
});

test('target-version not fotmob_pageprops_v2 fails', () => {
    assertInvalid({ 'target-version': 'wrong' }, /target-version must be fotmob_pageprops_v2/);
});

test('hash-strategy missing fails', () => {
    assertInvalid({ 'hash-strategy': '' }, /hash-strategy=stable_pageprops_payload_v1 is required/);
});

test('hash-strategy not stable_pageprops_payload_v1 fails', () => {
    assertInvalid({ 'hash-strategy': 'wrong' }, /hash-strategy must be stable_pageprops_payload_v1/);
});

test('target-match-id wrong fails', () => {
    assertInvalid({ 'target-match-id': 'wrong' }, /target-match-id must be 53_20252026_4830747/);
});

test('target-external-id wrong fails', () => {
    assertInvalid({ 'target-external-id': '1' }, /target-external-id must be 4830747/);
});

test('allow-network=yes blocked', () => {
    assertInvalid({ 'allow-network': 'yes' }, /allow-network=no is required/);
});

test('allow-db-write=yes blocked', () => {
    assertInvalid({ 'allow-db-write': 'yes' }, /allow-db-write=no is required/);
});

test('allow-migration=yes blocked', () => {
    assertInvalid({ 'allow-migration': 'yes' }, /allow-migration=no is required/);
});

test('allow-raw-match-data-write=yes blocked', () => {
    assertInvalid({ 'allow-raw-match-data-write': 'yes' }, /allow-raw-match-data-write=no is required/);
});

test('allow-parser-features=yes blocked', () => {
    assertInvalid({ 'allow-parser-features': 'yes' }, /allow-parser-features=no is required/);
});

test('allow-training=yes blocked', () => {
    assertInvalid({ 'allow-training': 'yes' }, /allow-training=no is required/);
});

test('allow-prediction=yes blocked', () => {
    assertInvalid({ 'allow-prediction': 'yes' }, /allow-prediction=no is required/);
});

test('execute=yes blocked', () => {
    assertInvalid({ execute: 'yes' }, /execute=yes is blocked/);
});

test('commit=yes blocked', () => {
    assertInvalid({ commit: 'yes' }, /commit=yes is blocked/);
});

test('rewrite-existing=yes blocked', () => {
    assertInvalid({ 'rewrite-existing': 'yes' }, /rewrite-existing=yes is blocked/);
});

test('drop-v1=yes blocked', () => {
    assertInvalid({ 'drop-v1': 'yes' }, /drop-v1=yes is blocked/);
});

test('alter-table=yes blocked', () => {
    assertInvalid({ 'alter-table': 'yes' }, /alter-table=yes is blocked/);
});

test('buildSchemaFindings detects unique(match_id)', () => {
    const findings = plan.buildSchemaFindings({
        constraints: [{ definition: 'UNIQUE (match_id)' }],
    });
    assert.equal(findings.raw_match_data_has_unique_match_id, 'true');
    assert.equal(findings.raw_match_data_allows_multi_version_per_match, 'false');
});

test('buildSchemaFindings detects unique(match_id,data_version)', () => {
    const findings = plan.buildSchemaFindings({
        constraints: [{ definition: 'UNIQUE (match_id, data_version)' }],
    });
    assert.equal(findings.raw_match_data_has_unique_match_id_data_version, 'true');
    assert.equal(findings.raw_match_data_allows_multi_version_per_match, 'true');
});

test('compareSchemaStrategies ranks unique(match_id,data_version)', () => {
    const strategies = plan.compareSchemaStrategies();
    assert.equal(strategies[0].strategy, 'unique_match_id_data_version');
    assert.equal(strategies[0].rank, 1);
});

test('compareSchemaStrategies documents new_versions_table tradeoff', () => {
    const strategy = plan.compareSchemaStrategies().find(item => item.strategy === 'new_versions_table');
    assert.ok(strategy);
    assert.ok(strategy.pros.length > 0);
    assert.ok(strategy.cons.length > 0);
});

test('recommended strategy does not overwrite v1', () => {
    const recommended = plan.buildRecommendedSchemaStrategy(
        plan.buildSchemaFindings({ constraints: [{ definition: 'UNIQUE (match_id)' }] })
    );
    assert.equal(recommended.strategy, 'unique_match_id_data_version');
    assert.equal(recommended.overwrite_v1_recommended, false);
});

test('write policy uses conflict target match_id,data_version', () => {
    assert.deepEqual(plan.buildVersionedWritePolicy().upsert_conflict_target, ['match_id', 'data_version']);
});

test('compatibility policy requires data_version filtering', () => {
    assert.equal(plan.buildCompatibilityPolicy().readers_must_filter_data_version, true);
    assert.equal(plan.buildCompatibilityPolicy().parser_must_branch_by_data_version, true);
});

test('rollback policy requires backup/preflight', () => {
    const policy = plan.buildRollbackPolicy();
    assert.equal(policy.pre_migration_backup_required, true);
    assert.equal(policy.rollback_plan_required, true);
    assert.equal(policy.no_execution_this_phase, true);
});

test('plan is planning_only=true', () => {
    const payload = plan.buildPagePropsV2ControlledWritePlan();
    assert.equal(payload.planning_only, true);
    assert.equal(payload.phase, 'PHASE5_21L2E_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING');
});

test('no fs write / mkdir', async () => {
    await withPatched(
        fs,
        'writeFileSync',
        () => {
            throw new Error('writeFileSync should not be called');
        },
        async () => {
            await withPatched(
                fs,
                'writeFile',
                () => {
                    throw new Error('writeFile should not be called');
                },
                async () => {
                    await withPatched(
                        fs,
                        'mkdir',
                        () => {
                            throw new Error('mkdir should not be called');
                        },
                        async () => {
                            const result = await plan.runCli(validArgs(), { output() {} });
                            assert.equal(result.status, 0);
                        }
                    );
                }
            );
        }
    );
});

test('no child_process spawn', async () => {
    await withPatched(
        childProcess,
        'spawn',
        () => {
            throw new Error('spawn should not be called');
        },
        async () => {
            await withPatched(
                childProcess,
                'exec',
                () => {
                    throw new Error('exec should not be called');
                },
                async () => {
                    await withPatched(
                        childProcess,
                        'execFile',
                        () => {
                            throw new Error('execFile should not be called');
                        },
                        async () => {
                            const result = await plan.runCli(validArgs(), { output() {} });
                            assert.equal(result.status, 0);
                        }
                    );
                }
            );
        }
    );
});

test('no network access', async () => {
    await withPatched(
        globalThis,
        'fetch',
        () => {
            throw new Error('fetch should not be called');
        },
        async () => {
            await withPatched(
                http,
                'request',
                () => {
                    throw new Error('http.request should not be called');
                },
                async () => {
                    await withPatched(
                        https,
                        'request',
                        () => {
                            throw new Error('https.request should not be called');
                        },
                        async () => {
                            const result = await plan.runCli(validArgs(), { output() {} });
                            assert.equal(result.status, 0);
                            assert.equal(result.payload.network_access_executed, false);
                        }
                    );
                }
            );
        }
    );
});

test('no DB write', () => {
    const payload = plan.buildPagePropsV2ControlledWritePlan();
    assert.equal(payload.db_write_executed, false);
    assert.equal(payload.raw_match_data_write_executed, false);
});

test('no migration execution', () => {
    const payload = plan.buildPagePropsV2ControlledWritePlan();
    assert.equal(payload.migration_executed, false);
    assert.equal(payload.recommended_schema_strategy.migration_execute_this_phase, false);
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no parser/features/training import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /require\([^)]*(parser|feature|train|predict)/i);
});
