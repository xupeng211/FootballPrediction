'use strict';

// lifecycle: permanent; D4C-only integration coverage against the disposable tmpfs compose database.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { Client } = require('pg');
const { createCanonicalObservation } = require('../../../src/infrastructure/odds_staging/contracts');
const { buildPersistencePlan } = require('../../../src/infrastructure/odds_staging/persistenceContracts');
const { HistoricalOddsStagingPersistenceRepository, PersistenceConflictError } = require('../../../src/infrastructure/odds_staging/persistenceRepository');
const { EphemeralPostgresAdapter, assertDatabaseFinalDefenses } = require('../../../scripts/test/odds_staging/ephemeral_postgres_adapter');
const { EphemeralDatabaseAuthorizationError, assertEphemeralConfig, authorizeEphemeralDatabase } = require('../../../scripts/test/odds_staging/ephemeral_authorizer');

const ROOT = path.resolve(__dirname, '../../..');
const config = {
    allow: process.env.ALLOW_EPHEMERAL_DB_TEST,
    confirmation: process.env.M3_D4C_EPHEMERAL_CONFIRMATION,
    host: process.env.M3_D4C_DB_HOST,
    port: Number(process.env.M3_D4C_DB_PORT),
    database: process.env.M3_D4C_DB_NAME,
    user: process.env.M3_D4C_DB_USER,
    password: process.env.M3_D4C_DB_PASSWORD,
};
let client;

function hash(char) { return char.repeat(64); }
function observation(selection) {
    return createCanonicalObservation({
        source_provider: 'm3-d4c-synthetic', source_url: 'synthetic://d4c', source_match_id: `fixture-${selection}`,
        competition: 'Synthetic League', season: '2099/2100', kickoff_at: '2099-08-16T19:00:00Z',
        home_team: 'Synthetic Home', away_team: 'Synthetic Away', bookmaker: 'FixtureBook', bookmaker_source_id: 'fixture-book',
        market: '1X2', selection, decimal_odds: selection === 'home' ? 2.1 : selection === 'draw' ? 3.4 : 4.2,
        snapshot_type: 'unknown', source_observed_at: null, captured_at: null, capture_time_status: 'unknown', source_timezone: 'UTC',
        raw_sha256: hash(selection === 'home' ? 'a' : selection === 'draw' ? 'b' : 'c'), raw_record_locator: `synthetic:row=${selection === 'home' ? 2 : selection === 'draw' ? 3 : 4}`,
        adapter: 'm3-d4c-fixture', adapter_version: '1.0.0', extraction_method: 'synthetic_fixture', provenance_status: 'declared', ingested_at: '2099-08-01T00:00:00Z',
        match_link: { status: 'matched', method: 'historical_identity', candidate_ids: ['synthetic-candidate-1'], matched_id: 'synthetic-candidate-1', evidence: { fixture: true } },
        kickoff_time_interpretation_evidence: { timezone: 'UTC', method: 'synthetic' },
    });
}

function resultFixture() {
    const accepted = ['home', 'draw', 'away'].map(observation);
    return {
        normalized_manifest: { schema_version: 'odds-source-manifest/v1', source_provider: 'm3-d4c-synthetic', raw_sha256: hash('d'), competition: 'Synthetic League', season: '2099/2100', raw_path: 'synthetic/d4c.csv' },
        accepted_observations: accepted,
        quarantine: [{ schema_version: 'odds-quarantine/v1', source_provider: 'm3-d4c-synthetic', raw_sha256: hash('d'), raw_record_locator: 'synthetic:row=5', adapter: 'm3-d4c-fixture', adapter_version: '1.0.0', reasons: ['kickoff_conflict_15m'], evidence: { parsed_fields: { idempotency_key: hash('e') }, synthetic: true } }],
        summary: { accepted_count: 3, quarantine_count: 1 },
    };
}

function plan() { return buildPersistencePlan(resultFixture(), { runMode: 'controlled_write', candidate_business_hash: hash('f'), pipeline_code_sha: '1'.repeat(40) }); }
async function count(table) { return Number((await client.query(`SELECT COUNT(*)::int AS count FROM ${table}`)).rows[0].count); }
async function runAudit(runKey) {
    return (await client.query('SELECT status, actual_accepted_count, actual_quarantine_count, duplicate_count, completed_at, updated_at, metadata, pipeline_code_sha, manifest_hash, candidate_business_hash FROM odds_historical_import_runs WHERE run_key = $1', [runKey])).rows[0];
}
async function execute(inputPlan, options = {}) {
    const adapter = options.adapter || new EphemeralPostgresAdapter(client);
    const repository = new HistoricalOddsStagingPersistenceRepository({ adapter, authorizeWrite: async () => authorizeEphemeralDatabase({ config, client }) });
    return repository.execute(inputPlan, { authorization: 'write_authorized' });
}

