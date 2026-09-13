'use strict';

// Writes one immutable snapshot generation.
//
// Sequencing, and why it is this order:
//
//   1. assert the transport contract
//   2. choose a generation id and prove the generation is absent
//   3. capture the source identity BEFORE
//   4. copy every governed input with a create-only write
//   5. read every written object back and re-hash it
//   6. capture the source identity AFTER and require BEFORE == AFTER
//   7. re-enumerate the input set and require it to be unchanged
//   8. write the manifest, binding both identities
//   9. write the completeness marker LAST, binding the manifest hash
//
// The mission's written sequence places the manifest (8) before the AFTER
// identity capture (6).  Those two requirements cannot both hold: the manifest
// schema must bind the source-after identity, so the manifest cannot be sealed
// before that identity exists.  This implementation resolves the conflict in
// favour of the schema and the last-written completeness marker, and the
// deviation is reported to the Controller rather than papered over.
//
// Nothing here deletes.  A snapshot that fails part way through leaves its
// partial generation in place, and because the marker is written last, no
// verifier will ever accept that partial generation as complete.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const { canonicalJson } = require('../transactionContract');
const { openMarketEvidenceAuthoritySnapshot } = require('../authorityReader');
const { readRequestLedger } = require('../stageDOperations');
const { ObjectAlreadyExistsError, SnapshotIntegrityError, assertTransportContract } = require('./transport');
const { STORE_FILE, enumerateSnapshotInputs } = require('./snapshotInputs');
const {
    assertGenerationId,
    buildCompletenessMarker,
    buildSnapshotManifest,
    completenessObjectKey,
    createSnapshotGenerationId,
    manifestObjectKey,
    payloadObjectKey,
    sha256Hex,
} = require('./snapshotManifest');

const SNAPSHOT_WRITER_VERSION = 'stage-d-independent-backup-writer/v1';

// A source that moves under a snapshot is not a warning.  An accepted
// generation is a permanent claim about a specific authority identity, so if
// the identity changed while the bytes were being copied, the claim would be
// false and the generation must never be sealed.
class SourceChangedDuringSnapshotError extends Error {
    constructor(message) {
        super(message);
        this.name = 'SourceChangedDuringSnapshotError';
        this.code = 'SOURCE_CHANGED_DURING_SNAPSHOT';
    }
}

function readGovernedBytes(sourcePath) {
    const before = fs.lstatSync(sourcePath);
    if (before.isSymbolicLink() || !before.isFile()) throw new SnapshotIntegrityError(`snapshot input must be a regular file: ${sourcePath}`);
    const fd = fs.openSync(sourcePath, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    try {
        const opened = fs.fstatSync(fd);
        if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino) throw new SnapshotIntegrityError(`snapshot input changed during open: ${sourcePath}`);
        const bytes = fs.readFileSync(fd);
        const after = fs.fstatSync(fd);
        if (after.dev !== opened.dev || after.ino !== opened.ino || after.size !== bytes.length) throw new SnapshotIntegrityError(`snapshot input changed during read: ${sourcePath}`);
        return bytes;
    } finally {
        fs.closeSync(fd);
    }
}

function hashGovernedFile(sourcePath) {
    const bytes = readGovernedBytes(sourcePath);
    return Object.freeze({ sha256: sha256Hex(bytes), size: bytes.length });
}

// The digest binds content, not the shape of the set.  A digest over
// logical_path and size is a digest over a stat: a file replaced by different
// content of the same length leaves it untouched, so a copy that read one
// version while the source moved on to another compares equal and the
// generation is sealed COMPLETE holding a mixture of the two.  Hashing the
// bytes makes the comparison answer what the invariant actually asks -- is what
// we wrote still what the source holds -- and it answers it for every input,
// including the committed packages and the run-state files that the identity
// tuple does not cover.
//
// The order is by logical path rather than by enumeration order so that the two
// sides of the comparison cannot agree or disagree because of how they were
// built.
function inputSetDigest(entries) {
    return sha256Hex(Buffer.from(canonicalJson(
        [...entries]
            .map(entry => ({ logical_path: entry.logical_path, size: entry.size, sha256: entry.sha256 }))
            .sort((left, right) => (left.logical_path < right.logical_path ? -1 : left.logical_path > right.logical_path ? 1 : 0)),
    ), 'utf8'));
}

