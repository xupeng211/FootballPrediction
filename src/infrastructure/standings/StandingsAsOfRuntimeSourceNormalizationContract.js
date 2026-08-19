'use strict';
/* eslint-disable max-lines -- one pure validator owns the complete versioned envelope boundary. */

// lifecycle: permanent
// Specialized / Internal: generic normalization handoff validator only.
// It does not parse provider payloads, select a provider, prove source truth,
// run the standings engine, or access network/DB/filesystem/wall clock.

const { sha256Text, stableStringify } = require('../canonical/StableValue');
const {
    validateStandingsAsOfEngineInput,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
} = require('./StandingsAsOfEngineInputContract');

const NORMALIZATION_CONTRACT_ID = 'standings-asof-runtime-source-normalization/v1';
const NORMALIZATION_CONTRACT_VERSION = 'v1';
const NORMALIZATION_CONTRACT_STATUS = 'FROZEN';
const NORMALIZATION_CONTENT_DIGEST_ALGORITHM = 'SHA-256';
const NORMALIZATION_CONTENT_DIGEST_SCOPE = 'SELF_EXCLUDING_CANONICAL_NORMALIZATION_ENVELOPE';
const CANONICAL_SERIALIZATION = 'STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON';
const MODEL_ASOF_CONTRACT_ID = 'canonical-model-asof/v1';
const MODEL_ASOF_CONTRACT_VERSION = 'v1';
const RUNTIME_CAPTURE_CONTRACT_ID = 'canonical-runtime-capture/v1';
const RUNTIME_CAPTURE_CONTRACT_VERSION = 'v1';
const STANDINGS_CONTRACT_ID = 'standings/premier-league-point-in-time/v1';
const STANDINGS_CONTRACT_VERSION = 'v1';

const NORMALIZATION_ENVELOPE_FIELDS = new Set([
    'NORMALIZATION_CONTRACT_ID',
    'NORMALIZATION_CONTRACT_VERSION',
    'NORMALIZATION_INSTANCE_ID',
    'NORMALIZATION_CONTENT_DIGEST',
    'PREDICTION_CONTEXT',
    'RUNTIME_CAPTURE_BINDING',
    'STANDINGS_EVIDENCE_IDS',
    'EVIDENCE_ATTESTATIONS',
    'FACT_BINDINGS',
    'OUTPUT_STANDINGS_INPUT_BINDING',
    'STATUS',
]);
const PREDICTION_CONTEXT_FIELDS = new Set([
    'PREDICTION_CONTEXT_ID',
    'MODEL_ASOF_CONTRACT_ID',
    'MODEL_ASOF_CONTRACT_VERSION',
    'MODEL_DECISION_TIME_UTC',
    'FEATURE_AS_OF_UTC',
    'TARGET_MATCH_ID',
    'TARGET_KICKOFF_UTC',
]);
const RUNTIME_CAPTURE_BINDING_FIELDS = new Set([
    'RUNTIME_CAPTURE_CONTRACT_ID',
    'RUNTIME_CAPTURE_CONTRACT_VERSION',
    'CAPTURE_INSTANCE_ID',
    'CAPTURE_CONTENT_DIGEST',
    'CAPTURE_SELECTED_EVIDENCE_IDS',
]);
const EVIDENCE_ATTESTATION_FIELDS = new Set([
    'EVIDENCE_ID',
    'SOURCE_FAMILY',
    'SOURCE_AUTHORITY_ID',
    'SOURCE_RECORD_ID',
    'PAYLOAD_KIND',
    'PAYLOAD_CONTENT_DIGEST',
    'PAYLOAD_BYTE_LENGTH',
    'SOURCE_EVENT_TIME_UTC',
    'SOURCE_EFFECTIVE_TIME_UTC',
    'SOURCE_OBSERVED_AT_UTC',
    'SOURCE_CAPTURED_AT_UTC',
    'AVAILABILITY_PROOF_KIND',
    'AVAILABILITY_PROOF_DATA',
    'SOURCE_PROVENANCE_STATUS',
]);
const FACT_BINDING_FIELDS = new Set([
    'BINDING_ID',
    'SEMANTIC_ROLE',
    'DOMAIN_IDENTITY',
    'SOURCE_EVIDENCE_IDS',
    'CANONICAL_MATCH_ID',
    'ADJUSTMENT_ID',
    'AVAILABILITY_EVIDENCE_ID',
    'NORMALIZED_FACT_DIGEST',
    'DERIVATION',
]);
const OUTPUT_STANDINGS_INPUT_BINDING_FIELDS = new Set([
    'STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID',
    'STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION',
    'STANDINGS_RANKING_CONTRACT_ID',
    'STANDINGS_RANKING_CONTRACT_VERSION',
    'CANONICAL_INPUT_DIGEST',
    'MODEL_DECISION_TIME_UTC',
    'FEATURE_AS_OF_UTC',
    'TARGET_MATCH_ID',
    'TARGET_KICKOFF_UTC',
    'FIXTURE_UNIVERSE_REFERENCE_ID',
    'FIXTURE_STATE_IDS',
    'ADMINISTRATIVE_ADJUSTMENT_IDS',
    'OUTPUT_INPUT_BINDING_DIGEST',
]);
const STATUS_FIELDS = new Set([
    'NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY',
    'CAPTURE_BINDING_VALIDITY',
    'OUTPUT_INPUT_BINDING_VALIDITY',
    'SOURCE_SEMANTIC_NORMALIZATION_VALIDITY',
    'SOURCE_AUTHORITY_VALIDITY',
    'SOURCE_STREAM_COMPLETENESS',
    'RUNTIME_NUMERIC_ELIGIBILITY',
]);
const FACT_BINDING_ROLES = new Set([
    'FIXTURE_UNIVERSE',
    'FIXTURE',
    'FIXTURE_STATUS',
    'RESULT',
    'ADMIN_ADJUSTMENT',
    'TARGET_IDENTITY',
]);
const DERIVATIONS = new Set(['SOURCE_ATTESTED', 'CORE_DERIVED']);
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9_.:/-]*$/;
const SHA256 = /^[0-9a-f]{64}$/;
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/;
const SECRET_KEYS = new Set([
    'AUTHORIZATION',
    'AUTH_HEADER',
    'API_KEY',
    'BEARER_TOKEN',
    'COOKIE',
    'COOKIES',
    'CREDENTIAL',
    'CREDENTIALS',
    'PASSWORD',
    'REFRESH_TOKEN',
    'SECRET',
    'SECRET_KEY',
    'SESSION_ID',
    'SIGNED_CREDENTIAL',
    'TOKEN',
]);

