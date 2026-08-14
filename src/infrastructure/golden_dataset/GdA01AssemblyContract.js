'use strict';

// lifecycle: permanent
// GD-A01 的纯合同层：只负责输入/输出的机器可读形状、稳定投影与 fail-closed
// 校验。它不连接数据库、不发网络请求，也不依赖 repo 外部 Markdown 设计文件。

const crypto = require('node:crypto');

const { computeV1IdentityProjectionHash, stableStringify } = require('../canonical/CanonicalInventoryContract');
const { isNumericExternalId, isStrictAbsoluteTimestamp } = require('../fotmob/FotMobCandidateExporter');
const {
    CLOSING_PHASE,
    FIRST_COLLECTION_PHASE,
    FOOTBALL_DATA_PROVIDER_CONTRACT,
} = require('../odds_staging/footballDataProviderContract');

const ASSEMBLY_SCHEMA_VERSION = 'golden-dataset-v1-assembly-artifact/v1';
const RECEIPT_SCHEMA_VERSION = 'gd-a01-assembly-receipt/v1';
const STAGE = 'GD-A01';
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const REQUIRED_SELECTIONS = new Set(['home', 'draw', 'away']);
const REQUIRED_SOURCE_FIELDS = new Set([
    'schema_version',
    'source_provider',
    'source_url',
    'source_match_id',
    'competition',
    'season',
    'kickoff_at',
    'home_team',
    'away_team',
    'bookmaker',
    'bookmaker_source_id',
    'market',
    'selection',
    'line',
    'decimal_odds',
    'snapshot_type',
    'source_observed_at',
    'captured_at',
    'source_timezone',
    'raw_sha256',
    'raw_record_locator',
    'adapter',
    'adapter_version',
    'extraction_method',
    'provenance_status',
    'capture_time_status',
    'source_quote_series',
    'provider_collection_phase',
    'idempotency_key',
    'match_link',
]);
const TEMPORAL_CAPABILITY = Object.freeze({
    identity_linkage: 'PROVEN',
    provider_defined_closing_benchmark: 'PROVEN',
    first_collection_after_market_open: 'PROVEN',
    exact_capture_timestamp: 'UNPROVEN',
    exact_opening_tick: 'UNPROVEN',
    exact_closing_tick: 'UNPROVEN',
    strict_decision_time_value_evaluation: 'NOT_READY',
    point_in_time_numeric_lineage: 'UNPROVEN',
});

class GdA01ContractError extends Error {
    constructor(message, code = 'GD_A01_CONTRACT_INVALID') {
        super(message);
        this.name = 'GdA01ContractError';
        this.code = code;
    }
}

function sha256Bytes(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}

function sha256Text(value) {
    return sha256Bytes(Buffer.from(String(value), 'utf8'));
}

function assertObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new GdA01ContractError(`${label} must be an object`);
    }
    return value;
}

function assertText(value, label) {
    if (typeof value !== 'string' || value.trim() === '') {
        throw new GdA01ContractError(`${label} must be non-empty text`);
    }
    return value;
}

function assertSha(value, label) {
    if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
        throw new GdA01ContractError(`${label} must be a lowercase SHA-256`);
    }
    return value;
}

function assertInteger(value, label, minimum = 0) {
    if (!Number.isSafeInteger(value) || value < minimum) {
        throw new GdA01ContractError(`${label} must be a safe integer >= ${minimum}`);
    }
    return value;
}

function assertKnownKeys(value, allowed, label) {
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) {
            throw new GdA01ContractError(`${label} contains unsupported field ${key}`);
        }
    }
}

function normalizeCandidate(candidate, index) {
    assertObject(candidate, `candidate[${index}]`);
    const allowed = new Set([
        'id',
        'source_provider',
        'source_match_id',
        'competition',
        'season',
        'home_team',
        'away_team',
        'kickoff_at',
    ]);
    assertKnownKeys(candidate, allowed, `candidate[${index}]`);
    for (const field of allowed) assertText(candidate[field], `candidate[${index}].${field}`);
    if (candidate.source_provider !== 'FotMob') {
        throw new GdA01ContractError(`candidate[${index}] source_provider must be FotMob`);
    }
    if (!isNumericExternalId(candidate.source_match_id)) {
        throw new GdA01ContractError(`candidate[${index}] source_match_id must be numeric`);
    }
    if (candidate.competition !== 'Premier League') {
        throw new GdA01ContractError(`candidate[${index}] competition is unsupported`);
    }
    if (!isStrictAbsoluteTimestamp(candidate.kickoff_at)) {
        throw new GdA01ContractError(`candidate[${index}] kickoff_at must be an absolute timestamp`);
    }
    if (candidate.home_team === candidate.away_team) {
        throw new GdA01ContractError(`candidate[${index}] home/away identities must differ`);
    }
    return {
        id: candidate.id,
        source_provider: candidate.source_provider,
        source_match_id: candidate.source_match_id,
        competition: candidate.competition,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
    };
}

