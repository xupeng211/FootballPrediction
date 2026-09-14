'use strict';

// Versioned snapshot manifest and completeness-marker contract.
//
// The manifest is the authoritative description of a generation.  The
// completeness marker is deliberately a separate, last-written object that
// binds the manifest's SHA-256.  Splitting them is what makes partial
// generations detectable: a crash between the payload and the marker leaves
// objects that no verifier will accept, and because nothing in this system can
// delete, the partial generation stays as visible evidence rather than being
// quietly cleaned up.
//
// Serialization is canonical, so the manifest hash is a function of content
// alone and not of key order or whitespace.

const crypto = require('node:crypto');

const { canonicalJson, assertHash } = require('../transactionContract');
const { isUtcTimestamp } = require('../contracts');
const { SnapshotIntegrityError } = require('./transport');

function assertManifestTimestamp(value, label) {
    if (typeof value !== 'string' || !isUtcTimestamp(value)) throw new SnapshotIntegrityError(`${label} must be UTC ISO-8601`);
    return value;
}

// Every rejection from this module is a SnapshotIntegrityError.  A caller that
// catches SnapshotIntegrityError to mean "this evidence is not contractual"
// must not have to also catch the shared hash assertion's plain Error.
function assertManifestHash(value, label) {
    try {
        assertHash(value, label);
    } catch (error) {
        throw new SnapshotIntegrityError(error.message);
    }
    return value;
}

const SNAPSHOT_MANIFEST_SCHEMA_VERSION = 'stage-d-independent-backup-snapshot/v1';
const SNAPSHOT_COMPLETENESS_SCHEMA_VERSION = 'stage-d-independent-backup-completeness/v1';
const SUPPORTED_MANIFEST_SCHEMA_VERSIONS = Object.freeze([SNAPSHOT_MANIFEST_SCHEMA_VERSION]);

const MANIFEST_OBJECT_NAME = 'MANIFEST.json';
const COMPLETENESS_OBJECT_NAME = 'COMPLETE';
const PAYLOAD_PREFIX = 'payload';

const SNAPSHOT_GENERATION_ID_PATTERN = /^snap_\d{8}T\d{9}Z_[a-f0-9]{16}$/;

function sha256Hex(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}

// A generation id must be unique, must not be derived from wall-clock seconds
// alone, and must not be the transaction head.  Two backup attempts of the
// same authority have to remain distinguishable, so the head is recorded
// inside the manifest instead of being used as the identity.
function createSnapshotGenerationId({ now = new Date(), randomBytes = crypto.randomBytes } = {}) {
    if (!(now instanceof Date) || Number.isNaN(now.getTime())) throw new SnapshotIntegrityError('a valid Date is required to create a snapshot id');
    const compact = now.toISOString().replace(/[-:.]/g, '');
    const entropy = randomBytes(8).toString('hex');
    // The shape is checked rather than trusted: a malformed id would become a
    // malformed object key, and object keys are the addressing scheme.
    const candidate = `snap_${compact}_${entropy}`;
    return assertGenerationId(candidate);
}

function assertGenerationId(snapshotId) {
    if (typeof snapshotId !== 'string' || !SNAPSHOT_GENERATION_ID_PATTERN.test(snapshotId)) throw new SnapshotIntegrityError(`snapshot generation id is malformed: ${snapshotId}`);
    return snapshotId;
}

function generationPrefix(snapshotId) {
    return assertGenerationId(snapshotId);
}

function manifestObjectKey(snapshotId) {
    return `${generationPrefix(snapshotId)}/${MANIFEST_OBJECT_NAME}`;
}

function completenessObjectKey(snapshotId) {
    return `${generationPrefix(snapshotId)}/${COMPLETENESS_OBJECT_NAME}`;
}

function payloadObjectKey(snapshotId, logicalPath) {
    if (typeof logicalPath !== 'string' || !logicalPath) throw new SnapshotIntegrityError('a logical path is required to derive a payload object key');
    if (logicalPath.startsWith('/') || logicalPath.split('/').some(segment => segment === '' || segment === '.' || segment === '..')) {
        throw new SnapshotIntegrityError(`logical path must be relative and free of traversal segments: ${logicalPath}`);
    }
    return `${generationPrefix(snapshotId)}/${PAYLOAD_PREFIX}/${logicalPath}`;
}

function parseCanonicalJsonObject(bytes, label) {
    if (!Buffer.isBuffer(bytes)) throw new SnapshotIntegrityError(`${label} must be read as bytes`);
    let parsed;
    const text = bytes.toString('utf8');
    try {
        parsed = JSON.parse(text);
    } catch (error) {
        throw new SnapshotIntegrityError(`${label} is not valid JSON: ${error.message}`);
    }
    if (canonicalJson(parsed) !== text) throw new SnapshotIntegrityError(`${label} must use canonical serialization`);
    return parsed;
}

