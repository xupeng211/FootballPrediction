'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');

// Verification is the read half of the offline claim and it walks every object
// in a generation; the whole file is sealed so that claim covers every test in
// it rather than the one that was written with the tripwire in mind.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});
const { canonicalJson } = require('../../../../src/infrastructure/market_evidence/transactionContract');
const { createLocalTransport } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');
const { writeSnapshot, captureSourceIdentity } = require('../../../../src/infrastructure/market_evidence/backup/snapshotWriter');
const { verifySnapshot, assertSnapshotVerification, loadAcceptedManifest, compareSnapshotToSourceIdentity } = require('../../../../src/infrastructure/market_evidence/backup/snapshotVerifier');
const { buildCompletenessMarker, payloadObjectKey, sha256Hex } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');

const STORE_LOGICAL_PATH = 'transactions/STORE.json';

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 1 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

async function sealedGeneration(t, name) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), `stage-d-verify-${name}-`));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const transport = createLocalTransport({ root });
    const fx = fixture();
    const report = await writeSnapshot({
        transport,
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
    });
    return { root, transport, report };
}

function codes(report) {
    return report.failures.map(item => item.code);
}

function absoluteFor(root, key) {
    return path.join(root, ...key.split('/'));
}

function readManifest(root, report) {
    return JSON.parse(fs.readFileSync(absoluteFor(root, report.manifest_object_key), 'utf8'));
}

function rewrite(target, bytes) {
    fs.writeFileSync(target, bytes);
}

// Re-seals a tampered manifest: the marker must keep binding the manifest's real
// bytes, otherwise every test here would fail on MANIFEST_HASH_MISMATCH instead
// of on the property under test.
function reseal(root, report, manifest) {
    const manifestBytes = Buffer.from(canonicalJson(manifest), 'utf8');
    rewrite(absoluteFor(root, report.manifest_object_key), manifestBytes);
    const marker = buildCompletenessMarker({
        snapshot_id: report.snapshot_id,
        manifest_object_key: report.manifest_object_key,
        manifest_sha256: sha256Hex(manifestBytes),
        artifact_count: manifest.artifact_count,
        total_bytes: manifest.total_bytes,
        source_head_transaction_id: manifest.source.head_transaction_id,
        source_state_hash: manifest.source.state_hash,
        completed_at: '2026-09-13T00:00:02Z',
    });
    rewrite(absoluteFor(root, report.completeness_object_key), marker.bytes);
}

test('a freshly written generation verifies', async t => {
    const { transport, report } = await sealedGeneration(t, 'pass');
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'PASS');
    assert.deepEqual(verified.failures, []);
    assert.equal(verified.evidence.manifest_sha256, report.manifest_sha256);
    assert.equal(verified.evidence.artifact_count, report.artifact_count);
    assert.equal(verified.evidence.observed_object_count, report.artifact_count + 2);
    assert.equal(verified.evidence.source_head_transaction_id, report.source_head_transaction_id);
    assert.equal(verified.evidence.source_state_hash, report.source_state_hash);
    assert.equal(assertSnapshotVerification(verified), verified);
});

test('verification writes nothing at all', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'readonly');
    const inventory = () => transport.listObjects({}).map(entry => `${entry.key}:${entry.size}:${fs.readFileSync(absoluteFor(root, entry.key)).length}`);
    const before = inventory();
    await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    const second = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(second.result, 'PASS');
    assert.deepEqual(inventory(), before, 'a verifier must not add, remove or rewrite an object');
});

test('a generation without its completeness marker is refused as incomplete', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'nomarker');
    fs.rmSync(absoluteFor(root, report.completeness_object_key));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['MISSING_COMPLETENESS_MARKER']);
    assert.throws(() => assertSnapshotVerification(verified), error => error instanceof SnapshotIntegrityError && /failed verification/.test(error.message));
});

test('a marker whose manifest is missing is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'nomanifest');
    fs.rmSync(absoluteFor(root, report.manifest_object_key));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['MISSING_MANIFEST']);
});

test('a manifest that no longer matches the hash its marker binds is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'manifesthash');
    const manifest = readManifest(root, report);
    manifest.created_at = '2026-09-13T00:00:05Z';
    rewrite(absoluteFor(root, report.manifest_object_key), Buffer.from(canonicalJson(manifest), 'utf8'));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['MANIFEST_HASH_MISMATCH']);
});

test('a tampered payload object is caught by its hash', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'tamperpayload');
    const target = absoluteFor(root, payloadObjectKey(report.snapshot_id, STORE_LOGICAL_PATH));
    const bytes = Buffer.from(fs.readFileSync(target));
    bytes[0] ^= 0x01;
    rewrite(target, bytes);
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['ARTIFACT_HASH_MISMATCH'], 'a same-length edit must be caught by the hash alone');
});

test('a payload object whose length drifted is caught by its size', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'truncated');
    const target = absoluteFor(root, payloadObjectKey(report.snapshot_id, STORE_LOGICAL_PATH));
    rewrite(target, fs.readFileSync(target).subarray(0, 8));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified).sort(), ['ARTIFACT_HASH_MISMATCH', 'ARTIFACT_SIZE_MISMATCH']);
});

