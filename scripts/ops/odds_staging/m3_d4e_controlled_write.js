'use strict';

// lifecycle: permanent；固定本地 sandbox 的 D4E 合成写入入口；不接受数据库、表名或样本路径参数。

const path = require('node:path');
const { Client } = require('pg');
const { sha256Text, stableStringify } = require('../../../src/infrastructure/odds_staging/contracts');
const { buildPersistencePlan } = require('../../../src/infrastructure/odds_staging/persistenceContracts');
const { HistoricalOddsStagingPersistenceRepository } = require('../../../src/infrastructure/odds_staging/persistenceRepository');
const { buildD4ESyntheticResult } = require('../../../src/infrastructure/odds_staging/d4eSyntheticFixture');
const { assertD4EConfig, authorizeD4EWrite, DATABASE, WRITER } = require('./m3_d4e_authorizer');
const { M3D4EPersistentAdapter } = require('./m3_d4e_persistent_adapter');

const ROOT = path.resolve(__dirname, '../../..');
const action = process.argv[2] || 'preflight';
if (!['preflight', 'write', 'replay', 'accepted-conflict', 'quarantine-conflict'].includes(action)) throw new Error('usage: m3_d4e_controlled_write.js {preflight|write|replay|accepted-conflict|quarantine-conflict}');

function counts(client) { return client.query("SELECT (SELECT count(*)::int FROM odds_historical_import_runs) AS runs,(SELECT count(*)::int FROM odds_historical_source_files) AS sources,(SELECT count(*)::int FROM odds_historical_staging_observations) AS accepted,(SELECT count(*)::int FROM odds_historical_quarantine) AS quarantine").then(result => result.rows[0]); }
function sameCounts(left, right) { return ['runs', 'sources', 'accepted', 'quarantine'].every(key => Number(left[key]) === Number(right[key])); }
function planFor(result) { const manifest_hash = sha256Text(stableStringify(result.normalized_manifest)); return buildPersistencePlan(result, { runMode: 'controlled_write', manifest_hash, candidate_business_hash: sha256Text('m3-d4e-synthetic-candidate/v1'), pipeline_code_sha: process.env.M3_D4E_PIPELINE_CODE_SHA || 'd4e-local-implementation' }); }

async function resolvePersistedD4EPlan(client, result) {
    const current = planFor(result); const run = current.run; const candidates = await client.query("SELECT * FROM odds_historical_import_runs WHERE status='completed' AND source_type=$1 AND mode=$2 AND pipeline_version=$3 AND manifest_hash=$4 AND candidate_business_hash=$5 AND expected_accepted_count=$6 AND expected_quarantine_count=$7 AND metadata=$8::jsonb", [run.source_type,run.mode,run.pipeline_version,run.manifest_hash,run.candidate_business_hash,run.expected_accepted_count,run.expected_quarantine_count,JSON.stringify(run.metadata)]);
    if (candidates.rowCount !== 1) throw new Error('D4E persisted identity must resolve exactly one completed run');
    const persisted = candidates.rows[0]; if (!persisted.pipeline_code_sha) throw new Error('D4E persisted run has no pipeline_code_sha');
    const plan = buildPersistencePlan(result,{runMode:'controlled_write',manifest_hash:run.manifest_hash,candidate_business_hash:run.candidate_business_hash,pipeline_code_sha:persisted.pipeline_code_sha});
    if (plan.run.run_key !== persisted.run_key) throw new Error('D4E rebuilt run key does not equal persisted run key');
    const sources=await client.query('SELECT * FROM odds_historical_source_files WHERE import_run_id=$1',[persisted.id]); if(sources.rowCount!==1) throw new Error('D4E persisted identity must resolve exactly one source');
    const source=sources.rows[0]; if(source.content_hash!==plan.source_file.content_hash||source.logical_path!==plan.source_file.logical_path||Number(source.row_count)!==plan.source_file.row_count)throw new Error('D4E persisted source identity mismatch');
    const accepted=await client.query('SELECT idempotency_key,business_fingerprint FROM odds_historical_staging_observations WHERE import_run_id=$1',[persisted.id]); const map=new Map(accepted.rows.map(r=>[r.idempotency_key,r.business_fingerprint.trim()])); if(accepted.rowCount!==6||plan.accepted.some(r=>map.get(r.idempotency_key)!==r.business_fingerprint))throw new Error('D4E persisted accepted identity mismatch');
    const quarantine=await client.query('SELECT quarantine_key,source_payload FROM odds_historical_quarantine WHERE import_run_id=$1',[persisted.id]); if(quarantine.rowCount!==3)throw new Error('D4E persisted quarantine identity mismatch');
    return { plan, persisted, probe_executor_code_sha: process.env.M3_D4E_PIPELINE_CODE_SHA, source, quarantine };
}

