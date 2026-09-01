'use strict';
/* eslint-disable complexity -- transaction manifest validates independent fail-closed invariants. */

// Transaction-v1 is intentionally a pure contract module.  It neither scans
// directories nor publishes files; identities are derived only from canonical
// supplied content.
const { sha256Text, stableStringify, isUtcTimestamp } = require('./contracts');
const { validateAllocationSnapshot } = require('../fixture_universe/FixtureUniverse');

const TRANSACTION_SCHEMA_VERSION = 'footballprediction-market-evidence-transaction/v1';
const STORE_SCHEMA_VERSION = 'footballprediction-market-evidence-transaction-store/v1';
const STORE_TYPE = 'market-evidence-transaction-v1';
const MARKER_SCHEMA_VERSION = 'footballprediction-market-evidence-transaction-commit/v1';
const METADATA_SCHEMA_VERSION = 'footballprediction-market-evidence-transaction-metadata/v1';
const REGISTRY_DELTA_SCHEMA_VERSION = 'footballprediction-market-evidence-registry-delta/v1';
const ARTIFACT_FILES = Object.freeze([
    'identity_decisions.jsonl',
    'observations.jsonl',
    'registry_delta.json',
    'metadata.json',
]);
const TRANSACTION_FILES = Object.freeze([...ARTIFACT_FILES, 'manifest.json', 'COMMITTED']);
const HEX_64 = /^[a-f0-9]{64}$/;
const TX_ID = /^tx_[a-f0-9]{64}$/;

