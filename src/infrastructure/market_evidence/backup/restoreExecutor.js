'use strict';

// Restores one accepted generation into an isolated root, and proves the
// restored root is a loadable authority.
//
// A restore is only evidence if it happens somewhere the source cannot reach.
// Restoring beside the source would prove nothing, and restoring onto the
// source would be a catastrophe, so the destination must be a path that does
// not exist yet, outside the governed production area, outside the source
// roots, and free of symbolic links.  The executor creates it and owns it.
//
// The proof is deliberately performed by the existing canonical readers
// (openMarketEvidenceAuthoritySnapshot and readRequestLedger) pointed at the
// restored root with no other input.  A bespoke checker would prove only that
// the checker and the writer agree; the canonical readers prove that the
// restored bytes are an authority the runtime would accept.
//
// Nothing here reads, writes or falls back to a production path.  If a
// required governed artifact cannot be restored from the generation, the
// restore fails; it never substitutes a file from somewhere else.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const { canonicalJson } = require('../transactionContract');
const { openMarketEvidenceAuthoritySnapshot } = require('../authorityReader');
const { readRequestLedger } = require('../stageDOperations');
const { ALLOCATION_FILE } = require('./snapshotInputs');
const { assertTransportContract, SnapshotIntegrityError } = require('./transport');
const { assertNotGovernedProductionPath, isGovernedProductionPath, realLocationOf } = require('./localTransport');
const { assertGenerationId, sha256Hex } = require('./snapshotManifest');
const { assertSnapshotVerification, loadAcceptedManifest, verifySnapshot } = require('./snapshotVerifier');

const RESTORE_VERSION = 'stage-d-independent-backup-restore/v1';

const DIRECTORY_MODE = 0o700;

// Restored modes mirror the production filesystem permission contract.  The
// governed files that carry authority are readable and not writable, because
// the canonical readers and the store contract both refuse mutable evidence.
const FILE_MODES = Object.freeze({
    transaction_package: 0o400,
    store: 0o444,
    allocation_authority: 0o444,
    request_accounting_epoch: 0o400,
    request_accounting_entry: 0o400,
    run_state: 0o444,
    quota_config: 0o444,
});

const READER_PATHS = Object.freeze({
    authority_reader: path.join(__dirname, '..', 'authorityReader.js'),
    stage_d_operations: path.join(__dirname, '..', 'stageDOperations.js'),
});

class RestoreProofError extends Error {
    constructor(message, report) {
        super(message);
        this.name = 'RestoreProofError';
        this.code = 'RESTORE_PROOF_FAILED';
        this.report = report;
    }
}

function pathContains(outer, inner) {
    const relative = path.relative(outer, inner);
    return Boolean(relative) && !relative.startsWith('..') && !path.isAbsolute(relative);
}

// Isolated means isolated from the source, not merely outside the production
// marker.  A destination nested inside the source root, or a source root nested
// inside the destination, would make the "restore" a copy of itself.
//
// The comparison has to be physical as well as lexical.  `path.resolve` never
// asks the filesystem, so a destination reached through a symlinked ancestor
// names none of the source roots while every write through it lands inside one:
// `<scratch>/link/restored`, where `link` points at the source root, is
// textually unrelated to that root and physically inside it.  The immediate
// parent's own `lstat` cannot see it either, because the link sits higher up
// and the parent it reaches is an ordinary directory.  Both views of both sides
// are therefore compared, and an ancestor link that makes the destination
// disjoint in name only is refused.
//
// `realLocationOf` resolves the longest *existing* prefix, so a destination
// that does not exist yet still has a physical location: the one it will have
// once those directories are created.  That is exactly the question worth
// asking, because it is asked before anything is created.
function physicalAncestryOf(target) {
    const real = realLocationOf(target);
    return typeof real === 'string' ? [target, real] : [target];
}

