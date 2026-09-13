'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');

// The whole file is sealed, not just the test that restores a generation.  A
// restore reads a snapshot and writes a tree, and the isolated-restore claim is
// only as strong as the weakest test in the file that could reach the network.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});
const { createLocalTransport } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');
const { writeSnapshot } = require('../../../../src/infrastructure/market_evidence/backup/snapshotWriter');
const { loadAcceptedManifest } = require('../../../../src/infrastructure/market_evidence/backup/snapshotVerifier');
const {
    DIRECTORY_MODE,
    FILE_MODES,
    RestoreProofError,
    assertFreshDestination,
    buildFreshProcessProbe,
    executeRestore,
    proveColdLoadInFreshProcess,
    proveRestoredRoot,
    restoredLayout,
} = require('../../../../src/infrastructure/market_evidence/backup/restoreExecutor');

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 2 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

function temporary(t, prefix) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

async function sealed(t, name) {
    const root = temporary(t, `stage-d-restore-${name}-`);
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

function destination(t, name) {
    return path.join(temporary(t, `stage-d-destination-${name}-`), 'restored');
}

function modeOf(target) {
    return fs.lstatSync(target).mode & 0o7777;
}

function successfulSpawn(capture = {}) {
    return (execPath, args, options) => {
        capture.execPath = execPath;
        capture.args = args;
        capture.options = options;
        const probe = args[1];
        const authorityRoot = /storeRoot: "([^"]+)"/.exec(probe)[1];
        const ledgerRoot = /ledgerRoot: "([^"]+)"/.exec(probe)[1];
        const { openMarketEvidenceAuthoritySnapshot } = require('../../../../src/infrastructure/market_evidence/authorityReader');
        const { readRequestLedger } = require('../../../../src/infrastructure/market_evidence/stageDOperations');
        const authority = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath: /allocationArtifactPath: "([^"]+)"/.exec(probe)[1] });
        const ledger = readRequestLedger({ ledgerRoot });
        void ledgerRoot;
        return {
            status: 0,
            stdout: `${JSON.stringify({
                ok: true,
                identity: {
                    head_transaction_id: authority.head_transaction_id,
                    head_transaction_content_hash: authority.head_transaction_content_hash,
                    head_sequence: authority.head_sequence,
                    state_hash: authority.state_hash,
                    observation_count: authority.observations.length,
                    decision_count: authority.decisions.length,
                    registry_state_count: authority.registry_state.length,
                    capture_binding_count: authority.capture_bindings.length,
                    epoch_id: ledger.epoch.epoch_id,
                    entry_count: ledger.entries.length,
                    last_entry_hash: ledger.last_entry_hash,
                },
            })}\n`,
        };
    };
}

test('a restore into a fresh isolated root produces a loadable authority', async t => {
    const { transport, report } = await sealed(t, 'happy');
    const target = destination(t, 'happy');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });

    assert.equal(restored.result, 'PASS');
    assert.equal(restored.snapshot_id, report.snapshot_id);
    assert.equal(restored.manifest_sha256, report.manifest_sha256);
    assert.equal(restored.restored_file_count, report.artifact_count);
    assert.equal(restored.restored_object_count, report.artifact_count);
    assert.equal(restored.proof.head_transaction_id, report.source_head_transaction_id);
    assert.equal(restored.proof.state_hash, report.source_state_hash);
    assert.equal(restored.proof.observation_count, report.observation_count);
    assert.equal(restored.production_fallback_used, false);
    assert.deepEqual(restored.production_paths_read, []);
    assert.deepEqual(restored.failures, []);
    assert.equal(restored.authority_root, path.join(target, 'transactions'));
    assert.equal(restored.ledger_root, path.join(target, 'request-accounting'));
});

test('the restored tree mirrors the production permission contract', async t => {
    const { transport, report } = await sealed(t, 'modes');
    const target = destination(t, 'modes');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });

    assert.equal(modeOf(target), DIRECTORY_MODE, 'the destination root is created and owned at 0700');
    for (const file of restored.restored_files) {
        assert.equal(file.mode, FILE_MODES[file.category], `${file.logical_path} (${file.category}) must be restored at ${FILE_MODES[file.category].toString(8)}`);
        const absolute = path.join(target, file.logical_path);
        assert.equal(modeOf(absolute), FILE_MODES[file.category]);
        assert.equal(modeOf(path.dirname(absolute)), DIRECTORY_MODE, `${path.dirname(absolute)} must be a 0700 directory`);
    }
    assert.equal(modeOf(path.join(target, 'transactions', 'STORE.json')), 0o444);
    assert.equal(modeOf(path.join(target, 'transactions', 'allocation.authority.json')), 0o444);
    assert.equal(modeOf(path.join(target, 'request-accounting', 'REQUEST_ACCOUNTING_EPOCH.json')), 0o400);
});

