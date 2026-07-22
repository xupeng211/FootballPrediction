'use strict';

// lifecycle: permanent；纯单元/静态合同测试，不创建数据库连接或执行 SQL migration。

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { createCanonicalObservation } = require('../../src/infrastructure/odds_staging/contracts');
const { persistStagingResult, planStagingPersistence } = require('../../src/infrastructure/odds_staging/pipeline');
const { buildPersistencePlan, mapQuarantineRecord } = require('../../src/infrastructure/odds_staging/persistenceContracts');
const {
    HistoricalOddsStagingPersistenceRepository,
    PersistenceConflictError,
    PersistenceWriteDisabledError,
} = require('../../src/infrastructure/odds_staging/persistenceRepository');

const ROOT = path.resolve(__dirname, '../..');
const MIGRATION = path.join(ROOT, 'database/migrations/V26.8__create_odds_historical_staging_contract.sql');

function resultFixture() {
    const accepted = createCanonicalObservation({
        source_provider: 'football-data-historical', source_url: 'git+repository://fixture', source_match_id: null,
        competition: 'Premier League', season: '2024/2025', kickoff_at: '2024-08-16T19:00:00Z',
        home_team: 'Manchester United', away_team: 'Fulham', bookmaker: 'Bet365', bookmaker_source_id: 'B365',
        market: '1X2', selection: 'home', decimal_odds: 2.1, snapshot_type: 'unknown', source_observed_at: null,
        captured_at: null, capture_time_status: 'unknown', source_timezone: 'unknown', raw_sha256: 'a'.repeat(64),
        raw_record_locator: 'csv:row=2', adapter: 'football-data-csv', adapter_version: '1.2.0',
        extraction_method: 'football_data_explicit_column', provenance_status: 'declared', ingested_at: '2026-07-22T00:00:00Z',
        match_link: { status: 'matched', method: 'historical_identity', candidate_ids: ['candidate-1'], matched_id: 'candidate-1', evidence: {} },
        kickoff_time_interpretation_evidence: { timezone: 'Europe/London', method: 'source_local_calendar_time' },
    });
    const quarantine = {
        schema_version: 'odds-quarantine/v1', source_provider: accepted.source_provider, source_match_id: null,
        raw_sha256: accepted.raw_sha256, raw_record_locator: 'csv:row=3', adapter: accepted.adapter,
        adapter_version: accepted.adapter_version, reasons: ['kickoff_conflict_15m'],
        evidence: { parsed_fields: { idempotency_key: 'b'.repeat(64) }, match_link: { candidate_ids: ['candidate-2'] } },
    };
    return {
        normalized_manifest: { schema_version: 'odds-source-manifest/v1', source_provider: accepted.source_provider, raw_sha256: accepted.raw_sha256 },
        accepted_observations: [accepted], quarantine: [quarantine],
        summary: { accepted_count: 1, quarantine_count: 1 },
    };
}

test('migration 是纯 DDL 静态合同：accepted/quarantine 分离、unique、TIMESTAMPTZ 且无数据 DML', () => {
    const sql = fs.readFileSync(MIGRATION, 'utf8');
    for (const table of ['odds_historical_import_runs', 'odds_historical_source_files', 'odds_historical_staging_observations', 'odds_historical_quarantine']) {
        assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
    }
    assert.match(sql, /idempotency_key CHAR\(64\) NOT NULL UNIQUE/);
    assert.match(sql, /content_hash CHAR\(64\) NOT NULL/);
    assert.match(sql, /decimal_odds NUMERIC\(12, 6\) NOT NULL CHECK \(decimal_odds > 1\)/);
    assert.match(sql, /TIMESTAMPTZ/);
    assert.doesNotMatch(sql, /\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b|DROP\s+.*CASCADE/i);
});

test('当前 canonical observation 与 quarantine 都可无损映射，#1797 identity evidence 保留且 FK fail closed', () => {
    const plan = buildPersistencePlan(resultFixture(), { candidate_business_hash: 'c'.repeat(64) });
    assert.equal(plan.persistence_status, 'not_persisted');
    assert.equal(plan.accepted[0].candidate_match_id, 'candidate-1');
    assert.equal(plan.accepted[0].canonical_match_id, null);
    assert.equal(plan.accepted[0].canonical_match_fk_status, 'unverified_database_fk');
    assert.equal(plan.accepted[0].observation.kickoff_time_interpretation_evidence.timezone, 'Europe/London');
    assert.deepEqual(plan.quarantine[0].reason_codes, ['kickoff_conflict_15m']);
    assert.equal(plan.quarantine[0].source_row_number, 3);
    assert.ok(plan.quarantine[0].quarantine_key);
});

