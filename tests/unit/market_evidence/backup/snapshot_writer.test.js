'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');

// The writer is the half that would reach a provider if anything ever did, so
// the whole file is sealed rather than only the test that performs a write.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});
const { createLocalTransport } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { ObjectAlreadyExistsError, SnapshotIntegrityError, TransportContractError } = require('../../../../src/infrastructure/market_evidence/backup/transport');
const { writeSnapshot, SourceChangedDuringSnapshotError } = require('../../../../src/infrastructure/market_evidence/backup/snapshotWriter');
const { readRequestLedger, recordRequestIntent } = require('../../../../src/infrastructure/market_evidence/stageDOperations');
const { CATEGORY } = require('../../../../src/infrastructure/market_evidence/backup/snapshotInputs');
const { completenessObjectKey, manifestObjectKey, parseCanonicalJsonObject, validateCompletenessMarker, validateSnapshotManifest } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 1 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

function storeRoot(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-writer-store-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

function writeOptions(overrides = {}) {
    const fx = fixture();
    return {
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
        ...overrides,
    };
}

function assertStoredMatchesSource(transport, manifest, logicalPath, sourcePath) {
    const artifact = manifest.artifacts.find(candidate => candidate.logical_path === logicalPath);
    assert.ok(artifact, `${logicalPath} must be in the manifest`);
    const stored = transport.getObject({ key: artifact.object_key });
    assert.equal(stored.length, artifact.size);
    assert.deepEqual(stored, fs.readFileSync(sourcePath), `${logicalPath} must be byte-identical to its governed source`);
}

// `wrapTransport` fires on the first write, which happens before most of the
// payload has been read.  The content check exists for a window that opens
// later than that: after a governed file has been read and written, while the
// copy is still running.  This fires on the write whose key matches instead, so
// the source moves after the copy has taken its version of it and before the
// post-copy re-read that is meant to notice.
function wrapTransportAfterPut(inner, matches, onMatch) {
    let fired = false;
    return {
        putObjectCreateOnly(params) {
            const written = inner.putObjectCreateOnly(params);
            if (!fired && matches(params.key)) {
                fired = true;
                onMatch();
            }
            return written;
        },
        getObject: params => inner.getObject(params),
        headObject: params => inner.headObject(params),
        listObjects: params => inner.listObjects(params),
        describe: () => inner.describe(),
    };
}

function wrapTransport(inner, onFirstPut) {
    let fired = false;
    return {
        putObjectCreateOnly(params) {
            if (!fired) {
                fired = true;
                onFirstPut();
            }
            return inner.putObjectCreateOnly(params);
        },
        getObject: params => inner.getObject(params),
        headObject: params => inner.headObject(params),
        listObjects: params => inner.listObjects(params),
        describe: () => inner.describe(),
    };
}

test('a snapshot contains every governed input plus a sealed manifest and marker', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const report = await writeSnapshot({ transport, ...writeOptions() });

    const objects = transport.listObjects({ prefix: `${report.snapshot_id}/` });
    assert.equal(objects.length, report.artifact_count + 2, 'exactly the payload, the manifest and the marker');

    const manifest = parseCanonicalJsonObject(transport.getObject({ key: manifestObjectKey(report.snapshot_id) }), 'manifest');
    assert.equal(validateSnapshotManifest(manifest), true);
    assert.equal(manifest.snapshot_id, report.snapshot_id);
    assert.equal(manifest.artifact_count, report.artifact_count);
    assert.equal(manifest.secrets_included, false);

    const marker = parseCanonicalJsonObject(transport.getObject({ key: completenessObjectKey(report.snapshot_id) }), 'marker');
    assert.equal(validateCompletenessMarker(marker), true);
    assert.equal(marker.manifest_sha256, report.manifest_sha256);
    assert.equal(marker.manifest_object_key, manifestObjectKey(report.snapshot_id));
});

test('every payload object is byte-identical to its governed source', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const report = await writeSnapshot({ transport, ...writeOptions() });
    const manifest = parseCanonicalJsonObject(transport.getObject({ key: report.manifest_object_key }), 'manifest');
    const fx = fixture();
    await assertStoredMatchesSource(transport, manifest, 'transactions/STORE.json', path.join(fx.authorityRoot, 'STORE.json'));
    await assertStoredMatchesSource(transport, manifest, 'transactions/allocation.authority.json', fx.allocationArtifactPath);
    const committed = manifest.artifacts.find(artifact => artifact.category === 'transaction_package');
    await assertStoredMatchesSource(transport, manifest, committed.logical_path, path.join(fx.authorityRoot, committed.logical_path.replace('transactions/', '')));
    for (const artifact of manifest.artifacts) assert.equal(transport.getObject({ key: artifact.object_key }).length, artifact.size);
});