// Canonical ordering is frozen as locale-independent Unicode code-point
// lexicographic ascending.  This comparator intentionally does not use
// localeCompare, Intl.Collator, numeric/cultural collation, or UTF-16
// code-unit ordering.
function compareUnicodeCodePoints(left, right) {
    const leftCodePoints = Array.from(String(left));
    const rightCodePoints = Array.from(String(right));
    const sharedLength = Math.min(leftCodePoints.length, rightCodePoints.length);
    for (let index = 0; index < sharedLength; index += 1) {
        const leftCodePoint = leftCodePoints[index].codePointAt(0);
        const rightCodePoint = rightCodePoints[index].codePointAt(0);
        if (leftCodePoint !== rightCodePoint) return leftCodePoint - rightCodePoint;
    }
    return leftCodePoints.length - rightCodePoints.length;
}

function sortUnicodeCodePoints(values) {
    return [...values].sort(compareUnicodeCodePoints);
}

class StandingsAsOfRuntimeSourceNormalizationError extends Error {
    constructor(reasonCode, message) {
        super(`${reasonCode}: ${message}`);
        this.name = 'StandingsAsOfRuntimeSourceNormalizationError';
        this.reasonCode = reasonCode;
    }
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function exactObject(value, fields, label) {
    if (
        !isPlainObject(value) ||
        Object.keys(value).length !== fields.size ||
        Object.keys(value).some(key => !fields.has(key))
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_SCHEMA_MISMATCH', `${label} malformed`);
    }
    return value;
}

function text(value, label, { safeId = false } = {}) {
    if (typeof value !== 'string' || value.trim() === '') {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_SCHEMA_MISMATCH', `${label} malformed`);
    }
    if (safeId && !SAFE_ID.test(value)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_SCHEMA_MISMATCH', `${label} malformed`);
    }
    return value;
}

function optionalText(value, label, options = {}) {
    if (value !== null) text(value, label, options);
}

function sha256(value, label) {
    if (typeof value !== 'string' || !SHA256.test(value)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_DIGEST_INVALID', `${label} malformed`);
    }
    return value;
}

function canonicalTimestamp(value, label) {
    if (typeof value !== 'string' || !UTC_TIMESTAMP.test(value) || Number.isNaN(Date.parse(value))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_TIMESTAMP_INVALID', `${label} malformed`);
    }
    return new Date(Date.parse(value)).toISOString();
}

function rejectSecretKeys(value) {
    if (Array.isArray(value)) {
        value.forEach(rejectSecretKeys);
    } else if (isPlainObject(value)) {
        Object.entries(value).forEach(([key, child]) => {
            if (SECRET_KEYS.has(key.toUpperCase())) {
                throw new StandingsAsOfRuntimeSourceNormalizationError(
                    'SECRET_METADATA_FORBIDDEN',
                    `secret-bearing field ${key} is forbidden`
                );
            }
            rejectSecretKeys(child);
        });
    }
}

function canonicalizeTree(value, key = null) {
    if (Array.isArray(value)) return value.map(child => canonicalizeTree(child, key));
    if (isPlainObject(value)) {
        return Object.keys(value)
            .sort(compareUnicodeCodePoints)
            .reduce((out, childKey) => {
                out[childKey] = canonicalizeTree(value[childKey], childKey);
                return out;
            }, {});
    }
    if (typeof value === 'string' && key && (key.endsWith('_UTC') || key === 'start_utc' || key === 'end_utc')) {
        return canonicalTimestamp(value, key);
    }
    return value;
}

function cloneJson(value) {
    return JSON.parse(JSON.stringify(value));
}

function sortedUniqueIds(value, label) {
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || !SAFE_ID.test(item))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('NORMALIZATION_SCHEMA_MISMATCH', `${label} malformed`);
    }
    const sorted = sortUnicodeCodePoints(value);
    if (new Set(value).size !== value.length) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            `${label} contains duplicates`
        );
    }
    return sorted;
}