test.before(async () => {
    assertEphemeralConfig(config);
    client = new Client({ host: config.host, port: config.port, database: config.database, user: config.user, password: config.password });
    await client.connect();
    await authorizeEphemeralDatabase({ config, client });
    const v268 = fs.readFileSync(path.join(ROOT, 'database/migrations/V26.8__create_odds_historical_staging_contract.sql'), 'utf8');
    await client.query(v268);
    await client.query(v268); // Direct DDL harness check: V26.8's IF NOT EXISTS path is harmless on retry.
    await client.query(fs.readFileSync(path.join(ROOT, 'database/migrations/V26.9__add_odds_historical_observation_fingerprint.sql'), 'utf8'));
});
test.after(async () => { await client?.end(); });

test('隔离预检、migration 与 schema introspection 通过', async () => {
    const identity = await client.query('SELECT current_database() AS database_name, inet_server_addr()::text AS address');
    assert.ok(identity.rows[0].database_name.startsWith('fp_m3_d4c_ephemeral_'));
    assert.equal(config.host, 'ephemeral-postgres');
    assert.ok(identity.rows[0].address === null || /^172\./.test(identity.rows[0].address));
    const tables = await client.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'odds_historical_%' ORDER BY table_name");
    assert.deepEqual(tables.rows.map(row => row.table_name), ['odds_historical_import_runs', 'odds_historical_quarantine', 'odds_historical_source_files', 'odds_historical_staging_observations']);
    const columns = await client.query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'odds_historical_staging_observations'");
    assert.equal(columns.rows.find(row => row.column_name === 'kickoff_at').data_type, 'timestamp with time zone');
    assert.ok(columns.rows.some(row => row.column_name === 'business_fingerprint'));
    const matchesFk = await client.query("SELECT 1 FROM pg_constraint WHERE conrelid = 'odds_historical_staging_observations'::regclass AND contype = 'f' AND confrelid = to_regclass('public.matches')");
    assert.equal(matchesFk.rowCount, 0);
});

test('authorizer 拒绝通过完整 repository 调用链保持零 transaction/SQL', async () => {
    for (const rejected of [
        { ...config, confirmation: 'wrong' }, { ...config, database: 'football_prediction_db_dev' },
        { ...config, host: 'host.docker.internal' }, { ...config, allow: undefined },
    ]) {
        const calls = { transaction: 0, query: 0, failure: 0 };
        const repository = new HistoricalOddsStagingPersistenceRepository({
            adapter: { runInTransaction: async () => { calls.transaction += 1; }, recordRunFailure: async () => { calls.failure += 1; } },
            authorizeWrite: async () => { calls.query += 0; assertEphemeralConfig(rejected); },
        });
        await assert.rejects(repository.execute(plan(), { authorization: 'write_authorized' }), EphemeralDatabaseAuthorizationError);
        assert.deepEqual(calls, { transaction: 0, query: 0, failure: 0 });
    }
});

test('首次受控写入、相同重跑 no-op 与 quarantine 隔离', async () => {
    const first = await execute(plan());
    assert.deepEqual(first, { status: 'persisted', accepted_count: 3, quarantine_count: 1, duplicate_count: 0 });
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], [1, 1, 3, 1]);
    const beforeAudit = await runAudit(plan().run.run_key);
    const repeat = await execute(plan());
    assert.equal(repeat.accepted_count, 0);
    assert.equal(repeat.duplicate_count, 3);
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], [1, 1, 3, 1]);
    assert.deepEqual(await runAudit(plan().run.run_key), beforeAudit);
    const accepted = await client.query("SELECT COUNT(*)::int AS count FROM odds_historical_staging_observations WHERE idempotency_key = $1", [plan().quarantine[0].idempotency_key]);
    assert.equal(accepted.rows[0].count, 0);
});

test('divergent duplicate 与注入 transaction failure 均 rollback 且不覆盖', async () => {
    const before = [await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')];
    const conflict = plan();
    conflict.accepted[0].observation.decimal_odds = 9.9;
    conflict.accepted[0].business_fingerprint = hash('9');
    await assert.rejects(execute(conflict), PersistenceConflictError);
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], before);
    const divergentRun = plan();
    divergentRun.run.manifest_hash = hash('0');
    await assert.rejects(execute(divergentRun), PersistenceConflictError);
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], before);
    const divergentQuarantine = plan();
    divergentQuarantine.quarantine[0].source_payload.synthetic = 'changed';
    await assert.rejects(execute(divergentQuarantine), PersistenceConflictError);
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], before);
    const altered = plan();
    altered.run.run_key = hash('7'); altered.source_file.import_run_key = hash('7');
    await assert.rejects(execute(altered, { adapter: new EphemeralPostgresAdapter(client, { failAfterSource: true }) }), /injected transaction failure/);
    assert.deepEqual([await count('odds_historical_import_runs'), await count('odds_historical_source_files'), await count('odds_historical_staging_observations'), await count('odds_historical_quarantine')], before);
});

test('数据库唯一与 check 约束是 repository 之外的最终防线', async () => {
    await assertDatabaseFinalDefenses(client, plan().accepted[0], hash('8'));
});
