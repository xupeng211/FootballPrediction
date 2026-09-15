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
const { loadAcceptedManifest, verifySnapshot } = require('../../../../src/infrastructure/market_evidence/backup/snapshotVerifier');
const { buildCompletenessMarker, payloadObjectKey } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');
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

// A destination is free to not exist yet, so the refusal cannot depend on the
// destination's own real path -- there is none.  What it depends on is where
// the destination would land, which is the real location of its parent plus the
// final segment.  A symlinked ancestor is the case that separates the two: the
// path spells the governed area nowhere, and its parent is a real directory.
test('a restore destination reached through a symlinked ancestor is refused before anything is created', async t => {
    const { transport, report } = await sealed(t, 'productionlink');
    const production = path.join(temporary(t, 'stage-d-elsewhere-'), 'data', 'market_evidence', 'live');
    // The destination's parent is an ordinary directory *inside* the governed
    // area, not the link itself.  A check that stopped at "the parent must not
    // be a symbolic link" passes here, so this shape is the one that isolates
    // the question the refusal is supposed to answer: where does it land.
    fs.mkdirSync(path.join(production, 'nested'), { recursive: true });
    const link = path.join(temporary(t, 'stage-d-link-'), 'link');
    fs.symlinkSync(production, link);
    const destination = path.join(link, 'nested', 'restored');
    assert.equal(fs.lstatSync(path.dirname(destination)).isSymbolicLink(), false, 'the parent must be an ordinary directory for this test to assert what it claims');

    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: destination }),
        error => error instanceof SnapshotIntegrityError && /resolve into the governed production area/.test(error.message)
    );
    assert.equal(fs.existsSync(path.join(production, 'nested', 'restored')), false, 'nothing may be created inside the governed area');
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

// These two assert a corrupt generation cannot be restored, and they assert it
// through the canonical verifier's own failure code rather than the restore's
// wording.  The check moved: a restore used to read the artifacts and discover
// the problem itself, and now the generation is refused before the destination
// is even evaluated.  The property is the same and is checked earlier, so the
// assertion names the reason (`ARTIFACT_MISSING`, `ARTIFACT_HASH_MISMATCH`)
// instead of the layer that happened to notice it.
test('a restore of a generation whose artifact is missing fails closed', async t => {
    const { root, transport, report } = await sealed(t, 'gapped');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const victim = manifest.artifacts.find(artifact => artifact.logical_path === 'transactions/STORE.json');
    fs.rmSync(path.join(root, ...victim.object_key.split('/')));
    const target = destination(t, 'gapped');
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
        error => error instanceof SnapshotIntegrityError && /ARTIFACT_MISSING: transactions\/STORE\.json/.test(error.message)
    );
    assert.equal(fs.existsSync(target), false);
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
        error => error instanceof SnapshotIntegrityError && /ARTIFACT_HASH_MISMATCH: transactions\/STORE\.json/.test(error.message)
    );
    assert.equal(fs.existsSync(target), false);
});

// The restore's precondition is the canonical verification, not the completeness
// marker.
//
// `loadAcceptedManifest` answers "was this generation sealed?": the marker
// exists and is structurally valid, it names the manifest that exists, and the
// manifest is byte for byte the one the marker bound.  That is all it answers,
// and it is deliberately not the whole contract.  A generation can satisfy every
// one of those checks and still fail the canonical verifier -- and while the
// restore was admitted on the marker alone, such a generation restored in full:
// every object read, every hash checked against the manifest, the tree proved
// and the destination committed, because the restore path never asked the
// question that would have refused it.
//
// The two shapes below are the ones that separate the two entry points.  Each is
// accepted by the marker checks and refused by exactly one canonical check, and
// they are refused by *different* canonical checks, so a gate that passed for
// the wrong reason could not pass both.
const PRECONDITION_CASES = [
    {
        label: 'an object no manifest entry accounts for',
        code: 'UNEXPECTED_OBJECT',
        corrupt: async ({ transport, report }) => {
            await transport.putObjectCreateOnly({
                key: payloadObjectKey(report.snapshot_id, 'foreign/NOTE.bin'),
                bytes: Buffer.from('an object no manifest entry accounts for', 'utf8'),
            });
        },
    },
    {
        label: 'a completeness marker that disagrees with the manifest it binds',
        code: 'IDENTITY_MISMATCH',
        corrupt: async ({ root, report }) => {
            const markerPath = path.join(root, ...report.completeness_object_key.split('/'));
            const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
            // Rebuilt through the module's own builder, so the bytes stay
            // canonical and the marker still binds the manifest hash.  Only the
            // count drifts, which no marker check compares against the manifest.
            fs.writeFileSync(markerPath, buildCompletenessMarker({ ...marker, artifact_count: marker.artifact_count + 1 }).bytes);
        },
    },
];