function orderedProjection(envelope, { includeDigest = false } = {}) {
    const projection = cloneJson(envelope);
    if (!includeDigest) delete projection.NORMALIZATION_CONTENT_DIGEST;
    if (projection.RUNTIME_CAPTURE_BINDING) {
        projection.RUNTIME_CAPTURE_BINDING.CAPTURE_SELECTED_EVIDENCE_IDS = sortUnicodeCodePoints(
            projection.RUNTIME_CAPTURE_BINDING.CAPTURE_SELECTED_EVIDENCE_IDS
        );
    }
    projection.STANDINGS_EVIDENCE_IDS = sortUnicodeCodePoints(projection.STANDINGS_EVIDENCE_IDS);
    projection.EVIDENCE_ATTESTATIONS = [...projection.EVIDENCE_ATTESTATIONS].sort((left, right) =>
        compareUnicodeCodePoints(left.EVIDENCE_ID, right.EVIDENCE_ID)
    );
    projection.FACT_BINDINGS = projection.FACT_BINDINGS.map(binding => ({
        ...binding,
        SOURCE_EVIDENCE_IDS: sortUnicodeCodePoints(binding.SOURCE_EVIDENCE_IDS),
    })).sort((left, right) => compareUnicodeCodePoints(left.BINDING_ID, right.BINDING_ID));
    projection.OUTPUT_STANDINGS_INPUT_BINDING.FIXTURE_STATE_IDS = sortUnicodeCodePoints(
        projection.OUTPUT_STANDINGS_INPUT_BINDING.FIXTURE_STATE_IDS
    );
    projection.OUTPUT_STANDINGS_INPUT_BINDING.ADMINISTRATIVE_ADJUSTMENT_IDS = sortUnicodeCodePoints(
        projection.OUTPUT_STANDINGS_INPUT_BINDING.ADMINISTRATIVE_ADJUSTMENT_IDS
    );
    return canonicalizeTree(projection);
}

function computeNormalizationContentDigest(envelope) {
    if (!isPlainObject(envelope)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            'envelope must be an object'
        );
    }
    return sha256Text(stableStringify(orderedProjection(envelope)));
}

function computeFactBindingDigest(binding) {
    const projection = cloneJson(binding);
    delete projection.NORMALIZED_FACT_DIGEST;
    projection.SOURCE_EVIDENCE_IDS = sortUnicodeCodePoints(projection.SOURCE_EVIDENCE_IDS);
    return sha256Text(stableStringify(canonicalizeTree(projection)));
}

function computeOutputInputBindingDigest(binding) {
    const projection = cloneJson(binding);
    delete projection.OUTPUT_INPUT_BINDING_DIGEST;
    projection.FIXTURE_STATE_IDS = sortUnicodeCodePoints(projection.FIXTURE_STATE_IDS);
    projection.ADMINISTRATIVE_ADJUSTMENT_IDS = sortUnicodeCodePoints(projection.ADMINISTRATIVE_ADJUSTMENT_IDS);
    return sha256Text(stableStringify(canonicalizeTree(projection)));
}

function sourceRecordRefForEvidenceIds(captureContentDigest, evidenceIds, attestationsById) {
    const ids = sortUnicodeCodePoints(evidenceIds);
    const records = ids.map(id => attestationsById[id].SOURCE_RECORD_ID);
    const nonNull = records.filter(record => record !== null);
    if (ids.length === 1 && nonNull.length === 1) return nonNull[0];
    if (nonNull.length > 0) {
        return `capture-record-set:${sha256Text(stableStringify(ids.map(id => [id, attestationsById[id].SOURCE_RECORD_ID])))}`;
    }
    return `capture:${captureContentDigest}:${ids.join('|')}`;
}

function validateContext(value) {
    const context = exactObject(value, PREDICTION_CONTEXT_FIELDS, 'PREDICTION_CONTEXT');
    text(context.PREDICTION_CONTEXT_ID, 'PREDICTION_CONTEXT_ID', { safeId: true });
    text(context.TARGET_MATCH_ID, 'TARGET_MATCH_ID', { safeId: true });
    if (
        context.MODEL_ASOF_CONTRACT_ID !== MODEL_ASOF_CONTRACT_ID ||
        context.MODEL_ASOF_CONTRACT_VERSION !== MODEL_ASOF_CONTRACT_VERSION
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CONTRACT_VERSION_MISMATCH',
            'model-as-of contract binding mismatch'
        );
    }
    const decision = canonicalTimestamp(context.MODEL_DECISION_TIME_UTC, 'MODEL_DECISION_TIME_UTC');
    const feature = canonicalTimestamp(context.FEATURE_AS_OF_UTC, 'FEATURE_AS_OF_UTC');
    const kickoff = canonicalTimestamp(context.TARGET_KICKOFF_UTC, 'TARGET_KICKOFF_UTC');
    if (decision !== feature) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_CONTEXT_MISMATCH',
            'FEATURE_AS_OF_UTC must equal T'
        );
    }
    if (Date.parse(decision) >= Date.parse(kickoff)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_CONTEXT_MISMATCH',
            'T must be before target kickoff'
        );
    }
    return { ...context, MODEL_DECISION_TIME_UTC: decision, FEATURE_AS_OF_UTC: feature, TARGET_KICKOFF_UTC: kickoff };
}

