'use strict';

// Verifies one snapshot generation against the contract, read-only.
//
// The verifier never writes, never repairs and never deletes.  A generation
// that fails verification stays exactly as it is: a failed verification is
// evidence about a generation, and repairing it in place would destroy that
// evidence.  Re-running the writer produces a new generation instead.
//
// Verification is anchored on the completeness marker.  The marker is written
// last and binds the manifest hash, so a generation missing its marker is
// reported as incomplete no matter how many payload objects it contains.  That
// is what makes a crashed or interrupted write safe: half a generation looks
// exactly like half a generation.
//
// Failures are collected rather than thrown, so one report describes everything
// wrong with a generation instead of only the first thing.

const { canonicalJson } = require('../transactionContract');
const { assertTransportContract, SnapshotIntegrityError } = require('./transport');
const { CATEGORY, REQUIRED_CATEGORIES } = require('./snapshotInputs');
const {
    assertGenerationId,
    completenessObjectKey,
    manifestObjectKey,
    parseCanonicalJsonObject,
    payloadObjectKey,
    sha256Hex,
    validateCompletenessMarker,
    validateSnapshotManifest,
} = require('./snapshotManifest');

const SNAPSHOT_VERIFIER_VERSION = 'stage-d-independent-backup-verifier/v1';

function failure(code, detail) {
    return Object.freeze({ code, detail });
}

function safeParseCanonical(bytes, label, failures, code) {
    try {
        return parseCanonicalJsonObject(bytes, label);
    } catch (error) {
        failures.push(failure(code, error.message));
        return null;
    }
}

// Loads the manifest of an accepted generation.  "Accepted" is defined by the
// completeness marker, not by the presence of a manifest object: a manifest
// without its marker describes a write that never finished.
async function loadAcceptedManifest({ transport, snapshotId } = {}) {
    assertTransportContract(transport);
    assertGenerationId(snapshotId);
    const markerBytes = await transport.getObject({ key: completenessObjectKey(snapshotId) });
    if (markerBytes === null || markerBytes === undefined) throw new SnapshotIntegrityError(`generation ${snapshotId} carries no completeness marker and is not an accepted snapshot`);
    const marker = parseCanonicalJsonObject(markerBytes, 'completeness marker');
    validateCompletenessMarker(marker);
    if (marker.snapshot_id !== snapshotId) throw new SnapshotIntegrityError(`completeness marker names ${marker.snapshot_id} but was read from ${snapshotId}`);
    const manifestBytes = await transport.getObject({ key: marker.manifest_object_key });
    if (manifestBytes === null || manifestBytes === undefined) throw new SnapshotIntegrityError(`the completeness marker binds ${marker.manifest_object_key}, which does not exist`);
    const manifest = parseCanonicalJsonObject(manifestBytes, 'snapshot manifest');
    validateSnapshotManifest(manifest);
    const manifestSha256 = sha256Hex(manifestBytes);
    if (manifestSha256 !== marker.manifest_sha256) throw new SnapshotIntegrityError('the manifest does not match the hash bound by the completeness marker');
    return Object.freeze({ marker, manifest, manifest_sha256: manifestSha256 });
}

function markerDisagreements(marker, manifest) {
    const disagreements = [];
    if (marker.artifact_count !== manifest.artifact_count) disagreements.push('completeness marker artifact_count disagrees with the manifest');
    if (marker.total_bytes !== manifest.total_bytes) disagreements.push('completeness marker total_bytes disagrees with the manifest');
    if (marker.source_head_transaction_id !== manifest.source.head_transaction_id) disagreements.push('completeness marker authority head disagrees with the manifest');
    if (marker.source_state_hash !== manifest.source.state_hash) disagreements.push('completeness marker authority state hash disagrees with the manifest');
    return disagreements;
}