function assertDestinationDisjointFromSources(resolved, sourceRoots) {
    const destinations = physicalAncestryOf(resolved);
    for (const sourceRoot of sourceRoots) {
        if (typeof sourceRoot !== 'string' || !sourceRoot.trim()) continue;
        for (const source of physicalAncestryOf(path.resolve(sourceRoot))) {
            for (const destination of destinations) {
                if (destination === source) throw new SnapshotIntegrityError(`restore destination must not be the source root: ${destination}`);
                if (pathContains(source, destination)) throw new SnapshotIntegrityError(`restore destination must not be inside the source root: ${destination}`);
                if (pathContains(destination, source)) throw new SnapshotIntegrityError(`restore destination must not contain the source root: ${destination}`);
            }
        }
    }
}

function assertFreshDestination(destinationRoot, { sourceRoots = [] } = {}) {
    if (typeof destinationRoot !== 'string' || !destinationRoot.trim()) throw new SnapshotIntegrityError('destinationRoot must be supplied explicitly; there is no default restore location');
    const resolved = assertNotGovernedProductionPath(destinationRoot, 'restore destination root');
    const parent = path.dirname(resolved);
    const parentStat = fs.lstatSync(parent);
    if (parentStat.isSymbolicLink() || !parentStat.isDirectory()) throw new SnapshotIntegrityError(`restore destination parent must be a plain directory: ${parent}`);
    if (isGovernedProductionPath(fs.realpathSync(parent))) throw new SnapshotIntegrityError(`restore destination must not resolve into the governed production area: ${resolved}`);
    if (fs.existsSync(resolved)) throw new SnapshotIntegrityError(`restore destination already exists; a restore never overwrites: ${resolved}`);
    assertDestinationDisjointFromSources(resolved, sourceRoots);
    return resolved;
}

function createDirectory(root, absolute) {
    const relative = path.relative(root, absolute);
    if (relative === '') return;
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`restored path escapes the destination root: ${absolute}`);
    let current = root;
    for (const segment of relative.split(path.sep)) {
        current = path.join(current, segment);
        try {
            const stat = fs.lstatSync(current);
            if (stat.isSymbolicLink() || !stat.isDirectory()) throw new SnapshotIntegrityError(`restored path parent is not a plain directory: ${current}`);
        } catch (error) {
            if (error.code !== 'ENOENT') throw error;
            fs.mkdirSync(current, { mode: DIRECTORY_MODE });
            fs.chmodSync(current, DIRECTORY_MODE);
        }
    }
}

function writeRestoredFile(root, relativePath, bytes, mode) {
    const absolute = path.resolve(root, relativePath);
    const relative = path.relative(root, absolute);
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`restored path escapes the destination root: ${relativePath}`);
    createDirectory(root, path.dirname(absolute));
    let fd;
    try {
        fd = fs.openSync(absolute, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0), mode);
    } catch (error) {
        if (error.code === 'EEXIST') throw new SnapshotIntegrityError(`a restore never overwrites: ${absolute}`);
        throw error;
    }
    try {
        fs.writeFileSync(fd, bytes);
        fs.fsyncSync(fd);
    } finally {
        fs.closeSync(fd);
    }
    // umask does not apply to an explicit chmod, so the restored mode is exactly
    // the mode the permission contract names rather than the process default.
    fs.chmodSync(absolute, mode);
    return absolute;
}

function readRestoredFile(absolute) {
    const stat = fs.lstatSync(absolute);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new SnapshotIntegrityError(`restored path is not a plain file: ${absolute}`);
    return fs.readFileSync(absolute);
}

function restoredLayout(destinationRoot, manifest) {
    const authorityRoot = path.join(destinationRoot, 'transactions');
    const ledgerRoot = path.join(destinationRoot, 'request-accounting');
    const allocation = manifest.artifacts.find(artifact => artifact.category === 'allocation_authority');
    const quota = manifest.artifacts.find(artifact => artifact.category === 'quota_config');
    if (!allocation) throw new SnapshotIntegrityError('the generation carries no allocation authority artifact and cannot be restored');
    if (!quota) throw new SnapshotIntegrityError('the generation carries no quota configuration artifact and cannot be restored');
    return Object.freeze({
        authority_root: authorityRoot,
        ledger_root: ledgerRoot,
        allocation_artifact_path: path.join(destinationRoot, allocation.logical_path),
        quota_config_path: path.join(destinationRoot, quota.logical_path),
        allocation_logical_path: allocation.logical_path,
        quota_logical_path: quota.logical_path,
        store_path: path.join(authorityRoot, 'STORE.json'),
        expected_allocation_basename: ALLOCATION_FILE,
    });
}

