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
const ACTIONS = new Set(['preflight', 'write', 'replay', 'accepted-conflict', 'quarantine-conflict']);

function counts(client) { return client.query("SELECT (SELECT count(*)::int FROM odds_historical_import_runs) AS runs,(SELECT count(*)::int FROM odds_historical_source_files) AS sources,(SELECT count(*)::int FROM odds_historical_staging_observations) AS accepted,(SELECT count(*)::int FROM odds_historical_quarantine) AS quarantine").then(result => result.rows[0]); }
function sameCounts(left, right) { return ['runs', 'sources', 'accepted', 'quarantine'].every(key => Number(left[key]) === Number(right[key])); }
function planFor(result, pipelineCodeSha = process.env.M3_D4E_PIPELINE_CODE_SHA || 'd4e-local-implementation') { const manifest_hash = sha256Text(stableStringify(result.normalized_manifest)); return buildPersistencePlan(result, { runMode: 'controlled_write', manifest_hash, candidate_business_hash: sha256Text('m3-d4e-synthetic-candidate/v1'), pipeline_code_sha: pipelineCodeSha }); }
const sameJson = (left, right) => stableStringify(left) === stableStringify(right);
function fail(message) { throw new Error(`D4E persisted identity mismatch: ${message}`); }
function mapBy(rows, key) { return new Map(rows.map(row => [row[key], row])); }
function assertExactKeys(expected, actual, key, label) {
    const expectedKeys = new Set(expected.map(row => row[key])); const actualKeys = new Set(actual.map(row => row[key]));
    if (expectedKeys.size !== expected.length || actualKeys.size !== actual.length || expectedKeys.size !== actualKeys.size || [...expectedKeys].some(value => !actualKeys.has(value))) fail(`${label} key set`);
}