function buildSnapshotManifest(fields) {
    const manifest = {
        schema_version: SNAPSHOT_MANIFEST_SCHEMA_VERSION,
        snapshot_id: fields.snapshot_id,
        created_at: fields.created_at,
        source: fields.source,
        source_before: fields.source_before,
        source_after: fields.source_after,
        source_identity_equal: fields.source_identity_equal,
        store_sha256: fields.store_sha256,
        allocation_authority_sha256: fields.allocation_authority_sha256,
        request_accounting: fields.request_accounting,
        quota_config: fields.quota_config,
        artifacts: fields.artifacts,
        artifact_count: fields.artifacts.length,
        total_bytes: fields.artifacts.reduce((sum, artifact) => sum + artifact.size, 0),
        secrets_included: false,
        completeness_marker: COMPLETENESS_OBJECT_NAME,
    };
    const bytes = Buffer.from(canonicalJson(manifest), 'utf8');
    return Object.freeze({ manifest: Object.freeze(manifest), bytes, sha256: sha256Hex(bytes) });
}

function assertArtifactPathSafety(artifact) {
    const segments = artifact.logical_path.split('/');
    if (artifact.logical_path.startsWith('/') || segments.some(segment => segment === '' || segment === '.' || segment === '..')) {
        throw new SnapshotIntegrityError(`snapshot manifest artifact logical path is unsafe: ${artifact.logical_path}`);
    }
    if (artifact.object_key.split('/').some(segment => segment === '.' || segment === '..')) throw new SnapshotIntegrityError(`snapshot manifest artifact object key is unsafe: ${artifact.object_key}`);
    if (artifact.logical_path.includes('.staging')) throw new SnapshotIntegrityError(`staging must never appear in a snapshot manifest: ${artifact.logical_path}`);
}

function validateManifestArtifact(artifact, seen) {
    if (artifact === null || typeof artifact !== 'object') throw new SnapshotIntegrityError('snapshot manifest artifact must be an object');
    for (const field of ['logical_path', 'object_key', 'category']) {
        if (typeof artifact[field] !== 'string' || !artifact[field]) throw new SnapshotIntegrityError(`snapshot manifest artifact ${field} is required`);
    }
    assertManifestHash(artifact.sha256, `artifact ${artifact.logical_path} sha256`);
    if (!Number.isInteger(artifact.size) || artifact.size < 0) throw new SnapshotIntegrityError(`snapshot manifest artifact size is invalid: ${artifact.logical_path}`);
    assertArtifactPathSafety(artifact);
    if (seen.logical_paths.has(artifact.logical_path)) throw new SnapshotIntegrityError(`duplicate logical path in snapshot manifest: ${artifact.logical_path}`);
    if (seen.object_keys.has(artifact.object_key)) throw new SnapshotIntegrityError(`duplicate object key in snapshot manifest: ${artifact.object_key}`);
    seen.logical_paths.add(artifact.logical_path);
    seen.object_keys.add(artifact.object_key);
}

// The small assertions below exist so each validator reads as the list of
// properties it requires.  Inlined, the tuple check is one long run of branches
// and the structure it is asserting -- which field belongs to which part of the
// identity -- stops being visible in the code that enforces it.
function assertPlainObject(value, label) {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new SnapshotIntegrityError(`${label} must be an object`);
    return value;
}

function assertNonEmptyString(value, label) {
    if (typeof value !== 'string' || !value) throw new SnapshotIntegrityError(`${label} is required`);
    return value;
}

function assertTransactionId(value, label) {
    if (typeof value !== 'string' || !/^tx_[a-f0-9]{64}$/.test(value)) throw new SnapshotIntegrityError(`${label} is invalid`);
    return value;
}

function assertCount(value, label) {
    if (!Number.isInteger(value) || value < 0) throw new SnapshotIntegrityError(`${label} is invalid`);
    return value;
}

// A pre-epoch accounting total is allowed to be the literal `UNKNOWN` string,
// because that is what the accepted authority baseline records and reading it
// as anything else is the reinterpretation the mission forbids.  Only the value
// *shape* is checkable here; which strings are meaningful belongs to the
// accounting contract, not to a manifest validator.
function isCarriedAccountingValue(value) {
    return value === null || typeof value === 'string' || Number.isInteger(value);
}