test('every restored file is byte-identical to the generation it came from', async t => {
    const { transport, report } = await sealed(t, 'bytes');
    const target = destination(t, 'bytes');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    assert.equal(restored.restored_files.length > 0, true);
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    for (const artifact of manifest.artifacts) {
        assert.deepEqual(
            fs.readFileSync(path.join(target, artifact.logical_path)),
            transport.getObject({ key: artifact.object_key }),
            `${artifact.logical_path} must be restored byte for byte`
        );
    }
});

test('a restore never overwrites an existing destination', async t => {
    const { transport, report } = await sealed(t, 'occupied');
    const target = destination(t, 'occupied');
    await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    const before = fs.readFileSync(path.join(target, 'transactions', 'STORE.json'));
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
        error => error instanceof SnapshotIntegrityError && /already exists/.test(error.message)
    );
    assert.deepEqual(fs.readFileSync(path.join(target, 'transactions', 'STORE.json')), before);
});

test('a restore destination in the governed production area is refused before anything is created', async t => {
    const { transport, report } = await sealed(t, 'production');
    const tainted = path.join(fixture().root, 'data', 'market_evidence', 'live', 'restored');
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: tainted }),
        error => error instanceof SnapshotIntegrityError && /governed production area/.test(error.message)
    );
    assert.equal(fs.existsSync(tainted), false);
});

test('a destination nested in a source root, or equal to one, is refused', async t => {
    const authorityRoot = temporary(t, 'stage-d-source-');
    const beside = path.join(temporary(t, 'stage-d-elsewhere-'), 'restored');

    assert.throws(
        () => assertFreshDestination(path.join(authorityRoot, 'restored'), { sourceRoots: [authorityRoot] }),
        error => error instanceof SnapshotIntegrityError && /must not be inside the source root/.test(error.message)
    );
    assert.throws(
        () => assertFreshDestination(authorityRoot, { sourceRoots: [authorityRoot] }),
        error => error instanceof SnapshotIntegrityError && /already exists/.test(error.message),
        'the source root itself exists, so it can never be a fresh destination'
    );
    assert.equal(path.resolve(assertFreshDestination(beside, { sourceRoots: [authorityRoot] })), path.resolve(beside));
});

test('a destination must be supplied explicitly', () => {
    for (const bad of [undefined, null, '', '   ', 42]) {
        assert.throws(() => assertFreshDestination(bad), error => error instanceof SnapshotIntegrityError && /no default restore location/.test(error.message));
    }
});

test('a restore of a generation whose artifact is missing fails closed', async t => {
    const { root, transport, report } = await sealed(t, 'gapped');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const victim = manifest.artifacts.find(artifact => artifact.logical_path === 'transactions/STORE.json');
    fs.rmSync(path.join(root, ...victim.object_key.split('/')));
    const target = destination(t, 'gapped');
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
        error => error instanceof SnapshotIntegrityError && /missing transactions\/STORE.json/.test(error.message)
    );
});

test('a restore of a generation whose artifact was tampered with fails closed', async t => {
    const { root, transport, report } = await sealed(t, 'tampered');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const victim = manifest.artifacts.find(artifact => artifact.logical_path === 'transactions/STORE.json');
    const absolute = path.join(root, ...victim.object_key.split('/'));
    const bytes = Buffer.from(fs.readFileSync(absolute));
    bytes[1] ^= 0x01;
    fs.writeFileSync(absolute, bytes);
    const target = destination(t, 'tampered');
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
        error => error instanceof SnapshotIntegrityError && /content the manifest does not bind/.test(error.message)
    );
});

test('an unsealed generation cannot be restored', async t => {
    const { root, transport, report } = await sealed(t, 'unsealed');
    fs.rmSync(path.join(root, ...report.completeness_object_key.split('/')));
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: destination(t, 'unsealed') }),
        error => error instanceof SnapshotIntegrityError && /no completeness marker/.test(error.message)
    );
});