test('a payload object that has gone missing is reported with its logical path', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'missingpayload');
    fs.rmSync(absoluteFor(root, payloadObjectKey(report.snapshot_id, STORE_LOGICAL_PATH)));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    const missing = verified.failures.filter(item => item.code === 'ARTIFACT_MISSING');
    assert.equal(missing.length, 2, 'the absent object is reported both by the artifact check and by the object-set check');
    assert.ok(missing.every(item => item.detail.includes(STORE_LOGICAL_PATH)));
});

test('an object no manifest entry accounts for is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'extra');
    rewrite(path.join(root, report.snapshot_id, 'payload', 'transactions', 'STRAY.json'), '{}');
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.ok(codes(verified).includes('UNEXPECTED_OBJECT'));
    assert.ok(verified.failures.some(item => item.code === 'UNEXPECTED_OBJECT' && item.detail.includes('STRAY.json')));
});

test('an object placed outside the generation is not this generation\'s problem', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'outside');
    rewrite(path.join(root, 'unrelated.json'), '{}');
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'PASS', 'the object set is scoped to the generation, not to the whole transport root');
});

test('a self-consistent but mislocated artifact is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'mislocated');
    const manifest = readManifest(root, report);
    manifest.artifacts[0].object_key = `${report.snapshot_id}/payload/elsewhere.json`;
    reseal(root, report, manifest);
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.ok(codes(verified).includes('ARTIFACT_KEY_MISMATCH'));
});

test('a marker that disagrees with its own manifest is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'markerdisagree');
    const markerPath = absoluteFor(root, report.completeness_object_key);
    const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
    marker.source_state_hash = 'f'.repeat(64);
    rewrite(markerPath, Buffer.from(canonicalJson(marker), 'utf8'));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['IDENTITY_MISMATCH']);
});

test('a non-canonical marker is refused rather than tolerated', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'noncanonical');
    const markerPath = absoluteFor(root, report.completeness_object_key);
    rewrite(markerPath, Buffer.from(JSON.stringify(JSON.parse(fs.readFileSync(markerPath, 'utf8')), null, 2), 'utf8'));
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['INVALID_COMPLETENESS_MARKER']);
});

test('a manifest whose summary contradicts its captured identity is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'summarydrift');
    const manifest = readManifest(root, report);
    manifest.source = { ...manifest.source, observation_count: manifest.source.observation_count + 1 };
    reseal(root, report, manifest);
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.deepEqual(codes(verified), ['SOURCE_SUMMARY_MISMATCH']);
});

test('a manifest missing a required category is refused', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'nocategory');
    const manifest = readManifest(root, report);
    const dropped = manifest.artifacts.find(artifact => artifact.category === 'quota_config');
    manifest.artifacts = manifest.artifacts.filter(artifact => artifact !== dropped);
    manifest.artifact_count = manifest.artifacts.length;
    manifest.total_bytes -= dropped.size;
    reseal(root, report, manifest);
    const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'FAIL');
    assert.ok(codes(verified).includes('MISSING_REQUIRED_CATEGORY'));
    assert.ok(codes(verified).includes('UNEXPECTED_OBJECT'), 'the orphaned object remains as evidence rather than being deleted');
});

test('loadAcceptedManifest refuses a generation that was never sealed', async t => {
    const { root, transport, report } = await sealedGeneration(t, 'unsealed');
    assert.ok((await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id })).manifest);
    fs.rmSync(absoluteFor(root, report.completeness_object_key));
    await assert.rejects(
        loadAcceptedManifest({ transport, snapshotId: report.snapshot_id }),
        error => error instanceof SnapshotIntegrityError && /no completeness marker/.test(error.message)
    );
});

test('a malformed generation id is refused before anything is read', async t => {
    const { transport } = await sealedGeneration(t, 'badid');
    for (const bad of ['../escape', 'snap_20260913T000000000Z_0011223344556677/../..', 'not-a-generation', null]) {
        await assert.rejects(verifySnapshot({ transport, snapshotId: bad }), error => error instanceof SnapshotIntegrityError);
    }
});

test('the manifest source tuple can be compared against a freshly captured identity', () => {
    const fx = fixture();
    const identity = captureSourceIdentity({
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
    });
    const manifest = { source: { ...identity.authority, input_set_sha256: 'a'.repeat(64) } };
    assert.deepEqual(compareSnapshotToSourceIdentity(manifest, identity), { matches: true, mismatches: [] });

    const drifted = { source: { ...manifest.source, head_sequence: identity.authority.head_sequence + 1, state_hash: 'b'.repeat(64) } };
    assert.deepEqual(compareSnapshotToSourceIdentity(drifted, identity), { matches: false, mismatches: ['head_sequence', 'state_hash'] });
});

test('verification performs no outbound network access', async t => {
    const { transport, report } = await sealedGeneration(t, 'offline');
    assert.deepEqual(tripwire.attempts, []);
    await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    await assert.rejects(verifySnapshot({ transport, snapshotId: '../escape' }));
    assert.deepEqual(tripwire.attempts, []);
});