function validateCaptureBinding(value) {
    const binding = exactObject(value, RUNTIME_CAPTURE_BINDING_FIELDS, 'RUNTIME_CAPTURE_BINDING');
    if (
        binding.RUNTIME_CAPTURE_CONTRACT_ID !== RUNTIME_CAPTURE_CONTRACT_ID ||
        binding.RUNTIME_CAPTURE_CONTRACT_VERSION !== RUNTIME_CAPTURE_CONTRACT_VERSION
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CONTRACT_VERSION_MISMATCH',
            'runtime-capture contract binding mismatch'
        );
    }
    text(binding.CAPTURE_INSTANCE_ID, 'CAPTURE_INSTANCE_ID', { safeId: true });
    const digest = sha256(binding.CAPTURE_CONTENT_DIGEST, 'CAPTURE_CONTENT_DIGEST');
    if (binding.CAPTURE_INSTANCE_ID === digest) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CAPTURE_IDENTITY_COLLISION',
            'capture instance must differ from content digest'
        );
    }
    return {
        ...binding,
        CAPTURE_SELECTED_EVIDENCE_IDS: sortedUniqueIds(
            binding.CAPTURE_SELECTED_EVIDENCE_IDS,
            'CAPTURE_SELECTED_EVIDENCE_IDS'
        ),
    };
}

function validateAttestation(value, index) {
    const label = `EVIDENCE_ATTESTATIONS[${index}]`;
    const attestation = cloneJson(exactObject(value, EVIDENCE_ATTESTATION_FIELDS, label));
    text(attestation.EVIDENCE_ID, `${label}.EVIDENCE_ID`, { safeId: true });
    text(attestation.SOURCE_FAMILY, `${label}.SOURCE_FAMILY`, { safeId: true });
    optionalText(attestation.SOURCE_AUTHORITY_ID, `${label}.SOURCE_AUTHORITY_ID`, { safeId: true });
    optionalText(attestation.SOURCE_RECORD_ID, `${label}.SOURCE_RECORD_ID`, { safeId: true });
    text(attestation.PAYLOAD_KIND, `${label}.PAYLOAD_KIND`, { safeId: true });
    if (!['BYTE_BLOB', 'CANONICAL_JSON'].includes(attestation.PAYLOAD_KIND)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            `${label}.PAYLOAD_KIND unsupported`
        );
    }
    sha256(attestation.PAYLOAD_CONTENT_DIGEST, `${label}.PAYLOAD_CONTENT_DIGEST`);
    if (!Number.isInteger(attestation.PAYLOAD_BYTE_LENGTH) || attestation.PAYLOAD_BYTE_LENGTH < 0) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            `${label}.PAYLOAD_BYTE_LENGTH malformed`
        );
    }
    ['SOURCE_EVENT_TIME_UTC', 'SOURCE_EFFECTIVE_TIME_UTC', 'SOURCE_OBSERVED_AT_UTC', 'SOURCE_CAPTURED_AT_UTC'].forEach(
        field => {
            if (attestation[field] !== null) {
                attestation[field] = canonicalTimestamp(attestation[field], `${label}.${field}`);
            }
        }
    );
    const proof = attestation.AVAILABILITY_PROOF_DATA;
    switch (attestation.AVAILABILITY_PROOF_KIND) {
        case 'EXACT_OBSERVATION_TIMESTAMP':
            if (
                JSON.stringify(proof) !== JSON.stringify({ observed_at_field: 'SOURCE_OBSERVED_AT_UTC' }) ||
                attestation.SOURCE_OBSERVED_AT_UTC === null
            ) {
                throw new StandingsAsOfRuntimeSourceNormalizationError(
                    'NORMALIZATION_SCHEMA_MISMATCH',
                    `${label} observation proof malformed`
                );
            }
            break;
        case 'EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF':
            if (
                JSON.stringify(proof) !==
                    JSON.stringify({
                        effective_time_field: 'SOURCE_EFFECTIVE_TIME_UTC',
                        observed_at_field: 'SOURCE_OBSERVED_AT_UTC',
                    }) ||
                attestation.SOURCE_EFFECTIVE_TIME_UTC === null ||
                attestation.SOURCE_OBSERVED_AT_UTC === null
            ) {
                throw new StandingsAsOfRuntimeSourceNormalizationError(
                    'NORMALIZATION_SCHEMA_MISMATCH',
                    `${label} effective proof malformed`
                );
            }
            break;
        case 'BOUNDED_INTERVAL_ENTIRELY_BEFORE_T':
            if (
                !isPlainObject(proof) ||
                Object.keys(proof).sort(compareUnicodeCodePoints).join('|') !== 'end_utc|start_utc'
            ) {
                throw new StandingsAsOfRuntimeSourceNormalizationError(
                    'NORMALIZATION_SCHEMA_MISMATCH',
                    `${label} interval proof malformed`
                );
            }
            attestation.AVAILABILITY_PROOF_DATA = {
                start_utc: canonicalTimestamp(proof.start_utc, `${label}.start_utc`),
                end_utc: canonicalTimestamp(proof.end_utc, `${label}.end_utc`),
            };
            break;
        default:
            throw new StandingsAsOfRuntimeSourceNormalizationError(
                'NORMALIZATION_SCHEMA_MISMATCH',
                `${label} proof kind unsupported`
            );
    }
    if (attestation.SOURCE_PROVENANCE_STATUS !== 'UNKNOWN') {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'SOURCE_AUTHORITY_PROOF_UNAVAILABLE',
            'generic normalization cannot upgrade source provenance'
        );
    }
    return attestation;
}