test('the manifest binds the source identity before and after the copy', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const report = await writeSnapshot({ transport, ...writeOptions() });
    const manifest = parseCanonicalJsonObject(transport.getObject({ key: report.manifest_object_key }), 'manifest');
    assert.equal(manifest.source_identity_equal, true);
    assert.deepEqual(manifest.source_before, manifest.source_after);
    assert.equal(manifest.source.head_transaction_id, report.source_head_transaction_id);
    assert.equal(manifest.source.state_hash, report.source_state_hash);
    assert.equal(manifest.source.observation_count, report.observation_count);
    assert.equal(manifest.store_sha256, manifest.source_before.authority.store_sha256);
    assert.equal(manifest.allocation_authority_sha256, manifest.source_before.authority.allocation_authority_content_hash);
});

test('staging never reaches a generation', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const report = await writeSnapshot({ transport, ...writeOptions() });
    assert.equal(report.staging_excluded, true);
    for (const entry of transport.listObjects({ prefix: `${report.snapshot_id}/` })) {
        assert.equal(entry.key.includes('.staging'), false, `${entry.key} must not be staged`);
    }
});

test('the report carries the category census and no payload bytes', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const report = await writeSnapshot({ transport, ...writeOptions() });
    assert.ok(report.categories[CATEGORY.TRANSACTION_PACKAGE] >= 1);
    assert.equal(report.categories[CATEGORY.STORE], 1);
    assert.equal(report.categories[CATEGORY.ALLOCATION_AUTHORITY], 1);
    assert.equal(report.categories[CATEGORY.REQUEST_ACCOUNTING_EPOCH], 1);
    assert.equal(report.categories[CATEGORY.QUOTA_CONFIG], 1);
    const serialized = JSON.stringify(report);
    assert.equal(serialized.includes('BEGIN'), false);
    assert.equal(/access[_-]?key|secret[_-]?access/i.test(serialized), false);
});

test('a generation that already exists is never overwritten', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const first = await writeSnapshot({ transport, ...writeOptions() });
    await assert.rejects(
        writeSnapshot({ transport, ...writeOptions(), snapshotId: first.snapshot_id }),
        error => error instanceof ObjectAlreadyExistsError && error.code === 'OBJECT_ALREADY_EXISTS'
    );
    assert.equal(transport.getObject({ key: first.manifest_object_key }).length > 0, true);
});

test('a generation whose marker is missing is treated as occupied', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    const snapshotId = 'snap_20260913T000000000Z_0011223344556677';
    transport.putObjectCreateOnly({ key: `${snapshotId}/payload/transactions/STORE.json`, bytes: Buffer.from('{}') });
    await assert.rejects(
        writeSnapshot({ transport, ...writeOptions(), snapshotId }),
        error => error instanceof ObjectAlreadyExistsError
    );
});

test('a source that moves during the copy aborts the generation before the marker', async t => {
    const fx = fixture();
    const transport = wrapTransport(createLocalTransport({ root: storeRoot(t) }), () => {
        recordRequestIntent({ ledgerRoot: fx.ledgerRoot, requestId: 'late-request', runId: 'late-run', createdAt: '2026-09-13T02:00:00Z', recordedAt: '2026-09-13T02:00:00Z' });
    });
    let caught = null;
    try {
        await writeSnapshot({ transport, ...writeOptions(), snapshotId: 'snap_20260913T000000000Z_0011223344556677' });
    } catch (error) {
        caught = error;
    }
    assert.ok(caught instanceof SourceChangedDuringSnapshotError, `expected a source-change abort, received ${caught && caught.message}`);
    assert.equal(caught.code, 'SOURCE_CHANGED_DURING_SNAPSHOT');
    assert.equal(transport.getObject({ key: completenessObjectKey('snap_20260913T000000000Z_0011223344556677') }), null, 'a partial generation must carry no completeness marker');
    assert.equal(transport.getObject({ key: manifestObjectKey('snap_20260913T000000000Z_0011223344556677') }), null, 'a partial generation must carry no manifest');
    assert.ok(transport.listObjects({ prefix: 'snap_20260913T000000000Z_0011223344556677/' }).length > 0, 'the partial payload is left in place rather than deleted');
    assert.ok(readRequestLedger({ ledgerRoot: fx.ledgerRoot }).requests.some(request => request.request_id === 'late-request'));
});

