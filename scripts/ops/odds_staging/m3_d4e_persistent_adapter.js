'use strict';

// lifecycle: permanent；D4E fixed-sandbox PostgreSQL persistence port；无任意 SQL 或表名入口。

const crypto = require('node:crypto');
const { assertDbWriteAllowed } = require('../helpers/db_write_guard');
const { PersistenceConflictError } = require('../../../src/infrastructure/odds_staging/persistenceRepository');
const { stableStringify } = require('../../../src/infrastructure/odds_staging/contracts');
const D4E_LOCK_KEY = 731642942;
const json = value => JSON.stringify(value ?? {});
const sameJson = (left, right) => stableStringify(left) === stableStringify(right);

class M3D4EPersistentAdapter {
    constructor(client, { failAfterSource = false } = {}) { this.client = client; this.failAfterSource = failAfterSource; }
    async runInTransaction(callback) {
        // SC-002's universal runtime guard is additive; D4E's stricter identity authorizer
        // runs before this adapter and the wrapper supplies no arbitrary DB target.
        assertDbWriteAllowed({ script: 'm3_d4e_persistent_adapter.js', tables: ['odds_historical_import_runs', 'odds_historical_source_files', 'odds_historical_staging_observations', 'odds_historical_quarantine'], operations: ['INSERT', 'UPDATE'] });
        await this.client.query('BEGIN');
        try {
            await this.client.query("SET LOCAL lock_timeout = '5s'; SET LOCAL statement_timeout = '30s'");
            const locked = await this.client.query('SELECT pg_try_advisory_xact_lock($1) AS locked, pg_backend_pid() AS backend_pid', [D4E_LOCK_KEY]);
            if (!locked.rows[0].locked) { const error = new Error('D4E advisory transaction lock busy'); error.code = 'LOCK_BUSY'; throw error; }
            this.backendPid = locked.rows[0].backend_pid; this.runId = null; this.sourceFileId = null; this.completedReplay = false;
            const value = await callback(this);
            await this.client.query('COMMIT'); return value;
        } catch (error) { await this.client.query('ROLLBACK'); throw error; }
    }
    async findAcceptedByIdempotencyKey(keys) { if (!keys.length) return []; const result = await this.client.query('SELECT idempotency_key,business_fingerprint FROM odds_historical_staging_observations WHERE idempotency_key=ANY($1::text[])', [keys]); return result.rows.map(row => ({ ...row, business_fingerprint: row.business_fingerprint?.trim() || null })); }
    async createImportRun(run) {
        // The fixed advisory xact lock serializes D4E; writer deliberately lacks broad UPDATE,
        // so row locks must not be used as a hidden privilege escalation.
        const existing = await this.client.query('SELECT * FROM odds_historical_import_runs WHERE run_key=$1', [run.run_key]);
        if (existing.rowCount) { const prior = existing.rows[0]; if (prior.mode !== run.mode || prior.source_type !== run.source_type || prior.pipeline_version !== run.pipeline_version || Number(prior.expected_accepted_count) !== run.expected_accepted_count || Number(prior.expected_quarantine_count) !== run.expected_quarantine_count || !sameJson(prior.metadata, run.metadata)) throw new PersistenceConflictError(`divergent import run conflict: ${run.run_key}`); this.runId = prior.id; this.completedReplay = prior.status === 'completed'; return { id: prior.id, already_present: true }; }
        const id = crypto.randomUUID(); await this.client.query("INSERT INTO odds_historical_import_runs (id,run_key,source_type,mode,status,pipeline_version,pipeline_code_sha,manifest_hash,candidate_business_hash,expected_accepted_count,expected_quarantine_count,metadata,started_at) VALUES ($1,$2,$3,$4,'running',$5,$6,$7,$8,$9,$10,$11,NOW())", [id,run.run_key,run.source_type,run.mode,run.pipeline_version,run.pipeline_code_sha,run.manifest_hash,run.candidate_business_hash,run.expected_accepted_count,run.expected_quarantine_count,json(run.metadata)]); this.runId=id; return { id, already_present:false };
    }
    async registerSourceFile(source) {
        const existing=await this.client.query('SELECT id,source_provider,logical_path,content_hash,hash_algorithm,manifest_hash,competition,season,row_count,provenance FROM odds_historical_source_files WHERE import_run_id=$1 AND content_hash=$2',[this.runId,source.content_hash]);
        if(existing.rowCount){const prior=existing.rows[0]; if(prior.source_provider!==source.source_provider||prior.logical_path!==source.logical_path||Number(prior.row_count)!==source.row_count||!sameJson(prior.provenance,source.provenance)) throw new PersistenceConflictError(`divergent source file conflict: ${source.content_hash}`); this.sourceFileId=prior.id;return {id:prior.id,already_present:true};}
        const id=crypto.randomUUID();await this.client.query('INSERT INTO odds_historical_source_files (id,import_run_id,source_provider,logical_path,content_hash,hash_algorithm,manifest_hash,competition,season,row_count,provenance) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)',[id,this.runId,source.source_provider,source.logical_path,source.content_hash,source.hash_algorithm,source.manifest_hash,source.competition,source.season,source.row_count,json(source.provenance)]);this.sourceFileId=id;if(this.failAfterSource)throw new Error('injected transaction failure');return {id,already_present:false};
    }
    async insertAcceptedObservations(rows) { let inserted_count=0,duplicate_count=0; for(const row of rows){const prior=await this.client.query('SELECT business_fingerprint FROM odds_historical_staging_observations WHERE idempotency_key=$1',[row.idempotency_key]);if(prior.rowCount){if(prior.rows[0].business_fingerprint.trim()===row.business_fingerprint){duplicate_count++;continue;}throw new PersistenceConflictError(`divergent idempotency conflict: ${row.idempotency_key}`);}const o=row.observation;await this.client.query('INSERT INTO odds_historical_staging_observations (import_run_id,source_file_id,source_row_number,idempotency_key,canonical_match_id,candidate_match_id,canonical_match_fk_status,historical_match_identity,source_provider,source_match_id,competition,season,kickoff_at,home_team,away_team,bookmaker,bookmaker_source_id,market,selection,line,decimal_odds,snapshot_type,source_observed_at,captured_at,ingested_at,source_timezone,raw_sha256,raw_record_locator,adapter,adapter_version,extraction_method,provenance_status,match_link_evidence,audit_payload,business_fingerprint) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,$35)',[this.runId,this.sourceFileId,row.source_row_number,row.idempotency_key,row.canonical_match_id,row.candidate_match_id,row.canonical_match_fk_status,json(row.historical_match_identity),o.source_provider,o.source_match_id,o.competition,o.season,o.kickoff_at,o.home_team,o.away_team,o.bookmaker,o.bookmaker_source_id,o.market,o.selection,o.line,o.decimal_odds,o.snapshot_type,o.source_observed_at,o.captured_at,o.ingested_at,o.source_timezone,o.raw_sha256,o.raw_record_locator,o.adapter,o.adapter_version,o.extraction_method,o.provenance_status,json(o.match_link?.evidence),json(o),row.business_fingerprint]);inserted_count++;}return {inserted_count,duplicate_count}; }
    async insertQuarantineRecords(rows) { let inserted_count=0,duplicate_count=0;for(const row of rows){const prior=await this.client.query('SELECT source_payload FROM odds_historical_quarantine WHERE quarantine_key=$1',[row.quarantine_key]);if(prior.rowCount){if(sameJson(prior.rows[0].source_payload,row.source_payload)){duplicate_count++;continue;}throw new PersistenceConflictError(`divergent quarantine conflict: ${row.quarantine_key}`);}await this.client.query('INSERT INTO odds_historical_quarantine (import_run_id,source_file_id,source_row_number,quarantine_key,idempotency_key,reason_codes,reason_detail,historical_match_identity,source_payload,resolution_status) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)',[this.runId,this.sourceFileId,row.source_row_number,row.quarantine_key,row.idempotency_key,json(row.reason_codes),json(row.reason_detail),json(row.historical_match_identity),json(row.source_payload),row.resolution_status]);inserted_count++;}return {inserted_count,duplicate_count}; }
    async markRunCompleted(runKey,result) { if(this.completedReplay)return {already_present:true};await this.client.query("UPDATE odds_historical_import_runs SET status='completed',actual_accepted_count=$1,actual_quarantine_count=$2,duplicate_count=$3,completed_at=COALESCE(completed_at,NOW()),updated_at=NOW() WHERE run_key=$4 AND status IN ('running','completed')",[result.accepted_count,result.quarantine_count,result.duplicate_count,runKey]); }
}
module.exports = { D4E_LOCK_KEY, M3D4EPersistentAdapter };