function validateFactBinding(value, index, standingsEvidenceIds) {
    const label = `FACT_BINDINGS[${index}]`;
    const binding = exactObject(value, FACT_BINDING_FIELDS, label);
    text(binding.BINDING_ID, `${label}.BINDING_ID`, { safeId: true });
    if (!FACT_BINDING_ROLES.has(binding.SEMANTIC_ROLE) || !DERIVATIONS.has(binding.DERIVATION)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            `${label} role/derivation malformed`
        );
    }
    text(binding.DOMAIN_IDENTITY, `${label}.DOMAIN_IDENTITY`, { safeId: true });
    const sourceIds = sortedUniqueIds(binding.SOURCE_EVIDENCE_IDS, `${label}.SOURCE_EVIDENCE_IDS`);
    if (binding.DERIVATION === 'SOURCE_ATTESTED' && sourceIds.length === 0) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'FACT_LINEAGE_MISSING',
            `${label} source lineage is required`
        );
    }
    if (sourceIds.some(id => !standingsEvidenceIds.includes(id))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'FACT_EVIDENCE_NOT_SELECTED',
            `${label} references unselected evidence`
        );
    }
    optionalText(binding.CANONICAL_MATCH_ID, `${label}.CANONICAL_MATCH_ID`, { safeId: true });
    optionalText(binding.ADJUSTMENT_ID, `${label}.ADJUSTMENT_ID`, { safeId: true });
    optionalText(binding.AVAILABILITY_EVIDENCE_ID, `${label}.AVAILABILITY_EVIDENCE_ID`, { safeId: true });
    if (binding.AVAILABILITY_EVIDENCE_ID !== null && !sourceIds.includes(binding.AVAILABILITY_EVIDENCE_ID)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'AVAILABILITY_EVIDENCE_UNBOUND',
            `${label} availability evidence is not in lineage`
        );
    }
    sha256(binding.NORMALIZED_FACT_DIGEST, `${label}.NORMALIZED_FACT_DIGEST`);
    if (computeFactBindingDigest(binding) !== binding.NORMALIZED_FACT_DIGEST) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('FACT_DIGEST_MISMATCH', `${label} digest mismatch`);
    }
    return { ...binding, SOURCE_EVIDENCE_IDS: sourceIds };
}

function validateOutputBinding(value, context, stateIds, adjustmentIds) {
    const binding = cloneJson(
        exactObject(value, OUTPUT_STANDINGS_INPUT_BINDING_FIELDS, 'OUTPUT_STANDINGS_INPUT_BINDING')
    );
    if (
        binding.STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID !== STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID ||
        binding.STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION !== STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CONTRACT_VERSION_MISMATCH',
            'standings input contract binding mismatch'
        );
    }
    if (
        binding.STANDINGS_RANKING_CONTRACT_ID !== STANDINGS_CONTRACT_ID ||
        binding.STANDINGS_RANKING_CONTRACT_VERSION !== STANDINGS_CONTRACT_VERSION
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CONTRACT_VERSION_MISMATCH',
            'standings ranking contract binding mismatch'
        );
    }
    sha256(binding.CANONICAL_INPUT_DIGEST, 'CANONICAL_INPUT_DIGEST');
    ['MODEL_DECISION_TIME_UTC', 'FEATURE_AS_OF_UTC', 'TARGET_KICKOFF_UTC'].forEach(field => {
        binding[field] = canonicalTimestamp(binding[field], field);
        if (binding[field] !== context[field]) {
            throw new StandingsAsOfRuntimeSourceNormalizationError(
                'OUTPUT_INPUT_CONTEXT_MISMATCH',
                `output binding ${field} mismatch`
            );
        }
    });
    text(binding.TARGET_MATCH_ID, 'OUTPUT_STANDINGS_INPUT_BINDING.TARGET_MATCH_ID', { safeId: true });
    if (binding.TARGET_MATCH_ID !== context.TARGET_MATCH_ID) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_CONTEXT_MISMATCH',
            'output target mismatch'
        );
    }
    text(binding.FIXTURE_UNIVERSE_REFERENCE_ID, 'FIXTURE_UNIVERSE_REFERENCE_ID', { safeId: true });
    binding.FIXTURE_STATE_IDS = sortedUniqueIds(binding.FIXTURE_STATE_IDS, 'FIXTURE_STATE_IDS');
    if (JSON.stringify(binding.FIXTURE_STATE_IDS) !== JSON.stringify(stateIds)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_BINDING_MISMATCH',
            'fixture state identity set is not canonical'
        );
    }
    binding.ADMINISTRATIVE_ADJUSTMENT_IDS = sortedUniqueIds(
        binding.ADMINISTRATIVE_ADJUSTMENT_IDS,
        'ADMINISTRATIVE_ADJUSTMENT_IDS'
    );
    if (JSON.stringify(binding.ADMINISTRATIVE_ADJUSTMENT_IDS) !== JSON.stringify(adjustmentIds)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_BINDING_MISMATCH',
            'adjustment identity set is not canonical'
        );
    }
    sha256(binding.OUTPUT_INPUT_BINDING_DIGEST, 'OUTPUT_INPUT_BINDING_DIGEST');
    if (computeOutputInputBindingDigest(binding) !== binding.OUTPUT_INPUT_BINDING_DIGEST) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_BINDING_DIGEST_MISMATCH',
            'output binding digest mismatch'
        );
    }
    return binding;
}