async function checkArtifacts({ transport, snapshotId, manifest, failures }) {
    for (const artifact of manifest.artifacts) {
        const expectedKey = payloadObjectKey(snapshotId, artifact.logical_path);
        if (artifact.object_key !== expectedKey) {
            failures.push(failure('ARTIFACT_KEY_MISMATCH', `${artifact.logical_path} is stored at ${artifact.object_key} instead of ${expectedKey}`));
            continue;
        }
        let bytes;
        try {
            bytes = await transport.getObject({ key: artifact.object_key });
        } catch (error) {
            failures.push(failure('ARTIFACT_MISSING', `${artifact.logical_path} could not be read: ${error.message}`));
            continue;
        }
        if (bytes === null || bytes === undefined) {
            failures.push(failure('ARTIFACT_MISSING', `${artifact.logical_path} is bound by the manifest but absent from the generation`));
            continue;
        }
        if (bytes.length !== artifact.size) failures.push(failure('ARTIFACT_SIZE_MISMATCH', `${artifact.logical_path} is ${bytes.length} bytes but the manifest declares ${artifact.size}`));
        if (sha256Hex(bytes) !== artifact.sha256) failures.push(failure('ARTIFACT_HASH_MISMATCH', `${artifact.logical_path} content does not match the hash bound by the manifest`));
    }
}

function checkCategories(manifest, failures) {
    const observed = new Set(manifest.artifacts.map(artifact => artifact.category));
    for (const category of REQUIRED_CATEGORIES) {
        if (!observed.has(category)) failures.push(failure('MISSING_REQUIRED_CATEGORY', `the generation does not carry a required category: ${category}`));
    }
    return manifest.artifacts.filter(artifact => artifact.category === CATEGORY.REQUEST_ACCOUNTING_ENTRY).length;
}

// The observed key set must be exactly what the manifest and marker describe.
// Because nothing in this system can delete, an extra object is either a
// foreign write or a bug, and either way the generation is not the generation
// the manifest claims.
async function checkObjectSet({ transport, snapshotId, manifest, marker, evidence, failures }) {
    const listed = await transport.listObjects({ prefix: `${snapshotId}/` });
    const observed = new Set(listed.map(entry => entry.key));
    evidence.observed_object_count = observed.size;
    const expected = new Set([marker.manifest_object_key, evidence.completeness_object_key, ...manifest.artifacts.map(artifact => artifact.object_key)]);
    for (const key of observed) {
        if (!expected.has(key)) failures.push(failure('UNEXPECTED_OBJECT', `the generation contains an object no manifest entry accounts for: ${key}`));
    }
    for (const key of expected) {
        if (!observed.has(key)) failures.push(failure('ARTIFACT_MISSING', `the generation is missing an object the manifest accounts for: ${key}`));
    }
}

const SUMMARY_FIELDS = Object.freeze([
    'head_transaction_id',
    'head_transaction_content_hash',
    'head_sequence',
    'state_hash',
    'observation_count',
    'decision_count',
    'registry_state_count',
    'capture_binding_count',
]);

// The summary tuple and the full before/after tuples must agree with each
// other.  validateSnapshotManifest already requires before == after; this
// closes the remaining gap where a manifest could carry a summary that its own
// captured identities contradict.
function checkSourceSummary(manifest, failures) {
    for (const field of SUMMARY_FIELDS) {
        if (manifest.source[field] !== manifest.source_before.authority[field]) failures.push(failure('SOURCE_SUMMARY_MISMATCH', `manifest source.${field} disagrees with the captured source identity`));
    }
    if (manifest.store_sha256 !== manifest.source_before.authority.store_sha256) failures.push(failure('SOURCE_SUMMARY_MISMATCH', 'manifest store_sha256 disagrees with the captured source identity'));
    if (manifest.allocation_authority_sha256 !== manifest.source_before.authority.allocation_authority_content_hash) failures.push(failure('SOURCE_SUMMARY_MISMATCH', 'manifest allocation_authority_sha256 disagrees with the captured source identity'));
    if (canonicalJson(manifest.quota_config) !== canonicalJson(manifest.source_before.quota_config)) failures.push(failure('SOURCE_SUMMARY_MISMATCH', 'manifest quota_config disagrees with the captured source identity'));
}