// The identity tuple is deliberately serializable.  The authority snapshot
// carries accessor functions, and a comparison that silently dropped them
// would be weaker than it looks, so the tuple is built field by field from
// values that canonicalJson can bind.
function captureSourceIdentity({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath }) {
    const authority = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    if (typeof authority.head_transaction_id !== 'string' || !/^tx_[a-f0-9]{64}$/.test(authority.head_transaction_id)) {
        throw new SnapshotIntegrityError('the authority has no committed head transaction; an empty authority is not snapshot-eligible');
    }
    const ledger = readRequestLedger({ ledgerRoot });
    const storeHash = hashGovernedFile(path.join(path.resolve(authorityRoot), STORE_FILE));
    const allocationHash = hashGovernedFile(allocationArtifactPath);
    const quotaHash = hashGovernedFile(quotaConfigPath);
    const epoch = ledger.epoch;

    return Object.freeze({
        authority: Object.freeze({
            head_transaction_id: authority.head_transaction_id,
            head_transaction_content_hash: authority.head_transaction_content_hash,
            head_sequence: authority.head_sequence,
            head_knowledge_time: authority.head_knowledge_time,
            state_hash: authority.state_hash,
            allocation_authority_content_hash: allocationHash.sha256,
            decision_count: authority.decisions.length,
            observation_count: authority.observations.length,
            registry_state_count: authority.registry_state.length,
            capture_binding_count: authority.capture_bindings.length,
            store_sha256: storeHash.sha256,
        }),
        request_accounting: Object.freeze({
            epoch_id: epoch.epoch_id,
            started_at: epoch.started_at,
            start_authority_head: epoch.start_authority_head,
            start_authority_state_hash: epoch.start_authority_state_hash,
            historical_pre_epoch_request_total: epoch.historical_pre_epoch_request_total,
            historical_pre_epoch_exact_total: epoch.historical_pre_epoch_exact_total,
            genesis_entry_hash: epoch.genesis_entry_hash,
            entry_count: ledger.entries.length,
            request_count: ledger.requests.length,
            last_entry_hash: ledger.last_entry_hash,
        }),
        quota_config: Object.freeze({ sha256: quotaHash.sha256, size: quotaHash.size }),
    });
}

async function assertGenerationAbsent(transport, snapshotId) {
    const manifestKey = manifestObjectKey(snapshotId);
    const existingManifest = await transport.headObject({ key: manifestKey });
    if (existingManifest !== null && existingManifest !== undefined) throw new ObjectAlreadyExistsError(manifestKey);
    const existing = await transport.listObjects({ prefix: `${snapshotId}/` });
    if (Array.isArray(existing) && existing.length > 0) throw new ObjectAlreadyExistsError(`${snapshotId}/`);
}

async function writeObjectCreateOnly(transport, key, bytes, label) {
    await transport.putObjectCreateOnly({ key, bytes });
    // Read-back is not paranoia about the network; it is the only evidence
    // that what the generation holds is what the manifest will claim.
    const head = await transport.headObject({ key });
    if (head === null || head === undefined) throw new SnapshotIntegrityError(`${label} is missing immediately after a successful write: ${key}`);
    if (head.size !== bytes.length) throw new SnapshotIntegrityError(`${label} size mismatch after write: ${key}`);
    const observed = await transport.getObject({ key });
    if (!Buffer.isBuffer(observed)) throw new SnapshotIntegrityError(`${label} could not be read back after write: ${key}`);
    if (sha256Hex(observed) !== sha256Hex(bytes)) throw new SnapshotIntegrityError(`${label} content mismatch after write: ${key}`);
    return Object.freeze({ size: bytes.length, sha256: sha256Hex(bytes) });
}