for (const { label, code, corrupt } of PRECONDITION_CASES) {
    test(`a generation with ${label} cannot be restored`, async t => {
        const sealedGeneration = await sealed(t, code.toLowerCase());
        const { transport, report } = sealedGeneration;
        await corrupt(sealedGeneration);
        const target = destination(t, code.toLowerCase());

        // The generation is still sealed: the marker binds the manifest, so the
        // acceptance path admits it.  This is the anchor that makes the test
        // about the precondition rather than about a malformed generation.
        const accepted = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
        assert.equal(accepted.manifest.artifact_count, report.artifact_count);

        // The canonical verifier refuses it, for the reason this case is about.
        const verified = await verifySnapshot({ transport, snapshotId: report.snapshot_id });
        assert.equal(verified.result, 'FAIL');
        assert.deepEqual([...new Set(verified.failures.map(failure => failure.code))], [code]);

        // The restore refuses with the verifier's reason, verbatim.  Comparing
        // against the report's own text is what makes this about the canonical
        // verifier being invoked rather than about some restore-local re-check
        // that could drift from it.
        const reason = verified.failures.map(failure => `${failure.code}: ${failure.detail}`).join('; ');
        await assert.rejects(
            executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
            error => error instanceof SnapshotIntegrityError && error.message.includes(reason)
        );

        assert.equal(fs.existsSync(target), false, 'an unverified generation must not create a destination');
        assert.deepEqual(fs.readdirSync(path.dirname(target)), [], 'no staging root may be created beside the destination');
    });
}

test('a successful restore reports the verification it was admitted on', async t => {
    const { transport, report } = await sealed(t, 'admitted');
    const restored = await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: destination(t, 'admitted') });

    assert.equal(restored.result, 'PASS');
    assert.equal(restored.snapshot_verification.result, 'PASS');
    assert.equal(restored.snapshot_verification.snapshot_id, report.snapshot_id);
    assert.equal(restored.snapshot_verification.evidence.manifest_sha256, report.manifest_sha256);
    assert.deepEqual(restored.snapshot_verification.failures, []);
});

// A restore that fails must not have created anything.  Creating the
// destination first and filling it in meant that a generation which turned out
// to be missing an object, or carrying a hash the manifest does not bind, left
// the destination as a partial tree -- at a path that had not existed before --
// and because a restore refuses a destination that already exists, that tree
// could never be restored into again.  The tests above already assert that the
// restore is refused; what they never asserted is the state it left behind, and
// the retry is what makes that observable: a retry that reaches the real
// problem is only possible if nothing was left in the way.
for (const [label, sabotage] of [
    ['a missing object', ({ root, manifest }) => {
        fs.rmSync(path.join(root, ...manifest.artifacts[manifest.artifacts.length - 1].object_key.split('/')));
    }],
    ['an object whose content the manifest does not bind', ({ root, manifest }) => {
        const victim = path.join(root, ...manifest.artifacts[manifest.artifacts.length - 1].object_key.split('/'));
        const bytes = Buffer.from(fs.readFileSync(victim));
        bytes[1] ^= 0x01;
        fs.writeFileSync(victim, bytes);
    }],
]) {
    test(`a restore that fails on ${label} leaves the destination exactly as it was`, async t => {
        const { root, transport, report } = await sealed(t, 'abandon');
        const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
        sabotage({ root, manifest });
        const target = destination(t, 'abandon');

        await assert.rejects(executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }));
        assert.equal(fs.existsSync(target), false, `a failed restore must leave no destination behind: ${target}`);
        assert.deepEqual(fs.readdirSync(path.dirname(target)), [], 'and no staging tree either');

        await assert.rejects(
            executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target }),
            error => !/already exists/.test(error.message),
            'the retry must reach the real problem, which it only can if nothing was left in the way'
        );
        assert.equal(fs.existsSync(target), false);
        assert.deepEqual(fs.readdirSync(path.dirname(target)), []);
    });
}

