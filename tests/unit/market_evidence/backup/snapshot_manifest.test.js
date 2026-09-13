'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const { canonicalJson } = require('../../../../src/infrastructure/market_evidence/transactionContract');
const { SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');

// The manifest and marker builders are pure, but "pure enough that it cannot
// reach the network" is a claim about the code, not a guarantee about the test
// run.  Sealing the whole file is what turns it into an enforced property.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});
const {
    SNAPSHOT_MANIFEST_SCHEMA_VERSION,
    SNAPSHOT_COMPLETENESS_SCHEMA_VERSION,
    MANIFEST_OBJECT_NAME,
    COMPLETENESS_OBJECT_NAME,
    createSnapshotGenerationId,
    assertGenerationId,
    manifestObjectKey,
    completenessObjectKey,
    payloadObjectKey,
    parseCanonicalJsonObject,
    buildSnapshotManifest,
    validateSnapshotManifest,
    buildCompletenessMarker,
    validateCompletenessMarker,
} = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');

const SNAPSHOT_ID = 'snap_20260913T000000000Z_0123456789abcdef';
const HASH_A = 'a'.repeat(64);
const HASH_B = 'b'.repeat(64);

function identity() {
    return {
        authority: {
            head_transaction_id: `tx_${HASH_A}`,
            head_transaction_content_hash: HASH_A,
            head_sequence: 3,
            head_knowledge_time: '2026-09-13T00:00:00Z',
            state_hash: HASH_B,
            allocation_authority_content_hash: HASH_B,
            decision_count: 2,
            observation_count: 6,
            registry_state_count: 6,
            capture_binding_count: 2,
            store_sha256: HASH_A,
        },
        request_accounting: {
            epoch_id: 'epoch-1',
            started_at: '2026-09-13T00:00:00Z',
            start_authority_head: `tx_${HASH_A}`,
            start_authority_state_hash: HASH_B,
            historical_pre_epoch_request_total: 'AT_LEAST_2_CONFIRMED',
            historical_pre_epoch_exact_total: 'UNKNOWN',
            genesis_entry_hash: HASH_A,
            entry_count: 2,
            request_count: 1,
            last_entry_hash: HASH_B,
        },
        quota_config: { sha256: HASH_B, size: 128 },
    };
}

function artifact(overrides = {}) {
    return {
        logical_path: 'transactions/STORE.json',
        category: 'store',
        object_key: payloadObjectKey(SNAPSHOT_ID, 'transactions/STORE.json'),
        size: 12,
        sha256: HASH_A,
        ...overrides,
    };
}

function manifestFields(overrides = {}) {
    const source = identity();
    return {
        snapshot_id: SNAPSHOT_ID,
        created_at: '2026-09-13T00:00:00Z',
        source: { ...source.authority, input_set_sha256: HASH_A },
        source_before: source,
        source_after: source,
        source_identity_equal: true,
        store_sha256: HASH_A,
        allocation_authority_sha256: HASH_B,
        request_accounting: source.request_accounting,
        quota_config: source.quota_config,
        artifacts: [artifact()],
        ...overrides,
    };
}

test('a generation id is time-ordered, entropy-bearing and never the transaction head', () => {
    const id = createSnapshotGenerationId({ now: new Date('2026-09-13T12:34:56.789Z'), randomBytes: () => Buffer.from('0011223344556677', 'hex') });
    assert.equal(id, 'snap_20260913T123456789Z_0011223344556677');
    assert.equal(assertGenerationId(id), id);

    const another = createSnapshotGenerationId({ now: new Date('2026-09-13T12:34:56.789Z'), randomBytes: () => Buffer.from('8899aabbccddeeff', 'hex') });
    assert.notEqual(id, another, 'two attempts in the same millisecond must remain distinguishable');
    assert.equal(id.includes('tx_'), false);
});

test('malformed generation ids are refused before they become object keys', () => {
    for (const bad of ['', 'snap_', 'snap_20260913T123456Z_0011223344556677', 'snap_20260913T123456789Z_00112233445566', 'snap_20260913T123456789Z_ZZZZ223344556677', `tx_${HASH_A}`, null, 42]) {
        assert.throws(() => assertGenerationId(bad), error => error instanceof SnapshotIntegrityError, `${JSON.stringify(bad)} must be refused`);
    }
});

test('object keys are derived from the generation id and validate their inputs', () => {
    assert.equal(manifestObjectKey(SNAPSHOT_ID), `${SNAPSHOT_ID}/MANIFEST.json`);
    assert.equal(completenessObjectKey(SNAPSHOT_ID), `${SNAPSHOT_ID}/COMPLETE`);
    assert.equal(MANIFEST_OBJECT_NAME, 'MANIFEST.json');
    assert.equal(COMPLETENESS_OBJECT_NAME, 'COMPLETE');
    assert.equal(payloadObjectKey(SNAPSHOT_ID, 'transactions/STORE.json'), `${SNAPSHOT_ID}/payload/transactions/STORE.json`);
    for (const bad of ['/absolute', 'a/../b', './a', 'a//b', '']) {
        assert.throws(() => payloadObjectKey(SNAPSHOT_ID, bad), error => error instanceof SnapshotIntegrityError, `${bad} must be refused`);
    }
});

test('the manifest serializes canonically and hashes its own bytes', () => {
    const built = buildSnapshotManifest(manifestFields());
    assert.equal(built.bytes.toString('utf8'), canonicalJson(built.manifest));
    assert.equal(built.sha256.length, 64);
    const rebuilt = buildSnapshotManifest(manifestFields());
    assert.equal(rebuilt.sha256, built.sha256, 'the manifest hash must be a function of content, not of evaluation order');
});

test('a valid manifest passes validation and pins the schema version', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    assert.equal(validateSnapshotManifest(manifest), true);
    assert.equal(manifest.schema_version, SNAPSHOT_MANIFEST_SCHEMA_VERSION);
    assert.equal(manifest.secrets_included, false);
    assert.equal(manifest.artifact_count, 1);
    assert.equal(manifest.total_bytes, 12);
    assert.equal(manifest.completeness_marker, COMPLETENESS_OBJECT_NAME);
});

