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
const { ALLOCATION_FILE, deriveRequiredDirectoriesForLegacyManifest } = require('./snapshotInputs');
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

// Which directories the restored tree must contain, and where that answer came
// from.
//
// There are two sources and the report names which was used, rather than
// presenting both as one fact.  A generation written by the current writer
// carries `required_directories` and the manifest is authoritative.  A
// generation written before the field existed does not, and the requirement is
// re-derived from the canonical layout instead; that derivation is a statement
// about the layout every ledger root has, not about the generation being read,
// which is what keeps it version-bound rather than snapshot-bound.
function resolveRequiredDirectories(manifest) {
    if (Object.hasOwn(manifest, 'required_directories')) {
        // Present-but-not-an-array is refused here rather than spread.  The
        // manifest validator refuses the same shape with the same words, and a
        // caller holding a hand-built manifest should get that refusal rather
        // than a TypeError from an iterator.
        const declared = manifest.required_directories;
        if (!Array.isArray(declared)) throw new SnapshotIntegrityError('snapshot manifest required_directories must be an array');
        return Object.freeze({
            directories: Object.freeze([...declared]),
            source: 'MANIFEST_REQUIRED_DIRECTORIES',
        });
    }
    return Object.freeze({
        directories: deriveRequiredDirectoriesForLegacyManifest(manifest.artifacts),
        source: 'DERIVED_FROM_CANONICAL_LAYOUT',
    });
}

function restoredLayout(destinationRoot, manifest) {
    const authorityRoot = path.join(destinationRoot, 'transactions');
    const ledgerRoot = path.join(destinationRoot, 'request-accounting');
    const allocation = manifest.artifacts.find(artifact => artifact.category === 'allocation_authority');
    const quota = manifest.artifacts.find(artifact => artifact.category === 'quota_config');
    if (!allocation) throw new SnapshotIntegrityError('the generation carries no allocation authority artifact and cannot be restored');
    if (!quota) throw new SnapshotIntegrityError('the generation carries no quota configuration artifact and cannot be restored');
    const required = resolveRequiredDirectories(manifest);
    return Object.freeze({
        authority_root: authorityRoot,
        ledger_root: ledgerRoot,
        allocation_artifact_path: path.join(destinationRoot, allocation.logical_path),
        quota_config_path: path.join(destinationRoot, quota.logical_path),
        allocation_logical_path: allocation.logical_path,
        quota_logical_path: quota.logical_path,
        store_path: path.join(authorityRoot, 'STORE.json'),
        expected_allocation_basename: ALLOCATION_FILE,
        required_directories: required.directories,
        required_directories_source: required.source,
    });
}

// Created explicitly, before any file is written.
//
// Most of these directories would come into existence as a side effect of
// writing the files beneath them, and that is precisely why the one that holds
// no files was invisible: nothing in a restore ever asked for a directory, only
// for the files inside it, so an empty `entries/` was a thing the restore
// produced only when the ledger happened to be non-empty.  Asking for the
// layout directly is what turns that coincidence into a guarantee.
//
// The containment check is not redundant with the manifest validator's.  This
// is the point where a logical name becomes a filesystem path, and the promise
// that it stays inside the destination is this function's to keep whatever
// supplied the name -- the manifest, a derivation from it, or a future caller.
function createRequiredDirectories(root, directories) {
    const created = [];
    for (const directory of directories) {
        const absolute = path.resolve(root, directory);
        const relative = path.relative(root, absolute);
        if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
            throw new SnapshotIntegrityError(`required directory escapes the destination root: ${directory}`);
        }
        createDirectory(root, absolute);
        created.push(Object.freeze({ logical_path: directory, absolute_path: absolute }));
    }
    return created;
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