function validateCanonicalCandidateDocument(document) {
    assertObject(document, 'canonical candidate artifact');
    if (document.schema_version !== 'candidate-match-identity/v1') {
        throw new GdA01ContractError('canonical candidate artifact schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    assertObject(document.snapshot, 'canonical candidate artifact snapshot');
    if (!Array.isArray(document.candidates) || document.candidates.length === 0) {
        throw new GdA01ContractError('canonical candidate artifact candidates are required');
    }
    const candidates = document.candidates.map(normalizeCandidate);
    const ids = new Set();
    const sourceIds = new Set();
    const fixtureKeys = new Set();
    for (const candidate of candidates) {
        if (ids.has(candidate.id)) throw new GdA01ContractError(`duplicate canonical match ID ${candidate.id}`);
        if (sourceIds.has(candidate.source_match_id)) {
            throw new GdA01ContractError(`duplicate FotMob source match ID ${candidate.source_match_id}`);
        }
        const fixtureKey = [candidate.competition, candidate.season, candidate.home_team, candidate.away_team].join(
            '\u0000'
        );
        if (fixtureKeys.has(fixtureKey)) throw new GdA01ContractError(`duplicate ordered fixture ${candidate.id}`);
        ids.add(candidate.id);
        sourceIds.add(candidate.source_match_id);
        fixtureKeys.add(fixtureKey);
    }
    assertInteger(document.snapshot.candidate_count, 'canonical candidate artifact snapshot.candidate_count', 1);
    if (document.snapshot.candidate_count !== candidates.length) {
        throw new GdA01ContractError('canonical candidate artifact declared count does not match rows');
    }
    if (document.snapshot.source_provider !== 'FotMob') {
        throw new GdA01ContractError('canonical candidate artifact snapshot source_provider mismatch');
    }
    if (document.snapshot.competition !== 'Premier League') {
        throw new GdA01ContractError('canonical candidate artifact snapshot competition mismatch');
    }
    assertSha(document.snapshot.business_content_sha256, 'canonical candidate artifact business_content_sha256');
    const computedHash = computeV1IdentityProjectionHash(candidates);
    if (computedHash !== document.snapshot.business_content_sha256) {
        throw new GdA01ContractError('canonical candidate artifact business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    return {
        candidates,
        byId: new Map(candidates.map(candidate => [candidate.id, candidate])),
        businessHash: computedHash,
    };
}

function validateFotMobFreezeDocument(document) {
    assertObject(document, 'FotMob freeze manifest');
    if (document.schema !== 'fotmob-888-asset-freeze/v1') {
        throw new GdA01ContractError('FotMob freeze schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    assertSha(document.snapshot_id, 'FotMob freeze snapshot_id');
    assertSha(document.target_population_hash, 'FotMob freeze target_population_hash');
    assertSha(document.manifest_sha256, 'FotMob freeze manifest_sha256');
    assertInteger(document.raw_payload_count, 'FotMob freeze raw_payload_count', 1);
    for (const field of ['missing', 'extra', 'duplicate']) assertInteger(document[field], `FotMob freeze ${field}`);
    if (document.missing !== 0 || document.extra !== 0 || document.duplicate !== 0) {
        throw new GdA01ContractError('FotMob freeze population is not complete', 'FROZEN_POPULATION_INVALID');
    }
    if (document.full_raw_retention !== true || document.raw_mutability !== 'immutable') {
        throw new GdA01ContractError('FotMob freeze is not immutable/full-retention');
    }
    if (document.acquisition_status !== 'complete' || document.golden_dataset_status !== 'not_complete') {
        throw new GdA01ContractError('FotMob freeze lifecycle status is unsupported');
    }
    if (document.live_fotmob_network !== false || document.db_writes_performed !== false) {
        throw new GdA01ContractError('FotMob freeze safety flags are not read-only');
    }
    return document;
}

function validateFotMobManifestRowShape(row, index) {
    const required = [
        'asset_manifest_schema',
        'canonical_match_id',
        'capture_timestamp_if_available',
        'fotmob_match_id',
        'kickoff_at',
        'raw_payload_sha256',
        'season',
        'snapshot_id',
        'source_provider',
        'target_population_hash',
    ];
    for (const field of required) {
        if (field === 'capture_timestamp_if_available') {
            if (typeof row[field] !== 'string') {
                throw new GdA01ContractError(`FotMob manifest row ${index}.${field} must be text`);
            }
        } else {
            assertText(row[field], `FotMob manifest row ${index}.${field}`);
        }
    }
}

function validateFotMobManifestRowIdentity(row, index, freeze) {
    if (row.asset_manifest_schema !== 'fotmob-888-raw-asset-manifest/v1') {
        throw new GdA01ContractError(`FotMob manifest row ${index} schema mismatch`, 'UNSUPPORTED_VERSION');
    }
    if (row.source_provider !== 'FotMob' || row.snapshot_id !== freeze.snapshot_id) {
        throw new GdA01ContractError(`FotMob manifest row ${index} snapshot identity mismatch`);
    }
    if (row.target_population_hash !== freeze.target_population_hash) {
        throw new GdA01ContractError(`FotMob manifest row ${index} target population mismatch`);
    }
    if (!isNumericExternalId(row.fotmob_match_id) || !isStrictAbsoluteTimestamp(row.kickoff_at)) {
        throw new GdA01ContractError(`FotMob manifest row ${index} source identity is invalid`);
    }
    assertSha(row.raw_payload_sha256, `FotMob manifest row ${index}.raw_payload_sha256`);
    if (row.capture_timestamp_if_available !== '') {
        throw new GdA01ContractError('FotMob raw capture timestamp is not proven', 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
}

function validateFotMobManifestRowCandidate(row, index, candidateById) {
    const candidate = candidateById.get(row.canonical_match_id);
    if (!candidate) throw new GdA01ContractError(`FotMob manifest row ${index} has no canonical candidate`);
    if (
        candidate.source_match_id !== row.fotmob_match_id ||
        candidate.season !== row.season ||
        candidate.kickoff_at !== row.kickoff_at ||
        candidate.competition !== 'Premier League'
    ) {
        throw new GdA01ContractError(
            `FotMob manifest row ${index} differs from canonical identity`,
            'IDENTITY_CONFLICT'
        );
    }
}

function normalizeFotMobManifestRow(row, index, freeze, candidateById) {
    assertObject(row, `FotMob manifest row ${index}`);
    validateFotMobManifestRowShape(row, index);
    validateFotMobManifestRowIdentity(row, index, freeze);
    validateFotMobManifestRowCandidate(row, index, candidateById);
    return {
        canonical_match_id: row.canonical_match_id,
        fotmob_match_id: row.fotmob_match_id,
        season: row.season,
        kickoff_at: row.kickoff_at,
        raw_payload_sha256: row.raw_payload_sha256,
        snapshot_id: row.snapshot_id,
        target_population_hash: row.target_population_hash,
        source_artifact_class: row.source_artifact_class || null,
        capture_origin: row.capture_origin || null,
        authoritative_run_revision: row.authoritative_run_revision || null,
    };
}

function validateFotMobManifestRows(rows, freeze, candidateById) {
    if (!Array.isArray(rows) || rows.length !== freeze.raw_payload_count) {
        throw new GdA01ContractError('FotMob manifest count does not match frozen population', 'POPULATION_MISMATCH');
    }
    const seenIds = new Set();
    const seenSourceIds = new Set();
    const normalized = rows.map((row, index) => normalizeFotMobManifestRow(row, index, freeze, candidateById));
    for (const row of normalized) {
        if (seenIds.has(row.canonical_match_id)) {
            throw new GdA01ContractError(`duplicate FotMob canonical ID ${row.canonical_match_id}`);
        }
        if (seenSourceIds.has(row.fotmob_match_id)) {
            throw new GdA01ContractError(`duplicate FotMob source ID ${row.fotmob_match_id}`);
        }
        seenIds.add(row.canonical_match_id);
        seenSourceIds.add(row.fotmob_match_id);
    }
    return normalized.sort((left, right) => left.canonical_match_id.localeCompare(right.canonical_match_id));
}

function validateProviderContractBinding(receipt) {
    const declared = assertObject(receipt.provider_semantic_contract, 'odds provider semantic contract');
    const fields = [
        'contract_id',
        'provider_id',
        'evidence_type',
        'effective_from_season',
        'exact_observation_timestamp_available',
        'exact_capture_timestamp_available',
    ];
    for (const field of fields) {
        if (declared[field] !== FOOTBALL_DATA_PROVIDER_CONTRACT[field]) {
            throw new GdA01ContractError(`provider semantic contract mismatch: ${field}`, 'PROVIDER_CONTRACT_MISMATCH');
        }
    }
    if (receipt.evaluation_readiness?.strict_decision_time_value_evaluation_ready !== 'NO') {
        throw new GdA01ContractError(
            'strict decision-time value evaluation must remain NOT_READY',
            'TEMPORAL_SEMANTICS_UNPROVEN'
        );
    }
    return {
        contract_id: declared.contract_id,
        provider_id: declared.provider_id,
        evidence_type: declared.evidence_type,
        effective_from_season: declared.effective_from_season,
        first_collection_semantics: FOOTBALL_DATA_PROVIDER_CONTRACT.first_collection_semantics,
        closing_series_semantics: FOOTBALL_DATA_PROVIDER_CONTRACT.closing_series_semantics,
        exact_observation_timestamp_available: 'UNPROVEN',
        exact_capture_timestamp_available: 'UNPROVEN',
    };
}

function validateMatchLink(link, label) {
    assertObject(link, `${label}.match_link`);
    if (link.status !== 'matched' || link.method !== 'exact_home_away_kickoff') {
        throw new GdA01ContractError(`${label} is not an exact unique match link`, 'LINKAGE_NOT_EXACT');
    }
    assertText(link.matched_id, `${label}.match_link.matched_id`);
    if (
        !Array.isArray(link.candidate_ids) ||
        link.candidate_ids.length !== 1 ||
        link.candidate_ids[0] !== link.matched_id
    ) {
        throw new GdA01ContractError(`${label}.match_link candidate set is not unique`, 'LINKAGE_NOT_EXACT');
    }
    return {
        status: link.status,
        method: link.method,
        candidate_ids: [link.candidate_ids[0]],
        matched_id: link.matched_id,
    };
}

function validateOddsObservationShape(observation, label) {
    for (const field of [
        'schema_version',
        'source_provider',
        'competition',
        'season',
        'kickoff_at',
        'home_team',
        'away_team',
        'bookmaker',
        'bookmaker_source_id',
        'market',
        'selection',
        'snapshot_type',
        'raw_sha256',
        'raw_record_locator',
        'adapter',
        'adapter_version',
        'capture_time_status',
        'source_quote_series',
        'provider_collection_phase',
        'idempotency_key',
    ]) {
        assertText(observation[field], `${label}.${field}`);
    }
    if (observation.schema_version !== 'odds-observation/v1' || observation.source_provider !== 'football-data-csv') {
        throw new GdA01ContractError(`${label} observation schema/provider mismatch`, 'ODDS_SCHEMA_MISMATCH');
    }
    if (observation.market !== '1X2' || !REQUIRED_SELECTIONS.has(observation.selection)) {
        throw new GdA01ContractError(`${label} is outside the admitted 1X2 market`);
    }
}

function validateOddsObservationIdentityAndValue(observation, label) {
    if (!isStrictAbsoluteTimestamp(observation.kickoff_at) || observation.home_team === observation.away_team) {
        throw new GdA01ContractError(`${label} identity is malformed`, 'IDENTITY_CONFLICT');
    }
    if (
        typeof observation.decimal_odds !== 'number' ||
        !Number.isFinite(observation.decimal_odds) ||
        observation.decimal_odds <= 1
    ) {
        throw new GdA01ContractError(`${label}.decimal_odds is invalid`);
    }
    assertSha(observation.raw_sha256, `${label}.raw_sha256`);
}

function validateOddsObservationTemporalSemantics(observation, label) {
    if (observation.source_observed_at !== null || observation.captured_at !== null) {
        throw new GdA01ContractError(
            `${label} contains an unproven observation timestamp`,
            'TEMPORAL_SEMANTICS_UNPROVEN'
        );
    }
    if (observation.capture_time_status !== 'unknown') {
        throw new GdA01ContractError(`${label} capture_time_status is not unknown`, 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
}

function validateOddsObservationProviderPhase(observation, label) {
    if (![FIRST_COLLECTION_PHASE, CLOSING_PHASE].includes(observation.provider_collection_phase)) {
        throw new GdA01ContractError(`${label} provider collection phase is unsupported`, 'PROVIDER_CONTRACT_MISMATCH');
    }
    const expectedSnapshot = observation.provider_collection_phase === CLOSING_PHASE ? 'closing' : 'unknown';
    if (observation.snapshot_type !== expectedSnapshot) {
        throw new GdA01ContractError(
            `${label} snapshot type does not match provider phase`,
            'PROVIDER_CONTRACT_MISMATCH'
        );
    }
}

function validateOddsObservation(observation, label) {
    assertObject(observation, label);
    validateOddsObservationShape(observation, label);
    validateOddsObservationIdentityAndValue(observation, label);
    validateOddsObservationTemporalSemantics(observation, label);
    validateOddsObservationProviderPhase(observation, label);
    // Do not infer phase from the spelling of source_quote_series: a plain
    // provider series such as "VC" itself ends in "C" while its closing
    // counterpart is "VCC". The existing M3 adapter's explicit phase and
    // snapshot_type are the sole semantic authority here.
    const link = validateMatchLink(observation.match_link, label);
    return {
        ...observation,
        decimal_odds: Number(observation.decimal_odds),
        match_link: link,
    };
}

// Artifact and receipt validation lives in a sibling module to keep the
// source-identity contract below the repository's max-lines rule. Lazy
// forwarding preserves the historical public contract surface without a
// module-initialization cycle.
function validateAssemblyArtifact(...args) {
    return require('./GdA01ArtifactContract').validateAssemblyArtifact(...args);
}

function validateOutputFiles(...args) {
    return require('./GdA01ArtifactContract').validateOutputFiles(...args);
}

function validateReceiptDocument(...args) {
    return require('./GdA01ArtifactContract').validateReceiptDocument(...args);
}

function observationProjection(observation, sourceId) {
    const output = {};
    for (const field of REQUIRED_SOURCE_FIELDS) {
        if (field === 'match_link') continue;
        output[field] = observation[field] ?? null;
    }
    output.source_id = sourceId;
    output.match_link = observation.match_link;
    return output;
}

function observationSortKey(observation) {
    return [
        observation.source_id,
        observation.raw_record_locator,
        observation.bookmaker_source_id,
        observation.bookmaker,
        observation.market,
        observation.selection,
        observation.provider_collection_phase,
        observation.source_quote_series,
        observation.idempotency_key,
    ].join('|');
}

function admittedIdSetHash(ids) {
    return sha256Text(JSON.stringify([...ids].sort()));
}

function linkageDecisionSetHash(rows) {
    const decisions = rows
        .map(row => ({
            canonical_match_id: row.canonical_match_id,
            status: row.source_linkage.status,
            method: row.source_linkage.method,
            candidate_ids: row.source_linkage.candidate_ids,
            matched_id: row.source_linkage.matched_id,
        }))
        .sort((left, right) => left.canonical_match_id.localeCompare(right.canonical_match_id));
    return sha256Text(stableStringify(decisions));
}

function artifactBusinessProjection(artifact) {
    const { business_content_sha256: ignored, ...projection } = artifact;
    return projection;
}

function computeArtifactBusinessHash(artifact) {
    return sha256Text(stableStringify(artifactBusinessProjection(artifact)));
}

module.exports = {
    ASSEMBLY_SCHEMA_VERSION,
    GdA01ContractError,
    RECEIPT_SCHEMA_VERSION,
    STAGE,
    TEMPORAL_CAPABILITY,
    admittedIdSetHash,
    computeArtifactBusinessHash,
    linkageDecisionSetHash,
    observationProjection,
    observationSortKey,
    sha256Bytes,
    sha256Text,
    stableStringify,
    // Internal sibling-module helpers; exported only to avoid duplicating
    // generic validation and linkage semantics in the artifact contract.
    assertInteger,
    assertObject,
    assertSha,
    assertText,
    validateMatchLink,
    validateAssemblyArtifact,
    validateCanonicalCandidateDocument,
    validateFotMobFreezeDocument,
    validateFotMobManifestRows,
    validateOddsObservation,
    validateOutputFiles,
    validateProviderContractBinding,
    validateReceiptDocument,
};