// The third failure mode is the one that happens after every artifact has been
// written and every hash checked: the proof itself comes back FAIL.  It is the
// case a fix that only verified the artifacts up front would still get wrong,
// because by the time the proof runs the tree already exists.
test('a restore whose proof fails leaves the destination exactly as it was', async t => {
    const { transport, report } = await sealed(t, 'prooffail');
    const target = destination(t, 'prooffail');
    const refusing = () => ({ status: 0, stdout: `${JSON.stringify({ ok: false, error: 'the restored root could not be loaded' })}\n` });

    let caught = null;
    try {
        await executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: target, includeFreshProcess: true, spawn: refusing });
    } catch (error) {
        caught = error;
    }
    assert.ok(caught instanceof RestoreProofError, `expected a proof failure, received ${caught && caught.name}: ${caught && caught.message}`);
    assert.ok(caught.report.failures.some(failure => /could not be loaded by a fresh process/.test(failure)), 'the report must carry the proof failure');
    assert.equal(fs.existsSync(target), false, 'a destination whose proof failed must not exist');
    assert.deepEqual(fs.readdirSync(path.dirname(target)), [], 'the staged tree the proof ran against must not be left beside it');
});

// The gap between "the destination did not exist" and "the destination was
// committed" is where another process can act, so the freshness check cannot be
// what decides it.  The commit itself has to be create-only, or a destination
// that appeared in the meantime is silently adopted: POSIX rename replaces an
// existing *empty* directory, so a plain rename would put the restored tree
// exactly where a restore is supposed to refuse to write.
test('a destination created by another process mid-restore is refused, not replaced', async t => {
    const { transport, report } = await sealed(t, 'race');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'race');
    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    let placed = null;

    // The competitor acts once the last artifact has been read: after the
    // freshness check, before the commit -- the whole window the finding is
    // about, and the one place a plain rename would silently adopt the
    // competitor's directory because POSIX rename replaces an empty one.
    const competing = {
        ...transport,
        async getObject(args) {
            const bytes = await transport.getObject(args);
            if (args.key === lastArtifact && placed === null) {
                fs.mkdirSync(target, { mode: 0o755 });
                placed = 'the destination existed before the commit';
            }
            return bytes;
        },
    };

    await assert.rejects(executeRestore({ transport: competing, snapshotId: report.snapshot_id, destinationRoot: target }));

    assert.equal(placed, 'the destination existed before the commit', 'the competitor must actually have run before the commit');
    assert.equal(fs.existsSync(target), true, 'the competing destination must still be there');
    assert.deepEqual(fs.readdirSync(target), [], 'it must be untouched -- a restore never fills a destination it did not create');
});

// FU-3: the staging tree a failed restore used to leave behind.
//
// The staging root is the one directory a restore creates that nobody asked
// for, so it is the one directory a restore may remove, and the whole safety of
// removing it rests on being able to say *which* directory that is.  It is
// minted here -- a random suffix drawn into a local variable, never derived from
// anything the caller supplied -- which is what makes "the staging root created
// by this exact invocation" a decidable question rather than a pattern match.
//
// These tests are the negative ones: what the cleanup must not reach, and what
// it must not hide.  A test that only showed the staging root disappearing would
// pass just as well for a cleanup that removed the whole parent.
//
// They also have to fail *after* materialization has begun.  The restore reads
// every artifact twice -- once while the canonical verifier admits the
// generation, once while it is written -- and the verifier reads through the
// same transport, so corrupting the store refuses the generation during
// admission, before a staging root exists.  The failure these tests are about
// therefore has to land on the second read, and the staging root's own
// existence is the signal for it: the root is created after admission, so its
// presence means the restore is past the gate and into the window that used to
// leave a tree behind.