// A fresh process is the strongest available statement that the restored root
// is self-sufficient: the child imports the canonical readers, is given the
// restored paths and nothing else, and inherits no environment at all, so a
// result cannot come from an ambient credential, an ambient configuration or a
// production path the parent happened to have in scope.
function buildFreshProcessProbe({ authority_root: authorityRoot, allocation_artifact_path: allocationArtifactPath, ledger_root: ledgerRoot }) {
    if (typeof authorityRoot !== 'string' || typeof allocationArtifactPath !== 'string' || typeof ledgerRoot !== 'string') {
        throw new SnapshotIntegrityError('the fresh process probe requires explicit restored authority, allocation and ledger paths');
    }
    return `
const run = () => {
    const { openMarketEvidenceAuthoritySnapshot } = require(${JSON.stringify(READER_PATHS.authority_reader)});
    const { readRequestLedger } = require(${JSON.stringify(READER_PATHS.stage_d_operations)});
    const authority = openMarketEvidenceAuthoritySnapshot({ storeRoot: ${JSON.stringify(authorityRoot)}, allocationArtifactPath: ${JSON.stringify(allocationArtifactPath)} });
    const ledger = readRequestLedger({ ledgerRoot: ${JSON.stringify(ledgerRoot)} });
    return {
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
    };
};
try {
    process.stdout.write(JSON.stringify({ ok: true, identity: run() }) + '\\n');
} catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error && error.message ? error.message : error) }) + '\\n');
}
`;
}

function proveColdLoadInFreshProcess(layout, { spawn = spawnSync, execPath = process.execPath } = {}) {
    const result = spawn(execPath, ['-e', buildFreshProcessProbe(layout)], { cwd: '/', encoding: 'utf8', env: { PATH: process.env.PATH || '' }, timeout: 120000 });
    const stdout = typeof result.stdout === 'string' ? result.stdout.trim() : '';
    if (result.error) return Object.freeze({ ok: false, error: `fresh process could not be started: ${result.error.message}` });
    if (!stdout) return Object.freeze({ ok: false, error: `fresh process produced no result (status ${result.status})` });
    let parsed;
    try {
        parsed = JSON.parse(stdout);
    } catch (error) {
        return Object.freeze({ ok: false, error: `fresh process output was not valid JSON: ${stdout.slice(0, 200)}` });
    }
    if (parsed.ok !== true) return Object.freeze({ ok: false, error: parsed.error });
    return Object.freeze({ ok: true, identity: Object.freeze(parsed.identity) });
}

const IDENTITY_FIELDS = Object.freeze([
    'head_transaction_id',
    'head_transaction_content_hash',
    'head_sequence',
    'state_hash',
    'observation_count',
    'decision_count',
    'registry_state_count',
    'capture_binding_count',
]);

function readRestoredIdentity(layout) {
    const authority = openMarketEvidenceAuthoritySnapshot({
        storeRoot: layout.authority_root,
        allocationArtifactPath: layout.allocation_artifact_path,
    });
    const ledger = readRequestLedger({ ledgerRoot: layout.ledger_root });
    return {
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
        store_sha256: sha256Hex(readRestoredFile(layout.store_path)),
        allocation_authority_sha256: sha256Hex(readRestoredFile(layout.allocation_artifact_path)),
        quota_config_sha256: sha256Hex(readRestoredFile(layout.quota_config_path)),
    };
}

function compareIdentity(observed, manifest, failures, label) {
    for (const field of IDENTITY_FIELDS) {
        if (canonicalJson(observed[field]) !== canonicalJson(manifest.source[field])) failures.push(`${label} ${field} is ${canonicalJson(observed[field])} but the manifest records ${canonicalJson(manifest.source[field])}`);
    }
    if (observed.epoch_id !== manifest.request_accounting.epoch_id) failures.push(`${label} request accounting epoch id does not match the manifest`);
    if (observed.entry_count !== manifest.request_accounting.entry_count) failures.push(`${label} request accounting entry count does not match the manifest`);
    if (observed.last_entry_hash !== manifest.request_accounting.last_entry_hash) failures.push(`${label} request accounting terminal hash does not match the manifest`);
}

