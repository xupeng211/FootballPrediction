'use strict';

// lifecycle: permanent；Historical odds staging 的纯持久化映射与 run 生命周期合同；不连接数据库。

const {
    sha256Text,
    stableCanonicalize,
    stableStringify,
} = require('./contracts');

const RUN_STATUSES = Object.freeze(['planned', 'running', 'completed', 'failed', 'rolled_back', 'cancelled']);
const RUN_MODES = Object.freeze(['dry_run', 'controlled_write']);
const RUN_TRANSITIONS = Object.freeze({
    planned: new Set(['running', 'cancelled']),
    running: new Set(['completed', 'failed', 'rolled_back']),
    completed: new Set(['rolled_back']),
    failed: new Set(['running', 'cancelled']),
    rolled_back: new Set(),
    cancelled: new Set(),
});

class PersistenceContractError extends Error {
    constructor(message, code = 'PERSISTENCE_CONTRACT_ERROR') {
        super(message);
        this.name = 'PersistenceContractError';
        this.code = code;
    }
}

function requireText(value, field) {
    const text = String(value ?? '').trim();
    if (!text) throw new PersistenceContractError(`${field} is required`);
    return text;
}

function sourceRowNumber(locator) {
    const match = /(?:^|[:;,\s])row=(\d+)(?:$|[:;,\s])/.exec(String(locator || ''));
    return match ? Number(match[1]) : null;
}

function canonicalMatchIdentity(observation) {
    return stableCanonicalize({
        source_provider: observation.source_provider,
        source_match_id: observation.source_match_id,
        competition: observation.competition,
        season: observation.season,
        kickoff_at: observation.kickoff_at,
        home_team: observation.home_team,
        away_team: observation.away_team,
        match_link: observation.match_link || null,
        kickoff_time_interpretation_evidence: observation.kickoff_time_interpretation_evidence || null,
    });
}

function createRunKey(result, context = {}) {
    const manifest = result.normalized_manifest || {};
    return sha256Text(
        stableStringify({
            contract: 'odds-historical-import-run/v1',
            raw_sha256: manifest.raw_sha256,
            manifest_hash: context.manifest_hash || null,
            candidate_business_hash: context.candidate_business_hash || null,
            pipeline_code_sha: context.pipeline_code_sha || null,
            accepted_count: result.summary?.accepted_count,
            quarantine_count: result.summary?.quarantine_count,
        })
    );
}

function createImportRunPlan(result, context = {}) {
    if (!result?.summary || !result?.normalized_manifest) {
        throw new PersistenceContractError('offline staging result with summary and normalized_manifest is required');
    }
    const acceptedCount = Number(result.summary.accepted_count);
    const quarantineCount = Number(result.summary.quarantine_count);
    if (!Number.isInteger(acceptedCount) || acceptedCount < 0 || !Number.isInteger(quarantineCount) || quarantineCount < 0) {
        throw new PersistenceContractError('summary counts must be non-negative integers');
    }
    const runMode = context.runMode || 'dry_run';
    if (!RUN_MODES.includes(runMode)) {
        throw new PersistenceContractError(`unsupported import run mode: ${runMode}`);
    }
    return stableCanonicalize({
        run_key: createRunKey(result, context),
        source_type: 'historical_odds',
        mode: runMode,
        status: 'planned',
        pipeline_version: context.pipeline_version || 'odds-staging-persistence/v1',
        pipeline_code_sha: context.pipeline_code_sha || null,
        manifest_hash: context.manifest_hash || null,
        candidate_business_hash: context.candidate_business_hash || null,
        expected_accepted_count: acceptedCount,
        expected_quarantine_count: quarantineCount,
        metadata: { source_manifest_schema: result.normalized_manifest.schema_version || null },
    });
}