function validateStatus(value) {
    const status = exactObject(value, STATUS_FIELDS, 'STATUS');
    const expected = {
        NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY: 'PROVEN',
        CAPTURE_BINDING_VALIDITY: 'PROVEN',
        OUTPUT_INPUT_BINDING_VALIDITY: 'NOT_PROVEN',
        SOURCE_SEMANTIC_NORMALIZATION_VALIDITY: 'NOT_PROVEN',
        SOURCE_AUTHORITY_VALIDITY: 'NOT_PROVEN',
        SOURCE_STREAM_COMPLETENESS: 'NOT_PROVEN',
        RUNTIME_NUMERIC_ELIGIBILITY: 'NO',
    };
    if (stableStringify(status) !== stableStringify(expected)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_STATUS_MISMATCH',
            'generic envelope status overclaims readiness'
        );
    }
    return { ...status };
}

function validateNormalizationEnvelopeStructure(envelope) {
    rejectSecretKeys(envelope);
    const value = exactObject(envelope, NORMALIZATION_ENVELOPE_FIELDS, 'normalization envelope');
    if (
        value.NORMALIZATION_CONTRACT_ID !== NORMALIZATION_CONTRACT_ID ||
        value.NORMALIZATION_CONTRACT_VERSION !== NORMALIZATION_CONTRACT_VERSION
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CONTRACT_VERSION_MISMATCH',
            'normalization contract identity mismatch'
        );
    }
    text(value.NORMALIZATION_INSTANCE_ID, 'NORMALIZATION_INSTANCE_ID', { safeId: true });
    sha256(value.NORMALIZATION_CONTENT_DIGEST, 'NORMALIZATION_CONTENT_DIGEST');
    const context = validateContext(value.PREDICTION_CONTEXT);
    const capture = validateCaptureBinding(value.RUNTIME_CAPTURE_BINDING);
    const standingsEvidenceIds = sortedUniqueIds(value.STANDINGS_EVIDENCE_IDS, 'STANDINGS_EVIDENCE_IDS');
    if (standingsEvidenceIds.some(id => !capture.CAPTURE_SELECTED_EVIDENCE_IDS.includes(id))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'STANDINGS_EVIDENCE_NOT_SELECTED',
            'standings evidence is outside capture selection'
        );
    }
    if (!Array.isArray(value.EVIDENCE_ATTESTATIONS) || !Array.isArray(value.FACT_BINDINGS)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_SCHEMA_MISMATCH',
            'evidence attestations and fact bindings must be arrays'
        );
    }
    const outputValue = exactObject(
        value.OUTPUT_STANDINGS_INPUT_BINDING,
        OUTPUT_STANDINGS_INPUT_BINDING_FIELDS,
        'OUTPUT_STANDINGS_INPUT_BINDING'
    );
    const attestations = value.EVIDENCE_ATTESTATIONS.map(validateAttestation);
    const attestationIds = attestations.map(row => row.EVIDENCE_ID);
    if (
        new Set(attestationIds).size !== attestationIds.length ||
        JSON.stringify(sortUnicodeCodePoints(attestationIds)) !== JSON.stringify(standingsEvidenceIds)
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'ATTESTATION_SET_MISMATCH',
            'attestations must exactly cover standings evidence'
        );
    }
    attestations.sort((left, right) => compareUnicodeCodePoints(left.EVIDENCE_ID, right.EVIDENCE_ID));
    const stateIds = sortedUniqueIds(outputValue.FIXTURE_STATE_IDS, 'FIXTURE_STATE_IDS');
    const adjustmentIds = sortedUniqueIds(outputValue.ADMINISTRATIVE_ADJUSTMENT_IDS, 'ADMINISTRATIVE_ADJUSTMENT_IDS');
    const facts = value.FACT_BINDINGS.map((row, index) => validateFactBinding(row, index, standingsEvidenceIds));
    const factIds = facts.map(row => row.BINDING_ID);
    if (new Set(factIds).size !== factIds.length) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'FACT_BINDING_ORDER_MISMATCH',
            'fact bindings must be unique'
        );
    }
    facts.sort((left, right) => compareUnicodeCodePoints(left.BINDING_ID, right.BINDING_ID));
    const output = validateOutputBinding(value.OUTPUT_STANDINGS_INPUT_BINDING, context, stateIds, adjustmentIds);
    const statuses = validateStatus(value.STATUS);
    if (computeNormalizationContentDigest(value) !== value.NORMALIZATION_CONTENT_DIGEST) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'NORMALIZATION_CONTENT_DIGEST_MISMATCH',
            'normalization content digest mismatch'
        );
    }
    return {
        valid: true,
        normalizationInstanceId: value.NORMALIZATION_INSTANCE_ID,
        normalizationContentDigest: value.NORMALIZATION_CONTENT_DIGEST,
        predictionContext: context,
        runtimeCaptureBinding: capture,
        standingsEvidenceIds,
        evidenceAttestations: attestations,
        evidenceAttestationsById: Object.fromEntries(attestations.map(row => [row.EVIDENCE_ID, row])),
        factBindings: facts,
        outputStandingsInputBinding: output,
        statuses,
    };
}