function canonicalJson(value) { return stableStringify(value); }
function canonicalBytes(value) { return `${canonicalJson(value)}\n`; }
function hashCanonical(value) { return sha256Text(canonicalJson(value)); }
function assertHash(value, label) { if (typeof value !== 'string' || !HEX_64.test(value)) throw new Error(`${label} must be lowercase SHA-256`); }
function assertPlainObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) throw new Error(`${label} must be a plain object`);
}
function assertExactKeys(value, keys, label) {
    assertPlainObject(value, label);
    const allowed = new Set(keys);
    const unknown = Object.keys(value).find(key => !allowed.has(key));
    if (unknown) throw new Error(`${label} contains unknown field: ${unknown}`);
    const missing = keys.find(key => !Object.prototype.hasOwnProperty.call(value, key));
    if (missing) throw new Error(`${label} requires ${missing}`);
}
function descriptorForBytes(path, bytes, recordCount, semanticBytes = bytes) {
    if (!ARTIFACT_FILES.includes(path)) throw new Error(`unsupported transaction artifact: ${path}`);
    if (typeof bytes !== 'string') throw new Error('artifact bytes must be text');
    if (!Number.isInteger(recordCount) || recordCount < 0) throw new Error('artifact record count is invalid');
    if (typeof semanticBytes !== 'string') throw new Error('artifact semantic bytes must be text');
    return Object.freeze({ path, sha256: sha256Text(bytes), byte_count: Buffer.byteLength(bytes, 'utf8'), semantic_sha256: sha256Text(semanticBytes), record_count: recordCount });
}
function validateArtifactDescriptor(value, expectedPath = null) {
    assertExactKeys(value, ['path', 'sha256', 'byte_count', 'semantic_sha256', 'record_count'], 'artifact descriptor');
    if (!ARTIFACT_FILES.includes(value.path) || (expectedPath && value.path !== expectedPath)) throw new Error('artifact descriptor path is invalid');
    assertHash(value.sha256, 'artifact descriptor sha256');
    assertHash(value.semantic_sha256, 'artifact descriptor semantic_sha256');
    if (!Number.isInteger(value.byte_count) || value.byte_count < 0 || !Number.isInteger(value.record_count) || value.record_count < 0) throw new Error('artifact descriptor counts are invalid');
    return Object.freeze({ ...value });
}
function validateAllocationBinding(value) {
    assertExactKeys(value, ['allocation_schema_version', 'allocation_content_hash', 'allocation_artifact_sha256', 'allocation_provenance_raw_sha256', 'allocation_snapshot'], 'allocation binding');
    if (typeof value.allocation_schema_version !== 'string' || !value.allocation_schema_version) throw new Error('allocation schema version is invalid');
    for (const key of ['allocation_content_hash', 'allocation_artifact_sha256', 'allocation_provenance_raw_sha256']) assertHash(value[key], key);
    const snapshot = validateAllocationSnapshot(value.allocation_snapshot, value.allocation_provenance_raw_sha256);
    if (snapshot.schema_version !== value.allocation_schema_version || snapshot.content_sha256 !== value.allocation_content_hash) throw new Error('allocation binding does not match the full allocation snapshot');
    return Object.freeze({ ...value, allocation_snapshot: Object.freeze(JSON.parse(canonicalJson(snapshot))) });
}
function validateSource(value) {
    assertExactKeys(value, ['provider', 'capture_id', 'raw_sha256', 'receipt_sha256'], 'transaction source');
    if (typeof value.provider !== 'string' || !value.provider || typeof value.capture_id !== 'string' || !value.capture_id) throw new Error('transaction source identity is invalid');
    assertHash(value.raw_sha256, 'raw_sha256'); assertHash(value.receipt_sha256, 'receipt_sha256');
    return Object.freeze({ ...value });
}
function validateVersions(value) {
    assertExactKeys(value, ['resolver_version', 'ruleset_version', 'adapter_version', 'projection_version', 'registry_schema_version', 'registry_version', 'observation_schema_version'], 'transaction versions');
    for (const key of Object.keys(value)) if (typeof value[key] !== 'string' || !value[key]) throw new Error(`transaction version is invalid: ${key}`);
    return Object.freeze({ ...value });
}
function computeLogicalBatchKey({ source, allocation, versions }) {
    source = validateSource(source); allocation = validateAllocationBinding(allocation); versions = validateVersions(versions);
    return hashCanonical({ provider: source.provider, capture_id: source.capture_id, allocation_hash: allocation.allocation_content_hash, adapter_version: versions.adapter_version, projection_version: versions.projection_version, ruleset_version: versions.ruleset_version, resolver_version: versions.resolver_version, observation_schema_version: versions.observation_schema_version });
}
function computeLogicalContentHash({ source, artifacts }) {
    source = validateSource(source); const descriptors = artifactMap(artifacts);
    return hashCanonical({ source, artifacts: Object.fromEntries(ARTIFACT_FILES.map(path => [path, { path, semantic_sha256: descriptors[path].semantic_sha256, record_count: descriptors[path].record_count }])) });
}
function artifactMap(artifacts) {
    assertPlainObject(artifacts, 'transaction artifacts');
    const keys = Object.keys(artifacts).sort();
    if (canonicalJson(keys) !== canonicalJson([...ARTIFACT_FILES].sort())) throw new Error('transaction artifacts must have the exact artifact set');
    const out = {};
    for (const path of ARTIFACT_FILES) out[path] = validateArtifactDescriptor(artifacts[path], path);
    return Object.freeze(out);
}
function computeBatchContentHash(artifacts) {
    const descriptors = artifactMap(artifacts);
    return hashCanonical({ artifacts: Object.fromEntries(ARTIFACT_FILES.map(path => [path, descriptors[path]])) });
}
function transactionContentFields(manifest) {
    return {
        schema_version: manifest.schema_version,
        sequence: manifest.sequence,
        parent_transaction_id: manifest.parent_transaction_id,
        parent_transaction_content_hash: manifest.parent_transaction_content_hash,
        expected_parent_state_hash: manifest.expected_parent_state_hash,
        logical_batch_key: manifest.logical_batch_key,
        logical_content_hash: manifest.logical_content_hash,
        batch_content_hash: manifest.batch_content_hash,
        post_state_hash: manifest.post_state_hash,
        allocation: manifest.allocation,
        source: manifest.source,
        versions: manifest.versions,
        artifacts: manifest.artifacts,
        decision_count: manifest.decision_count,
        observation_count: manifest.observation_count,
        registry_delta_count: manifest.registry_delta_count,
        quarantine_count: manifest.quarantine_count,
        publication_metadata: manifest.publication_metadata,
    };
}
function computeTransactionContentHash(manifest) { return hashCanonical(transactionContentFields(manifest)); }
function computeTransactionId(manifest) { return `tx_${computeTransactionContentHash(manifest)}`; }
function manifestWithoutHash(manifest) { const copy = { ...manifest }; delete copy.manifest_sha256; return copy; }
function computeManifestHash(manifest) { return hashCanonical(manifestWithoutHash(manifest)); }
function validatePublicationMetadata(value) {
    assertPlainObject(value, 'publication_metadata');
    const allowed = new Set(['schema_version', 'prepared_at', 'committed_at', 'knowledge_time']);
    const unknown = Object.keys(value).find(key => !allowed.has(key));
    if (unknown) throw new Error(`publication_metadata contains unknown field: ${unknown}`);
    if (value.schema_version !== undefined && (typeof value.schema_version !== 'string' || !value.schema_version)) throw new Error('publication_metadata schema_version is invalid');
    for (const key of ['prepared_at', 'committed_at', 'knowledge_time']) {
        if (value[key] !== undefined && value[key] !== null && typeof value[key] !== 'string') throw new Error(`publication_metadata ${key} is invalid`);
    }
    if (value.knowledge_time !== undefined && value.knowledge_time !== null && !isUtcTimestamp(value.knowledge_time)) throw new Error('publication_metadata knowledge_time must be UTC ISO-8601');
    return Object.freeze({ ...value });
}
const MANIFEST_KEYS = Object.freeze(['schema_version', 'transaction_id', 'sequence', 'logical_batch_key', 'logical_content_hash', 'batch_content_hash', 'transaction_content_hash', 'parent_transaction_id', 'parent_transaction_content_hash', 'expected_parent_state_hash', 'post_state_hash', 'allocation', 'source', 'versions', 'artifacts', 'decision_count', 'observation_count', 'registry_delta_count', 'quarantine_count', 'publication_metadata', 'manifest_sha256']);
function validateManifest(manifest) {
    assertExactKeys(manifest, MANIFEST_KEYS, 'transaction manifest');
    if (manifest.schema_version !== TRANSACTION_SCHEMA_VERSION) throw new Error('transaction manifest schema_version is invalid');
    if (!TX_ID.test(manifest.transaction_id)) throw new Error('transaction_id is invalid');
    if (!Number.isInteger(manifest.sequence) || manifest.sequence < 1) throw new Error('transaction sequence is invalid');
    for (const key of ['logical_batch_key', 'logical_content_hash', 'batch_content_hash', 'transaction_content_hash', 'expected_parent_state_hash', 'post_state_hash', 'manifest_sha256']) assertHash(manifest[key], key);
    if (manifest.parent_transaction_id !== null && !TX_ID.test(manifest.parent_transaction_id)) throw new Error('parent_transaction_id is invalid');
    if (manifest.parent_transaction_content_hash !== null) assertHash(manifest.parent_transaction_content_hash, 'parent_transaction_content_hash');
    if ((manifest.parent_transaction_id === null) !== (manifest.parent_transaction_content_hash === null)) throw new Error('parent transaction fields must both be null or both be present');
    const allocation = validateAllocationBinding(manifest.allocation); const source = validateSource(manifest.source); const versions = validateVersions(manifest.versions); const artifacts = artifactMap(manifest.artifacts);
    for (const key of ['decision_count', 'observation_count', 'registry_delta_count', 'quarantine_count']) if (!Number.isInteger(manifest[key]) || manifest[key] < 0) throw new Error(`transaction ${key} is invalid`);
    validatePublicationMetadata(manifest.publication_metadata);
    if (manifest.logical_batch_key !== computeLogicalBatchKey({ source, allocation, versions })) throw new Error('logical_batch_key does not match transaction inputs');
    if (manifest.logical_content_hash !== computeLogicalContentHash({ source, artifacts })) throw new Error('logical_content_hash does not match transaction inputs');
    if (manifest.batch_content_hash !== computeBatchContentHash(artifacts)) throw new Error('batch_content_hash does not match artifacts');
    if (manifest.transaction_content_hash !== computeTransactionContentHash(manifest) || manifest.transaction_id !== computeTransactionId(manifest)) throw new Error('transaction content identity is invalid');
    if (manifest.manifest_sha256 !== computeManifestHash(manifest)) throw new Error('manifest_sha256 is invalid');
    return Object.freeze({ ...manifest, allocation, source, versions, artifacts });
}
function createManifest(fields) {
    assertPlainObject(fields, 'manifest fields');
    const base = { ...fields, schema_version: TRANSACTION_SCHEMA_VERSION };
    base.logical_batch_key = computeLogicalBatchKey({ source: base.source, allocation: base.allocation, versions: base.versions });
    base.logical_content_hash = computeLogicalContentHash({ source: base.source, artifacts: base.artifacts });
    base.batch_content_hash = computeBatchContentHash(base.artifacts);
    base.transaction_content_hash = computeTransactionContentHash(base);
    base.transaction_id = `tx_${base.transaction_content_hash}`;
    base.manifest_sha256 = computeManifestHash(base);
    return validateManifest(base);
}
function validateCommittedMarker(marker, manifest) {
    assertExactKeys(marker, ['schema_version', 'transaction_id', 'transaction_content_hash', 'manifest_sha256'], 'COMMITTED marker');
    if (marker.schema_version !== MARKER_SCHEMA_VERSION) throw new Error('COMMITTED marker schema_version is invalid');
    for (const key of ['transaction_content_hash', 'manifest_sha256']) assertHash(marker[key], `COMMITTED ${key}`);
    if (!TX_ID.test(marker.transaction_id)) throw new Error('COMMITTED transaction_id is invalid');
    if (manifest && (marker.transaction_id !== manifest.transaction_id || marker.transaction_content_hash !== manifest.transaction_content_hash || marker.manifest_sha256 !== manifest.manifest_sha256)) throw new Error('COMMITTED marker does not bind manifest');
    return Object.freeze({ ...marker });
}
function createCommittedMarker(manifest) {
    validateManifest(manifest);
    return Object.freeze({ schema_version: MARKER_SCHEMA_VERSION, transaction_id: manifest.transaction_id, transaction_content_hash: manifest.transaction_content_hash, manifest_sha256: manifest.manifest_sha256 });
}
function computeAuthorityStateHash({ allocation, decisions, latestDecisions, activeMatched, registryState, observationIndex }) {
    validateAllocationBinding(allocation);
    const authorityObservation = row => {
        const copy = { ...row };
        // Transaction identity and the parent content chain bind publisher T2.
        // State identity remains a semantic projection so a logical retry can
        // compare authority state independently from publication metadata.
        delete copy.projection_available_at;
        return copy;
    };
    return hashCanonical({
        allocation,
        decisions: [...decisions].map(row => ({ identity_decision_id: row.identity_decision_id, content_hash: hashCanonical(row) })).sort((a, b) => a.identity_decision_id.localeCompare(b.identity_decision_id)),
        latest_decisions: [...latestDecisions].map(([key, row]) => ({ key, identity_decision_id: row.identity_decision_id, content_hash: hashCanonical(row) })).sort((a, b) => a.key.localeCompare(b.key)),
        active_matched: [...activeMatched].map(([key, row]) => ({ key, identity_decision_id: row.identity_decision_id, content_hash: hashCanonical(row) })).sort((a, b) => a.key.localeCompare(b.key)),
        registry_state: [...registryState].map(([key, row]) => ({ key, content_hash: hashCanonical(row) })).sort((a, b) => a.key.localeCompare(b.key)),
        observations: [...observationIndex].map(([observationId, row]) => ({ observation_id: observationId, content_hash: hashCanonical(authorityObservation(row)) })).sort((a, b) => a.observation_id.localeCompare(b.observation_id)),
    });
}

module.exports = { TRANSACTION_SCHEMA_VERSION, STORE_SCHEMA_VERSION, STORE_TYPE, MARKER_SCHEMA_VERSION, METADATA_SCHEMA_VERSION, REGISTRY_DELTA_SCHEMA_VERSION, ARTIFACT_FILES, TRANSACTION_FILES, canonicalJson, canonicalBytes, hashCanonical, descriptorForBytes, validateArtifactDescriptor, validateAllocationBinding, validateSource, validateVersions, computeLogicalBatchKey, computeLogicalContentHash, computeBatchContentHash, computeTransactionContentHash, computeTransactionId, computeManifestHash, validateManifest, createManifest, validateCommittedMarker, createCommittedMarker, computeAuthorityStateHash, assertHash, assertPlainObject };