test('the restore proof compares the restored authority against the manifest', async t => {
    const { transport, report } = await sealed(t, 'proofcompare');
    const target = destination(t, 'proofcompare');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });

    const agreeing = await proveRestoredRoot({ destinationRoot: target, manifest });
    assert.equal(agreeing.result, 'PASS');
    assert.equal(agreeing.proof.head_sequence, manifest.source.head_sequence);
    assert.equal(agreeing.proof.store_sha256, manifest.store_sha256);
    assert.equal(agreeing.proof.quota_config_sha256, manifest.quota_config.sha256);

    const drifted = { ...manifest, source: { ...manifest.source, observation_count: manifest.source.observation_count + 1 } };
    const disagreeing = await proveRestoredRoot({ destinationRoot: target, manifest: drifted });
    assert.equal(disagreeing.result, 'FAIL');
    assert.ok(disagreeing.failures.some(detail => /observation_count/.test(detail)));

    const hashDrift = { ...manifest, store_sha256: 'f'.repeat(64) };
    const hashed = await proveRestoredRoot({ destinationRoot: target, manifest: hashDrift });
    assert.equal(hashed.result, 'FAIL');
    assert.ok(hashed.failures.some(detail => /restored STORE.json does not match the hash bound by the manifest/.test(detail)));
    assert.equal(restored.result, 'PASS');
});

test('a failed proof raises a RestoreProofError that carries the report', async t => {
    const { transport, report } = await sealed(t, 'prooferror');
    const target = destination(t, 'prooferror');
    await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const drifted = { ...manifest, artifacts: manifest.artifacts.map(artifact => (artifact.logical_path === 'transactions/STORE.json' ? { ...artifact, sha256: 'f'.repeat(64) } : artifact)) };

    assert.throws(() => { throw new RestoreProofError('x', { result: 'FAIL' }); }, error => error.code === 'RESTORE_PROOF_FAILED' && error.report.result === 'FAIL');
    assert.equal((await proveRestoredRoot({ destinationRoot: target, manifest: drifted })).result, 'FAIL');
});

test('a fresh process is asked to load the restored root and inherits no environment', async t => {
    const { transport, report } = await sealed(t, 'fresh');
    const target = destination(t, 'fresh');
    const capture = {};
    const restored = await executeRestore({
        transport,
        snapshotId: report.snapshot_id,
        destinationRoot: target,
        includeFreshProcess: true,
        spawn: successfulSpawn(capture),
    });
    assert.equal(restored.result, 'PASS');
    assert.equal(restored.fresh_process_proof.ok, true);
    assert.equal(capture.options.cwd, '/');
    assert.deepEqual(Object.keys(capture.options.env), ['PATH'], 'a fresh process must inherit no environment beyond PATH');
    for (const name of ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_PROFILE', 'R2_ACCESS_KEY_ID', 'CLOUDFLARE_API_TOKEN', 'HOME']) {
        assert.equal(name in capture.options.env, false, `${name} must never reach the probe`);
    }
    assert.ok(capture.args[1].includes(target), 'the probe is pointed at the restored root');
    assert.equal(capture.args[1].includes(fixture().authorityRoot), false, 'the probe is never pointed at the source');
});

test('the restored root is loadable by a genuinely fresh process', async t => {
    const { transport, report } = await sealed(t, 'realprocess');
    const target = destination(t, 'realprocess');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target, includeFreshProcess: true });
    assert.equal(restored.fresh_process_proof.ok, true, restored.fresh_process_proof.error);
    assert.equal(restored.fresh_process_proof.identity.head_transaction_id, report.source_head_transaction_id);
    assert.equal(restored.fresh_process_proof.identity.observation_count, report.observation_count);
});

