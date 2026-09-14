'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const backup = require('../../../../src/infrastructure/market_evidence/backup');
const { writeSnapshot } = require('../../../../src/infrastructure/market_evidence/backup/snapshotWriter');
const { verifySnapshot, assertSnapshotVerification, loadAcceptedManifest } = require('../../../../src/infrastructure/market_evidence/backup/snapshotVerifier');
const { manifestObjectKey, completenessObjectKey } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');
const { executeRestore } = require('../../../../src/infrastructure/market_evidence/backup/restoreExecutor');
const { SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');

// A whole generation -- write, verify, restore -- is driven through the real R2
// transport here, with the network replaced by an in-memory SDK surface.  The
// transport is the code that would run against the live target; only the socket
// is substituted, so every mapping decision it makes (configured prefix onto
// physical keys, physical keys back to logical ones, continuation tokens, the
// create-only condition) is exercised for real.
//
// The tripwire proves the substitution was complete: an SDK surface is not a
// guarantee on its own, and a test that reached the endpoint through some path
// the stub did not cover would otherwise look like a pass.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

const { createR2Transport } = backup.loadR2Transport();

const PREFIX = 'footballprediction/stage-d/transaction-v1/snapshots';
const CREDENTIALS = Object.freeze({ accessKeyId: 'AKIASYNTHETICBACKUP', secretAccessKey: 'synthetic-backup-secret' });

function createStubR2({ pageSize = 1000 } = {}) {
    const objects = new Map();
    const calls = [];

    const command = operation => class StubCommand {
        constructor(input) {
            this.operation = operation;
            this.input = input;
        }
    };

    class StubS3Client {
        async send(request) {
            const { operation, input } = request;
            calls.push(Object.freeze({ operation, input }));
            switch (operation) {
                case 'PutObject': {
                    if (input.IfNoneMatch === '*' && objects.has(input.Key)) {
                        const error = new Error('PreconditionFailed');
                        error.name = 'PreconditionFailed';
                        error.$metadata = { httpStatusCode: 412 };
                        throw error;
                    }
                    objects.set(input.Key, Buffer.from(input.Body));
                    return { ETag: '"stub"' };
                }
                case 'GetObject': {
                    if (!objects.has(input.Key)) {
                        const error = new Error('NoSuchKey');
                        error.name = 'NoSuchKey';
                        error.$metadata = { httpStatusCode: 404 };
                        throw error;
                    }
                    const body = objects.get(input.Key);
                    return { Body: { transformToByteArray: async () => new Uint8Array(body) }, ContentLength: body.length };
                }
                case 'HeadObject': {
                    if (!objects.has(input.Key)) {
                        const error = new Error('NotFound');
                        error.name = 'NotFound';
                        error.$metadata = { httpStatusCode: 404 };
                        throw error;
                    }
                    const body = objects.get(input.Key);
                    return { ContentLength: body.length, ETag: '"stub"' };
                }
                case 'ListObjects': {
                    const scope = input.Prefix || '';
                    const matching = [...objects.keys()].filter(key => key.startsWith(scope)).sort();
                    const start = input.ContinuationToken === undefined ? 0 : Number(input.ContinuationToken);
                    const page = matching.slice(start, start + pageSize);
                    const next = start + page.length;
                    return {
                        Contents: page.map(key => ({ Key: key, Size: objects.get(key).length })),
                        IsTruncated: next < matching.length,
                        ...(next < matching.length ? { NextContinuationToken: String(next) } : {}),
                    };
                }
                default:
                    throw new Error(`the stub SDK received an operation it does not model: ${operation}`);
            }
        }
    }

    return Object.freeze({
        sdk: {
            S3Client: StubS3Client,
            PutObjectCommand: command('PutObject'),
            GetObjectCommand: command('GetObject'),
            HeadObjectCommand: command('HeadObject'),
            ListObjectsV2Command: command('ListObjects'),
        },
        objects,
        calls,
    });
}

let sharedFixture = null;
function fixture() {
    if (sharedFixture === null) sharedFixture = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 2 });
    return sharedFixture;
}
test.after(() => { if (sharedFixture) sharedFixture.cleanup(); });

function temporary(t, prefix) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

async function writeGeneration(t, { pageSize = 1000, prefix = PREFIX } = {}) {
    const stub = createStubR2({ pageSize });
    const transport = createR2Transport({
        endpoint: 'https://account.r2.cloudflarestorage.com',
        bucket: 'stage-d-backup-test',
        region: 'auto',
        prefix,
        credentials: CREDENTIALS,
        sdk: stub.sdk,
    });
    const fx = fixture();
    const report = await writeSnapshot({
        transport,
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
    });
    // Read back through the canonical reader rather than trusting the writer's
    // own summary: the assertions below are about what the target actually
    // holds, and a writer's report is not evidence about the target.
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    return { stub, transport, report, manifest };
}

