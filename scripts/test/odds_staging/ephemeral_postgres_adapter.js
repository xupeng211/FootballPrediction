'use strict';

// lifecycle: permanent; test-only PostgreSQL implementation of the D4B persistence port.

const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { PersistenceConflictError } = require('../../../src/infrastructure/odds_staging/persistenceRepository');
const { stableStringify } = require('../../../src/infrastructure/odds_staging/contracts');

function json(value) { return JSON.stringify(value ?? {}); }
function sameJson(left, right) { return stableStringify(left) === stableStringify(right); }

class EphemeralPostgresAdapter {
    constructor(client, { failAfterSource = false } = {}) {
        this.client = client;
        this.failAfterSource = failAfterSource;
        this.runId = null;
        this.sourceFileId = null;
        this.completedReplay = false;
    }

    resetExecutionState() {
        this.runId = null;
        this.sourceFileId = null;
        this.completedReplay = false;
    }

    async runInTransaction(callback) {
        this.resetExecutionState();
        await this.client.query('BEGIN');
        try {
            const value = await callback(this);
            await this.client.query('COMMIT');
            return value;
        } catch (error) {
            await this.client.query('ROLLBACK');
            throw error;
        }
    }

    async findAcceptedByIdempotencyKey(keys) {
        if (!keys.length) return [];
        const result = await this.client.query(
            'SELECT idempotency_key, business_fingerprint FROM odds_historical_staging_observations WHERE idempotency_key = ANY($1::text[])', [keys]
        );
        return result.rows.map(row => ({ ...row, business_fingerprint: row.business_fingerprint?.trim() || null }));
    }

    async createImportRun(run) {
        const existing = await this.client.query('SELECT * FROM odds_historical_import_runs WHERE run_key = $1 FOR UPDATE', [run.run_key]);
        if (existing.rowCount) {
            const prior = existing.rows[0];
            const differs = prior.mode !== run.mode || prior.source_type !== run.source_type || prior.pipeline_version !== run.pipeline_version
                || (prior.pipeline_code_sha?.trim() || null) !== run.pipeline_code_sha || (prior.manifest_hash?.trim() || null) !== run.manifest_hash
                || (prior.candidate_business_hash?.trim() || null) !== run.candidate_business_hash
                || Number(prior.expected_accepted_count) !== run.expected_accepted_count || Number(prior.expected_quarantine_count) !== run.expected_quarantine_count
                || !sameJson(prior.metadata, run.metadata);
            if (differs) {
                throw new PersistenceConflictError(`divergent import run conflict: ${run.run_key}`);
            }
            this.runId = prior.id;
            this.completedReplay = prior.status === 'completed';
            return { id: prior.id, already_present: true };
        }
        const id = crypto.randomUUID();
        await this.client.query(
            `INSERT INTO odds_historical_import_runs
            (id, run_key, source_type, mode, status, pipeline_version, pipeline_code_sha, manifest_hash, candidate_business_hash, expected_accepted_count, expected_quarantine_count, metadata, started_at)
            VALUES ($1,$2,$3,$4,'running',$5,$6,$7,$8,$9,$10,$11,NOW())`,
            [id, run.run_key, run.source_type, run.mode, run.pipeline_version, run.pipeline_code_sha, run.manifest_hash, run.candidate_business_hash, run.expected_accepted_count, run.expected_quarantine_count, json(run.metadata)]
        );
        this.runId = id;
        return { id, already_present: false };
    }