function compareGovernedHashes(observed, manifest, failures) {
    if (observed.store_sha256 !== manifest.store_sha256) failures.push('the restored STORE.json does not match the hash bound by the manifest');
    if (observed.allocation_authority_sha256 !== manifest.allocation_authority_sha256) failures.push('the restored allocation authority does not match the hash bound by the manifest');
    if (observed.quota_config_sha256 !== manifest.quota_config.sha256) failures.push('the restored quota configuration does not match the hash bound by the manifest');
}

function compareRestoredFiles(resolvedRoot, manifest, failures) {
    const restoredFiles = [];
    for (const artifact of manifest.artifacts) {
        const absolute = path.join(resolvedRoot, artifact.logical_path);
        const stat = fs.lstatSync(absolute);
        const bytes = readRestoredFile(absolute);
        if (bytes.length !== artifact.size) failures.push(`restored ${artifact.logical_path} is ${bytes.length} bytes but the manifest declares ${artifact.size}`);
        if (sha256Hex(bytes) !== artifact.sha256) failures.push(`restored ${artifact.logical_path} does not match the hash bound by the manifest`);
        restoredFiles.push(Object.freeze({ logical_path: artifact.logical_path, category: artifact.category, size: bytes.length, mode: stat.mode & 0o7777 }));
    }
    return restoredFiles;
}

// Reads the restored root back through the canonical readers and compares
// everything against the manifest.  Performs no writes.
async function proveRestoredRoot({ destinationRoot, manifest, layout = null, includeFreshProcess = false, spawn = spawnSync, execPath = process.execPath } = {}) {
    const resolvedRoot = path.resolve(assertNotGovernedProductionPath(destinationRoot, 'restore destination root'));
    const resolvedLayout = layout || restoredLayout(resolvedRoot, manifest);
    const failures = [];

    const proof = readRestoredIdentity(resolvedLayout);
    compareIdentity(proof, manifest, failures, 'restored authority');
    compareGovernedHashes(proof, manifest, failures);
    const restoredFiles = compareRestoredFiles(resolvedRoot, manifest, failures);

    const freshProcess = includeFreshProcess ? proveColdLoadInFreshProcess(resolvedLayout, { spawn, execPath }) : null;
    if (freshProcess && freshProcess.ok !== true) failures.push(`the restored root could not be loaded by a fresh process: ${freshProcess.error}`);
    if (freshProcess && freshProcess.ok === true) compareIdentity(freshProcess.identity, manifest, failures, 'fresh process authority');

    return Object.freeze({
        restore_version: RESTORE_VERSION,
        result: failures.length === 0 ? 'PASS' : 'FAIL',
        destination_root: resolvedRoot,
        authority_root: resolvedLayout.authority_root,
        ledger_root: resolvedLayout.ledger_root,
        allocation_artifact_path: resolvedLayout.allocation_artifact_path,
        quota_config_path: resolvedLayout.quota_config_path,
        restored_file_count: restoredFiles.length,
        restored_total_bytes: restoredFiles.reduce((sum, file) => sum + file.size, 0),
        restored_files: Object.freeze(restoredFiles),
        proof: Object.freeze(proof),
        fresh_process_proof: freshProcess,
        production_fallback_used: false,
        production_paths_read: Object.freeze([]),
        failures: Object.freeze(failures),
    });
}

// The tree is built somewhere else and moved into place only once it has been
// proven, because the destination must not exist at all unless the restore
// succeeded.  Creating it first and filling it in is what left a destination
// that had not existed become a partial tree on any later failure -- a missing
// object, a hash the manifest does not bind, or a proof that came back FAIL --
// and because a restore refuses a destination that already exists, that partial
// tree could never be restored into again.  It was also the one case where a
// failed restore did not leave the destination as it was found.
//
// Nothing here removes anything, so a failure before the commit leaves the
// staging directory behind as visible evidence of the attempt while the
// destination itself stays exactly as it was.
function createStagingRoot(destination) {
    const staging = path.join(path.dirname(destination), `.${path.basename(destination)}.restore-staging-${crypto.randomBytes(8).toString('hex')}`);
    if (isGovernedProductionPath(staging)) throw new SnapshotIntegrityError(`restore staging root must never be the governed production area: ${staging}`);
    fs.mkdirSync(staging, { mode: DIRECTORY_MODE });
    fs.chmodSync(staging, DIRECTORY_MODE);
    return staging;
}