// eslint-disable-next-line complexity -- each branch is a separate fail-closed persisted-identity field check.
async function resolvePersistedD4EPlan(client, result) {
    const current = planFor(result); const run = current.run;
    const candidates = await client.query("SELECT * FROM odds_historical_import_runs WHERE status='completed' AND source_type=$1 AND mode=$2 AND pipeline_version=$3 AND manifest_hash=$4 AND candidate_business_hash=$5 AND expected_accepted_count=$6 AND expected_quarantine_count=$7 AND metadata=$8::jsonb", [run.source_type,run.mode,run.pipeline_version,run.manifest_hash,run.candidate_business_hash,run.expected_accepted_count,run.expected_quarantine_count,JSON.stringify(run.metadata)]);
    if (candidates.rowCount !== 1) fail('candidate run count');
    const persisted = candidates.rows[0]; if (!persisted.pipeline_code_sha) fail('missing pipeline_code_sha');
    const plan = planFor(result, persisted.pipeline_code_sha);
    for (const field of ['run_key', 'source_type', 'mode', 'pipeline_version', 'pipeline_code_sha', 'manifest_hash', 'candidate_business_hash', 'expected_accepted_count', 'expected_quarantine_count']) if (String(persisted[field]) !== String(plan.run[field])) fail(`run.${field}`);
    if (!sameJson(persisted.metadata, plan.run.metadata)) fail('run.metadata');
    const sources=await client.query('SELECT * FROM odds_historical_source_files WHERE import_run_id=$1',[persisted.id]); if(sources.rowCount!==1) fail('source count');
    const source=sources.rows[0]; const plannedSource=plan.source_file;
    for (const field of ['source_provider','logical_path','content_hash','hash_algorithm','manifest_hash','competition','season']) if (String(source[field] ?? '') !== String(plannedSource[field] ?? '')) fail(`source.${field}`);
    if (Number(source.row_count)!==Number(plannedSource.row_count) || !sameJson(source.provenance, plannedSource.provenance)) fail('source row_count/provenance');
    const accepted=await client.query('SELECT import_run_id,source_file_id,source_row_number,idempotency_key,canonical_match_id,candidate_match_id,canonical_match_fk_status,business_fingerprint FROM odds_historical_staging_observations WHERE import_run_id=$1',[persisted.id]);
    if (accepted.rowCount !== 6 || plan.accepted.length !== 6) fail('accepted count'); assertExactKeys(plan.accepted, accepted.rows, 'idempotency_key', 'accepted');
    const acceptedByKey=mapBy(accepted.rows,'idempotency_key'); for (const row of plan.accepted) { const prior=acceptedByKey.get(row.idempotency_key); if (String(prior.import_run_id)!==String(persisted.id)||String(prior.source_file_id)!==String(source.id)||Number(prior.source_row_number)!==Number(row.source_row_number)||prior.canonical_match_id !== null||prior.candidate_match_id!==row.candidate_match_id||prior.canonical_match_fk_status!==row.canonical_match_fk_status||String(prior.business_fingerprint).trim()!==row.business_fingerprint) fail('accepted row'); }
    const quarantine=await client.query('SELECT import_run_id,source_file_id,source_row_number,quarantine_key,idempotency_key,reason_codes,reason_detail,historical_match_identity,source_payload,resolution_status FROM odds_historical_quarantine WHERE import_run_id=$1',[persisted.id]);
    if (quarantine.rowCount !== 3 || plan.quarantine.length !== 3) fail('quarantine count'); assertExactKeys(plan.quarantine, quarantine.rows, 'quarantine_key', 'quarantine');
    const quarantineByKey=mapBy(quarantine.rows,'quarantine_key'); for (const row of plan.quarantine) { const prior=quarantineByKey.get(row.quarantine_key); if (String(prior.import_run_id)!==String(persisted.id)||String(prior.source_file_id)!==String(source.id)||Number(prior.source_row_number)!==Number(row.source_row_number)||prior.idempotency_key!==row.idempotency_key||!sameJson(prior.reason_codes,row.reason_codes)||!sameJson(prior.reason_detail,row.reason_detail)||!sameJson(prior.historical_match_identity,row.historical_match_identity)||!sameJson(prior.source_payload,row.source_payload)||prior.resolution_status!==row.resolution_status) fail('quarantine row'); }
    return { plan, persisted, probe_executor_code_sha: process.env.M3_D4E_PIPELINE_CODE_SHA, source, accepted, quarantine };
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

// eslint-disable-next-line complexity -- action routing keeps each fixed D4E operation explicit and non-generic.
async function main() {
    const action = process.argv[2] || 'preflight'; if (!ACTIONS.has(action)) throw new Error('usage: m3_d4e_controlled_write.js {preflight|write|replay|accepted-conflict|quarantine-conflict}');
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
        let resolved = null; if (action !== 'write') { resolved=await resolvePersistedD4EPlan(client,result); plan=resolved.plan; }
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
            console.log(JSON.stringify({ status: 'ok', action, write_result: writeResult, before, after, fixture_hash: result.fixture.content_hash, persisted_run_key: resolved?.persisted.run_key || plan.run.run_key, rebuilt_run_key: plan.run.run_key, import_pipeline_code_sha: plan.run.pipeline_code_sha, probe_executor_code_sha: process.env.M3_D4E_PIPELINE_CODE_SHA }));
        } catch (error) {
            const after = await counts(client);
            const expectedScope = action === 'accepted-conflict' ? 'accepted' : action === 'quarantine-conflict' ? 'quarantine' : null;
            if (expectedScope && error.code === 'PERSISTENCE_CONFLICT' && error.conflict_scope === expectedScope && error.conflict_key_hash && sameCounts(before, after)) {
                console.log(JSON.stringify({ status: 'conflict_rolled_back', action, code: error.code, conflict_scope: error.conflict_scope, conflict_key_hash: error.conflict_key_hash, conflict_reason: error.conflict_reason, before, after, persisted_run_key: resolved?.persisted.run_key, rebuilt_run_key: plan.run.run_key, import_pipeline_code_sha: plan.run.pipeline_code_sha, probe_executor_code_sha: process.env.M3_D4E_PIPELINE_CODE_SHA })); return;
            }
            throw error;
        }
    } finally { await client.end(); }
}
if (require.main === module) main().catch(error => { console.error(`D4E_ERROR code=${error.code || 'UNEXPECTED'} message=${error.message}`); process.exitCode = 1; });
module.exports = { assertExactKeys, planFor, resolvePersistedD4EPlan, sameCounts };