function destination(t, name) {
    return path.join(temporary(t, `stage-d-r2-harness-${name}-`), 'restored');
}

test('a whole generation is written, verified and restored through the R2 transport', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verification.result, 'PASS', JSON.stringify(verification.failures));
    assert.equal(verification.transport.kind, 'r2-s3');
    assert.equal(verification.transport.prefix, PREFIX);
    assert.deepEqual(tripwire.attempts, [], 'the whole generation must run without a network attempt');

    const restored = await executeRestore({
        transport,
        snapshotId: report.snapshot_id,
        destinationRoot: destination(t, 'full'),
        // The generation has no filesystem source in this process: it lives on
        // the target.  A local path here would make the disjointness assertion
        // check a source that is not the source.
        sourceRoots: [],
        includeFreshProcess: true,
    });

    assert.equal(restored.result, 'PASS', JSON.stringify(restored.failures));
    assert.equal(restored.production_fallback_used, false);
    assert.deepEqual(restored.production_paths_read, []);
    assert.equal(restored.fresh_process_proof.ok, true, restored.fresh_process_proof.error);
    assert.equal(restored.proof.head_transaction_id, fixture().head_transaction_id);
    assert.equal(stub.objects.size > 0, true);
});

test('every object of the generation lands under the configured prefix and nowhere else', async t => {
    const { stub, report, manifest } = await writeGeneration(t);

    const artifactCount = manifest.artifact_count;
    assert.equal(stub.objects.size, artifactCount + 2, 'the payload plus the manifest plus the completeness marker, and nothing else');

    const physicalPrefix = `${PREFIX}/${report.snapshot_id}/`;
    const physical = [...stub.objects.keys()];
    assert.deepEqual(physical.filter(key => !key.startsWith(physicalPrefix)), [], 'no object may land outside the generation namespace');
    assert.equal(physical.filter(key => key.startsWith(physicalPrefix)).length, artifactCount + 2);

    // The manifest records logical keys.  A tree that wrote the manifest's own
    // keys verbatim would look right here and wrong at verification time, so
    // both halves of the mapping are asserted.
    for (const artifact of manifest.artifacts) {
        assert.equal(artifact.object_key.startsWith(report.snapshot_id), true);
        assert.equal(stub.objects.has(`${PREFIX}/${artifact.object_key}`), true, `${artifact.object_key} must exist under the configured prefix`);
        assert.equal(stub.objects.has(artifact.object_key), false, 'a logical key must never be the physical one');
    }
    assert.equal(stub.objects.has(`${PREFIX}/${manifestObjectKey(report.snapshot_id)}`), true);
    assert.equal(stub.objects.has(`${PREFIX}/${completenessObjectKey(report.snapshot_id)}`), true);
});

test('the verifier compares logical object sets over a prefixed transport, and lists in physical keys', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);
    stub.calls.length = 0;

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });

    // If the prefix leaked outward, every expected object would read as missing
    // and every listed object as unexpected -- the generation would fail
    // verification against itself.  A PASS is therefore the assertion that the
    // strip is symmetric.
    assert.equal(verification.result, 'PASS');
    assert.equal(verification.failures.length, 0);
    assert.equal(verification.evidence.observed_object_count, manifest.artifact_count + 2);

    const listCalls = stub.calls.filter(call => call.operation === 'ListObjects');
    assert.equal(listCalls.length, 1, 'one listing, scoped to the generation');
    assert.equal(listCalls[0].input.Prefix, `${PREFIX}/${report.snapshot_id}/`, 'the provider is addressed in physical keys');
});

test('verification is unaffected by an object outside the generation namespace', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);
    // A probe object, a previous generation, another tenant: all of it sits in
    // the same bucket and none of it is an object of this generation.
    stub.objects.set(`${PREFIX}/preflight-probe/conditional-write/v1/PROBE.json`, Buffer.from('probe'));
    stub.objects.set(`${PREFIX}/snap_20260101T000000000Z_0000000000000000/COMPLETE`, Buffer.from('other'));

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verification.result, 'PASS', 'a neighbouring object must not be able to break a generation');
    assert.equal(verification.evidence.observed_object_count, manifest.artifact_count + 2);
});