// Absolute paths, deliberately: a bare name is resolved against the process
// working directory, so a test that swapped "the staging root" by name would
// leave the real one alone and act on the repository instead.
function stagingRootsBeside(target) {
    const parent = path.dirname(target);
    const prefix = `.${path.basename(target)}.restore-staging-`;
    return fs.readdirSync(parent)
        .filter(name => name.startsWith(prefix))
        .map(name => path.join(parent, name))
        .filter(absolute => {
            const stat = fs.lstatSync(absolute);
            return stat.isDirectory() && !stat.isSymbolicLink();
        });
}

function duringMaterialization(transport, target, key, act) {
    return {
        ...transport,
        async getObject(args) {
            const bytes = await transport.getObject(args);
            if (args.key === key && stagingRootsBeside(target).length === 1) act(bytes);
            return bytes;
        },
    };
}

test('a failed restore removes the staging root it created and nothing else', async t => {
    const { transport, report } = await sealed(t, 'cleanup');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'cleanup');
    const parent = path.dirname(target);

    // A bystander, and a look-alike named the way this invocation names its own
    // staging root.  A cleanup that matched the pattern instead of holding the
    // one path it minted would take the look-alike with it; one that reached for
    // the parent would take both and then the directory itself.
    const lookAlike = path.join(parent, `.${path.basename(target)}.restore-staging-0000000000000000`);
    fs.writeFileSync(lookAlike, 'not the staging tree of this invocation');
    fs.writeFileSync(path.join(parent, 'bystander.txt'), 'not a staging root at all');
    const before = fs.readdirSync(parent).sort();

    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const corrupting = duringMaterialization(transport, target, lastArtifact, bytes => { bytes[1] ^= 0x01; });
    await assert.rejects(executeRestore({ transport: corrupting, snapshotId: report.snapshot_id, destinationRoot: target }));

    assert.equal(fs.existsSync(target), false, 'a failed restore must leave no destination');
    assert.deepEqual(fs.readdirSync(parent).sort(), before, 'the parent must hold exactly what it held before the restore');
    assert.equal(fs.readFileSync(lookAlike, 'utf8'), 'not the staging tree of this invocation');
    assert.deepEqual(stagingRootsBeside(target), [], 'no staging root of this invocation may survive it');
});

// The reach of the cleanup is bounded by construction rather than by a denylist:
// it starts at a path this invocation minted and can only name that path joined
// with a name `readdirSync` returned.  A symbolic link inside the staging tree
// is the case that separates "bounded" from "tidy": descending through it would
// make the reach a property of whatever the link points at, and the restored
// tree refuses symbolic-link parents when it is written, so a link in there is
// foreign content by definition.
test('staging cleanup unlinks a symbolic link rather than walking into it', async t => {
    const { transport, report } = await sealed(t, 'nolinkwalk');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'nolinkwalk');
    const parent = path.dirname(target);

    const elsewhere = temporary(t, 'stage-d-outside-');
    fs.writeFileSync(path.join(elsewhere, 'IRREPLACEABLE.bin'), 'outside the staging root');

    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const planting = duringMaterialization(transport, target, lastArtifact, bytes => {
        const [staging] = stagingRootsBeside(target);
        fs.symlinkSync(elsewhere, path.join(staging, 'escaped'));
        bytes[1] ^= 0x01;
    });

    await assert.rejects(executeRestore({ transport: planting, snapshotId: report.snapshot_id, destinationRoot: target }));

    assert.equal(fs.readFileSync(path.join(elsewhere, 'IRREPLACEABLE.bin'), 'utf8'), 'outside the staging root', 'the cleanup must not have reached through the link');
    assert.deepEqual(fs.readdirSync(elsewhere), ['IRREPLACEABLE.bin'], 'nothing may be added or removed outside the staging root either');
    assert.deepEqual(fs.readdirSync(parent), [], 'the staging root must be gone even though a link was in it');
    assert.equal(fs.existsSync(target), false);
});