// The commit is the point at which the destination starts to exist, so it is
// the point at which "a restore never overwrites" has to be decided, and it has
// to be decided by the filesystem rather than by a prior existence check.
//
// `mkdirSync` is that decision: it creates or fails with EEXIST, and it can
// never replace.  `fs.renameSync` cannot be used here even though it is atomic,
// because POSIX rename onto an existing *empty* directory succeeds -- a
// destination another process created after the freshness check would be
// silently adopted and overwritten, which is the one outcome a restore must
// never produce.
//
// The staged entries are therefore moved in one by one.  That is not atomic as
// a whole, so any failure moves every entry back where it came from and removes
// the directory again: the destination is either absent, or the complete proven
// tree.  Entries are only ever moved, never deleted, so nothing of anyone
// else's can be destroyed by the rollback -- and a directory that is no longer
// empty refuses to be removed, so the rollback stops rather than deletes.
function commitStagedRoot(staging, destination) {
    fs.mkdirSync(destination, { mode: DIRECTORY_MODE });
    fs.chmodSync(destination, DIRECTORY_MODE);
    const moved = [];
    try {
        for (const entry of fs.readdirSync(staging)) {
            fs.renameSync(path.join(staging, entry), path.join(destination, entry));
            moved.push(entry);
        }
    } catch (error) {
        rollbackCommittedEntries(error, moved, staging, destination);
        throw error;
    }
    try {
        fs.rmdirSync(staging);
    } catch {
        // An empty staging directory that will not go away is untidy, not
        // unsafe, and the restored root is already complete and proven.
    }
    return moved.length;
}

function rollbackCommittedEntries(error, moved, staging, destination) {
    for (const entry of moved.reverse()) {
        try {
            fs.renameSync(path.join(destination, entry), path.join(staging, entry));
        } catch (rollbackError) {
            error.message = `${error.message} (rollback could not return ${entry}: ${rollbackError.code || rollbackError.message})`;
        }
    }
    try {
        fs.rmdirSync(destination);
    } catch (rollbackError) {
        error.message = `${error.message} (the destination could not be removed again: ${rollbackError.code || rollbackError.message})`;
    }
}

// The proof reports the paths it ran against, which are the staging paths the
// tree had before it moved.  Handing those back would name locations that no
// longer exist, so the layout is recomputed from the final destination -- it is
// a pure function of the destination and the manifest, so this is a
// recalculation rather than a rewrite of what the proof found.  The bytes,
// hashes, modes and identity in the report are the proof's own and are carried
// through untouched.
function relocateRestoredReport(report, destinationRoot, manifest) {
    const layout = restoredLayout(destinationRoot, manifest);
    return Object.freeze({
        ...report,
        destination_root: destinationRoot,
        authority_root: layout.authority_root,
        ledger_root: layout.ledger_root,
        allocation_artifact_path: layout.allocation_artifact_path,
        quota_config_path: layout.quota_config_path,
    });
}