test('an unsupported manifest schema version is refused', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    for (const version of ['stage-d-independent-backup-snapshot/v2', 'stage-d-independent-backup-snapshot/v0', undefined, null]) {
        assert.throws(
            () => validateSnapshotManifest({ ...manifest, schema_version: version }),
            error => error instanceof SnapshotIntegrityError && /unsupported snapshot manifest schema version/.test(error.message)
        );
    }
});

test('a manifest that admits carrying secrets is refused', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    for (const flag of [true, undefined, 'false']) {
        assert.throws(
            () => validateSnapshotManifest({ ...manifest, secrets_included: flag }),
            error => error instanceof SnapshotIntegrityError && /secrets_included/.test(error.message)
        );
    }
});

test('a manifest whose source identity moved is refused', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    assert.throws(
        () => validateSnapshotManifest({ ...manifest, source_identity_equal: false }),
        error => error instanceof SnapshotIntegrityError && /unchanged/.test(error.message)
    );
    const moved = { ...manifest, source_after: { ...manifest.source_after, authority: { ...manifest.source_after.authority, head_sequence: 4 } } };
    assert.throws(() => validateSnapshotManifest(moved), error => error instanceof SnapshotIntegrityError && /source_before and source_after must be identical/.test(error.message));
});

test('duplicate logical paths and duplicate object keys are refused', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    const duplicatedPath = { ...manifest, artifacts: [manifest.artifacts[0], { ...manifest.artifacts[0], object_key: `${SNAPSHOT_ID}/payload/other.json` }], artifact_count: 2, total_bytes: 24 };
    assert.throws(() => validateSnapshotManifest(duplicatedPath), error => error instanceof SnapshotIntegrityError && /duplicate logical path/.test(error.message));

    const duplicatedKey = { ...manifest, artifacts: [manifest.artifacts[0], { ...manifest.artifacts[0], logical_path: 'transactions/other.json' }], artifact_count: 2, total_bytes: 24 };
    assert.throws(() => validateSnapshotManifest(duplicatedKey), error => error instanceof SnapshotIntegrityError && /duplicate object key/.test(error.message));
});

test('traversal, absolute paths and staging never enter a manifest', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    for (const logicalPath of ['../escape.json', '/absolute.json', 'a/./b.json', 'a/../b.json', 'transactions/.staging/partial.json']) {
        const tampered = { ...manifest, artifacts: [{ ...manifest.artifacts[0], logical_path: logicalPath }] };
        assert.throws(() => validateSnapshotManifest(tampered), error => error instanceof SnapshotIntegrityError, `${logicalPath} must be refused`);
    }
});