// The directories the manifest or the canonical layout requires, checked as
// requirements rather than assumed from the files around them.  A generation
// whose ledger is empty has no artifact that would create `request-accounting/
// entries`, so "the files all match" is not evidence that the tree is the one
// the reader accepts -- which is exactly the gap this restores.
//
// The failure is named here, in the manifest's own vocabulary.  Left to the
// canonical reader it arrives as an ENOENT naming a path under /proc that the
// operator never wrote, because the reader opens directories through a
// descriptor-scoped walk; a report that says which logical directory is missing
// is the difference between a diagnosable restore and an inexplicable one.
function compareRestoredDirectories(resolvedRoot, layout, failures) {
    const observed = [];
    for (const directory of layout.required_directories) {
        const absolute = path.join(resolvedRoot, directory);
        let stat;
        try {
            stat = fs.lstatSync(absolute);
        } catch (error) {
            if (error.code !== 'ENOENT') throw error;
            failures.push(`the restored tree is missing the required directory ${directory}`);
            continue;
        }
        if (stat.isSymbolicLink() || !stat.isDirectory()) {
            failures.push(`the restored required directory ${directory} is not a plain directory`);
            continue;
        }
        observed.push(Object.freeze({ logical_path: directory, mode: stat.mode & 0o7777 }));
    }
    return observed;
}