function validateIdentityAuthority(authority, label) {
    assertPlainObject(authority, label);
    assertTransactionId(authority.head_transaction_id, `${label}.head_transaction_id`);
    for (const field of ['head_transaction_content_hash', 'state_hash', 'allocation_authority_content_hash', 'store_sha256']) {
        assertManifestHash(authority[field], `${label}.${field}`);
    }
    assertManifestTimestamp(authority.head_knowledge_time, `${label}.head_knowledge_time`);
    for (const field of ['head_sequence', 'decision_count', 'observation_count', 'registry_state_count', 'capture_binding_count']) {
        assertCount(authority[field], `${label}.${field}`);
    }
}

// The two pre-epoch accounting fields are required to be *present* and are not
// required to have a particular value: the contract records one of them as the
// literal `UNKNOWN`, and reading that as anything else is the reinterpretation
// the mission forbids.  Presence is the part that is checkable.
function validateIdentityAccounting(accounting, label) {
    assertPlainObject(accounting, label);
    assertNonEmptyString(accounting.epoch_id, `${label}.epoch_id`);
    assertManifestTimestamp(accounting.started_at, `${label}.started_at`);
    assertTransactionId(accounting.start_authority_head, `${label}.start_authority_head`);
    for (const field of ['start_authority_state_hash', 'genesis_entry_hash', 'last_entry_hash']) {
        assertManifestHash(accounting[field], `${label}.${field}`);
    }
    for (const field of ['entry_count', 'request_count']) {
        assertCount(accounting[field], `${label}.${field}`);
    }
    for (const field of ['historical_pre_epoch_request_total', 'historical_pre_epoch_exact_total']) {
        if (!Object.hasOwn(accounting, field)) throw new SnapshotIntegrityError(`${label}.${field} must be carried, even when its value is unknown`);
        if (!isCarriedAccountingValue(accounting[field])) throw new SnapshotIntegrityError(`${label}.${field} is invalid`);
    }
}

function validateIdentityQuota(quota, label) {
    assertPlainObject(quota, label);
    assertManifestHash(quota.sha256, `${label}.sha256`);
    assertCount(quota.size, `${label}.size`);
}

// The identity tuple is what makes an accepted generation evidence: it is the
// claim that this generation is a snapshot of *that* authority at *that*
// request-accounting epoch.  A validator that tolerates the fields being absent
// accepts a manifest that binds nothing, and a verifier built on it would then
// report PASS for a generation that proves no such thing -- so every field the
// tuple is defined to carry is required, and required to have the shape the
// writer produces.
function validateIdentityTuple(tuple, label) {
    assertPlainObject(tuple, label);
    validateIdentityAuthority(tuple.authority, `${label}.authority`);
    validateIdentityAccounting(tuple.request_accounting, `${label}.request_accounting`);
    validateIdentityQuota(tuple.quota_config, `${label}.quota_config`);
}

// Both tuples are validated before they are compared.  Comparing them first
// would let two absent tuples agree -- `undefined` equals `undefined` -- and
// the manifest would pass on the strength of carrying no identity at all.
function assertManifestIdentity(value) {
    validateIdentityTuple(value.source_before, 'snapshot manifest source_before');
    validateIdentityTuple(value.source_after, 'snapshot manifest source_after');
    if (canonicalJson(value.source_before) !== canonicalJson(value.source_after)) throw new SnapshotIntegrityError('snapshot manifest source_before and source_after must be identical');
    if (canonicalJson(value.request_accounting) !== canonicalJson(value.source_before.request_accounting)) throw new SnapshotIntegrityError('snapshot manifest request_accounting must be the captured identity\'s request accounting');
    if (canonicalJson(value.quota_config) !== canonicalJson(value.source_before.quota_config)) throw new SnapshotIntegrityError('snapshot manifest quota_config must be the captured identity\'s quota configuration');
}

// `source` is the same identity projected flat for readers that want the
// authority fields without the rest.  This validates the summary's *shape* and
// nothing more.  Whether it agrees with the identity it summarises is a
// different question, and it belongs to the verifier, which answers it with a
// code of its own; deciding it here would replace that code with a generic one
// and make the summary-drift failure unreachable.
function validateManifestSource(source) {
    assertPlainObject(source, 'snapshot manifest source');
    assertTransactionId(source.head_transaction_id, 'snapshot manifest source.head_transaction_id');
    for (const field of ['head_transaction_content_hash', 'state_hash', 'allocation_authority_content_hash', 'input_set_sha256']) {
        assertManifestHash(source[field], `snapshot manifest source.${field}`);
    }
    assertManifestTimestamp(source.head_knowledge_time, 'snapshot manifest source.head_knowledge_time');
    for (const field of ['observation_count', 'decision_count', 'registry_state_count', 'capture_binding_count', 'head_sequence']) {
        assertCount(source[field], `snapshot manifest source.${field}`);
    }
}