// The same invariant one level down, which is where it is hardest to hold.  The
// link above sits directly in the directory the walk minted; this one sits
// inside a directory the walk has to *enter* to reach it, so the refusal has to
// survive the step that holds one directory open while it enumerates another.
// A walk that guarded only its first level would pass the test above and delete
// the file below.
//
// The target is a directory with a file in it rather than a file, because
// entering is the failure being tested: unlinking a link to a file and
// unlinking a link to a directory are the same instruction, and only the second
// can be got wrong by descending.
test('staging cleanup unlinks a link it meets inside the tree rather than walking into it', async t => {
    const { transport, report } = await sealed(t, 'nestednolinkwalk');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'nestednolinkwalk');
    const parent = path.dirname(target);

    const elsewhere = temporary(t, 'stage-d-outside-');
    fs.mkdirSync(path.join(elsewhere, 'inner'), { mode: 0o700 });
    fs.writeFileSync(path.join(elsewhere, 'inner', 'IRREPLACEABLE.bin'), 'outside the staging root');

    // A directory the restore really creates, taken from the manifest rather
    // than guessed: a link planted under a path the tree does not have would
    // give the cleanup nothing to descend through and would prove nothing.
    const nested = path.dirname(manifest.artifacts[0].logical_path);
    assert.notEqual(nested, '.', 'the first artifact must live below the staging root, or there is no level to descend');

    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const planting = duringMaterialization(transport, target, lastArtifact, bytes => {
        const [staging] = stagingRootsBeside(target);
        const inside = path.join(staging, nested);
        assert.equal(fs.existsSync(inside), true, 'the level the link is planted in must exist, or the planting fails rather than the walk');
        fs.symlinkSync(elsewhere, path.join(inside, 'escaped'));
        bytes[1] ^= 0x01;
    });

    await assert.rejects(executeRestore({ transport: planting, snapshotId: report.snapshot_id, destinationRoot: target }));

    assert.equal(fs.readFileSync(path.join(elsewhere, 'inner', 'IRREPLACEABLE.bin'), 'utf8'), 'outside the staging root', 'the cleanup must not have reached through a link it met below the root');
    assert.deepEqual(fs.readdirSync(path.join(elsewhere, 'inner')), ['IRREPLACEABLE.bin'], 'nothing may be added or removed outside the staging root either');
    assert.deepEqual(fs.readdirSync(elsewhere), ['inner'], 'the link target must be untouched');
    assert.deepEqual(stagingRootsBeside(target), [], 'the staging root must be gone even though a link was nested inside it');
    assert.deepEqual(fs.readdirSync(parent), [], 'and nothing else of this invocation may survive beside it');
    assert.equal(fs.existsSync(target), false);
});

// A cleanup failure is recorded on the error that caused it, never thrown in its
// place.  The restore already failed for a reason the operator needs; replacing
// that reason with "the tidy-up failed as well" would hide the one that matters,
// and the failure being cleaned up for is exactly the failure most likely to
// leave a tree behind.  The staging root here is not a plain directory, which is
// a refusal that holds regardless of who is running -- a permission-based
// sabotage would not, since uid 0 can remove entries from a directory it cannot write.
test('a cleanup that cannot finish is recorded on the failure that caused it, never in its place', async t => {
    const { transport, report } = await sealed(t, 'cleanupfail');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'cleanupfail');

    const elsewhere = temporary(t, 'stage-d-outside-');
    fs.writeFileSync(path.join(elsewhere, 'IRREPLACEABLE.bin'), 'outside the staging root');
    let swapped = null;

    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const swapping = duringMaterialization(transport, target, lastArtifact, bytes => {
        const [staging] = stagingRootsBeside(target);
        fs.rmSync(staging, { recursive: true, force: true });
        fs.symlinkSync(elsewhere, staging);
        swapped = staging;
        bytes[1] ^= 0x01;
    });

    let caught = null;
    try {
        await executeRestore({ transport: swapping, snapshotId: report.snapshot_id, destinationRoot: target });
    } catch (error) {
        caught = error;
    }

    assert.ok(swapped !== null, 'the staging root must have been swapped for a link before the restore failed');
    assert.ok(caught instanceof SnapshotIntegrityError, `expected the restore's own failure, received ${caught && caught.name}: ${caught && caught.message}`);
    assert.match(caught.message, /content the manifest does not bind/, 'the reason the restore failed must survive the cleanup');
    assert.match(caught.message, /could not be removed/, 'the cleanup failure must be recorded');
    assert.ok(caught.message.includes(swapped), 'the note must name the staging root it could not remove');
    assert.equal(fs.readFileSync(path.join(elsewhere, 'IRREPLACEABLE.bin'), 'utf8'), 'outside the staging root', 'a refused cleanup must not have gone looking for something to remove');
    assert.deepEqual(fs.readdirSync(elsewhere), ['IRREPLACEABLE.bin']);
    assert.equal(fs.existsSync(target), false, 'a failed restore must leave no destination');
    assert.equal(fs.lstatSync(swapped).isSymbolicLink(), true, 'the refusal must be the swap, not a cleanup that succeeded anyway');
});