async function writeSnapshot({
    transport,
    authorityRoot,
    allocationArtifactPath,
    ledgerRoot,
    quotaConfigPath,
    runStateInputs = [],
    snapshotId = null,
    now = () => new Date(),
    randomBytes = crypto.randomBytes,
} = {}) {
    assertTransportContract(transport);

    const resolvedSnapshotId = snapshotId === null
        ? createSnapshotGenerationId({ now: now(), randomBytes })
        : assertGenerationId(snapshotId);
    await assertGenerationAbsent(transport, resolvedSnapshotId);

    const inputsBefore = enumerateSnapshotInputs({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath, runStateInputs });
    const identityBefore = captureSourceIdentity({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath });

    const artifacts = [];
    for (const entry of inputsBefore.entries) {
        const bytes = readGovernedBytes(entry.source_path);
        const objectKey = payloadObjectKey(resolvedSnapshotId, entry.logical_path);
        const written = await writeObjectCreateOnly(transport, objectKey, bytes, `payload ${entry.logical_path}`);
        if (written.sha256 !== sha256Hex(bytes)) throw new SnapshotIntegrityError(`payload hash drifted while writing ${entry.logical_path}`);
        artifacts.push(Object.freeze({
            logical_path: entry.logical_path,
            category: entry.category,
            object_key: objectKey,
            size: written.size,
            sha256: written.sha256,
        }));
    }

    // What the generation holds, taken from the bytes that were actually
    // written rather than from a second stat of the source.
    const inputSetBefore = inputSetDigest(artifacts);

    const identityAfter = captureSourceIdentity({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath });
    if (canonicalJson(identityBefore) !== canonicalJson(identityAfter)) {
        // The generation is left in place, unmarked and unverifiable.  It is
        // not cleaned up, because the only thing that could clean it up is a
        // delete, which this system does not have.
        throw new SourceChangedDuringSnapshotError(`the authority changed while snapshot ${resolvedSnapshotId} was being written; the generation is partial and carries no completeness marker`);
    }

    // Every governed input is read back from the source and hashed, not merely
    // re-enumerated.  Re-enumerating is a stat: it notices a file that appeared,
    // disappeared or changed length, and it cannot notice one whose content was
    // replaced in place at the same length -- which is exactly the case that
    // leaves the generation holding a coherent-looking mixture of two moments.
    const inputsAfter = enumerateSnapshotInputs({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath, runStateInputs });
    const survived = inputsAfter.entries.map(entry => {
        const bytes = readGovernedBytes(entry.source_path);
        return { logical_path: entry.logical_path, size: bytes.length, sha256: sha256Hex(bytes) };
    });
    if (inputSetDigest(survived) !== inputSetBefore) {
        throw new SourceChangedDuringSnapshotError(`the governed input set changed while snapshot ${resolvedSnapshotId} was being written; the generation is partial and carries no completeness marker`);
    }

    const authority = identityBefore.authority;
    const built = buildSnapshotManifest({
        snapshot_id: resolvedSnapshotId,
        created_at: now().toISOString(),
        source: Object.freeze({
            head_transaction_id: authority.head_transaction_id,
            head_transaction_content_hash: authority.head_transaction_content_hash,
            head_sequence: authority.head_sequence,
            head_knowledge_time: authority.head_knowledge_time,
            state_hash: authority.state_hash,
            allocation_authority_content_hash: authority.allocation_authority_content_hash,
            decision_count: authority.decision_count,
            observation_count: authority.observation_count,
            registry_state_count: authority.registry_state_count,
            capture_binding_count: authority.capture_binding_count,
            input_set_sha256: inputSetBefore,
        }),
        source_before: identityBefore,
        source_after: identityAfter,
        source_identity_equal: true,
        store_sha256: authority.store_sha256,
        allocation_authority_sha256: authority.allocation_authority_content_hash,
        request_accounting: identityBefore.request_accounting,
        quota_config: identityBefore.quota_config,
        artifacts,
    });

    const manifestKey = manifestObjectKey(resolvedSnapshotId);
    await writeObjectCreateOnly(transport, manifestKey, built.bytes, 'snapshot manifest');

    // The marker is last on purpose.  Everything before it is a proposal; the
    // marker is what turns the generation into an accepted snapshot.
    const marker = buildCompletenessMarker({
        snapshot_id: resolvedSnapshotId,
        manifest_object_key: manifestKey,
        manifest_sha256: built.sha256,
        artifact_count: artifacts.length,
        total_bytes: built.manifest.total_bytes,
        source_head_transaction_id: authority.head_transaction_id,
        source_state_hash: authority.state_hash,
        completed_at: now().toISOString(),
    });
    await writeObjectCreateOnly(transport, completenessObjectKey(resolvedSnapshotId), marker.bytes, 'completeness marker');

    return Object.freeze({
        writer_version: SNAPSHOT_WRITER_VERSION,
        snapshot_id: resolvedSnapshotId,
        manifest_object_key: manifestKey,
        manifest_sha256: built.sha256,
        completeness_object_key: completenessObjectKey(resolvedSnapshotId),
        completeness_sha256: marker.sha256,
        artifact_count: artifacts.length,
        total_bytes: built.manifest.total_bytes,
        source_head_transaction_id: authority.head_transaction_id,
        source_state_hash: authority.state_hash,
        observation_count: authority.observation_count,
        input_set_sha256: inputSetBefore,
        source_identity_equal: true,
        categories: inputsBefore.categories,
        staging_excluded: true,
        transport: transport.describe(),
    });
}

module.exports = {
    SNAPSHOT_WRITER_VERSION,
    SourceChangedDuringSnapshotError,
    writeSnapshot,
    captureSourceIdentity,
    inputSetDigest,
    readGovernedBytes,
    hashGovernedFile,
    assertGenerationAbsent,
    writeObjectCreateOnly,
};