    async registerSourceFile(source) {
        const existing = await this.client.query('SELECT id, source_provider, logical_path, provenance FROM odds_historical_source_files WHERE import_run_id = $1 AND content_hash = $2 FOR UPDATE', [this.runId, source.content_hash]);
        if (existing.rowCount) {
            const prior = existing.rows[0];
            if (prior.source_provider !== source.source_provider || prior.logical_path !== source.logical_path || !sameJson(prior.provenance, source.provenance)) {
                throw new PersistenceConflictError(`divergent source file conflict: ${source.content_hash}`);
            }
            this.sourceFileId = prior.id;
            return { id: prior.id, already_present: true };
        }
        const id = crypto.randomUUID();
        await this.client.query(
            `INSERT INTO odds_historical_source_files
            (id, import_run_id, source_provider, logical_path, content_hash, hash_algorithm, manifest_hash, competition, season, row_count, provenance)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
            [id, this.runId, source.source_provider, source.logical_path, source.content_hash, source.hash_algorithm, source.manifest_hash, source.competition, source.season, source.row_count, json(source.provenance)]
        );
        this.sourceFileId = id;
        if (this.failAfterSource) throw new Error('injected transaction failure');
        return { id, already_present: false };
    }

    async insertAcceptedObservations(rows) {
        let insertedCount = 0;
        let duplicateCount = 0;
        for (const row of rows) {
            const observation = row.observation;
            if (!row.business_fingerprint) throw new PersistenceConflictError('business fingerprint is required');
            const result = await this.client.query('SELECT business_fingerprint FROM odds_historical_staging_observations WHERE idempotency_key = $1 FOR UPDATE', [row.idempotency_key]);
            if (result.rowCount) {
                if (result.rows[0].business_fingerprint?.trim() === row.business_fingerprint) {
                    duplicateCount += 1;
                    continue;
                }
                throw new PersistenceConflictError(`divergent idempotency conflict: ${row.idempotency_key}`);
            }
            await this.client.query(
                `INSERT INTO odds_historical_staging_observations
                (import_run_id, source_file_id, source_row_number, idempotency_key, canonical_match_id, candidate_match_id, canonical_match_fk_status, historical_match_identity, source_provider, source_match_id, competition, season, kickoff_at, home_team, away_team, bookmaker, bookmaker_source_id, market, selection, line, decimal_odds, snapshot_type, source_observed_at, captured_at, ingested_at, source_timezone, raw_sha256, raw_record_locator, adapter, adapter_version, extraction_method, provenance_status, source_quote_series, capture_time_status, kickoff_time_interpretation_evidence, match_link_evidence, audit_payload, business_fingerprint)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,$35,$36,$37,$38)`,
                [this.runId, this.sourceFileId, row.source_row_number, row.idempotency_key, row.canonical_match_id, row.candidate_match_id, row.canonical_match_fk_status, json(row.historical_match_identity), observation.source_provider, observation.source_match_id, observation.competition, observation.season, observation.kickoff_at, observation.home_team, observation.away_team, observation.bookmaker, observation.bookmaker_source_id, observation.market, observation.selection, observation.line, observation.decimal_odds, observation.snapshot_type, observation.source_observed_at, observation.captured_at, observation.ingested_at, observation.source_timezone, observation.raw_sha256, observation.raw_record_locator, observation.adapter, observation.adapter_version, observation.extraction_method, observation.provenance_status, observation.source_quote_series, observation.capture_time_status, json(observation.kickoff_time_interpretation_evidence), json(observation.match_link?.evidence), json(observation), row.business_fingerprint]
            );
            insertedCount += 1;
        }
        return { inserted_count: insertedCount, duplicate_count: duplicateCount };
    }

    async insertQuarantineRecords(rows) {
        let insertedCount = 0;
        let duplicateCount = 0;
        for (const row of rows) {
            const existing = await this.client.query('SELECT source_payload FROM odds_historical_quarantine WHERE quarantine_key = $1 FOR UPDATE', [row.quarantine_key]);
            if (existing.rowCount) {
                if (sameJson(existing.rows[0].source_payload, row.source_payload)) {
                    duplicateCount += 1;
                    continue;
                }
                throw new PersistenceConflictError(`divergent quarantine conflict: ${row.quarantine_key}`);
            }
            await this.client.query(
                `INSERT INTO odds_historical_quarantine
                (import_run_id, source_file_id, source_row_number, quarantine_key, idempotency_key, reason_codes, reason_detail, historical_match_identity, source_payload, resolution_status)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
                [this.runId, this.sourceFileId, row.source_row_number, row.quarantine_key, row.idempotency_key, json(row.reason_codes), json(row.reason_detail), json(row.historical_match_identity), json(row.source_payload), row.resolution_status]
            );
            insertedCount += 1;
        }
        return { inserted_count: insertedCount, duplicate_count: duplicateCount };
    }

    async markRunCompleted(runKey, result) {
        if (this.completedReplay) return { already_present: true };
        await this.client.query(
            `UPDATE odds_historical_import_runs SET status = 'completed', actual_accepted_count = $1, actual_quarantine_count = $2, duplicate_count = $3, completed_at = COALESCE(completed_at, NOW()), updated_at = NOW()
             WHERE run_key = $4 AND status IN ('running', 'completed')`,
            [result.accepted_count, result.quarantine_count, result.duplicate_count, runKey]
        );
    }
}

async function assertDatabaseFinalDefenses(client, accepted, runKey) {
    await Promise.all([
        client.query(
            'INSERT INTO odds_historical_staging_observations (import_run_id, source_file_id, idempotency_key, canonical_match_fk_status, historical_match_identity, source_provider, bookmaker, market, selection, decimal_odds, snapshot_type, raw_sha256, raw_record_locator, adapter, adapter_version, provenance_status, audit_payload, business_fingerprint) SELECT import_run_id, source_file_id, idempotency_key, canonical_match_fk_status, historical_match_identity, source_provider, bookmaker, market, selection, decimal_odds, snapshot_type, raw_sha256, raw_record_locator, adapter, adapter_version, provenance_status, audit_payload, business_fingerprint FROM odds_historical_staging_observations WHERE idempotency_key = $1',
            [accepted.idempotency_key]
        ).then(() => assert.fail('duplicate unique key was accepted'), error => assert.match(error.message, /duplicate key/)),
        client.query("INSERT INTO odds_historical_import_runs (id, run_key, source_type, mode, status, pipeline_version, expected_accepted_count, expected_quarantine_count) VALUES ('00000000-0000-0000-0000-000000000099', $1, 'historical_odds', 'invalid', 'planned', 'x', 0, 0)", [runKey])
            .then(() => assert.fail('invalid mode was accepted'), error => assert.match(error.message, /check constraint/)),
    ]);
    await client.query('UPDATE odds_historical_staging_observations SET decimal_odds = 1 WHERE idempotency_key = $1', [accepted.idempotency_key])
        .then(() => assert.fail('invalid odds were accepted'), error => assert.match(error.message, /check constraint/));
}

module.exports = { EphemeralPostgresAdapter, assertDatabaseFinalDefenses };