// `sourceRoots` is how a caller that knows where the source lives states it.  A
// restore into a directory that contains, or is contained by, the very root it
// was taken from would prove nothing about isolating a failure domain, so the
// caller is expected to pass them and the check is skipped only when it
// genuinely has no filesystem source (a remote transport).
async function executeRestore({ transport, snapshotId, destinationRoot, sourceRoots = [], includeFreshProcess = false, spawn = spawnSync, execPath = process.execPath } = {}) {
    assertTransportContract(transport);
    assertGenerationId(snapshotId);

    // The precondition is the canonical verification, not the completeness
    // marker.
    //
    // `loadAcceptedManifest` answers "was this generation sealed?": the marker
    // exists and is structurally valid, it names the manifest that exists, and
    // the manifest is byte for byte the one the marker bound.  It is
    // deliberately not the whole contract.  The marker/manifest identity
    // agreement, the artifact hashes and sizes, the required categories, the
    // exact object set and the source summary are `verifySnapshot`'s, and the
    // manifest validator leaves them there on purpose so each keeps its own
    // failure code.
    //
    // Restoring on the marker alone therefore admitted a generation the
    // canonical verifier refuses: an object no manifest entry accounts for, or
    // a marker whose counts disagree with the manifest it binds, still
    // materialized a complete restored tree, because the restore path never
    // asked the question that would have refused it.
    //
    // The gate is `verifySnapshot` itself rather than a second implementation
    // of it.  A restore-local re-check would be a second opinion free to drift
    // from the canonical one, and the two would disagree silently; asking the
    // canonical verifier is what makes it impossible for the restore path to
    // accept a generation that `stage_d_restore_verify.js --verify-only`
    // rejects.
    //
    // Nothing is admitted before it.  The destination is not evaluated, no
    // staging directory is created and no object is read for materialization
    // until the verifier has returned PASS; a generation that fails is refused
    // with the verifier's own failure codes, and the destination is left
    // exactly as it was found.
    //
    // This is an admission gate, not an atomic verify-and-restore.  What it
    // guarantees is bounded by the transport: create-only writes and no delete
    // verb, with a generation id that is never reused, so the objects verified
    // here are the objects read below.  Where the store is a local filesystem,
    // each object's size and hash are re-checked as it is written and the whole
    // tree is proved again through the canonical readers before the commit, so
    // a swap performed through the transport is caught before anything is
    // committed -- but the window is not claimed to be closed against a process
    // that mutates the store's directory directly, which is outside this
    // module's threat model and has write authority there already.
    const verification = assertSnapshotVerification(await verifySnapshot({ transport, snapshotId }));

    const { manifest, manifest_sha256: manifestSha256 } = await loadAcceptedManifest({ transport, snapshotId });

    const resolvedDestination = assertFreshDestination(destinationRoot, { sourceRoots });
    const staging = createStagingRoot(resolvedDestination);
    const layout = restoredLayout(staging, manifest);

    const written = [];
    for (const artifact of manifest.artifacts) {
        const bytes = await transport.getObject({ key: artifact.object_key });
        if (bytes === null || bytes === undefined) throw new SnapshotIntegrityError(`the generation is missing ${artifact.logical_path} and cannot be restored`);
        if (bytes.length !== artifact.size) throw new SnapshotIntegrityError(`the generation holds ${artifact.logical_path} at ${bytes.length} bytes but the manifest declares ${artifact.size}`);
        if (sha256Hex(bytes) !== artifact.sha256) throw new SnapshotIntegrityError(`the generation holds ${artifact.logical_path} with content the manifest does not bind`);
        const mode = FILE_MODES[artifact.category];
        if (mode === undefined) throw new SnapshotIntegrityError(`no restored file mode is defined for category ${artifact.category}`);
        const absolute = writeRestoredFile(staging, artifact.logical_path, bytes, mode);
        written.push(Object.freeze({ logical_path: artifact.logical_path, absolute_path: absolute, mode }));
    }

    const report = await proveRestoredRoot({ destinationRoot: staging, manifest, layout, includeFreshProcess, spawn, execPath });
    const full = Object.freeze({
        ...report,
        snapshot_id: snapshotId,
        manifest_sha256: manifestSha256,
        // The verification this restore was admitted on, carried into the
        // report so the restored tree arrives with the proof that the gate ran
        // and on what evidence it passed -- a caller holding only the report can
        // see which generation was verified and against which object set.
        snapshot_verification: verification,
        restored_object_count: written.length,
        transport: transport.describe(),
    });
    if (full.result !== 'PASS') throw new RestoreProofError(`restored root failed proof: ${full.failures.join('; ')}`, full);

    // The commit: the destination is created create-only and the proven tree is
    // moved into it.  An interruption returns it to non-existent rather than
    // leaving a partial authority behind.
    commitStagedRoot(staging, resolvedDestination);
    return relocateRestoredReport(full, resolvedDestination, manifest);
}

module.exports = {
    RESTORE_VERSION,
    DIRECTORY_MODE,
    FILE_MODES,
    RestoreProofError,
    assertFreshDestination,
    restoredLayout,
    buildFreshProcessProbe,
    proveColdLoadInFreshProcess,
    proveRestoredRoot,
    executeRestore,
};