function validateLineage(lineage, label, envelopeResult, factByEvidence) {
    if (
        !isPlainObject(lineage) ||
        Object.keys(lineage).sort(compareUnicodeCodePoints).join('|') !== 'evidenceRefs|sourceRecordRef'
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('OUTPUT_LINEAGE_INVALID', `${label} malformed`);
    }
    const evidenceRefs = sortedUniqueIds(lineage.evidenceRefs, `${label}.evidenceRefs`);
    if (evidenceRefs.length === 0 || evidenceRefs.some(id => !envelopeResult.standingsEvidenceIds.includes(id))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_LINEAGE_INVALID',
            `${label} references unselected evidence`
        );
    }
    if (evidenceRefs.some(id => !factByEvidence.has(id))) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_LINEAGE_INVALID',
            `${label} has no fact binding`
        );
    }
    const attestationsById = Object.fromEntries(envelopeResult.evidenceAttestations.map(row => [row.EVIDENCE_ID, row]));
    const expectedSourceRecordRef = sourceRecordRefForEvidenceIds(
        envelopeResult.runtimeCaptureBinding.CAPTURE_CONTENT_DIGEST,
        evidenceRefs,
        attestationsById
    );
    if (lineage.sourceRecordRef !== expectedSourceRecordRef) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'SOURCE_RECORD_REF_MISMATCH',
            `${label} sourceRecordRef mismatch`
        );
    }
    return evidenceRefs;
}

function validateProofRef(proofRef, label, envelopeResult) {
    text(proofRef, label, { safeId: true });
    if (!envelopeResult.standingsEvidenceIds.includes(proofRef)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'PROOF_REF_UNBOUND',
            `${label} must equal a selected evidence ID`
        );
    }
    if (!Object.prototype.hasOwnProperty.call(envelopeResult.evidenceAttestationsById, proofRef)) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'PROOF_REF_UNBOUND',
            `${label} has no matching canonical evidence attestation`
        );
    }
    return proofRef;
}