test('a governed input set that grows during the copy aborts the generation', async t => {
    const fx = fixture();
    const runStateRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-writer-runstate-'));
    t.after(() => fs.rmSync(runStateRoot, { recursive: true, force: true }));
    fs.writeFileSync(path.join(runStateRoot, 'turn.json'), '{"turn":1}');
    const transport = wrapTransport(createLocalTransport({ root: storeRoot(t) }), () => {
        fs.writeFileSync(path.join(runStateRoot, 'appeared-mid-copy.json'), '{"turn":2,"appeared":true}');
    });
    await assert.rejects(
        writeSnapshot({ transport, ...writeOptions(), runStateInputs: [runStateRoot], snapshotId: 'snap_20260913T000000000Z_8899aabbccddeeff' }),
        error => error instanceof SourceChangedDuringSnapshotError && /input set changed/.test(error.message)
    );
    assert.equal(transport.getObject({ key: completenessObjectKey('snap_20260913T000000000Z_8899aabbccddeeff') }), null);
});

// The input set that grows is caught by re-enumerating it: the file is new, so
// it is visible as a new entry.  A file replaced in place at the same length is
// not.  Nothing about the set's shape changes -- the same path, the same size,
// the same count -- so re-enumerating it sees a set identical to the one before
// and the generation is sealed COMPLETE holding the old bytes of a file the
// source has since moved on from.  Only the content distinguishes the two, so
// the digest has to be over content for this case to be refused at all.
test('a governed input replaced at the same length during the copy aborts the generation', async t => {
    const runStateRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-writer-swap-'));
    t.after(() => fs.rmSync(runStateRoot, { recursive: true, force: true }));
    const turnPath = path.join(runStateRoot, 'turn.json');
    const before = '{"turn":1}';
    const after = '{"turn":2}';
    assert.equal(before.length, after.length, 'the replacement must be the same length for this case to mean anything');
    fs.writeFileSync(turnPath, before);

    const snapshotId = 'snap_20260913T000000000Z_ffeeddccbbaa9988';
    const transport = wrapTransportAfterPut(
        createLocalTransport({ root: storeRoot(t) }),
        key => key === `${snapshotId}/payload/run-state/turn.json`,
        () => fs.writeFileSync(turnPath, after),
    );

    await assert.rejects(
        writeSnapshot({ transport, ...writeOptions(), runStateInputs: [runStateRoot], snapshotId }),
        error => error instanceof SourceChangedDuringSnapshotError && /input set changed/.test(error.message)
    );

    assert.equal(fs.readFileSync(turnPath, 'utf8'), after, 'the source must really have moved');
    assert.equal(transport.getObject({ key: completenessObjectKey(snapshotId) }), null, 'a generation holding a mixture of two moments must carry no completeness marker');
    assert.equal(transport.getObject({ key: manifestObjectKey(snapshotId) }), null, 'a generation holding a mixture of two moments must carry no manifest');
    // The bytes that were copied are the ones the source no longer holds -- which
    // is exactly why the marker above must be absent rather than merely unread.
    const stored = transport.getObject({ key: `${snapshotId}/payload/run-state/turn.json` });
    assert.equal(stored.toString('utf8'), before);
});

test('the writer refuses a transport that violates the contract', async () => {
    const fake = { putObjectCreateOnly: () => {}, getObject: () => null, headObject: () => null, listObjects: () => [], deleteObject: () => {}, describe: () => ({ create_only: true, delete_exposed: false }) };
    await assert.rejects(writeSnapshot({ transport: fake, ...writeOptions() }), error => error instanceof TransportContractError && /forbidden capability/.test(error.message));
    await assert.rejects(writeSnapshot({ ...writeOptions() }), error => error instanceof TransportContractError);
});

test('the writer refuses a malformed generation id and honours a well formed one', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    await assert.rejects(writeSnapshot({ transport, ...writeOptions(), snapshotId: 'not-a-generation' }), error => error instanceof SnapshotIntegrityError);
    const report = await writeSnapshot({ transport, ...writeOptions(), snapshotId: 'snap_20260913T000000000Z_0011223344556677' });
    assert.equal(report.snapshot_id, 'snap_20260913T000000000Z_0011223344556677');
});

test('the writer performs no outbound network access', async t => {
    const transport = createLocalTransport({ root: storeRoot(t) });
    await writeSnapshot({ transport, ...writeOptions() });
    assert.deepEqual(tripwire.attempts, []);
});