// Reads the restored root back through the canonical readers and compares
// everything against the manifest.  Performs no writes.
async function proveRestoredRoot({ destinationRoot, manifest, layout = null, includeFreshProcess = false, spawn = spawnSync, execPath = process.execPath } = {}) {
    const resolvedRoot = path.resolve(assertNotGovernedProductionPath(destinationRoot, 'restore destination root'));
    const resolvedLayout = layout || restoredLayout(resolvedRoot, manifest);
    const failures = [];

    // The directory requirements are checked first, before any canonical reader
    // is asked anything, because a missing required directory is precisely what
    // makes those readers throw: `readRequestLedger` opens a ledger root through
    // a descriptor-scoped walk and reports the absence of `entries/` as an
    // ENOENT naming a path under /proc.  Asking it first would replace the named
    // failure below with that ENOENT, which is the unhelpful message the whole
    // repair exists to remove.
    const restoredDirectories = compareRestoredDirectories(resolvedRoot, resolvedLayout, failures);
    const directoriesSatisfied = failures.length === 0;

    // The files are compared either way.  They are read by their manifest paths
    // and do not depend on the directory walk, so a report of a tree whose
    // layout is incomplete still says what content it did find.
    const restoredFiles = compareRestoredFiles(resolvedRoot, manifest, failures);

    // The identity half of the proof is skipped rather than attempted when the
    // layout is incomplete.  `proof` is null in that case and the report carries
    // the failures it did find, which is the truthful account: the restored root
    // could not be loaded, and the reason is named.
    const proof = directoriesSatisfied ? readRestoredIdentity(resolvedLayout) : null;
    if (proof !== null) {
        compareIdentity(proof, manifest, failures, 'restored authority');
        compareGovernedHashes(proof, manifest, failures);
    }

    const freshProcess = includeFreshProcess && directoriesSatisfied ? proveColdLoadInFreshProcess(resolvedLayout, { spawn, execPath }) : null;
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
        // Both halves of the directory claim: what the restore was required to
        // produce, where that requirement came from, and what it found.  A
        // reader of the report can tell a generation that described its own
        // layout from one whose layout was re-derived, without having to
        // re-open the manifest to find out which.
        required_directories: Object.freeze([...resolvedLayout.required_directories]),
        required_directories_source: resolvedLayout.required_directories_source,
        restored_directories: Object.freeze(restoredDirectories),
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
// The staging root is named for the invocation that created it: the random
// suffix is drawn here, held in a local, and never derived from anything the
// caller supplied.  That is what makes "the staging root created by this exact
// invocation" a decidable question, and it is the precondition for removing one
// at all.
function createStagingRoot(destination) {
    const staging = path.join(path.dirname(destination), `.${path.basename(destination)}.restore-staging-${crypto.randomBytes(8).toString('hex')}`);
    if (isGovernedProductionPath(staging)) throw new SnapshotIntegrityError(`restore staging root must never be the governed production area: ${staging}`);
    fs.mkdirSync(staging, { mode: DIRECTORY_MODE });
    fs.chmodSync(staging, DIRECTORY_MODE);
    return staging;
}

// Removes the *contents* of a directory this invocation created, one entry at a
// time, never following a symbolic link.
//
// The reach of this walk is bounded by construction rather than by a check: it
// starts at a path the caller minted and held in a local variable, and every
// other path it can name is that path joined with a name `readdirSync` returned
// from a directory it has already visited.  `readdirSync` cannot return `..`,
// so there is no traversal to refuse and no denylist to keep current.
//
// A link is unlinked, never entered.  Descending through one would make the
// walk's reach a property of whatever the link happens to point at, which is
// the opposite of a bounded cleanup -- and the restored tree is written with
// O_NOFOLLOW and refuses symbolic-link parents, so a link here is foreign
// content, which is exactly what must not be walked into.
function removeStagingContents(directory) {
    for (const name of fs.readdirSync(directory)) {
        const absolute = path.join(directory, name);
        const stat = fs.lstatSync(absolute);
        if (stat.isDirectory() && !stat.isSymbolicLink()) {
            removeStagingContents(absolute);
            // `rmdirSync` refuses a directory that is not empty, so a race that
            // puts something back between the walk and this call stops the
            // cleanup instead of deleting whatever arrived.
            fs.rmdirSync(absolute);
            continue;
        }
        fs.unlinkSync(absolute);
    }
}

// Runs when a restore fails.  Its whole job is to leave nothing behind, and its
// whole risk is that "nothing" is not what it removes -- so the destination is
// not a special case here, it is simply a different path, and nothing outside
// the staging root is ever named.
//
// A cleanup failure is recorded on the error that caused it, never thrown in
// its place.  The restore already failed for a reason the operator needs, and
// replacing that reason with "the tidy-up also failed as well" would hide the
// one that matters.  The note is therefore best-effort: an error that cannot
// carry one is still the error that gets reported.
function discardStagingRoot(staging, destination, error) {
    let cleanupFailure = null;
    try {
        if (staging === destination) throw new SnapshotIntegrityError('refusing to clean a staging root that is the destination itself');
        const stat = fs.lstatSync(staging);
        if (stat.isSymbolicLink() || !stat.isDirectory()) throw new SnapshotIntegrityError(`the staging root is not a plain directory: ${staging}`);
        removeStagingContents(staging);
        fs.rmdirSync(staging);
    } catch (thrown) {
        cleanupFailure = thrown;
    }
    if (cleanupFailure === null) return;
    try {
        error.message = `${error.message} (the staging tree at ${staging} could not be removed: ${cleanupFailure.code || cleanupFailure.message})`;
    } catch {
        // A thrown value that will not carry a note is still the failure to
        // report; losing the note is strictly better than losing the reason.
    }
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

    // Everything below happens inside a tree this invocation created, named with
    // entropy drawn for it, and never derived from anything the caller supplied.
    // That is what makes the cleanup in the `catch` decidable: there is exactly
    // one directory it may remove, and the destination is not it.
    //
    // The staging tree used to be left behind on failure, on the reasoning that
    // it was visible evidence of the attempt and that the destination was
    // untouched either way.  The destination part was true; the evidence part
    // was the problem.  A failed restore is the common case for a generation
    // that cannot be restored, so every retry left another complete copy of the
    // authority at 0700 beside the destination -- the tooling's own litter,
    // accumulating next to the thing it was supposed to be proving something
    // about, and indistinguishable at a glance from a restored root.
    const staging = createStagingRoot(resolvedDestination);
    try {
        const layout = restoredLayout(staging, manifest);

        // The layout goes in first and the content second, so a directory that
        // no artifact occupies is produced by the restore in its own right
        // rather than as a by-product of one that does.
        const createdDirectories = createRequiredDirectories(staging, layout.required_directories);

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
            // report so the restored tree arrives with the proof that the gate
            // ran and on what evidence it passed -- a caller holding only the
            // report can see which generation was verified and against which
            // object set.
            snapshot_verification: verification,
            restored_object_count: written.length,
            restored_directory_count: createdDirectories.length,
            transport: transport.describe(),
        });
        if (full.result !== 'PASS') throw new RestoreProofError(`restored root failed proof: ${full.failures.join('; ')}`, full);

        // The commit: the destination is created create-only and the proven tree
        // is moved into it.  An interruption returns it to non-existent rather
        // than leaving a partial authority behind.
        commitStagedRoot(staging, resolvedDestination);
        return relocateRestoredReport(full, resolvedDestination, manifest);
    } catch (error) {
        discardStagingRoot(staging, resolvedDestination, error);
        throw error;
    }
}

module.exports = {
    RESTORE_VERSION,
    DIRECTORY_MODE,
    FILE_MODES,
    RestoreProofError,
    assertFreshDestination,
    restoredLayout,
    resolveRequiredDirectories,
    createRequiredDirectories,
    buildFreshProcessProbe,
    proveColdLoadInFreshProcess,
    proveRestoredRoot,
    executeRestore,
};