async function assertIdentity(client) {
    const identity = await client.query('SELECT current_database() AS database,current_user, current_schema() AS schema, current_setting(\'server_version_num\') AS version');
    const row = identity.rows[0];
    if (row.database !== DATABASE || row.current_user !== WRITER || row.schema !== 'public' || !String(row.version).startsWith('15')) throw new Error('D4E database identity preflight failed');
    // The migration ledger is intentionally owner/migrator-only. Its two-row/checksum
    // verification is performed by the fixed sandbox status/plan commands before this
    // writer process starts; granting writer ledger SELECT would widen its contract.
    const matchesFk = await client.query("SELECT count(*)::int AS count FROM pg_constraint WHERE conrelid='odds_historical_staging_observations'::regclass AND contype='f' AND confrelid=to_regclass('public.matches')");
    if (matchesFk.rows[0].count !== 0) throw new Error('D4E matches FK preflight failed');
    return row;
}

async function main() {
    assertD4EConfig(process.env);
    const client = new Client({ host: process.env.PGHOST, port: 5432, database: DATABASE, user: WRITER, password: process.env.M3_SANDBOX_WRITER_PASSWORD, ssl: false });
    await client.connect();
    try {
        const identity = await assertIdentity(client);
        const before = await counts(client);
        const result = buildD4ESyntheticResult(ROOT);
        let plan = planFor(result);
        if (action === 'preflight') {
            console.log(JSON.stringify({ status: 'preflight_ok', identity, fixture_hash: result.fixture.content_hash, row_count: result.fixture.rows.length, counts: before, run_key: plan.run.run_key }));
            return;
        }
        if (action !== 'write') { const resolved=await resolvePersistedD4EPlan(client,result); plan=resolved.plan; }
        if (action === 'write' && !sameCounts(before,{runs:0,sources:0,accepted:0,quarantine:0})) throw new Error('D4E write requires empty business tables');
        const repository = new HistoricalOddsStagingPersistenceRepository({ adapter: new M3D4EPersistentAdapter(client), authorizeWrite: request => authorizeD4EWrite(request, process.env) });
        if (action === 'accepted-conflict') {
            plan.accepted[0].observation.decimal_odds = 9.99; plan.accepted[0].business_fingerprint = sha256Text('m3-d4e-divergent-accepted');
        }
        if (action === 'quarantine-conflict') {
            plan.quarantine[0].source_payload.divergent_probe = true;
        }
        try {
            const writeResult = await repository.execute(plan, { authorization: 'write_authorized' });
            const after = await counts(client);
            console.log(JSON.stringify({ status: 'ok', action, write_result: writeResult, before, after, fixture_hash: result.fixture.content_hash, run_key: plan.run.run_key }));
        } catch (error) {
            const after = await counts(client);
            if (['accepted-conflict', 'quarantine-conflict'].includes(action) && error.code === 'PERSISTENCE_CONFLICT' && sameCounts(before, after)) {
                console.log(JSON.stringify({ status: 'conflict_rolled_back', code: error.code, conflict_scope: action === 'accepted-conflict' ? 'accepted' : 'quarantine', conflict_reason: action === 'accepted-conflict' ? 'divergent accepted/idempotency conflict' : 'divergent quarantine conflict', before, after, run_key: plan.run.run_key })); return;
            }
            throw error;
        }
    } finally { await client.end(); }
}
main().catch(error => { console.error(`D4E_ERROR code=${error.code || 'UNEXPECTED'} message=${error.message}`); process.exitCode = 1; });