function mapSourceFile(manifest, runKey) {
    return stableCanonicalize({
        import_run_key: requireText(runKey, 'run_key'),
        source_provider: requireText(manifest.source_provider, 'manifest.source_provider'),
        logical_path: manifest.repository_provenance?.path || manifest.raw_path || null,
        content_hash: requireText(manifest.raw_sha256, 'manifest.raw_sha256'),
        hash_algorithm: 'sha256',
        manifest_hash: null,
        provider: manifest.source_provider,
        competition: manifest.competition || null,
        season: manifest.season || null,
        row_count: null,
        provenance: stableCanonicalize({
            acquisition_mode: manifest.acquisition_mode || null,
            source_url: manifest.source_url || null,
            repository_provenance: manifest.repository_provenance || null,
            provenance_status: manifest.provenance_status || null,
        }),
    });
}

function mapAcceptedObservation(observation, sourceFileHash) {
    if ((observation.quarantine_reasons || []).length > 0) {
        throw new PersistenceContractError('quarantined observation cannot map to accepted persistence row');
    }
    return stableCanonicalize({
        source_file_content_hash: requireText(sourceFileHash, 'source_file_content_hash'),
        source_row_number: sourceRowNumber(observation.raw_record_locator),
        idempotency_key: requireText(observation.idempotency_key, 'observation.idempotency_key'),
        // #1797 matched_id is a local candidate identity, not a statically proven matches.match_id FK.
        canonical_match_id: null,
        candidate_match_id: observation.match_link?.matched_id || null,
        canonical_match_fk_status: 'unverified_database_fk',
        historical_match_identity: canonicalMatchIdentity(observation),
        observation: stableCanonicalize(observation),
        business_fingerprint: sha256Text(stableStringify(observation)),
    });
}

function mapQuarantineRecord(record, sourceFileHash) {
    const reasons = [...new Set(record.reasons || [])].sort();
    if (reasons.length === 0) throw new PersistenceContractError('quarantine record requires at least one reason');
    const payload = stableCanonicalize({
        source_file_content_hash: requireText(sourceFileHash, 'source_file_content_hash'),
        source_row_number: sourceRowNumber(record.raw_record_locator),
        idempotency_key: record.evidence?.parsed_fields?.idempotency_key || null,
        reason_codes: reasons,
        reason_detail: record.evidence || {},
        historical_match_identity: {
            source_provider: record.source_provider || null,
            source_match_id: record.source_match_id || null,
            raw_sha256: record.raw_sha256 || null,
            raw_record_locator: record.raw_record_locator || null,
        },
        source_payload: stableCanonicalize(record),
        resolution_status: 'open',
    });
    return { ...payload, quarantine_key: sha256Text(stableStringify(payload)) };
}

function buildPersistencePlan(result, context = {}) {
    const run = createImportRunPlan(result, context);
    const sourceFile = mapSourceFile(result.normalized_manifest, run.run_key);
    const accepted = (result.accepted_observations || []).map(observation =>
        mapAcceptedObservation(observation, sourceFile.content_hash)
    );
    const quarantine = (result.quarantine || []).map(record => mapQuarantineRecord(record, sourceFile.content_hash));
    if (accepted.length !== run.expected_accepted_count || quarantine.length !== run.expected_quarantine_count) {
        throw new PersistenceContractError('result arrays do not reconcile with summary counts');
    }
    return stableCanonicalize({
        contract_version: 'odds-historical-persistence-plan/v1',
        mode: 'dry_run',
        persistence_status: 'not_persisted',
        run,
        source_file: sourceFile,
        accepted,
        quarantine,
    });
}

function assertRunTransition(from, to) {
    if (!RUN_STATUSES.includes(from) || !RUN_STATUSES.includes(to) || !RUN_TRANSITIONS[from].has(to)) {
        throw new PersistenceContractError(`invalid import run transition: ${from} -> ${to}`);
    }
}

module.exports = {
    PersistenceContractError,
    RUN_STATUSES,
    RUN_MODES,
    RUN_TRANSITIONS,
    assertRunTransition,
    buildPersistencePlan,
    canonicalMatchIdentity,
    createImportRunPlan,
    createRunKey,
    mapAcceptedObservation,
    mapQuarantineRecord,
    mapSourceFile,
};