// The same swap with the one thing that makes it invisible to every check that
// compares a directory to itself: the replacement is an ordinary directory, so
// it is a plain directory before the open, it is a plain directory after it, and
// the `lstat` and the `open` agree with each other about it.  A link is caught
// because it is not a directory; this is caught only by knowing which directory
// this restore actually made.
//
// The replacement holds a file that belongs to someone else and nothing of this
// invocation's, so the cleanup must refuse it whole: not empty it, not remove
// it, and not present the refusal as the reason the restore failed.  A cleanup
// that matched the staging name instead of the staging directory passes every
// assertion about the failure and loses the file.
test('staging cleanup refuses an ordinary directory that merely has the staging name', async t => {
    const { transport, report } = await sealed(t, 'swappedroot');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'swappedroot');
    const parent = path.dirname(target);

    let swapped = null;
    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const swapping = duringMaterialization(transport, target, lastArtifact, bytes => {
        const [staging] = stagingRootsBeside(target);
        fs.rmSync(staging, { recursive: true, force: true });
        fs.mkdirSync(staging, { mode: DIRECTORY_MODE });
        fs.writeFileSync(path.join(staging, 'IRREPLACEABLE.bin'), 'not the staging tree of this invocation');
        swapped = staging;
        bytes[1] ^= 0x01;
    });

    let caught = null;
    try {
        await executeRestore({ transport: swapping, snapshotId: report.snapshot_id, destinationRoot: target });
    } catch (error) {
        caught = error;
    }

    assert.ok(swapped !== null, 'the staging root must have been swapped for another directory before the restore failed');
    assert.ok(caught instanceof SnapshotIntegrityError, `expected the restore's own failure, received ${caught && caught.name}: ${caught && caught.message}`);
    assert.match(caught.message, /content the manifest does not bind/, 'the reason the restore failed must survive the cleanup');
    assert.match(caught.message, /could not be removed/, 'the cleanup failure must be recorded');
    assert.ok(caught.message.includes(swapped), 'the note must name the staging root it could not remove');
    assert.equal(fs.readFileSync(path.join(swapped, 'IRREPLACEABLE.bin'), 'utf8'), 'not the staging tree of this invocation', 'a refused cleanup must not have emptied a directory this restore did not create');
    assert.deepEqual(fs.readdirSync(swapped), ['IRREPLACEABLE.bin'], 'and must not have added or removed anything in it');
    assert.equal(fs.lstatSync(swapped).isDirectory(), true, 'the refusal must be the identity, not a cleanup that succeeded anyway');
    assert.deepEqual(fs.readdirSync(parent), [path.basename(swapped)], 'nothing else of this invocation may survive beside the replacement');
    assert.equal(fs.existsSync(target), false, 'a failed restore must leave no destination');
});