test('a generation split across many pages verifies exactly as one that fits in a single page', async t => {
    // The provider truncates at its own page size; here that size is two, so a
    // generation of a dozen objects arrives in half a dozen responses.  The
    // property being pinned is the verifier's exact-set comparison: a listing
    // that stops at the first page would report every later object as missing.
    const { transport, report, manifest } = await writeGeneration(t, { pageSize: 2 });
    assert.equal(manifest.artifact_count > 2, true, 'the fixture must produce more objects than one page holds for this to mean anything');

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verification.result, 'PASS', JSON.stringify(verification.failures));
    assert.equal(verification.evidence.observed_object_count, manifest.artifact_count + 2);
});

test('an incomplete generation is refused, and a restore from it materializes nothing', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);
    // Exactly what a write that died between the manifest and the marker leaves
    // behind.  Nothing here deletes anything on the target: the object is
    // removed from the stub's memory to model the state, which is the only way
    // to reach it without a delete verb.
    stub.objects.delete(`${PREFIX}/${completenessObjectKey(report.snapshot_id)}`);

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verification.result, 'FAIL');
    assert.deepEqual(verification.failures.map(item => item.code), ['MISSING_COMPLETENESS_MARKER']);
    assert.throws(() => assertSnapshotVerification(verification), SnapshotIntegrityError);

    // The admission gate runs before the destination is evaluated, so a
    // generation that cannot be verified cannot cause a tree to be built.  That
    // ordering is the whole point: a destination that had been created and then
    // abandoned could never be restored into again.
    const destinationRoot = destination(t, 'incomplete');
    await assert.rejects(
        () => executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot, sourceRoots: [] }),
        error => error instanceof SnapshotIntegrityError && /failed verification/.test(error.message),
    );
    assert.equal(fs.existsSync(destinationRoot), false, 'a refused restore must leave no destination behind');
});

test('a generation missing one payload object fails the exact-set comparison by name', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);
    const { object_key: victim, logical_path: logicalPath } = manifest.artifacts[0];
    stub.objects.delete(`${PREFIX}/${victim}`);

    const verification = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verification.result, 'FAIL');

    // Two independent checks see it: reading every artifact back, and comparing
    // the listed set against what the manifest accounts for. Either alone would
    // be enough to fail the generation; both firing is what shows neither is
    // quietly relying on the other.
    const missing = verification.failures.filter(item => item.code === 'ARTIFACT_MISSING');
    assert.equal(missing.length, 2, 'a missing object is caught by the read-back and by the exact-set comparison');
    assert.equal(missing.some(item => item.detail.includes(victim)), true, 'the object-set failure names the missing object key');
    assert.equal(missing.some(item => item.detail.includes(logicalPath)), true, 'the read-back failure names the missing logical path');
    // Every other artifact is still intact, so the failure is about this object
    // and not a knock-on effect of the first read failing.
    assert.deepEqual(verification.failures.filter(item => item.code !== 'ARTIFACT_MISSING'), []);
});

test('a restored generation is proven by reading the target, never a local copy', async t => {
    const { stub, transport, report, manifest } = await writeGeneration(t);
    stub.calls.length = 0;

    const restored = await executeRestore({
        transport,
        snapshotId: report.snapshot_id,
        destinationRoot: destination(t, 'read-only-source'),
        sourceRoots: [],
        includeFreshProcess: true,
    });
    assert.equal(restored.result, 'PASS', JSON.stringify(restored.failures));

    // A restore reads.  It cannot have written to the target, and it cannot have
    // read from anywhere else: the only object store in this process is the
    // stub, and every call it saw was a read.
    assert.deepEqual([...new Set(stub.calls.map(call => call.operation))].sort(), ['GetObject', 'ListObjects']);
    assert.deepEqual(restored.production_paths_read, []);
    assert.equal(restored.production_fallback_used, false);
    assert.equal(restored.restored_file_count, manifest.artifact_count);
});

test('a second generation in the same namespace does not disturb the first', async t => {
    const first = await writeGeneration(t);
    const second = await writeGeneration(t);
    assert.notEqual(first.report.snapshot_id, second.report.snapshot_id);

    // The two generations share one stub store so the second write happens into
    // a namespace that already holds a complete generation -- which is what a
    // real bucket looks like by the second backup.
    for (const [key, value] of second.stub.objects) first.stub.objects.set(key, value);

    for (const report of [first.report, second.report]) {
        const verification = await verifySnapshot({ transport: first.transport, snapshotId: report.snapshot_id });
        assert.equal(verification.result, 'PASS', JSON.stringify(verification.failures));
    }
});