test('src odds staging 不反向依赖 scripts/ops', () => {
    const sourceDirectory = path.join(ROOT, 'src/infrastructure/odds_staging');
    for (const filename of fs.readdirSync(sourceDirectory).filter(filename => filename.endsWith('.js'))) {
        assert.doesNotMatch(fs.readFileSync(path.join(sourceDirectory, filename), 'utf8'), /scripts\/ops\//);
    }
});

test('dry-run 明确不持久化，且不会调用 authorizer 或 adapter', async () => {
    let authorizerCalls = 0;
    let adapterCalls = 0;
    const repository = new HistoricalOddsStagingPersistenceRepository({
        adapter: { runInTransaction: async () => { adapterCalls += 1; } },
        authorizeWrite: async () => { authorizerCalls += 1; },
    });
    const plan = repository.plan(resultFixture());
    assert.equal(plan.run.mode, 'dry_run');
    assert.deepEqual(await repository.execute(plan), { status: 'not_persisted', reason: 'dry_run', run_key: plan.run.run_key });
    assert.equal(authorizerCalls, 0);
    assert.equal(adapterCalls, 0);
    assert.deepEqual(await persistStagingResult(resultFixture(), repository), { status: 'not_persisted', reason: 'dry_run', run_key: plan.run.run_key });
    assert.equal(planStagingPersistence(resultFixture(), repository).run.run_key, plan.run.run_key);
});

test('controlled write 缺少 adapter 或 authorizer，以及 dry-run plan 的 write authorization，均 fail closed', async () => {
    const repository = new HistoricalOddsStagingPersistenceRepository();
    const controlledPlan = repository.plan(resultFixture(), { runMode: 'controlled_write' });
    await assert.rejects(repository.execute(controlledPlan, { authorization: 'write_authorized' }), PersistenceWriteDisabledError);
    const adapterOnly = new HistoricalOddsStagingPersistenceRepository({ adapter: { runInTransaction: async () => {} } });
    await assert.rejects(adapterOnly.execute(controlledPlan, { authorization: 'write_authorized' }), PersistenceWriteDisabledError);
    await assert.rejects(repository.execute(repository.plan(resultFixture()), { authorization: 'write_authorized' }), PersistenceWriteDisabledError);
});

test('authorizer 拒绝时没有 adapter、failure 或 transaction 调用', async () => {
    const calls = { transaction: 0, failure: 0, writes: 0 };
    const repository = new HistoricalOddsStagingPersistenceRepository({
        adapter: {
            runInTransaction: async () => { calls.transaction += 1; },
            recordRunFailure: async () => { calls.failure += 1; },
        },
        authorizeWrite: async () => { throw new Error('authorization denied'); },
    });
    const plan = repository.plan(resultFixture(), { runMode: 'controlled_write' });
    await assert.rejects(repository.execute(plan, { authorization: 'write_authorized' }), /authorization denied/);
    assert.deepEqual(calls, { transaction: 0, failure: 0, writes: 0 });
});

test('controlled write 保持 mode、identical duplicate no-op；divergent conflict fail closed', async () => {
    const writes = [];
    let createdRun = null;
    const adapter = {
        async runInTransaction(callback) {
            return callback({
                findAcceptedByIdempotencyKey: async () => [{ idempotency_key: 'same', business_fingerprint: 'same' }],
                createImportRun: async run => { createdRun = run; writes.push('run'); }, registerSourceFile: async () => writes.push('source'),
                insertAcceptedObservations: async rows => writes.push(['accepted', rows.length]),
                insertQuarantineRecords: async rows => writes.push(['quarantine', rows.length]),
                markRunCompleted: async () => writes.push('completed'),
            });
        },
    };
    const repository = new HistoricalOddsStagingPersistenceRepository({ adapter, authorizeWrite: async () => {} });
    const plan = buildPersistencePlan(resultFixture(), { runMode: 'controlled_write' });
    plan.accepted[0].idempotency_key = 'same'; plan.accepted[0].business_fingerprint = 'same';
    const result = await repository.execute(plan, { authorization: 'write_authorized' });
    assert.equal(result.duplicate_count, 1);
    assert.ok(!writes.some(item => Array.isArray(item) && item[0] === 'accepted'));

    assert.ok(writes.includes('run'));
    assert.equal(createdRun.mode, 'controlled_write');
    const conflictRepository = new HistoricalOddsStagingPersistenceRepository({ adapter: { ...adapter, runInTransaction: callback => callback({
        findAcceptedByIdempotencyKey: async () => [{ idempotency_key: 'same', business_fingerprint: 'different' }],
    }) }, authorizeWrite: async () => {} });
    await assert.rejects(conflictRepository.execute(plan, { authorization: 'write_authorized' }), PersistenceConflictError);
});

test('transaction error 原样传播，不触发事务外 failure write 或 completed 伪装', async () => {
    let failureCalls = 0;
    const repository = new HistoricalOddsStagingPersistenceRepository({
        adapter: {
            runInTransaction: async () => { throw new Error('transaction failed'); },
            recordRunFailure: async () => { failureCalls += 1; },
        },
        authorizeWrite: async () => {},
    });
    const plan = repository.plan(resultFixture(), { runMode: 'controlled_write' });
    await assert.rejects(repository.execute(plan, { authorization: 'write_authorized' }), /transaction failed/);
    assert.equal(failureCalls, 0);
});

test('quarantine reason 缺失被拒绝，避免空隔离记录伪装成功', () => {
    assert.throws(() => mapQuarantineRecord({ reasons: [] }, 'a'.repeat(64)), /at least one reason/);
});