// The identity binding, separated from the walk it guards.  An *empty*
// replacement is the case a walk alone cannot refuse: there is nothing in it to
// notice, `rmdir` has no non-empty directory to refuse, and the walk empties a
// directory that no longer exists under any name while the removal takes the one
// that does.  The descriptor is then the only thing that tells the two apart --
// and it tells them apart without comparing anything, because a descriptor is
// the directory rather than a description of it.
//
// This test fails with the descriptor walk kept and the identity check dropped,
// which is what makes it a test of the binding rather than of the walk.
test('staging cleanup leaves an empty directory that merely has the staging name', async t => {
    const { transport, report } = await sealed(t, 'swappedemptyroot');
    const { manifest } = await loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    const target = destination(t, 'swappedemptyroot');
    const parent = path.dirname(target);

    let swapped = null;
    const lastArtifact = manifest.artifacts[manifest.artifacts.length - 1].object_key;
    const swapping = duringMaterialization(transport, target, lastArtifact, bytes => {
        const [staging] = stagingRootsBeside(target);
        fs.rmSync(staging, { recursive: true, force: true });
        fs.mkdirSync(staging, { mode: DIRECTORY_MODE });
        swapped = staging;
        bytes[1] ^= 0x01;
    });

    let caught = null;
    try {
        await executeRestore({ transport: swapping, snapshotId: report.snapshot_id, destinationRoot: target });
    } catch (error) {
        caught = error;
    }

    assert.ok(swapped !== null, 'the staging root must have been swapped for another directory before the restore failed');
    assert.ok(caught instanceof SnapshotIntegrityError, `expected the restore's own failure, received ${caught && caught.name}: ${caught && caught.message}`);
    assert.match(caught.message, /content the manifest does not bind/, 'the reason the restore failed must survive the cleanup');
    assert.match(caught.message, /could not be removed/, 'the cleanup failure must be recorded');
    assert.ok(caught.message.includes(swapped), 'the note must name the staging root it could not remove');
    assert.deepEqual(fs.readdirSync(swapped), [], 'the cleanup must not have put anything in a directory this restore did not create');
    assert.equal(fs.lstatSync(swapped).isDirectory(), true, 'and must not have removed it either');
    assert.deepEqual(fs.readdirSync(parent), [path.basename(swapped)], 'nothing else of this invocation may survive beside the replacement');
    assert.equal(fs.existsSync(target), false, 'a failed restore must leave no destination');
});

// Isolation is a property of where the destination *is*, not of how it is
// spelled.  `path.resolve` never asks the filesystem, so a destination reached
// through a symlinked ancestor names nothing while every write through it lands
// inside the source root; the immediate parent's own lstat cannot see it either,
// because the link sits higher up and the directory it reaches is ordinary.
test('a destination reached through an ancestor symlink into the source root is refused', t => {
    const sourceRoot = temporary(t, 'stage-d-source-');
    fs.mkdirSync(path.join(sourceRoot, 'nested'), { mode: 0o700 });
    const scratch = temporary(t, 'stage-d-scratch-');
    fs.mkdirSync(path.join(scratch, 'nested'), { mode: 0o700 });
    const link = path.join(scratch, 'link');
    fs.symlinkSync(sourceRoot, link);

    const target = path.join(link, 'nested', 'restored');
    assert.equal(fs.existsSync(target), false, 'the destination itself must not exist yet');
    assert.equal(fs.realpathSync(path.dirname(target)), path.join(sourceRoot, 'nested'), 'the link must be the only thing making this destination what it is');

    assert.throws(
        () => assertFreshDestination(target, { sourceRoots: [sourceRoot] }),
        error => error instanceof SnapshotIntegrityError && /must not be inside the source root/.test(error.message)
    );
    // The same destination without the link is accepted, so the refusal is the
    // link and not an over-eager denylist.
    assert.equal(
        assertFreshDestination(path.join(scratch, 'nested', 'restored'), { sourceRoots: [sourceRoot] }),
        path.join(scratch, 'nested', 'restored')
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
    assert.equal(capture.args[1].includes(fixture().authorityRoot), false, 'the probe is never pointed at the source');
    // The tree is proven where it was staged and only then moved into place, so
    // the probe names the staging path rather than the destination.  The bytes
    // it loaded are the ones that became the destination, so the property that
    // matters is that it was pointed at that tree and not at the source -- and
    // that the report names where the tree actually ended up rather than the
    // staging path the proof ran against.
    const probed = /storeRoot:\s*"([^"]+)"/.exec(capture.args[1]);
    assert.ok(probed, 'the probe must name the authority root it was pointed at');
    assert.equal(path.dirname(path.dirname(probed[1])), path.dirname(target), 'the probe must be pointed at the tree staged beside the destination');
    assert.equal(restored.destination_root, target);
    assert.equal(restored.authority_root, path.join(target, 'transactions'), 'the report must name the final destination, not the staging path');
    assert.equal(restored.proof.head_transaction_id, report.source_head_transaction_id);
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