test('counts and totals must agree with the artifact list', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    assert.throws(() => validateSnapshotManifest({ ...manifest, artifact_count: 2 }), error => error instanceof SnapshotIntegrityError && /artifact_count/.test(error.message));
    assert.throws(() => validateSnapshotManifest({ ...manifest, total_bytes: 13 }), error => error instanceof SnapshotIntegrityError && /total_bytes/.test(error.message));
});

test('a manifest with no artifacts is refused', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    assert.throws(() => validateSnapshotManifest({ ...manifest, artifacts: [], artifact_count: 0, total_bytes: 0 }), error => error instanceof SnapshotIntegrityError && /at least one artifact/.test(error.message));
});

test('the completeness marker binds the manifest hash and the manifest key', () => {
    const { manifest, sha256 } = buildSnapshotManifest(manifestFields());
    const built = buildCompletenessMarker({
        snapshot_id: SNAPSHOT_ID,
        manifest_object_key: manifestObjectKey(SNAPSHOT_ID),
        manifest_sha256: sha256,
        artifact_count: manifest.artifact_count,
        total_bytes: manifest.total_bytes,
        source_head_transaction_id: manifest.source.head_transaction_id,
        source_state_hash: manifest.source.state_hash,
        completed_at: '2026-09-13T00:00:01Z',
    });
    assert.equal(validateCompletenessMarker(built.marker), true);
    assert.equal(built.marker.schema_version, SNAPSHOT_COMPLETENESS_SCHEMA_VERSION);
    assert.equal(built.marker.manifest_sha256, sha256);
    assert.equal(built.bytes.toString('utf8'), canonicalJson(built.marker));
});

test('a marker pointing at another generation is refused', () => {
    const { manifest, sha256 } = buildSnapshotManifest(manifestFields());
    const fields = {
        snapshot_id: SNAPSHOT_ID,
        manifest_object_key: manifestObjectKey(SNAPSHOT_ID),
        manifest_sha256: sha256,
        artifact_count: manifest.artifact_count,
        total_bytes: manifest.total_bytes,
        source_head_transaction_id: manifest.source.head_transaction_id,
        source_state_hash: manifest.source.state_hash,
        completed_at: '2026-09-13T00:00:01Z',
    };
    assert.throws(
        () => validateCompletenessMarker({ ...buildCompletenessMarker(fields).marker, manifest_object_key: `${createSnapshotGenerationId({ randomBytes: () => Buffer.alloc(8, 9) })}/${MANIFEST_OBJECT_NAME}` }),
        error => error instanceof SnapshotIntegrityError && /does not match its snapshot id/.test(error.message)
    );
    assert.throws(
        () => validateCompletenessMarker({ ...buildCompletenessMarker(fields).marker, manifest_sha256: 'not-a-hash' }),
        error => error instanceof SnapshotIntegrityError
    );
});

test('manifest parsing requires canonical serialization', () => {
    const { bytes } = buildSnapshotManifest(manifestFields());
    assert.ok(parseCanonicalJsonObject(bytes, 'manifest'));
    const pretty = Buffer.from(`${JSON.stringify(JSON.parse(bytes.toString('utf8')), null, 2)}`, 'utf8');
    assert.throws(() => parseCanonicalJsonObject(pretty, 'manifest'), error => error instanceof SnapshotIntegrityError && /canonical serialization/.test(error.message));
    assert.throws(() => parseCanonicalJsonObject(Buffer.from('{', 'utf8'), 'manifest'), error => error instanceof SnapshotIntegrityError && /not valid JSON/.test(error.message));
    assert.throws(() => parseCanonicalJsonObject(bytes.toString('utf8'), 'manifest'), error => error instanceof SnapshotIntegrityError && /read as bytes/.test(error.message));
});

test('timestamps are validated as UTC ISO-8601', () => {
    const { manifest } = buildSnapshotManifest(manifestFields());
    for (const created of ['2026-09-13 00:00:00', '2026-09-13T00:00:00+01:00', 'yesterday', '']) {
        assert.throws(() => validateSnapshotManifest({ ...manifest, created_at: created }), error => error instanceof SnapshotIntegrityError && /UTC ISO-8601/.test(error.message));
    }
});