function validateStandingsAsOfRuntimeSourceNormalization(envelope, candidateInput) {
    const envelopeResult = validateNormalizationEnvelopeStructure(envelope);
    const before = JSON.stringify(candidateInput);
    let inputResult;
    try {
        inputResult = validateStandingsAsOfEngineInput(candidateInput);
    } catch (error) {
        throw new StandingsAsOfRuntimeSourceNormalizationError('STANDINGS_INPUT_INVALID', error.message);
    }
    if (JSON.stringify(candidateInput) !== before) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'CALLER_INPUT_MUTATED',
            'input validator mutated caller input'
        );
    }
    const normalizedInput = inputResult.normalizedInput;
    const outputBinding = envelopeResult.outputStandingsInputBinding;
    const stateIds = sortUnicodeCodePoints(normalizedInput.fixture_states.map(row => row.canonicalMatchId));
    const adjustmentIds = sortUnicodeCodePoints(
        normalizedInput.administrative_adjustments.map(row => row.adjustmentId)
    );
    if (
        inputResult.canonicalDigest !== outputBinding.CANONICAL_INPUT_DIGEST ||
        outputBinding.TARGET_MATCH_ID !== normalizedInput.target.canonicalMatchId ||
        outputBinding.TARGET_KICKOFF_UTC !==
            canonicalTimestamp(normalizedInput.target.targetKickoffUtc, 'target.targetKickoffUtc') ||
        outputBinding.FIXTURE_UNIVERSE_REFERENCE_ID !== normalizedInput.fixture_universe.reference.referenceId ||
        JSON.stringify(outputBinding.FIXTURE_STATE_IDS) !== JSON.stringify(stateIds) ||
        JSON.stringify(outputBinding.ADMINISTRATIVE_ADJUSTMENT_IDS) !== JSON.stringify(adjustmentIds)
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_BINDING_MISMATCH',
            'candidate standings input does not match envelope binding'
        );
    }
    const context = envelopeResult.predictionContext;
    if (
        canonicalTimestamp(normalizedInput.model_decision_time_utc, 'model_decision_time_utc') !==
            context.MODEL_DECISION_TIME_UTC ||
        canonicalTimestamp(normalizedInput.feature_as_of_utc, 'feature_as_of_utc') !== context.FEATURE_AS_OF_UTC
    ) {
        throw new StandingsAsOfRuntimeSourceNormalizationError(
            'OUTPUT_INPUT_CONTEXT_MISMATCH',
            'candidate T differs from envelope'
        );
    }
    const factByEvidence = new Map();
    envelopeResult.factBindings.forEach(binding =>
        binding.SOURCE_EVIDENCE_IDS.forEach(id => factByEvidence.set(id, binding))
    );
    const lineage = (value, label) => validateLineage(value, label, envelopeResult, factByEvidence);
    normalizedInput.fixture_universe.fixtures.forEach((fixture, index) =>
        lineage(fixture.sourceLineage, `fixtureUniverse.fixtures[${index}].sourceLineage`)
    );
    lineage(normalizedInput.target.sourceLineage, 'target.sourceLineage');
    normalizedInput.fixture_states.forEach((state, index) => {
        lineage(
            {
                evidenceRefs: state.basis.evidenceRefs,
                sourceRecordRef: sourceRecordRefForEvidenceIds(
                    envelopeResult.runtimeCaptureBinding.CAPTURE_CONTENT_DIGEST,
                    state.basis.evidenceRefs,
                    Object.fromEntries(envelopeResult.evidenceAttestations.map(row => [row.EVIDENCE_ID, row]))
                ),
            },
            `fixtureStates[${index}].basis`
        );
        if (state.basis.availabilityProofRef !== null) {
            validateProofRef(
                state.basis.availabilityProofRef,
                `fixtureStates[${index}].basis.availabilityProofRef`,
                envelopeResult
            );
        }
        if (state.state === 'RESULT_AVAILABLE_AT_T') {
            lineage(state.result.sourceLineage, `fixtureStates[${index}].result.sourceLineage`);
            validateProofRef(
                state.result.availabilityProof.proofRef,
                `fixtureStates[${index}].result.availabilityProof.proofRef`,
                envelopeResult
            );
            const fact = envelopeResult.factBindings.find(
                row => row.SEMANTIC_ROLE === 'RESULT' && row.CANONICAL_MATCH_ID === state.canonicalMatchId
            );
            if (!fact || fact.AVAILABILITY_EVIDENCE_ID !== state.result.availabilityProof.proofRef) {
                throw new StandingsAsOfRuntimeSourceNormalizationError(
                    'PROOF_REF_UNBOUND',
                    `fixtureStates[${index}] result proof is not fact-bound`
                );
            }
        }
    });
    normalizedInput.administrative_adjustments.forEach((adjustment, index) => {
        lineage(adjustment.sourceLineage, `administrativeAdjustments[${index}].sourceLineage`);
        validateProofRef(
            adjustment.availabilityProof.proofRef,
            `administrativeAdjustments[${index}].availabilityProof.proofRef`,
            envelopeResult
        );
        const fact = envelopeResult.factBindings.find(
            row => row.SEMANTIC_ROLE === 'ADMIN_ADJUSTMENT' && row.ADJUSTMENT_ID === adjustment.adjustmentId
        );
        if (!fact || fact.AVAILABILITY_EVIDENCE_ID !== adjustment.availabilityProof.proofRef) {
            throw new StandingsAsOfRuntimeSourceNormalizationError(
                'PROOF_REF_UNBOUND',
                `administrativeAdjustments[${index}] proof is not fact-bound`
            );
        }
    });
    const status = {
        NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY: 'PROVEN',
        CAPTURE_BINDING_VALIDITY: 'PROVEN',
        OUTPUT_INPUT_BINDING_VALIDITY: 'PROVEN',
        SOURCE_SEMANTIC_NORMALIZATION_VALIDITY: 'NOT_PROVEN',
        SOURCE_AUTHORITY_VALIDITY: 'NOT_PROVEN',
        SOURCE_STREAM_COMPLETENESS: 'NOT_PROVEN',
        RUNTIME_NUMERIC_ELIGIBILITY: 'NO',
    };
    return {
        valid: true,
        normalizedInput,
        canonicalInputDigest: inputResult.canonicalDigest,
        normalizationContentDigest: envelopeResult.normalizationContentDigest,
        statuses: status,
        sourceAuthority: {
            sourceSemanticNormalizationValidity: 'NOT_PROVEN',
            sourceAuthorityValidity: 'NOT_PROVEN',
            sourceStreamCompleteness: 'NOT_PROVEN',
            runtimeNumericEligibility: 'NO',
        },
    };
}

module.exports = {
    CANONICAL_SERIALIZATION,
    FACT_BINDING_FIELDS,
    FACT_BINDING_ROLES,
    NORMALIZATION_CONTENT_DIGEST_ALGORITHM,
    NORMALIZATION_CONTENT_DIGEST_SCOPE,
    NORMALIZATION_CONTRACT_ID,
    NORMALIZATION_CONTRACT_STATUS,
    NORMALIZATION_CONTRACT_VERSION,
    NORMALIZATION_ENVELOPE_FIELDS,
    StandingsAsOfRuntimeSourceNormalizationError,
    compareUnicodeCodePoints,
    computeFactBindingDigest,
    computeNormalizationContentDigest,
    computeOutputInputBindingDigest,
    sourceRecordRefForEvidenceIds,
    sortUnicodeCodePoints,
    validateNormalizationEnvelopeStructure,
    validateStandingsAsOfRuntimeSourceNormalization,
};