async function openGeneration({ transport, snapshotId, failures, evidence }) {
    const markerBytes = await transport.getObject({ key: evidence.completeness_object_key });
    if (markerBytes === null || markerBytes === undefined) {
        failures.push(failure('MISSING_COMPLETENESS_MARKER', `generation ${snapshotId} carries no completeness marker and is therefore incomplete`));
        return null;
    }
    const marker = safeParseCanonical(markerBytes, 'completeness marker', failures, 'INVALID_COMPLETENESS_MARKER');
    if (marker === null) return null;
    try {
        validateCompletenessMarker(marker);
    } catch (error) {
        failures.push(failure('INVALID_COMPLETENESS_MARKER', error.message));
        return null;
    }
    if (marker.snapshot_id !== snapshotId) {
        failures.push(failure('IDENTITY_MISMATCH', `completeness marker names ${marker.snapshot_id} but was read from ${snapshotId}`));
        return null;
    }
    evidence.manifest_object_key = marker.manifest_object_key;

    const manifestBytes = await transport.getObject({ key: marker.manifest_object_key });
    if (manifestBytes === null || manifestBytes === undefined) {
        failures.push(failure('MISSING_MANIFEST', `the completeness marker binds ${marker.manifest_object_key}, which does not exist`));
        return null;
    }
    evidence.manifest_sha256 = sha256Hex(manifestBytes);
    if (evidence.manifest_sha256 !== marker.manifest_sha256) {
        failures.push(failure('MANIFEST_HASH_MISMATCH', `manifest hash ${evidence.manifest_sha256} does not match the hash bound by the completeness marker`));
        return null;
    }
    const manifest = safeParseCanonical(manifestBytes, 'snapshot manifest', failures, 'INVALID_MANIFEST');
    if (manifest === null) return null;
    try {
        validateSnapshotManifest(manifest);
    } catch (error) {
        failures.push(failure('INVALID_MANIFEST', error.message));
        return null;
    }
    return Object.freeze({ marker, manifest });
}

async function verifySnapshot({ transport, snapshotId } = {}) {
    assertTransportContract(transport);
    assertGenerationId(snapshotId);

    const failures = [];
    const evidence = {
        snapshot_id: snapshotId,
        manifest_object_key: manifestObjectKey(snapshotId),
        completeness_object_key: completenessObjectKey(snapshotId),
        manifest_sha256: null,
        artifact_count: null,
        total_bytes: null,
        observed_object_count: null,
        request_accounting_entries: null,
        source_head_transaction_id: null,
        source_state_hash: null,
    };
    const report = result => Object.freeze({
        verifier_version: SNAPSHOT_VERIFIER_VERSION,
        result: failures.length === 0 && result === 'PASS' ? 'PASS' : 'FAIL',
        snapshot_id: snapshotId,
        failures: Object.freeze(failures),
        evidence: Object.freeze(evidence),
        transport: transport.describe(),
    });

    const generation = await openGeneration({ transport, snapshotId, failures, evidence });
    if (generation === null) return report('FAIL');
    const { marker, manifest } = generation;

    evidence.artifact_count = manifest.artifact_count;
    evidence.total_bytes = manifest.total_bytes;
    evidence.source_head_transaction_id = manifest.source.head_transaction_id;
    evidence.source_state_hash = manifest.source.state_hash;
    for (const disagreement of markerDisagreements(marker, manifest)) failures.push(failure('IDENTITY_MISMATCH', disagreement));

    await checkArtifacts({ transport, snapshotId, manifest, failures });
    evidence.request_accounting_entries = checkCategories(manifest, failures);
    await checkObjectSet({ transport, snapshotId, manifest, marker, evidence, failures });
    checkSourceSummary(manifest, failures);

    return report('PASS');
}

function assertSnapshotVerification(report) {
    if (report === null || typeof report !== 'object') throw new SnapshotIntegrityError('a verification report is required');
    if (report.result !== 'PASS') {
        const detail = (report.failures || []).map(item => `${item.code}: ${item.detail}`).join('; ') || 'no failure detail was recorded';
        throw new SnapshotIntegrityError(`snapshot ${report.snapshot_id} failed verification: ${detail}`);
    }
    return report;
}

// Compares a manifest's source tuple with a freshly captured identity.  Used to
// answer "is this generation still the current authority?" without reading the
// payload, and to prove in tests that the manifest binds the source it claims.
function compareSnapshotToSourceIdentity(manifest, sourceIdentity) {
    const mismatches = [];
    for (const field of SUMMARY_FIELDS) {
        if (canonicalJson(manifest.source[field]) !== canonicalJson(sourceIdentity.authority[field])) mismatches.push(field);
    }
    return Object.freeze({ matches: mismatches.length === 0, mismatches: Object.freeze(mismatches) });
}

module.exports = {
    SNAPSHOT_VERIFIER_VERSION,
    SUMMARY_FIELDS,
    loadAcceptedManifest,
    verifySnapshot,
    assertSnapshotVerification,
    compareSnapshotToSourceIdentity,
};
