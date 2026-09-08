'use strict';

// The only transaction-v1 authority transition is one same-device directory
// rename from .staging/ into committed/.  Nothing below staging is authority.
const fs = require('node:fs');
const path = require('node:path');
const { ARTIFACT_FILES, TRANSACTION_FILES, canonicalBytes, canonicalJson, descriptorForBytes, validateManifest, createCommittedMarker } = require('./transactionContract');
const { readStoreContract } = require('./transactionStore');
const { openMarketEvidenceAuthoritySnapshot, readPackage } = require('./authorityReader');
const { isVerifiedProspectiveTransactionCandidate, finalizeProspectiveMarketEvidenceTransactionForPublication } = require('./prospectiveBatch');

function fail(code, message, extra = {}) { const error = new Error(message); error.code = code; Object.assign(error, extra); throw error; }
function assertControlledDirectory(stat, label) {
    const owner = typeof process.getuid === 'function' ? process.getuid() : stat.uid;
    if ((stat.uid !== owner && stat.uid !== 0) || (stat.mode & 0o022) !== 0) {
        fail('UNSAFE_PATH', `${label} must be runtime- or root-owned and not group/world writable`);
    }
}
// eslint-disable-next-line complexity -- pinned /proc descriptors and path-bound opens have distinct safety checks.
function openDirectoryDescriptor(target, label, expected = null) {
    const pinnedDescriptorPath = /^\/proc\/self\/fd\/\d+$/.test(target);
    if (pinnedDescriptorPath) {
        let fd;
        try {
            fd = fs.openSync(target, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0));
            const opened = fs.fstatSync(fd);
            if (!opened.isDirectory()) fail('UNSAFE_PATH', `${label} descriptor is not a directory`);
            assertControlledDirectory(opened, label);
            if (expected && (opened.dev !== expected.dev || opened.ino !== expected.ino)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} identity is not the expected authority generation`);
            return Object.freeze({ fd, identity: Object.freeze({ dev: opened.dev, ino: opened.ino, mode: opened.mode, uid: opened.uid, gid: opened.gid }) });
        } catch (error) {
            if (fd !== undefined) fs.closeSync(fd);
            throw error;
        }
    }
    const before = fs.lstatSync(target);
    if (before.isSymbolicLink() || !before.isDirectory()) fail('UNSAFE_PATH', `${label} must be a non-symlink directory`);
    const fd = fs.openSync(target, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0) | (fs.constants.O_NOFOLLOW || 0));
    try {
        const opened = fs.fstatSync(fd);
        if (!opened.isDirectory() || opened.dev !== before.dev || opened.ino !== before.ino) fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed during open`);
        assertControlledDirectory(opened, label);
        if (expected && (opened.dev !== expected.dev || opened.ino !== expected.ino)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} identity is not the expected authority generation`);
        return Object.freeze({ fd, identity: Object.freeze({ dev: opened.dev, ino: opened.ino, mode: opened.mode, uid: opened.uid, gid: opened.gid }) });
    } catch (error) { fs.closeSync(fd); throw error; }
}
function descriptorPath(fd) {
    if (process.platform !== 'linux') fail('UNSUPPORTED_PLATFORM', 'descriptor-bound transaction publication requires Linux /proc/self/fd');
    return `/proc/self/fd/${fd}`;
}
function closeDirectoryDescriptor(descriptor) { if (descriptor && Number.isInteger(descriptor.fd)) fs.closeSync(descriptor.fd); }
function fsyncDir(target, fault, point) { if (fault === point) fail('INJECTED_IO_FAILURE', `injected failure at ${point}`); const fd = fs.openSync(target, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0)); try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); } }
function safeWrite(target, bytes, fault, point) {
    if (fault === point) fail('INJECTED_IO_FAILURE', `injected failure at ${point}`);
    let fd;
    try {
        fd = fs.openSync(target, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0), 0o400);
        const buffer = Buffer.from(bytes, 'utf8'); let offset = 0;
        while (offset < buffer.length) { const written = fs.writeSync(fd, buffer, offset, buffer.length - offset); if (!Number.isInteger(written) || written <= 0 || written > buffer.length - offset) fail('SHORT_WRITE', `short write at ${point}`); offset += written; }
        fs.fchmodSync(fd, 0o400);
        if (fault === `${point}:fsync`) fail('INJECTED_IO_FAILURE', `injected failure at ${point}:fsync`);
        fs.fsyncSync(fd);
    } finally { if (fd !== undefined) fs.closeSync(fd); }
}
function acquireLock(root, rootDescriptor = null) {
    const lock = rootDescriptor ? path.join(descriptorPath(rootDescriptor.fd), '.writer-lock') : path.join(root, '.writer-lock'); let fd;
    const syncRoot = () => {
        if (rootDescriptor) fs.fsyncSync(rootDescriptor.fd);
        else fsyncDir(root);
    };
    const deadline = Date.now() + 5000;
    while (fd === undefined) {
        try { fd = fs.openSync(lock, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0), 0o400); }
        catch (error) {
            if (error?.code !== 'EEXIST') throw error;
            const stat = fs.lstatSync(lock); if (stat.isSymbolicLink() || !stat.isFile()) fail('UNSAFE_LOCK', 'transaction store writer lock is unsafe');
            if (Date.now() >= deadline) fail('WRITER_LOCKED', 'transaction store writer lock did not clear; manual recovery is required');
            Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
        }
    }
    fs.writeFileSync(fd, 'market-evidence-transaction-v1\n'); fs.fchmodSync(fd, 0o400); fs.fsyncSync(fd);
    const lockIdentity = fs.fstatSync(fd);
    // eslint-disable-next-line complexity -- release distinguishes held, replaced and next-owner lock states.
    return () => {
        let released = false;
        let releaseError = null;
        try {
            const held = fs.fstatSync(fd);
            if (held.dev !== lockIdentity.dev || held.ino !== lockIdentity.ino) fail('UNSAFE_LOCK', 'writer lock descriptor changed while held');
            const current = fs.lstatSync(lock);
            if (current.isSymbolicLink() || !current.isFile() || current.dev !== lockIdentity.dev || current.ino !== lockIdentity.ino) fail('UNSAFE_LOCK', 'writer lock changed while held');
            const final = fs.lstatSync(lock);
            if (final.isSymbolicLink() || !final.isFile() || final.dev !== lockIdentity.dev || final.ino !== lockIdentity.ino) fail('UNSAFE_LOCK', 'writer lock changed during release');
            fs.unlinkSync(lock);
            syncRoot();
            // Do not inspect the pathname again after unlink.  A legitimate
            // next owner may create a fresh lock between unlink and the
            // directory fsync; treating that fresh inode as our release
            // outcome would reintroduce a check-then-use race and could turn a
            // completed publication into COMMIT_OUTCOME_UNKNOWN.  The
            // pre-unlink identity checks plus successful unlink/fsync are the
            // authoritative release boundary. Any unlink or fsync error
            // remains ambiguous and is surfaced to the caller.
            released = true;
        } catch (error) {
            releaseError = error;
            throw error;
        } finally {
            fs.closeSync(fd);
            if (!released && !releaseError) fail('UNSAFE_LOCK', 'writer lock release was ambiguous; manual recovery is required');
        }
    };
}
function candidateFiles(candidate) {
    if (!isVerifiedProspectiveTransactionCandidate(candidate)) fail('UNVERIFIED_CANDIDATE', 'verified ProspectiveTransactionCandidate is required');
    const manifest = validateManifest(candidate.manifest);
    if (candidate.transaction_id !== manifest.transaction_id || candidate.transaction_content_hash !== manifest.transaction_content_hash || candidate.post_state_hash !== manifest.post_state_hash) fail('CANDIDATE_CONTRACT', 'candidate transaction identity does not match manifest');
    const bytes = { ...candidate.artifact_bytes, 'manifest.json': canonicalBytes(manifest), COMMITTED: canonicalBytes(createCommittedMarker(manifest)) };
    if (canonicalJson(Object.keys(bytes).sort()) !== canonicalJson([...TRANSACTION_FILES].sort())) fail('CANDIDATE_CONTRACT', 'candidate does not contain the exact transaction file set');
    for (const name of ARTIFACT_FILES) {
        const semanticBytes = name === 'observations.jsonl'
            ? (candidate.observations.length ? `${candidate.observations.map(row => { const copy = { ...row }; delete copy.projection_available_at; return canonicalJson(copy); }).join('\n')}\n` : '')
            : bytes[name];
        const descriptor = descriptorForBytes(name, bytes[name], candidate.artifacts[name].record_count, semanticBytes);
        if (canonicalJson(descriptor) !== canonicalJson(manifest.artifacts[name])) fail('CANDIDATE_CONTRACT', `candidate artifact does not match manifest: ${name}`);
    }
    return { manifest, bytes };
}
function existingLogicalBatch(committed, logicalBatchKey) {
    for (const name of fs.readdirSync(committed)) {
        const pkg = readPackage(committed, name);
        if (pkg.manifest.logical_batch_key === logicalBatchKey) return pkg.manifest;
    }
    return null;
}
function assertParent(snapshot, manifest) {
    if (snapshot.head_transaction_id !== manifest.parent_transaction_id || snapshot.head_transaction_content_hash !== manifest.parent_transaction_content_hash || snapshot.state_hash !== manifest.expected_parent_state_hash) fail('STALE_PARENT_TRANSACTION', 'candidate parent no longer matches the authoritative head');
}
function commitOutcomeUnknown(candidate, original) {
    fail('COMMIT_OUTCOME_UNKNOWN', 'rename outcome cannot be authoritatively resolved; reopen the transaction authority before retrying', { transaction_id: candidate.transaction_id, logical_batch_key: candidate.logical_batch_key, cause: original, resolution: 'fresh authority reopen required before retry' });
}
function resolveAfterRename({ storeRoot, allocationArtifactPath, candidate, original, expectedCommittedIdentity = null }) {
    try {
        const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath, expectedCommittedIdentity });
        if (snapshot.head_transaction_id === candidate.transaction_id && snapshot.state_hash === candidate.post_state_hash) return Object.freeze({ status: 'COMMITTED', transaction_id: candidate.transaction_id, reused: false, snapshot });
    } catch (error) { commitOutcomeUnknown(candidate, error); }
    throw original;
}
// eslint-disable-next-line complexity -- publication explicitly enumerates every durability boundary.
function publishProspectiveMarketEvidenceTransaction({ storeRoot, allocationArtifactPath, candidate, fault = null, expectedStagingIdentity = null, expectedCommittedIdentity = null } = {}) {
    const planned = candidateFiles(candidate);
    const contract = readStoreContract({ storeRoot, allocationArtifactPath }); const root = contract.root;
    let rootDescriptor;
    const stagingPath = path.join(root, '.staging'); const committedPath = path.join(root, 'committed');
    let stagingDescriptor;
    let committedDescriptor;
    try {
        rootDescriptor = openDirectoryDescriptor(root, 'transaction authority root');
        const pinnedRoot = descriptorPath(rootDescriptor.fd);
        stagingDescriptor = openDirectoryDescriptor(path.join(pinnedRoot, '.staging'), 'staging directory', expectedStagingIdentity);
        committedDescriptor = openDirectoryDescriptor(path.join(pinnedRoot, 'committed'), 'committed directory', expectedCommittedIdentity);
    } catch (error) {
        closeDirectoryDescriptor(committedDescriptor);
        closeDirectoryDescriptor(stagingDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
        throw error;
    }
    const staging = descriptorPath(stagingDescriptor.fd);
    const committed = descriptorPath(committedDescriptor.fd);
    const stagingStat = fs.fstatSync(stagingDescriptor.fd); const committedStat = fs.fstatSync(committedDescriptor.fd);
    if (stagingStat.dev !== committedStat.dev) {
        closeDirectoryDescriptor(committedDescriptor);
        closeDirectoryDescriptor(stagingDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
        fail('CROSS_DEVICE_PUBLICATION', 'staging and committed directories must share a filesystem');
    }
    let release;
    try { release = acquireLock(root, rootDescriptor); }
    catch (error) {
        closeDirectoryDescriptor(committedDescriptor);
        closeDirectoryDescriptor(stagingDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
        throw error;
    }
    let possibleRename = false; let outcome = null; let pendingError = null; let publicationCandidate = null;
    try {
        const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: root, allocationArtifactPath, expectedCommittedIdentity: committedDescriptor.identity });
        const sameLogical = existingLogicalBatch(committed, planned.manifest.logical_batch_key);
        if (sameLogical) {
            // A retry rebuilt against the already-published parent contains a
            // zero-record delta, while the first attempt contained the full
            // batch.  Only that exact retry shape may reuse the prior commit;
            // a non-empty delta with the same logical source identity is a
            // conflicting projection/configuration and must fail closed.
            const sameSource = canonicalJson(sameLogical.source) === canonicalJson(planned.manifest.source);
            const isExactRetry = sameSource && sameLogical.logical_content_hash === planned.manifest.logical_content_hash;
            const isEmptyRetry = planned.manifest.decision_count === 0 && planned.manifest.observation_count === 0 && planned.manifest.registry_delta_count === 0;
            if (!isExactRetry && !(sameSource && isEmptyRetry)) fail('LOGICAL_BATCH_CONFLICT', 'logical batch key already exists with different source content or transaction delta');
            outcome = Object.freeze({ status: 'COMMITTED', transaction_id: sameLogical.transaction_id, reused: true, snapshot });
        } else {
            assertParent(snapshot, planned.manifest);
            // T2 is finalized only after lock acquisition and the authoritative
            // parent recheck.  It participates in the exact transaction ID;
            // logical retry identity remains a separate contract.
            publicationCandidate = finalizeProspectiveMarketEvidenceTransactionForPublication(candidate);
            const { manifest, bytes } = candidateFiles(publicationCandidate);
            if (manifest.logical_batch_key !== planned.manifest.logical_batch_key || manifest.logical_content_hash !== planned.manifest.logical_content_hash) fail('CANDIDATE_CONTRACT', 'publisher finalization changed logical batch identity');
            assertParent(snapshot, manifest);
            const finalPath = path.join(committed, manifest.transaction_id);
            if (fs.existsSync(finalPath)) fail('FINAL_TARGET_EXISTS', 'committed transaction target already exists without a matching logical batch');
            const stagePath = path.join(staging, manifest.transaction_id); if (fs.existsSync(stagePath)) fail('STAGING_RESIDUE_EXISTS', 'staging residue exists; manual recovery is required');
            fs.mkdirSync(stagePath, { mode: 0o700 });
            for (const name of [...ARTIFACT_FILES, 'manifest.json', 'COMMITTED']) safeWrite(path.join(stagePath, name), bytes[name], fault, name);
            fsyncDir(stagePath, fault, 'staging-directory-fsync');
            if (fault === 'staging-tamper') fs.appendFileSync(path.join(stagePath, 'observations.jsonl'), 'tamper\n');
            readPackage(staging, manifest.transaction_id);
            if (fault === 'before-rename') fail('INJECTED_IO_FAILURE', 'injected failure before rename');
            try { if (fault === 'rename') fail('INJECTED_IO_FAILURE', 'injected failure at rename'); fs.renameSync(stagePath, finalPath); possibleRename = true; }
            catch (error) { const resolved = resolveAfterRename({ storeRoot: root, allocationArtifactPath, candidate: publicationCandidate, original: error, expectedCommittedIdentity: committedDescriptor.identity }); possibleRename = resolved.status === 'COMMITTED'; outcome = resolved; }
            if (!outcome) {
                try { fsyncDir(committed, fault, 'committed-directory-fsync'); }
                catch (error) { outcome = resolveAfterRename({ storeRoot: root, allocationArtifactPath, candidate: publicationCandidate, original: error, expectedCommittedIdentity: committedDescriptor.identity }); }
            }
            if (!outcome) {
                try {
                    if (fault === 'final-reader-io') fail('INJECTED_IO_FAILURE', 'injected final authority reader I/O failure');
                    if (fault === 'final-reader-tamper') { const target = path.join(finalPath, 'manifest.json'); fs.chmodSync(target, 0o600); fs.appendFileSync(target, 'tamper\n'); fs.chmodSync(target, 0o400); }
                    const reopened = openMarketEvidenceAuthoritySnapshot({ storeRoot: root, allocationArtifactPath, expectedCommittedIdentity: committedDescriptor.identity });
                    if (reopened.head_transaction_id !== publicationCandidate.transaction_id || reopened.state_hash !== publicationCandidate.post_state_hash) fail('POST_RENAME_VERIFICATION_FAILED', 'committed transaction did not become the verified authority head');
                    outcome = Object.freeze({ status: 'COMMITTED', transaction_id: publicationCandidate.transaction_id, reused: false, snapshot: reopened });
                } catch (error) { commitOutcomeUnknown(publicationCandidate, error); }
            }
        }
    } catch (error) { pendingError = error; }
    try { release(); } catch (error) { pendingError = possibleRename && publicationCandidate ? (() => { try { commitOutcomeUnknown(publicationCandidate, error); } catch (unknown) { return unknown; } })() : error; }
    closeDirectoryDescriptor(committedDescriptor);
    closeDirectoryDescriptor(stagingDescriptor);
    closeDirectoryDescriptor(rootDescriptor);
    if (pendingError) throw pendingError;
    return outcome;
}

module.exports = { publishProspectiveMarketEvidenceTransaction };