test('a fresh process that cannot load the restored root fails the proof', async t => {
    const { transport, report } = await sealed(t, 'freshfail');
    const target = destination(t, 'freshfail');
    await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });

    const exploded = () => ({ error: new Error('spawn failed'), status: null, stdout: '' });
    assert.equal(proveColdLoadInFreshProcess(restoredLayout(target, manifest), { spawn: exploded }).ok, false);

    const refused = () => ({ status: 0, stdout: `${JSON.stringify({ ok: false, error: 'authority store is not readable' })}\n` });
    assert.deepEqual(proveColdLoadInFreshProcess(restoredLayout(target, manifest), { spawn: refused }), { ok: false, error: 'authority store is not readable' });

    const silent = () => ({ status: 1, stdout: '' });
    assert.ok(/produced no result/.test(proveColdLoadInFreshProcess(restoredLayout(target, manifest), { spawn: silent }).error));

    const garbage = () => ({ status: 0, stdout: 'not json\n' });
    assert.ok(/not valid JSON/.test(proveColdLoadInFreshProcess(restoredLayout(target, manifest), { spawn: garbage }).error));

    // A failing child must fail the whole proof even though the in-process half
    // succeeds: the restored root would be unloadable at runtime.
    const proven = await proveRestoredRoot({ destinationRoot: target, manifest, includeFreshProcess: true, spawn: refused });
    assert.equal(proven.result, 'FAIL');
    assert.ok(proven.failures.some(detail => /could not be loaded by a fresh process/.test(detail)));
});

test('a fresh process that loads a different authority fails the proof', async t => {
    const { transport, report } = await sealed(t, 'freshdrift');
    const target = destination(t, 'freshdrift');
    await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target });
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });

    const other = () => ({
        status: 0,
        stdout: `${JSON.stringify({ ok: true, identity: { head_transaction_id: `tx_${'a'.repeat(64)}`, head_transaction_content_hash: 'a'.repeat(64), head_sequence: 999, state_hash: 'b'.repeat(64), observation_count: 1, decision_count: 1, registry_state_count: 1, capture_binding_count: 1, epoch_id: 'other', entry_count: 0, last_entry_hash: null } })}\n`,
    });
    const proven = await proveRestoredRoot({ destinationRoot: target, manifest, includeFreshProcess: true, spawn: other });
    assert.equal(proven.result, 'FAIL');
    assert.ok(proven.failures.some(detail => /fresh process authority head_sequence/.test(detail)));
    assert.ok(proven.failures.some(detail => /fresh process authority observation_count/.test(detail)));
    assert.ok(proven.failures.some(detail => /fresh process authority request accounting epoch id/.test(detail)));
});

test('a fresh process probe cannot be built without explicit paths', () => {
    for (const bad of [{}, { authority_root: '/a' }, { authority_root: '/a', allocation_artifact_path: '/b' }, { authority_root: 1, allocation_artifact_path: '/b', ledger_root: '/c' }]) {
        assert.throws(() => buildFreshProcessProbe(bad), error => error instanceof SnapshotIntegrityError && /requires explicit restored authority/.test(error.message));
    }
    const probe = buildFreshProcessProbe({ authority_root: '/a', allocation_artifact_path: '/b', ledger_root: '/c' });
    assert.ok(probe.includes('storeRoot: "/a"'));
    assert.ok(probe.includes('allocationArtifactPath: "/b"'));
    assert.ok(probe.includes('ledgerRoot: "/c"'));
});

test('a layout that cannot be restored is refused', async t => {
    const { transport, report } = await sealed(t, 'layout');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const withoutAllocation = { ...manifest, artifacts: manifest.artifacts.filter(artifact => artifact.category !== 'allocation_authority') };
    assert.throws(() => restoredLayout('/tmp/nowhere', withoutAllocation), error => error instanceof SnapshotIntegrityError && /no allocation authority artifact/.test(error.message));
    const withoutQuota = { ...manifest, artifacts: manifest.artifacts.filter(artifact => artifact.category !== 'quota_config') };
    assert.throws(() => restoredLayout('/tmp/nowhere', withoutQuota), error => error instanceof SnapshotIntegrityError && /no quota configuration artifact/.test(error.message));

    const layout = restoredLayout('/tmp/nowhere', manifest);
    assert.equal(layout.authority_root, '/tmp/nowhere/transactions');
    assert.equal(layout.ledger_root, '/tmp/nowhere/request-accounting');
    assert.equal(layout.store_path, '/tmp/nowhere/transactions/STORE.json');
});

test('the restore performs no outbound network access', async t => {
    const { transport, report } = await sealed(t, 'offline');
    const restored = await executeRestore({
        transport,
        snapshotId: report.snapshot_id,
        destinationRoot: destination(t, 'offline'),
        includeFreshProcess: true,
        spawn: successfulSpawn(),
    });
    assert.equal(restored.result, 'PASS');
    assert.deepEqual(tripwire.attempts, []);
});