function validateSnapshotManifest(value) {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new SnapshotIntegrityError('snapshot manifest must be an object');
    if (!SUPPORTED_MANIFEST_SCHEMA_VERSIONS.includes(value.schema_version)) throw new SnapshotIntegrityError(`unsupported snapshot manifest schema version: ${value.schema_version}`);
    assertGenerationId(value.snapshot_id);
    if (value.secrets_included !== false) throw new SnapshotIntegrityError('snapshot manifest must declare secrets_included: false');
    assertManifestTimestamp(value.created_at, 'snapshot manifest created_at');
    for (const field of ['store_sha256', 'allocation_authority_sha256']) assertManifestHash(value[field], field);
    if (!Array.isArray(value.artifacts) || value.artifacts.length === 0) throw new SnapshotIntegrityError('snapshot manifest must list at least one artifact');

    const seen = { logical_paths: new Set(), object_keys: new Set() };
    for (const artifact of value.artifacts) validateManifestArtifact(artifact, seen);

    if (value.artifact_count !== value.artifacts.length) throw new SnapshotIntegrityError('snapshot manifest artifact_count does not match the artifact list');
    const expectedTotal = value.artifacts.reduce((sum, artifact) => sum + artifact.size, 0);
    if (value.total_bytes !== expectedTotal) throw new SnapshotIntegrityError('snapshot manifest total_bytes does not match the artifact list');
    if (value.source_identity_equal !== true) throw new SnapshotIntegrityError('snapshot manifest must record that the source identity was unchanged');
    assertManifestIdentity(value);
    validateManifestSource(value.source);
    return true;
}

function buildCompletenessMarker(fields) {
    const marker = {
        schema_version: SNAPSHOT_COMPLETENESS_SCHEMA_VERSION,
        snapshot_id: fields.snapshot_id,
        manifest_object_key: fields.manifest_object_key,
        manifest_sha256: fields.manifest_sha256,
        artifact_count: fields.artifact_count,
        total_bytes: fields.total_bytes,
        source_head_transaction_id: fields.source_head_transaction_id,
        source_state_hash: fields.source_state_hash,
        completed_at: fields.completed_at,
    };
    const bytes = Buffer.from(canonicalJson(marker), 'utf8');
    return Object.freeze({ marker: Object.freeze(marker), bytes, sha256: sha256Hex(bytes) });
}

function validateCompletenessMarker(value) {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new SnapshotIntegrityError('completeness marker must be an object');
    if (value.schema_version !== SNAPSHOT_COMPLETENESS_SCHEMA_VERSION) throw new SnapshotIntegrityError(`unsupported completeness marker schema version: ${value.schema_version}`);
    assertGenerationId(value.snapshot_id);
    assertManifestHash(value.manifest_sha256, 'completeness marker manifest_sha256');
    if (typeof value.manifest_object_key !== 'string' || !value.manifest_object_key) throw new SnapshotIntegrityError('completeness marker manifest_object_key is required');
    if (value.manifest_object_key !== manifestObjectKey(value.snapshot_id)) throw new SnapshotIntegrityError('completeness marker manifest_object_key does not match its snapshot id');
    if (!Number.isInteger(value.artifact_count) || value.artifact_count < 1) throw new SnapshotIntegrityError('completeness marker artifact_count is invalid');
    if (!Number.isInteger(value.total_bytes) || value.total_bytes < 0) throw new SnapshotIntegrityError('completeness marker total_bytes is invalid');
    assertManifestTimestamp(value.completed_at, 'completeness marker completed_at');
    return true;
}

module.exports = {
    SNAPSHOT_MANIFEST_SCHEMA_VERSION,
    SNAPSHOT_COMPLETENESS_SCHEMA_VERSION,
    SUPPORTED_MANIFEST_SCHEMA_VERSIONS,
    MANIFEST_OBJECT_NAME,
    COMPLETENESS_OBJECT_NAME,
    PAYLOAD_PREFIX,
    SNAPSHOT_GENERATION_ID_PATTERN,
    sha256Hex,
    createSnapshotGenerationId,
    assertGenerationId,
    generationPrefix,
    manifestObjectKey,
    completenessObjectKey,
    payloadObjectKey,
    parseCanonicalJsonObject,
    buildSnapshotManifest,
    validateSnapshotManifest,
    buildCompletenessMarker,
    validateCompletenessMarker,
};
