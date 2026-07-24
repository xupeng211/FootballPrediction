'use strict';

// lifecycle: permanent；D4E 固定合成样本与双重授权的纯行为测试。
const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { buildPersistencePlan } = require('../../src/infrastructure/odds_staging/persistenceContracts');
const { buildD4ESyntheticResult } = require('../../src/infrastructure/odds_staging/d4eSyntheticFixture');
const { AUTHORIZATION_PHRASE, D4EAuthorizationError, assertD4EConfig, authorizeD4EWrite } = require('../../scripts/ops/odds_staging/m3_d4e_authorizer');

const ROOT = path.resolve(__dirname, '../..');
const config = Object.freeze({
    ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE: '1', M3_D4E_AUTHORIZATION_PHRASE: AUTHORIZATION_PHRASE,
    M3_D4E_SAMPLE_KIND: 'synthetic', M3_D4E_DATABASE: 'fp_m3_persistent_sandbox', M3_D4E_PROJECT: 'fp_m3_persistent_sandbox',
    M3_D4E_SERVICE: 'm3-persistent-postgres', M3_D4E_WRITER: 'fp_m3_sandbox_writer', M3_D4E_PRODUCTION: 'false', M3_D4E_STAGING: 'false', PGHOST: 'm3-persistent-postgres',
});

test('D4E fixture is deterministic and covers 6 accepted plus 3 natural quarantines', () => {
    const one = buildD4ESyntheticResult(ROOT); const two = buildD4ESyntheticResult(ROOT);
    assert.equal(one.fixture.rows.length, 9); assert.equal(one.fixture.content_hash, two.fixture.content_hash);
    assert.equal(one.accepted_observations.length, 6); assert.equal(one.quarantine.length, 3);
    assert.deepEqual(one.accepted_observations.map(row => `${row.snapshot_type}:${row.selection}`).sort(), ['closing:away','closing:draw','closing:home','opening:away','opening:draw','opening:home']);
    assert.ok(one.accepted_observations.every(row => row.decimal_odds > 1 && row.match_link.matched_id === 'm3-d4e-local-candidate-001'));
    assert.ok(one.quarantine.some(row => row.reasons.includes('decimal_odds_invalid')));
    assert.ok(one.quarantine.some(row => row.reasons.includes('source_observed_at_invalid')));
    assert.ok(one.quarantine.some(row => row.reasons.includes('match_link_ambiguous')));
    const plan = buildPersistencePlan(one, { runMode: 'controlled_write', manifest_hash: 'a'.repeat(64), candidate_business_hash: 'b'.repeat(64), pipeline_code_sha: 'c'.repeat(40) });
    assert.equal(plan.source_file.row_count, 9); assert.equal(plan.accepted.length, 6); assert.equal(plan.quarantine.length, 3);
    assert.ok(plan.accepted.every(row => row.canonical_match_id === null && row.canonical_match_fk_status === 'unverified_database_fk' && row.business_fingerprint));
});

test('D4E authorizer rejects every identity and operation escape hatch before transactions', async () => {
    assert.doesNotThrow(() => assertD4EConfig(config));
    await assert.doesNotReject(authorizeD4EWrite({ tables: ['odds_historical_import_runs','odds_historical_source_files','odds_historical_staging_observations','odds_historical_quarantine'], operations: ['INSERT','UPDATE'] }, config));
    for (const changed of [
        { ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE: undefined }, { M3_D4E_AUTHORIZATION_PHRASE: 'wrong' }, { M3_D4E_SAMPLE_KIND: 'real' },
        { M3_D4E_DATABASE: 'football_db' }, { M3_D4E_WRITER: 'fp_m3_sandbox_owner' }, { M3_D4E_PRODUCTION: 'true' }, { PGHOST: 'localhost' },
    ]) assert.throws(() => assertD4EConfig({ ...config, ...changed }), D4EAuthorizationError);
    await assert.rejects(authorizeD4EWrite({ tables: ['matches'], operations: ['INSERT'] }, config), D4EAuthorizationError);
});
